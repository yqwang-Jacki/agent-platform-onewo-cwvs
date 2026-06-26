from datetime import datetime, timedelta, timezone
from typing import Optional, List
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User, Publisher, Role

_bearer = HTTPBearer(auto_error=False)

# ── Role hierarchy (dynamic, loaded from DB) ──

# Cache for role hierarchy – loaded lazily from DB and refreshed per-session
_role_cache: Optional[dict] = None  # {"admin": {"level": 2, "label": "管理员", "permissions": [...]}, ...}


def _load_roles_from_db(db: Session) -> dict:
    """Load all active roles from DB into a {key: {level, label, permissions}} dict."""
    roles = db.query(Role).filter(Role.status == "active").all()
    return {
        r.key: {"level": r.level, "label": r.label, "permissions": r.permissions or []}
        for r in roles
    }


def get_role_hierarchy(db: Session = None) -> dict:
    """Get role hierarchy from cache or DB. Returns {key: level}."""
    global _role_cache
    if db is not None:
        _role_cache = _load_roles_from_db(db)
    if _role_cache is None:
        # During startup or tests, return hardcoded defaults
        return {"user": 0, "developer": 1, "admin": 2}
    return {k: v["level"] for k, v in _role_cache.items()}


def get_valid_roles(db: Session = None) -> set:
    return set(get_role_hierarchy(db).keys())


def get_role_labels(db: Session = None) -> dict:
    global _role_cache
    if db is not None:
        _role_cache = _load_roles_from_db(db)
    if _role_cache is None:
        return {"user": "普通用户", "developer": "开发者", "admin": "管理员"}
    return {k: v["label"] for k, v in _role_cache.items()}


def get_role_permissions(db: Session = None) -> dict:
    global _role_cache
    if db is not None:
        _role_cache = _load_roles_from_db(db)
    if _role_cache is None:
        return {
            "user": ["对话交互", "查看历史记录"],
            "developer": ["对话交互", "查看历史记录", "登录管理后台", "发布/管理 Agent", "查看用量统计"],
            "admin": ["对话交互", "查看历史记录", "登录管理后台", "发布/管理 Agent", "查看用量统计", "用户管理", "角色管理", "系统设置"],
        }
    return {k: v["permissions"] for k, v in _role_cache.items()}


# Legacy exports – callable functions for backward compat
# admin.py should use these with a db session: get_valid_roles(db), get_role_hierarchy(db), get_role_labels(db)
# But if no db provided, returns defaults


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def hash_password(password: str) -> str:
    return get_password_hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def verify_secretkey(plain: str, hashed: str) -> bool:
    return verify_password(plain, hashed)


def _has_role(user_role: str, required: str) -> bool:
    """Check if user_role is at least required_role in the hierarchy."""
    hierarchy = get_role_hierarchy()
    return hierarchy.get(user_role, -1) >= hierarchy.get(required, 99)


def has_role(user_role: str, required: str) -> bool:
    """Public alias for _has_role."""
    return _has_role(user_role, required)


def create_access_token(user_id: str, role: str = "user") -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: str, role: str = "user") -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "type": "refresh",
        "exp": datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证失效，请重新登录")


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if not creds:
        raise HTTPException(status_code=401, detail="缺少认证信息")
    payload = decode_token(creds.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="无效的 access token")
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
    return user


def _find_user_by_token_sub(payload: dict, db: Session) -> User:
    """Look up user: first by id, then via linked publisher by phone."""
    sub = payload["sub"]
    # Direct user lookup
    user = db.query(User).filter(User.id == sub).first()
    if user:
        return user
    # Fallback: token sub is a publisher appid, find linked user by phone
    pub = db.query(Publisher).filter(Publisher.appid == sub).first()
    if pub and pub.phone:
        user = db.query(User).filter(User.phone == pub.phone).first()
        if user:
            return user
    raise HTTPException(status_code=401, detail="认证失败")


def get_current_admin_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Require admin role."""
    if not creds:
        raise HTTPException(status_code=401, detail="缺少认证信息")
    payload = decode_token(creds.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="无效的 access token")
    user = _find_user_by_token_sub(payload, db)
    if user.status != "active":
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
    if not _has_role(user.role, "admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def require_role(*roles: str):
    """Dependency factory: require at least one of the given roles."""
    def checker(
        creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
        db: Session = Depends(get_db),
    ) -> User:
        if not creds:
            raise HTTPException(status_code=401, detail="缺少认证信息")
        payload = decode_token(creds.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="无效的 access token")
        user = _find_user_by_token_sub(payload, db)
        if user.status != "active":
            raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
        if not any(_has_role(user.role, r) for r in roles):
            raise HTTPException(status_code=403, detail="权限不足")
        return user
    return checker


def verify_publisher_key(
    appid: str,
    secretkey: str,
    db: Session,
) -> Publisher:
    pub = db.query(Publisher).filter(Publisher.appid == appid).first()
    if not pub or not verify_password(secretkey, pub.secretkey_hash):
        raise HTTPException(status_code=401, detail="appid 或 secretkey 错误")
    if pub.status != "active":
        raise HTTPException(status_code=403, detail="Publisher 已被禁用")
    return pub


def get_current_publisher(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Publisher:
    """Authenticate publisher via JWT (admin-backend login or API key)."""
    if not creds:
        raise HTTPException(status_code=401, detail="缺少认证信息")
    payload = decode_token(creds.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="无效的 access token")
    publisher = db.query(Publisher).filter(Publisher.appid == payload["sub"]).first()
    if publisher and publisher.status == "active":
        return publisher
    # Fallback: also accept user tokens with developer+ role
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if user and user.status == "active" and _has_role(user.role, "developer"):
        # Return a synthetic publisher for the user's linked publisher
        pub = db.query(Publisher).filter(Publisher.phone == user.phone).first()
        if pub and pub.status == "active":
            return pub
        raise HTTPException(status_code=403, detail="当前用户未关联发布者账号，请先注册发布者")
    raise HTTPException(status_code=401, detail="认证失败")

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models import User
from app.schemas import (
    UserRegister, UserLogin, TokenResponse,
    UserProfile, UserProfileUpdate,
)
from app.core import security
from datetime import datetime, timezone

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: UserRegister, db: Session = Depends(get_db)):
    # 唯一性校验
    if db.query(User).filter(User.sap_id == body.sap_id).first():
        raise HTTPException(400, "SAP 工号已被注册")
    if db.query(User).filter(User.phone == body.phone).first():
        raise HTTPException(400, "手机号已被注册")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(400, "邮箱已被注册")

    user = User(
        name=body.name,
        department=body.department,
        sap_id=body.sap_id,
        phone=body.phone,
        email=body.email,
        password_hash=security.hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, db: Session = Depends(get_db)):
    # 支持手机号或邮箱登录
    user = db.query(User).filter(
        (User.phone == body.account) | (User.email == body.account)
    ).first()
    if not user or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(401, "账号或密码错误")
    if user.status != "active":
        raise HTTPException(403, "账号已被禁用")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return _token_response(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    payload = security.decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(401, "无效的 refresh token")
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or user.status != "active":
        raise HTTPException(401, "用户不存在或已被禁用")
    return _token_response(user)


@router.get("/profile", response_model=UserProfile)
def get_profile(current_user: User = Depends(security.get_current_user)):
    return current_user


@router.put("/profile", response_model=UserProfile)
def update_profile(
    body: UserProfileUpdate,
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    if body.name is not None:
        current_user.name = body.name
    if body.department is not None:
        current_user.department = body.department
    if body.phone is not None:
        if db.query(User).filter(User.phone == body.phone, User.id != current_user.id).first():
            raise HTTPException(400, "手机号已被注册")
        current_user.phone = body.phone
    if body.email is not None:
        if db.query(User).filter(User.email == body.email, User.id != current_user.id).first():
            raise HTTPException(400, "邮箱已被注册")
        current_user.email = body.email
    db.commit()
    db.refresh(current_user)
    return current_user


def _token_response(user: User) -> TokenResponse:
    role = getattr(user, "role", "user")
    return TokenResponse(
        access_token=security.create_access_token(str(user.id), role),
        refresh_token=security.create_refresh_token(str(user.id), role),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

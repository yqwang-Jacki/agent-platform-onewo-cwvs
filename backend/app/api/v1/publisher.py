from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import (
    verify_password, create_access_token, get_password_hash,
    has_role, get_current_user,
)
from app.schemas import PublisherCreate, PublisherOut, TokenOut, PublisherLogin, PublisherWebLogin
from app.models import User, Publisher
import uuid

router = APIRouter()


@router.post("/register", response_model=PublisherOut, status_code=status.HTTP_201_CREATED)
def register_publisher(data: PublisherCreate, db: Session = Depends(get_db)):
    """注册新的发布者，生成 appid+secretkey（API 发布用）和 phone+password（管理后台登录用）"""
    from app.models import Publisher

    # 检查 appid 是否已存在
    if db.query(Publisher).filter(Publisher.appid == data.appid).first():
        raise HTTPException(status_code=400, detail="appid 已存在")

    # 检查手机号是否已被注册
    if db.query(Publisher).filter(Publisher.phone == data.phone).first():
        raise HTTPException(status_code=400, detail="手机号已被注册")

    # 创建发布者
    publisher = Publisher(
        appid=data.appid,
        secretkey_hash=get_password_hash(data.secretkey),
        name=data.name,
        phone=data.phone,
        password_hash=get_password_hash(data.password),
        quota_config={},
        status="active"
    )
    db.add(publisher)
    db.commit()
    db.refresh(publisher)

    return {
        "appid": publisher.appid,
        "name": publisher.name,
        "status": publisher.status,
        "created_at": publisher.created_at
    }


@router.post("/login", response_model=TokenOut)
def login_publisher(data: PublisherLogin, db: Session = Depends(get_db)):
    """发布者 API 登录（appid + secretkey），用于程序化发布 Agent"""
    from app.models import Publisher

    publisher = db.query(Publisher).filter(Publisher.appid == data.appid).first()
    if not publisher or not verify_password(data.secretkey, publisher.secretkey_hash):
        raise HTTPException(status_code=401, detail="appid 或 secretkey 错误")
    if publisher.status != "active":
        raise HTTPException(status_code=403, detail="Publisher 已被禁用")

    access_token = create_access_token(str(publisher.appid))
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/web-login", response_model=TokenOut)
def web_login_publisher(data: PublisherWebLogin, db: Session = Depends(get_db)):
    """管理后台 Web 登录：用户表鉴权 + 角色检查（需 developer 或 admin）"""
    # 从用户表查找
    user = db.query(User).filter(
        (User.phone == data.account) | (User.email == data.account)
    ).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已被禁用")
    if not has_role(user.role, "developer"):
        raise HTTPException(status_code=403, detail="需要开发者或管理员权限才能登录管理后台")

    # 查找关联的发布者（通过手机号关联）
    pub = db.query(Publisher).filter(Publisher.phone == user.phone).first()
    if not pub:
        # 自动创建发布者
        pub = Publisher(
            appid=f"pub_{user.sap_id}",
            secretkey_hash=get_password_hash(f"auto_{str(uuid.uuid4())[:16]}"),
            name=user.name,
            phone=user.phone,
            password_hash=user.password_hash,
            quota_config={},
            status="active",
        )
        db.add(pub)
        db.commit()
        db.refresh(pub)

    access_token = create_access_token(str(pub.appid), user.role)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_name": user.name,
        "user_role": user.role,
    }

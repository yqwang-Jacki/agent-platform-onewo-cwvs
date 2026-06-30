from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.api.v1 import auth, agents, chat, publisher, admin, platforms

# 导入连接器以触发自动注册
import app.connectors.gc_connector   # noqa: F401
import app.connectors.coze_connector  # noqa: F401

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时尝试建表和初始化数据，失败不崩溃（兼容无 VPC / 网络延迟等场景）
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("[OK] Database tables created/verified")
    except Exception as e:
        logger.warning(f"[WARN] Database create_all failed (app will still start): {e}")

    # 初始化测试账号（仅开发环境，MVP 用）
    db = None
    try:
        db = SessionLocal()
        from app.models import User, Publisher, Role
        from app.core.security import get_password_hash, _load_roles_from_db

        # Seed default roles
        default_roles = [
            {"key": "user", "label": "普通用户", "description": "通过用户端与已发布的 Agent 进行对话交互",
             "level": 0, "permissions": ["对话交互", "查看历史记录"], "is_system": True},
            {"key": "developer", "label": "开发者", "description": "可登录管理后台发布和管理 Agent，查看用量统计",
             "level": 1, "permissions": ["对话交互", "查看历史记录", "登录管理后台", "发布/管理 Agent", "查看用量统计"],
             "is_system": True},
            {"key": "admin", "label": "管理员", "description": "拥有系统所有权限，可管理用户、分配角色、管理系统设置",
             "level": 2, "permissions": ["对话交互", "查看历史记录", "登录管理后台", "发布/管理 Agent",
                                        "查看用量统计", "用户管理", "角色管理", "系统设置"],
             "is_system": True},
        ]
        for dr in default_roles:
            existing = db.query(Role).filter(Role.key == dr["key"]).first()
            if not existing:
                db.add(Role(**dr))
        db.commit()

        # Preload role hierarchy into cache
        _load_roles_from_db(db)

        if not db.query(User).first():
            users_data = [
                {"name": "管理员", "department": "技术部", "sap_id": "ADMIN001", "phone": "13800000000",
                 "email": "admin@example.com", "password": "Test123456", "role": "admin"},
                {"name": "开发者张三", "department": "AI平台组", "sap_id": "DEV001", "phone": "13800000001",
                 "email": "dev@example.com", "password": "Test123456", "role": "developer"},
                {"name": "普通用户", "department": "业务部", "sap_id": "USER001", "phone": "13800000002",
                 "email": "user@example.com", "password": "Test123456", "role": "user"},
            ]
            for u in users_data:
                db.add(User(
                    name=u["name"], department=u["department"], sap_id=u["sap_id"],
                    phone=u["phone"], email=u["email"],
                    password_hash=get_password_hash(u["password"]),
                    role=u["role"], status="active",
                ))
            db.commit()
            print("[OK] Created 3 test users: admin(13800000000) / developer(13800000001) / user(138000002), password Test123456")

        if not db.query(Publisher).first():
            test_publisher = Publisher(
                appid="test_app",
                secretkey_hash=get_password_hash("test_secret_key_123"),
                name="开发者张三",
                phone="13800000001",   # 关联 developer 用户
                password_hash=get_password_hash("Test123456"),
                quota_config={},
                status="active",
            )
            db.add(test_publisher)
            db.commit()
            print("[OK] Created test publisher: appid=test_app, secretkey=test_secret_key_123, phone=13800000001")
    except Exception as e:
        logger.warning(f"[WARN] Database seed/init failed (app will still start): {e}")
    finally:
        if db:
            db.close()

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="公司内部 Agent 发布平台 - 开发者提交 Agent API，平台生成可分享的 H5 对话页",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# V1 API routes
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["用户认证"])
app.include_router(publisher.router, prefix=f"{settings.API_V1_STR}/publisher", tags=["发布者管理"])
app.include_router(agents.router, prefix=f"{settings.API_V1_STR}/publisher/agents", tags=["Agent 管理"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["终端用户对话"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["管理员"])
app.include_router(platforms.router, prefix=f"{settings.API_V1_STR}", tags=["平台管理"])


@app.get("/health", tags=["系统"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}

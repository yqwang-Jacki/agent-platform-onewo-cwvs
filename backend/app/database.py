import sqlite3
from uuid import UUID
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings


# 注册 SQLite 的 UUID 适配器（开发环境使用 SQLite 时）
if settings.DATABASE_URL.startswith("sqlite"):
    sqlite3.register_adapter(UUID, lambda u: str(u))

# 判断是否使用 SQLite
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Sync engine for Alembic & general use
engine_args = {"pool_pre_ping": True, "echo": False}
if is_sqlite:
    # SQLite 需要额外配置
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, **engine_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

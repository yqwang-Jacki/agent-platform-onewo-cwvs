import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, JSON, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid_str():
    return str(uuid.uuid4())


class Publisher(Base):
    __tablename__ = "publishers"

    appid = Column(String(64), primary_key=True)
    secretkey_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(32), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    quota_config = Column(JSON, default=dict)
    status = Column(String(32), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    agents = relationship("Agent", back_populates="publisher", cascade="all, delete-orphan")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    appid = Column(String(64), ForeignKey("publishers.appid"), nullable=False)
    name = Column(String(255), nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    visibility = Column(String(32), default="public", nullable=False)
    permission_config = Column(JSON, default=None)
    status = Column(String(32), default="active", nullable=False)
    api_endpoint = Column(Text, nullable=True)
    api_headers = Column(JSON, default=dict)
    platform_type = Column(String(32), default="custom", nullable=False, index=True)
    platform_config = Column(JSON, default=dict)  # {bot_id, project_id, domain, appid, secret_key, ...}
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    publisher = relationship("Publisher", back_populates="agents")
    share_links = relationship("ShareLink", back_populates="agent", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="agent")
    token_usage = relationship("TokenUsageRecord", back_populates="agent")

    __table_args__ = (
        Index("idx_agents_appid_status", "appid", "status"),
    )


class ShareLink(Base):
    __tablename__ = "share_links"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    link_code = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(32), default="active", nullable=False)
    expire_at = Column(DateTime(timezone=True), default=None)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    agent = relationship("Agent", back_populates="share_links")

    __table_args__ = (
        Index("idx_share_links_link_code", "link_code"),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    sap_id = Column(String(64), unique=True, nullable=False, index=True)
    phone = Column(String(32), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), default="user", nullable=False, index=True)  # role key (FK to roles.key logically, but as string for simplicity)
    status = Column(String(32), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_login_at = Column(DateTime(timezone=True), default=None)

    conversations = relationship("Conversation", back_populates="user")
    token_usage = relationship("TokenUsageRecord", back_populates="user")


class Role(Base):
    """Dynamic role table with permission menus."""
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    key = Column(String(64), unique=True, nullable=False, index=True)  # "admin", "developer", "custom_role"
    label = Column(String(128), nullable=False)                       # "管理员", "开发者"
    description = Column(String(512), default="")
    level = Column(Integer, default=0, nullable=False)                 # hierarchy level, higher = more powerful
    permissions = Column(JSON, default=list)                           # e.g. ["对话交互", "用户管理", ...]
    is_system = Column(Boolean, default=False)                         # built-in roles cannot be deleted
    status = Column(String(32), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_active_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    agent = relationship("Agent", back_populates="conversations")
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_conversations_agent_user", "agent_id", "user_id"),
        Index("idx_conversations_user_active", "user_id", "last_active_at"),
        UniqueConstraint("agent_id", "user_id", name="uq_agent_user_one_conv"),
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    conv_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("idx_messages_conv_created", "conv_id", "created_at"),
    )


class TokenUsageRecord(Base):
    __tablename__ = "token_usage_records"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    appid = Column(String(64), nullable=False, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    usage_date = Column(DateTime(timezone=True), nullable=False, index=True)
    total_tokens = Column(Integer, default=0)
    request_count = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    agent = relationship("Agent", back_populates="token_usage")
    user = relationship("User", back_populates="token_usage")

    __table_args__ = (
        Index("idx_token_usage_agent_date", "agent_id", "usage_date"),
    )

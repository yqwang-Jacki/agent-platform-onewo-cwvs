from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ── Auth ─────────────────────────────────────────────

class UserRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=255)
    sap_id: str = Field(..., min_length=1, max_length=64)
    phone: str = Field(..., min_length=8, max_length=32)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    account: str = Field(..., description="手机号或邮箱")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserProfile(BaseModel):
    id: UUID
    name: str
    department: str
    sap_id: str
    phone: str
    email: str
    role: str = "user"
    status: str = "active"
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


# ── Publisher (开发者) ──────────────────────────────

class PublisherCreate(BaseModel):
    appid: str = Field(..., min_length=8, max_length=64, description="开发者自定义的 appid")
    secretkey: str = Field(..., min_length=16, max_length=128, description="开发者自定义的 secretkey（用于 API 发布）")
    name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=8, max_length=32, description="手机号（用于管理后台登录）")
    password: str = Field(..., min_length=8, max_length=128, description="登录密码（用于管理后台登录）")


class PublisherLogin(BaseModel):
    appid: str
    secretkey: str


class PublisherWebLogin(BaseModel):
    account: str = Field(..., description="手机号")
    password: str


class PublisherOut(BaseModel):
    appid: str
    name: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PublisherKeyResponse(BaseModel):
    appid: str
    secretkey: str   # 仅创建时返回明文，之后不可查
    name: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_name: Optional[str] = None
    user_role: Optional[str] = None


# ── Agent ────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    config: dict = Field(default_factory=dict)
    api_endpoint: Optional[str] = Field(None, description="开发者已部署的 Agent HTTP 接口地址 (自定义协议时必填)")
    api_headers: dict = Field(default_factory=dict, description="调用 Agent API 时附加的 HTTP 头")
    visibility: str = Field(default="public", pattern="^(public|department|specific)$")
    permission_config: Optional[dict] = None
    # 平台导入字段
    platform_type: str = Field(default="custom", description="平台类型: custom, gc, coze")
    platform_config: dict = Field(default_factory=dict, description="平台配置: {bot_id, project_id, domain, appid, secret_key, ...}")


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None
    api_endpoint: Optional[str] = None
    api_headers: Optional[dict] = None
    visibility: Optional[str] = Field(None, pattern="^(public|department|specific)$")
    permission_config: Optional[dict] = None
    status: Optional[str] = None
    platform_type: Optional[str] = None
    platform_config: Optional[dict] = None


class AgentResponse(BaseModel):
    id: UUID
    name: str
    visibility: str
    permission_config: Optional[dict] = None
    status: str
    api_endpoint: Optional[str] = None
    platform_type: str = "custom"
    platform_config: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentPublicInfo(BaseModel):
    id: UUID
    name: str
    visibility: str
    config: dict

    class Config:
        from_attributes = True


# ── Share Link ──────────────────────────────────────

class ShareLinkCreate(BaseModel):
    expire_days: Optional[int] = None


class ShareLinkResponse(BaseModel):
    id: UUID
    link_code: str
    status: str
    expire_at: Optional[datetime] = None
    created_at: datetime
    share_url: str  # 前端拼接的完整 URL

    class Config:
        from_attributes = True


# ── Conversation & Message ────────────────────────

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    stream: bool = True


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    tokens_used: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    id: UUID
    agent_id: UUID
    agent_name: str = ""
    created_at: datetime
    last_active_at: datetime
    message_count: int = 0
    last_message: str = ""

    class Config:
        from_attributes = True


class ConversationMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    stream: bool = False


class ConversationResponse(BaseModel):
    id: UUID
    agent_id: UUID
    agent_name: str = ""
    created_at: datetime
    last_active_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


class AgentListItem(BaseModel):
    id: UUID
    name: str
    visibility: str

    class Config:
        from_attributes = True


# ── Token Usage Stats ─────────────────────────────

class TokenUsageStats(BaseModel):
    agent_id: UUID
    agent_name: str
    user_id: Optional[UUID] = None
    user_name: Optional[str] = None
    usage_date: datetime
    total_tokens: int
    request_count: int


# ── Admin: User & Role Management ──────────────────

class UserAdminItem(BaseModel):
    id: UUID
    name: str
    department: str
    sap_id: str
    phone: str
    email: str
    role: str
    status: str
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """管理员编辑用户所有基本信息（不含密码）。"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    department: Optional[str] = Field(None, min_length=1, max_length=255)
    sap_id: Optional[str] = Field(None, min_length=1, max_length=64)
    phone: Optional[str] = Field(None, min_length=8, max_length=32)
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|disabled)$")


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=255)
    sap_id: str = Field(..., min_length=1, max_length=64)
    phone: str = Field(..., min_length=8, max_length=32)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="user")


class UserRoleUpdate(BaseModel):
    role: str = Field(..., min_length=1)


class UserStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|disabled)$")


class RoleInfo(BaseModel):
    key: str
    label: str
    level: int
    permissions: List[str]


# ── Admin: Dynamic Role CRUD ─────────────────────────

class RoleItem(BaseModel):
    id: UUID
    key: str
    label: str
    description: str = ""
    level: int = 0
    permissions: List[str] = []
    is_system: bool = False
    status: str = "active"
    created_at: datetime

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    key: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    level: int = 0
    permissions: List[str] = []


class RoleUpdate(BaseModel):
    label: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    level: Optional[int] = None
    permissions: Optional[List[str]] = None


class MenuPermission(BaseModel):
    key: str
    label: str
    category: str = ""


# ── Platform Connector Schemas ─────────────────────

class PlatformInfo(BaseModel):
    """可用平台信息"""
    platform_type: str
    label: str
    icon: str
    help_text: str


class PlatformCredentialCheck(BaseModel):
    """平台凭据验证请求"""
    platform_type: str
    appid: str = ""
    secret_key: str = ""
    api_token: str = ""
    client_id: str = ""
    client_secret: str = ""
    domain: str = ""
    project_id: int = 0


class PlatformBotItem(BaseModel):
    """平台 Bot 信息"""
    bot_id: str
    name: str
    description: str = ""
    platform_type: str = ""


class PlatformImportRequest(BaseModel):
    """一键导入 Agent 请求"""
    platform_type: str
    # 凭据
    appid: str = ""
    secret_key: str = ""
    api_token: str = ""
    client_id: str = ""
    client_secret: str = ""
    domain: str = ""
    project_id: int = 0
    # Bot 信息
    bot_id: str = ""
    bot_name: str = ""
    # Agent 配置
    name: str = Field(..., min_length=1, max_length=255)
    visibility: str = Field(default="public", pattern="^(public|department|specific)$")
    permission_config: Optional[dict] = None
    config: dict = Field(default_factory=dict)

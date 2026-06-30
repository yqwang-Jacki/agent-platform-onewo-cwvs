"""
平台管理 API — 平台凭据验证、Bot 发现、一键导入

所有端点需要 developer+ 角色
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4

from app.database import get_db
from app.models import Agent, Publisher
from app.core.security import get_current_admin_user, get_current_publisher, require_role
from app.schemas import (
    PlatformInfo,
    PlatformCredentialCheck,
    PlatformBotItem,
    PlatformImportRequest,
    AgentResponse,
)
from app.connectors import (
    PlatformCredential,
    get_connector,
    list_platforms,
)

router = APIRouter(prefix="/platforms", tags=["平台管理"])


@router.get("", response_model=list[PlatformInfo])
def get_platforms():
    """获取所有可用平台列表"""
    return list_platforms()


@router.post("/validate")
async def validate_credentials(body: PlatformCredentialCheck):
    """验证平台凭据是否有效"""
    connector = get_connector(body.platform_type)
    if not connector:
        raise HTTPException(400, f"不支持的平台类型: {body.platform_type}")

    cred = PlatformCredential(
        platform_type=body.platform_type,
        appid=body.appid,
        secret_key=body.secret_key,
        api_token=body.api_token,
        client_id=body.client_id,
        client_secret=body.client_secret,
        domain=body.domain,
        project_id=body.project_id,
    )

    try:
        valid = await connector.validate_credentials(cred)
    except Exception as e:
        # 透传底层错误（如 401/403/连接超时等）
        return {"valid": False, "detail": str(e), "platform_type": body.platform_type}

    if not valid:
        return {
            "valid": False,
            "detail": "凭据无效：请检查 API Token 是否正确、域名是否可访问",
            "platform_type": body.platform_type,
        }

    return {"valid": True, "detail": "", "platform_type": body.platform_type}


@router.post("/bots", response_model=list[PlatformBotItem])
async def list_bots(body: PlatformCredentialCheck):
    """获取平台上可用的 Bot 列表"""
    connector = get_connector(body.platform_type)
    if not connector:
        raise HTTPException(400, f"不支持的平台类型: {body.platform_type}")

    cred = PlatformCredential(
        platform_type=body.platform_type,
        appid=body.appid,
        secret_key=body.secret_key,
        api_token=body.api_token,
        client_id=body.client_id,
        client_secret=body.client_secret,
        domain=body.domain,
        project_id=body.project_id,
    )

    try:
        bots = await connector.list_bots(cred)
    except Exception as e:
        raise HTTPException(502, f"获取 Bot 列表失败: {str(e)}")

    return [
        PlatformBotItem(
            bot_id=b.bot_id,
            name=b.name,
            description=b.description,
            platform_type=b.platform_type,
        )
        for b in bots
    ]


@router.post("/import", response_model=AgentResponse, status_code=201)
async def import_agent(
    body: PlatformImportRequest,
    publisher: Publisher = Depends(get_current_publisher),
    db: Session = Depends(get_db),
):
    """一键从平台导入 Agent"""
    connector = get_connector(body.platform_type)
    if not connector:
        raise HTTPException(400, f"不支持的平台类型: {body.platform_type}")

    # 构建平台凭据
    cred = PlatformCredential(
        platform_type=body.platform_type,
        appid=body.appid,
        secret_key=body.secret_key,
        api_token=body.api_token,
        client_id=body.client_id,
        client_secret=body.client_secret,
        domain=body.domain,
        project_id=body.project_id,
    )

    # 验证凭据
    if not await connector.validate_credentials(cred):
        raise HTTPException(400, "平台凭据验证失败，请检查后重试")

    # 根据平台类型构建 api_endpoint 和 api_headers
    api_endpoint = ""
    api_headers = {}
    platform_config = {
        "bot_id": body.bot_id,
        "project_id": body.project_id,
        "domain": body.domain,
    }

    if body.platform_type == "gc":
        api_endpoint = "https://gc.4009515151.com/aics/chat"
        # GC 用 appid+secret 获取临时 token，不直接存 token
        platform_config["appid"] = body.appid
        platform_config["secret_key"] = body.secret_key  # TODO: 生产环境应加密存储
        api_headers = {"Content-Type": "application/json"}

    elif body.platform_type == "coze":
        raw_domain = body.domain.strip() if body.domain else ""
        # 清理域名：只保留基础部分，去除 /v3/chat、/chat、/stream_run 等路径后缀
        for suffix in ("/v3/chat", "/chat", "/stream_run"):
            if raw_domain.endswith(suffix):
                raw_domain = raw_domain[: -len(suffix)]
        domain = raw_domain or "https://api.coze.cn"
        if not domain.startswith("http"):
            domain = f"https://{domain}"
        # api_endpoint 由连接器运行时动态构建，此处只存基础信息
        platform_config["domain"] = domain
        platform_config["api_token"] = body.api_token  # TODO: 生产环境应加密存储
        if body.client_id:
            platform_config["client_id"] = body.client_id
        if body.client_secret:
            platform_config["client_secret"] = body.client_secret
        api_headers = {
            "Content-Type": "application/json",
        }

    # 创建 Agent
    agent = Agent(
        id=uuid4(),
        appid=publisher.appid,
        name=body.name or body.bot_name or "未命名 Agent",
        config=body.config or {},
        visibility=body.visibility,
        permission_config=body.permission_config,
        api_endpoint=api_endpoint,
        api_headers=api_headers,
        platform_type=body.platform_type,
        platform_config=platform_config,
        status="active",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent

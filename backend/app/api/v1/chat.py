from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import uuid4, UUID
from datetime import datetime, timezone
import json
import httpx
import asyncio

from app.database import get_db
from app.config import settings
from app.models import Agent, ShareLink, User, Conversation, Message, TokenUsageRecord
from app.schemas import AgentPublicInfo, MessageCreate, MessageResponse, ConversationResponse, ConversationSummary, AgentListItem, ConversationMessageCreate
from app.core import security
from app.connectors import get_connector, PlatformCredential, CustomConnector

router = APIRouter()


async def _call_agent_api(agent: Agent, history: list[dict], stream: bool, conv_id: str = "") -> tuple[str, int]:
    """调用 Agent API (支持连接器路由 和 自定义协议直连)

    conv_id: 会话 ID — 平台连接器用于维持对话上下文 (COZE: session_id, GC: userId)
    """
    pt = getattr(agent, "platform_type", "custom") or "custom"

    # 自定义协议 — 走原有 httpx 直连 (用线程池避免阻塞事件循环)
    if pt == "custom":
        if not agent.api_endpoint:
            raise HTTPException(400, "该 Agent 尚未配置 API 地址")

        def _sync_call():
            resp = httpx.post(
                agent.api_endpoint,
                json={"messages": history, "stream": stream},
                headers=agent.api_headers or {},
                timeout=settings.AGENT_PROXY_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()

        try:
            agent_data = await asyncio.to_thread(_sync_call)
            return agent_data.get("content", ""), agent_data.get("tokens_used", 0)
        except Exception as e:
            raise HTTPException(502, f"Agent API 调用失败: {e}")

    # 平台连接器路由
    connector = get_connector(pt)
    if not connector:
        raise HTTPException(400, f"不支持的平台类型: {pt}")

    pc = getattr(agent, "platform_config", {}) or {}
    # 注入 conv_id 到 bot_config，连接器用此保持对话连续性
    bot_config = {**pc, "conv_id": conv_id}

    cred = PlatformCredential(
        platform_type=pt,
        appid=pc.get("appid", ""),
        secret_key=pc.get("secret_key", ""),
        api_token=pc.get("api_token", ""),
        domain=pc.get("domain", ""),
        project_id=pc.get("project_id", 0),
    )

    try:
        result = await connector.chat(cred, bot_config, history, stream=False)
        return result.content, result.tokens_used
    except Exception as e:
        raise HTTPException(502, f"平台 [{pt}] API 调用失败: {e}")


async def _call_agent_api_stream(agent: Agent, history: list[dict], conv_id: str = ""):
    """流式调用 Agent API (仅平台连接器支持真流式)"""
    pt = getattr(agent, "platform_type", "custom") or "custom"

    # 自定义协议 — 模拟流式
    if pt == "custom":
        content, _ = await _call_agent_api(agent, history, stream=False)
        for chunk in content:
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"
        return

    connector = get_connector(pt)
    if not connector:
        yield f"data: {json.dumps({'error': 'Unsupported platform'})}\n\n"
        return

    pc = getattr(agent, "platform_config", {}) or {}
    bot_config = {**pc, "conv_id": conv_id}

    cred = PlatformCredential(
        platform_type=pt,
        appid=pc.get("appid", ""),
        secret_key=pc.get("secret_key", ""),
        api_token=pc.get("api_token", ""),
        domain=pc.get("domain", ""),
        project_id=pc.get("project_id", 0),
    )

    try:
        async for chunk in connector.chat_stream(cred, bot_config, history):
            if chunk == "[DONE]":
                yield "data: [DONE]\n\n"
            else:
                yield f"data: {json.dumps({'content': chunk})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


def _get_agent_by_link(link_code: str, db: Session) -> Agent:
    link = db.query(ShareLink).filter(
        ShareLink.link_code == link_code,
        ShareLink.status == "active",
    ).first()
    if not link:
        raise HTTPException(404, "分享链接不存在或已失效")
    if link.expire_at and link.expire_at.replace(tzinfo=None) < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(410, "分享链接已过期")
    agent = db.query(Agent).filter(Agent.id == link.agent_id).first()
    if not agent or agent.status != "active":
        raise HTTPException(404, "Agent 不存在或已下线")
    return agent


def _check_permission(agent: Agent, user: User) -> None:
    if agent.visibility == "public":
        return
    if agent.visibility == "department":
        depts = (agent.permission_config or {}).get("departments", [])
        if user.department not in depts:
            raise HTTPException(403, "您没有访问该 Agent 的权限")
        return
    if agent.visibility == "specific":
        user_ids = (agent.permission_config or {}).get("user_ids", [])
        if str(user.id) not in user_ids:
            raise HTTPException(403, "您没有访问该 Agent 的权限")
        return


def _get_or_create_conversation(agent_id: UUID, user_id: UUID, db: Session) -> Conversation:
    conv = db.query(Conversation).filter(
        Conversation.agent_id == agent_id,
        Conversation.user_id == user_id,
    ).first()
    if not conv:
        conv = Conversation(id=uuid4(), agent_id=agent_id, user_id=user_id)
        db.add(conv)
        db.commit()
        db.refresh(conv)
    else:
        conv.last_active_at = datetime.now(timezone.utc)
        db.commit()
    return conv


@router.get("/agents", response_model=list[AgentListItem])
def list_accessible_agents(
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """返回当前用户可以访问的所有 Agent（根据 visibility + permission）"""
    all_agents = db.query(Agent).filter(Agent.status == "active").all()
    accessible = []
    for agent in all_agents:
        if agent.visibility == "public":
            accessible.append(agent)
        elif agent.visibility == "department":
            depts = (agent.permission_config or {}).get("departments", [])
            if current_user.department in depts:
                accessible.append(agent)
        elif agent.visibility == "specific":
            user_ids = (agent.permission_config or {}).get("user_ids", [])
            if str(current_user.id) in user_ids:
                accessible.append(agent)
    return [AgentListItem(id=UUID(a.id), name=a.name, visibility=a.visibility) for a in accessible]


@router.post("/agents/{agent_id}/conversations", response_model=ConversationResponse, status_code=201)
def create_conversation(
    agent_id: str,
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """为一个 Agent 创建新会话（如果已有则返回已有）"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.status != "active":
        raise HTTPException(404, "Agent 不存在或已下线")

    # Check permission
    if agent.visibility == "department":
        depts = (agent.permission_config or {}).get("departments", [])
        if current_user.department not in depts:
            raise HTTPException(403, "无权限")
    elif agent.visibility == "specific":
        user_ids = (agent.permission_config or {}).get("user_ids", [])
        if str(current_user.id) not in user_ids:
            raise HTTPException(403, "无权限")

    existing = db.query(Conversation).filter(
        Conversation.agent_id == agent_id,
        Conversation.user_id == current_user.id,
    ).first()
    if existing:
        return _conv_to_response(existing, agent.name)

    conv = Conversation(id=uuid4(), agent_id=agent_id, user_id=current_user.id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _conv_to_response(conv, agent.name)


def _conv_to_response(conv, agent_name: str) -> ConversationResponse:
    return ConversationResponse(
        id=UUID(conv.id),
        agent_id=UUID(conv.agent_id),
        agent_name=agent_name,
        created_at=conv.created_at,
        last_active_at=conv.last_active_at,
        messages=[],
    )


@router.get("/agent/{link_code}", response_model=AgentPublicInfo)
def get_agent_info(
    link_code: str,
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    agent = _get_agent_by_link(link_code, db)
    _check_permission(agent, current_user)
    return agent


@router.post("/agent/{link_code}/messages")
async def send_message(
    link_code: str,
    body: MessageCreate,
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    agent = _get_agent_by_link(link_code, db)
    _check_permission(agent, current_user)
    conv = _get_or_create_conversation(agent.id, current_user.id, db)

    # 1. 保存用户消息
    user_msg = Message(
        id=uuid4(),
        conv_id=conv.id,
        role="user",
        content=body.content,
        tokens_used=0,
    )
    db.add(user_msg)
    db.commit()

    # 拉取历史消息作为上下文
    history_rows = (
        db.query(Message)
        .filter(Message.conv_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    # 2. 调用 Agent API (连接器路由)
    # 5. 返回（如 stream=True 则用 SSE）
    if body.stream:
        return StreamingResponse(
            _call_agent_api_stream(agent, history, str(conv.id)),
            media_type="text/event-stream",
        )

    assistant_content, tokens_used = await _call_agent_api(agent, history, stream=False, conv_id=str(conv.id))

    # 3. 保存 assistant 消息
    asst_msg = Message(
        id=uuid4(),
        conv_id=conv.id,
        role="assistant",
        content=assistant_content,
        tokens_used=tokens_used,
    )
    db.add(asst_msg)

    # 4. 更新 token 用量
    today = datetime.now(timezone.utc).date()
    usage = db.query(TokenUsageRecord).filter(
        TokenUsageRecord.agent_id == agent.id,
        TokenUsageRecord.user_id == current_user.id,
        func.date(TokenUsageRecord.usage_date) == today,
    ).first()
    if usage:
        usage.total_tokens += tokens_used
        usage.request_count += 1
    else:
        usage = TokenUsageRecord(
            id=uuid4(),
            appid=agent.appid,
            agent_id=agent.id,
            user_id=current_user.id,
            usage_date=today,
            total_tokens=tokens_used,
            request_count=1,
        )
        db.add(usage)

    db.commit()
    db.refresh(asst_msg)

    return MessageResponse(
        id=asst_msg.id,
        role="assistant",
        content=assistant_content,
        tokens_used=tokens_used,
        created_at=asst_msg.created_at,
    )


def _sse_stream(content: str):
    for chunk in content:
        yield f"data: {json.dumps({'content': chunk})}\n\n"
    yield "data: [DONE]\n\n"


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.last_active_at.desc())
        .all()
    )
    result = []
    for c in convs:
        agent = db.query(Agent).filter(Agent.id == c.agent_id).first()
        agent_name = agent.name if agent else "未知"
        msg_count = db.query(Message).filter(Message.conv_id == c.id).count()
        last_msg = db.query(Message).filter(Message.conv_id == c.id).order_by(Message.created_at.desc()).first()
        result.append(ConversationSummary(
            id=UUID(c.id),
            agent_id=UUID(c.agent_id),
            agent_name=agent_name,
            created_at=c.created_at,
            last_active_at=c.last_active_at,
            message_count=msg_count,
            last_message=last_msg.content[:100] if last_msg else "",
        ))
    return result


@router.get("/conversations/{conv_id}", response_model=ConversationResponse)
def get_conversation(
    conv_id: str,
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(404, "会话不存在")
    if conv.user_id != current_user.id:
        raise HTTPException(403, "无权访问此会话")
    agent = db.query(Agent).filter(Agent.id == conv.agent_id).first()
    msgs = (
        db.query(Message)
        .filter(Message.conv_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return ConversationResponse(
        id=UUID(conv.id),
        agent_id=UUID(conv.agent_id),
        agent_name=agent.name if agent else "未知",
        created_at=conv.created_at,
        last_active_at=conv.last_active_at,
        messages=[
            MessageResponse(
                id=UUID(m.id),
                role=m.role,
                content=m.content,
                tokens_used=m.tokens_used or 0,
                created_at=m.created_at,
            ) for m in msgs
        ],
    )


@router.post("/conversations/{conv_id}/messages")
async def send_message_to_conv(
    conv_id: str,
    body: ConversationMessageCreate,
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """直接向已有会话发送消息"""
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(404, "会话不存在")
    if conv.user_id != current_user.id:
        raise HTTPException(403, "无权访问此会话")

    agent = db.query(Agent).filter(Agent.id == conv.agent_id).first()
    if not agent or agent.status != "active":
        raise HTTPException(404, "Agent 不存在或已下线")

    # 保存用户消息
    user_msg = Message(id=uuid4(), conv_id=conv.id, role="user", content=body.content, tokens_used=0)
    db.add(user_msg)
    db.commit()

    # 拉取历史并调用 Agent API
    history_rows = db.query(Message).filter(Message.conv_id == conv.id).order_by(Message.created_at.asc()).all()
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    assistant_content, tokens_used = await _call_agent_api(agent, history, stream=False, conv_id=conv_id)

    asst_msg = Message(
        id=uuid4(), conv_id=conv.id, role="assistant",
        content=assistant_content, tokens_used=tokens_used,
    )
    db.add(asst_msg)

    today = datetime.now(timezone.utc).date()
    usage = db.query(TokenUsageRecord).filter(
        TokenUsageRecord.agent_id == agent.id,
        TokenUsageRecord.user_id == current_user.id,
        func.date(TokenUsageRecord.usage_date) == today,
    ).first()
    if usage:
        usage.total_tokens += tokens_used
        usage.request_count += 1
    else:
        usage = TokenUsageRecord(
            id=uuid4(), appid=agent.appid, agent_id=agent.id,
            user_id=current_user.id, usage_date=today,
            total_tokens=tokens_used, request_count=1,
        )
        db.add(usage)

    conv.last_active_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(asst_msg)

    return MessageResponse(
        id=UUID(asst_msg.id), role="assistant", content=assistant_content,
        tokens_used=tokens_used, created_at=asst_msg.created_at,
    )


@router.get("/agent/{agent_id}/share-link")
def get_agent_share_link(
    agent_id: str,
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """获取或自动创建 Agent 的分享链接"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.status != "active":
        raise HTTPException(404, "Agent 不存在或已下线")

    _check_permission(agent, current_user)

    link = db.query(ShareLink).filter(
        ShareLink.agent_id == agent_id,
        ShareLink.status == "active",
    ).first()

    if not link:
        link_code = datetime.now(timezone.utc).strftime("%Y%m%d") + _rand_str(8)
        link = ShareLink(id=uuid4(), agent_id=agent_id, link_code=link_code, status="active")
        db.add(link)
        db.commit()
        db.refresh(link)

    return {"link_code": link.link_code, "agent_name": agent.name}


def _rand_str(n: int) -> str:
    import secrets
    return secrets.token_hex(n)[:n]

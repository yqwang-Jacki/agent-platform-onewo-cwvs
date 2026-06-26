from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import uuid4, UUID
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.config import settings
from app.models import Agent, ShareLink, Publisher, TokenUsageRecord
from app.schemas import AgentCreate, AgentUpdate, AgentResponse, ShareLinkCreate, ShareLinkResponse
from app.core import security

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


def _get_publisher(
    appid: Optional[str] = Query(None),
    secretkey: Optional[str] = Query(None),
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Publisher:
    if creds:
        return security.get_current_publisher(creds, db)
    if appid and secretkey:
        return security.verify_publisher_key(appid, secretkey, db)
    raise HTTPException(status_code=401, detail="缺少发布者认证信息")


def _get_agent_or_404(agent_id: str, db: Session) -> Agent:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent 不存在")
    return agent


@router.post("", response_model=AgentResponse, status_code=201)
def create_agent(
    body: AgentCreate,
    publisher: Publisher = Depends(_get_publisher),
    db: Session = Depends(get_db),
):
    agent = Agent(
        id=uuid4(),
        appid=publisher.appid,
        name=body.name,
        config=body.config,
        visibility=body.visibility,
        permission_config=body.permission_config,
        api_endpoint=body.api_endpoint,
        api_headers=body.api_headers,
        platform_type=getattr(body, "platform_type", "custom") or "custom",
        platform_config=getattr(body, "platform_config", {}) or {},
        status="active",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("", response_model=list[AgentResponse])
def list_agents(
    publisher: Publisher = Depends(_get_publisher),
    db: Session = Depends(get_db),
):
    return (
        db.query(Agent)
        .filter(Agent.appid == publisher.appid)
        .order_by(Agent.created_at.desc())
        .all()
    )


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str,
    body: AgentUpdate,
    publisher: Publisher = Depends(_get_publisher),
    db: Session = Depends(get_db),
):
    agent = _get_agent_or_404(agent_id, db)
    if agent.appid != publisher.appid:
        raise HTTPException(403, "无权操作此 Agent")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=204)
def delete_agent(
    agent_id: str,
    publisher: Publisher = Depends(_get_publisher),
    db: Session = Depends(get_db),
):
    agent = _get_agent_or_404(agent_id, db)
    if agent.appid != publisher.appid:
        raise HTTPException(403, "无权操作此 Agent")
    agent.status = "deleted"
    db.commit()


@router.post("/{agent_id}/links", response_model=ShareLinkResponse, status_code=201)
def create_link(
    agent_id: str,
    body: ShareLinkCreate,
    publisher: Publisher = Depends(_get_publisher),
    db: Session = Depends(get_db),
):
    agent = _get_agent_or_404(agent_id, db)
    if agent.appid != publisher.appid:
        raise HTTPException(403, "无权操作此 Agent")

    link_code = datetime.now(timezone.utc).strftime("%Y%m%d") + _rand_str(8)
    expire_at = None
    if body.expire_days:
        expire_at = datetime.now(timezone.utc) + timedelta(days=body.expire_days)

    link = ShareLink(
        id=uuid4(),
        agent_id=agent.id,
        link_code=link_code,
        status="active",
        expire_at=expire_at,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return _build_link_response(link, agent.id)


@router.get("/{agent_id}/links", response_model=list[ShareLinkResponse])
def list_links(
    agent_id: str,
    publisher: Publisher = Depends(_get_publisher),
    db: Session = Depends(get_db),
):
    agent = _get_agent_or_404(agent_id, db)
    if agent.appid != publisher.appid:
        raise HTTPException(403, "无权操作此 Agent")
    links = db.query(ShareLink).filter(ShareLink.agent_id == agent.id).all()
    return [_build_link_response(l, agent.id) for l in links]


@router.delete("/links/{link_id}", status_code=204)
def revoke_link(
    link_id: str,
    publisher: Publisher = Depends(_get_publisher),
    db: Session = Depends(get_db),
):
    link = db.query(ShareLink).filter(ShareLink.id == link_id).first()
    if not link:
        raise HTTPException(404, "链接不存在")
    agent = db.query(Agent).filter(Agent.id == link.agent_id).first()
    if agent.appid != publisher.appid:
        raise HTTPException(403, "无权操作此链接")
    link.status = "revoked"
    db.commit()


@router.get("/stats/tokens")
def token_stats(
    publisher: Publisher = Depends(_get_publisher),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            TokenUsageRecord.agent_id,
            func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
            func.sum(TokenUsageRecord.request_count).label("total_requests"),
        )
        .filter(TokenUsageRecord.appid == publisher.appid)
        .group_by(TokenUsageRecord.agent_id)
        .all()
    )
    return [
        {"agent_id": str(r.agent_id), "total_tokens": r.total_tokens, "total_requests": r.total_requests}
        for r in rows
    ]


def _rand_str(n: int) -> str:
    import secrets
    return secrets.token_hex(n)[:n]


def _build_link_response(link: ShareLink, agent_id: UUID) -> ShareLinkResponse:
    return ShareLinkResponse(
        id=link.id,
        link_code=link.link_code,
        status=link.status,
        expire_at=link.expire_at,
        created_at=link.created_at,
        share_url=f"{settings.SHARE_BASE_URL.rstrip('/')}/c/{link.link_code}" if settings.SHARE_BASE_URL else f"http://localhost:3001/c/{link.link_code}",
    )

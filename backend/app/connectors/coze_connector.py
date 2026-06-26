"""
Coze 平台连接器 — 字节跳动 Coze AI Bot 平台
─────────────────────────────────────
实测验证 ✅ 2026-06-26  (Bot: 莫比乌斯考官)

部署类型: API 部署 (自有域名)
  URL:  https://6dzhzw2vvm.coze.site/stream_run
  Auth: Bearer {API Token} (永久有效)
  会话: session_id 保持上下文 ✅

SSE 事件流 (实测格式):
  event: message
  data: {"type":"message_start","session_id":"...","reply_id":"...","msg_id":"...","sequence_id":1}
  event: message
  data: {"type":"answer","content":{"answer":"文本片段"},"sequence_id":N}
  ...
  event: message
  data: {"type":"message_end","content":{"message_end":{"token_cost":{"total_tokens":0}}}}

请求格式:
  {
    "content": {"query": {"prompt": [{"type":"text","content":{"text":"..."}}]}},
    "type": "query",
    "session_id": "...",
    "project_id": 0   // 可选, 0 表示不传
  }
"""
import httpx
import json
import uuid
from typing import AsyncIterator
from app.connectors import BaseConnector, PlatformCredential, BotInfo, ConnectorChatResult, register_connector
from app.config import settings


class CozeConnector(BaseConnector):
    """Coze 平台连接器"""

    platform_type = "coze"
    platform_label = "Coze AI 平台"
    platform_icon = "🤖"
    help_text = "字节 Coze 平台 — 输入 API Token 和部署域名自动导入 Bot"

    def _build_headers(self, cred: PlatformCredential) -> dict:
        return {
            "Authorization": f"Bearer {cred.api_token}",
            "Content-Type": "application/json",
        }

    def _get_stream_url(self, cred: PlatformCredential, bot_config: dict = None) -> str:
        """获取 stream_run 完整 URL

        用户可能输入:
          - 完整 URL: https://xxx.coze.site/stream_run
          - 仅域名:   6dzhzw2vvm.coze.site 或 api.coze.cn
          - bot_id:   6dzhzw2vvm (自动补全为 .coze.site)
          - 空:       默认 api.coze.cn
        """
        domain = cred.domain

        # domain 为空时, 尝试从 bot_config.bot_id 构造
        if not domain and bot_config:
            bot_id = bot_config.get("bot_id", "")
            if bot_id:
                # bot_id 不含 . 则假定为 coze.site 子域名
                if "." not in bot_id and "/" not in bot_id:
                    domain = f"{bot_id}.coze.site"
                else:
                    domain = bot_id

        if not domain:
            domain = "api.coze.cn"

        if not domain.startswith("http"):
            domain = f"https://{domain}"

        # 如果已经是完整 stream_run URL, 直接返回
        if domain.endswith("/stream_run"):
            return domain
        return f"{domain.rstrip('/')}/stream_run"

    def _build_payload(self, cred: PlatformCredential, bot_config: dict, messages: list[dict], session_id: str = "") -> dict:
        """将标准 [{role, content}] 格式转为 COZE 格式

        Coze 通过 session_id 维持上下文，prompt 只需发送最新用户消息。
        """
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m["content"]
                break

        # 优先使用 conv_id 作为稳定的 session_id (多轮对话上下文关键!)
        # 其次用 bot_config 中持久化的 session_id, 最后才随机生成
        conv_id = bot_config.get("conv_id", "")
        if not session_id:
            session_id = conv_id or bot_config.get("session_id", "")

        # 如果仍然没有 session_id, 用随机值 (首次对话)
        if not session_id:
            session_id = f"coze_{uuid.uuid4().hex[:12]}"

        payload = {
            "content": {
                "query": {
                    "prompt": [
                        {"type": "text", "content": {"text": last_user_msg}}
                    ]
                }
            },
            "type": "query",
            "session_id": session_id,
        }

        # project_id 可选 (实测不带也能正常工作)
        prj_id = bot_config.get("project_id") or cred.project_id
        if prj_id:
            payload["project_id"] = prj_id

        return payload

    async def validate_credentials(self, cred: PlatformCredential) -> bool:
        """通过调用 stream_run 验证凭据 — 200=OK, 401/403=令牌无效"""
        try:
            stream_url = self._get_stream_url(cred)
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    stream_url,
                    json={
                        "content": {
                            "query": {
                                "prompt": [{"type": "text", "content": {"text": "ping"}}]
                            }
                        },
                        "type": "query",
                        "session_id": "cred_validation",
                    },
                    headers=self._build_headers(cred),
                )
                if resp.status_code in (401, 403):
                    return False
                return resp.status_code < 500
        except Exception:
            return False

    async def list_bots(self, cred: PlatformCredential) -> list[BotInfo]:
        """Coze API 部署模式不支持列出 Bot — 返回域名作为 Bot 标识"""
        domain = cred.domain or "api.coze.cn"
        bot_name = domain.replace("https://", "").replace("http://", "").split(".")[0]

        return [
            BotInfo(
                bot_id=domain,
                name=f"Coze Bot: {bot_name}",
                description=f"已部署在 {domain} 的 Coze Bot。输入 API Token 和部署域名后即可使用。",
                platform_type="coze",
                extra={"stream_url": self._get_stream_url(cred)},
            )
        ]

    async def chat(
        self,
        cred: PlatformCredential,
        bot_config: dict,
        messages: list[dict],
        stream: bool = False,
    ) -> ConnectorChatResult:
        """非流式对话 — 调用 stream_run 并收集所有 answer 片段"""
        stream_url = self._get_stream_url(cred, bot_config)
        payload = self._build_payload(cred, bot_config, messages)

        full_answer = ""
        tokens_used = 0
        error_msg = ""

        async with httpx.AsyncClient(timeout=settings.AGENT_PROXY_TIMEOUT) as client:
            async with client.stream(
                "POST", stream_url, json=payload, headers=self._build_headers(cred)
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if not data_str:
                        continue
                    try:
                        event = json.loads(data_str)
                        event_type = event.get("type", "")

                        if event_type == "answer":
                            full_answer += event.get("content", {}).get("answer", "")

                        elif event_type == "message_end":
                            msg_end = event.get("content", {}).get("message_end", {})
                            token_cost = msg_end.get("token_cost", {})
                            tokens_used = token_cost.get("total_tokens", 0)

                        elif event_type == "error":
                            error_msg = event.get("content", {}).get("error", "Coze 平台错误")

                        # message_start — 忽略

                    except json.JSONDecodeError:
                        continue

        if error_msg and not full_answer:
            raise ValueError(f"Coze 对话失败: {error_msg}")

        return ConnectorChatResult(content=full_answer, tokens_used=tokens_used)

    async def chat_stream(
        self,
        cred: PlatformCredential,
        bot_config: dict,
        messages: list[dict],
    ) -> AsyncIterator[str]:
        """Coze SSE 流式对话 — 实时逐字返回 answer 片段"""
        stream_url = self._get_stream_url(cred, bot_config)
        payload = self._build_payload(cred, bot_config, messages)

        async with httpx.AsyncClient(timeout=settings.AGENT_PROXY_TIMEOUT) as client:
            async with client.stream(
                "POST", stream_url, json=payload, headers=self._build_headers(cred)
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if not data_str:
                        continue
                    try:
                        event = json.loads(data_str)
                        event_type = event.get("type", "")

                        if event_type == "answer":
                            answer = event.get("content", {}).get("answer", "")
                            if answer:
                                yield answer

                        elif event_type == "error":
                            error_msg = event.get("content", {}).get("error", "Coze 平台错误")
                            yield f"\n[错误: {error_msg}]"

                        # message_start, message_end — 忽略

                    except json.JSONDecodeError:
                        continue

        yield "[DONE]"


# 注册
register_connector(CozeConnector())

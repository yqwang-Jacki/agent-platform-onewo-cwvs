"""
Coze 平台连接器 — 字节跳动 Coze AI Bot 平台
─────────────────────────────────────
支持两种 API 格式:

  1. 旧版 coze.site (stream_run)
     ── 实测验证 ✅ 2026-06-26  (Bot: 莫比乌斯考官)
     URL:  {bot_id}.coze.site/stream_run
     Auth: Bearer {API Token} (永久有效)
     请求: {"type":"query","session_id":"...","content":{...}}

  2. 新版 api.coze.cn (v3 chat)
     ── 支持 2026-06-30  (Bot: 万梁人事助手等新版 API 部署)
     URL:  https://api.coze.cn/v3/chat
     Auth: Bearer {PAT 或 OAuth Token}
     请求: {"bot_id":"...","user_id":"...","stream":bool, "additional_messages":[...]}

自动检测逻辑:
  - domain 含 "coze.site" 或不含 "api.coze" → 旧版 stream_run 模式
  - domain 含 "api.coze" → 新版 v3 chat 模式
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

    def _is_v3_api(self, domain: str) -> bool:
        """判断是否使用新版 v3 API (api.coze.cn / api.coze.com)

        判定规则:
          - domain 含 "api.coze" → v3 模式
          - domain 含 "coze.site" 或其他 → 旧版 stream_run 模式
        """
        if not domain:
            return False
        return "api.coze" in domain.lower()

    def _build_url(self, cred: PlatformCredential, bot_config: dict = None) -> tuple[str, str]:
        """构建完整 API URL 和模式标识

        Returns:
            (url, mode)  mode = "v3" | "stream_run"
        """
        domain = cred.domain

        # domain 为空时, 尝试从 bot_config.bot_id 构造
        if not domain and bot_config:
            bot_id = bot_config.get("bot_id", "")
            if bot_id:
                if "." not in bot_id and "/" not in bot_id:
                    domain = f"{bot_id}.coze.site"
                else:
                    domain = bot_id

        if not domain:
            # 默认使用新版 v3 API（2026 年推荐）
            domain = "api.coze.cn"

        if not domain.startswith("http"):
            domain = f"https://{domain}"

        # 检测 API 模式
        if self._is_v3_api(domain):
            # 新版: POST https://api.coze.cn/v3/chat
            base = domain.rstrip("/")
            # 如果用户误填了 /stream_run 后缀，去掉它
            if base.endswith("/stream_run"):
                base = base[: -len("/stream_run")]
            return f"{base}/v3/chat", "v3"

        # 旧版 coze.site stream_run
        if domain.endswith("/stream_run"):
            return domain, "stream_run"
        return f"{domain.rstrip('/')}/stream_run", "stream_run"

    def _build_payload(self, cred: PlatformCredential, bot_config: dict, messages: list[dict], session_id: str = "", mode: str = "stream_run") -> dict:
        """将标准 [{role, content}] 格式转为 Coze API 请求体

        mode="stream_run" → 旧版 coze.site 格式
        mode="v3"         → 新版 api.coze.cn/v3/chat 格式
        """
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m["content"]
                break

        # session_id 处理
        if not session_id:
            conv_id = bot_config.get("conv_id", "")
            session_id = conv_id or bot_config.get("session_id", "")
        if not session_id:
            session_id = f"coze_{uuid.uuid4().hex[:12]}"

        # ── 新版 v3 chat 格式 ──
        if mode == "v3":
            return {
                "bot_id": bot_config.get("bot_id", ""),
                "user_id": bot_config.get("user_id", f"user_{session_id}"),
                "stream": True,
                "auto_save_history": True,
                "additional_messages": [
                    {
                        "role": "user",
                        "content": last_user_msg,
                        "content_type": "text",
                    }
                ],
            }

        # ── 旧版 stream_run 格式 ──
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

        prj_id = bot_config.get("project_id") or cred.project_id
        if prj_id:
            payload["project_id"] = prj_id

        return payload

    async def validate_credentials(self, cred: PlatformCredential) -> bool:
        """验证凭据 — 旧版调 stream_run, 新版调 v3/chat"""
        try:
            url, mode = self._build_url(cred)
            async with httpx.AsyncClient(timeout=15) as client:
                if mode == "v3":
                    # 新版 v3: 需要 bot_id
                    resp = await client.post(
                        url,
                        json={
                            "bot_id": "",
                            "user_id": "validation",
                            "stream": False,
                            "additional_messages": [
                                {"role": "user", "content": "ping", "content_type": "text"}
                            ],
                        },
                        headers=self._build_headers(cred),
                    )
                else:
                    # 旧版 stream_run
                    resp = await client.post(
                        url,
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
        url, _ = self._build_url(cred)

        return [
            BotInfo(
                bot_id=domain,
                name=f"Coze Bot: {bot_name}",
                description=f"已部署在 {domain} 的 Coze Bot。",
                platform_type="coze",
                extra={"stream_url": url, "api_mode": "v3" if self._is_v3_api(domain) else "stream_run"},
            )
        ]

    async def chat(
        self,
        cred: PlatformCredential,
        bot_config: dict,
        messages: list[dict],
        stream: bool = False,
    ) -> ConnectorChatResult:
        """非流式对话 — 自动检测 v3 / stream_run 模式"""
        url, mode = self._build_url(cred, bot_config)
        payload = self._build_payload(cred, bot_config, messages, mode=mode)

        # v3 非流式: 设置 stream=False
        if mode == "v3":
            payload["stream"] = False

        full_answer = ""
        tokens_used = 0
        error_msg = ""

        async with httpx.AsyncClient(timeout=settings.AGENT_PROXY_TIMEOUT) as client:
            async with client.stream(
                "POST", url, json=payload, headers=self._build_headers(cred)
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    parsed = self._parse_sse_line(line, mode)
                    if not parsed:
                        continue

                    event_type, data = parsed

                    if mode == "v3":
                        # v3 SSE 格式: {"event":"conversation.message.delta","data":{"content":"..."}}
                        if event_type == "message.delta" or event_type == "conversation.message.delta":
                            content = (data.get("data") or data).get("content", "")
                            if content:
                                full_answer += content
                        elif event_type == "message.end" or event_type == "conversation.message.complete":
                            token_info = data.get("data", data) or {}
                            tokens_used = token_info.get("token_count", 0) or token_info.get("usage", {}).get("total_tokens", 0)
                        elif event_type in ("error", "conversation.message.error"):
                            error_msg = str(data.get("message", data.get("msg", "Coze v3 错误")))
                    else:
                        # 旧版 stream_run 格式
                        if event_type == "answer":
                            full_answer += data.get("content", {}).get("answer", "")
                        elif event_type == "message_end":
                            msg_end = data.get("content", {}).get("message_end", {})
                            token_cost = msg_end.get("token_cost", {})
                            tokens_used = token_cost.get("total_tokens", 0)
                        elif event_type == "error":
                            error_msg = data.get("content", {}).get("error", "Coze 平台错误")

        if error_msg and not full_answer:
            raise ValueError(f"Coze 对话失败: {error_msg}")

        return ConnectorChatResult(content=full_answer, tokens_used=tokens_used)

    def _parse_sse_line(self, line: str, mode: str) -> tuple[str, dict] | None:
        """解析一行 SSE 数据

        Returns:
            (event_type, data_dict) 或 None
        """
        if not line.startswith("data:"):
            return None
        data_str = line[5:].strip()
        if not data_str:
            return None
        try:
            event = json.loads(data_str)
        except json.JSONDecodeError:
            return None

        event_type = event.get("type", "") or event.get("event", "")

        # v3 的事件名在 .event 字段
        if mode == "v3" and not event_type:
            event_type = event.get("event", "")

        return event_type, event

    async def chat_stream(
        self,
        cred: PlatformCredential,
        bot_config: dict,
        messages: list[dict],
    ) -> AsyncIterator[str]:
        """Coze 流式对话 — 自动检测 v3 / stream_run 模式，实时逐字返回"""
        url, mode = self._build_url(cred, bot_config)
        payload = self._build_payload(cred, bot_config, messages, mode=mode)

        # v3 流式: 确保开启
        if mode == "v3":
            payload["stream"] = True

        async with httpx.AsyncClient(timeout=settings.AGENT_PROXY_TIMEOUT) as client:
            async with client.stream(
                "POST", url, json=payload, headers=self._build_headers(cred)
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    parsed = self._parse_sse_line(line, mode)
                    if not parsed:
                        continue

                    event_type, data = parsed

                    if mode == "v3":
                        if event_type in ("message.delta", "conversation.message.delta"):
                            delta_data = data.get("data", data)
                            content = delta_data.get("content", "")
                            if content:
                                yield content
                        elif event_type in ("error", "conversation.message.error"):
                            err_msg = data.get("message", data.get("msg", "Coze v3 错误"))
                            yield f"\n[错误: {err_msg}]"
                    else:
                        if event_type == "answer":
                            answer = data.get("content", {}).get("answer", "")
                            if answer:
                                yield answer
                        elif event_type == "error":
                            error_msg = data.get("content", {}).get("error", "Coze 平台错误")
                            yield f"\n[错误: {error_msg}]"

        yield "[DONE]"


# 注册
register_connector(CozeConnector())

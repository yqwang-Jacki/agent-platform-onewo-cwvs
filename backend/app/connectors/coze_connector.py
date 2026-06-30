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
    platform_label = "扣子（Coze）"
    platform_icon = "coze"
    help_text = "支持 PAT 或 OAuth 2.0：填入 API Token，或客户端 ID + 客户端密钥"

    def _use_oauth(self, cred: PlatformCredential) -> bool:
        """当同时提供 client_id 和 client_secret 时使用 OAuth 2.0"""
        return bool(cred.client_id and cred.client_secret)

    def _oauth_token_url(self, cred: PlatformCredential) -> str:
        """根据域名判断 OAuth token endpoint"""
        domain = (cred.domain or "").lower()
        if "api.coze.com" in domain:
            return "https://api.coze.com/api/permission/oauth2/token"
        return "https://api.coze.cn/api/permission/oauth2/token"

    async def _get_oauth_token(self, cred: PlatformCredential) -> str:
        """用 client_credentials 换取 access_token"""
        url = self._oauth_token_url(cred)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url,
                json={
                    "grant_type": "client_credentials",
                    "client_id": cred.client_id,
                    "client_secret": cred.client_secret,
                },
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            token = data.get("access_token", "")
            if not token:
                raise ValueError("Coze OAuth 响应中未包含 access_token")
            return token

    async def _build_headers(self, cred: PlatformCredential) -> dict:
        if self._use_oauth(cred):
            token = await self._get_oauth_token(cred)
        else:
            token = cred.api_token
            if not token:
                raise ValueError("缺少 Coze 凭据：请提供 API Token 或 Client ID + Client Secret")
        return {
            "Authorization": f"Bearer {token}",
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
            # 如果用户误填了 /v3/chat 或 /stream_run 后缀，去掉
            for suffix in ("/v3/chat", "/chat", "/stream_run"):
                if base.endswith(suffix):
                    base = base[: -len(suffix)]
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
                        "type": "question",
                    }
                ],
                "parameters": {},
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
        """验证凭据 — 通过调用 Coze 用户信息接口验证 Token 有效性

        新版 v3: 调 GET /v1/users/me (只需要 token, 不需要 bot_id)
        旧版 coze.site: 调 stream_run 接口测试 (bot_id 填空)
        """
        try:
            domain = (cred.domain or "").strip()
            if not domain.startswith("http"):
                domain = f"https://{domain}"
            headers = await self._build_headers(cred)

            if self._is_v3_api(domain):
                # 新版 v3: 调用 /v1/users/me 验证 Token，无需 bot_id
                base = domain.rstrip("/")
                for suffix in ("/v3/chat", "/chat"):
                    if base.endswith(suffix):
                        base = base[: -len(suffix)]
                verify_url = f"{base}/v1/users/me"
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(verify_url, headers=headers)
                    if resp.status_code in (401, 403):
                        return False
                    try:
                        body = resp.json()
                        code = body.get("code", 0)
                        # Coze 认证错误码: 4100=token无效, 4101=token过期, 4102=权限不足
                        if code in (4100, 4101, 4102):
                            msg = body.get("msg", "Token 无效")
                            raise ValueError(f"Coze 认证失败 (code={code}): {msg}")
                    except ValueError:
                        raise
                    except Exception:
                        pass
                    return resp.status_code < 500
            else:
                # 旧版 coze.site: stream_run 接口
                url, _ = self._build_url(cred)
                async with httpx.AsyncClient(timeout=15) as client:
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
                        headers=headers,
                    )
                    if resp.status_code in (401, 403):
                        return False
                    return resp.status_code < 500
        except ValueError:
            raise  # 透传详细错误给 platforms.py
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

        # v3 始终走流式模式收集结果（非流式需要轮询 chat 状态，更复杂）
        if mode == "v3":
            payload["stream"] = True

        full_answer = ""
        tokens_used = 0
        error_msg = ""

        current_event = ""
        headers = await self._build_headers(cred)
        async with httpx.AsyncClient(timeout=settings.AGENT_PROXY_TIMEOUT) as client:
            async with client.stream(
                "POST", url, json=payload, headers=headers
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    # v3: 先捕获 event: 行
                    if mode == "v3" and line.startswith("event:"):
                        current_event = line[6:].strip()
                        continue

                    parsed = self._parse_sse_line(line, mode, current_event)
                    if not parsed:
                        continue

                    event_type, data = parsed

                    if mode == "v3":
                        # 只有 conversation.message.delta 且 type=answer 才收集内容
                        if event_type == "conversation.message.delta" and data.get("type") == "answer":
                            content = data.get("content", "")
                            if content:
                                full_answer += content
                        elif event_type == "conversation.chat.completed":
                            usage = data.get("usage", {}) or {}
                            tokens_used = usage.get("token_count", 0) or usage.get("total_tokens", 0)
                        elif event_type in ("conversation.message.error", "error"):
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

    def _parse_sse_line(self, line: str, mode: str, sse_event: str = "") -> tuple[str, dict] | None:
        """解析一行 SSE data

        v3 模式：event 名来自 sse_event 参数（从 event: 行读取），
                 数据 JSON 中的 type 字段表示消息类型（answer/function_call/tool_response）

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

        if mode == "v3":
            # event 名来自 SSE event: 行，数据中的 type 是消息类型
            event_type = sse_event or event.get("event", "")
            return event_type, event

        # 旧版: 从 JSON 中取 type 或 event 字段
        event_type = event.get("type", "") or event.get("event", "")
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

        current_event = ""
        headers = await self._build_headers(cred)
        async with httpx.AsyncClient(timeout=settings.AGENT_PROXY_TIMEOUT) as client:
            async with client.stream(
                "POST", url, json=payload, headers=headers
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    # v3: 先捕获 event: 行
                    if mode == "v3" and line.startswith("event:"):
                        current_event = line[6:].strip()
                        continue

                    parsed = self._parse_sse_line(line, mode, current_event)
                    if not parsed:
                        continue

                    event_type, data = parsed

                    if mode == "v3":
                        # 只输出 type=answer 的 delta 增量
                        if event_type == "conversation.message.delta" and data.get("type") == "answer":
                            content = data.get("content", "")
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

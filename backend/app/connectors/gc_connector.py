"""
GC 平台连接器 — 公司内部 GC 客服 AI 平台
─────────────────────────────────────
按 GC 官方文档实现: https://gc.4009515151.com/aics-gitbook/

认证:  getToken(appid+secretKey) → header: Authorization: {token}  (无 Bearer 前缀!)
对话:  sendMessage (非流式) / connect/subscribe (SSE 流式)
Bot发现: promptWord?botId={appid}
"""
import httpx
import json
import uuid
import logging
from typing import AsyncIterator
from app.connectors import BaseConnector, PlatformCredential, BotInfo, ConnectorChatResult, register_connector
from app.config import settings

logger = logging.getLogger(__name__)

GC_BASE_URL = "https://gc.4009515151.com"


class GCConnector(BaseConnector):
    """GC 平台连接器"""

    platform_type = "gc"
    platform_label = "GC平台"
    platform_icon = "gc"
    help_text = "输入 AppID 和 SecretKey，自动导入智能客服 Bot"

    def _headers(self, token: str) -> dict:
        """GC 文档要求 token 直接放在 Authorization，不加 Bearer 前缀"""
        return {"Authorization": token, "Content-Type": "application/json"}

    async def _get_token(self, cred: PlatformCredential) -> str:
        """获取 GC 平台 access token (有效期 2 小时)"""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GC_BASE_URL}/aics/auth/getToken",
                json={"appid": cred.appid, "secretKey": cred.secret_key},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                raise ValueError(
                    f"GC 认证失败(errorCode={data.get('errorCode')}): {data.get('errorMsg', '未知错误')}"
                )
            return data["data"]["token"]

    # ── 凭据验证 ──

    async def validate_credentials(self, cred: PlatformCredential) -> bool:
        try:
            await self._get_token(cred)
            return True
        except Exception:
            return False

    # ── Bot 发现 ──

    async def list_bots(self, cred: PlatformCredential) -> list[BotInfo]:
        """获取 GC 平台 Bot 信息 — botId 即 appid, 通过 promptWord 获取名称"""
        try:
            token = await self._get_token(cred)
            bot_id = cred.appid

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{GC_BASE_URL}/aics/message/promptWord?botId={bot_id}",
                    headers=self._headers(token),
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("success"):
                    info = data.get("data", {})
                    return [
                        BotInfo(
                            bot_id=bot_id,
                            name=info.get("name", "GC 智能客服"),
                            description=info.get(
                                "messagePrompt", f"GC Bot (appid={bot_id[:12]}...)"
                            ),
                            avatar_url=info.get("avatarUrl", ""),
                            platform_type="gc",
                            extra={
                                "messageId": info.get("messageId", ""),
                                "messagePrompt": info.get("messagePrompt", ""),
                            },
                        )
                    ]
                else:
                    logger.warning(f"GC promptWord 失败: {data.get('errorMsg')}")
        except Exception as e:
            logger.warning(f"GC list_bots 异常: {e}")

        # 失败时返回 appid 作为占位 Bot
        return [
            BotInfo(
                bot_id=cred.appid,
                name=f"GC Bot ({cred.appid[:12]}...)",
                description="请输入 botId (即 AppID) 以导入",
                platform_type="gc",
            )
        ]

    # ── 非流式对话 ──

    async def chat(
        self,
        cred: PlatformCredential,
        bot_config: dict,
        messages: list[dict],
        stream: bool = False,
    ) -> ConnectorChatResult:
        token = await self._get_token(cred)
        bot_id = bot_config.get("bot_id", cred.appid)

        # 用 conv_id 生成稳定的 user_id (多轮对话上下文关键!)
        conv_id = bot_config.get("conv_id", "")
        if conv_id:
            user_id = f"wb_{conv_id[:20]}"
        else:
            user_id = bot_config.get("user_id", f"wb_user_{uuid.uuid4().hex[:8]}")

        # message_id 每次生成新值 (GC 用其做消息去重)
        message_id = f"wb_msg_{uuid.uuid4().hex[:12]}"

        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m["content"]
                break

        async with httpx.AsyncClient(timeout=settings.AGENT_PROXY_TIMEOUT) as client:
            resp = await client.post(
                f"{GC_BASE_URL}/aics/message/sendMessage",
                json={
                    "botId": bot_id,
                    "userId": user_id,
                    "content": last_user_msg,
                    "messageId": message_id,
                },
                headers=self._headers(token),
            )
            resp.raise_for_status()
            data = resp.json()

        if not data.get("success"):
            error_code = data.get("errorCode", 0)
            error_msg = data.get("errorMsg", "未知错误")
            raise ValueError(f"GC 对话失败 (errorCode={error_code}): {error_msg}")

        inner = data.get("data", {})
        content = str(inner.get("responseContent", ""))
        tokens_used = inner.get("inputTokens", 0) + inner.get("outputTokens", 0)

        return ConnectorChatResult(
            content=content,
            tokens_used=tokens_used,
            extra={
                "gc_message_id": inner.get("id", ""),
                "gc_response_type": inner.get("responseType", "text"),
                "user_id": user_id,
                "message_id": message_id,
            },
        )

    # ── 流式对话 (SSE) ──

    async def chat_stream(
        self,
        cred: PlatformCredential,
        bot_config: dict,
        messages: list[dict],
    ) -> AsyncIterator[str]:
        """
        GC 流式 SSE 格式 (实测 2026-06-26):
          event:connect
          data:{numeric_msg_id}                    ← 连接 ID, 跳过
          :comment
          data:{"success":true,"data":{"responseContent":"第1字",...}}  ← 逐字累加
          data:{"success":true,"data":{"responseContent":"第2字",...}}
          ...
          data:{"success":true,"data":{"responseContent":"",...}}       ← 结束标记
          event:close
          id:{numeric_msg_id}
          data:{numeric_msg_id}

        注意: responseContent 是**增量**的 (每个 chunk 只包含新增文本片段),
        不是累积的。直接拼接所有非空 responseContent 即可得到完整回复。
        """
        token = await self._get_token(cred)
        bot_id = bot_config.get("bot_id", cred.appid)

        # 用 conv_id 生成稳定的 user_id (多轮对话上下文关键!)
        conv_id = bot_config.get("conv_id", "")
        if conv_id:
            user_id = f"wb_{conv_id[:20]}"
        else:
            user_id = bot_config.get("user_id", f"wb_user_{uuid.uuid4().hex[:8]}")

        message_id = f"wb_msg_{uuid.uuid4().hex[:12]}"

        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m["content"]
                break

        async with httpx.AsyncClient(timeout=settings.AGENT_PROXY_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{GC_BASE_URL}/aics/message/connect/subscribe",
                json={
                    "botId": bot_id,
                    "userId": user_id,
                    "content": last_user_msg,
                    "messageId": message_id,
                },
                headers=self._headers(token),
            ) as resp:
                resp.raise_for_status()
                connected = False

                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue

                    # 事件标签
                    if line.startswith("event:connect"):
                        connected = True
                        continue
                    if line.startswith("event:close"):
                        break
                    if line.startswith(":") or line.startswith("id:"):
                        continue

                    # 数据行
                    if not line.startswith("data:"):
                        continue

                    chunk = line[5:]
                    if not chunk:
                        continue

                    # 纯数字的 message ID (跳过)
                    if not connected and chunk.isdigit():
                        continue

                    # 解析 JSON
                    try:
                        data = json.loads(chunk)
                        if not isinstance(data, dict):
                            continue

                        # 错误帧
                        if not data.get("success", True):
                            yield json.dumps({
                                "error": data.get("errorMsg", "GC 错误"),
                                "error_code": data.get("errorCode"),
                            })
                            yield "[DONE]"
                            return

                        # 提取 responseContent (增量文本)
                        inner = data.get("data", {})
                        content = inner.get("responseContent", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        # 非 JSON 的纯文本 (如最后的 data:{numeric_msg_id})
                        pass

        yield "[DONE]"


# 注册
register_connector(GCConnector())

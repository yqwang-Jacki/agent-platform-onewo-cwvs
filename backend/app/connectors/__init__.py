"""
Platform Connector System — 通用 Agent 平台连接器

架构:
  BaseConnector (ABC)
    ├── GCConnector      — 公司 GC 客服平台
    ├── CozeConnector    — 字节 Coze 平台
    └── CustomConnector  — 自定义 Agent API (现有协议, 向后兼容)

对话代理流程:
  chat.py → get_connector(agent.platform_type) → connector.chat(messages, stream)
"""

from abc import ABC, abstractmethod
from typing import Optional, AsyncIterator
from dataclasses import dataclass, field


@dataclass
class PlatformCredential:
    """平台凭据 (用于验证和 API 调用)"""
    platform_type: str
    appid: str = ""
    secret_key: str = ""
    api_token: str = ""
    client_id: str = ""      # OAuth 2.0 client_id
    client_secret: str = ""  # OAuth 2.0 client_secret
    domain: str = ""         # COZE domain
    project_id: int = 0      # COZE project_id
    extra: dict = field(default_factory=dict)


@dataclass
class BotInfo:
    """平台上的 Bot/Agent 信息"""
    bot_id: str
    name: str
    description: str = ""
    avatar_url: str = ""
    platform_type: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class ConnectorChatResult:
    """连接器对话结果"""
    content: str
    tokens_used: int = 0
    finish_reason: str = "stop"
    extra: dict = field(default_factory=dict)


class BaseConnector(ABC):
    """平台连接器抽象基类"""

    platform_type: str = "custom"
    platform_label: str = "自定义"
    platform_icon: str = "🔌"
    help_text: str = "手动填写 Agent API 地址和认证信息"

    @abstractmethod
    async def validate_credentials(self, cred: PlatformCredential) -> bool:
        """验证凭据是否有效 (调用平台认证 API)"""
        ...

    @abstractmethod
    async def list_bots(self, cred: PlatformCredential) -> list[BotInfo]:
        """从平台获取可用的 Bot 列表"""
        ...

    @abstractmethod
    async def chat(
        self,
        cred: PlatformCredential,
        bot_config: dict,
        messages: list[dict],
        stream: bool = False,
    ) -> ConnectorChatResult:
        """向平台的 Bot 发送对话请求 (非流式)"""
        ...

    async def chat_stream(
        self,
        cred: PlatformCredential,
        bot_config: dict,
        messages: list[dict],
    ) -> AsyncIterator[str]:
        """向平台的 Bot 发送对话请求 (流式 SSE)"""
        # 默认实现：调用非流式 chat 后逐字 yield
        result = await self.chat(cred, bot_config, messages, stream=False)
        for chunk in result.content:
            yield chunk
        yield "[DONE]"


class CustomConnector(BaseConnector):
    """自定义 Agent API 连接器 (保持现有协议兼容)"""

    platform_type = "custom"
    platform_label = "自定义 API"
    platform_icon = "🔌"
    help_text = "已有 Agent API 服务，手动填写接口地址和认证头"

    async def validate_credentials(self, cred: PlatformCredential) -> bool:
        return True  # 自定义协议无需额外验证

    async def list_bots(self, cred: PlatformCredential) -> list[BotInfo]:
        return []  # 自定义协议不支持自动发现

    async def chat(
        self,
        cred: PlatformCredential,
        bot_config: dict,
        messages: list[dict],
        stream: bool = False,
    ) -> ConnectorChatResult:
        # 自定义协议走原有 httpx 直连逻辑，不经过 connector
        raise NotImplementedError("Custom connector should use direct HTTP proxy")


# ── 连接器注册表 ──────────────────────────────────

_connector_registry: dict[str, BaseConnector] = {}


def register_connector(connector: BaseConnector):
    _connector_registry[connector.platform_type] = connector


def get_connector(platform_type: str) -> Optional[BaseConnector]:
    return _connector_registry.get(platform_type)


def list_platforms() -> list[dict]:
    """列出所有可用平台 (供前端选择)"""
    return [
        {
            "platform_type": c.platform_type,
            "label": c.platform_label,
            "icon": c.platform_icon,
            "help_text": c.help_text,
        }
        for c in _connector_registry.values()
    ]


# ── 内建连接器注册 ────────────────────────────────

register_connector(CustomConnector())

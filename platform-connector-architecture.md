# Agent 平台连接器架构设计

## 概述

为 Agent 发布平台新增通用平台连接器系统，支持从 GC 客服平台和 Coze AI 平台一键导入 Agent，让非技术用户也能完成 Agent 发布。

## 核心决策：不需要额外接入大模型接口

| 方案 | 判断 | 理由 |
|------|------|------|
| 直接在平台接入 LLM | ❌ 不需要 | GC/Coze 已内置 LLM（GC 有混元/DeepSeek、Coze 有豆包），重复接入会架构分裂 |
| 平台连接器 + 协议转换 | ✅ 正确方案 | 每个平台自管模型选择，我们只需转换消息格式 + 管理凭据 |

未来如需直接托管模型，可以作为 `platform_type=openai` / `platform_type=hunyuan` 的连接器类型扩展。

## 架构图

```
┌─────────────────────────┐
│   管理后台 (一键导入UI)   │
│  选择平台 → 输入凭据      │
│  → 自动发现 Bot → 发布    │
└───────────┬─────────────┘
            │ POST /api/v1/platforms/import
┌───────────▼─────────────┐
│   后端 API               │
│  ┌─────────────────────┐│
│  │ Connector Registry  ││
│  │ ┌────┐ ┌─────┐     ││
│  │ │ GC │ │Coze │ ...  ││
│  │ └──┬─┘ └──┬──┘     ││
│  └────┼──────┼────────┘│
│       │      │          │
│  ┌────▼──────▼────────┐ │
│  │ chat.py (代理路由)  │ │
│  │ platform_type →     │ │
│  │ connector.chat()    │ │
│  └────────────────────┘ │
└──────────────────────────┘
```

## 文件变更清单

### 新增文件
- `backend/app/connectors/__init__.py` — BaseConnector 抽象基类 + 注册表
- `backend/app/connectors/gc_connector.py` — GC 平台连接器
- `backend/app/connectors/coze_connector.py` — Coze 平台连接器
- `backend/app/api/v1/platforms.py` — 平台管理 API (验证/发现/导入)
- `admin-frontend/src/components/PlatformImportDialog.tsx` — 一键导入对话框

### 修改文件
- `backend/app/models/__init__.py` — Agent 新增 platform_type, platform_config
- `backend/app/schemas/__init__.py` — 新增平台相关 Schema
- `backend/app/api/v1/chat.py` — 对话路由改为异步 + 连接器分发
- `backend/app/api/v1/agents.py` — 创建 Agent 时支持 platform 字段
- `backend/app/main.py` — 注册 platforms 路由 + 导入连接器
- `admin-frontend/src/lib/api.ts` — 新增平台 API 函数
- `admin-frontend/src/app/agents/page.tsx` — 新增"从平台导入"按钮

## 两个平台接口对照

| 维度 | GC 平台 | Coze 平台 | 自定义协议 |
|------|---------|-----------|-----------|
| 认证 | appid+secret → 临时token | API Token (JWT永久) | 自定义 Headers |
| 请求格式 | `{botId, message, history}` | `{content.query.prompt[], type, session_id, project_id}` | `{messages, stream}` |
| 响应格式 | JSON `{content, tokens_used}` | SSE 事件流 (answer/message_end) | JSON |
| 流式 | 未确认(预留) | 原生 SSE ✅ | 模拟 SSE |
| Bot 发现 | API (预留) | 手动输入 | 不支持 |

## TODO / 注意事项

1. **GC 对话/列表端点**: 当前基于通用模式推测 (`/aics/chat`, `/aics/bot/list`)，需根据实际 GC 文档调整
2. **凭据加密**: `platform_config` 中存储的 secret_key 和 api_token 为明文，生产环境应加密
3. **Token 缓存**: GC 平台 token 需缓存避免频繁获取
4. **Coze session_id**: 当前每轮对话生成临时 session，如需多轮记忆需管理 session_id 映射

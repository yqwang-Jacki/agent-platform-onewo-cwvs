# Agent 平台连接器联调报告

## 状态：✅ 两个平台全部联调通过

---

## GC 平台 (`gc`)

| 测试项 | 端点 | 结果 |
|--------|------|------|
| 认证 | `POST /aics/auth/getToken` | ✅ |
| Bot 发现 | `GET /aics/message/promptWord` | ✅ Bot: "测试" |
| 非流式对话 | `POST /aics/message/sendMessage` | ✅ "您好！我是万物云/Onewo的智能助手..." |
| 流式对话 | `POST /aics/message/connect/subscribe` | ✅ "1+1等于2。" |

**关键修复**: GC 文档要求 `Authorization: {token}`（**不加 Bearer 前缀**），之前用 `Authorization: Bearer {token}` 全部返回 `40001`。

**GC 流式格式**:
```
event:connect
data:{numeric_msg_id}
data:{"success":true, "data":{"responseContent":"逐","id":...}}  ← JSON 增量
data:{"success":true, "data":{"responseContent":"字","id":...}}
...
event:close
```

---

## COZE 平台 (`coze`)

| 测试项 | 端点 | 结果 |
|--------|------|------|
| 认证 | API Token Bearer | ✅ |
| Bot 发现 | 域名自动识别 | ✅ Bot: "6dzhzw2vvm" |
| 非流式对话 | `POST /stream_run` | ✅ "莫比乌斯考官" 安全生产系统 |
| 流式对话 | `POST /stream_run` (SSE) | ✅ 逐字转发 answer 事件 |

---

## 架构：一个平台一个文件

```
connectors/
├── __init__.py           ← BaseConnector + 注册表
├── gc_connector.py       ← GC 专属 (appid+secret, 逐字 JSON SSE)
├── coze_connector.py     ← COZE 专属 (API Token, answer SSE)
└── (未来平台...)         ← 零侵入添加
```

每个连接器只需实现：`validate_credentials` / `list_bots` / `chat` / `chat_stream`

**自定义协议 Agent 100% 向后兼容，不受影响。**

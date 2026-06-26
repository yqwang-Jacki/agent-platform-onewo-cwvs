# Agent 发布平台 — MVP 代码框架

> 基于 `agent-publish-platform-architecture.md` 生成的 MVP 基础代码框架
> 包含两个平台：普通用户端（员工使用） + 管理后台（发布者使用）

---

## 平台划分

| 平台 | 端口 | 入口 | 用途 |
|------|------|------|------|
| **普通用户端** | 3001 | http://localhost:3001 | 员工注册/登录，打开分享链接与 Agent 对话 |
| **管理后台** | 3002 | http://localhost:3002 | 发布者登录后发布 Agent、管理权限、查看用量 |
| **后端 API** | 8000 | http://127.0.0.1:8000 | 统一 API 服务（/api/v1） |

---

## 技术栈

### 后端
- **Python 3.13** + **FastAPI** — 统一后端服务
- **SQLAlchemy** — ORM（7 张核心表已定义，开发环境默认 SQLite）
- **Pydantic v2** — 请求/响应校验
- **python-jose** — JWT 签发与验证
- **passlib** — bcrypt 密码哈希
- **httpx** — 代理调用开发者部署的 Agent API

### 前端
- **Next.js 15** + **React 19** + **TypeScript**
- **Tailwind CSS v3** — 样式
- **原生 fetch** — API 调用

---

## 快速启动

### 1. 后端

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
pip install -r requirements.txt

# 已有 .env 配置好 SQLite，可直接启动
./venv/Scripts/uvicorn app.main:app --reload --port 8000
```

### 2. 普通用户端

```bash
cd ../frontend
npm install
npm run dev -- -p 3001
```

浏览器打开 `http://localhost:3001`

测试账号：手机号 `13800000000` / 邮箱 `test@example.com`，密码 `Test123456`

### 3. 管理后台

```bash
cd ../admin-frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:3002`

测试发布者：appid `test_app`，secretkey `test_secret_key_123`

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SECRET_KEY` | JWT 签名密钥（生产环境必须修改） | dev 随机值 |
| `DATABASE_URL` | 数据库连接（SQLite 用于开发） | `sqlite:///./agent_platform.db` |
| `BACKEND_CORS_ORIGINS` | 前端 origin | `["*"]`（开发环境） |
| `SHARE_BASE_URL` | H5 分享页基础 URL | `http://localhost:3001` |

---

## API 概览

### 用户认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 注册（姓名/部门/SAP/手机/邮箱/密码） |
| POST | `/api/v1/auth/login` | 登录（手机或邮箱 + 密码） |
| POST | `/api/v1/auth/refresh` | 刷新 token |
| GET | `/api/v1/auth/profile` | 获取个人资料（需 JWT） |

### 发布者认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/publisher/login` | 发布者登录（appid + secretkey） |
| POST | `/api/v1/publisher/register` | 发布者注册 |

### 管理后台 API（需发布者 JWT Bearer）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/publisher/agents` | 创建 Agent |
| GET | `/api/v1/publisher/agents` | Agent 列表 |
| GET | `/api/v1/publisher/agents/:id` | Agent 详情 |
| PUT | `/api/v1/publisher/agents/:id` | 更新 Agent（权限、API 地址等） |
| DELETE | `/api/v1/publisher/agents/:id` | 下线 Agent |
| POST | `/api/v1/publisher/agents/:id/links` | 生成分享链接 |
| GET | `/api/v1/publisher/agents/:id/links` | 链接列表 |
| DELETE | `/api/v1/publisher/agents/links/:id` | 撤销链接 |
| GET | `/api/v1/publisher/agents/stats/tokens` | Token 用量统计 |

### 终端用户对话（需用户 JWT）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/chat/agent/:link_code` | 获取 Agent 信息 |
| POST | `/api/v1/chat/agent/:link_code/messages` | 发送消息（代理到开发者的 Agent API） |
| GET | `/api/v1/chat/conversations` | 会话列表 |
| GET | `/api/v1/chat/conversations/:id` | 会话历史 |

---

## 数据库表结构

```
publishers (appid PK, secretkey_hash, name, quota_config)
  └── agents (id, appid FK, name, config, visibility, permission_config, api_endpoint)
        ├── share_links (id, agent_id FK, link_code, status, expire_at)
        ├── conversations (id, agent_id FK, user_id FK)
        │     └── messages (id, conv_id FK, role, content, tokens_used)
        └── token_usage_records (id, agent_id FK, user_id FK, date, total_tokens)
users (id PK, name, department, sap_id UK, phone UK, email UK, password_hash)
```

---

## 下一步开发建议

1. **接入 PostgreSQL**：修改 `.env` 中的 `DATABASE_URL`
2. **Agent API 协议标准化**：与开发团队约定 Agent API 的请求/响应格式
3. **SSE 流式输出**：前端改 fetch 为 EventSource，后端用 `StreamingResponse`
4. **Redis 缓存**：缓存 Agent 权限配置和用户信息
5. **用量统计增强**：按天聚合、导出报表

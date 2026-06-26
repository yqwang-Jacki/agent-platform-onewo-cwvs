# Agent 发布平台 - CloudBase 部署指南

## 环境信息
- **环境 ID**: `test-d9gd58qzc9e1242ac`
- **环境别名**: `test`
- **地域**: 上海（ap-shanghai）
- **静态托管域名**: `test-d9gd58qzc9e1242ac-1392056271.tcloudbaseapp.com`

## 部署架构
```
┌─────────────────────────────────────────────────────────────┐
│                    CloudBase 环境                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  后端服务     │  │  用户端前端   │  │  管理后台     │ │
│  │  (CloudRun)  │  │  (CloudRun)  │  │  (CloudRun)  │ │
│  │  Port: 9000  │  │  Port: 9001  │  │  Port: 9002  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 步骤 1：部署后端服务（FastAPI）

### 1.1 使用 CloudBase 控制台部署
1. 登录 [CloudBase 控制台](https://tcb.cloud.tencent.com/dev?envId=test-d9gd58qzc9e1242ac)
2. 进入 **云托管** → **服务列表**
3. 点击 **新建服务**
   - 服务名称：`agent-backend`
   - 服务类型：`容器型`
   - 端口：`9000`
4. 上传代码：
   - 将 `agent-platform/backend` 目录打包为 `.zip` 文件
   - 在控制台上传并部署
5. 配置环境变量：
   ```
   SECRET_KEY=your-secret-key-here
   CORS_ORIGINS=*
   ENV=production
   ```

### 1.2 或使用本地构建 + 推送镜像
```bash
# 构建 Docker 镜像
cd agent-platform/backend
docker build -t ccr.ccs.tencentyun.com/test-d9gd58qzc9e1242ac/agent-backend:latest .

# 推送镜像
docker push ccr.ccs.tencentyun.com/test-d9gd58qzc9e1242ac/agent-backend:latest

# 在控制台中更新服务镜像
```

## 步骤 2：部署用户端前端（Next.js）

### 2.1 构建 Docker 镜像
```bash
cd agent-platform/frontend

# 更新 API 地址为后端 CloudRun 地址
echo "NEXT_PUBLIC_API_URL=https://agent-backend.service.tcloudbase.com" > .env.local

# 构建镜像
docker build -t ccr.ccs.tencentyun.com/test-d9gd58qzc9e1242ac/agent-frontend:latest .
docker push ccr.ccs.tencentyun.com/test-d9gd58qzc9e1242ac/agent-frontend:latest
```

### 2.2 在控制台创建 CloudRun 服务
1. 进入 **云托管** → **服务列表**
2. 新建服务：
   - 服务名称：`agent-frontend`
   - 服务类型：`容器型`
   - 端口：`9000`（Next.js 默认）
3. 使用上面推送的镜像部署

## 步骤 3：部署管理后台（Next.js）

重复步骤 2，服务名称改为 `agent-admin`。

## 步骤 4：配置域名

### 4.1 使用默认域名
部署完成后，CloudBase 会自动为每个 CloudRun 服务分配一个公网访问域名：
- 后端：`https://agent-backend-xxx.service.tcloudbase.com`
- 用户端：`https://agent-frontend-xxx.service.tcloudbase.com`
- 管理后台：`https://agent-admin-xxx.service.tcloudbase.com`

### 4.2 绑定自定义域名
1. 进入 **环境** → **安全配置** → **Service 域名配置**
2. 点击 **添加域名**
3. 输入你的域名（如 `agent.example.com`）
4. 按照提示在域名服务商处配置 CNAME 记录
5. 等待 DNS 生效（通常 10 分钟内）

### 4.3 配置 HTTPS 证书
- CloudBase 自动为 `.tcloudbase.com` 域名配置 SSL 证书
- 自定义域名需要手动上传证书或在控制台申请免费证书

## 验证部署

### 检查后端健康状态
```bash
curl https://agent-backend-xxx.service.tcloudbase.com/health
# 预期返回：{"status": "ok", "version": "1.0.0"}
```

### 检查前端访问
在浏览器中访问前端域名，确认可以正常加载和登录。

## 常见问题

### Q1: 后端无法连接数据库
**A**: 当前使用 SQLite，数据会随容器重启丢失。建议迁移到 CloudBase PostgreSQL：
1. 在控制台开通 PostgreSQL
2. 更新后端代码使用 `DATABASE_URL` 环境变量连接

### Q2: 前端 API 请求失败
**A**: 检查 CORS 配置和后端的 `CORS_ORIGINS` 环境变量。

### Q3: 静态资源加载失败
**A**: 确认 Next.js 配置正确，所有静态资源路径使用相对路径或绝对 URL。

## 下一步

1. **配置 CI/CD**：使用 CloudBase CLI 或 GitHub Actions 实现自动部署
2. **监控和日志**：在控制台配置日志收集和监控告警
3. **数据库迁移**：从 SQLite 迁移到 CloudBase PostgreSQL
4. **配置 CDN 加速**：为前端静态资源配置 CDN

---

**部署完成后，请运行以下命令验证**：
```bash
# 检查后端健康状态
curl https://your-backend-domain/health

# 检查前端访问
curl https://your-frontend-domain

# 测试 API 登录
curl -X POST https://your-backend-domain/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"account": "admin@example.com", "password": "Test123456"}'
```

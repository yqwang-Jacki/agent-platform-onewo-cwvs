# GitHub + CloudBase 部署指南

## 📋 完整部署流程

### 步骤 1：在 GitHub 上创建仓库

1. **访问 GitHub 并登录**
   - 打开：https://github.com
   - 登录你的 GitHub 账号

2. **创建新仓库**
   - 点击右上角 `+` 图标 → 选择 `New repository`
   - 填写仓库信息：
     - **Repository name**: `agent-platform`
     - **Description**: `Full-stack AI Agent Management Platform`
     - **Public/Private**: 选择 `Public` 或 `Private`
     - ⚠️ **不要**勾选 "Initialize with README"（我们已经有代码了）
   - 点击 `Create repository`

3. **记录仓库 URL**
   - 创建后会看到类似这样的 URL：
   ```
   https://github.com/YOUR_USERNAME/agent-platform.git
   ```

---

### 步骤 2：推送代码到 GitHub

在 WorkBuddy 终端执行以下命令（替换 `YOUR_USERNAME` 为你的 GitHub 用户名）：

```bash
# 1. 进入项目目录
cd /c/Users/71520/WorkBuddy/2026-06-18-11-53-45/agent-platform

# 2. 添加远程仓库（替换 YOUR_USERNAME）
git remote add origin https://github.com/YOUR_USERNAME/agent-platform.git

# 3. 重命名分支为 main（GitHub 默认分支）
git branch -M main

# 4. 推送代码到 GitHub
git push -u origin main
```

**首次推送会要求输入 GitHub 认证信息**：
- **方法 A（推荐）**：使用 GitHub Personal Access Token (PAT)
  1. 访问：https://github.com/settings/tokens
  2. 点击 `Generate new token (classic)`
  3. 勾选 `repo` 权限
  4. 生成 token 并复制
  5. 推送时，用户名输入你的 GitHub 用户名，密码输入 **token**（不是 GitHub 密码）

- **方法 B**：使用 GitHub CLI（需要先安装）
  ```bash
  # 安装 GitHub CLI
  winget install --id GitHub.cli
  
  # 登录 GitHub
  gh auth login
  
  # 推送代码
  git push -u origin main
  ```

---

### 步骤 3：配置 CloudBase 从 GitHub 自动部署

#### 3.1 连接 GitHub 仓库到 CloudBase

1. **登录 CloudBase 控制台**
   - 访问：https://tcb.cloud.tencent.com
   - 选择环境：`test-d9gd58qzc9e1242ac`

2. **进入云托管设置**
   - 左侧菜单 → `云托管` → `服务列表`

3. **创建服务并连接 GitHub**
   - 点击 `新建服务`
   - 服务名称：`agent-backend`
   - 选择 `从 GitHub 仓库部署`
   - 首次使用需要授权 CloudBase 访问你的 GitHub 账号
   - 选择刚才创建的 `agent-platform` 仓库
   - 选择分支：`main`
   - 选择 Dockerfile 路径：`backend/Dockerfile`

4. **配置构建和环境变量**
   - 端口：`9000`
   - 环境变量：
     ```
     SECRET_KEY=your-production-secret-key
     CORS_ORIGINS=https://your-frontend-domain.com
     DATABASE_URL=sqlite:///tmp/agent_platform.db
     ```
   - 点击 `创建并部署`

#### 3.2 部署用户端前端

重复上述步骤，创建服务：
- 服务名：`agent-frontend`
- Dockerfile 路径：`frontend/Dockerfile`
- 端口：`3000`
- 环境变量：
  ```
  NEXT_PUBLIC_API_URL=https://agent-backend.your-domain.com
  ```

#### 3.3 部署管理后台

- 服务名：`agent-admin`
- Dockerfile 路径：`admin-frontend/Dockerfile`
- 端口：`3002`

---

### 步骤 4：配置自定义域名（可选）

1. **在 CloudBase 控制台配置域名**
   - 左侧菜单 → `环境` → `安全配置`
   - 找到 `Service 域名配置`
   - 添加你的自定义域名（如 `agent.yourcompany.com`）

2. **在域名服务商配置 CNAME 记录**
   - 根据 CloudBase 提供的 CNAME 信息
   - 在你的域名服务商（如阿里云、腾讯云）配置 DNS 记录

---

## 🚀 自动部署工作流

配置完成后，每次你推送代码到 GitHub `main` 分支，CloudBase 会自动：
1. 检测仓库变更
2. 拉取最新代码
3. 使用 Dockerfile 构建镜像
4. 部署到云托管服务
5. 发送部署通知（可配置）

---

## 📝 快速命令参考

```bash
# 查看当前远程仓库
git remote -v

# 更新代码并推送到 GitHub
git add .
git commit -m "Your commit message"
git push origin main

# 查看部署状态
# 访问 CloudBase 控制台 → 云托管 → 服务列表 → 查看日志
```

---

## ⚠️ 常见问题

### Q1: 推送代码时提示 "Authentication failed"
**解决方法**：使用 Personal Access Token 而不是密码。参考步骤 2 中的 "方法 A"。

### Q2: CloudBase 无法访问 GitHub 仓库
**解决方法**：
1. 确认在 CloudBase 控制台正确授权了 GitHub 访问权限
2. 确认仓库是 `Public`，或者 Private 仓库已授予 CloudBase 访问权限

### Q3: 构建失败，提示 "Dockerfile not found"
**解决方法**：在 CloudBase 部署配置中，确认 Dockerfile 路径正确：
- 后端：`backend/Dockerfile`
- 用户端：`frontend/Dockerfile`
- 管理后台：`admin-frontend/Dockerfile`

---

## 📞 需要帮助？

如果遇到问题，可以：
1. 查看 CloudBase 部署日志（控制台 → 云托管 → 服务详情 → 部署日志）
2. 查看 GitHub 仓库的 Actions 标签页（如果有配置 CI/CD）
3. 向我提问，我会帮你解决！

---

**下一步**：完成步骤 1 和 2（创建 GitHub 仓库并推送代码），然后告诉我，我会帮你配置 CloudBase 自动部署。

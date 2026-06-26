FROM node:22-alpine

WORKDIR /app

# 安装 pnpm（可选，如果使用 pnpm）
# RUN npm install -g pnpm

# 复制依赖文件
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制应用代码
COPY . .

# 构建 Next.js 应用
RUN npm run build

# 暴露端口（CloudRun 默认使用 9000）
EXPOSE 9000

# 启动 Next.js 服务器
# 需要设置 HOST 为 0.0.0.0 以允许外部访问
CMD ["sh", "-c", "npm run start -H 0.0.0.0 -p 9000"]
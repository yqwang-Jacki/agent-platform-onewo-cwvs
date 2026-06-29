FROM node:22-alpine

WORKDIR /app

# 接受构建参数
ARG NEXT_PUBLIC_API_URL=https://agent-backend-275072-5-1392056271.sh.run.tcloudbase.com/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# 复制依赖文件
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制应用代码
COPY . .

# 构建 Next.js 应用
RUN npm run build

# 暴露端口
EXPOSE 3000

# 启动
CMD ["npx", "next", "start", "-H", "0.0.0.0", "-p", "3000"]

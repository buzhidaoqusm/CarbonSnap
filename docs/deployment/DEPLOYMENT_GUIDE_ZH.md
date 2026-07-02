# CarbonSnap 远程服务器部署指南

本文档提供了将 CarbonSnap 项目部署到远程服务器（如阿里云、腾讯云、AWS等）的详细步骤。推荐使用 **Docker & Docker Compose** 方式进行容器化部署，这有助于隔离环境、简化配置并提高可移植性。

## 方案一：使用 Docker 部署（推荐）

使用 Docker 可以一键启动前后端以及数据库等依赖服务。

### 1. 准备工作

在远程服务器上，你需要安装：
- [Docker](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- Git（用于克隆代码库）

### 2. 添加 Docker 配置文件

在项目根目录下，我们需要准备后端的 `Dockerfile`，前端的 `Dockerfile`，以及编排它们的 `docker-compose.yml`。

#### 后端 Dockerfile (`infra/docker/Dockerfile.backend`)
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装必要的系统依赖（如果有些包需要编译）
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

COPY backend/ .

# 暴露端口
EXPOSE 5000

# 使用 Gunicorn 作为生产环境的 WSGI 服务器启动
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
```

#### 前端 Dockerfile (`infra/docker/Dockerfile.frontend`)
```dockerfile
# 编译阶段
FROM node:22-alpine as build-stage
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
# 在构建时可以通过环境变量设定后端 API 地址
# ENV VITE_API_BASE_URL=https://your-domain.com/api
RUN npm run build

# 部署阶段，使用 Nginx 提供静态文件服务
FROM nginx:alpine as production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### Nginx 配置 (`infra/docker/nginx.conf`)
```nginx
server {
    listen       80;
    server_name  localhost;

    # 静态文件前端页面
    location / {
        root   /usr/share/nginx/html;
        index  index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    # 转发 API 请求到后端容器
    location /api/ {
        proxy_pass http://backend:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Docker Compose (`docker-compose.yml`)
在项目根目录创建：
```yaml
version: '3.8'

services:
  frontend:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: always

  backend:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.backend
    ports:
      - "5000:5000"
    volumes:
      # 挂载数据卷以便保存上传的文件等持久化数据
      - ./data:/app/data
    environment:
      - FLASK_ENV=production
      # - DATABASE_URL=postgresql://user:password@db/dbname
    restart: always
```

### 3. 上传代码并在服务器上启动

1. 通过 SSH 连接你的远程服务器。
2. 使用 `git clone` 将代码仓库拉取到服务器中（或通过 SCP、SFTP 等方式上传源码）。
3. 进入项目根目录：
   ```bash
   cd CarbonSnap
   ```
4. 执行以下命令构建并启动容器组，这将在后台运行程序：
   ```bash
   docker-compose up -d --build
   ```

启动成功后，在浏览器中访问服务器的公网 IP 或绑定的域名，即可查看部署好的 CarbonSnap。

---

## 方案二：传统方式手动部署 (Ubuntu/Debian)

如果你不想使用 Docker，也可以直接在系统系统上安装和配置 Nginx + Gunicorn + Node.js 等。

### 1. 服务器环境准备
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv nginx git
# 安装 Node.js
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

### 2. 部署后端环境与 Gunicorn

1. 进入项目后端目录，创建并激活虚拟环境，安装依赖：
   ```bash
   cd CarbonSnap/backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn
   ```

2. 测试拉起应用：
   ```bash
   gunicorn -w 4 -b 127.0.0.1:5000 run:app
   ```
   *推荐使用 Systemd 编写一个服务守护进程使得后端 Gunicorn 常驻在后台。*

### 3. 编译打包前端静态文件

1. 进入前端目录，安装依赖库：
   ```bash
   cd ../frontend
   npm install
   ```

2. 打包构建出静态文件：
   ```bash
   npm run build
   ```
   打包完成后，所有前端的构建产物都将生成在 `frontend/dist` 目录中。

### 4. 配置 Nginx 代理与静态资源服务器

1. 创建 Nginx 配置文件 `sudo nano /etc/nginx/sites-available/carbonsnap`：
   ```nginx
   server {
       listen 80;
       server_name your_domain_or_ip;

       # 托管 Vue.js 打包出的前端静态文件
       location / {
           root /path/to/CarbonSnap/frontend/dist;
           index index.html;
           try_files $uri $uri/ /index.html;
       }

       # 反向代理将 API 请求转发到后端的 Gunicorn 服务器上
       location / {
           proxy_pass http://127.0.0.1:5000/;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
   注意：由于项目路由有可能是 `/api/` 或者直接挂载在主应用上，请根据后端的 Blueprint 实际路径来调整反向代理的前缀匹配条件。

2. 启用配置并重启 Nginx 服务器：
   ```bash
   sudo ln -s /etc/nginx/sites-available/carbonsnap /etc/nginx/sites-enabled
   sudo nginx -t
   sudo systemctl restart nginx
   ```

## 额外建议与安全设置

1. **设置 HTTPS 证书**：项目上线通常需要加密连接，建议使用 [Certbot (Let's Encrypt)](https://certbot.eff.org/) 一键为你的域名获取免费证书并自动配置 SSL。
2. **防火墙配置**：检查服务器安全组以及 UFW，确保开放了：80 端口 (HTTP)、443 端口 (HTTPS) 及你所需的 22 端口 (SSH)。
3. **数据库迁移与初始化**：后端部署后，如果涉及到数据库新建与变更，请在确认启动后进入 `.venv` 执行 Alembic 或相关 Python 脚本初始化你的表结构（比如 `alembic upgrade head` 或你的 init DB 脚本）。

## 可选：使用 Docker 启动 Neo4j GraphRAG

Neo4j 只用于 CarbonSnap 的可选 GraphRAG 知识图谱层，不是主业务数据库。即使 Neo4j 不可用，后端也可以把 `AI_NEO4J_GRAPHRAG_ENABLED=false`，继续使用普通 AI chat、论坛 RAG 和 SQLite 业务数据。

如果你的服务器还没有 Docker，先安装 Docker Engine。下面是 Ubuntu 22.04 推荐使用的 apt repository 安装方式：

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo ${UBUNTU_CODENAME:-$VERSION_CODENAME}) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run hello-world
```

`hello-world` 能正常输出后，再单独启动一个 Neo4j 容器：

```bash
docker run -d --name carbonsnap-neo4j --restart unless-stopped \
  -p 127.0.0.1:7474:7474 \
  -p 127.0.0.1:7687:7687 \
  -e NEO4J_AUTH=neo4j/YOUR_STRONG_PASSWORD \
  -v carbonsnap-neo4j-data:/data \
  neo4j:5
```

这里故意把 `7474` 和 `7687` 绑定到 `127.0.0.1`：

- Flask 后端和 Neo4j 在同一台服务器上，通过 `bolt://127.0.0.1:7687` 连接即可。
- Neo4j Browser 不直接暴露到公网，避免占用或绕过 Nginx 对外端口。
- 如果你需要从本地电脑打开 Neo4j Browser，用 SSH 隧道访问：

```bash
ssh -L 7474:127.0.0.1:7474 student@YOUR_SERVER
```

然后本地浏览器打开：

```text
http://127.0.0.1:7474/browser/
```

后端 `.env` 中启用 Neo4j GraphRAG：

```env
AI_TRACE_ENABLED=true
AI_GRAPH_AGENT_ENABLED=true
AI_NEO4J_GRAPHRAG_ENABLED=true
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=YOUR_STRONG_PASSWORD
```

初始化图谱数据：

```bash
cd ~/CarbonSnap/backend
source .venv/bin/activate
python scripts/seed_recycling_graph.py
sudo systemctl restart gunicorn
```

如果服务器没有 Docker，或部署环境不允许额外服务，保持：

```env
AI_GRAPH_AGENT_ENABLED=true
AI_NEO4J_GRAPHRAG_ENABLED=false
```

这样仍然可以展示 LangGraph Agent Trace、PromptOps、工具调用和传统 RAG，只是不会显示 Neo4j Graph Evidence。

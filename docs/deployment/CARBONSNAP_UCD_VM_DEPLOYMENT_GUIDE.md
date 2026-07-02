# CarbonSnap 项目部署指南

> 适用场景：
> 1. 按照课程文档把项目部署到 UCD 分配的 Ubuntu VM 上
> 2. 让老师/助教直接通过浏览器访问
> 3. 项目结构为 `Vue/Vite 前端 + Flask 后端 + SQLite`

> 本文档综合了以下材料：
> - `docs/deployment/Deploying web applications.pptx`
> - `docs/deployment/COMP3030J Web server instructions - Part 1 (2024).pdf`
> - `docs/deployment/COMP3030J Web server instructions - Part 2 (2024).pdf`
> - 当前仓库的实际代码结构与配置

---

## 1. 先理解这次部署的目标

课程文档里的示例是“一个简单 Flask 页面监听 `127.0.0.1:5000`，再由 Nginx 反向代理出去”。  
但 `CarbonSnap` 不是单文件 Flask 项目，而是下面这个结构：

```text
CarbonSnap/
├─ backend/                 # Flask API
│  ├─ run.py                # Gunicorn/Flask 启动入口，暴露 app
│  ├─ requirements.txt
│  ├─ .env.example
│  └─ app/
├─ frontend/                # Vue + Vite
│  ├─ package.json
│  ├─ vite.config.js
│  └─ dist/                 # 构建后生成，Nginx 直接托管
├─ data/                    # SQLite / uploads / faiss 数据
└─ docs/
```

所以最终上线结构应该是：

```text
浏览器
  -> http://{VM_NAME}/
  -> Nginx
      -> /            直接返回 frontend/dist 中的静态文件
      -> /api/*       转发到 Gunicorn
      -> Gunicorn     运行 backend/run.py 里的 Flask app
      -> SQLite       data/carbonsnap.db
```

这也是最适合你们当前仓库的部署方式：

- 前端不再跑 `vite dev`
- 后端不再跑 `python run.py` 作为长期服务
- 对外只开放 80/443/22
- 5000 端口不暴露到公网
- Gunicorn 通过 `systemd` 常驻
- Nginx 负责反向代理和静态资源托管

---

## 2. 这份仓库里已经确定的关键信息

在真正部署前，先明确几个和你们项目强相关的事实：

### 2.1 后端入口

`backend/run.py` 的内容说明 Gunicorn 启动目标应该是：

```python
from app import create_app

app = create_app()
```

也就是说后面 Gunicorn 应该启动 `run:app`。

### 2.2 后端默认数据库

`backend/app/config/settings.py` 中默认数据库路径是：

```text
data/carbonsnap.db
```

也就是仓库根目录下的：

```text
CarbonSnap/data/carbonsnap.db
```

如果你不额外设置 `DATABASE_URL`，项目默认就会使用 SQLite。

### 2.3 后端会读 `.env`

后端启动时会自动读取：

```text
backend/.env
```

所以生产环境的密钥、JWT、模型 API Key，都应该放在服务器上的 `backend/.env`，不要写死进代码。

### 2.4 前端生产环境 API 地址

你们前端代码里用了 `VITE_API_BASE_URL`，但逻辑是：

- 开发环境默认走 `http://127.0.0.1:5000`
- 生产环境如果不配置，则默认走当前域名下的相对路径 `/api/...`

这意味着只要 Nginx 配好了：

- `/` -> 前端静态资源
- `/api/` -> Flask

那么生产环境通常 **不需要** 额外设置 `VITE_API_BASE_URL`。

### 2.5 上传和 AI 索引数据目录

后端还会使用：

- `data/uploads/`
- `data/faiss/`

这两个目录是运行期数据目录，不应该提交到 Git，但服务器上必须存在且可写。

---

## 3. 部署前你要准备好的东西

开始之前，请把下面这些信息准备好：

### 3.1 服务器信息

- 你的 UCD VM 主机名，例如 `<VM_HOST>`
- `student` 用户密码

说明：

- 课程 PPT 和 PDF 都强调：对外只有 `22 / 80 / 443` 端口可用
- 不要试图直接让浏览器访问 `:5000`

### 3.2 代码仓库地址

你需要仓库的克隆地址，例如：

```bash
https://csgitlab.ucd.ie/<your-group>/<your-repo>.git
```

### 3.3 后端生产环境变量

至少要准备：

- `JWT_SECRET_KEY`
- `LLM_PROVIDER`
- `QWEN_API_KEY` 或 `OPENROUTER_API_KEY`

建议额外确认：

- `OPENROUTER_SITE_URL`
- `OPENROUTER_SITE_NAME`
- `QWEN_MODEL`
- `UPLOAD_ROOT`

如果你要启用可选的 Neo4j GraphRAG，还需要准备：

- `AI_GRAPH_AGENT_ENABLED`
- `AI_NEO4J_GRAPHRAG_ENABLED`
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`

课程 VM 对外通常只开放 `22 / 80 / 443`。Neo4j 不应该暴露公网端口，也不需要走 Nginx；如果安装 Neo4j，应让后端通过 `bolt://127.0.0.1:7687` 在服务器本机访问。

如果服务器没有 Docker，`docker run` 不会自动安装 Docker，需要先安装 Docker Engine。Ubuntu 22.04 可以使用 Docker 官方 apt repository：

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

确认 Docker 可用后，可以用下面的本机私有端口方式启动 Neo4j：

```bash
docker run -d --name carbonsnap-neo4j --restart unless-stopped \
  -p 127.0.0.1:7474:7474 \
  -p 127.0.0.1:7687:7687 \
  -e NEO4J_AUTH=neo4j/YOUR_STRONG_PASSWORD \
  -v carbonsnap-neo4j-data:/data \
  neo4j:5
```

如果课程 VM 没有 Docker 或不允许安装 Docker，可以跳过 Neo4j 并设置 `AI_NEO4J_GRAPHRAG_ENABLED=false`。Graph Agent 仍可运行，图谱证据会 fallback。

### 3.4 本地工具

你本地电脑建议准备：

- SSH 客户端
- Git
- Node.js（如果你选择本地构建前端）

---

## 4. 推荐的部署总路线

推荐你按下面顺序做，不要跳步：

1. SSH 登录 VM，确认主机名和密码可用
2. 在 VM 上克隆仓库
3. 创建后端虚拟环境并安装 Python 依赖
4. 配置 `backend/.env`
5. 执行数据库迁移
6. 先在 VM 本机上验证 Flask/Gunicorn 能启动
7. 构建前端 `frontend/dist`
8. 写 `gunicorn.conf.py`
9. 写 `systemd` 的 `gunicorn.service` 和 `gunicorn.socket`
10. 写 Nginx 站点配置
11. 启动 Gunicorn 和 Nginx
12. 用浏览器和命令行做验收

---

## 5. 第一步：登录 VM 并修改密码

课程文档要求的第一步就是 SSH 登录。

在你本地终端执行：

```bash
ssh student@{VM_NAME}
```

例如如果你们当前 VM 是 `<VM_HOST>`，那就是：

```bash
ssh student@<VM_HOST>
```

第一次登录时如果看到类似：

```text
The authenticity of host ... can't be established.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

输入：

```text
yes
```

然后输入老师给你们的初始密码。

如果这是你第一次登录，课程要求你改密码：

```bash
passwd
```

注意：

- 新密码要团队共享
- 不要把密码继续保存在仓库明文文件中
- 最好使用密码管理器或单独的安全文档

---

## 6. 第二步：更新系统并安装基础依赖

登录到 VM 后，先更新软件索引：

```bash
sudo apt update
```

再安装项目部署常用工具：

```bash
sudo apt install -y git python3 python3-venv python3-pip nginx
```

建议顺手检查版本：

```bash
python3 --version
git --version
nginx -v
```

说明：

- 课程 PDF 明确要求使用 Python 虚拟环境
- Nginx 是课程指定的反向代理
- 这里不需要安装数据库服务，因为你们当前默认用 SQLite

---

## 7. 第三步：把仓库拉到服务器

先回到家目录：

```bash
cd ~
```

克隆仓库：

```bash
git clone <YOUR_GIT_REPO_URL> CarbonSnap
```

例如：

```bash
git clone https://csgitlab.ucd.ie/<your-group>/<your-repo>.git CarbonSnap
```

进入项目目录：

```bash
cd ~/CarbonSnap
```

可以确认目录结构：

```bash
ls
```

你应该能看到：

- `backend`
- `frontend`
- `data`
- `docs`

---

## 8. 第四步：准备后端 Python 虚拟环境

进入后端目录：

```bash
cd ~/CarbonSnap/backend
```

创建虚拟环境：

```bash
python3 -m venv .venv
```

激活虚拟环境：

```bash
source .venv/bin/activate
```

升级 pip：

```bash
pip install --upgrade pip
```

安装依赖：

```bash
pip install -r requirements.txt
```

安装完成后可以确认路径：

```bash
which python
which pip
```

它们都应该指向：

```text
/home/student/CarbonSnap/backend/.venv/...
```

注意：

- 不要用 `sudo pip install ...`
- 课程文档已经明确禁止把 Python 依赖装成全局系统依赖

---

## 9. 第五步：创建并填写生产环境 `.env`

先复制模板：

```bash
cp .env.example .env
```

再编辑：

```bash
nano .env
```

推荐至少写成下面这样：

```dotenv
JWT_SECRET_KEY=<CHANGE_TO_A_LONG_RANDOM_SECRET>

LLM_PROVIDER=qwen

QWEN_API_KEY=<YOUR_QWEN_API_KEY>
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-vl-plus-2025-05-07

OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openai/gpt-5.2
OPENROUTER_SITE_URL=http://{VM_NAME}
OPENROUTER_SITE_NAME=CarbonSnap

AI_MAP_SEARCH_RADIUS_METERS=5000
AI_MAP_SEARCH_LIMIT=12
AI_SHORT_TERM_MEMORY_TURNS=10
FORUM_RAG_EMBEDDING_MODEL=text-embedding-v3
AI_DECISION_ENGINE_MODE=shadow
```

如果你们要继续使用 OpenRouter，则改成：

```dotenv
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=<YOUR_OPENROUTER_API_KEY>
```

### 9.1 强烈建议你单独设置 JWT 密钥

可以直接在服务器上生成一个随机值：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

把输出粘贴到：

```dotenv
JWT_SECRET_KEY=...
```

### 9.2 如果你想显式写运行数据目录

你也可以把路径显式写清楚：

```dotenv
UPLOAD_ROOT=/home/student/CarbonSnap/data/uploads
```

SQLite 数据库如果继续使用默认值，通常不必写：

```dotenv
DATABASE_URL=
```

因为代码已经默认指向：

```text
/home/student/CarbonSnap/data/carbonsnap.db
```

### 9.3 不要做的事

- 不要把真实 API Key 提交回 Git
- 不要把 `.env` 发到群里
- 不要在仓库文档里记录真实密钥

---

## 10. 第六步：准备运行数据目录

回到仓库根目录：

```bash
cd ~/CarbonSnap
```

创建运行目录：

```bash
mkdir -p data/uploads data/faiss
```

如果你们之后要保留数据库文件，也可以先确认：

```bash
touch data/.keep
```

再检查权限：

```bash
ls -ld data data/uploads data/faiss
```

通常它们的所有者应该是 `student`。

---

## 11. 第七步：执行数据库迁移

再次进入后端并激活虚拟环境：

```bash
cd ~/CarbonSnap/backend
source .venv/bin/activate
```

对于你们这个仓库，**不要在服务器上重新 `flask db init`**，因为迁移文件已经存在于：

```text
backend/migrations/
```

正确做法是直接升级数据库：

```bash
flask --app run.py db upgrade
```

如果成功，SQLite 文件会出现在：

```text
~/CarbonSnap/data/carbonsnap.db
```

你可以检查：

```bash
ls -l ~/CarbonSnap/data
```

如果数据库迁移失败，先检查：

- 是否激活了 `.venv`
- `backend/.env` 是否格式正确
- 当前命令是否在 `backend/` 目录执行

---

## 12. 第八步：先在服务器本机验证后端能启动

这一步非常重要。  
在配 Nginx 和 systemd 之前，先确认 Flask 本身可以跑起来。

### 12.1 先用开发方式快速验证

在 `backend/` 目录里执行：

```bash
source .venv/bin/activate
python run.py
```

如果启动成功，另开一个 SSH 会话，或者在 VM 本机执行：

```bash
curl http://127.0.0.1:5000/api/health
```

你应该看到类似：

```json
{"message":"Backend is running.","service":"carbonsnap-backend","status":"ok"}
```

确认成功后按：

```text
Ctrl + C
```

停止它。

### 12.2 再用 Gunicorn 临时验证

同样在 `backend/` 目录执行：

```bash
source .venv/bin/activate
gunicorn --bind 127.0.0.1:5000 run:app
```

然后再测一次：

```bash
curl http://127.0.0.1:5000/api/health
```

如果这里也成功，说明：

- Gunicorn 可以正常导入 `run:app`
- 后端依赖和 `.env` 基本没问题

确认后按 `Ctrl + C` 停止。

---

## 13. 第九步：构建前端

你们前端是 Vue + Vite，最终部署需要 `frontend/dist/`。

这里有两种做法。

### 13.1 方案 A：在 VM 上构建前端

这是最整齐的做法，但要求服务器上有可用的 Node.js。

先检查 Node：

```bash
node -v
npm -v
```

如果 VM 上已经有合适的 Node 版本，就继续。

进入前端目录：

```bash
cd ~/CarbonSnap/frontend
```

安装依赖：

```bash
npm ci
```

如果 `npm ci` 因锁文件或环境问题失败，再退回：

```bash
npm install
```

构建生产包：

```bash
npm run build
```

成功后应该生成：

```text
~/CarbonSnap/frontend/dist/
```

### 13.2 方案 B：在你本地电脑构建，再上传到 VM

如果 VM 上装 Node 比较麻烦，这是更稳妥的替代方案。

你在本地仓库执行：

```bash
cd frontend
npm install
npm run build
```

然后把构建产物上传到服务器：

```bash
scp -r dist/* student@{VM_NAME}:~/CarbonSnap/frontend/dist/
```

说明：

- 这种方式不会影响后端部署
- 但每次前端改动后，你都要重新本地 build 再上传

### 13.3 为什么生产环境一般不用 `VITE_API_BASE_URL`

因为你们前端生产代码默认会访问相对路径：

```text
/api/...
```

只要后面 Nginx 配好 `/api/` 反向代理，前端就能直接工作。

---

## 14. 第十步：创建 Gunicorn 配置文件

课程 Part 2 讲的是 Gunicorn + systemd。  
对 `CarbonSnap` 来说，我们最终使用：

- Gunicorn 运行 Flask
- systemd 保证它常驻
- Nginx 通过 Unix socket 连接它

在服务器上创建文件：

```bash
cd ~/CarbonSnap/backend
nano gunicorn.conf.py
```

写入下面内容：

```python
import multiprocessing

# CarbonSnap 在 4C / 4G 的课程 VM 上，先保守一点。
# 课程文档给出的 cpu*2+1 对这个项目可能偏大。
workers = min(3, multiprocessing.cpu_count())
timeout = 300
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
capture_output = True
```

### 14.1 为什么这里不写 `bind`

因为我们后面会使用 `systemd socket activation`：

- socket 文件决定监听 `/run/gunicorn.sock`
- Gunicorn 直接接管这个 socket

这样就不需要再在配置文件里写 `bind = "127.0.0.1:5000"`。

### 14.2 为什么 workers 先用 3

课程 VM 是：

- 4 cores
- 4 GiB RAM

你们这个项目还包含：

- AI 流式接口
- 图片上传
- SQLite
- FAISS 目录

如果直接照最经典的 `cpu_count() * 2 + 1`，可能会把 worker 开得太激进。  
先从 `3` 开始更稳，后续如果运行非常稳定，再考虑调大。

---

## 15. 第十一步：创建 systemd 服务

课程 Part 2 的核心就是这一步。

### 15.1 创建 `gunicorn.service`

执行：

```bash
sudo nano /etc/systemd/system/gunicorn.service
```

写入：

```ini
[Unit]
Description=Gunicorn daemon for CarbonSnap backend
Requires=gunicorn.socket
After=network.target

[Service]
Type=notify
User=student
Group=student
WorkingDirectory=/home/student/CarbonSnap/backend
ExecStart=/home/student/CarbonSnap/backend/.venv/bin/gunicorn --config /home/student/CarbonSnap/backend/gunicorn.conf.py run:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=20
PrivateTmp=true
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

说明：

- `WorkingDirectory` 必须是 `backend`
- `ExecStart` 必须指向虚拟环境里的 gunicorn
- 启动对象必须是 `run:app`

### 15.2 创建 `gunicorn.socket`

执行：

```bash
sudo nano /etc/systemd/system/gunicorn.socket
```

写入：

```ini
[Unit]
Description=Gunicorn socket for CarbonSnap

[Socket]
ListenStream=/run/gunicorn.sock
SocketUser=www-data

[Install]
WantedBy=sockets.target
```

### 15.3 重新加载 systemd

创建或修改完这两个文件后，执行：

```bash
sudo systemctl daemon-reload
```

### 15.4 启动并设置开机自启

执行：

```bash
sudo systemctl enable --now gunicorn.socket
```

然后检查：

```bash
sudo systemctl status gunicorn.socket
```

如果你想看 Gunicorn 服务本体是否被触发，也可以执行：

```bash
sudo systemctl status gunicorn.service
```

第一次通常在收到请求后会被 socket 激活。

---

## 16. 第十二步：编写 Nginx 站点配置

这一部分是把课程 Part 1 和你们实际项目拼起来的关键步骤。

### 16.1 创建站点配置文件

执行：

```bash
sudo nano /etc/nginx/sites-available/{VM_NAME}
```

如果你们当前机器名是 `<VM_HOST>`，那文件名就是：

```bash
sudo nano /etc/nginx/sites-available/<VM_HOST>
```

### 16.2 写入适配 CarbonSnap 的配置

把下面内容完整粘进去，然后把 `{VM_NAME}` 换成你们真实域名：

```nginx
upstream carbonsnap_backend {
    server unix:/run/gunicorn.sock;
}

server {
    listen 80;
    listen [::]:80;
    server_name <VM_HOST>;

    root /home/student/CarbonSnap/frontend/dist;
    index index.html;

    # 论坛图片、审核图片等可能是 base64 上传后落盘，留一个更宽松的上限
    client_max_body_size 20M;

    location /api/ {
        proxy_pass http://carbonsnap_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # AI chat / analyze-image / audit-recycling 使用 SSE 流式返回
        proxy_buffering off;
        proxy_read_timeout 300;
        proxy_send_timeout 300;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 16.3 这个配置为什么这么写

#### `root /home/student/CarbonSnap/frontend/dist;`

表示首页和静态资源由 Nginx 直接提供，不走 Flask。

#### `location /api/`

表示所有后端接口都交给 Gunicorn。

这和你们代码中的 API 路径完全匹配，因为后端蓝图都注册在：

```text
/api/...
```

例如：

- `/api/health`
- `/api/auth/login`
- `/api/ai/chat/stream`
- `/api/uploads/...`

#### `try_files $uri $uri/ /index.html;`

因为你们前端是单页应用，像 `/forum/posts/1` 这种前端路由在刷新时必须回退到 `index.html`。

#### `proxy_buffering off;`

这是为了支持 AI 接口的流式输出。  
你们后端 `/api/ai/chat/stream`、`/api/ai/analyze-image`、`/api/ai/audit-recycling` 都是 SSE 风格响应，如果 Nginx 缓冲，就会出现前端长时间收不到流式内容的问题。

### 16.4 启用站点配置

先删除默认站点，避免它抢占：

```bash
sudo rm -f /etc/nginx/sites-enabled/default
```

再建立软链接：

```bash
sudo ln -sf /etc/nginx/sites-available/<VM_HOST> /etc/nginx/sites-enabled/<VM_HOST>
```

### 16.5 检查 Nginx 配置语法

执行：

```bash
sudo nginx -t
```

如果成功，你会看到类似：

```text
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 16.6 重启 Nginx

执行：

```bash
sudo systemctl restart nginx
```

如果你想让它开机启动，也可以确认：

```bash
sudo systemctl enable nginx
```

---

## 17. 第十三步：做第一次上线验证

现在开始做验收。

### 17.1 检查 Gunicorn socket

```bash
sudo systemctl status gunicorn.socket
```

### 17.2 检查 Gunicorn service

```bash
sudo systemctl status gunicorn.service
```

### 17.3 检查 Nginx

```bash
sudo systemctl status nginx
```

### 17.4 检查本机健康接口

```bash
curl http://127.0.0.1/api/health
```

或者：

```bash
curl http://localhost/api/health
```

正常应该返回：

```json
{"message":"Backend is running.","service":"carbonsnap-backend","status":"ok"}
```

### 17.5 用浏览器访问公网地址

在你自己的电脑浏览器打开：

```text
http://{VM_NAME}/
```

你应该至少验证以下内容：

1. 首页能打开
2. 刷新页面不会 404
3. 首页健康检查不报错
4. 登录/注册接口能正常请求
5. AI 页面至少能打开
6. 如果模型 key 已配置，AI 聊天或图片分析能返回结果

---

## 18. 第十四步：以后怎么更新部署

后续每次你们改完代码，推荐按下面流程更新服务器。

### 18.1 更新后端代码

```bash
cd ~/CarbonSnap
git pull
```

如果后端依赖变了：

```bash
cd ~/CarbonSnap/backend
source .venv/bin/activate
pip install -r requirements.txt
```

如果数据库模型变了并且仓库里已经有新的 migration：

```bash
flask --app run.py db upgrade
```

然后重启 Gunicorn：

```bash
sudo systemctl restart gunicorn
```

### 18.2 更新前端代码

如果你选择的是“VM 上构建”：

```bash
cd ~/CarbonSnap/frontend
npm ci
npm run build
```

然后重启 Nginx：

```bash
sudo systemctl restart nginx
```

如果你选择的是“本地构建再上传”：

1. 本地 `npm run build`
2. `scp` 覆盖服务器上的 `frontend/dist/`
3. `sudo systemctl restart nginx`

### 18.3 如果 systemd 文件改了

每次修改了：

- `/etc/systemd/system/gunicorn.service`
- `/etc/systemd/system/gunicorn.socket`

都要执行：

```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn.socket
sudo systemctl restart gunicorn.service
```

---

## 19. 常用排错命令

部署时最常用的不是“重试”，而是“看日志”。

### 19.1 Gunicorn 日志

```bash
journalctl -u gunicorn.service -n 100 --no-pager
```

持续跟踪：

```bash
journalctl -u gunicorn.service -f
```

### 19.2 Nginx 错误日志

```bash
sudo tail -n 100 /var/log/nginx/error.log
```

持续跟踪：

```bash
sudo tail -f /var/log/nginx/error.log
```

### 19.3 看端口和 socket

```bash
sudo systemctl status gunicorn.socket
ls -l /run/gunicorn.sock
```

### 19.4 看前端构建结果

```bash
ls -l ~/CarbonSnap/frontend/dist
```

你至少应该看到：

- `index.html`
- `assets/`

---

## 20. 常见问题与对应处理

### 20.1 浏览器打开后是 `502 Bad Gateway`

这通常意味着 Nginx 找不到 Gunicorn。

按顺序检查：

```bash
sudo systemctl status gunicorn.socket
sudo systemctl status gunicorn.service
journalctl -u gunicorn.service -n 100 --no-pager
ls -l /run/gunicorn.sock
```

重点排查：

- `ExecStart` 路径是不是写错
- `.venv` 是否真的在 `/home/student/CarbonSnap/backend/.venv`
- Gunicorn 是否能导入 `run:app`
- `.env` 里是否有格式错误导致 Flask 启动失败

### 20.2 首页能开，但 API 请求失败

先测试：

```bash
curl http://127.0.0.1/api/health
curl http://127.0.0.1/api/auth/me
```

再看 Nginx 配置中是否真的写了：

```nginx
location /api/ { ... }
```

### 20.3 页面空白或静态资源 404

先检查：

```bash
ls -l ~/CarbonSnap/frontend/dist
```

如果没有 `dist`，说明你没 build 前端。

如果 `dist` 存在，再检查 Nginx 的：

```nginx
root /home/student/CarbonSnap/frontend/dist;
```

路径是否写对。

### 20.4 刷新前端子页面出现 404

这是典型的 SPA 回退没有配。

确认 `location /` 里写了：

```nginx
try_files $uri $uri/ /index.html;
```

### 20.5 AI 功能报错，但普通页面没问题

这通常不是部署结构问题，而是后端配置问题。

重点检查：

- `backend/.env` 中模型 API Key 是否有效
- `LLM_PROVIDER` 是否和已填写的 key 对应
- `QWEN_MODEL` 或 `OPENROUTER_MODEL` 是否正确
- 日志中是否出现上游模型错误

### 20.6 图片上传时报 `413 Request Entity Too Large`

说明请求体太大。  
确认 Nginx 配置里有：

```nginx
client_max_body_size 20M;
```

改完后：

```bash
sudo nginx -t
sudo systemctl restart nginx
```

### 20.7 流式 AI 响应一直不出来，最后一次性出来

这是 Nginx 缓冲导致的典型现象。  
确认：

```nginx
proxy_buffering off;
```

已经写在 `/api/` 代理配置里。

### 20.8 数据库相关错误

如果是 SQLite 文件不存在或权限错误，检查：

```bash
ls -l ~/CarbonSnap/data
```

如果数据库文件不存在，重新执行：

```bash
cd ~/CarbonSnap/backend
source .venv/bin/activate
flask --app run.py db upgrade
```

---

## 21. 最后一份可直接照着执行的命令清单

如果你已经理解上面的解释，可以直接按下面这份最短流程做。

### 21.1 初次部署

```bash
ssh student@{VM_NAME}
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip nginx

cd ~
git clone <YOUR_GIT_REPO_URL> CarbonSnap

cd ~/CarbonSnap/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
nano .env

cd ~/CarbonSnap
mkdir -p data/uploads data/faiss

cd ~/CarbonSnap/backend
source .venv/bin/activate
flask --app run.py db upgrade

cd ~/CarbonSnap/frontend
npm ci
npm run build

cd ~/CarbonSnap/backend
nano gunicorn.conf.py
sudo nano /etc/systemd/system/gunicorn.service
sudo nano /etc/systemd/system/gunicorn.socket
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn.socket

sudo nano /etc/nginx/sites-available/{VM_NAME}
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/{VM_NAME} /etc/nginx/sites-enabled/{VM_NAME}
sudo nginx -t
sudo systemctl restart nginx
```

### 21.2 验收

```bash
curl http://127.0.0.1/api/health
sudo systemctl status gunicorn.socket
sudo systemctl status gunicorn.service
sudo systemctl status nginx
journalctl -u gunicorn.service -n 100 --no-pager
```

浏览器访问：

```text
http://{VM_NAME}/
```

---

## 22. 给你们项目的最终建议

对于 `CarbonSnap`，最推荐的正式部署方案就是：

1. `backend/.venv` 管理 Python 依赖
2. `backend/.env` 保存生产环境密钥
3. `flask --app run.py db upgrade` 初始化或升级数据库
4. `frontend/dist` 作为唯一前端上线产物
5. `Nginx` 托管前端并代理 `/api`
6. `Gunicorn + systemd socket` 运行 Flask
7. `data/` 持久化数据库、上传文件和 FAISS 数据

如果你们后面只是为了课程展示与验收，这个方案已经足够稳定、清晰，而且和课程给的 Part 1 / Part 2 思路完全一致，只是把它扩展成了适合你们仓库的版本。

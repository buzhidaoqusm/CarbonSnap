> **⚠️ 已过时，仅供参考（2026-10-20）**：课程 VM 已经停用。本文写于后端还是 Flask + SQLite、
> 由 Gunicorn 运行 `run.py` 的时候；现在后端是 FastAPI + PostgreSQL，用 uvicorn 运行，`run.py` 已删除，
> 迁移命令也变成了 `alembic -c migrations/alembic.ini upgrade head`，文中的大部分命令都已经无法执行。
> 本地运行请看仓库根目录的 `README.md`。

``` commands
ssh <UCD_USERNAME>@<RDP_HOST>
ssh student@<VM_HOST>
<VM_PASSWORD>

cd ~/CarbonSnap/
git pull

<GITHUB_USERNAME>
<GITHUB_TOKEN>

cd frontend
npm ci
npm run build

cd ../backend
source .venv/bin/activate
pip install -r requirements.txt
flask --app run.py db upgrade

sudo systemctl daemon-reload
sudo systemctl restart gunicorn.service
sudo nginx -t
sudo systemctl reload nginx

https://<VM_HOST>/
```
# 测试命令速查

## 后端（在 `backend/` 下）

测试跑在 PostgreSQL 上，先在仓库根目录启动它（Docker Desktop 要先开）：

```bash
docker compose up -d postgres
```

```bash
uv sync                       # 首次 / 依赖变了之后
uv run ruff check .           # lint
uv run ruff format --check .  # 格式（去掉 --check 就是自动格式化）
uv run mypy                   # 类型检查
uv run pytest -q              # 全量测试，本机约 5–7 分钟
```

提交前一条跑完：

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q
```

只跑一部分：

```bash
uv run pytest tests/unit -q                                   # 只跑单元测试
uv run pytest tests/unit/test_tool_selection_shadow.py -q     # 单个文件
uv run pytest -k "auth" -q                                    # 按名字匹配
uv run pytest -x --lf -q                                      # 只重跑上次失败的，遇错即停
```

测试每次运行会重建 `carbonsnap_test` 库（名字必须以 `_test` 结尾，否则拒绝运行），每个测试结束后回滚，
并拦截外网请求；不会碰开发库 `carbonsnap`，也不需要 `.env`。换一个库：`TEST_DATABASE_URL=postgresql+psycopg://...`。

**不要同时跑两个 pytest**：第二个会把第一个正在用的测试库删掉重建。

本机连 PG 一律用 `127.0.0.1`，不要用 `localhost`：Windows 上 `localhost` 先试 IPv6 `::1`，
compose 只绑定了 IPv4，每个新连接都会卡到 TCP 超时（实测 130 秒以上）才回落。

SQLite 和 PG 的行为对比（外键、长度、类型、并发写）：

```bash
uv run python ../tools/db_compare.py sqlite:///../data/compare.db
uv run python ../tools/db_compare.py postgresql+psycopg://carbonsnap:carbonsnap@127.0.0.1:5432/compare
```

## 前端（在 `frontend/` 下）

```bash
npm ci                                  # 首次 / 依赖变了之后
npm run test                            # 全量 vitest
npx vitest run tests/unit/auth-api.spec.js   # 单个文件
npm run build                           # 确认能打包
```

## Docker（在仓库根目录，需先启动 Docker Desktop）

启动并冒烟测试：

```bash
docker compose up -d --build
curl http://127.0.0.1:5000/api/health
docker compose logs api --tail 50       # 起不来时看这里
docker compose exec postgres psql -U carbonsnap   # 直接查库
docker compose down                     # 加 -v 会连同 PG 数据一起删掉
```

## 压测（在仓库根目录）

```bash
docker compose -f docker-compose.yml -f docker-compose.bench.yml --profile bench up -d --build
uv run --no-project --with locust locust -f tools/load_test/locustfile.py --host http://127.0.0.1:5000 --headless --users 20 --spawn-rate 2 --run-time 2m --only-summary
docker compose -f docker-compose.yml -f docker-compose.bench.yml --profile bench down
docker volume rm carbonsnap_bench-data carbonsnap_bench-postgres-data
```

`--users` 分别取 1 / 3 / 10 / 20，结果记入 [benchmarks.md](benchmarks.md)。压测用独立的数据卷（上传目录和 PG 数据目录都是），不会写入开发库。**不要用 `down -v`**：它会删掉项目里所有数据卷，包括开发库 `postgres-data`。逐个问题的复现实验见 [PERFORMANCE_ISSUES.md](PERFORMANCE_ISSUES.md)。

## 本地开发库恢复演示数据（在 `backend/` 下，PG 要先启动）

```bash
uv run flask --app "app:create_app()" db upgrade   # 空库先建表
uv run python scripts/reset_all_data.py
uv run python scripts/seed_example_data.py
```

## CI

```bash
gh run list --limit 5          # 最近几次运行
gh run view <run-id> --log-failed   # 只看失败步骤的日志
```

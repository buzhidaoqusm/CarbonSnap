# 测试命令速查

## 后端（在 `backend/` 下）

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

测试会自动使用临时数据库并拦截外网请求，不会碰 `data/carbonsnap.db`，也不需要 `.env`。

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
docker compose down
```

## 压测（在仓库根目录）

```bash
docker compose -f docker-compose.yml -f docker-compose.bench.yml --profile bench up -d --build
uv run --no-project --with locust locust -f tools/load_test/locustfile.py --host http://127.0.0.1:5000 --headless --users 20 --spawn-rate 2 --run-time 2m --only-summary
docker compose -f docker-compose.yml -f docker-compose.bench.yml --profile bench down -v
```

`--users` 分别取 1 / 3 / 10 / 20，结果记入 [benchmarks.md](benchmarks.md)。压测用独立的数据卷，不会写入开发库。逐个问题的复现实验见 [PERFORMANCE_ISSUES.md](PERFORMANCE_ISSUES.md)。

## 本地开发库恢复演示数据（在 `backend/` 下）

```bash
uv run python scripts/reset_all_data.py
uv run python scripts/seed_example_data.py
```

## CI

```bash
gh run list --limit 5          # 最近几次运行
gh run view <run-id> --log-failed   # 只看失败步骤的日志
```

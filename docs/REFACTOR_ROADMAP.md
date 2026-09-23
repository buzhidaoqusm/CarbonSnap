# CarbonSnap 重构路线图（面向 Agent 应用开发岗）

> 生成日期：2026-09-19
>
> 这份是**执行计划**：按阶段排序，每个阶段有任务清单、验收标准和面试要点。
> AI 层的问题清单与编号（A1–G4）见 [AI_AGENT_IMPROVEMENT_PLAN.md](AI_AGENT_IMPROVEMENT_PLAN.md)，本文引用时写作「旧计划 A4」。

---

## 0. 总览

| 阶段 | 主题 | 预计时间 | 做完后简历能多写什么 |
|---|---|---|---|
| P0 | 工程地基 | 3–4 天 | Docker Compose、CI、压测基线 |
| P1 | 后端底座迁移 | 3 周 | FastAPI + async SQLAlchemy + PostgreSQL，从 Flask 渐进式迁移 |
| P2 | Agent 上主路径 | 2–3 周 | 统一 LangGraph 主图、checkpointer、`interrupt()` 人工审批、LLM 网关 |
| P3 | MCP、可观测、安全 | 1.5 周 | MCP server、Langfuse、限流、输入/输出双侧 guardrail |
| P4 | 评测与检索质量 | 2 周 | 真实评测集、LLM-as-judge、pgvector + rerank、CI 评测门禁 |
| P5 | 收尾与展示 | 1 周 | 公网 demo、压测对比数字、README、ADR |

合计约 10–11 周（按全职投入估算，兼职按比例拉长）。时间不够时的裁剪方案见第 8 节。

**四条原则**

1. 每个阶段结束时项目都能跑、测试是绿的。不做大爆炸式重写。
2. 每个任务一个分支 + PR + 有意义的 commit。git 历史本身就是简历的一部分。
3. 所有"提升了 X%"都必须来自脚本跑出的真实数字。**先测基线，再改。**
4. 每个重大技术选型写一篇短 ADR（`docs/adr/`），这同时也是面试准备。

---

## 1. 目标架构

### 1.1 请求链路

```text
Vue 前端 ──SSE──▶ FastAPI (/api/v1)
                    │
                    ├─ 业务路由 (forum/market/ledger/project/...)
                    │     └─ Service ─ Repository ─ PostgreSQL
                    │
                    └─ /ai/chat/stream ──▶ LangGraph 主图 (AsyncPostgresSaver)
                          START → load_context → guard_input → route
                                 ├─ clarify              (interrupt: 等用户选择)
                                 ├─ recycling 子图        (interrupt: 等位置)
                                 └─ agent ⇄ tools         (工具经 MCP client 调用)
                          → guard_output → persist → END

LLM 网关   AsyncOpenAI：超时 / 重试 / 主备降级 / 结构化输出 / 用量统计
MCP server 7 个业务工具，对内给 agent 用，对外给 Claude Desktop 等客户端用
Redis      限流、每日配额、embedding 缓存、Celery broker
Langfuse   trace、token、成本、延迟
```

### 1.2 目录结构（迁移完成后）

```text
backend/
  app/
    main.py              FastAPI 入口
    core/                config (pydantic-settings)、logging、security (JWT)、errors
    db/                  base、session、models/
    api/v1/              各模块 router
    schemas/             Pydantic 请求/响应模型
    repositories/
    services/            业务服务 (forum、market、ledger ...)
    agent/
      graph.py           主图
      state.py
      nodes/             route、guard、agent、tools、persist
      subgraphs/recycling.py
      prompts/           带版本号的 prompt 正文
    llm/                 provider 网关
    tools/               工具实现 + MCP server
    retrieval/           chunking、embedding、pgvector、关键词、融合、rerank
    memory/
    guardrails/
    observability/
    workers/             Celery 任务
  evals/                 datasets、runners、judges、reports
  tests/
docker-compose.yml
.github/workflows/ci.yml
docs/adr/
```

---

## 2. P0 工程地基（3–4 天）

> ✅ **已完成（2026-09-23）**，除 0.6 的基线实测外。提交见 `24bc36c..bed2639`。
> 过程中多出来的工作：后端 12 个、前端 18 个失败测试全部修复（它们依赖开发者本机的
> `.env` 和真实网络），现在后端 515、前端 84 全绿。
> **待办**：0.6 的基线数字需要 Linux 或 Docker（gunicorn 不支持 Windows），
> 见 `docs/benchmarks.md` 里空着的表格。

- [x] **0.1 提交现有改动**：未提交的 A6/A7 工作拆成 2–3 个 commit（shadow 模块 + 测试 / 接入 conversation service / 报告脚本 + 文档）。
- [x] **0.2 依赖管理换成 uv**：`backend/pyproject.toml` + `uv.lock`，替代 `requirements.txt`。Python 固定 3.12（本机系统 Python 是 3.14，部分依赖可能没有对应 wheel）。删除损坏的 `.venv`（指向已不存在的 `D:\anaconda3`）并重建。
- [x] **0.3 容器化**：
  - `backend/Dockerfile`：多阶段构建，非 root 用户运行。
  - 根目录 `docker-compose.yml`：`api`、`postgres`（直接用 `pgvector/pgvector:pg16` 镜像，P4 用得上）、`redis`、`neo4j`（放在可选 profile 里）。
  - 前端暂时保持本地 `vite`。
- [x] **0.4 代码质量**：ruff（lint + format）、mypy（先只检查 `app/services/ai`，逐步扩大范围）、pre-commit。
- [x] **0.5 CI**：GitHub Actions `ci.yml`，依次跑 ruff → mypy → pytest → vitest。
- [~] **0.6 压测基线**（工具就绪，数字待测）（后面做对比全靠它）：
  - 写一个假的 OpenAI 兼容服务 `tools/fake_llm/`：固定延迟，按固定速度流式吐 token。压测不花钱，结果可复现。
  - 用 locust 压 `/api/ai/chat/stream`，记录最大并发流式会话数、p50/p95 首 token 延迟、错误率。
  - 结果写进 `docs/benchmarks.md`。
- [x] **0.7 修掉已知失败的测试**（实际修了 30 个）：`test_ai_decision_engine.py::TestForumRetrieval::test_recycling_intents_enable_forum_retrieval`。
- [x] **0.8 顺手修安全问题**（旧计划 D3、D4）：
  - `/ai/analyze-image`、`/ai/location-context`、`/ai/chat/resume` 补鉴权。
  - SSE 出错时不再把异常原文发给前端，只返回通用错误码；详细信息只写服务端日志。

**验收**
- `docker compose up` 一条命令拉起全部服务。
- CI 在 PR 上是绿的。
- `docs/benchmarks.md` 里有基线数字。

**面试点**
- 为什么压测要用假 LLM（隔离外部依赖、结果可复现、不花钱）。

---

## 3. P1 后端底座迁移：Flask → FastAPI（3 周）

**策略：绞杀者模式（strangler fig）。**
- FastAPI 作为新入口，用 `a2wsgi` 把旧 Flask app 挂在它下面。
- 每迁完一个模块，就在 FastAPI 注册对应路由，并从 Flask 删掉。
- URL 保持 `/api/...` 不变，前端不用改。
- 每一步都能上线、测试都是绿的。

### 3.1 配置解耦（2 天）

- 新建 `app/core/config.py`：`Settings(BaseSettings)`，把 `app/config/settings.py` 里的 60 多个配置项搬过去，带上类型和默认值；`get_settings()` 用 `lru_cache` 缓存。
- 把 43 个文件里 96 处 `current_app.config.get(...)` 换成 `get_settings().xxx`。这是和 Flask 解耦的第一步。
- 过渡期让 `load_app_settings()` 从 `Settings` 回填 `app.config`，Flask 照常能跑。
- 测试：在 `conftest.py` 里用 fixture 覆盖 settings，替代现在的 `flask_app.config.update(...)`。

### 3.2 SQLite → PostgreSQL（2 天）

- `DATABASE_URL` 指向 compose 里的 PG，在 PG 上把全部 Alembic 迁移跑一遍，修掉 SQLite 专属写法（`batch_alter_table` 在 PG 上也能用，重点检查 JSON、布尔和日期字段）。
- 数据直接用现有 seed 脚本重建。
- 测试库：CI 用 GitHub Actions 的 postgres service，本地用 compose 里的 PG。每个测试用事务回滚，替代现在的 `drop_all/create_all`。

### 3.3 数据层与 Flask 解耦（4 天）

- 新建 `app/db/base.py`，定义 `class Base(DeclarativeBase)`。过渡期用 `db = SQLAlchemy(model_class=Base)`，让 Flask 和 FastAPI 共用同一套模型。
- 11 个 models 文件改成 SQLAlchemy 2.0 的类型写法（`Mapped[...]` + `mapped_column`）。
- 新建 `app/db/session.py`：async engine（asyncpg）+ `async_sessionmaker`。FastAPI 用依赖 `get_db()` 注入 `AsyncSession`。
- repositories 改成接收 session 参数并 async 化（共 12 个文件，都很薄）。

### 3.4 路由迁移（1.5 周）

从简单到复杂，每迁一个模块开一个 PR：

1. `health`、`notification`：先建立统一模式（router + Pydantic schema + 依赖注入 + 统一错误响应）。
2. `profile/auth`：JWT 改用 PyJWT，加 `get_current_user` 依赖。token 格式保持兼容，已登录的用户不会掉线。
3. `ledger`、`project`、`market`、`forum`、`uploads`。
4. `ai/memory`。
5. `ai/chat` 最后迁：它依赖 P2 的 async LLM 网关。过渡期可以用 `run_in_threadpool` 包住旧的同步代码。

同时要做：
- 每个接口都写 Pydantic 请求/响应模型，自动生成 OpenAPI 文档（`/docs`），这本身就是展示点。
- 统一响应格式沿用 `app/utils/response.py` 的结构，改用 exception handler 实现。
- 测试迁移：`app.test_client()` 换成 `httpx.AsyncClient(transport=ASGITransport(app))`，13 个集成测试文件逐个改。
- 论坛后台索引任务：`ThreadPoolExecutor(max_workers=1)` 换成 Celery（Redis 做 broker），带重试；worker 作为 compose 里的独立服务。
- 迁完后删除 Flask、Flask-* 和 a2wsgi 依赖，gunicorn sync worker 换成 uvicorn 多 worker。

**验收**
- 代码里不再有 Flask。
- `/docs` 能看到全部接口。
- 全部测试在 PG 上通过。
- 前端不改代码也能正常使用。

**面试点**
- 为什么要迁：拿 P0 的压测数字说话（3 个 sync worker 被流式长连接占满）。
- 渐进式迁移怎么保证不停服、不破坏前端。
- async 里什么会阻塞事件循环：同步 SDK、CPU 密集的向量计算。怎么发现，怎么处理（`run_in_threadpool` 或进程池）。
- `AsyncSession` 的生命周期，连接池大小怎么定。

---

## 4. P2 Agent 上主路径（2–3 周）

> 现状：前端只调用 `/api/ai/chat/stream`，而模型驱动的 tool-calling 环路和 A6/A7 灰度只接在非流式路径上，用户实际用不到。主图是直线，回收分析是 1555 行写死的流程，"等位置"的暂停/恢复靠进程内的 dict。这个阶段就是把这些都收拢到一张真正的图里。

### 4.1 LLM 网关层（3 天，旧计划 B1–B5）

- 新建 `app/llm/`，基于 `AsyncOpenAI`，统一提供 `chat()`、`stream()`、`structured()`、`embed()` 四个接口。
- 超时（连接和读取分开设）；用 tenacity 做指数退避重试，只重试 429、5xx 和超时；主备 provider 自动降级（OpenRouter ⇄ Qwen）。
- 结构化输出：router、memory extractor、回收分析 stage1 改用 `response_format=json_schema` + Pydantic 校验，删掉正则抠 JSON 的逻辑。**记录改造前后的 JSON 解析失败率。**
- 每次调用记录 model、tokens、延迟和成本，供 P3 的 Langfuse 使用。

### 4.2 统一主图（1 周，旧计划 A2、A6、A9）

- 新建 `app/agent/graph.py`，把现在分散的三条路径（线性 decision engine、graph agent、tool-calling 环路）合成一张图，结构见 1.1。
- **回收分析做成子图，保持 workflow 形态**（步骤固定、结果可预测），不要硬塞进 agent 环路。把 `recycling_analysis_service.py` 拆成子图节点：`analyze_stage1` → `check_location` → `nearby_search` → `summarize`。
- 流式输出：
  - 用 `graph.astream(stream_mode=["updates", "custom"])`。
  - LLM 的 token 在网关里通过 `get_stream_writer()` 以 custom 模式发出。`messages` 模式只能自动捕获 LangChain 模型的 token，我们用的是原生 SDK。
  - 在 SSE 层映射成现有的事件协议（`meta` / `stage_start` / `delta` / `done` ...），前端基本不用改。
- 工具并行：同一轮的多个 tool_call 用 `asyncio.gather` 并行执行。
- 灰度：保留 `AI_TOOL_SELECTION_MODE` 的 rule / shadow / model 三种模式。先用 shadow 采集数据，用 `tool_selection_shadow_report.py` 出一致率，再切到 model。
- 清理：
  - 新图稳定后，删除旧的线性路径。
  - `demo_seed_replay_service.py`（1031 行）移出主路径，改成只在开发环境可用的脚本。

### 4.3 Checkpointer + 人工介入（4 天，旧计划 A4、A5）

- 用 `AsyncPostgresSaver`（`langgraph-checkpoint-postgres`），`thread_id = conversation_id`。
- 业务表（`ai_conversations` / `ai_messages`）仍然是前端展示对话历史的数据源，checkpointer 只存 agent 的运行状态。两者的分工写进 ADR。
- 三个 `interrupt()` 场景：
  1. **等位置**：替换现在手写的 `awaiting_location` + 进程内 `_SESSION_STORE` + `/ai/chat/resume`。这是最有说服力的一个：原实现在多 worker 下会丢状态，换成 checkpointer 后这个问题自然消失。
  2. **澄清**：`clarify` 节点 interrupt，用户选的选项作为 resume 的值。
  3. **高风险工具审批**：`record_recycling_completion` 不再直接拒绝，而是 interrupt 等用户确认，确认后用 `Command(resume={"approved": True})` 继续执行。
- 新增接口：
  - `POST /api/v1/ai/threads/{thread_id}/resume`：恢复执行。
  - `GET /api/v1/ai/threads/{thread_id}/state`：刷新页面后恢复待确认的状态。

### 4.4 记忆（2 天）

- 短期记忆：交给 checkpointer 里的消息状态；超过 N 轮时用 LLM 对早期对话做摘要压缩。
- 长期记忆：保留现有的 `user_memory_items`。抽取改用结构化输出；读取通过已有的 `read_user_memory` 工具由模型按需调用。

**验收**
- 前端走的流式路径就是 LangGraph 主图，trace 面板能看到节点和工具调用。
- `_SESSION_STORE` 被删除。写一个集成测试：会话在"等位置"时，换一个 worker 也能恢复。
- 高风险工具审批有端到端测试。
- shadow 报告里有真实数字。

**面试点**
- 为什么回收分析用 workflow、通用问答用 agent。
- `interrupt()` 怎么实现的（checkpoint + 恢复时节点从头重新执行）→ 所以 interrupt 之前的副作用必须幂等。
- 模型一直调工具不收敛怎么办（`max_iterations` + 到上限强制出答案）。

---

## 5. P3 MCP、可观测、安全（1.5 周）

### 5.1 MCP（4 天）

- 新建 `app/tools/mcp_server.py`：用官方 `mcp` Python SDK（FastMCP）把 7 个工具暴露为 MCP server，挂在 `/mcp`（streamable HTTP 传输）。
- 工具定义只保留一份：`tool_registry` 是唯一来源，MCP 和 agent 都从它生成。
- 风险等级映射成 MCP tool annotations（`readOnlyHint` / `destructiveHint`）。
- 鉴权：MCP 请求带用户 JWT，服务端从 token 解析 `user_id` 并注入工具参数。**不让模型传 `user_id`。**
- agent 侧通过 MCP client 加载工具（`langchain-mcp-adapters` 或 SDK 自带的 client）；支持在配置里挂外部 MCP server。
- 演示：用 MCP Inspector 或 Claude Desktop 连上你的 server 调用工具，录一段 GIF 放进 README。

### 5.2 可观测（3 天，旧计划 F1、F2、F4）

- Langfuse：
  - LangGraph 节点通过 Langfuse 的 callback handler 接入；OpenAI 调用用 Langfuse 的 openai 包装。
  - 每次对话一条 trace，能看到节点、工具、token、成本和延迟。
  - 部署用 Langfuse Cloud 免费档最省事。v3 自托管需要 ClickHouse、Redis 和对象存储，本地跑太重。
- 自建的 Agent Trace 面板保留（它是产品功能）。面试可以讲它和 Langfuse 各自负责什么。
- structlog 输出 JSON 日志；中间件生成 request_id，贯穿 API → agent → LLM → 工具，并写进 Langfuse trace 的 metadata。
- Prompt 版本化：prompt 正文移到 `app/agent/prompts/`，带版本号；trace 里记录每次用的是哪个版本。

### 5.3 安全与限流（3 天，旧计划 B7、D1、D2、D5、D6）

- 限流：slowapi + Redis，按用户和 IP 限流；每个用户每天的 token 配额用 Redis 计数。
- guardrail 做双侧：
  - 输入侧：关键词快筛 + 小模型结构化判别 prompt injection。
  - 输出侧：检查是否泄露 system prompt、是否有有害内容。
  - 检索文本侧保留现有逻辑。
- 图片上传：校验大小和 MIME 类型。
- 记忆写入前做 PII 检测（手机号、邮箱等），命中则脱敏。

**验收**
- 外部 MCP 客户端能调用工具。
- Langfuse 能看到完整 trace 和成本。
- guardrail 在对抗样本上的召回率有数字（数据集在 P4）。

---

## 6. P4 评测与检索质量（2 周）

### 6.1 评测体系（1 周，旧计划 E1–E6）

目录 `backend/evals/`，下分 `datasets/`、`runners/`、`judges/`、`reports/`。

数据集从现在的 9 条扩到 60–100 条：

| 类别 | 条数 | 检查什么 |
|---|---|---|
| 回收识别（文字/图片） | 15 | 路由、材质判断 |
| 多轮追问 | 10 | 是否正确使用上下文 |
| 需要澄清 | 8 | 是否触发 clarify |
| 需要位置 | 8 | 是否 interrupt |
| 论坛/图谱知识问答 | 15 | 引用是否正确、回答是否忠实于来源 |
| 高风险写操作 | 6 | 是否走审批 |
| 注入/越狱 | 12 | guardrail 是否拦截 |
| 工具失败/依赖不可用 | 6 | 降级是否合理 |

- **真实 runner**：跑真正的主图 + 真实 LLM；结果按输入哈希缓存，只有改了 prompt 才重跑，控制成本。
- **指标**：路由准确率、工具选择 F1、任务成功率、引用准确率、忠实度、guardrail 召回率/误拦率、p50/p95 延迟、单条平均成本。
- **LLM-as-judge**：
  - 用和被测模型不同的模型做裁判，按 rubric 输出结构化分数。
  - **先人工标注 20 条，算出裁判和人工的一致率**，证明裁判可信。
- **CI**：PR 上跑 15 条冒烟集（缓存命中时不花钱）；主分支或手动触发时跑全量。关键指标低于阈值则 CI 失败。
- **产出** `docs/evaluation.md`：方法、数据集说明、每次改造前后的对比表。

### 6.2 检索升级（1 周，旧计划 C1–C9）

- **向量**：FAISS + JSON manifest 换成 pgvector（HNSW 索引）。向量和业务数据放同一个库，不再自己维护索引文件。
- **关键词**：现在是 Python 全表扫描，换成 PostgreSQL 全文检索。中文先用 jieba 分词，写入 `simple` 配置的 tsvector 列 + GIN 索引。
- **跨语言**：用多语言 embedding（如 bge-m3 或 DashScope text-embedding-v3），删除硬编码的中英查询扩展表。
- **重排**：召回后接 reranker（DashScope gte-rerank API 或本地 bge-reranker）。
- **缓存**：查询 embedding 缓存到 Redis。
- **引用**：模型通过结构化输出返回 `used_reference_ids`，替代现在的子串匹配。
- **检索评测**：
  - 标注 40 条 query → 相关帖子的 golden 集。
  - 指标：recall@k、MRR、nDCG。
  - 消融实验：仅关键词 / 仅向量 / RRF / RRF + rerank / 不同 chunk 大小。

**验收**
- `docs/evaluation.md` 里有完整数字。
- CI 有评测门禁。

---

## 7. P5 收尾与展示（1 周）

- [ ] **压测复测**：用 P0 同一套 locust 脚本对比 Flask sync 和 FastAPI async，数字写进 `docs/benchmarks.md`。
- [ ] **公网 demo**：云服务器 + docker compose + Caddy（自动 HTTPS）；准备演示账号和演示数据。
- [ ] **README 重写**：架构图、30 秒 demo GIF、关键指标、快速启动。
- [ ] **ADR**（`docs/adr/`），至少 5 篇：
  1. 为什么从 Flask 迁到 FastAPI
  2. pgvector 还是 Milvus
  3. 回收流程为什么用 workflow 而不是 agent
  4. 为什么用 MCP 暴露工具
  5. LLM-as-judge 的可信度怎么验证
- [ ] **可选**：supervisor 多 agent（回收专家 / 社区检索 / 地图定位）。只在前面都完成后才做。

---

## 8. 时间不够时怎么裁剪

| 可用时间 | 做什么 |
|---|---|
| 4 周 | P0 → P1 精简版（只做 3.1、3.2 和路由迁移；repository 保持同步，路由用 `def` 跑在线程池）→ P2 的 4.2、4.3 → P4 的 6.1 精简版（30 条） |
| 6–7 周 | 4 周方案 + P2 完整 + P3 的 MCP 和 Langfuse + P4 完整 |
| 10 周以上 | 全部 |

**优先级：agent 上主路径 + 人工介入 + 真实评测 > FastAPI 迁移 > MCP > 其他。** 前三项决定面试能不能扛住深挖。

---

## 9. 前端需要配合的改动

- 新增审批卡片组件（高风险工具确认）。
- 处理 `interrupt` 事件；位置恢复改走 `/threads/{id}/resume`。
- 刷新页面后调用 `/threads/{id}/state`，恢复待处理的 interrupt。
- 如果 API 前缀改成 `/api/v1`，修改 `frontend/src/api/http.js` 和 `frontend/src/api/ai/chat.js` 里的路径。
- 其他页面不动。

---

## 10. 简历条目模板

> 数字全部来自 `docs/evaluation.md` 和 `docs/benchmarks.md`，没跑出来之前不要写。

- 基于 FastAPI + LangGraph 构建 tool-calling agent。用 PostgresSaver 持久化 agent 状态，对高风险写操作通过 `interrupt()` 实现人工审批与断点续跑。
- 把业务工具封装为 MCP server；通过 shadow 灰度对比规则选择（v1）和模型选择（v2），工具选择一致率 X%，据此完成全量切换。
- hybrid 检索（PG 全文 + pgvector，RRF 融合）+ reranker，recall@5 从 X 提升到 Y。
- 自建评测体系：N 条标注集 + LLM-as-judge（与人工一致率 Z%）+ CI 回归门禁；用 Langfuse 追踪 p95 延迟和单次对话成本。
- 将同步 Flask 单体渐进式迁移到异步 FastAPI + PostgreSQL，进程内状态外置到 Redis/Postgres；同等资源下并发流式会话从 X 提升到 Y。

---

## 11. 面试高频追问（每个阶段结束时自测）

- LangGraph `interrupt()` 恢复时节点会从头重新执行，你怎么处理副作用？
- 模型一直调工具不收敛怎么办？
- 工具参数里的 `user_id` 为什么不能让模型传？
- LLM-as-judge 怎么证明可信？
- RRF 里的 k 是什么意思？为什么不用加权求和？
- async 函数里调用同步代码会怎样？怎么发现？
- Postgres checkpointer 的数据会无限增长吗？怎么清理？
- 流式输出中途 LLM 报错，前端和数据库分别处于什么状态？
- MCP 和直接用 function calling 有什么区别？
- shadow 模式多花了多少成本？值不值？

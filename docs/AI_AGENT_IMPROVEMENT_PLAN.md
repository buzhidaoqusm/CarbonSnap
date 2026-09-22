# CarbonSnap AI/Agent 改进计划（Improvement Plan）

> 目标：把当前项目从"看得出是课设"提升为"能写进简历、经得起 AI 应用开发岗深挖"的成熟项目。
> 本文档聚焦 **AI / Agent 技术栈**，按主题分组，标注 **优先级 / 工作量 / 面试叙事价值**，作为后续改造的执行清单。
>
> 生成日期：2026-07-17　范围：`backend/app/services/ai/`、`backend/app/ai/`、`backend/app/api/ai/`、`frontend/src/**/ai`

---

## 0. 总体判断（先读这段）

- **技术栈选型不落伍**：LangGraph、FAISS、Neo4j GraphRAG、hybrid RAG（RRF 融合）、意图路由、shadow 灰度、trace 可观测——这些都是企业在用的主流构件，方向对。
- **真正的差距是：当前系统是"工作流（workflow）"而不是"agent"**。核心症结——**模型没有决策权**：工具由 `if-else` 规则选择，LLM 从未见过工具定义，LangGraph 图是一条没有环的直线。
- **第二个差距是工程健壮性与评测**：LLM 调用无 timeout/retry、结构化输出靠正则、eval 是 mock（断言全 1.0）、无业界可观测工具。
- **值得保留的亮点**（改造时不要丢，面试要主动讲）：decision engine 的 compat/shadow/llm_first 三模式灰度、逐层 fallback 留痕、工具风险分级、丰富的 trace schema、RRF 混合检索、OSM 工具的完整重试/退避/降级。

---

## ✅ 进度：A1–A3 已完成（2026-07-17）

模型驱动的 tool-calling agent 环路已落地并测试通过。新增/改动：

- `backend/app/services/ai/openrouter_service.py` — 新增 `complete_with_tools()`：native OpenAI tool calling（把工具 schema 通过 `tools=` 交给模型），带 timeout（`AI_LLM_TIMEOUT_SECONDS`）。
- `backend/app/services/ai/tool_registry.py` — 新增 `to_openai_tools()`（工具 schema 导出为 OpenAI 格式）+ `execute_tool_call()`（注入 user_id/坐标等上下文、复用 `run_tool` 的风险分级门控）。
- `backend/app/services/ai/tool_calling_agent.py`（新）— 真正的 LangGraph `agent ⇄ tools` 环路（`StateGraph` + `tools→agent` 回边），带 `max_iterations` 上限与"到顶强制出文本答案"的收敛保护；`completion_fn`/`execute_fn`/`tools` 全部可注入以便隔离测试；输出结构化 `tool_trace`。
- `backend/app/services/ai/ai_conversation_service.py` — 新增 `complete_tool_calling_agent_message()`：把环路接入 general-chat 持久化路径，工具由**模型选择**而非规则预注入；把真实 `tool_trace` 写入 trace 供 Agent Trace 面板展示。
- `backend/app/services/ai/langgraph_agent.py` — general 节点在 `AI_TOOL_CALLING_AGENT_ENABLED` 打开时改走环路（默认关，保证既有行为与测试不变）。
- 配置：`AI_TOOL_CALLING_AGENT_ENABLED` / `AI_AGENT_MAX_ITERATIONS` / `AI_LLM_TIMEOUT_SECONDS`（`settings.py` + `.env.example`）。
- 测试：`test_tool_calling_agent.py`（环路单测，注入 fake）、`test_openrouter_tool_calling.py`（provider 原语）、`test_tool_registry_openai_tools.py`（schema+执行器）、`test_tool_calling_agent_integration.py`（**真实组合**：真 provider+真 registry+真环路，仅 mock 最底层 client；含 high-risk 门控与"Graph Agent 全链路+持久化"两个端到端用例）。

> 说明：本增量刻意保持 `AI_TOOL_CALLING_AGENT_ENABLED` 默认关闭以不破坏既有 465 测试；把它设为主路径 + 用 shadow 对比规则 v1/模型 v2（见 A6/A7）留作下一步。
> 遗留：`test_ai_decision_engine.py::TestForumRetrieval::test_recycling_intents_enable_forum_retrieval` 为**改动前既有**失败（`AI_TRACE_ENABLED` 配置相关，已用 git stash 验证与本次改动无关）。

---

## ✅ 进度：A6–A7 已完成（2026-07-18）

把"规则驱动 → 模型驱动"做成了可灰度、可度量的上线路径，复用 decision engine 的三模式思路。

- `backend/app/services/ai/tool_selection_shadow.py`（新）— 工具选择灰度核心：
  - `resolve_tool_selection_mode()` → `rule`（v1，默认）/ `model`（v2，A6）/ `shadow`（A7）；空值回退到旧的 `AI_TOOL_CALLING_AGENT_ENABLED`（true→model），保证既有 flag 不失效。
  - `rule_tool_selection()`（v1 规则选择）、`model_tool_selection()`（v2 仅选择、不执行的单次模型调用）、`compare_tool_selections()`（matched / rule_only / model_only / exact_match / jaccard）、`record_shadow_comparison()`（best-effort 追加 JSONL，绝不阻断服务）。
- `backend/app/services/ai/ai_conversation_service.py` — 新增 `complete_general_chat_with_mode()`（general 路径的模式入口）：
  - `model` 模式：走模型环路服务用户，**零额外成本**地把"模型实际调用的工具"与"规则会选的工具"对比（A6 主路径 + A7 度量）。
  - `shadow` 模式：仍由安全的规则路径服务，另跑一次不执行的模型选择调用，记录分歧（A7 上线前取证）。
  - `rule` 模式：完全等价于既有 `complete_chat_message`（默认，行为不变）。
- `backend/app/services/ai/langgraph_agent.py` — general 节点统一改走 `complete_general_chat_with_mode()`（移除旧的布尔分支）。
- 配置：`AI_TOOL_SELECTION_MODE`、`AI_TOOL_SELECTION_SHADOW_LOG`（默认空=不落盘，opt-in）（`settings.py` + `.env.example`）。
- 报告：`backend/scripts/tool_selection_shadow_report.py` — 把 JSONL 聚合成"规则 vs 模型工具选择一致率"的真实数字（exact-match 率、mean Jaccard、逐工具一致率、Top 分歧），支撑"X%→Y% 后全量"的叙事。
- 测试：`test_tool_selection_shadow.py`（14 项：模式解析、对比指标、两种选择策略、JSONL 落盘、三模式 orchestrator 分发）。

> 说明：默认仍为 `rule`——正确的灰度姿势是先用 `shadow` 采集证据、再凭数字 flip 到 `model`，而不是一上来硬切默认（也避免破坏既有测试与依赖真实 LLM）。A6/A7 的价值正是把这条"有据可依的全量"路径本身建好。

---

## A. Agent 架构（核心，最高优先级）

> 这一组决定"到底是不是 agent"。P0 全部集中在这里。

### A1. 工具选择是 if-else，不是模型驱动 ⭐️ 最关键
- **现状**：`tool_registry.py:88 select_tools_for_decision()` 用纯规则匹配 intent → 追加工具；`openrouter_service.py:400 _send_completion_request()` 从不传 `tools=` 参数。每个工具的 JSON Schema（`tool_registry.py:139` 起）写得很规范，但**从未发给过模型**。
- **问题**：面试问"你的 agent 怎么决定调用哪个工具"，答案是"if 语句"，agent 叙事当场崩塌。
- **改法**：把工具 schema 通过 `tools=` 交给模型，用 native tool calling 让模型发起 tool_call。
- **优先级 P0｜工作量 中｜叙事价值 极高**

### A2. LangGraph 图是线性 DAG，没有 agent loop（无环）
- **现状**：`langgraph_agent.py:148 build_graph_agent()` 结构为 `START → route_intent → select_tools → {clarify|recycling|general} → END`，是一条直线。用三个普通函数顺序调用即可复现，LangGraph 沦为装饰。
- **改法**：改成真正的 agent 环：`agent`(带 tools 调模型) → 条件边判断有无 tool_call → `tools`(执行) → 回到 `agent`，设 `max_iterations` 上限防死循环。
- **优先级 P0｜工作量 中｜叙事价值 极高**

### A3. 选出来的工具其实没被"执行"，只是记录进 trace
- **现状**：`tool_registry.py:116 build_tool_trace_entries()` 的 `execution_mode="planned_for_downstream_nodes"`；真正干活的是下游硬编码节点（`_execute_recycling_node` 等）。所谓"工具调用"在 trace 里是**计划态**，不是模型驱动的真实执行回路。
- **改法**：随 A1/A2 一起，让 `tools` 节点真正执行模型选定的工具并把结果喂回。
- **优先级 P0｜工作量 中｜叙事价值 高**

### A4. 没有 human-in-the-loop（现成用例被浪费）
- **现状**：`tool_registry.py` 已设计 `risk_level:"high"` + `auto_execute:False`（如 `record_recycling_completion` 需用户确认），但实现方式是 `_blocked_business_write` **直接拒绝**（`tool_registry.py:321`）。这正是 LangGraph `interrupt()` + checkpointer 的教科书用例，却用"block 掉"实现了。
- **改法**：high-risk 工具触发 `interrupt()`，暂停图、等前端用户确认后 `Command(resume=...)` 继续。
- **优先级 P0/P1｜工作量 中｜叙事价值 极高**（human-in-the-loop 是企业 agent 高频考点）

### A5. 没有 checkpointer / 状态持久化 / 断点续跑
- **现状**：`graph.compile()` 未配置 checkpointer；`GraphAgentState` 每次请求从零构建。
- **改法**：接入 LangGraph checkpointer（`SqliteSaver`/`PostgresSaver`），用 `thread_id`=conversation_id 持久化 agent 状态，支撑 A4 的中断续跑与多轮状态恢复。
- **优先级 P1｜工作量 中｜叙事价值 高**

### A6. 旗舰 Graph Agent 默认关闭，不是默认路径
- **现状**：`AI_GRAPH_AGENT_ENABLED` 默认 `false`（`settings.py`、`.env.example`），`ai_conversation_service.py:966` 只有开关打开才走 agent；默认走线性 decision engine。简历主打的功能默认不启用。
- **改法**：把重构后的 agent loop 作为主路径；保留规则路径作为 shadow/fallback（见 A7）。
- **优先级 P1｜工作量 小｜叙事价值 中**

### A7. 用 shadow mode 讲"规则驱动 → 模型驱动"的演进故事（叙事增强）
- **现状**：`ai_decision_engine.py:78` 已有 compat/shadow/llm_first 三模式框架，但对比的是决策 payload，不是工具选择。
- **改法**：保留现有规则选择作为 v1；把模型驱动的工具循环作为 v2；用 shadow 模式**对比两者的 tool-selection 准确率**，产出真实数字。故事线："v1 规则 → v2 模型驱动，shadow 对比命中率 X%→Y%"——企业味十足。
- **优先级 P1｜工作量 中｜叙事价值 极高**

### A8. 缺少多步推理 / 规划能力
- **现状**：单轮 route → 单次执行，无 ReAct/Plan-and-Execute，无法处理"先查图谱确认材质，再估算碳减排，再找附近回收点"这类需要多步串联的任务。
- **改法**：agent loop（A2）天然支持多步；可选实现一个显式 planner 节点。
- **优先级 P2｜工作量 中｜叙事价值 中**

### A9. 工具无并行执行
- **现状**：即便未来多工具，也是串行。
- **改法**：无依赖的 tool_calls 并行（`asyncio.gather` 或 LangGraph 并行分支）。
- **优先级 P2｜工作量 小｜叙事价值 中**

---

## B. LLM 交互健壮性

> 反差点：OSM 地图工具做了完整的 timeout/retry/backoff/fallback（`.env.example` 的 `OSM_OVERPASS_*`），但**最关键的 LLM 调用一个都没有**。这本身就是很好的"我发现并修复了不一致"的叙事。

### B1. LLM 调用无 timeout
- **现状**：`openrouter_service.py:47 _get_client()` 裸构造 `OpenAI(base_url, api_key)`，未设 `timeout`；OpenAI SDK 默认 600s。provider 挂起会吊死一个 Flask sync worker 最长 10 分钟。
- **改法**：设置合理 `timeout`（如 30~60s），区分连接/读取超时。
- **优先级 P0｜工作量 小｜叙事价值 中**

### B2. LLM 调用无重试 / 退避
- **现状**：`_send_completion_request` 直调，无重试。对比 OSM 有 `MAX_ATTEMPTS`/`RETRY_BACKOFF_MS`。
- **改法**：对可重试错误（429/5xx/超时）做指数退避重试（tenacity 或 SDK `max_retries`）。
- **优先级 P0｜工作量 小｜叙事价值 中**

### B3. 结构化输出靠 prompt + 正则解析，不是 native 能力
- **现状**：`complete_json_diagnostic()`（`openrouter_service.py:478`）让模型输出文本再抠 JSON；stage1 prompt 里写"return exactly one JSON object / Do not wrap in markdown"。`invalid_json` 的 fallback 链其实是在为自己制造的问题打补丁。
- **改法**：router/extractor/stage1 等结构化场景改用 `response_format={type:"json_schema"}`（structured outputs）或 native tool calling 拿结构化结果。
- **优先级 P0｜工作量 中｜叙事价值 高**

### B4. 无降级 / 备用 provider（failover）
- **现状**：配了 openrouter 和 qwen 两套（`settings.py`），但无自动 failover；主 provider 挂了整条链路失败。
- **改法**：主/备 provider 或主/备模型自动切换；可结合 B2 重试。
- **优先级 P1｜工作量 中｜叙事价值 中**

### B5. 无 token / 成本 / 延迟落库
- **现状**：`complete_text()` 拿到了 `usage`（prompt/completion/total tokens），但只回传给前端，未按请求聚合落库；无法回答"一次请求花多少钱、慢在哪"。
- **改法**：把每次 LLM 调用的 model/tokens/latency/cost 结构化记录（配合 F 可观测）。
- **优先级 P1｜工作量 中｜叙事价值 高**

### B6. 全同步阻塞，无 async / 并发模型
- **现状**：AI 链路全同步（`grep async` 仅 forum 后台任务用到）；gunicorn sync worker + 阻塞 LLM 调用 = 并发瓶颈。
- **改法**：评估 async（FastAPI 迁移成本高，可先用 gunicorn gevent/线程 worker + 流式）；至少保证流式下不阻塞。
- **优先级 P2｜工作量 大｜叙事价值 中**

### B7. 无限流 / 配额
- **现状**：AI 接口无 rate limit，无每用户配额；易被刷、成本易失控。
- **改法**：接入 Flask-Limiter，按用户/IP 限流；对 LLM 调用加日/月配额。
- **优先级 P1｜工作量 小｜叙事价值 中**

---

## C. 检索质量（RAG / GraphRAG）

### C1. 无 reranker（检索后重排）
- **现状**：`forum_retrieval_service.py` 融合后直接 top-k，无 cross-encoder 重排。
- **改法**：召回后接 bge-reranker / cohere-rerank 之类做精排；对比加 reranker 前后的 precision@k。
- **优先级 P1｜工作量 中｜叙事价值 高**（RAG 岗高频考点）

### C2. 查询扩展是硬编码中英词表
- **现状**：`_QUERY_EXPANSION_RULES`（`forum_retrieval_service.py:16`）把"塑料瓶→plastic bottle"等写死，甚至有专门的"塑料瓶+方法→lantern"特判。不可扩展、易过拟合到 demo 数据。
- **改法**：改用多语言 embedding 天然跨语言，或用 LLM 做查询改写（query rewriting / HyDE）。
- **优先级 P1｜工作量 中｜叙事价值 中**

### C3. 关键词召回全表扫描
- **现状**：`_keyword_recall()` 遍历 `list_active_chunks()` 全部 chunk，在 Python 里逐条打分（`_score_keyword_match`），O(n)，无倒排索引/BM25。数据量一大就崩。
- **改法**：用 SQLite FTS5 / PostgreSQL 全文检索 / Elasticsearch 做 BM25；或至少建倒排索引。
- **优先级 P1｜工作量 中｜叙事价值 中**

### C4. 无 embedding 缓存
- **现状**：每次查询都实时调 provider embed（`_vector_recall` → `build_forum_rag_index().search`），查询侧无缓存。
- **改法**：查询 embedding 加 LRU/Redis 缓存；相同 query 命中缓存。
- **优先级 P2｜工作量 小｜叙事价值 中**

### C5. FAISS 向量存进 JSON manifest，非生产级
- **现状**：`forum_index.py` 把整向量写进 `_StoredChunk.to_manifest_item()` 的 JSON manifest，并有纯 Python `_dot_product` 兜底。demo 可用，不具生产扩展性。
- **改法**：给出 pgvector / Milvus / Qdrant 的可选后端；至少把 FAISS 索引与元数据分离持久化。
- **优先级 P2｜工作量 中｜叙事价值 中**

### C6. citation 抽取靠子串匹配
- **现状**：`extract_used_forum_references()`（`forum_retrieval_service.py:81`）在回复文本里子串匹配 URL/title 判断"引用了哪些来源"，脆弱（模型换个写法就漏）。
- **改法**：用结构化输出让模型显式返回 `used_reference_ids`；或用 span/引用标记。
- **优先级 P1｜工作量 小｜叙事价值 中**

### C7. Neo4j 每请求新建 driver，无连接池复用；无 retry
- **现状**：`neo4j_graph_retrieval_service.py:141 query_graph_context()` 内 `_create_driver()` 建后即 `close()`；无跨请求连接池、无重试。
- **改法**：driver 单例化 + 连接池；查询加超时与重试。
- **优先级 P1｜工作量 小｜叙事价值 中**

### C8. 无检索质量评测
- **现状**：没有 recall@k / precision@k / MRR 等检索指标，无法量化 RAG 好坏（与 E 评测体系联动）。
- **改法**：建带 golden 标注的检索评测集，产出 recall/precision/MRR。
- **优先级 P1｜工作量 中｜叙事价值 高**

### C9. Chunk 策略固定未评估
- **现状**：chunk 大小/overlap 由 `FORUM_RAG_CHUNK_TARGET_TOKENS=420` 等固定，未做消融对比。
- **改法**：对比不同 chunk 策略对检索指标的影响，写进评测报告。
- **优先级 P2｜工作量 小｜叙事价值 中**

---

## D. 安全 / Guardrails

### D1. Guardrails 是 43 行关键词表，易绕过
- **现状**：`guardrails.py` 全部逻辑是 `INJECTION_PATTERNS` 字面匹配（"reveal the system prompt" 等），换种说法即绕过。
- **改法**：升级为 moderation 模型 / LLM-as-judge 判别；关键词作为快筛第一层。
- **优先级 P1｜工作量 中｜叙事价值 高**

### D2. 只扫检索文本，不扫用户输入 / 模型输出（双侧缺失）
- **现状**：`scan_retrieved_text_for_injection()` 只在 `_aggregate_hits_by_post` 里扫**检索到的论坛文本**；用户输入侧、模型输出侧都没有防护。
- **改法**：输入侧（prompt injection / 越权意图）+ 输出侧（有害内容 / 泄露）双侧检查。
- **优先级 P1｜工作量 中｜叙事价值 高**

### D3. 多个 AI 接口无鉴权
- **现状**：`api/ai/chat.py` 中 `/ai/analyze-image`、`/ai/location-context`、`/ai/chat/resume` **没有 `@jwt_required()`**（对比 `/ai/chat` 有）。未授权即可调用消耗 LLM。
- **改法**：补齐鉴权；确需匿名的接口加限流与配额。
- **优先级 P0（安全）｜工作量 小｜叙事价值 中**

### D4. SSE 把异常详情泄露给前端
- **现状**：`_json_sse_response` 与 `ai_chat` 的兜底把 `f"AI request failed: {exc}"` / `f"AI stream failed: {exc}"` 原样下发，可能泄露内部实现/堆栈信息。
- **改法**：对外返回通用错误码+消息，详情只进服务端日志（配合 F）。
- **优先级 P1（安全）｜工作量 小｜叙事价值 低**

### D5. memory 存用户信息无 PII 脱敏
- **现状**：`memory_service` 存用户偏好/画像，无 PII 识别与脱敏策略。
- **改法**：入库前 PII 检测/脱敏；提供用户侧删除（已有 `delete_memory_item`，需补隐私说明）。
- **优先级 P2｜工作量 中｜叙事价值 中**

### D6. 图像输入无内容/大小校验
- **现状**：`_parse_recycling_payload` 仅校验是否为字符串 data URL，未限制大小/类型/内容安全。
- **改法**：限制大小与 MIME，必要时接图像审核。
- **优先级 P2｜工作量 小｜叙事价值 低**

### D7. 把注入/越狱样本纳入评测（与 E 联动）
- **现状**：eval fixture 里有 `malicious_user_prompt` 类别，但跑在 mock 上（见 E1）。
- **改法**：把对抗样本放进真实 eval，持续回归 guardrail 召回率。
- **优先级 P1｜工作量 中｜叙事价值 高**

---

## E. 评测体系（AI 应用岗最能区分候选人的部分）⭐️

### E1. eval 是 mock，断言全 1.0，不测真实系统
- **现状**：`eval_suite.run_eval_suite()` 默认 `runner=run_mock_case`，`run_mock_case` 手工构造理想 trace；`test_eval_suite.py` 断言 `intent_accuracy==1.0`、`citation_coverage==1.0` 等。这是在测 mock harness，不是系统。
- **改法**：用 `run_live_graph_agent_case`（已存在但未接）真跑系统，产出**真实**指标。
- **优先级 P0（对 AI 岗）｜工作量 中｜叙事价值 极高**

### E2. 数据集太小（仅 ~8 条）
- **现状**：`ai_eval_cases.json` 只有 8+ 条。
- **改法**：扩到 50~100 条标注 case，覆盖正常/多语言/越狱注入/工具失败/Neo4j 不可用/需澄清等类别。
- **优先级 P0/P1｜工作量 中｜叙事价值 极高**

### E3. 无 LLM-as-judge
- **现状**：只有规则化断言（intent 相等、有无 citation），无法评"回答质量/忠实度/是否 grounded"。
- **改法**：引入 LLM-as-judge 评 faithfulness/relevance/groundedness；可参考 RAGAS 指标体系。
- **优先级 P1｜工作量 中｜叙事价值 极高**

### E4. 无 CI 回归护栏
- **现状**：改 prompt 无自动评测把关，指标退化无人知。
- **改法**：CI 里跑 eval（可用小样本 + 缓存控成本），指标低于阈值则 fail。
- **优先级 P1｜工作量 中｜叙事价值 高**

### E5. 无成本 / 延迟指标
- **现状**：eval 只看正确性，不看 p50/p95 延迟与每 case token 成本。
- **改法**：eval 输出延迟与成本分布，写进报告。
- **优先级 P1｜工作量 小｜叙事价值 高**

### E6. shadow mode 有框架但无真实指标产出
- **现状**：`AI_PROMPTOPS_SHADOW_ENABLED`、`shadow_decision` 存在，但没有把 shadow 对比结果聚合成可展示的数字。
- **改法**：把 shadow 对比落库/出报告，支撑"新旧策略命中率对比"的叙事（与 A7 联动）。
- **优先级 P1｜工作量 中｜叙事价值 高**
- **产出物**：`docs/evaluation.md`（方法 + 真实数字 + 前后对比），并把关键数字写进 README 和简历。

---

## F. 可观测性（Observability）

### F1. 无业界可观测工具
- **现状**：自建 `AgentTracePanel.vue` + trace schema 很好（是好的产品功能，保留），但底层无 Langfuse/Phoenix/LangSmith 类工具，拿不到聚合的 token 成本/延迟分布/调用链。
- **改法**：接 Langfuse（可自托管、免费）记录每次 LLM/agent 调用；自建 trace 保留做产品展示。面试聊"自建 trace vs Langfuse 各覆盖什么"是好话题。
- **优先级 P1｜工作量 中｜叙事价值 高**

### F2. 无结构化日志 / request-id 贯穿
- **现状**：无统一结构化日志、无贯穿一次请求的 trace/request id。
- **改法**：结构化 JSON 日志 + request id 贯穿 API→service→LLM→工具。
- **优先级 P1｜工作量 小｜叙事价值 中**

### F3. 无 metrics / dashboard / 告警
- **现状**：无延迟分布、错误率、token 消耗的 metrics 与看板，无异常告警。
- **改法**：Prometheus + Grafana 或 Langfuse 自带看板；关键指标告警。
- **优先级 P2｜工作量 中｜叙事价值 中**

### F4. prompt_registry 只有元数据，不是真正的 prompt 版本化
- **现状**：`prompt_registry.py` 只存 name/version/schema/safety_notes，**不存 prompt 正文**；实际 prompt 文本硬编码散落在各 service（如 `_stage1_analysis_system_prompt`）。无正文版本化/回滚/diff/AB。
- **改法**：把 prompt 正文纳入注册表（含版本、变量、可回滚）；或接 Langfuse Prompt Management。
- **优先级 P1｜工作量 中｜叙事价值 高**

---

## G. 工程化 / 可维护性

### G1. 巨型 service 文件
- **现状**：`recycling_analysis_service.py` 1555 行、`ai_conversation_service.py` 1225 行，单文件职责过重。
- **改法**：按 stage/流式/持久化拆分，划清 agent / tool / retrieval / persistence 边界。
- **优先级 P2｜工作量 中｜叙事价值 低**

### G2. AI 模块分层边界不清
- **现状**：编排、工具、检索、记忆全平铺在 `services/ai/`，无清晰的 `agent/` `tools/` `retrieval/` 分层。
- **改法**：重构目录结构，让"这是一个 agent 系统"从代码组织上一眼可见。
- **优先级 P2｜工作量 中｜叙事价值 中**

### G3. 无类型检查
- **现状**：代码有类型注解但无 mypy/pyright CI 校验。
- **改法**：加 mypy/pyright + ruff，进 CI。
- **优先级 P2｜工作量 小｜叙事价值 低**

### G4. prompt 硬编码散落
- **现状**：见 F4，prompt 文本分散在各函数里。
- **改法**：集中到 prompt 目录/注册表。
- **优先级 P2｜工作量 小｜叙事价值 中**

---

## H. 推荐执行顺序（按面试收益排序）

### 第一阶段 P0：把"假 agent"变成"真 agent"（约 1~1.5 周）
1. **A1+A2+A3**：LangGraph 改成真正的 agent loop，工具 schema 交给模型，`tools` 节点真实执行并回喂。（保留规则选择作为 fallback）
2. **B1+B2+B3**：provider 层加 timeout + 重试；router/extractor/stage1 改 structured outputs。
3. **D3**：补齐 AI 接口鉴权（安全兜底，顺手做）。
4. **E1**：eval 切到真实系统跑（`run_live_graph_agent_case`），先跑通再谈数字。

**阶段产出叙事**：从"规则驱动工作流"升级为"模型驱动 agent，带 native tool calling + 结构化输出 + 超时重试"。

### 第二阶段 P1：深度与可信度（约 1.5~2 周）
5. **A4+A5**：human-in-the-loop（`interrupt()`）+ checkpointer，把已有的 high-risk 风险分级真正用起来。
6. **A7+E6**：shadow 模式对比 v1 规则 vs v2 模型驱动的 tool-selection 命中率，产出真实数字。
7. **E2+E3+E4+E5**：50~100 条标注集 + LLM-as-judge + CI 回归 + 成本/延迟指标 → `docs/evaluation.md`。
8. **C1+C8**：RAG 加 reranker，建检索评测（recall/precision/MRR）。
9. **F1+F2+F4**：接 Langfuse，结构化日志，prompt 正文版本化。
10. **D1+D2+D7**：guardrails 升级为模型判别 + 输入/输出双侧 + 对抗样本进 eval。
11. **B7**：接入限流。

### 第三阶段 P2：打磨（可选，视时间）
- C2/C3/C4/C5（检索工程化）、B4/B6（failover/async）、G 系列（重构与类型检查）、F3（metrics 看板）。

---

## I. 面试叙事映射（把改造翻译成简历/面试话术）

| 改造项 | 可讲的话术方向 |
|---|---|
| A1~A3 agent loop | "用 LangGraph 实现模型驱动的 tool-calling agent，工具 schema 由模型决策，带 max-iteration 环路控制" |
| A4+A5 HITL + checkpointer | "对高风险写操作用 interrupt + checkpointer 实现 human-in-the-loop 审批与断点续跑" |
| A7 shadow 对比 | "灰度上线：shadow 模式对比规则 v1 与模型 v2 的工具选择命中率，X%→Y% 后全量" |
| B1~B3 健壮性 | "provider 层做了超时/指数退避重试/结构化输出，把 JSON 解析失败率从 X 降到 ~0" |
| C1+C8 reranker+评测 | "hybrid 检索(RRF)+cross-encoder 重排，precision@k 提升 X 个点" |
| E 系列 eval | "自建 AI 评测体系：100 条标注集 + LLM-as-judge + CI 回归，citation coverage X%、guardrail 召回 Y%、p50 延迟 Zs" |
| F1+F4 可观测 | "Langfuse 追踪每次调用的 token/成本/延迟，prompt 正文版本化可回滚" |
| D 系列安全 | "输入/输出双侧 guardrails + 对抗样本回归，接口鉴权与限流防滥用" |

---

## J. 需要保留并主动讲的现有亮点（改造中勿丢）

- `ai_decision_engine.py` 的 **compat / shadow / llm_first 三模式灰度**——企业上线 LLM 功能的标准姿势。
- **逐层 fallback 留痕**（`router_used_fallback`、`fallback_mode`、`*_failure_reason` 全进 trace）。
- **工具风险分级**（`risk_level` + `auto_execute`）——A4 的现成地基。
- **丰富的 trace schema**（`agent_trace_service.py`）+ 前端 `AgentTracePanel.vue`——好的产品化可观测。
- **RRF 混合检索**（keyword + vector 融合，`forum_retrieval_service.py:_fuse_hits`）。
- **OSM 工具的完整重试/退避/降级**——把它当作 B1/B2 给 LLM 层补健壮性的模板。

---

_备注：本文档为规划清单，不含代码改动。执行时建议每个 P0/P1 项单独开分支+有意义的 commit，让 git 历史体现工程演进（当前仓库仅 1 个 commit，本身也是"课设感"来源之一）。_

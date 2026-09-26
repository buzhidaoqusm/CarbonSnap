# 性能问题清单（P1 之前的基线）

> 测于 2026-09-26，提交 `bbce2d7`。每个问题都附了复现命令和当前数字。后续每完成一个阶段，
> 重跑同一条命令，数字的变化就是"系统变好了多少"。

## 压测是怎么做的

```
locust / probe.py  ──HTTP──▶  api（gunicorn，3 个 sync worker）  ──HTTP──▶  fake-llm
    模拟用户                        被测对象                             假的大模型
```

- **假 LLM**（[tools/fake_llm/server.py](../tools/fake_llm/server.py)）：兼容 OpenAI 接口，每次调用固定
  400 ms 出首 token，之后 120 个 token 每个间隔 25 ms，一次调用约 3.4 s。它排除了第三方
  provider 的抖动，结果可复现，而且不花钱。**测出来的是我们服务器自己的问题。**
- **locust**（[tools/load_test/locustfile.py](../tools/load_test/locustfile.py)）：N 个用户各自注册账号，
  然后循环执行"发一条消息 → 读完整个流 → 等 1–3 s"。它回答的是**"N 个用户时有多慢"**。
- **probe.py**（[tools/load_test/probe.py](../tools/load_test/probe.py)）：每个实验只隔离一个问题，
  回答的是**"为什么慢"**。

启动压测环境（仓库根目录）：

```bash
docker compose -f docker-compose.yml -f docker-compose.bench.yml --profile bench up -d --build
```

## 问题一览

| # | 问题 | 当前数字 | 由哪个阶段修 | 目标 |
|---|---|---|---|---|
| 1 | 并发上限等于 worker 数 | 最大稳定并发 **3** | P1 | ≥ 50 |
| 2 | 3 个人聊天，整个 API 无响应 | `/api/health` **4 ms → 12.8 s** | P1 | < 50 ms |
| 3 | 单用户首 token 就要 10 s | ttft **10.7 s**（其中 10.2 s 在串行等 LLM） | P2 | < 4 s |
| 4 | 首 token 前 10 s 没有任何进度 | 心跳之后 **10.2 s** 无事件 | P2 | 每个阶段都推送事件 |
| 5 | 用户关掉页面，服务端不停 | 继续占用 worker **8.5 s**，打满 4 次 LLM 调用，留下没有回复的会话 | P1 | 断开后 < 1 s 释放 |
| 6 | ~~LLM 调用实际没有超时~~ ✅ 已修 | provider 卡住时：600 s 后 worker 被强杀 → **105 s 后返回错误事件** | 已修（2026-09-26） | 配置值生效 |
| 7 | 每个并发会话约 115 MB | 3 个 worker 共 320 MB，12 个共 1.04 GB | P1 | 内存不随并发线性增长 |

---

## 1. 并发上限等于 worker 数

gunicorn sync worker 一次只能处理一个请求，一个流式对话从开始到结束（约 13.7 s）都占着它。

| 用户数 | ttft p50 / p95 | 吞吐（轮/秒） |
|---|---|---|
| 1 | 10 / 10 s | 0.07 |
| 3 | 10 / 10 s | 0.18 |
| 10 | 36 / 48 s | 0.20 |
| 20 | 51 / 91 s | 0.18 |

从 3 个用户开始，吞吐就不再增长了，多出来的用户全部在排队。吞吐 ≈ worker 数 ÷ 单轮耗时
（3 ÷ 13.7 ≈ 0.22）。

```bash
uv run --no-project --with locust locust -f tools/load_test/locustfile.py --host http://127.0.0.1:5000 --headless --users 20 --spawn-rate 2 --run-time 2m --only-summary
```

`--users` 依次取 1 / 3 / 10 / 20。

**加 worker 行不行？** 12 个 worker、20 个用户时，吞吐升到 0.83，ttft p50 降到 19 s，
但内存从 320 MB 涨到 1.04 GB，而且 20 个用户仍然多于 12 个 worker，还是要排队。
这只是把上限往后推，"一个对话占一个进程"的模型没有变。

```bash
GUNICORN_CMD_ARGS="--workers 12" docker compose -f docker-compose.yml -f docker-compose.bench.yml --profile bench up -d api
```

## 2. 3 个人聊天，整个 API 无响应

`/api/health` 什么都不做，但只要 3 个 worker 都被对话占着，它也得排队。

| 进行中的对话数 | `/api/health` 延迟 |
|---|---|
| 0 | 3 ms |
| 2 | 4 ms |
| 3 | **12.8 s** |

locust 里的注册接口也一样：1 个用户时 0.1 s，20 个用户时 14 s。
如果将来部署在负载均衡或 k8s 后面，健康检查超时会被判定为宕机，容器会被重启。

```bash
uv run --no-project --with requests python tools/load_test/probe.py blocking --streams 3
```

## 3. 单用户首 token 就要 10 s

一轮对话串行调用了 5 次 provider，前 4 次都在首 token 之前完成：

| 相对开始时间 | 调用 | 耗时 |
|---|---|---|
| +0.0 s | 决策路由 | 3.4 s |
| +3.4 s | 长期记忆提取 | 3.4 s |
| +6.8 s | 论坛检索 embedding | 约 16 ms |
| +6.8 s | 生成会话标题 | 3.4 s |
| +10.3 s | 回答（流式） | 首 token 0.4 s |

我们自己代码的开销只有约 0.1 s，问题出在调用编排上：
- 路由和记忆提取互不依赖，可以并行；
- 标题生成跟回答无关，可以放到回答之后，或者在后台做；
- 记忆提取可以不阻塞本轮回答。

入口在 [ai_conversation_service.py](../backend/app/services/ai/ai_conversation_service.py) 的
`stream_routed_chat_message` → `decide_message` → `stream_chat_message`。

```bash
FAKE_LLM_LOG=1 docker compose -f docker-compose.yml -f docker-compose.bench.yml --profile bench up -d fake-llm
```

```bash
uv run --no-project --with requests python tools/load_test/probe.py timeline
```

```bash
docker compose logs fake-llm -t --tail 10
```

> 注意：假 LLM 对每次调用都输出 120 个 token。真实场景下路由、标题这类短输出会更快，
> 所以真实的 ttft 会低于 10 s，但"串行等待"的结构是一样的。另外，假 LLM 返回的不是 JSON，
> 路由会回退到 `general_chat`，所以测到的始终是这一条路径。

## 4. 首 token 前 10 s 没有任何进度

服务端先发一个 `heartbeat`，然后要等 10.2 s 才发下一个事件（`meta`）。这段时间前端只能一直转圈，
用户不知道系统在做什么，也分不清是在处理还是已经卡死。上面 `timeline` 实验的输出里能直接看到
`first_heartbeat 4 ms → meta 10.2 s`。

## 5. 用户关掉页面，服务端不停

用户在第 1 秒断开连接后：
- 服务端**照样跑完**路由、记忆提取、embedding、标题生成 4 次调用，还发起了第 5 次流式回答调用，
  直到第一次向已断开的连接写数据才发现用户已经走了；
- 这段时间里 worker 一直被占着：先把另外 2 个 worker 占满，此时 `/api/health` 要等 **8.5 s**；
- 用户消息**已经落库，但助手回复没有**，数据库里留下一个只有提问、没有回答的会话。

连续刷新 3 次页面，就能在约 10 s 内占满所有 worker。

```bash
uv run --no-project --with requests python tools/load_test/probe.py disconnect
```

## 6. LLM 调用实际没有超时 ✅ 已修复

**原来的问题**：`AI_LLM_TIMEOUT_SECONDS=60` 只在 `complete_with_tools` 里用到，而它所在的工具调用
agent 默认是关闭的。主路径上的调用都没有传 timeout，用的是 OpenAI SDK 的默认值 600 s。
provider 卡住时，worker 会等到 600 s 被 gunicorn 强杀，用户只收到一个中途断开的 500。

**修复过程中发现的第二层问题**：让 60 s 超时生效后，SDK 默认会重试 2 次，而首 token 之前有 3 次
串行调用，重试把等待时间放大了 3 倍，一轮对话还是会超过 600 s，worker 照样被强杀。

**修复方式**：
- 超时设在客户端上，所有调用都会生效；连接超时单独设为 5 s。
- 路由、记忆提取、标题生成这 3 个首 token 之前的"辅助调用"改用
  `AI_LLM_AUX_TIMEOUT_SECONDS`（默认 15 s），并且不重试。这 3 个调用失败后都有兜底，
  超时只会让这一轮用上兜底结果（比如标题变成 "New chat"），不会报错。
- 回答调用保持 60 s 超时和 2 次重试。对流式调用来说，60 s 限制的是两次收到数据之间的间隔，
  不是总时长，所以正常的长回答不会被误杀。

实测（假 LLM 每次调用卡 65 s）：

| | 修复前 | 只修超时 | 最终 |
|---|---|---|---|
| 路由 / 记忆提取 / 标题 | 各等 68 s | 各 3 × 60 s | 各 15 s |
| 回答 | 等到 65 s 才出首 token | — | 60 s 后超时 |
| 一轮对话 | 272 s 后才完成；彻底卡死时 600 s 被强杀 | 600 s 被强杀 | **105 s** |
| 用户看到的 | 一直转圈 | 中途断开，只有一个 500 | 正常的错误事件 |

回答调用只超时了一次，没有重试：假 LLM 先返回响应头再卡住，而 SDK 只在拿到响应头之前重试。
如果 provider 连响应头都不返回，回答调用会重试 2 次，最坏约 45 + 180 = 225 s，仍然在 600 s 以内。

```bash
FAKE_LLM_FIRST_TOKEN_MS=65000 docker compose -f docker-compose.yml -f docker-compose.bench.yml --profile bench up -d fake-llm
```

```bash
uv run --no-project --with requests python tools/load_test/probe.py slow
```

跑完记得把假 LLM 恢复成默认值（去掉环境变量，重新执行一次 `up -d fake-llm`）。

## 7. 每个并发会话约 115 MB

每个 gunicorn worker 空闲时约 115 MB。在同步模型下，一个并发会话就要占一个 worker，
所以支持 100 个同时对话大约需要 11 GB 内存。

```bash
docker stats --no-stream carbonsnap-api-1
```

---

## 查过但没有发现问题的

- **SQLite 写锁**：12 个 worker、20 个用户跑了 2 分钟，没有出现 `database is locked`。
- **服务端自身的处理开销**：一轮对话里除去等 LLM 的时间，只有约 0.1 s。

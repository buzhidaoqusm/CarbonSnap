# 性能问题清单（P1 之前的基线）

> 测于 2026-09-26，提交 `bbce2d7`。每个问题都附了复现命令和当前数字。后续每完成一个阶段，
> 重跑同一条命令，数字的变化就是"系统变好了多少"。

## 压测是怎么做的

```
locust / probe.py  ──HTTP──▶  api（uvicorn，1 个进程 × 40 线程；P1 之前是 gunicorn 3 个 sync worker）  ──HTTP──▶  fake-llm
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
| 1 | ~~并发上限等于 worker 数~~ ✅ 已修 | 最大稳定并发 **3 → ≥ 60**（只测到 60）；20 个用户时 ttft p50 **51 s → 11 s** | 已修（2026-10-03，P1 第 1 段） | ≥ 50 |
| 2 | ~~3 个人聊天，整个 API 无响应~~ ✅ 已修 | 3 个对话时 `/api/health` **12.8 s → 9 ms**，10 个对话时 3 ms | 已修（2026-10-03，P1 第 1 段） | < 50 ms |
| 3 | 单用户首 token 就要 10 s | ttft **10.7 s**（其中 10.2 s 在串行等 LLM） | P2 | < 4 s |
| 4 | 首 token 前 10 s 没有任何进度 | 心跳之后 **10.2 s** 无事件 | P2 | 每个阶段都推送事件 |
| 5 | 用户关掉页面，服务端不停 | 继续占用 worker **8.5 s**，打满 4 次 LLM 调用，留下没有回复的会话 | P1 | 断开后 < 1 s 释放 |
| 6 | ~~LLM 调用实际没有超时~~ ✅ 已修 | provider 卡住时：600 s 后 worker 被强杀 → **105 s 后返回错误事件** | 已修（2026-09-26） | 配置值生效 |
| 7 | ~~每个并发会话约 115 MB~~ ✅ 已修 | 3 个对话 320 MB → 40 个对话 **245 MB**（单进程 40 线程） | 已修（2026-10-03，P1 第 1 段） | 内存不随并发线性增长 |
| 8 | ~~第三方资源卡住，整站白屏~~ ✅ 已修 | 第三方请求挂起时：**30 s 后仍白屏 → 0.7 s 出现**；首页 LCP 中位数 **3.0 s → 0.68 s** | 已修（2026-10-03） | 首屏不依赖任何第三方 |
| 9 | 一轮对话全程占着一个数据库连接 | 20 个用户时 **11–20 个连接 "idle in transaction"**；线程多于连接池时 **34% 的对话失败** | P2（第 1 段先把连接池调到和线程数一样大） | 调用 LLM 前结束事务 |

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

**✅ 已修（P1 第 1 段，2026-10-03）**：改用 uvicorn，Flask 挂在 FastAPI 后面、跑在线程池里，
一个对话只占一个线程。单进程 40 线程：20 / 40 个用户时 ttft p50 都是 11 s，吞吐 1.17 / 2.22 轮/秒；
60 个用户时开始排队（ttft p50 15 s），0 错误。完整数字和选型过程见 [benchmarks.md](benchmarks.md)。

**加 worker 行不行？** 12 个 worker、20 个用户时，吞吐升到 0.83，ttft p50 降到 19 s，
但内存从 320 MB 涨到 1.04 GB，而且 20 个用户仍然多于 12 个 worker，还是要排队。
这只是把上限往后推，"一个对话占一个进程"的模型没有变。

（这组数字是修复前用 gunicorn 测的，gunicorn 现在已经移除。修复后换进程数和线程数的方法：
`WEB_WORKERS=3 WSGI_THREADS=10 docker compose -f docker-compose.yml -f docker-compose.bench.yml --profile bench up -d api`）

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

**✅ 已修（P1 第 1 段）**：3 个对话进行中时 `/api/health` 9 ms，10 个时 3 ms；
40 个用户压测时注册接口 p50 86 ms（修复前 20 个用户时 14 s）。

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

**✅ 已修（P1 第 1 段）**：一个对话占一个线程而不是一个进程。单进程空闲约 100 MB，
40 个用户压测之后约 245 MB。

## 8. 第三方资源卡住，整站白屏 ✅ 已修复

**原来的问题**：`index.html` 的 `<head>` 里同步加载了 Google Fonts 的两个样式表和 Tailwind 的
Play CDN 脚本，全站样式都是这个脚本在浏览器里现场编译出来的。样式表会阻塞渲染；普通 `<script>`
会阻塞解析，而且要等它前面的样式表下载完才执行。所以只要任何一个第三方请求挂住（防火墙丢包时就是
这样，请求既不成功也不失败），解析器就停在 `<head>` 里，`<body>` 和应用代码永远加载不到。

实测（生产构建，真实网络，两个构建交替各跑 5 次取中位数）：

| | 修复前 | 修复后 |
|---|---|---|
| 第三方请求全部挂起 | 30 s 后仍白屏：`readyState` 停在 `loading`，没有 `<body>`，一帧都没画 | 首页 0.70 s、市场页 0.57 s 出现 |
| 只挂起字体 CSS / 只挂起 Tailwind | 都是白屏，任何一个都是单点故障 | 不再请求它们 |
| 第三方请求立即失败 | 0.56 s 出现，但完全没有样式，图标显示成英文单词 | 和正常一样 |
| 首页 LCP | 3044 ms（2.2–4.2 s） | 676 ms（0.65–0.77 s） |
| 市场页 LCP | 3504 ms（2.1–5.8 s） | 424 ms（0.36–0.50 s） |
| 每页传输量 | Tailwind 脚本 127 KB（gzip） | 少约 120 KB：脚本没了，构建出的 CSS 多 8 KB |

同一天网络差的时候，修复前的首页 9.7 s 才出现，市场页一次 LCP 到了 44.5 s（Tailwind 脚本下了 24 s）。

**修复方式**：
- Tailwind 改成构建时编译：装 CDN 实际提供的版本（3.4.17、forms 0.5.10、container-queries
  0.1.1，固定版本号），作为 Vite 的 PostCSS 插件运行，只为源码里出现的 class 生成规则。
- 字体用 fontsource 的包自托管。9 个正文字体文件和 Google 发的逐字节相同；图标字体差 456 字节，
  但用 fonttools 比过，两个文件能画的 4299 个图标完全一样。`legacy-fonts.css` 沿用 Google 的
  字体名和它实际提供的字重范围，别处不用改。
- CSS 的 import 顺序就是层叠顺序：字体放最前（原来 Google 样式表的位置），Tailwind 放最后
  （原来 CDN 的 `<style>` 插在我们的 CSS 之后、路由懒加载的 CSS 之前）。

**修复过程中发现的问题**：
- **index.html 里的 Tailwind 主题从来没生效过**：它在 CDN 脚本加载前写了
  `window.tailwind.config`，脚本加载时替换了整个 `window.tailwind`，配置就丢了。模板里的
  `bg-primary`、`font-headline` 等 class 一直没有任何样式。为了不改变用户看到的样子，构建用的是
  CDN 实际生效的配置（默认配置加两个插件），这些页面在重新设计时会被替换。
- Google 是按 300、400……800 逐个字重声明的，`font-weight: 650` 会就近画成 700；自托管的
  可变字体按范围声明，会真的画成 650。`home-view.css` 里 5 处这样的值改成了以前实际画出来的值。
- CDN 在浏览器里还跑了 autoprefixer。旧版 Safari 需要的前缀（`-webkit-backdrop-filter`、
  `-webkit-user-select`）由 Vite 的 esbuild 按默认目标浏览器补上了，只差 `transition-property`
  列表里一个多余的 `-webkit-text-decoration-color`。

**怎么验证"看起来没变"**：`style-diff.mjs` 把修复前后两个构建的 18 个路由、桌面和手机两种宽度、
登录前后各加载一遍，逐个元素比较全部计算样式，逐屏比较截图像素。修复前的构建用的是"CDN 文件
放在本机"的副本，排除网络抖动。先拿同一个构建和自己比（A/A），噪声是：大照片每次缩放出来的像素
不完全一样、取景框的淡入动画。A/B 剩下的差异都在这个范围内，或者是上面说的刻意改动；头像圆角有
16 个像素差 1 个色阶（满分 255），计算样式相同。

```bash
node tools/frontend/third-party.mjs http://localhost:4173/          # 别的域名全部挂起：修复前退出码 1
node tools/frontend/third-party.mjs http://localhost:4173/ --fail   # 别的域名立即失败
```

---

## 9. 一轮对话全程占着一个数据库连接

一轮对话的第一条查询（读用户的偏好画像）会自动开启一个事务（SQLAlchemy 的 autobegin），
之后代码去调 LLM，事务一直不结束，连接也就一直被占着，直到下一次 commit，大约 13 s。
20 个用户时，PG 里同时有 11–20 个连接处于 "idle in transaction"。

后果：
- 连接池比线程少时，多出来的线程等 30 s 拿不到连接就报错。单进程 40 线程、默认连接池（5 + 10）、
  40 个用户时，**34% 的对话失败**（`QueuePool limit of size 5 overflow 10 reached`）。
- 长时间不结束的事务会拖住 PG 的清理（vacuum），持有的锁也会挡住别的写操作。

P1 第 1 段的处理只是止血：连接池大小跟线程数一致（40 + 5）。真正的修法是在调用 LLM 之前结束事务，
放在 P2 重写对话链路时做；做完以后连接池可以缩回去。

```bash
docker compose -f docker-compose.yml -f docker-compose.bench.yml exec postgres psql -U carbonsnap -d carbonsnap -c "select state, count(*) from pg_stat_activity group by state"
```

（压测进行中执行。）

## 查过但没有发现问题的

- **SQLite 写锁**：12 个 worker、20 个用户跑了 2 分钟，没有出现 `database is locked`。
- **服务端自身的处理开销**：一轮对话里除去等 LLM 的时间，只有约 0.1 s。

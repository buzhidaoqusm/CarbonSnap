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
| 5 | 用户关掉页面，服务端不停（部分改善） | 第 1 秒断开后：仍发起的 LLM 调用 **4 → 3 次**（最后的流式回答不再发起）；首 token 前的 3 次串行调用在同一步里，照样跑完 | P1 迁 SSE（部分）；其余在 P2 | 断开后 < 1 s 释放 |
| 6 | ~~LLM 调用实际没有超时~~ ✅ 已修 | provider 卡住时：600 s 后 worker 被强杀 → **105 s 后返回错误事件** | 已修（2026-09-26） | 配置值生效 |
| 7 | ~~每个并发会话约 115 MB~~ ✅ 已修 | 3 个对话 320 MB → 40 个对话 **245 MB**（单进程 40 线程） | 已修（2026-10-03，P1 第 1 段） | 内存不随并发线性增长 |
| 8 | ~~第三方资源卡住，整站白屏~~ ✅ 已修 | 第三方请求挂起时：**30 s 后仍白屏 → 0.7 s 出现**；首页 LCP 中位数 **3.0 s → 0.68 s** | 已修（2026-10-03） | 首屏不依赖任何第三方 |
| 9 | 一轮对话全程占着一个数据库连接 | N 个对话时有 **N 个连接 "idle in transaction"**（实测到 40）；线程多于连接池时 **34% 的对话失败** | P2（先让连接池和流式线程数一样大：Flask 时是 40 + 5，迁到 FastAPI 后是 40 + 20） | 调用 LLM 前结束事务 |
| 10 | 上传接口不限请求体大小 | 未实测：读代码确认没有任何上限 | 待定 | 头像等接口有大小上限，超出返回 413 |
| 11 | ~~并发扣积分重复扣款、超额筹款、一件商品卖两次~~ ✅ 已修 | 每个场景跑 20 轮：重复扣款 **14 → 0**、超额筹款 **19 → 0**、一件商品卖两次 **16 → 0**、订单既发货又退款 **15 → 0** | 已修（2026-10-16） | 并发请求结果和串行执行一致 |
| 12 | ~~论坛列表 N+1 查询~~ ✅ 已修 | 全站 200 帖、一页 20 帖：未登录 **62 → 5 条 SQL**，已登录 **489 → 15 条**；5 条评论：**12 / 17 → 4 / 5 条** | 已修（2026-10-18） | 一页帖子的 SQL 条数不随帖子数增长 |
| 13 | ~~已登录列表把全站数据加载进内存再排序~~ ✅ 已修 | 全站 2 万行、有画像的用户拉第 1 页：forum **18.3 s → 49 ms**，project **14.6 s → 183 ms**，market **15.3 s → 41 ms**；内存峰值 **约 70 MB → 0.7 MB** | 已修（2026-10-18） | 耗时和内存不随全站行数增长 |

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

**迁到 FastAPI 之后（2026-10-20）**：用新增的 `probe.py abandon` 测量（读取假 LLM 的调用日志，统计客户端断开之后
还发起了几次调用；原来的 `disconnect` 是按 gunicorn worker 设计的，已经不适用）。每组测 3 次，结果一致：

| | 这一轮的 LLM 调用 | 断开之后才发起的 |
|---|---|---|
| Flask + a2wsgi | 5 | 4 |
| FastAPI `sse_response` | 4 | 3 |

Starlette 会监听断开，在下一个事件边界停止迭代，并立即关闭 service 的生成器（`finally` 会执行）。
但路由、记忆提取、标题生成这 3 次串行调用发生在第一个事件之前，处在同一个"取下一个事件"的步骤里，
线程无法中途取消，所以照样跑完。要根治，得让这些调用之间有让出点，或者改成可以取消的 async 调用，留给 P2。

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

## 10. 上传接口不限请求体大小

`PATCH /api/auth/me/avatar` 接收一个 base64 data URL，`store_data_url_image` 会先把它整个解码进内存，
然后写到磁盘。整个链路上没有任何大小检查：Flask 没设置 `MAX_CONTENT_LENGTH`，迁到 FastAPI 以后也没有加，
`store_data_url_image` 里同样没有。一个已登录的用户可以上传任意大的"头像"，处理过程中会占用这么大的内存，
最后还要占用这么大的磁盘空间。论坛、AI 对话这些接口也走 `store_data_url_image`，所以有同样的问题。

这是 P1 第 3 段迁移 auth 时读代码发现的，还没有实测。修的时候先测一下：上传 50 MB 的 data URL，
看进程内存涨了多少、请求花了多久，以及磁盘上多出了什么。

## 11. 并发扣积分重复扣款、超额筹款、一件商品卖两次 ✅ 已修

扣积分、加积分、项目筹款、商品下单、订单状态流转，原来都是同一个模式：**先读出来，在 Python 里判断和计算，
再写回去**，全程没有加锁。`place_order` 的 docstring 写着 "Lock item"，但代码里其实并没有锁。

PG 默认的隔离级别是 READ COMMITTED：两个并发事务可能读到同一个旧值，各自算完后写回，
后提交的会覆盖先提交的（lost update），状态检查也会被两个事务同时通过。

**复现方法**：在临时库上起一个真实的 uvicorn，用 barrier 让两个线程同时发请求，每个场景跑 20 轮。

| 场景 | 修复前出错次数 | 修复前的后果 |
|---|---|---|
| A 一个用户有 100 积分，同时给两个项目各贡献 60 | 14/20 | 14 个用户各有 60 积分花了但没扣，合计 840 积分 |
| B 两个用户同时给目标 100 的项目各贡献 60 | 19/20 | 项目筹到了 120 |
| C 两个买家同时买同一件商品 | 16/20 | 同一件商品出现两个订单 |
| D 卖家发货和买家取消同时发生 | 15/20 | 订单"已发货"但买家拿到了退款，之后还能确认收货，让卖家也拿到货款 |
| E 卖家下架和买家下单同时发生（迁移 market 时发现） | 两边同时成功 | 买家为一件已经下架的商品付了钱 |

修复后 4 个场景都是 **0/20**。

**修法**：悲观锁 `SELECT ... FOR UPDATE`。读这些行的时候就锁住，另一个事务读同一行时要等这个事务提交，
然后读到的是最新值。

- 用户余额：`user_repository.get_for_update`，`spend_points`、`earn_points` 和审核通过发积分都改用它；
- 项目、商品、订单：`get_project_for_update`、`get_item_for_update`、`get_order_for_update`；
- 加了 `populate_existing`，确保即使对象已经在 session 里，也会用刚查到的最新值覆盖。

加锁顺序统一为**先锁资源（项目、商品、订单），再锁用户**，避免死锁。

**过程中还发现了一个问题**：同一个用户的两个请求同时成功时，都会去重建这个用户的推荐画像。重建的做法是
"先删光再插入"，第二个事务的 DELETE 看不到第一个刚插入的行，于是插入时撞上唯一约束。这个异常被
`except Exception: pass` 吞掉了，但 session 一直处于失败状态，后面的查询都会报错，结果**已经提交成功的贡献返回了 500**。

处理方法：重建画像前先锁住这个用户的行，让两次重建串行执行；project_service 的 4 处 `except` 改成记录日志并回滚。

market、forum 和 AI 相关的 service 里还有十几处同样的 `except Exception: pass` 没有处理。这些代码块有的可能处在主事务提交之前，
在那里回滚会把主操作也一起回滚掉，所以要等迁移这些模块时逐个确认上下文再改。

回归测试见 `tests/integration/test_concurrent_spending.py`，用子进程起一个真实的服务器，共 5 个场景、各 10 轮，耗时约 13 秒。

## 12. 论坛列表 N+1 查询 ✅ 已修复

`forum_service.list_posts` 原来对返回的每个帖子都要单独查一次作者、点赞数、评论数，已登录时还要再查一次
"我有没有点过赞"。`list_comments` 也一样，每条评论要单独查作者和点赞数。

已登录时问题更严重：列表会先把**全站所有**已发布帖子交给个性化排序，排完再分页，而排序里的
`_engagement_score` 对每个候选帖子都要查一次点赞数、一次评论数。所以 SQL 条数随**全站帖子数**增长，
而不只是随每页条数增长。第一次测量时全站只有 20 个帖子，正好一页，没有暴露出这一点。

修法：作者、点赞数、评论数、"我点过赞的 id"都改成按 id 列表批量查询（`IN (...)` 加 `GROUP BY`），
每种只查一次。排序要用的点赞数和评论数在 `build_ranking_context` 里一次查好，`_engagement_score`
改为只从 context 里读，和 market、project 的排序写法保持一致。

`tests/integration/test_forum_query_count.py` 统计每个请求执行的 SQL 条数，断言 5 个帖子和 20 个帖子时条数相同；
修复前 5 个用例全部失败。

实测：每帖 1 个赞、1 条评论，第一个帖子 5 条评论，用同一个 probe 分别跑修复前后的代码。

| 请求 | 返回条数 | 修复前 SQL | 修复后 SQL |
|---|---|---|---|
| 帖子列表，全站 20 帖，未登录 | 20 | 62 | 5 |
| 帖子列表，全站 20 帖，已登录（冷启动） | 20 | 129 | 15 |
| 帖子列表，全站 20 帖，已登录（有画像） | 20 | 130 | 16 |
| 帖子列表，全站 200 帖，未登录 | 20 | 62 | 5 |
| 帖子列表，全站 200 帖，已登录（冷启动） | 20 | 489 | 15 |
| 帖子列表，全站 200 帖，已登录（有画像） | 20 | 490 | 16 |
| 评论列表，未登录 | 5 | 12 | 4 |
| 评论列表，已登录 | 5 | 17 | 5 |

已登录时仍然会把全站帖子都加载进内存、排完序再分页：SQL 条数固定了，但内存和 CPU 仍随帖子数增长。这个问题见 #13。

## 13. 已登录列表把全站数据加载进内存再排序 ✅ 已修复

forum、project、market 三个已登录列表原来的做法都一样：把全站所有符合条件的行加载进内存，交给个性化排序，排完再切出请求的那一页。
#12 修完之后 SQL 条数是固定的，但内存和 CPU 仍随全站行数增长。

测出来比预期更严重：有画像的用户，耗时随行数近似**平方**增长。原因在 `merge_ranked_*` 这个函数。
它要把全部 n 个候选合并成一个序列，每取一个都要从头扫一遍候选池，跳过已经用过的行和不满足多样性限制的行。
2 万帖时多样性检查被调用了 320 万次，占了整个请求 57 s 里的 55 s（cProfile 下测得）。冷启动的路径不走 merge，是线性增长。

修法分两层：
- **候选**：只取列表默认 SQL 顺序的前 `RANKING_CANDIDATE_LIMIT = 200` 行，在 Python 里精排。
  forum 和 market 的默认顺序是时间倒序，project 是"筹款中优先、截止日最近的在前"。
- **翻页**：第 200 行以后不再个性化，按同一个 SQL 顺序用 `OFFSET` 接着取。
  两段没有交集，所以把所有页走一遍，每行恰好出现一次，`total` 仍是真实总数。
  project 中查看者自己的项目照旧排在最前，单独查询。
  market 原来在 Python 里排除"已经买过的"商品，现在改成 SQL 的 `NOT IN (子查询)`，这样后半段和候选段的过滤条件一致。
  默认每页 20 条时，前 10 页是个性化排序。

`tests/integration/test_ranking_candidates.py` 把上限设为 5、造 12 行数据，断言排序函数收到的候选不超过 5 个，
并把所有页走一遍，确认不重复、不遗漏。修复前三个用例全部失败（排序函数收到了 12 / 12 / 11 个）。

复现（`backend/` 下，PG 要先起来）：

```bash
uv run python ../tools/load_test/list_ranking_probe.py 200 2000 20000
PROBE_PAGE=11 uv run python ../tools/load_test/list_ranking_probe.py 20000
```

probe 在进程内直接调用 service，数据库是单独的 `carbonsnap_probe_test`。每页 20 条，看第 1 页。
时间取 3 次的中位数，内存是 tracemalloc 记录的单次调用峰值。

| 全站行数 | 列表 | 冷启动 修复前 → 后 | 有画像 修复前 → 后 | 内存峰值 修复前 → 后 |
|---|---|---|---|---|
| 200 | forum | 27 → 25 ms | 38 → 28 ms | 0.7 → 0.7 MB |
| 2000 | forum | 120 → 21 ms | 321 → 41 ms | 7.1 → 0.7 MB |
| 20000 | forum | 1118 → 39 ms | 18281 → 49 ms | 71.5 → 0.7 MB |
| 2000 | project | 97 → 27 ms | 315 → 43 ms | 7.2 → 0.7 MB |
| 20000 | project | 987 → 51 ms | 14575 → 183 ms | 69.7 → 0.7 MB |
| 2000 | market | 114 → 16 ms | 310 → 27 ms | 6.9 → 0.6 MB |
| 20000 | market | 950 → 42 ms | 15310 → 41 ms | 67.7 → 0.6 MB |

2 万行时看第 11 页（已经进入 SQL 那一段）：forum 53 / 58 ms，project 58 / 250 ms，market 49 / 56 ms。
每页仍是 20 条，`total` 仍是 20000，SQL 只多 1 条，就是取后半段的那次查询。

SQL 条数：forum 和 market 不变。project 多 1–2 条：原来一次查出全部项目，现在拆成计数、自己的项目、候选三条。

**后续：merge 改成接近线性** ✅ 已修复。上面修完后，merge 本身仍是 O(N²)，只是 N 被固定在 200。
project 在 2 万行时的 183 ms 就是最坏情况：probe 里截止日期按 `i % 60` 循环，截止日最近的 200 个候选恰好全是同一个 topic，
多样性限制每次都要把整个池子扫一遍，而且每次检查都要重算候选和最近两行的主 topic。
修法（`app/services/recommendation/merge.py`，三个列表共用）：多样性限制最多只会禁掉一个 topic，也就是最近两行共同的那个 topic。
所以每个池子按主 topic 分成若干个队列，保持池内顺序；"第一个可用的行"就是各队列队首里位置最小的那个，被禁的那个 topic 的队列直接跳过。
已经从别的池取走的行留在队列里，等它到了队首再丢掉。主 topic 每行只算一次。每取一行的成本是 O(topic 数)，整个 merge 是 O(N × topic 数)。
`tests/unit/test_ranking_merge.py` 在测试文件里保留了一份原来的实现作为参照，用 300 组随机输入（池子之间有重叠、1–5 个 topic）
逐个元素对比三个 `merge_ranked_*` 的输出，再加上几个手写的用例（包括全部候选属于同一个 topic 的情况）。改之前和改之后都是全绿，说明输出顺序没变。

| 单独测 merge，全部候选属于同一个 topic | 修复前 | 修复后 |
|---|---|---|
| N = 200 | 47.9 ms | 0.4 ms |
| N = 1000 | 1792 ms | 2.3 ms |
| N = 2000 | 8739 ms | 4.8 ms |

probe 2 万行的 project history：102 → 36 ms，和 cold（36 ms）持平。这次修复前测的是 102 ms，不是上表的 183 ms，因为两次测量时机器状态不同。
现在调大 `RANKING_CANDIDATE_LIMIT`，merge 不会再成为瓶颈。

**测量时踩的坑**：第一次测，未登录论坛 2 万帖要 2.1 s。原因是刚批量插完数据、PG 还没有统计信息，执行计划选错了。
跑过 `ANALYZE` 之后同一条 SQL 只要 16 ms。probe 现在 seed 完会先跑一次 `ANALYZE`。

## 查过但没有发现问题的

- **SQLite 写锁**：12 个 worker、20 个用户跑了 2 分钟，没有出现 `database is locked`。
- **服务端自身的处理开销**：一轮对话里除去等 LLM 的时间，只有约 0.1 s。

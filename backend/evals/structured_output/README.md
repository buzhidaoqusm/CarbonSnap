# 结构化输出评测（P2 E2）

对话决策路径上有 4 个返回 JSON 的调用：路由、记忆提取、case resolver、回收分析 stage1。这个评测衡量它们拿到的回复能不能用。
`cases.json` 里的用例都是专门为这个评测写的，没有复用 prompt 里的 few-shot 示例；每个用例发一次请求。
`results/` 下是每次运行的完整记录：原始回复、函数输出、用量记录。

```bash
LLM_PROVIDER=openrouter OPENROUTER_MODEL=nvidia/nemotron-3.5-super-vl:free LLM_FALLBACK_PROVIDER= AI_LLM_AUX_TIMEOUT_SECONDS=60 AI_LLM_MAX_RETRIES=0 uv run python -m scripts.eval_structured_output --label <name>
```

- 免费 key 每天只有 50 次请求，一遍评测要用 25 次。
- `AI_LLM_MAX_RETRIES=0`：SDK 每重试一次也要占一次额度。
- 辅助调用的超时调到 60 s：免费模型可能比生产环境的 15 s 慢，而超时和 JSON 格式没有关系，不该混进统计。

## 2026-10-21：`nvidia/nemotron-3.5-super-vl:free`

- before：prompt 里要求"只返回 JSON"，再用 `_parse_json_object` 解析：先去掉代码块标记，失败时用正则 `\{.*\}` 抠出对象。
- after：strict `json_schema` 加 Pydantic 校验，删掉了正则兜底。

两遍各有几次失败出在 provider 那边：0.5 s 内返回的 500，或者内容为空。这些都单独统计，不算进格式和正确率。
after 那一遍，记忆提取 6 次里有 4 次 500，所以又重跑了一遍记忆提取（after-memory-rerun），结果 6/6 都正常，说明那几次 500 和 schema 无关。

| | before | after |
|---|---|---|
| 拿到回复的调用 | 22 / 25 | 19 / 25（重跑记忆后 6 / 6） |
| 回复是干净的 JSON | 22 / 22 | 19 / 19 |
| 包在代码块里 / 夹在文字里 | 0 / 0 | 0 / 0 |
| 符合约定格式 | 22 / 22 | 19 / 19 |
| 记忆提取：`memory_service` 能读出来的记忆 | **2 / 4** | **2 / 2；重跑 5 / 5** |
| 记忆提取：有回复时结果正确 | 2 / 4 | 2 / 2；重跑 6 / 6 |
| router / resolver：有回复时结果正确 | 11 / 11，4 / 4 | 10 / 10，4 / 4 |
| stage1：有回复时材质判断正确 | 3 / 3 | 2 / 3（水瓶被判成 "reusable water bottle"，没有提到材质） |

结论：
- **这个模型只靠 prompt 也几乎从不出 JSON 格式错误**，正则兜底一次都没用上。
- 真正的问题是**字段约定**：prompt 只写了 "`value`: object"，模型就自己决定键名，返回 `{"style": "concise"}`，而 `memory_service` 读的是 `value["value"]`。偏好存进了库，却从来没有生效。schema 给每种值规定了字段名，这个问题就没有了。
- stage1 的 normalizer 在 try 之外对回复调用 `float()`，回复里的重量是 `"0.5 kg"` 这样的字符串时会直接抛出异常，没有走兜底。schema 校验把这种回复挡在了 normalizer 之前（见 `tests/unit/test_structured_outputs.py`）。

延迟中位数：router 5.5 → 6.3 s，resolver 2.3 → 5.8 s，stage1 18.7 → 7.4 s，记忆提取 8.8 → 4.3 s（取重跑那一遍）。
每类只有 3–12 条用例，免费 endpoint 本身又不稳定，这些延迟数字只能说明加上 schema 后没有出现数量级的变慢，不能说明谁快谁慢。

另外，before 那一遍有 2 次调用在 120 s 后才返回，内容为空，而读超时设的是 60 s。见 docs/PERFORMANCE_ISSUES.md #16。

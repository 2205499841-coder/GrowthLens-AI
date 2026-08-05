# AI 增长报告

## MVP 边界

AI 报告模块不读取 Excel 文件或用户明细，只接收后端已经完成的数据理解
上下文与聚合结果：

- `analysis_context`
- `schema_mapping`
- `data_quality`
- `metrics`
- `funnel`
- `channels`

接口为 `POST /api/ai/report`。请求出现额外的原始数据字段时会返回 422。

## 输出契约

报告使用固定结构输出：

- `summary`：一句话业务诊断；
- `key_findings`：2-3 条问题诊断，每条包含问题、证据和对应建议；
- `channel_strategy`：基于真实渠道表现差异生成差异化策略；
- `growth_actions`：2-3 条行动建议、目标指标和预期方向；

## Prompt 设计

System Prompt 将角色、任务、格式与事实约束分开定义，核心规则为：

1. 用 `analysis_context` 确定分析类型和优先指标；
2. 用 `schema_mapping` 理解字段语义，不读取原始数据；
3. 只使用 `metrics`、`funnel`、`channels` 中的结果作为诊断事实；
4. evidence 中的数字必须来自输入；
5. 不补充渠道、用户画像、行业基准或业务事件；
6. 不把原因假设写成事实；
7. 不声称读取过 Excel 原始数据。

完整 Prompt 常量位于 `backend/app/services/ai_report.py`。

## Provider 设计

`AIReportProvider` 协议将报告业务逻辑与模型供应商隔离。默认
`AI_PROVIDER=deepseek`，由 `DeepSeekAIReportProvider` 使用 OpenAI SDK
兼容接口调用 `https://api.deepseek.com`。

`OpenAICompatibleAIReportProvider` 统一负责 Chat Completions 调用、JSON
解析、Pydantic Schema 校验与异常转换。DeepSeek 与未来 OpenAI Provider
只负责各自的密钥、模型和 Base URL 配置，前端与报告输出契约无需变化。

DeepSeek JSON Output 的调用参数为：

```python
response_format={"type": "json_object"}
```

System Prompt 同时包含 JSON 字段示例，并要求模型不输出 Markdown 或额外
说明。模型响应还会经过 `AIReportResponse` 校验，并检查渠道名称是否来自
输入数据。

默认环境变量：

```env
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=
AI_MODEL=deepseek-v4-pro
```

`DEEPSEEK_API_KEY` 只从运行环境读取，不写入代码或 Git。缺少密钥时接口
返回 503，不会静默使用虚假报告。

本地开发或自动测试可切换确定性的 Mock Provider：

```env
AI_PROVIDER=mock
```

未来切换 OpenAI 时使用同一个输出结构：

```env
AI_PROVIDER=openai
OPENAI_API_KEY=
AI_MODEL=your-openai-model
```

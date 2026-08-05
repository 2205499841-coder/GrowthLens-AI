# AI 增长报告

## MVP 边界

AI 报告模块不读取 Excel 文件或用户明细，只接收后端已经计算完成的四类
聚合结果：

- `data_quality`
- `metrics`
- `funnel`
- `channels`

接口为 `POST /api/ai/report`。请求出现额外的原始数据字段时会返回 422。

## 输出契约

报告使用固定结构输出：

- `summary`：一句话总结；
- `key_insights`：2-3 条洞察，包含数据依据、原因假设和置信度；
- `channel_opportunities`：只引用输入中存在的渠道；
- `growth_actions`：2-3 条行动建议、目标指标和预期方向；
- `limitations`：说明数据限制。

## Prompt 设计

System Prompt 将角色、任务、格式与事实约束分开定义，核心规则为：

1. 只使用输入中的四类聚合结果；
2. evidence 中的数字必须来自输入；
3. 不补充渠道、用户画像、行业基准或业务事件；
4. interpretation 必须以“可能”“推测”或“假设”表达；
5. 样本量或完整度不足时下调置信度；
6. 不声称读取过 Excel 原始数据。

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

# AI 增长报告

## MVP 边界

AI 报告模块不读取 Excel 文件或原始业务明细，只接收后端已经完成的
结构化分析结果。

- `user_level`：数据质量、增长指标、用户漏斗和渠道表现；
- `aggregate_metrics`：报表周期、筛选条件、维度表现、维度漏斗诊断、
  重点经营洞察、异常和数据限制。

聚合经营上下文最多保留优先级最高或流量最大的 20 个维度值，不包含
文件名、Sheet、源字段和完整 Excel 内容。

接口为 `POST /api/ai/report`。请求出现额外的原始数据字段时会返回 422。

## 输出契约

报告使用固定结构输出：

- `core_conclusion`：一段核心业务结论；
- `key_issues`：最多 3 条重点问题、证据、影响和置信度；
- `priority_actions`：最多 3 条建议动作、适用对象、原因和目标指标；
- `opportunities`：最多 2 条增长机会；
- `limitations`：数据限制。

模型只为每条证据返回 `evidence_ref` 和不含数字的 `interpretation`。
服务端检查引用后，按引用顺序注入 `display_values`；数字和单位不再由模型
自由生成。一条证据可引用多个后端字段。

## Prompt 设计

System Prompt 将角色、任务、格式与事实约束分开定义，核心规则为：

1. 优先使用后端已经生成的结构化经营洞察；
2. 不重新计算或修改任何指标；
3. AI 草稿中的自由文本原则上不写数字；
4. evidence 必须引用真实 `evidence_ref`，显示值由后端注入；
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
说明。模型响应先经过草稿 Schema 和自由文本数字校验，再由后端注入证据
显示值并生成最终 `AIReportResponse`。百分比与百分点保持严格区分。

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

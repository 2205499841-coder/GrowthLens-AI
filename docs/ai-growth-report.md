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

`AIReportProvider` 协议将报告业务逻辑与模型供应商隔离。当前
`AI_REPORT_PROVIDER=mock`，由 `MockAIReportProvider` 根据真实聚合指标
生成确定性结果，便于本地开发、自动测试和作品集演示。

已预留环境变量：

```env
AI_REPORT_PROVIDER=mock
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6
```

真实 OpenAI Provider 不在本阶段范围内。后续实现时，只需新增一个遵循
`AIReportProvider` 协议的适配器，并继续返回同一个 `AIReportResponse`
结构，前端无需修改。

# GrowthLens Frontend

## 本地运行

```bash
pnpm install
pnpm dev
```

打开 <http://localhost:3000>。

复制环境变量示例：

```bash
cp .env.local.example .env.local
```

Dashboard 默认调用：

```text
POST http://localhost:8000/api/analysis/growth
```

页面根据 `dataset_type` 展示可用结果。当前完整支持用户级数据质量、
核心指标、用户漏斗、渠道对比和统一 AI 增长诊断；聚合经营报表已具备
类型识别与占位状态，暂不计算完整经营指标。
前端不重复计算业务指标。

AI 报告由用户在 Dashboard 主动触发，调用：

```text
POST http://localhost:8000/api/ai/report
```

页面将 `analysis_context`、`schema_mapping` 与聚合指标交给后端 Provider
生成业务诊断，默认 Provider 为 DeepSeek；前端不持有 API Key，也不直接
调用模型服务。

## 检查

```bash
pnpm lint
pnpm build
```

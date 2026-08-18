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
核心指标、用户漏斗、渠道对比和统一 AI 增长诊断；聚合经营报表支持
动态漏斗、维度诊断、重点经营洞察和异步 AI 增长诊断。
前端不重复计算业务指标。

用户级报告可在 Dashboard 主动触发；聚合经营分析完成后会异步生成，调用：

```text
POST http://localhost:8000/api/ai/report
```

页面只把后端已验证的结构化分析结果交给报告接口。Dashboard 不依赖 AI
请求成功；失败时保留分析结果并提供重新生成入口。前端不持有 API Key，
也不直接调用模型服务。

## 检查

```bash
pnpm lint
pnpm build
```

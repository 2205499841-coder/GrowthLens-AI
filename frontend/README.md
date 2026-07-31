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

页面展示数据质量、核心指标、用户漏斗、渠道对比图、渠道明细表和
结构化 AI 增长报告。
前端不重复计算业务指标。

AI 报告由用户在 Dashboard 主动触发，调用：

```text
POST http://localhost:8000/api/ai/report
```

当前页面会明确标记 `Mock LLM`，方便作品集演示且不会产生外部 API 调用。

## 检查

```bash
pnpm lint
pnpm build
```

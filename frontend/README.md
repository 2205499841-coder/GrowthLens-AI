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

页面展示数据质量、核心指标、用户漏斗、渠道对比图和渠道明细表。
前端不重复计算业务指标。

## 检查

```bash
pnpm lint
pnpm build
```

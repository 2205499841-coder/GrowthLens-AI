# GrowthLens AI

面向写真行业增长运营场景的 AI 产品经理作品集 Demo。

AI user growth analysis assistant for lifestyle service businesses.

当前开发范围仅包含：

1. Excel 上传
2. 数据清洗
3. 指标计算
4. 漏斗分析
5. Dashboard 展示
6. AI 增长报告（DeepSeek Provider）

当前不包含 AI 问答、Agent、RAG、登录、数据库、用户系统和多项目管理。

## 项目结构

```text
growthlens-ai/
├── frontend/              # Next.js Dashboard
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── types/
├── backend/               # FastAPI 数据服务
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   └── services/
│   └── tests/
├── sample_data/           # 写真行业演示数据
└── docs/                  # 字段模板与接口说明
```

前后端的具体运行命令将在各自目录的 README 中维护。

## 当前进度

- Step 3：Excel 上传与解析；
- Step 4：数据清洗、增长指标、漏斗及渠道分析；
- Step 5：单页增长 Dashboard；
- Step 6：结构化 AI 增长报告（默认使用 DeepSeek Provider）；
- AI 问答尚未实现。

写真行业演示数据位于 `sample_data/portrait_growth_demo.xlsx`，可通过
`sample_data/generate_sample_data.py` 使用固定随机种子重新生成。

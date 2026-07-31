# GrowthLens AI

面向写真行业增长运营场景的 AI 产品经理作品集 Demo。

AI user growth analysis assistant for lifestyle service businesses.

当前开发范围仅包含：

1. Excel 上传
2. 数据清洗
3. 指标计算
4. 漏斗分析
5. Dashboard 展示

当前不包含 AI 问答、登录、数据库、用户系统和多项目管理。

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

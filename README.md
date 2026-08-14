# GrowthLens AI

面向增长运营与产品运营人员的 AI 数据诊断助手。

读取业务平台导出的 Excel 报表，识别数据结构并生成可追溯的增长分析。

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
├── sample_data/           # 通用脱敏示例数据
└── docs/                  # 字段模板与接口说明
```

前后端的具体运行命令将在各自目录的 README 中维护。

## 当前进度

- Step 3：Excel 上传与解析；
- Step 4：数据清洗、增长指标、漏斗及渠道分析；
- Step 5：单页增长 Dashboard；
- Step 6：结构化 AI 增长报告（默认使用 DeepSeek Provider）；
- AI 问答尚未实现。

通用脱敏示例数据位于
`sample_data/growthlens_synthetic_user_growth.xlsx`，可通过
`sample_data/generate_sample_data.py` 使用固定随机种子重新生成。

## 部署

FastAPI 后端使用仓库根目录的 `render.yaml` 部署到 Render。生产密钥只在
Render Dashboard 配置，详细步骤见 [Render 后端部署](docs/render-deployment.md)。

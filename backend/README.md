# GrowthLens Backend

## 初始化

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 本地运行

```bash
uvicorn app.main:app --reload --port 8000
```

未设置 `BACKEND_CORS_ORIGINS` 时，后端默认允许本地前端
`http://localhost:3000` 和 `http://127.0.0.1:3000`。部署时通过逗号分隔的
环境变量配置实际前端域名：

```bash
BACKEND_CORS_ORIGINS=https://your-project.vercel.app,http://localhost:3000 uvicorn app.main:app --host 0.0.0.0 --port 8000
```

域名会自动去除首尾空格和末尾 `/`，重复值只保留一次。

健康检查：<http://localhost:8000/api/health>

接口文档：<http://localhost:8000/docs>

Excel 解析：

```bash
curl -X POST \
  -F "file=@/absolute/path/photo_growth.xlsx" \
  http://localhost:8000/api/uploads/parse
```

增长分析：

```bash
curl -X POST \
  -F "file=@../sample_data/portrait_growth_demo.xlsx" \
  http://localhost:8000/api/analysis/growth
```

响应统一包含 `data_quality`、`metrics`、`funnel` 和 `channels`。
详细口径见 [增长分析口径](../docs/growth-analysis.md)。

AI 增长报告：

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  --data @analysis_result.json \
  http://localhost:8000/api/ai/report
```

报告接口只接收增长分析结果中的 `data_quality`、`metrics`、`funnel`
和 `channels`。当前默认使用本地 Mock Provider，不会调用外部模型：

```bash
AI_REPORT_PROVIDER=mock uvicorn app.main:app --reload --port 8000
```

`OPENAI_API_KEY` 与 `OPENAI_MODEL` 已预留，但本阶段没有实现或启用真实
OpenAI Provider。接口与 Prompt 设计见
[AI 增长报告说明](../docs/ai-growth-report.md)。

## 测试

```bash
pytest
```

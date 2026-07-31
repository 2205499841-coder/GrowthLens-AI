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

## 测试

```bash
pytest
```

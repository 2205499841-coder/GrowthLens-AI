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

## 测试

```bash
pytest
```

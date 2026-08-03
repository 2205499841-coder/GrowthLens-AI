# Render 后端部署

## 部署配置

仓库根目录的 `render.yaml` 定义一个 FastAPI Web Service：

- Service：`growthlens-ai-api`
- Runtime：Python 3.12.13
- Region：Singapore
- Root Directory：`backend`
- Build Command：`pip install -r requirements.txt`
- Start Command：`uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check：`/api/health`

Render 的构建与启动命令会在 `backend` 目录执行。服务不需要数据库、磁盘或
前端构建步骤。

## 创建服务

推荐使用 Blueprint：

1. 确认待部署分支已经包含 `render.yaml` 和 Step 6 DeepSeek Provider；
2. 登录 Render，选择 **New > Blueprint**；
3. 连接 GitHub 仓库 `2205499841-coder/GrowthLens-AI`；
4. 选择包含本次部署配置的分支；正式发布前应合并并切换到 `main`；
5. Render 读取 `render.yaml` 后，填写两个标记为 `sync: false` 的变量；
6. 创建 Blueprint，等待构建、健康检查和发布完成。

也可以手动创建 **Web Service**，并按“部署配置”中的值填写 Root Directory、
Build Command、Start Command 和 Health Check Path。

## 生产环境变量

| Key | Value | 是否敏感 | 配置位置 |
| --- | --- | --- | --- |
| `AI_PROVIDER` | `deepseek` | 否 | Blueprint 已设置 |
| `AI_MODEL` | `deepseek-chat` | 否 | Blueprint 已设置 |
| `DEEPSEEK_API_KEY` | 真实 DeepSeek API Key | 是 | 仅 Render Dashboard |
| `BACKEND_CORS_ORIGINS` | 实际 Vercel HTTPS 域名 | 否 | Render Dashboard |
| `PYTHON_VERSION` | `3.12.13` | 否 | Blueprint 已设置 |

`BACKEND_CORS_ORIGINS` 只填写 Origin，不包含路径，不以 `/` 结尾。例如：

```text
https://growthlens-ai.vercel.app
```

如需同时允许 Vercel Production 与 Preview 域名，使用英文逗号分隔明确的
Origin。不要为方便测试配置 `*`。

## 发布后验证

假设 Render 地址为 `https://growthlens-ai-api.onrender.com`：

```bash
curl --fail https://growthlens-ai-api.onrender.com/api/health
```

预期返回 HTTP 200：

```json
{
  "status": "ok",
  "service": "GrowthLens API",
  "version": "0.1.0"
}
```

验证生产前端域名的 CORS 预检：

```bash
curl -i -X OPTIONS \
  -H "Origin: https://growthlens-ai.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  https://growthlens-ai-api.onrender.com/api/analysis/growth
```

响应应包含与 Origin 完全一致的 `access-control-allow-origin`。未配置的域名
不应获得该响应头。

最后上传写真演示 Excel，确认 `/api/analysis/growth` 返回分析结果，再将该
结果提交给 `/api/ai/report`，确认真实 DeepSeek 报告返回 200。不要使用健康
检查接口调用 DeepSeek，以免平台探活产生模型费用。

## 本地 Mock 模式

本地测试不需要真实 Key：

```bash
AI_PROVIDER=mock \
BACKEND_CORS_ORIGINS=http://localhost:3000 \
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Mock 模式只用于本地测试。Render 生产环境必须保持
`AI_PROVIDER=deepseek` 并配置 `DEEPSEEK_API_KEY`。

## 前端后续配置

本步骤不部署或修改 Vercel 前端。后端验证完成后，再在 Vercel 设置：

```env
NEXT_PUBLIC_API_BASE_URL=https://growthlens-ai-api.onrender.com
```

该变量只包含后端公开地址。`DEEPSEEK_API_KEY` 永远不应配置到 Vercel，
也不能使用 `NEXT_PUBLIC_` 前缀。

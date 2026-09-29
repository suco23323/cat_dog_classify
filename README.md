---
title: Cat Dog Classifier API
emoji: 🐱
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
pinned: false
---

# 猫狗分类 Demo

Vue 3 前端 + FastAPI/PyTorch CPU 后端的猫狗图片分类实验，适合作为免费部署的小型 Demo。

## 推荐部署架构

```text
浏览器
  ├── Vue 3 / Vite 静态页面  -> Vercel
  └── FastAPI API + 模型推理 -> Hugging Face Spaces(Gradio SDK, CPU Basic)
                                  └── best_model_opt20.pth
```

后端首选 **Hugging Face Spaces 的免费 Gradio CPU Space**：

- PyTorch 是 CPU 推理，不需要 GPU；
- 根目录 app.py 复用现有 FastAPI 应用，Space 首页由 Gradio 提供；
- 免费额度通常为 2 vCPU / 16 GB 内存，运行当前 ResNet 模型足够；
- 长期无人访问后可能休眠，首次请求需要冷启动；
- 免费环境没有可靠持久化，SQLite 历史记录和上传图片会在重建/重启后丢失，Demo 可接受。

备选方案：

| 平台 | 优点 | 注意 |
| --- | --- | --- |
| Google Cloud Run | 免费额度、自动扩缩容、稳定性较好 | 需要绑定结算账号，PyTorch 冷启动较慢 |
| Oracle Cloud Always Free VM | 可长期运行、可自己管理磁盘 | 需要自己配置系统、Nginx 和 HTTPS，ARM 实例可能缺货 |
| Render Free | 上手简单 | 免费实例内存较小且会休眠，PyTorch 有内存超限风险 |

不建议把 FastAPI/PyTorch 后端直接部署到 Vercel。Vercel 更适合当前 Vue 静态前端。

## 本地运行

### 后端

建议使用 Python 3.11。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements-cpu.txt
pip install -r backend\requirements.txt
python -m uvicorn main:app --app-dir backend --reload --port 8000
```

打开 <http://127.0.0.1:8000/docs> 可查看 FastAPI 文档。

### 前端

```powershell
cd frontend
npm install
npm run dev
```

本地开发无需设置 `.env`，Vite 会把 `/api`、`/uploads`、`/result` 代理到 `127.0.0.1:8000`。

## 部署步骤

### 1. 上传 GitHub

仓库根目录已经包含 Hugging Face Gradio 入口 `app.py`、根依赖 `requirements.txt` 和后端代码，不能只上传 `frontend/` 或 `backend/` 子目录。

```powershell
git init
git add .
git commit -m "chore: prepare cat dog demo for deployment"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

`best_model_opt20.pth` 约 45 MB，低于 GitHub 单文件 100 MB 限制，可以正常提交。上传图片、历史记录、SQLite 数据库、`node_modules` 和构建产物已由 `.gitignore` 排除。

### 2. 部署 FastAPI 后端到 Hugging Face Spaces（Gradio SDK）

1. 登录 Hugging Face，创建一个新 Space。
2. 选择 **Gradio** SDK、Blank 模板和 **CPU Basic** 免费硬件。
3. 选择从 GitHub 仓库导入，或者把当前仓库推送到 Space 仓库。
4. 确认 README 顶部保留 `sdk: gradio`、`sdk_version: 5.49.1` 和 `app_file: app.py`。
5. 部署完成后确认健康检查可用：

```text
https://<你的-space>.hf.space/api/health
```

应返回：

```json
{"status":"ok"}
```

### 3. 配置后端跨域

在 Hugging Face Space 的 Settings -> Variables and secrets 中，先添加占位值或最终 Vercel 域名：

```text
CORS_ORIGINS=https://<你的项目>.vercel.app
```

如果要同时允许 Vercel 的预览域名，可以额外添加：

```text
CORS_ORIGIN_REGEX=https://.*\.vercel\.app
```

正式 Demo 建议只保留明确的 `CORS_ORIGINS`，不要长期使用过宽的预览域名正则。

### 4. 部署前端到 Vercel

1. 在 Vercel 导入同一个 GitHub 仓库。
2. Root Directory 设置为 `frontend`。
3. Framework Preset 选择 `Vite`。
4. 添加环境变量：

```text
VITE_API_BASE_URL=https://<你的-space>.hf.space/api
```

5. 点击 Deploy。
6. 部署完成后，把 Vercel 正式域名回填到 Hugging Face 的 `CORS_ORIGINS`，并重启/重新部署后端。

前端代码会使用 `VITE_API_BASE_URL` 请求 API，并把后端返回的 `/uploads/...`、`/result/...` 自动转换成 Hugging Face 的完整地址。

## 接口概览

- `GET /api/health`：健康检查
- `POST /api/classify`：单张分类
- `POST /api/batch`：批量任务提交
- `GET /api/batch/status/{job_id}`：批量任务进度
- `GET /api/history`：历史记录
- `GET /docs`：Swagger 文档

## Demo 上线后的注意事项

- 公开接口没有鉴权，别人可以调用批量接口。对外演示时建议把 `backend/config.py` 中的 `MAX_BATCH_FILES` 调低，或后续增加 API Key、限流。
- Hugging Face 免费实例可能休眠，第一次识别需要等待模型和 Python 运行时启动。
- 当前历史记录使用本地 SQLite。免费 Space 重启后数据可能丢失；如果需要持久化，应改用云数据库和对象存储。
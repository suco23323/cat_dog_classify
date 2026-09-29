"""Hugging Face Spaces Gradio 免费部署入口。

该文件只在 HF Space 使用：
- 复用 backend/main.py 的 FastAPI 应用与全部 /api 路由；
- 用 Gradio 提供一个简单的 Space 首页；
- 最终由 Uvicorn 监听 7860 端口。

因此前端仍然访问 /api/classify、/api/health 等接口，无需修改 API 契约。
"""
from pathlib import Path
import sys

import gradio as gr
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app as fastapi_app  # noqa: E402


with gr.Blocks(title="猫狗分类 API") as demo:
    gr.Markdown("# 🐱 猫狗分类 API")
    gr.Markdown(
        "FastAPI 后端正在运行。前端请使用 `/api` 前缀访问接口，"
        "也可以打开 [Swagger 文档](/docs) 进行测试。"
    )
    gr.Textbox(value="/api/health", label="健康检查地址", interactive=False)


# Gradio 挂在根路径，FastAPI 已注册的 /api、/docs、/uploads、/result 会优先匹配。
app = gr.mount_gradio_app(fastapi_app, demo, path="/")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
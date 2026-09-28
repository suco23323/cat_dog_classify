"""M8 API 路由层:FastAPI 应用、统一错误响应与静态文件挂载。

只做路由、协议转换与错误映射,业务全部在 M7;失败统一返回 `{"detail": 中文提示}`。
阻塞推理接口使用普通 `def`(FastAPI 线程池执行)。
"""
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List

import config
import database
import file_storage
import service
from config import MSG_HISTORY_EMPTY_EXPORT, MSG_JOB_NOT_FOUND, MSG_RECOGNIZE_FAILED
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from model_loader import get_model
from schemas import (
    BatchSubmitResponse,
    ClassifyResponse,
    HistoryPageResponse,
    JobStatusResponse,
)

# 挂载静态目录前必须先保证目录存在(StaticFiles 默认 check_dir=True)
config.ensure_dirs()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """启动时初始化数据库并加载模型一次(常驻内存,日志出现"模型加载完成")。"""
    database.init_db()
    get_model()
    yield


app = FastAPI(title="猫狗分类识别后端", lifespan=lifespan)

# 允许前端域名跨域访问。线上通过 CORS_ORIGINS 配置,多个域名用英文逗号分隔。
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX") or None,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(config.UPLOAD_DIR)), name="uploads")
app.mount("/result", StaticFiles(directory=str(config.RESULT_DIR)), name="result")

# 记录不存在时该提示文案 config 无对应常量,此处内联一处(设计 §6 未单独定义)
MSG_RECORD_NOT_FOUND = "记录不存在或已删除"


@app.get("/api/health")
def health() -> Dict[str, str]:
    """健康检查:前端据此探测后端是否就绪(TC-13)。"""
    return {"status": "ok"}


@app.post("/api/classify", response_model=ClassifyResponse)
def classify(file: UploadFile = File(...)) -> Any:
    """单张识别:multipart `file` → 结构化结果;校验失败 400,意外异常 500。"""
    try:
        data = file.file.read()
        filename = file.filename or "upload"
        return service.classify_single(data, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=MSG_RECOGNIZE_FAILED) from exc


@app.post("/api/batch", response_model=BatchSubmitResponse)
def batch(files: List[UploadFile] = File(...)) -> Any:
    """批量识别提交:multipart `files[]` → {job_id, total};超上限 400。"""
    try:
        items = [(f.file.read(), f.filename or "upload") for f in files]
        job_id, total = service.submit_batch(items)
        return {"job_id": job_id, "total": total}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=MSG_RECOGNIZE_FAILED) from exc


@app.get("/api/batch/status/{job_id}", response_model=JobStatusResponse)
def batch_status(job_id: str) -> Any:
    """批量任务状态轮询(设计 §4.4);任务不存在 404(设计 §1.4 内存态)。"""
    status = service.get_job_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail=MSG_JOB_NOT_FOUND)
    return status


@app.get("/api/history", response_model=HistoryPageResponse)
def history(page: int = 1, page_size: int = 10) -> Any:
    """历史分页查询(倒序)。"""
    total, items = database.query_page(page, page_size)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@app.delete("/api/history/{record_id}")
def delete_history_record(record_id: int) -> Dict[str, Any]:
    """删除单条历史并联动删除 uploads/ 图片文件(设计 §5.4)。"""
    stored_path = database.delete_record(record_id)
    if stored_path is None:
        raise HTTPException(status_code=404, detail=MSG_RECORD_NOT_FOUND)
    file_storage.delete_file(stored_path)
    return {"ok": True}


@app.delete("/api/history")
def clear_history() -> Dict[str, Any]:
    """清空全部历史并联动删除全部图片文件(设计 §5.4)。"""
    paths = database.clear_all()
    for stored_path in paths:
        file_storage.delete_file(stored_path)
    return {"ok": True, "deleted": len(paths)}


@app.get("/api/history/export")
def history_export() -> Any:
    """导出历史 CSV(同时保存 result/);空历史 400 中文提示。"""
    try:
        filename = service.export_history()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=MSG_HISTORY_EMPTY_EXPORT) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=MSG_RECOGNIZE_FAILED) from exc
    return FileResponse(
        path=config.RESULT_DIR / filename,
        media_type="text/csv",
        filename=filename,
    )

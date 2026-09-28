"""M7 业务编排模块:单张识别编排、批量异步任务(内存 JobRegistry)与历史导出。

批量任务状态仅存后端内存(设计 §1.4):后端重启/页面刷新后进度不可查,
但每张结果实时写入历史,数据不丢失;任务不支持取消、不允许超过批量上限。
"""
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import database
import file_storage
import predict
import preprocess
from config import (
    JOB_RETENTION,
    MAX_BATCH_FILES,
    MSG_BATCH_TOO_MANY,
    MSG_HISTORY_EMPTY_EXPORT,
    MSG_INVALID_FORMAT_SIZE,
)

# 批量任务输入项:(文件字节, 原始文件名)
FileItem = Tuple[bytes, str]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class JobRegistry:
    """内存任务注册表:线程锁保护,仅内存保存,创建时淘汰最旧任务(设计 §5.3)。"""

    def __init__(self, retention: int = JOB_RETENTION) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._retention = retention

    def create_job(self, total: int) -> str:
        """创建任务并返回 job_id;顺带把任务数控制在保留数以内。"""
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "total": total,
                "done": 0,
                "current_filename": None,
                "results": [],
                "summary": None,
                "csv_filename": None,
                "error": None,
                "created_at": _now(),
            }
            self._prune_locked()
        return job_id

    def _prune_locked(self) -> None:
        """淘汰最旧任务直到数量 ≤ 保留数(调用方需持有锁)。"""
        while len(self._jobs) > self._retention:
            oldest = min(self._jobs, key=lambda key: self._jobs[key]["created_at"])
            self._jobs.pop(oldest, None)

    def update_progress(self, job_id: str, done: int, current_filename: Optional[str]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job["status"] = "running"
            job["done"] = done
            job["current_filename"] = current_filename

    def complete_job(
        self,
        job_id: str,
        summary: Dict[str, int],
        results: List[Dict[str, Any]],
        csv_filename: str,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job["status"] = "succeeded"
            job["summary"] = summary
            job["results"] = results
            job["csv_filename"] = csv_filename

    def fail_job(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job["status"] = "failed"
            job["error"] = error

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job is not None else None


_REGISTRY = JobRegistry()


def classify_single(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """单张识别编排:校验 → 预处理 → 推理 → 存图 → 落库,返回结构化结果。

    字段与 M9 `ClassifyResponse` 一致;校验/解码/推理失败抛出带中文文案的异常。
    """
    if not preprocess.is_supported_suffix(filename) or not preprocess.is_within_size_limit(len(file_bytes)):
        raise ValueError(MSG_INVALID_FORMAT_SIZE)
    image = preprocess.load_rgb_image(file_bytes)
    tensor = preprocess.preprocess_to_tensor(image)
    probs = predict.predict_tensor(tensor)
    result = predict.format_result(probs)
    stored = file_storage.save_upload(file_bytes, filename)
    created_at = _now()
    record_id = database.insert_record(
        filename=filename,
        stored_path=stored,
        predict=result["predict"],
        prob_cat=result["probs"]["cat"],
        prob_dog=result["probs"]["dog"],
        confidence=result["confidence"],
        created_at=created_at,
    )
    return {
        "id": record_id,
        "filename": filename,
        "predict": result["predict"],
        "predict_label": result["predict_label"],
        "confidence": result["confidence"],
        "probs": result["probs"],
        "image_url": "/uploads/" + stored,
        "created_at": created_at,
    }


def validate_batch(files: List[FileItem]) -> None:
    """批量数量校验:超过上限抛出中文异常(单张坏文件在任务内逐张失败,不在此拦截)。"""
    if len(files) > MAX_BATCH_FILES:
        raise ValueError(MSG_BATCH_TOO_MANY)


def run_batch_job(job_id: str, files: List[FileItem]) -> None:
    """后台线程入口:逐张识别并更新进度,最后写 CSV 并置 succeeded;整体异常置 failed。"""
    total = len(files)
    results: List[Dict[str, Any]] = []
    success = 0
    failed = 0
    cat_count = 0
    dog_count = 0
    try:
        for index, (data, name) in enumerate(files, start=1):
            _REGISTRY.update_progress(job_id, index - 1, name)
            try:
                item = classify_single(data, name)
                results.append(
                    {
                        "filename": name,
                        "predict_label": item["predict_label"],
                        "confidence": item["confidence"],
                        "remark": "",
                    }
                )
                success += 1
                if item["predict"] == "cat":
                    cat_count += 1
                else:
                    dog_count += 1
            except Exception as exc:
                results.append(
                    {
                        "filename": name,
                        "predict_label": "-",
                        "confidence": None,
                        "remark": str(exc),
                    }
                )
                failed += 1
        csv_filename = file_storage.write_batch_csv(results)
        summary = {
            "total": total,
            "success": success,
            "failed": failed,
            "cat_count": cat_count,
            "dog_count": dog_count,
        }
        _REGISTRY.update_progress(job_id, total, None)
        _REGISTRY.complete_job(job_id, summary, results, csv_filename)
    except Exception as exc:
        _REGISTRY.fail_job(job_id, str(exc))


def submit_batch(files: List[FileItem]) -> Tuple[str, int]:
    """批量提交入口:校验 → 创建任务 → 启动守护线程 → 立即返回 (job_id, total)。"""
    validate_batch(files)
    job_id = _REGISTRY.create_job(len(files))
    thread = threading.Thread(target=run_batch_job, args=(job_id, files), daemon=True)
    thread.start()
    return job_id, len(files)


def _build_status(job: Dict[str, Any]) -> Dict[str, Any]:
    """由注册表内的原始 job 状态构造对外状态字典(设计 §4.4),便于单独测试。"""
    total = int(job["total"])
    done = int(job["done"])
    status: Dict[str, Any] = {
        "job_id": str(job["job_id"]),
        "status": str(job["status"]),
        "total": total,
        "done": done,
        "percent": round(done / total * 100, 1) if total else 0.0,
        "current_filename": job["current_filename"],
    }
    if job["status"] == "succeeded":
        status["summary"] = job["summary"]
        status["results"] = job["results"]
        status["csv_url"] = "/result/" + str(job["csv_filename"])
    elif job["status"] == "failed":
        status["error"] = job["error"]
    return status


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """查询任务状态(设计 §4.4);任务不存在返回 None(供 M8 转 404)。"""
    job = _REGISTRY.get_job(job_id)
    if job is None:
        return None
    return _build_status(job)


def export_history() -> str:
    """历史导出编排:全量查询 → 写 CSV 到 result/,返回文件名;空历史抛中文异常。"""
    records = database.query_all()
    if not records:
        raise ValueError(MSG_HISTORY_EMPTY_EXPORT)
    return file_storage.write_history_csv(records)

"""M6 文件与 CSV 读写模块:上传副本保存、文件删除、批量/历史 CSV 生成。

本模块是唯一写 `uploads/` 与 `result/` 的模块;CSV 编码 `utf-8-sig`;
删除文件采用"忽略不存在"策略(设计 §5.4 联动删除)。
目录路径经 `config` 模块动态访问,便于测试注入临时目录。
"""
import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from config import BATCH_COLUMNS, HISTORY_COLUMNS, MSG_CSV_WRITE_FAILED


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_upload(file_bytes: bytes, original_name: str) -> str:
    """保存上传副本到 `uploads/`,命名 `原文件名_YYYYmmdd_HHMMSS.扩展名`,返回文件名。

    若同一秒内同名文件已存在,追加 `_序号` 后缀,保证同名文件绝不覆盖(设计 §5.2 防重名意图)。
    """
    original = Path(original_name)
    stem = original.stem or "upload"
    suffix = original.suffix or ".bin"
    stored_name = f"{stem}_{_timestamp()}{suffix}"
    counter = 1
    while (config.UPLOAD_DIR / stored_name).exists():
        stored_name = f"{stem}_{_timestamp()}_{counter}{suffix}"
        counter += 1
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (config.UPLOAD_DIR / stored_name).write_bytes(file_bytes)
    return stored_name


def delete_file(stored_path: str) -> None:
    """删除 `uploads/` 下对应文件;文件不存在时静默忽略(设计 §5.4)。"""
    target = config.UPLOAD_DIR / stored_path
    try:
        target.unlink()
    except FileNotFoundError:
        pass


def _write_csv(path: Path, columns: List[str], rows: List[List[Any]]) -> None:
    """按 `utf-8-sig` 写入 CSV(自动创建父目录);任何 IO 错误统一转为中文 `RuntimeError`。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
    except OSError as exc:
        raise RuntimeError(MSG_CSV_WRITE_FAILED) from exc


def write_batch_csv(results: List[Dict[str, Any]], created_at: Optional[str] = None) -> str:
    """写批量结果 CSV 到 `result/batch_result_<ts>.csv`,返回文件名。

    `results` 每条含 `filename`/`predict_label`/`confidence`/`remark`;
    失败行 predict_label/confidence 填 "-"、remark 为原因(设计 §5.2)。
    """
    filename = f"batch_result_{created_at or _timestamp()}.csv"
    rows: List[List[Any]] = []
    for item in results:
        confidence = item.get("confidence")
        rows.append(
            [
                item.get("filename", ""),
                item.get("predict_label") or "-",
                "-" if confidence is None else confidence,
                item.get("remark", ""),
            ]
        )
    _write_csv(config.RESULT_DIR / filename, BATCH_COLUMNS, rows)
    return filename


def write_history_csv(records: List[Dict[str, Any]], created_at: Optional[str] = None) -> str:
    """写历史导出 CSV 到 `result/history_<ts>.csv`,返回文件名。

    `records` 每条含 `id`/`filename`/`predict_label`/`confidence`/`created_at`(M5 `query_all` 输出)。
    """
    filename = f"history_{created_at or _timestamp()}.csv"
    rows: List[List[Any]] = []
    for item in records:
        rows.append(
            [
                item.get("id", ""),
                item.get("filename", ""),
                item.get("predict_label", ""),
                item.get("confidence", ""),
                item.get("created_at", ""),
            ]
        )
    _write_csv(config.RESULT_DIR / filename, HISTORY_COLUMNS, rows)
    return filename

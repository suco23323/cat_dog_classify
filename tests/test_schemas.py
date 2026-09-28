"""tests/test_schemas.py —— M9 响应模型单元测试。

以 `doc/high-level-design.md` §4.3/§4.4 与 `doc/proposal.md` §6 的示例 JSON
构造各模型,断言 `model_dump_json()` 序列化结果与示例一致,
并覆盖可选字段缺省(None)场景。
"""
import json
from typing import Any, Dict

from pydantic import BaseModel
from schemas import BatchSubmitResponse, ClassifyResponse, HistoryItem, HistoryPageResponse, JobStatusResponse


def _dump(model: BaseModel) -> Dict[str, Any]:
    """把模型序列化为 JSON 字符串再解析回 dict,校验最终线格式。"""
    dumped = json.loads(model.model_dump_json())
    assert isinstance(dumped, dict)
    return dumped


def test_classify_response_matches_proposal_example() -> None:
    """proposal §6 单张识别成功响应示例。"""
    example: Dict[str, Any] = {
        "id": 42,
        "filename": "cat_001.jpg",
        "predict": "cat",
        "predict_label": "猫",
        "confidence": 0.924,
        "probs": {"cat": 0.924, "dog": 0.076},
        "image_url": "/uploads/cat_001_20260910_103000.jpg",
        "created_at": "2026-09-10 10:30:00",
    }
    response = ClassifyResponse(**example)
    assert _dump(response) == example


def test_batch_submit_response_matches_design_example() -> None:
    """设计 §4.3 批量提交响应 `{"job_id": "...", "total": n}`。"""
    example: Dict[str, Any] = {
        "job_id": "a1b2c3d4-0000-1111-2222-333344445555",
        "total": 100,
    }
    response = BatchSubmitResponse(**example)
    assert _dump(response) == example


def test_job_status_running_matches_design_example() -> None:
    """设计 §4.4 进行中示例:可选字段序列化为 null。"""
    example: Dict[str, Any] = {
        "job_id": "a1b2c3d4-0000-1111-2222-333344445555",
        "status": "running",
        "total": 100,
        "done": 37,
        "percent": 37.0,
        "current_filename": "cat_038.jpg",
        "summary": None,
        "results": None,
        "csv_url": None,
        "error": None,
    }
    response = JobStatusResponse(**example)
    assert _dump(response) == example


def test_job_status_succeeded_matches_design_example() -> None:
    """设计 §4.4 成功终态示例:携带 summary/results/csv_url。"""
    example: Dict[str, Any] = {
        "job_id": "a1b2c3d4-0000-1111-2222-333344445555",
        "status": "succeeded",
        "total": 100,
        "done": 100,
        "percent": 100.0,
        "current_filename": None,
        "summary": {"total": 100, "success": 98, "failed": 2, "cat_count": 50, "dog_count": 48},
        "results": [
            {"filename": "a.jpg", "predict_label": "猫", "confidence": 0.924, "remark": ""},
            {
                "filename": "坏文件.txt",
                "predict_label": "-",
                "confidence": None,
                "remark": "无法读取该图片,请上传 jpg/png/bmp 等图片文件",
            },
        ],
        "csv_url": "/result/batch_result_20260910_140000.csv",
        "error": None,
    }
    response = JobStatusResponse(**example)
    assert _dump(response) == example


def test_job_status_failed_matches_design_example() -> None:
    """设计 §4.4 失败终态示例:仅 error 有值,其余可选字段为 null。"""
    example: Dict[str, Any] = {
        "job_id": "a1b2c3d4-0000-1111-2222-333344445555",
        "status": "failed",
        "total": 100,
        "done": 37,
        "percent": 37.0,
        "current_filename": None,
        "summary": None,
        "results": None,
        "csv_url": None,
        "error": "识别失败,请重试",
    }
    response = JobStatusResponse(**example)
    assert _dump(response) == example


def test_job_status_optional_fields_default_to_none() -> None:
    """可选字段缺省场景:未传入时默认 None 且序列化为 null。"""
    response = JobStatusResponse(job_id="job-1", status="queued", total=10, done=0, percent=0.0)
    assert response.current_filename is None
    assert response.summary is None
    assert response.results is None
    assert response.csv_url is None
    assert response.error is None
    assert _dump(response) == {
        "job_id": "job-1",
        "status": "queued",
        "total": 10,
        "done": 0,
        "percent": 0.0,
        "current_filename": None,
        "summary": None,
        "results": None,
        "csv_url": None,
        "error": None,
    }


def test_history_item_matches_proposal_example() -> None:
    """proposal §6 历史响应 items 元素示例。"""
    example: Dict[str, Any] = {
        "id": 42,
        "filename": "cat_001.jpg",
        "predict_label": "猫",
        "confidence": 0.924,
        "probs": {"cat": 0.924, "dog": 0.076},
        "image_url": "/uploads/cat_001_20260910_103000.jpg",
        "created_at": "2026-09-10 10:30:00",
    }
    item = HistoryItem(**example)
    assert _dump(item) == example


def test_history_page_response_matches_proposal_example() -> None:
    """proposal §6 历史分页响应示例,items 经 HistoryItem 校验。"""
    example: Dict[str, Any] = {
        "total": 128,
        "page": 1,
        "page_size": 10,
        "items": [
            {
                "id": 42,
                "filename": "cat_001.jpg",
                "predict_label": "猫",
                "confidence": 0.924,
                "probs": {"cat": 0.924, "dog": 0.076},
                "image_url": "/uploads/cat_001_20260910_103000.jpg",
                "created_at": "2026-09-10 10:30:00",
            }
        ],
    }
    response = HistoryPageResponse(**example)
    assert _dump(response) == example
    assert isinstance(response.items[0], HistoryItem)


def test_model_field_names_match_design_documents() -> None:
    """字段名与设计 §4.3/§4.4、proposal §6 完全一致(字段名即接口契约)。"""
    assert set(ClassifyResponse.model_fields) == {
        "id",
        "filename",
        "predict",
        "predict_label",
        "confidence",
        "probs",
        "image_url",
        "created_at",
    }
    assert set(BatchSubmitResponse.model_fields) == {"job_id", "total"}
    assert set(JobStatusResponse.model_fields) == {
        "job_id",
        "status",
        "total",
        "done",
        "percent",
        "current_filename",
        "summary",
        "results",
        "csv_url",
        "error",
    }
    assert set(HistoryItem.model_fields) == {
        "id",
        "filename",
        "predict_label",
        "confidence",
        "probs",
        "image_url",
        "created_at",
    }
    assert set(HistoryPageResponse.model_fields) == {"total", "page", "page_size", "items"}

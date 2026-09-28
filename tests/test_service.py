"""M7 service 模块单元测试(monkeypatch 隔离,不加载权重、不依赖 GPU、不碰真实库/目录)。"""
import csv
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

import config
import database
import file_storage
import predict as predict_module
import pytest
import service as service_module
import torch
from config import MSG_BATCH_TOO_MANY, MSG_HISTORY_EMPTY_EXPORT, MSG_INVALID_FORMAT_SIZE
from service import (
    JobRegistry,
    classify_single,
    export_history,
    get_job_status,
    run_batch_job,
    submit_batch,
    validate_batch,
)


@pytest.fixture()
def isolated_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(config, "RESULT_DIR", tmp_path / "result")
    return tmp_path


def _fake_predict_tensor(monkeypatch: pytest.MonkeyPatch, probs: List[float]) -> None:
    monkeypatch.setattr(
        predict_module, "predict_tensor", lambda tensor: torch.tensor([probs])
    )


def _fake_storage_and_db(
    monkeypatch: pytest.MonkeyPatch,
    stored_name: str = "cat_x.jpg",
    record_id: int = 42,
) -> Dict[str, Any]:
    calls: Dict[str, Any] = {"insert": None}
    monkeypatch.setattr(file_storage, "save_upload", lambda data, name: stored_name)
    monkeypatch.setattr(
        database,
        "insert_record",
        lambda **kwargs: calls.update(insert=kwargs) or record_id,
    )
    return calls


# ---------------------------------------------------------------- validate_batch


def test_validate_batch_rejects_too_many_files() -> None:
    files: List[Any] = [(b"x", "a.jpg")] * 501
    with pytest.raises(ValueError) as excinfo:
        validate_batch(files)
    assert str(excinfo.value) == MSG_BATCH_TOO_MANY


def test_validate_batch_accepts_upper_bound() -> None:
    files: List[Any] = [(b"x", "a.jpg")] * 500
    validate_batch(files)


# ---------------------------------------------------------------- classify_single


def test_classify_single_unsupported_suffix_raises_chinese_error() -> None:
    with pytest.raises(ValueError) as excinfo:
        classify_single(b"abc", "note.txt")
    assert str(excinfo.value) == MSG_INVALID_FORMAT_SIZE


def test_classify_single_oversized_file_raises_chinese_error() -> None:
    big = b"x" * (config.MAX_FILE_SIZE_BYTES + 1)
    with pytest.raises(ValueError) as excinfo:
        classify_single(big, "cat.jpg")
    assert str(excinfo.value) == MSG_INVALID_FORMAT_SIZE


def test_classify_single_full_chain_returns_contract_dict(
    isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_predict_tensor(monkeypatch, [0.924, 0.076])
    insert_calls = _fake_storage_and_db(monkeypatch)
    image_bytes = (Path(__file__).parent / "fixtures" / "cat_1.jpg").read_bytes()
    result = classify_single(image_bytes, "cat.jpg")
    assert result["id"] == 42
    assert result["filename"] == "cat.jpg"
    assert result["predict"] == "cat"
    assert result["predict_label"] == "猫"
    assert result["confidence"] == 0.924
    assert result["probs"] == {"cat": 0.924, "dog": 0.076}
    assert result["image_url"] == "/uploads/cat_x.jpg"
    assert result["created_at"]
    kwargs = insert_calls["insert"]
    assert kwargs["predict"] == "cat"
    assert kwargs["prob_cat"] == 0.924
    assert kwargs["prob_dog"] == 0.076
    assert kwargs["stored_path"] == "cat_x.jpg"


def test_classify_single_bad_image_raises_chinese_error(
    isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 后缀/大小合法但内容不是图片 → M3 解码校验抛中文 ValueError
    with pytest.raises(ValueError) as excinfo:
        classify_single(b"not-an-image", "cat.jpg")
    assert "无法读取该图片" in str(excinfo.value)


# ---------------------------------------------------------------- JobRegistry


def test_job_registry_lifecycle_and_get() -> None:
    registry = JobRegistry()
    job_id = registry.create_job(3)
    job = registry.get_job(job_id)
    assert job is not None
    assert job["status"] == "queued"
    registry.update_progress(job_id, 1, "a.jpg")
    job = registry.get_job(job_id)
    assert job is not None
    assert job["status"] == "running"
    assert job["done"] == 1
    registry.complete_job(job_id, {"total": 3}, [], "batch.csv")
    job = registry.get_job(job_id)
    assert job is not None
    assert job["status"] == "succeeded"
    assert job["csv_filename"] == "batch.csv"


def test_job_registry_fail_and_missing_job() -> None:
    registry = JobRegistry()
    job_id = registry.create_job(1)
    registry.fail_job(job_id, "识别失败,请重试")
    job = registry.get_job(job_id)
    assert job is not None
    assert job["status"] == "failed"
    assert job["error"] == "识别失败,请重试"
    assert registry.get_job("no-such-job") is None


def test_job_registry_prunes_oldest_jobs() -> None:
    registry = JobRegistry(retention=2)
    first = registry.create_job(1)
    registry.create_job(1)
    registry.create_job(1)  # 超过保留数,最旧的 first 被淘汰
    assert registry.get_job(first) is None


# ---------------------------------------------------------------- get_job_status


def test_get_job_status_running_shape() -> None:
    registry = JobRegistry()
    job_id = registry.create_job(10)
    registry.update_progress(job_id, 4, "cat_005.jpg")
    job = registry.get_job(job_id)
    assert job is not None
    status = service_module._build_status(job)
    assert status["status"] == "running"
    assert status["percent"] == 40.0
    assert status["current_filename"] == "cat_005.jpg"


def test_get_job_status_succeeded_and_failed_shapes() -> None:
    registry = JobRegistry()
    ok_job = registry.create_job(1)
    summary = {"total": 1, "success": 1, "failed": 0, "cat_count": 1, "dog_count": 0}
    registry.complete_job(ok_job, summary, [], "batch.csv")
    ok = registry.get_job(ok_job)
    assert ok is not None
    status = service_module._build_status(ok)
    assert status["status"] == "succeeded"
    assert status["csv_url"] == "/result/batch.csv"
    bad_job = registry.create_job(1)
    registry.fail_job(bad_job, "识别失败,请重试")
    bad = registry.get_job(bad_job)
    assert bad is not None
    failed_status = service_module._build_status(bad)
    assert failed_status["status"] == "failed"
    assert failed_status["error"] == "识别失败,请重试"


# ---------------------------------------------------------------- run_batch_job


def _fake_classify(monkeypatch: pytest.MonkeyPatch, behavior: Callable[[bytes, str], Dict[str, Any]]) -> None:
    monkeypatch.setattr(service_module, "classify_single", behavior)


def test_run_batch_job_mixed_success_and_failure(
    isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(data: bytes, name: str) -> Dict[str, Any]:
        if name == "坏文件.txt":
            raise ValueError("无法读取该图片,请上传 jpg/png/bmp 等图片文件")
        predict = "cat" if name.startswith("cat") else "dog"
        label = "猫" if predict == "cat" else "狗"
        return {
            "id": 1,
            "filename": name,
            "predict": predict,
            "predict_label": label,
            "confidence": 0.9,
            "probs": {"cat": 0.9, "dog": 0.1},
            "image_url": "/uploads/x.jpg",
            "created_at": "2026-09-10 10:00:00",
        }

    _fake_classify(monkeypatch, fake)
    registry = JobRegistry()
    monkeypatch.setattr(service_module, "_REGISTRY", registry)
    job_id = registry.create_job(3)
    files = [(b"1", "cat_a.jpg"), (b"2", "dog_b.jpg"), (b"3", "坏文件.txt")]
    run_batch_job(job_id, files)

    job = registry.get_job(job_id)
    assert job is not None
    assert job["status"] == "succeeded"
    summary = job["summary"]
    assert summary == {"total": 3, "success": 2, "failed": 1, "cat_count": 1, "dog_count": 1}
    results = job["results"]
    assert results[0] == {"filename": "cat_a.jpg", "predict_label": "猫", "confidence": 0.9, "remark": ""}
    assert results[2]["predict_label"] == "-"
    assert results[2]["confidence"] is None
    assert "无法读取该图片" in str(results[2]["remark"])
    # CSV 已真实写入 result 目录且 utf-8-sig
    csv_path = config.RESULT_DIR / str(job["csv_filename"])
    assert csv_path.exists()
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["文件名", "预测类别", "置信度", "备注"]
    assert len(rows) == 4


def test_run_batch_job_whole_failure_marks_failed(
    isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(data: bytes, name: str) -> Dict[str, Any]:
        raise RuntimeError("boom")

    _fake_classify(monkeypatch, fake)

    def boom(results: List[Dict[str, Any]]) -> str:
        raise RuntimeError("写盘失败")

    monkeypatch.setattr(file_storage, "write_batch_csv", boom)
    registry = JobRegistry()
    monkeypatch.setattr(service_module, "_REGISTRY", registry)
    job_id = registry.create_job(1)
    run_batch_job(job_id, [(b"1", "a.jpg")])
    job = registry.get_job(job_id)
    assert job is not None
    assert job["status"] == "failed"
    assert job["error"] == "写盘失败"


# ---------------------------------------------------------------- submit_batch


def test_submit_batch_runs_background_thread_to_success(
    isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(data: bytes, name: str) -> Dict[str, Any]:
        return {
            "id": 1,
            "filename": name,
            "predict": "cat",
            "predict_label": "猫",
            "confidence": 0.9,
            "probs": {"cat": 0.9, "dog": 0.1},
            "image_url": "/uploads/x.jpg",
            "created_at": "2026-09-10 10:00:00",
        }

    _fake_classify(monkeypatch, fake)
    job_id, total = submit_batch([(b"1", "a.jpg"), (b"2", "b.jpg")])
    assert total == 2
    deadline = time.time() + 10
    status = None
    while time.time() < deadline:
        status = get_job_status(job_id)
        if status is not None and status["status"] == "succeeded":
            break
        time.sleep(0.05)
    assert status is not None
    assert status["status"] == "succeeded"
    assert status["summary"]["success"] == 2


def test_submit_batch_rejects_over_limit() -> None:
    with pytest.raises(ValueError) as excinfo:
        submit_batch([(b"x", "a.jpg")] * 501)
    assert str(excinfo.value) == MSG_BATCH_TOO_MANY


# ---------------------------------------------------------------- export_history


def test_export_history_empty_raises_chinese_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(database, "query_all", lambda: [])
    with pytest.raises(ValueError) as excinfo:
        export_history()
    assert str(excinfo.value) == MSG_HISTORY_EMPTY_EXPORT


def test_export_history_writes_csv(
    isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        database,
        "query_all",
        lambda: [
            {
                "id": 1,
                "filename": "cat.jpg",
                "predict_label": "猫",
                "confidence": 0.9,
                "probs": {"cat": 0.9, "dog": 0.1},
                "image_url": "/uploads/cat.jpg",
                "created_at": "2026-09-10 10:00:00",
            }
        ],
    )
    filename = export_history()
    assert filename.startswith("history_")
    path = config.RESULT_DIR / filename
    assert path.exists()
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["编号", "文件名", "预测类别", "置信度", "识别时间"]
    assert rows[1][1] == "cat.jpg"

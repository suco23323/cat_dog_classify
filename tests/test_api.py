"""M8 api 模块单元测试(TestClient;monkeypatch 隔离,不加载真实权重、不碰真实库/目录)。"""
from pathlib import Path
from typing import Any, Callable, Dict, List

import config
import database
import file_storage
import main as main_module
import pytest
import service
from config import (
    MSG_BATCH_TOO_MANY,
    MSG_HISTORY_EMPTY_EXPORT,
    MSG_INVALID_FORMAT_SIZE,
    MSG_JOB_NOT_FOUND,
    MSG_RECOGNIZE_FAILED,
)
from fastapi.testclient import TestClient
from main import app

ResultDict = Dict[str, Any]


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Any:
    """TestClient 上下文触发 startup;模型加载与建库均被替换,避免真实副作用。"""
    monkeypatch.setattr(main_module, "get_model", lambda: None)
    monkeypatch.setattr(main_module.database, "init_db", lambda: None)
    with TestClient(app) as test_client:
        yield test_client


def _fake_classify(monkeypatch: pytest.MonkeyPatch, behavior: Callable[[bytes, str], ResultDict]) -> None:
    monkeypatch.setattr(service, "classify_single", behavior)


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_static_mounts_registered() -> None:
    paths = [getattr(route, "path", None) for route in app.routes]
    assert "/uploads" in paths
    assert "/result" in paths


# ---------------------------------------------------------------- classify


def test_classify_success_returns_contract(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(data: bytes, name: str) -> ResultDict:
        return {
            "id": 42,
            "filename": name,
            "predict": "cat",
            "predict_label": "猫",
            "confidence": 0.924,
            "probs": {"cat": 0.924, "dog": 0.076},
            "image_url": "/uploads/cat_x.jpg",
            "created_at": "2026-09-10 10:00:00",
        }

    _fake_classify(monkeypatch, fake)
    response = client.post(
        "/api/classify", files={"file": ("cat.jpg", b"image-bytes", "image/jpeg")}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 42
    assert body["predict_label"] == "猫"
    assert body["probs"] == {"cat": 0.924, "dog": 0.076}


def test_classify_value_error_maps_to_400(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(data: bytes, name: str) -> ResultDict:
        raise ValueError(MSG_INVALID_FORMAT_SIZE)

    _fake_classify(monkeypatch, fake)
    response = client.post("/api/classify", files={"file": ("bad.txt", b"xx", "text/plain")})
    assert response.status_code == 400
    assert response.json()["detail"] == MSG_INVALID_FORMAT_SIZE


def test_classify_unexpected_error_maps_to_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(data: bytes, name: str) -> ResultDict:
        raise RuntimeError("boom")

    _fake_classify(monkeypatch, fake)
    response = client.post("/api/classify", files={"file": ("a.jpg", b"xx", "image/jpeg")})
    assert response.status_code == 500
    assert response.json()["detail"] == MSG_RECOGNIZE_FAILED


# ---------------------------------------------------------------- batch


def test_batch_submit_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service, "submit_batch", lambda files: ("jobid123", 2))
    response = client.post(
        "/api/batch",
        files=[
            ("files", ("a.jpg", b"x", "image/jpeg")),
            ("files", ("b.jpg", b"y", "image/jpeg")),
        ],
    )
    assert response.status_code == 200
    assert response.json() == {"job_id": "jobid123", "total": 2}


def test_batch_over_limit_maps_to_400(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(files: List[Any]) -> Any:
        raise ValueError(MSG_BATCH_TOO_MANY)

    monkeypatch.setattr(service, "submit_batch", fake)
    response = client.post("/api/batch", files=[("files", ("a.jpg", b"x", "image/jpeg"))])
    assert response.status_code == 400
    assert response.json()["detail"] == MSG_BATCH_TOO_MANY


def test_batch_status_success_shape(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        service,
        "get_job_status",
        lambda job_id: {
            "job_id": job_id,
            "status": "running",
            "total": 10,
            "done": 4,
            "percent": 40.0,
            "current_filename": "cat_005.jpg",
        },
    )
    response = client.get("/api/batch/status/jobid123")
    assert response.status_code == 200
    body = response.json()
    assert body["percent"] == 40.0
    assert body["current_filename"] == "cat_005.jpg"
    # response_model 的 Optional 字段以 null 呈现
    assert body["summary"] is None


def test_batch_status_not_found_maps_to_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service, "get_job_status", lambda job_id: None)
    response = client.get("/api/batch/status/no-such-job")
    assert response.status_code == 404
    assert response.json()["detail"] == MSG_JOB_NOT_FOUND


# ---------------------------------------------------------------- history


def test_history_page_shape(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    item = {
        "id": 1,
        "filename": "cat.jpg",
        "predict_label": "猫",
        "confidence": 0.9,
        "probs": {"cat": 0.9, "dog": 0.1},
        "image_url": "/uploads/cat.jpg",
        "created_at": "2026-09-10 10:00:00",
    }
    monkeypatch.setattr(database, "query_page", lambda page, page_size: (5, [item]))
    response = client.get("/api/history", params={"page": 1, "page_size": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["items"][0]["predict_label"] == "猫"


def test_delete_history_record_with_linked_file_removal(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(database, "delete_record", lambda record_id: "cat_x.jpg")
    deleted: List[str] = []
    monkeypatch.setattr(file_storage, "delete_file", lambda path: deleted.append(path))
    response = client.delete("/api/history/7")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert deleted == ["cat_x.jpg"]


def test_delete_history_record_not_found_maps_to_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(database, "delete_record", lambda record_id: None)
    response = client.delete("/api/history/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "记录不存在或已删除"


def test_clear_history_with_linked_file_removal(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(database, "clear_all", lambda: ["a.jpg", "b.jpg"])
    deleted: List[str] = []
    monkeypatch.setattr(file_storage, "delete_file", lambda path: deleted.append(path))
    response = client.delete("/api/history")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "deleted": 2}
    assert deleted == ["a.jpg", "b.jpg"]


# ---------------------------------------------------------------- export


def test_export_history_downloads_csv(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(config, "RESULT_DIR", tmp_path)
    csv_path = tmp_path / "history_test.csv"
    csv_path.write_bytes("编号,文件名\n1,cat.jpg\n".encode("utf-8-sig"))
    monkeypatch.setattr(service, "export_history", lambda: "history_test.csv")
    response = client.get("/api/history/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "编号" in response.text


def test_export_history_empty_maps_to_400(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake() -> str:
        raise ValueError(MSG_HISTORY_EMPTY_EXPORT)

    monkeypatch.setattr(service, "export_history", fake)
    response = client.get("/api/history/export")
    assert response.status_code == 400
    assert response.json()["detail"] == MSG_HISTORY_EMPTY_EXPORT

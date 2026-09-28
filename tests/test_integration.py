"""集成测试:真实权重 + 全接口端到端(标记 integration)。

依赖工程根目录 best_model_opt20.pth;设备自适应(GPU 可用用 GPU,否则 CPU)。
每个测试前后清空历史,避免污染真实 app.db/uploads/result。
"""
import csv
import time
from io import StringIO
from pathlib import Path
from typing import Any, Dict

import config
import pytest
from fastapi.testclient import TestClient
from main import app

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def client() -> Any:
    """TestClient 上下文触发 startup:init_db + 真实权重加载(仅一次)。"""
    with TestClient(app) as test_client:
        yield test_client


def _clear_history(client: TestClient) -> None:
    client.delete("/api/history")


@pytest.fixture(autouse=True)
def clean_history(client: TestClient) -> Any:
    _clear_history(client)
    yield
    _clear_history(client)


def _upload(client: TestClient, path: Path) -> Any:
    with open(path, "rb") as f:
        return client.post(
            "/api/classify", files={"file": (path.name, f.read(), "image/jpeg")}
        )


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_classify_real_cat_image_and_static_serving(client: TestClient) -> None:
    response = _upload(client, FIXTURES / "cat_1.jpg")
    assert response.status_code == 200
    body = response.json()
    assert body["predict"] == "cat"
    assert body["predict_label"] == "猫"
    assert 0.0 < body["confidence"] <= 1.0
    assert abs(body["probs"]["cat"] + body["probs"]["dog"] - 1.0) < 1e-3
    assert body["id"] > 0
    assert body["image_url"].startswith("/uploads/")
    # 静态图片可访问
    image = client.get(body["image_url"])
    assert image.status_code == 200
    assert len(image.content) > 100


def test_classify_real_dog_image(client: TestClient) -> None:
    response = _upload(client, FIXTURES / "dog_1.jpg")
    assert response.status_code == 200
    body = response.json()
    assert body["predict"] == "dog"
    assert body["predict_label"] == "狗"


def test_classify_invalid_file_returns_400(client: TestClient) -> None:
    response = client.post("/api/classify", files={"file": ("note.txt", b"hello", "text/plain")})
    assert response.status_code == 400
    assert response.json()["detail"] == config.MSG_INVALID_FORMAT_SIZE


def test_history_crud_flow(client: TestClient) -> None:
    assert _upload(client, FIXTURES / "cat_1.jpg").status_code == 200
    assert _upload(client, FIXTURES / "dog_1.jpg").status_code == 200

    page = client.get("/api/history", params={"page": 1, "page_size": 10})
    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 2
    assert body["items"][0]["created_at"] >= body["items"][1]["created_at"]  # 倒序

    first_id = body["items"][0]["id"]
    deleted = client.delete(f"/api/history/{first_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True}
    page = client.get("/api/history", params={"page": 1, "page_size": 10})
    assert page.json()["total"] == 1

    deleted_again = client.delete(f"/api/history/{first_id}")
    assert deleted_again.status_code == 404

    cleared = client.delete("/api/history")
    assert cleared.status_code == 200
    assert cleared.json() == {"ok": True, "deleted": 1}
    page = client.get("/api/history", params={"page": 1, "page_size": 10})
    assert page.json()["total"] == 0


def test_export_history_flow(client: TestClient) -> None:
    assert _upload(client, FIXTURES / "cat_2.jpg").status_code == 200
    exported = client.get("/api/history/export")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(StringIO(exported.content.decode("utf-8-sig"))))
    assert rows[0] == ["编号", "文件名", "预测类别", "置信度", "识别时间"]
    assert len(rows) == 2

    _clear_history(client)
    empty_export = client.get("/api/history/export")
    assert empty_export.status_code == 400
    assert empty_export.json()["detail"] == config.MSG_HISTORY_EMPTY_EXPORT


def test_batch_async_end_to_end(client: TestClient) -> None:
    files = [
        ("files", ((FIXTURES / "cat_1.jpg").name, (FIXTURES / "cat_1.jpg").read_bytes(), "image/jpeg")),
        ("files", ((FIXTURES / "dog_1.jpg").name, (FIXTURES / "dog_1.jpg").read_bytes(), "image/jpeg")),
        ("files", ("坏文件.txt", b"not-an-image", "text/plain")),
    ]
    submitted = client.post("/api/batch", files=files)
    assert submitted.status_code == 200
    job_id = submitted.json()["job_id"]
    assert submitted.json()["total"] == 3

    deadline = time.time() + 90
    status: Dict[str, Any] = {}
    while time.time() < deadline:
        response = client.get(f"/api/batch/status/{job_id}")
        assert response.status_code == 200
        status = response.json()
        if status["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.3)
    assert status["status"] == "succeeded"
    summary = status["summary"]
    assert summary == {"total": 3, "success": 2, "failed": 1, "cat_count": 1, "dog_count": 1}
    results = status["results"]
    assert results[2]["predict_label"] == "-"
    assert results[2]["remark"]  # 坏文件备注非空
    assert status["csv_url"].startswith("/result/")
    csv_response = client.get(status["csv_url"])
    assert csv_response.status_code == 200
    rows = list(csv.reader(StringIO(csv_response.content.decode("utf-8-sig"))))
    assert rows[0] == ["文件名", "预测类别", "置信度", "备注"]
    assert len(rows) == 4
    # 成功的两张写入历史,坏文件未写入
    page = client.get("/api/history", params={"page": 1, "page_size": 10})
    assert page.json()["total"] == 2


def test_batch_status_missing_job_returns_404(client: TestClient) -> None:
    response = client.get("/api/batch/status/definitely-not-exists")
    assert response.status_code == 404
    assert response.json()["detail"] == config.MSG_JOB_NOT_FOUND

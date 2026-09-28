"""M6 file_storage 模块单元测试(临时目录隔离,不依赖 GPU/权重)。"""
import csv
from pathlib import Path
from typing import Any, Dict, List

import config
import file_storage
import pytest
from config import MSG_CSV_WRITE_FAILED


@pytest.fixture()
def isolated_dirs(tmp_path: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    """把 UPLOAD_DIR/RESULT_DIR 指向临时目录,隔离真实 uploads/result。"""
    root = Path(tmp_path)
    uploads = root / "uploads"
    result = root / "result"
    monkeypatch.setattr(config, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(config, "RESULT_DIR", result)
    return root


def test_save_upload_writes_bytes_and_returns_unique_names(isolated_dirs: Path) -> None:
    first = file_storage.save_upload(b"abc", "cat.jpg")
    second = file_storage.save_upload(b"abc", "cat.jpg")  # 同一秒内同名不覆盖
    assert first != second
    assert first.startswith("cat_")
    assert first.endswith(".jpg")
    assert (config.UPLOAD_DIR / first).read_bytes() == b"abc"
    assert (config.UPLOAD_DIR / second).read_bytes() == b"abc"


def test_save_upload_keeps_suffix_case_insensitive(isolated_dirs: Path) -> None:
    stored = file_storage.save_upload(b"x", "photo.PNG")
    assert stored.endswith(".PNG")
    assert (config.UPLOAD_DIR / stored).read_bytes() == b"x"


def test_delete_file_removes_existing_file(isolated_dirs: Path) -> None:
    stored = file_storage.save_upload(b"data", "dog.jpg")
    path = config.UPLOAD_DIR / stored
    assert path.exists()
    file_storage.delete_file(stored)
    assert not path.exists()


def test_delete_file_ignores_nonexistent(isolated_dirs: Path) -> None:
    # 不存在时静默忽略(设计 §5.4)
    file_storage.delete_file("no_such_file.jpg")


def test_write_batch_csv_columns_and_utf8_sig(isolated_dirs: Path) -> None:
    results: List[Dict[str, Any]] = [
        {"filename": "a.jpg", "predict_label": "猫", "confidence": 0.924, "remark": ""},
        {"filename": "坏文件.txt", "predict_label": "-", "confidence": None, "remark": "无法读取该图片"},
    ]
    filename = file_storage.write_batch_csv(results, "20260910_103000")
    assert filename == "batch_result_20260910_103000.csv"
    raw = (config.RESULT_DIR / filename).read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # utf-8-sig BOM
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    assert lines[0] == "文件名,预测类别,置信度,备注"
    assert "a.jpg,猫,0.924," in lines[1]
    assert "坏文件.txt,-,-,无法读取该图片" in lines[2]
    # csv 模块可正确解析(标准库读回校验)
    with open(config.RESULT_DIR / filename, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["文件名", "预测类别", "置信度", "备注"]
    assert rows[2][:4] == ["坏文件.txt", "-", "-", "无法读取该图片"]


def test_write_history_csv_columns_and_rows(isolated_dirs: Path) -> None:
    records: List[Dict[str, Any]] = [
        {
            "id": 1,
            "filename": "cat.jpg",
            "predict_label": "猫",
            "confidence": 0.9,
            "created_at": "2026-09-10 10:00:00",
        }
    ]
    filename = file_storage.write_history_csv(records, "20260910_103000")
    assert filename == "history_20260910_103000.csv"
    with open(config.RESULT_DIR / filename, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["编号", "文件名", "预测类别", "置信度", "识别时间"]
    assert rows[1] == ["1", "cat.jpg", "猫", "0.9", "2026-09-10 10:00:00"]


def test_write_batch_csv_uses_timestamp_when_not_given(isolated_dirs: Path) -> None:
    filename = file_storage.write_batch_csv([])
    assert filename.startswith("batch_result_")
    assert filename.endswith(".csv")


def test_write_csv_failure_raises_chinese_runtime_error(
    isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 把 RESULT_DIR 指向一个普通文件路径,目录创建必然失败 → OSError → 中文 RuntimeError
    not_a_dir = isolated_dirs / "occupied"
    not_a_dir.write_bytes(b"x")
    monkeypatch.setattr(config, "RESULT_DIR", not_a_dir)
    with pytest.raises(RuntimeError) as excinfo:
        file_storage.write_batch_csv([{"filename": "a.jpg"}])
    assert str(excinfo.value) == MSG_CSV_WRITE_FAILED

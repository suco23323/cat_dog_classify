"""M5 database 模块单元测试(纯 sqlite3,临时库隔离,不依赖 GPU/权重)。"""
from pathlib import Path
from typing import Any, Dict, List

from database import (
    clear_all,
    delete_record,
    get_connection,
    init_db,
    insert_record,
    query_all,
    query_page,
)


def _insert(
    db_path: Path,
    index: int,
    filename: str = "cat.jpg",
    stored: str = "cat_0000.jpg",
    predict: str = "cat",
    prob_cat: float = 0.9,
    prob_dog: float = 0.1,
    confidence: float = 0.9,
    created_at: str = "2026-09-10 10:00:00",
) -> int:
    return insert_record(
        filename=filename,
        stored_path=stored,
        predict=predict,
        prob_cat=prob_cat,
        prob_dog=prob_dog,
        confidence=confidence,
        created_at=created_at,
        db_path=str(db_path),
    )


def _db(tmp_path: Path, name: str = "t.db") -> Path:
    return tmp_path / name


def test_get_connection_executes_sql(tmp_path: Path) -> None:
    conn = get_connection(str(_db(tmp_path)))
    try:
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0
    finally:
        conn.close()


def test_init_db_creates_table_and_index_idempotent(tmp_path: Path) -> None:
    db_path = _db(tmp_path)
    init_db(str(db_path))
    init_db(str(db_path))  # 幂等:重复调用不报错
    conn = get_connection(str(db_path))
    try:
        cols = [row["name"] for row in conn.execute("PRAGMA table_info(classify_history)")]
        assert cols == [
            "id",
            "filename",
            "stored_path",
            "predict",
            "prob_cat",
            "prob_dog",
            "confidence",
            "created_at",
        ]
        indexes = [
            row["name"]
            for row in conn.execute("PRAGMA index_list(classify_history)").fetchall()
        ]
        assert "idx_history_created_at" in indexes
    finally:
        conn.close()


def test_insert_record_returns_increasing_ids(tmp_path: Path) -> None:
    db_path = _db(tmp_path)
    init_db(str(db_path))
    first = _insert(db_path, 1)
    second = _insert(db_path, 2)
    assert second == first + 1


def test_query_page_pagination_and_desc_order(tmp_path: Path) -> None:
    db_path = _db(tmp_path)
    init_db(str(db_path))
    for i in range(25):
        _insert(db_path, i, created_at=f"2026-09-10 10:{i:02d}:00")
    total, page3 = query_page(3, 10, str(db_path))
    assert total == 25
    assert len(page3) == 5
    # 倒序:第一页第一条应是最后插入(时间最大)的记录
    total2, page1 = query_page(1, 10, str(db_path))
    assert total2 == 25
    assert page1[0]["created_at"] == "2026-09-10 10:24:00"
    assert page1[-1]["created_at"] == "2026-09-10 10:15:00"


def test_query_page_item_fields_match_history_item_contract(tmp_path: Path) -> None:
    db_path = _db(tmp_path)
    init_db(str(db_path))
    record_id = _insert(db_path, 1, filename="cat.jpg", stored="cat_1.jpg", predict="cat")
    _, page = query_page(1, 10, str(db_path))
    item: Dict[str, Any] = page[0]
    assert item["id"] == record_id
    assert item["filename"] == "cat.jpg"
    assert item["predict_label"] == "猫"
    assert item["confidence"] == 0.9
    assert item["probs"] == {"cat": 0.9, "dog": 0.1}
    assert item["image_url"] == "/uploads/cat_1.jpg"


def test_query_page_label_mapping_for_dog(tmp_path: Path) -> None:
    db_path = _db(tmp_path)
    init_db(str(db_path))
    _insert(db_path, 1, predict="dog", prob_cat=0.2, prob_dog=0.8, confidence=0.8)
    _, page = query_page(1, 10, str(db_path))
    assert page[0]["predict_label"] == "狗"


def test_delete_record_returns_stored_path_and_removes_row(tmp_path: Path) -> None:
    db_path = _db(tmp_path)
    init_db(str(db_path))
    record_id = _insert(db_path, 1, stored="cat_9.jpg")
    assert delete_record(record_id, str(db_path)) == "cat_9.jpg"
    assert delete_record(record_id, str(db_path)) is None  # 已删除,重复删除返回 None
    total, _ = query_page(1, 10, str(db_path))
    assert total == 0


def test_delete_record_nonexistent_returns_none(tmp_path: Path) -> None:
    db_path = _db(tmp_path)
    init_db(str(db_path))
    assert delete_record(999, str(db_path)) is None


def test_clear_all_returns_all_paths_and_empties_table(tmp_path: Path) -> None:
    db_path = _db(tmp_path)
    init_db(str(db_path))
    _insert(db_path, 1, stored="a.jpg")
    _insert(db_path, 2, stored="b.jpg")
    paths = clear_all(str(db_path))
    assert sorted(paths) == ["a.jpg", "b.jpg"]
    total, _ = query_page(1, 10, str(db_path))
    assert total == 0


def test_clear_all_on_empty_table_returns_empty_list(tmp_path: Path) -> None:
    db_path = _db(tmp_path)
    init_db(str(db_path))
    assert clear_all(str(db_path)) == []


def test_query_all_returns_all_rows_desc(tmp_path: Path) -> None:
    db_path = _db(tmp_path)
    init_db(str(db_path))
    for i in range(3):
        _insert(db_path, i, filename=f"f{i}.jpg", created_at=f"2026-09-10 10:0{i}:00")
    items: List[Dict[str, Any]] = query_all(str(db_path))
    assert len(items) == 3
    assert [item["created_at"] for item in items] == [
        "2026-09-10 10:02:00",
        "2026-09-10 10:01:00",
        "2026-09-10 10:00:00",
    ]
    assert items[0]["filename"] == "f2.jpg"


def test_query_page_defensive_pagination(tmp_path: Path) -> None:
    """极小/极端分页参数不应崩溃(page/page_size 由 M8 层保证为正)。"""
    db_path = _db(tmp_path)
    init_db(str(db_path))
    _insert(db_path, 1)
    total, items = query_page(1, 1, str(db_path))
    assert total == 1
    assert len(items) == 1

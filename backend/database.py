"""M5 数据库访问模块:使用标准库 sqlite3 封装历史记录表的建表与增删查。

表结构与 `doc/high-level-design.md` §5.1 一致;本模块是唯一访问 SQLite 的模块。
删除/清空记录时返回对应 `stored_path`,供 M6 联动删除 `uploads/` 图片文件(设计 §5.4)。
连接策略(设计 §10 待办敲定):每次调用新建连接,简单可靠,单用户本地场景足够。
"""
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from config import CLASS_INDEX, DB_PATH

# 英文类别 -> 中文标签(与 config.CLASS_INDEX 派生,索引 0=cat→猫,1=dog→狗)
LABEL_BY_PREDICT: Dict[str, str] = {en: zh for en, zh in CLASS_INDEX.values()}


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """新建 SQLite 连接(默认使用 `config.DB_PATH`),行以 `sqlite3.Row` 返回。

    db_path 参数供测试注入临时库文件;生产代码不传参,使用默认真实库。
    """
    conn = sqlite3.connect(db_path if db_path is not None else str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """建表 `classify_history` 并在 `created_at` 上建索引(幂等)。"""
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS classify_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                predict     TEXT NOT NULL,
                prob_cat    REAL NOT NULL,
                prob_dog    REAL NOT NULL,
                confidence  REAL NOT NULL,
                created_at  TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_created_at ON classify_history (created_at)"
        )
        conn.commit()
    finally:
        conn.close()


def insert_record(
    filename: str,
    stored_path: str,
    predict: str,
    prob_cat: float,
    prob_dog: float,
    confidence: float,
    created_at: str,
    db_path: Optional[str] = None,
) -> int:
    """插入一条识别记录,返回自增 id。"""
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO classify_history
                (filename, stored_path, predict, prob_cat, prob_dog, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (filename, stored_path, predict, prob_cat, prob_dog, confidence, created_at),
        )
        conn.commit()
        assert cur.lastrowid is not None
        return int(cur.lastrowid)
    finally:
        conn.close()


def _row_to_item(row: sqlite3.Row) -> Dict[str, Any]:
    """数据库行 -> 历史条目 dict(字段与 M9 `HistoryItem` 一致)。"""
    stored_path = str(row["stored_path"])
    return {
        "id": int(row["id"]),
        "filename": str(row["filename"]),
        "predict_label": LABEL_BY_PREDICT.get(str(row["predict"]), str(row["predict"])),
        "confidence": float(row["confidence"]),
        "probs": {"cat": float(row["prob_cat"]), "dog": float(row["prob_dog"])},
        "image_url": "/uploads/" + stored_path,
        "created_at": str(row["created_at"]),
    }


def query_page(page: int, page_size: int, db_path: Optional[str] = None) -> Tuple[int, List[Dict[str, Any]]]:
    """按 `created_at DESC, id DESC` 倒序分页查询,返回 (总数, 当前页条目列表)。"""
    conn = get_connection(db_path)
    try:
        total = int(conn.execute("SELECT COUNT(*) FROM classify_history").fetchone()[0])
        offset = (page - 1) * page_size
        rows = conn.execute(
            "SELECT * FROM classify_history ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()
        return total, [_row_to_item(row) for row in rows]
    finally:
        conn.close()


def delete_record(record_id: int, db_path: Optional[str] = None) -> Optional[str]:
    """删除指定记录并返回其 `stored_path`;记录不存在返回 `None`(供 M8 判 404)。"""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT stored_path FROM classify_history WHERE id = ?", (record_id,)
        ).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM classify_history WHERE id = ?", (record_id,))
        conn.commit()
        return str(row["stored_path"])
    finally:
        conn.close()


def clear_all(db_path: Optional[str] = None) -> List[str]:
    """清空全部记录,返回所有 `stored_path`(供 M6 批量删除图片文件)。"""
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT stored_path FROM classify_history").fetchall()
        paths = [str(row["stored_path"]) for row in rows]
        conn.execute("DELETE FROM classify_history")
        conn.commit()
        return paths
    finally:
        conn.close()


def query_all(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """按时间倒序返回全部条目(供历史导出 CSV)。"""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM classify_history ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [_row_to_item(row) for row in rows]
    finally:
        conn.close()

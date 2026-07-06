"""Работа с SQLite базой (data/trends.db)."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trends.db"


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """Создаёт таблицы, если их ещё нет."""
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            url TEXT,
            score_raw REAL,
            published_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_trends(trends: list[dict]) -> int:
    """Сохраняет список трендов в таблицу trends. Возвращает число вставленных строк."""
    if not trends:
        return 0
    conn = get_connection()
    conn.executemany(
        """
        INSERT INTO trends (title, source, url, score_raw, published_at)
        VALUES (:title, :source, :url, :score_raw, :published_at)
        """,
        trends,
    )
    conn.commit()
    conn.close()
    return len(trends)


def get_recent_trends(limit: int = 50) -> list[dict]:
    """Возвращает последние сохранённые тренды, новые сначала."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, title, source, url, score_raw, published_at, created_at "
        "FROM trends ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

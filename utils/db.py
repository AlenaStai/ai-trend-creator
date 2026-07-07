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
    columns = [row[1] for row in conn.execute("PRAGMA table_info(trends)").fetchall()]
    if "title_ru" not in columns:
        conn.execute("ALTER TABLE trends ADD COLUMN title_ru TEXT")
    if "trend_date" not in columns:
        conn.execute("ALTER TABLE trends ADD COLUMN trend_date TEXT")
    if "trend_gist" not in columns:
        conn.execute("ALTER TABLE trends ADD COLUMN trend_gist TEXT")
    conn.commit()
    conn.close()


def save_trends(trends: list[dict]) -> int:
    """Сохраняет тренды. Если тренд (по title+source) уже есть — обновляет его данные
    и время, вместо того чтобы вставлять дубликат. Возвращает число новых трендов."""
    if not trends:
        return 0
    conn = get_connection()
    inserted = 0
    for t in trends:
        existing = conn.execute(
            "SELECT id FROM trends WHERE title = ? AND source = ?",
            (t.get("title"), t.get("source")),
        ).fetchone()
        defaults = {"title_ru": None, "trend_date": None, "trend_gist": None}
        if existing:
            conn.execute(
                """
                UPDATE trends SET url = :url, score_raw = :score_raw,
                    published_at = :published_at,
                    title_ru = COALESCE(:title_ru, title_ru),
                    trend_date = COALESCE(:trend_date, trend_date),
                    trend_gist = COALESCE(:trend_gist, trend_gist),
                    created_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """,
                {**defaults, **t, "id": existing[0]},
            )
        else:
            conn.execute(
                """
                INSERT INTO trends
                    (title, source, url, score_raw, published_at, title_ru, trend_date, trend_gist)
                VALUES
                    (:title, :source, :url, :score_raw, :published_at, :title_ru, :trend_date, :trend_gist)
                """,
                {**defaults, **t},
            )
            inserted += 1
    conn.commit()
    conn.close()
    return inserted


def get_recent_trends(limit: int = 100) -> list[dict]:
    """Возвращает последние обновлённые тренды, новые сначала."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, title, title_ru, source, url, score_raw, published_at, "
        "trend_date, trend_gist, created_at "
        "FROM trends ORDER BY created_at DESC, id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

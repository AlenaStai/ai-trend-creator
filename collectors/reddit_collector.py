"""Фолбэк-источник трендов — Reddit API (praw)."""

from __future__ import annotations


def fetch_trends(subreddits: list[str] | None = None, limit: int = 20) -> list[dict]:
    """Возвращает список трендов из Reddit.

    Каждый элемент: {title, source, url, score_raw, published_at}
    """
    raise NotImplementedError

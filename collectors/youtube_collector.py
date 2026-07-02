"""Фолбэк-источник трендов — YouTube Data API."""

from __future__ import annotations


def fetch_trends(query: str | None = None, limit: int = 20) -> list[dict]:
    """Возвращает список трендов из YouTube.

    Каждый элемент: {title, source, url, score_raw, published_at}
    """
    raise NotImplementedError

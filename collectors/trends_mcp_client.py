"""Основной источник трендов — Trends MCP (Google Trends, YouTube, TikTok, Reddit)."""

from __future__ import annotations


def fetch_trends(query: str | None = None, limit: int = 20) -> list[dict]:
    """Возвращает список трендов через Trends MCP.

    Каждый элемент: {title, source, url, score_raw, published_at}
    """
    raise NotImplementedError

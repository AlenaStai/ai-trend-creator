"""Фолбэк-источник трендов — RSS блогов (OpenAI, Anthropic, Google AI)."""

from __future__ import annotations

FEEDS = [
    "https://openai.com/blog/rss.xml",
    "https://www.anthropic.com/rss.xml",
    "https://blog.google/technology/ai/rss/",
]


def fetch_trends(feeds: list[str] | None = None, limit: int = 20) -> list[dict]:
    """Возвращает список трендов из RSS-лент.

    Каждый элемент: {title, source, url, score_raw, published_at}
    """
    raise NotImplementedError

"""Фолбэк-источник трендов — YouTube Data API (используется, если Trends MCP недоступен)."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
REGION_CODE = "US"


class YouTubeCollectorError(Exception):
    """Ошибка сбора трендов через YouTube Data API."""


def fetch_trends(query: str | None = None, limit: int = 20) -> list[dict]:
    """Возвращает список трендовых видео YouTube (чарт mostPopular).

    Если передан query — фильтрует результаты по вхождению в заголовок.

    Каждый элемент: {title, source, url, score_raw, published_at}
    """
    if not API_KEY:
        raise YouTubeCollectorError("YOUTUBE_API_KEY не задан в .env")

    try:
        youtube = build("youtube", "v3", developerKey=API_KEY)
        response = (
            youtube.videos()
            .list(
                part="snippet,statistics",
                chart="mostPopular",
                regionCode=REGION_CODE,
                maxResults=min(limit, 50),
            )
            .execute()
        )
    except HttpError as e:
        raise YouTubeCollectorError(f"YouTube Data API: {e}") from e

    trends = []
    for item in response.get("items", []):
        snippet = item["snippet"]
        stats = item.get("statistics", {})
        trends.append(
            {
                "title": snippet["title"],
                "source": "YouTube Trending",
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "score_raw": float(stats.get("viewCount", 0)),
                "published_at": snippet.get("publishedAt"),
            }
        )

    if query:
        query_lower = query.lower()
        trends = [t for t in trends if query_lower in t["title"].lower()]

    return trends


if __name__ == "__main__":
    # Быстрая ручная проверка: python -m collectors.youtube_collector
    results = fetch_trends(limit=10)
    print(f"Получено трендов: {len(results)}")
    for t in results:
        print(f"  [{t['source']}] {t['title']} (views={t['score_raw']}) {t['url']}")

"""Фолбэк-источник трендов — Reddit API (используется, если Trends MCP недоступен)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import praw
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = "ai-trend-creator/0.1 (personal script)"

DEFAULT_SUBREDDITS = ["all"]


class RedditCollectorError(Exception):
    """Ошибка сбора трендов через Reddit API."""


def fetch_trends(subreddits: list[str] | None = None, limit: int = 20) -> list[dict]:
    """Возвращает список трендов из Reddit (горячие посты по сабреддитам).

    Каждый элемент: {title, source, url, score_raw, published_at}
    """
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RedditCollectorError("REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET не заданы в .env")

    subreddits = subreddits or DEFAULT_SUBREDDITS

    try:
        reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            user_agent=USER_AGENT,
        )

        trends = []
        for name in subreddits:
            for post in reddit.subreddit(name).hot(limit=limit):
                if post.stickied:
                    continue
                trends.append(
                    {
                        "title": post.title,
                        "source": f"Reddit r/{name}",
                        "url": f"https://reddit.com{post.permalink}",
                        "score_raw": float(post.score),
                        "published_at": datetime.fromtimestamp(
                            post.created_utc, tz=timezone.utc
                        ).isoformat(),
                    }
                )
    except Exception as e:
        raise RedditCollectorError(f"Reddit API: {e}") from e

    return trends


if __name__ == "__main__":
    # Быстрая ручная проверка: python -m collectors.reddit_collector
    results = fetch_trends(limit=10)
    print(f"Получено трендов: {len(results)}")
    for t in results:
        print(f"  [{t['source']}] {t['title']} (score={t['score_raw']}) {t['url']}")

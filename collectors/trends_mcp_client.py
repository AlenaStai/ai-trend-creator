"""Основной источник трендов — Trends MCP (Google Trends, YouTube, TikTok, Reddit).

REST API (не MCP-протокол): POST https://api.trendsmcp.ai/api, Bearer-токен.
Бесплатный тариф — 100 запросов/мес, при превышении отдаёт 429.
"""

from __future__ import annotations

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.trendsmcp.ai/api"
API_KEY = os.getenv("TRENDS_MCP_API_KEY")
TIMEOUT = 10

# Живые фиды, которые объединяем в единую ленту трендов
FEED_TYPES = [
    "Google Trends",
    "YouTube Trending",
    "TikTok Trending Hashtags",
    "Reddit Hot Posts",
]


class TrendsMCPError(Exception):
    """Ошибка запроса к Trends MCP (сеть, авторизация, лимит, формат ответа)."""


def _request(payload: dict) -> dict:
    if not API_KEY:
        raise TrendsMCPError("TRENDS_MCP_API_KEY не задан в .env")

    try:
        response = requests.post(
            API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        raise TrendsMCPError(f"сетевая ошибка: {e}") from e

    if response.status_code == 401:
        raise TrendsMCPError("неверный или отсутствующий API-ключ (401)")
    if response.status_code == 429:
        raise TrendsMCPError("превышен месячный лимит запросов (429)")
    if not response.ok:
        raise TrendsMCPError(f"ошибка {response.status_code}: {response.text[:200]}")

    try:
        envelope = response.json()
    except ValueError as e:
        raise TrendsMCPError(f"не удалось разобрать ответ как JSON: {e}") from e

    # API всегда отвечает HTTP 200 и оборачивает реальный результат в конверт:
    # {"statusCode": <настоящий код>, "body": "<json-строка>"}. Настоящие
    # 400/401/429 нужно искать внутри, а не в HTTP-статусе.
    if isinstance(envelope, dict) and "body" in envelope and isinstance(envelope["body"], str):
        try:
            body = json.loads(envelope["body"])
        except ValueError as e:
            raise TrendsMCPError(f"не удалось разобрать 'body' как JSON: {e}") from e

        inner_status = envelope.get("statusCode", 200)
        if inner_status == 429:
            raise TrendsMCPError("превышен месячный лимит запросов (429)")
        if inner_status == 401:
            raise TrendsMCPError("неверный или отсутствующий API-ключ (401)")
        if inner_status and inner_status >= 400:
            error_code = body.get("error", "unknown_error") if isinstance(body, dict) else "unknown_error"
            message = body.get("message", str(body)) if isinstance(body, dict) else str(body)
            raise TrendsMCPError(f"{inner_status} {error_code}: {message}")

        return body

    return envelope


def _fetch_feed(feed_type: str, limit: int) -> list[dict]:
    """Запрашивает один фид (например, 'Google Trends') и приводит к общей структуре."""
    payload = {"mode": "get_top_trends", "type": feed_type, "limit": limit}
    data = _request(payload)

    items = data.get("data", [])
    as_of = data.get("as_of_ts")
    total = len(items) or 1

    trends = []
    for entry in items:
        rank, title = entry[0], entry[1]
        trends.append(
            {
                "title": title,
                "source": feed_type,
                "url": None,
                # чем выше место в топе (меньше rank), тем больше score_raw
                "score_raw": float(total - rank + 1),
                "published_at": as_of,
            }
        )
    return trends


def fetch_trends(query: str | None = None, limit: int = 20) -> list[dict]:
    """Возвращает список трендов через Trends MCP.

    Опрашивает несколько живых фидов и объединяет результаты. Если один фид
    недоступен (лимит, сеть, авторизация) — остальные всё равно возвращаются,
    ошибка только логируется.

    Каждый элемент: {title, source, url, score_raw, published_at}
    """
    all_trends: list[dict] = []

    for feed_type in FEED_TYPES:
        try:
            all_trends.extend(_fetch_feed(feed_type, limit))
        except TrendsMCPError as e:
            print(f"[trends_mcp_client] пропускаю фид '{feed_type}': {e}")

    if query:
        query_lower = query.lower()
        all_trends = [t for t in all_trends if query_lower in t["title"].lower()]

    return all_trends


if __name__ == "__main__":
    # Быстрая ручная проверка стабильности: python -m collectors.trends_mcp_client
    results = fetch_trends(limit=10)
    print(f"Получено трендов: {len(results)}")
    for t in results:
        print(f"  [{t['source']}] {t['title']} (score={t['score_raw']})")

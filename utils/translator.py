"""Перевод заголовков трендов на русский — для отображения в интерфейсе.

Не влияет на анализ и генерацию контента: там по-прежнему используется оригинальный
заголовок, Claude одинаково хорошо работает с английским.
"""

from __future__ import annotations

import json

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """Переведи заголовки трендов на русский язык — коротко и естественно,
как в новостной ленте, без пояснений и кавычек. Сохрани порядок и количество строк."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "translations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["translations"],
    "additionalProperties": False,
}


def translate_titles(titles: list[str]) -> list[str | None]:
    """Переводит заголовки на русский. При любой ошибке возвращает None на каждой позиции —
    вызывающий код в этом случае просто показывает оригинал."""
    if not titles:
        return []

    client = anthropic.Anthropic()
    user_content = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(titles))

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            output_config={
                "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
            },
            messages=[{"role": "user", "content": user_content}],
        )
        text = next(block.text for block in response.content if block.type == "text")
        translations = json.loads(text)["translations"]
        if len(translations) == len(titles):
            return translations
    except (anthropic.APIError, StopIteration, json.JSONDecodeError, KeyError):
        pass

    return [None] * len(titles)

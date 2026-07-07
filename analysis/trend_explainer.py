"""Уточнение тренда через веб-поиск: реальная дата и суть — по запросу, для одного тренда.

В отличие от analyze_trend (оценка виральности по общим знаниям модели), здесь Claude
реально ищет в интернете через встроенный web_search — полезно для трендов, слишком
свежих или нишевых, чтобы модель знала их по обучающим данным.
"""

from __future__ import annotations

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """Ты помогаешь автору Telegram-канала про нейросети разобраться в тренде.
Тебе дан заголовок тренда с одной из платформ (Google Trends/YouTube/TikTok/Reddit).
Найди через веб-поиск, что это такое и когда это реально произошло/завирусилось.

Ответь по-русски. Финальное сообщение начни СРАЗУ со слова "Дата:" — без вступительных фраз
вроде "Я поищу..." или "Вот что я нашёл...". Ровно такой формат:
Дата: <конкретная дата или период, например "3 июля 2026", либо "не удалось установить">
Суть: <2-3 предложения о том, что это за тренд и почему он завирусился>"""


class TrendExplanationError(Exception):
    """Ошибка уточнения тренда через веб-поиск."""


def explain_trend(title: str, source: str) -> str:
    """Возвращает текст с датой и сутью тренда, найденный через веб-поиск."""
    client = anthropic.Anthropic()

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[
                {
                    "type": "web_search_20260209",
                    "name": "web_search",
                    "max_uses": 3,
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"Источник: {source}\nЗаголовок тренда: {title}",
                }
            ],
        )
    except anthropic.APIError as e:
        raise TrendExplanationError(f"Claude API: {e}") from e

    if response.stop_reason == "refusal":
        raise TrendExplanationError("Claude отказался искать информацию по этому тренду")

    # Цитаты из web_search дробят финальный ответ на несколько text-блоков подряд.
    # Текст до первого обращения к поиску — это только "сейчас поищу..." нарратив,
    # его отбрасываем и берём всё, что идёт после последнего результата поиска.
    last_tool_index = max(
        (i for i, b in enumerate(response.content) if b.type != "text"),
        default=-1,
    )
    text_blocks = [
        block.text
        for i, block in enumerate(response.content)
        if block.type == "text" and i > last_tool_index
    ]
    if not text_blocks:
        raise TrendExplanationError("Не удалось получить ответ (пустой результат)")

    return "".join(text_blocks).strip()


def parse_explanation(text: str) -> tuple[str, str]:
    """Разбивает ответ explain_trend на (дата, суть) для отображения в отдельных колонках."""
    marker = "Суть:"
    if text.startswith("Дата:") and marker in text:
        idx = text.index(marker)
        date_part = text[len("Дата:"):idx].strip()
        gist_part = text[idx + len(marker):].strip()
        return date_part, gist_part
    return "", text

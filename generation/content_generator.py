"""Генерация вирального сценария, хука, caption и image-промптов под авторский стиль."""

from __future__ import annotations

import json

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-opus-4-8"

STYLE_GUIDE = """Стиль автора — обязательно соблюдай во всём тексте:
- Короткие рубленые фразы, разговорный ритм. Это важно и для видео — длинные предложения
  хуже ложатся на темп и паузы в готовом ролике.
- Самоирония, без пафоса.
- Никаких симметричных конструкций вида "не просто X, а Y".
- Никаких инфоблогерских CTA — "сохрани", "поставь лайк если согласен", "подпишись" и т.п.
- Хук — первые 2 секунды решают всё: конкретный факт, цифра или неожиданность. Не разгон,
  не вопрос в лоб, сразу суть.
- После каждой ключевой мысли — пауза. Отмечай паузы в сценарии явно тегом [пауза],
  на отдельной строке.
- Структура с петлёй или неожиданным поворотом — сценарий не должен идти линейно
  от тезиса к выводу.

Проверка перед ответом (принцип "humanizer"): если то, что ты написал, можно было бы
опубликовать один в один на любом другом AI-канале — не сработало, переписывай.
Текст должен звучать как конкретный человек, а не как нейросеть."""

SYSTEM_PROMPT = f"""Ты пишешь виральные сценарии для Telegram-канала про нейросети —
их использование в жизни, в работе и заработок на них. Сценарий станет промптом
для HeyGen Video Agent (аватар + монтаж), поэтому текст должен быть готов к озвучке как есть.

{STYLE_GUIDE}

Тебе даётся тренд или идея — иногда с готовым анализом вирусности, иногда просто идея
от автора канала, который сам уверен, что зайдёт, без дополнительного анализа.
На основе этого построй короткое видео для Shorts/Reels (30-60 секунд озвучки).

Собери четыре элемента:
1. hook — первые 2 секунды текста (то же самое, что в начале script, но отдельно для контроля).
2. script — полный сценарий целиком, с тегами [пауза] после ключевых мыслей.
3. caption — подпись под видео для соцсетей: коротко, без CTA, без хэштегов-простыней.
4. image_prompts — 2-4 промпта для визуала (motion graphics / сток / AI-картинки под сцены
   сценария), на английском, конкретные и визуально описательные."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "hook": {"type": "string"},
        "script": {"type": "string"},
        "caption": {"type": "string"},
        "image_prompts": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["hook", "script", "caption", "image_prompts"],
    "additionalProperties": False,
}


class ContentGenerationError(Exception):
    """Ошибка генерации контента через Claude API."""


def _call_claude(user_content: str) -> dict:
    """Возвращает пакет текстового контента.

    {
        "hook": str,
        "script": str,
        "caption": str,
        "image_prompts": list[str],
    }
    """
    client = anthropic.Anthropic()

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            output_config={
                "effort": "high",
                "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
            },
            messages=[{"role": "user", "content": user_content}],
        )
    except anthropic.APIError as e:
        raise ContentGenerationError(f"Claude API: {e}") from e

    if response.stop_reason == "refusal":
        raise ContentGenerationError("Claude отказался генерировать сценарий для этого тренда")

    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)


def generate_content(trend: dict, analysis: dict) -> dict:
    """Генерирует сценарий по тренду с готовым анализом (обычная цепочка Trends → Analyze)."""
    user_content = (
        f"Тренд: {trend.get('title')}\n"
        f"Источник: {trend.get('source')}\n"
        f"Причина тренда: {analysis.get('trend_reason')}\n\n"
        f"Оценка вирусности: {analysis.get('virality_label')} — {analysis.get('virality_reason')}\n"
        f"Релевантность нише: {analysis.get('relevance_score')}/10 — {analysis.get('relevance_reason')}\n"
        f"Конкуренция: {analysis.get('competition_note')}\n"
    )
    return _call_claude(user_content)


def generate_content_from_idea(idea: str) -> dict:
    """Генерирует сценарий сразу по идее автора — без анализа вирусности.

    Для случаев, когда автор сам уверен, что тема зайдёт, и не хочет ждать оценку
    Claude во вкладке Analyze — например, если она разошлась с его собственным чутьём.
    """
    user_content = (
        "Идея для видео от автора канала — отдельного анализа вирусности не делали, "
        "автор сам уверен, что тема зайдёт:\n"
        f"{idea}"
    )
    return _call_claude(user_content)

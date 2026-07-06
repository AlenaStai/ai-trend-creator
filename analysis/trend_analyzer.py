"""Скоринг трендов через Claude API: вероятность вирусности, релевантность, конкуренция."""

from __future__ import annotations

import json

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-opus-4-8"

NICHE_DESCRIPTION = (
    "Telegram-канал про нейросети: их использование в жизни, в работе и заработок на них. "
    "Аудитория — люди, которым интересно, как AI встраивается в повседневность, "
    "рабочие задачи и монетизацию."
)

VIRALITY_LABELS = ["вероятно залетит", "под вопросом", "вряд ли залетит"]

SYSTEM_PROMPT = f"""Ты — аналитик виральности контента для автора AI-блога.

Ниша канала: {NICHE_DESCRIPTION}

Тебе дают один тренд (заголовок, источник, сырой рейтинг популярности, дата) — оцени его
по трём осям и верни строго структурированный ответ.

1. Вирусность (virality_label): выбери ровно одну метку — "вероятно залетит", "под вопросом"
   или "вряд ли залетит". Обоснуй в virality_reason: что именно в тренде даёт (или не даёт)
   потенциал для короткого видео — неожиданность, эмоциональный заряд, простота пересказа
   за 2 секунды хука, актуальность момента.

2. Релевантность нише (relevance_score от 0 до 10, relevance_reason): насколько тренд связан
   с нейросетями и их применением в жизни/работе/заработке. Тренд может быть релевантен и
   косвенно — если из него можно сделать заход через призму AI (например, вирусное событие,
   которое интересно разобрать "как бы это сделал/изменил AI").

3. Конкуренция (competition_note): насколько тема уже заезжена другими AI-блогерами/каналами
   и есть ли ещё окно для свежего захода.

Дополнительно — причина тренда (trend_reason): кратко, почему это вообще стало трендом
именно сейчас (что произошло, что резонирует).

Пиши по-русски, кратко и по делу, без общих фраз и воды."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "virality_label": {"type": "string", "enum": VIRALITY_LABELS},
        "virality_reason": {"type": "string"},
        "relevance_score": {"type": "number"},
        "relevance_reason": {"type": "string"},
        "competition_note": {"type": "string"},
        "trend_reason": {"type": "string"},
    },
    "required": [
        "virality_label",
        "virality_reason",
        "relevance_score",
        "relevance_reason",
        "competition_note",
        "trend_reason",
    ],
    "additionalProperties": False,
}


class TrendAnalysisError(Exception):
    """Ошибка анализа тренда через Claude API."""


def analyze_trend(trend: dict) -> dict:
    """Возвращает оценку тренда.

    {
        "virality_label": "вероятно залетит" | "под вопросом" | "вряд ли залетит",
        "virality_reason": str,
        "relevance_score": float,
        "relevance_reason": str,
        "competition_note": str,
        "trend_reason": str,
    }
    """
    client = anthropic.Anthropic()

    user_content = (
        f"Заголовок: {trend.get('title')}\n"
        f"Источник: {trend.get('source')}\n"
        f"Сырой рейтинг популярности: {trend.get('score_raw')}\n"
        f"Дата/время: {trend.get('published_at')}\n"
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            output_config={
                "effort": "medium",
                "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
            },
            messages=[{"role": "user", "content": user_content}],
        )
    except anthropic.APIError as e:
        raise TrendAnalysisError(f"Claude API: {e}") from e

    if response.stop_reason == "refusal":
        raise TrendAnalysisError("Claude отказался анализировать этот тренд")

    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)

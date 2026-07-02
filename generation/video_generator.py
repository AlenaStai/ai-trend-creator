"""Генерация видео целиком через HeyGen Video Agent (сценарий → визуал → аватар → монтаж)."""

from __future__ import annotations


def generate_video(script: str, avatar_id: str | None = None) -> dict:
    """Запускает генерацию видео в формате Portrait через HeyGen Video Agent.

    Возвращает {"video_url": str, "status": str}
    """
    raise NotImplementedError

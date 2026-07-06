"""Генерация видео целиком через HeyGen Video Agent (сценарий → визуал → аватар → монтаж).

Работает через официальный HeyGen CLI (не через сырой REST API — HeyGen сам просит
не дёргать api.heygen.com напрямую, CLI/MCP делают коррекцию формата и подбор визуала).
Рендер занимает 20-45 минут, поэтому здесь только отправка задачи и отдельная проверка
статуса — без блокирующего ожидания.

Авторизация — только через локальную OAuth-сессию CLI (heygen auth login --oauth):
списывает кредиты обычного платного плана, а не отдельный пул API-кредитов. Ключ
HEYGEN_API_KEY здесь намеренно не используется.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

HEYGEN_AVATAR_ID = os.getenv("HEYGEN_AVATAR_ID")
HEYGEN_VOICE_ID = os.getenv("HEYGEN_VOICE_ID")

CLI_TIMEOUT = 30  # секунд на сам вызов CLI — рендер идёт асинхронно на стороне HeyGen
DOWNLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "videos"


class VideoGenerationError(Exception):
    """Ошибка при работе с HeyGen CLI."""


def _run_heygen(args: list[str]) -> dict:
    try:
        result = subprocess.run(
            ["heygen", *args],
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT,
            check=False,
        )
    except FileNotFoundError as e:
        raise VideoGenerationError(
            "HeyGen CLI не найден. Установите: "
            "curl -fsSL https://static.heygen.ai/cli/install.sh | bash"
        ) from e
    except subprocess.TimeoutExpired as e:
        raise VideoGenerationError(f"HeyGen CLI не ответил за {CLI_TIMEOUT}с") from e

    if result.returncode != 0:
        raise VideoGenerationError(f"heygen {' '.join(args)}: {result.stderr.strip()}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise VideoGenerationError(
            f"Не удалось разобрать ответ heygen CLI: {result.stdout[:300]}"
        ) from e


def submit_video(script: str) -> dict:
    """Отправляет сценарий в HeyGen Video Agent. Не ждёт рендера (20-45 минут).

    Формат — Portrait, аватар и голос — из .env (HEYGEN_AVATAR_ID / HEYGEN_VOICE_ID).

    Возвращает {"video_id": str | None, "session_id": str}.
    """
    if not HEYGEN_AVATAR_ID or not HEYGEN_VOICE_ID:
        raise VideoGenerationError("HEYGEN_AVATAR_ID / HEYGEN_VOICE_ID не заданы в .env")

    response = _run_heygen(
        [
            "video-agent", "create",
            "--prompt", script,
            "--avatar-id", HEYGEN_AVATAR_ID,
            "--voice-id", HEYGEN_VOICE_ID,
            "--orientation", "portrait",
        ]
    )
    data = response.get("data", {})
    return {"video_id": data.get("video_id"), "session_id": data.get("session_id")}


def check_status(session_id: str) -> dict:
    """Проверяет статус рендера: thinking → generating → completed | failed."""
    response = _run_heygen(["video-agent", "get", session_id])
    return response.get("data", {})


def download_video(video_id: str) -> str:
    """Скачивает готовое видео в data/videos/. Возвращает путь к файлу."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DOWNLOAD_DIR / f"{video_id}.mp4"

    response = _run_heygen(
        ["video", "download", video_id, "--output-path", str(output_path), "--force"]
    )
    path = response.get("path")
    if not path:
        raise VideoGenerationError(f"Не удалось получить путь к скачанному видео: {response}")
    return path

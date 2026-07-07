"""Расшифровка голосовой заметки в текст — чтобы надиктовать идею вместо печати.

Использует бесплатное распознавание речи Google через SpeechRecognition (без
API-ключа и без биллинга) — этого достаточно для коротких заметок в одно-два
предложения. st.audio_input отдаёт аудио в WAV, поэтому ffmpeg не нужен.
"""

from __future__ import annotations

import io

import speech_recognition as sr


class TranscriptionError(Exception):
    """Ошибка распознавания речи."""


def transcribe_audio(audio_bytes: bytes, language: str = "ru-RU") -> str:
    """Распознаёт русскую речь из WAV-аудио в текст."""
    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
    except Exception as e:
        raise TranscriptionError(f"не удалось прочитать аудио: {e}") from e

    try:
        return recognizer.recognize_google(audio_data, language=language)
    except sr.UnknownValueError as e:
        raise TranscriptionError("речь не распознана — попробуй сказать чётче и не слишком тихо") from e
    except sr.RequestError as e:
        raise TranscriptionError(f"сервис распознавания недоступен: {e}") from e

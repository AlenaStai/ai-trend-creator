"""Экспорт готового пакета: видеофайл + текстовый пакет (сценарий, caption, image-промпты)."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def export_package(video_path: str, content: dict, output_dir: str = "export_output") -> str:
    """Сохраняет видео и текстовый пакет в output_dir, возвращает путь к папке с экспортом."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_dir = Path(output_dir) / timestamp
    package_dir.mkdir(parents=True, exist_ok=True)

    video_src = Path(video_path)
    shutil.copy2(video_src, package_dir / video_src.name)

    text_lines = [
        "# Хук",
        content.get("hook", ""),
        "",
        "# Сценарий",
        content.get("script", ""),
        "",
        "# Caption",
        content.get("caption", ""),
        "",
        "# Image-промпты",
    ]
    text_lines.extend(f"- {prompt}" for prompt in content.get("image_prompts", []))

    (package_dir / "content.md").write_text("\n".join(text_lines), encoding="utf-8")

    return str(package_dir)

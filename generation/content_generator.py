"""Генерация вирального сценария, хука, caption и image-промптов под авторский стиль."""


def generate_content(trend: dict, analysis: dict) -> dict:
    """Возвращает пакет текстового контента.

    {
        "hook": str,
        "script": str,
        "caption": str,
        "image_prompts": list[str],
    }
    """
    raise NotImplementedError

"""AI Trend Creator — точка входа Streamlit.

Цепочка: Trends → Analyze → Generate Content → Generate Video → Экспорт
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from analysis.trend_analyzer import TrendAnalysisError, analyze_trend
from analysis.trend_explainer import TrendExplanationError, explain_trend
from collectors.reddit_collector import RedditCollectorError
from collectors.reddit_collector import fetch_trends as fetch_trends_reddit
from collectors.trends_mcp_client import TrendsMCPError
from collectors.trends_mcp_client import fetch_trends as fetch_trends_mcp
from collectors.youtube_collector import YouTubeCollectorError
from collectors.youtube_collector import fetch_trends as fetch_trends_youtube
from export.exporter import export_package
from generation.content_generator import (
    ContentGenerationError,
    generate_content,
    generate_content_from_idea,
)
from generation.video_generator import VideoGenerationError, check_status, download_video, submit_video
from utils.db import get_recent_trends, init_db, save_trends
from utils.speech import TranscriptionError, transcribe_audio
from utils.translator import translate_titles


def collect_trends_with_fallback(limit: int = 20) -> tuple[list[dict], str | None]:
    """Собирает тренды: Trends MCP — основной источник, YouTube и Reddit — фолбэк.

    Переключается на следующий источник, если предыдущий недоступен или не вернул
    ни одного тренда. Возвращает (тренды, название сработавшего источника).
    """
    try:
        trends = fetch_trends_mcp(limit=limit)
        if trends:
            return trends, "Trends MCP"
        st.warning("Trends MCP не вернул ни одного тренда, пробую YouTube...")
    except TrendsMCPError as e:
        st.warning(f"Trends MCP недоступен: {e}. Пробую YouTube...")

    try:
        trends = fetch_trends_youtube(limit=limit)
        if trends:
            return trends, "YouTube Data API"
        st.warning("YouTube не вернул ни одного тренда, пробую Reddit...")
    except YouTubeCollectorError as e:
        st.warning(f"YouTube недоступен: {e}. Пробую Reddit...")

    try:
        trends = fetch_trends_reddit(limit=limit)
        if trends:
            return trends, "Reddit API"
    except RedditCollectorError as e:
        st.error(f"Reddit тоже недоступен: {e}")

    return [], None

st.set_page_config(page_title="AI Trend Creator", page_icon="🎬", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Quicksand', sans-serif;
    }

    h1, h2, h3 {
        font-family: 'Quicksand', sans-serif;
        font-weight: 700;
    }

    /* Сайдбар — мягкий пастельный градиент */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F3E8FF 0%, #FDE8F0 100%);
        border-right: 1px solid #EBDCF9;
    }

    /* Кнопки — округлые, с мягкой тенью */
    div[data-testid="stButton"] > button {
        border-radius: 14px;
        border: 1px solid #E4D3FB;
        box-shadow: 0 2px 6px rgba(183, 156, 237, 0.25);
        transition: transform 0.1s ease;
    }
    div[data-testid="stButton"] > button:hover {
        transform: translateY(-1px);
        border-color: #B79CED;
        color: #7C5DC7;
    }

    /* Вкладки — пилюли вместо строгих линий */
    div[data-testid="stTabs"] button[role="tab"] {
        border-radius: 999px;
        padding: 6px 18px;
        margin-right: 6px;
        background-color: #F8F3FF;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        background-color: #B79CED;
        color: white !important;
    }

    /* Поля ввода и текстовые области — мягкие скругления */
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stTextInput"] input,
    div[data-testid="stSelectbox"] > div {
        border-radius: 12px !important;
    }

    /* Карточки метрик и датафреймов */
    div[data-testid="stMetric"], div[data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
    }
    div[data-testid="stMetric"] {
        background-color: #FFF6FB;
        padding: 12px;
        border: 1px solid #F5DCEC;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

init_db()

st.title("🎬 AI Trend Creator")

with st.sidebar:
    st.subheader("✨ Статус цепочки")

    sidebar_trend = st.session_state.get("last_trend")
    sidebar_analysis = st.session_state.get("last_analysis")
    sidebar_content = st.session_state.get("last_content")
    sidebar_video_status = st.session_state.get("video_status")
    sidebar_video_path = st.session_state.get("video_path")

    st.write(
        "1. Тренд — "
        + (
            f"✅ {(sidebar_trend.get('title_ru') or sidebar_trend['title'])[:40]}"
            if sidebar_trend
            else "—"
        )
    )
    st.write("2. Анализ — " + (f"✅ {sidebar_analysis['virality_label']}" if sidebar_analysis else "—"))
    st.write("3. Сценарий — " + ("✅ готов" if sidebar_content else "—"))
    if sidebar_video_path:
        st.write("4. Видео — ✅ скачано")
    elif sidebar_video_status:
        st.write(f"4. Видео — ⏳ {sidebar_video_status}")
    else:
        st.write("4. Видео — —")

    st.divider()
    if st.button("Начать новый цикл"):
        for key in (
            "last_trend", "last_analysis", "last_content",
            "video_session_id", "video_id", "video_status", "video_path",
        ):
            st.session_state.pop(key, None)
        st.rerun()

tab_trends, tab_analyze, tab_content, tab_video = st.tabs(
    ["🔥 1. Trends", "🔍 2. Analyze", "✍️ 3. Generate Content", "🎬 4. Generate Video"]
)

with tab_trends:
    st.header("🔥 Сбор трендов")
    st.caption("Источники: Trends MCP → YouTube → Reddit (автоматический фолбэк при ошибке)")
    if st.button("Собрать тренды"):
        with st.spinner("Собираю тренды..."):
            trends, source_used = collect_trends_with_fallback(limit=20)
        if trends:
            with st.spinner("Перевожу заголовки..."):
                translations = translate_titles([t["title"] for t in trends])
            for t, title_ru in zip(trends, translations):
                t["title_ru"] = title_ru

            saved = save_trends(trends)
            st.session_state["last_collected_trends"] = trends
            st.session_state["last_collected_source"] = source_used
            st.session_state["last_collected_saved"] = saved
        else:
            st.session_state.pop("last_collected_trends", None)
            st.error("Все источники трендов недоступны")

    last_collected_trends = st.session_state.get("last_collected_trends")
    if last_collected_trends:
        st.success(
            f"Собрано через {st.session_state['last_collected_source']}. "
            f"Сохранено трендов: {st.session_state['last_collected_saved']}"
        )
        st.dataframe(
            last_collected_trends,
            use_container_width=True,
            column_config={
                "title": "Заголовок",
                "title_ru": "Заголовок (рус.)",
                "url": st.column_config.LinkColumn("Ссылка", display_text="Открыть"),
            },
        )
        st.caption(
            "Суть и дату конкретного тренда можно уточнить через веб-поиск во вкладке Analyze"
        )

with tab_analyze:
    st.header("🔍 Анализ и скоринг")
    st.caption("Оценка виральности через Claude API: вероятно залетит / под вопросом / вряд ли")

    recent_trends = get_recent_trends(limit=100)
    if not recent_trends:
        st.info("Сначала соберите тренды во вкладке Trends")
    else:
        options = {
            f"[{t['source']}] {t.get('title_ru') or t['title']}": t for t in recent_trends
        }
        selected_label = st.selectbox("Выберите тренд", options.keys())
        selected_trend = options[selected_label]
        if selected_trend.get("title_ru"):
            st.caption(f"Оригинал: {selected_trend['title']}")

        if selected_trend.get("trend_gist"):
            st.info(f"**{selected_trend.get('trend_date') or '?'}** — {selected_trend['trend_gist']}")

        button_label = (
            "🔎 Уточнить ещё раз (веб-поиск)"
            if selected_trend.get("trend_gist")
            else "🔎 Найти дату и суть (веб-поиск)"
        )
        if st.button(button_label):
            with st.spinner("Ищу в интернете через Claude..."):
                try:
                    explanation = explain_trend(
                        selected_trend["title"], selected_trend["source"]
                    )
                except TrendExplanationError as e:
                    st.error(f"Не удалось уточнить тренд: {e}")
                else:
                    st.session_state[f"explanation::{selected_label}"] = explanation

        explanation = st.session_state.get(f"explanation::{selected_label}")
        if explanation:
            st.info(explanation)

        if st.button("Проанализировать выбранный тренд"):
            with st.spinner("Анализирую через Claude API..."):
                try:
                    result = analyze_trend(selected_trend)
                except TrendAnalysisError as e:
                    st.error(f"Не удалось проанализировать тренд: {e}")
                else:
                    st.session_state["last_trend"] = selected_trend
                    st.session_state["last_analysis"] = result
                    st.session_state["last_content_source"] = "analysis"

        last_analysis = st.session_state.get("last_analysis")
        last_trend = st.session_state.get("last_trend")
        if last_analysis and last_trend and "virality_reason" in last_analysis:
            st.caption(
                f"Последний анализ: [{last_trend['source']}] "
                f"{last_trend.get('title_ru') or last_trend['title']}"
            )
            st.subheader(last_analysis["virality_label"])
            st.write(last_analysis["virality_reason"])
            st.metric("Релевантность нише", f"{last_analysis['relevance_score']}/10")
            st.write(last_analysis["relevance_reason"])
            st.write("**Конкуренция:**", last_analysis["competition_note"])
            st.write("**Почему это тренд:**", last_analysis["trend_reason"])

with tab_content:
    st.header("✍️ Генерация контента")
    st.caption("Хук за 2 секунды, сценарий, caption, image-промпты — под авторский стиль")

    st.subheader("⚡ Быстро по своей идее")
    st.caption(
        "Пропускает Analyze — на случай, если ты сама уверена, что тема зайдёт, "
        "а не согласна с оценкой Claude."
    )
    idea_audio = st.audio_input("🎤 Или надиктуй идею голосом")
    if idea_audio is not None and st.button("Расшифровать в текст"):
        with st.spinner("Распознаю речь..."):
            try:
                transcript = transcribe_audio(idea_audio.read())
            except TranscriptionError as e:
                st.error(f"Не удалось распознать речь: {e}")
            else:
                st.session_state["own_idea_input"] = transcript
                st.rerun()

    idea_text = st.text_area(
        "Твоя идея",
        placeholder="Например: люди делают предложение руки и сердца на крышах небоскрёбов — залетит однозначно",
        key="own_idea_input",
    )
    if st.button("Сгенерировать по идее"):
        if not idea_text.strip():
            st.warning("Сначала опиши идею")
        else:
            with st.spinner("Генерирую сценарий через Claude API..."):
                try:
                    content = generate_content_from_idea(idea_text.strip())
                except ContentGenerationError as e:
                    st.error(f"Не удалось сгенерировать сценарий: {e}")
                else:
                    st.session_state["last_content"] = content
                    st.session_state["last_content_source"] = "idea"
                    st.session_state["last_idea_text"] = idea_text.strip()
                    st.session_state["last_trend"] = {
                        "title": idea_text.strip()[:80],
                        "source": "Своя идея",
                    }
                    st.session_state["last_analysis"] = {
                        "virality_label": "по мнению автора — залетит"
                    }
                    for edit_key in ("edit_hook", "edit_script", "edit_caption", "edit_image_prompts"):
                        st.session_state.pop(edit_key, None)
                    st.rerun()

    st.divider()

    last_trend = st.session_state.get("last_trend")
    last_analysis = st.session_state.get("last_analysis")

    if not last_trend or not last_analysis:
        st.info("Сначала проанализируйте тренд во вкладке Analyze — либо сгенерируй по своей идее выше")
    else:
        st.caption(f"Тренд: [{last_trend['source']}] {last_trend['title']} — {last_analysis['virality_label']}")

        last_content = st.session_state.get("last_content")
        generate_label = "Сгенерировать заново" if last_content else "Сгенерировать сценарий"

        if st.button(generate_label):
            with st.spinner("Генерирую сценарий через Claude API..."):
                try:
                    if st.session_state.get("last_content_source") == "idea":
                        content = generate_content_from_idea(st.session_state["last_idea_text"])
                    else:
                        content = generate_content(last_trend, last_analysis)
                except ContentGenerationError as e:
                    st.error(f"Не удалось сгенерировать сценарий: {e}")
                else:
                    st.session_state["last_content"] = content
                    # сбрасываем поля редактирования, чтобы подхватили новый текст
                    for edit_key in ("edit_hook", "edit_script", "edit_caption", "edit_image_prompts"):
                        st.session_state.pop(edit_key, None)
                    st.rerun()

        last_content = st.session_state.get("last_content")
        if last_content:
            st.divider()
            st.subheader("Редактирование сценария")
            st.caption(
                "Поправьте текст вручную и сохраните — в HeyGen уйдёт версия с правками. "
                "Либо нажмите «Сгенерировать заново» выше, если хочется другой вариант целиком."
            )

            edited_hook = st.text_area("Хук", value=last_content["hook"], height=80, key="edit_hook")
            edited_script = st.text_area(
                "Сценарий", value=last_content["script"], height=280, key="edit_script"
            )
            edited_caption = st.text_area(
                "Caption", value=last_content["caption"], height=100, key="edit_caption"
            )
            edited_image_prompts = st.text_area(
                "Image-промпты (по одному на строку)",
                value="\n".join(last_content["image_prompts"]),
                height=120,
                key="edit_image_prompts",
            )

            if st.button("Сохранить правки"):
                st.session_state["last_content"] = {
                    "hook": edited_hook,
                    "script": edited_script,
                    "caption": edited_caption,
                    "image_prompts": [
                        line.strip() for line in edited_image_prompts.splitlines() if line.strip()
                    ],
                }
                st.success("Правки сохранены — именно этот текст уйдёт в HeyGen")

with tab_video:
    st.header("🎬 Генерация видео")
    st.caption("HeyGen Video Agent: сценарий → визуал → аватар → монтаж, формат Portrait")
    st.caption("Рендер занимает 20-45 минут — отправка и проверка статуса разделены")

    last_content = st.session_state.get("last_content")

    if not last_content:
        st.info("Сначала сгенерируйте сценарий во вкладке Generate Content")
    else:
        if st.button("Отправить сценарий в HeyGen"):
            with st.spinner("Отправляю в HeyGen Video Agent..."):
                try:
                    submitted = submit_video(last_content["script"])
                except VideoGenerationError as e:
                    st.error(f"Не удалось отправить видео на генерацию: {e}")
                else:
                    st.session_state["video_session_id"] = submitted["session_id"]
                    st.session_state["video_id"] = submitted.get("video_id")
                    st.session_state.pop("video_status", None)
                    st.success(f"Отправлено. session_id: {submitted['session_id']}")

        video_session_id = st.session_state.get("video_session_id")
        if video_session_id:
            st.caption(f"Текущая задача: {video_session_id}")

            if st.button("Проверить статус"):
                with st.spinner("Проверяю статус..."):
                    try:
                        status = check_status(video_session_id)
                    except VideoGenerationError as e:
                        st.error(f"Не удалось проверить статус: {e}")
                    else:
                        st.session_state["video_status"] = status.get("status")
                        st.session_state["video_progress"] = status.get("progress", 0)
                        if status.get("video_id"):
                            st.session_state["video_id"] = status["video_id"]

                        model_messages = [
                            m for m in status.get("messages", []) if m.get("role") == "model"
                        ]
                        if model_messages:
                            latest = max(model_messages, key=lambda m: m.get("created_at", 0))
                            st.session_state["video_agent_message"] = latest.get("content", "")

            video_status_display = st.session_state.get("video_status")
            if video_status_display:
                st.write(f"**Статус:** {video_status_display}")
                st.progress(min(st.session_state.get("video_progress", 0), 100) / 100)
                agent_message = st.session_state.get("video_agent_message")
                if agent_message:
                    st.caption(f"Агент: {agent_message}")

            video_id = st.session_state.get("video_id")
            video_status = st.session_state.get("video_status")
            if video_id and video_status != "completed":
                st.caption("Видео ещё не готово — сначала проверьте статус")
            elif video_id and st.button("Скачать готовое видео"):
                try:
                    path = download_video(video_id)
                except VideoGenerationError as e:
                    st.error(f"Не удалось скачать видео: {e}")
                else:
                    st.session_state["video_path"] = path
                    st.success(f"Видео сохранено: {path}")

            video_path_ready = st.session_state.get("video_path")
            if video_path_ready:
                with open(video_path_ready, "rb") as f:
                    st.download_button(
                        "⬇️ Скачать видео на компьютер (в Загрузки)",
                        data=f.read(),
                        file_name=Path(video_path_ready).name,
                        mime="video/mp4",
                    )

    st.divider()
    st.subheader("Экспорт")

    video_path = st.session_state.get("video_path")
    if not video_path or not last_content:
        st.info("Сначала сгенерируйте сценарий и скачайте готовое видео")
    else:
        if st.button("Экспортировать пакет"):
            package_dir = export_package(video_path, last_content)
            st.success(f"Пакет сохранён: {package_dir}")

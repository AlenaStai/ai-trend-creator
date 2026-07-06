"""AI Trend Creator — точка входа Streamlit.

Цепочка: Trends → Analyze → Generate Content → Generate Video → Экспорт
"""

from __future__ import annotations

import streamlit as st

from analysis.trend_analyzer import TrendAnalysisError, analyze_trend
from collectors.reddit_collector import RedditCollectorError
from collectors.reddit_collector import fetch_trends as fetch_trends_reddit
from collectors.trends_mcp_client import TrendsMCPError
from collectors.trends_mcp_client import fetch_trends as fetch_trends_mcp
from collectors.youtube_collector import YouTubeCollectorError
from collectors.youtube_collector import fetch_trends as fetch_trends_youtube
from export.exporter import export_package
from generation.content_generator import ContentGenerationError, generate_content
from generation.video_generator import VideoGenerationError, check_status, download_video, submit_video
from utils.db import get_recent_trends, init_db, save_trends


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

init_db()

st.title("AI Trend Creator")

with st.sidebar:
    st.subheader("Статус цепочки")

    sidebar_trend = st.session_state.get("last_trend")
    sidebar_analysis = st.session_state.get("last_analysis")
    sidebar_content = st.session_state.get("last_content")
    sidebar_video_status = st.session_state.get("video_status")
    sidebar_video_path = st.session_state.get("video_path")

    st.write("1. Тренд — " + (f"✅ {sidebar_trend['title'][:40]}" if sidebar_trend else "—"))
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
    ["1. Trends", "2. Analyze", "3. Generate Content", "4. Generate Video"]
)

with tab_trends:
    st.header("Сбор трендов")
    st.caption("Источники: Trends MCP → YouTube → Reddit (автоматический фолбэк при ошибке)")
    if st.button("Собрать тренды"):
        with st.spinner("Собираю тренды..."):
            trends, source_used = collect_trends_with_fallback(limit=20)
        if trends:
            saved = save_trends(trends)
            st.success(f"Собрано через {source_used}. Сохранено трендов: {saved}")
            st.dataframe(trends, use_container_width=True)
        else:
            st.error("Все источники трендов недоступны")

with tab_analyze:
    st.header("Анализ и скоринг")
    st.caption("Оценка виральности через Claude API: вероятно залетит / под вопросом / вряд ли")

    recent_trends = get_recent_trends(limit=50)
    if not recent_trends:
        st.info("Сначала соберите тренды во вкладке Trends")
    else:
        options = {
            f"[{t['source']}] {t['title']}": t for t in recent_trends
        }
        selected_label = st.selectbox("Выберите тренд", options.keys())

        if st.button("Проанализировать выбранный тренд"):
            with st.spinner("Анализирую через Claude API..."):
                try:
                    result = analyze_trend(options[selected_label])
                except TrendAnalysisError as e:
                    st.error(f"Не удалось проанализировать тренд: {e}")
                else:
                    st.session_state["last_trend"] = options[selected_label]
                    st.session_state["last_analysis"] = result

                    st.subheader(result["virality_label"])
                    st.write(result["virality_reason"])
                    st.metric("Релевантность нише", f"{result['relevance_score']}/10")
                    st.write(result["relevance_reason"])
                    st.write("**Конкуренция:**", result["competition_note"])
                    st.write("**Почему это тренд:**", result["trend_reason"])

with tab_content:
    st.header("Генерация контента")
    st.caption("Хук за 2 секунды, сценарий, caption, image-промпты — под авторский стиль")

    last_trend = st.session_state.get("last_trend")
    last_analysis = st.session_state.get("last_analysis")

    if not last_trend or not last_analysis:
        st.info("Сначала проанализируйте тренд во вкладке Analyze")
    else:
        st.caption(f"Тренд: [{last_trend['source']}] {last_trend['title']} — {last_analysis['virality_label']}")

        if st.button("Сгенерировать сценарий"):
            with st.spinner("Генерирую сценарий через Claude API..."):
                try:
                    content = generate_content(last_trend, last_analysis)
                except ContentGenerationError as e:
                    st.error(f"Не удалось сгенерировать сценарий: {e}")
                else:
                    st.session_state["last_content"] = content

                    st.subheader("Хук")
                    st.write(content["hook"])
                    st.subheader("Сценарий")
                    st.text(content["script"])
                    st.subheader("Caption")
                    st.write(content["caption"])
                    st.subheader("Image-промпты")
                    for prompt in content["image_prompts"]:
                        st.write(f"- {prompt}")

with tab_video:
    st.header("Генерация видео")
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
                        if status.get("video_id"):
                            st.session_state["video_id"] = status["video_id"]

                        st.write(f"**Статус:** {status.get('status')}")
                        st.progress(min(status.get("progress", 0), 100) / 100)

                        model_messages = [
                            m for m in status.get("messages", []) if m.get("role") == "model"
                        ]
                        if model_messages:
                            latest = max(model_messages, key=lambda m: m.get("created_at", 0))
                            st.caption(f"Агент: {latest.get('content', '')}")

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

    st.divider()
    st.subheader("Экспорт")

    video_path = st.session_state.get("video_path")
    if not video_path or not last_content:
        st.info("Сначала сгенерируйте сценарий и скачайте готовое видео")
    else:
        if st.button("Экспортировать пакет"):
            package_dir = export_package(video_path, last_content)
            st.success(f"Пакет сохранён: {package_dir}")

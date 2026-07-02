"""AI Trend Creator — точка входа Streamlit.

Цепочка: Trends → Analyze → Generate Content → Generate Video → Экспорт
"""

import streamlit as st

from utils.db import init_db

st.set_page_config(page_title="AI Trend Creator", page_icon="🎬", layout="wide")

init_db()

st.title("AI Trend Creator")

tab_trends, tab_analyze, tab_content, tab_video = st.tabs(
    ["Trends", "Analyze", "Generate Content", "Generate Video"]
)

with tab_trends:
    st.header("Сбор трендов")
    st.caption("Источники: Trends MCP (основной) + Reddit / YouTube / RSS (фолбэк)")
    if st.button("Собрать тренды"):
        st.info("Пока заглушка — коллекторы ещё не реализованы")

with tab_analyze:
    st.header("Анализ и скоринг")
    st.caption("Оценка виральности через Claude API: вероятно залетит / под вопросом / вряд ли")
    if st.button("Проанализировать выбранный тренд"):
        st.info("Пока заглушка — анализатор ещё не реализован")

with tab_content:
    st.header("Генерация контента")
    st.caption("Хук за 2 секунды, сценарий, caption, image-промпты — под авторский стиль")
    if st.button("Сгенерировать сценарий"):
        st.info("Пока заглушка — генератор контента ещё не реализован")

with tab_video:
    st.header("Генерация видео")
    st.caption("HeyGen Video Agent: сценарий → визуал → аватар → монтаж, формат Portrait")
    if st.button("Сгенерировать видео"):
        st.info("Пока заглушка — видео-генератор ещё не реализован")

    st.divider()
    st.subheader("Экспорт")
    if st.button("Экспортировать пакет"):
        st.info("Пока заглушка — экспортёр ещё не реализован")

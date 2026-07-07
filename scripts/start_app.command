#!/bin/bash
# Запуск AI Trend Creator: поднимает Streamlit (если ещё не запущен) и открывает браузер.

PROJECT_DIR="/Users/alena/ai-trend-creator"
URL="http://localhost:8501"
LOG_FILE="/tmp/ai-trend-creator-streamlit.log"

cd "$PROJECT_DIR" || exit 1

if ! lsof -i :8501 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Запускаю сервер..."
    source .venv/bin/activate
    nohup streamlit run app.py --server.headless true > "$LOG_FILE" 2>&1 &
    disown

    for i in $(seq 1 30); do
        if curl -s -o /dev/null "$URL"; then
            break
        fi
        sleep 1
    done
else
    echo "Сервер уже запущен."
fi

open "$URL"

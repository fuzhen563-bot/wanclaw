#!/bin/bash
# 版权所有 © 2025-2026 厦门万岳科技有限公司
SERVICE_NAME="wanclaw"
INSTALL_DIR="${INSTALL_DIR:-/opt/wanclaw}"
DATA_DIR="${DATA_DIR:-/var/lib/wanclaw}"
PID_FILE="${DATA_DIR}/wanclaw.pid"

if command -v systemctl &>/dev/null && systemctl list-unit-files "$SERVICE_NAME.service" &>/dev/null; then
    exec systemctl stop "$SERVICE_NAME"
fi

if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        sleep 1
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID"
        fi
        echo "WanClaw 已停止 (PID: $PID)"
    else
        echo "进程已不存在"
    fi
    rm -f "$PID_FILE"
else
    PIDS=$(pgrep -f "uvicorn.*wanclaw.*im_adapter" 2>/dev/null || true)
    if [[ -n "$PIDS" ]]; then
        echo "$PIDS" | xargs kill 2>/dev/null || true
        sleep 1
        echo "WanClaw 已停止"
    else
        echo "WanClaw 未运行"
    fi
fi

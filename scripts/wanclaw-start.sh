#!/bin/bash
# 版权所有 © 2025-2026 厦门万岳科技有限公司
SERVICE_NAME="wanclaw"
INSTALL_DIR="${INSTALL_DIR:-/opt/wanclaw}"
DATA_DIR="${DATA_DIR:-/var/lib/wanclaw}"

if command -v systemctl &>/dev/null && systemctl list-unit-files "$SERVICE_NAME.service" &>/dev/null; then
    exec systemctl start "$SERVICE_NAME"
fi

PYTHON_CMD="${INSTALL_DIR}/.venv/bin/python"
SCRIPT_DIR="${INSTALL_DIR}/wanclaw/backend/im_adapter"
PID_FILE="${DATA_DIR}/wanclaw.pid"

if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "WanClaw 已在运行 (PID: $PID)"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

cd "$SCRIPT_DIR"
nohup "$PYTHON_CMD" -m uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000 > /var/log/wanclaw/wanclaw-stdout.log 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"
echo "WanClaw 已启动 (PID: $PID)"

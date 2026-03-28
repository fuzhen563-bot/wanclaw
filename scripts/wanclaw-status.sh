#!/bin/bash
# 版权所有 © 2025-2026 厦门万岳科技有限公司
SERVICE_NAME="wanclaw"
INSTALL_DIR="${INSTALL_DIR:-/opt/wanclaw}"
DATA_DIR="${DATA_DIR:-/var/lib/wanclaw}"
PID_FILE="${DATA_DIR}/wanclaw.pid"
PORT="${PORT:-8000}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "  ${BLUE}WanClaw 服务状态${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"

if command -v systemctl &>/dev/null && systemctl list-unit-files "$SERVICE_NAME.service" &>/dev/null; then
    echo ""
    systemctl status "$SERVICE_NAME" --no-pager -l
    echo ""
fi

echo "━━━ 进程信息 ━━━"
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "  PID:     ${GREEN}$PID${NC} (运行中)"
        CPU=$(ps -p "$PID" -o %cpu= 2>/dev/null | tr -d ' ' || echo "?")
        MEM=$(ps -p "$PID" -o %mem= 2>/dev/null | tr -d ' ' || echo "?")
        echo -e "  CPU:     ${CPU}%"
        echo -e "  内存:    ${MEM}%"
        UPTIME=$(ps -p "$PID" -o etime= 2>/dev/null | tr -d ' ' || echo "?")
        echo -e "  运行时间: $UPTIME"
    else
        echo -e "  PID 文件: ${YELLOW}$PID (进程已退出)${NC}"
    fi
else
    PIDS=$(pgrep -f "uvicorn.*wanclaw.*im_adapter" 2>/dev/null || true)
    if [[ -n "$PIDS" ]]; then
        echo -e "  进程:    ${GREEN}运行中${NC} (非 systemd 管理)"
        echo "$PIDS" | head -1 | xargs -I{} sh -c "echo '  PID:     {}' && CPU=\$(ps -p {} -o %cpu= | tr -d ' ' || echo '?'); echo '  CPU:     '\$CPU'%'"
    else
        echo -e "  状态:    ${RED}未运行${NC}"
    fi
fi

echo ""
echo "━━━ 网络监听 ━━━"
if command -v ss &>/dev/null; then
    ss -tlnp 2>/dev/null | grep ":$PORT " && echo "" || echo -e "  ${RED}端口 $PORT 未监听${NC}"
elif command -v netstat &>/dev/null; then
    netstat -tlnp 2>/dev/null | grep ":$PORT " && echo "" || echo -e "  ${RED}端口 $PORT 未监听${NC}"
fi

echo "━━━ HTTP 探测 ━━━"
HTTP_CODE=$(curl -sf -m 3 "http://localhost:$PORT/" -o /dev/null -w '%{http_code}' 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
    echo -e "  首页:    ${GREEN}200 OK${NC}"
else
    echo -e "  首页:    ${RED}状态码: $HTTP_CODE${NC}"
fi

HEALTH=$(curl -sf -m 3 "http://localhost:$PORT/health" 2>/dev/null || echo "{}")
STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "error")
if [[ "$STATUS" == "ok" ]]; then
    echo -e "  健康端点: ${GREEN}ok${NC}"
else
    echo -e "  健康端点: ${YELLOW}$STATUS${NC}"
fi

echo ""
echo "━━━ 最近日志 ━━━"
LOG_FILE="/var/log/wanclaw/wanclaw.log"
if [[ -f "$LOG_FILE" ]]; then
    tail -n 5 "$LOG_FILE" 2>/dev/null | while IFS= read -r line; do
        echo -e "  $line"
    done
else
    echo -e "  (无日志文件)"
fi

echo ""

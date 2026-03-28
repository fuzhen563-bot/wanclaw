#!/bin/bash
# =============================================================================
#  WanClaw 健康检查脚本
#  版权所有 © 2025-2026 厦门亦梓科技有限公司
#  https://github.com/fuzhen563-bot/wanclaw
# =============================================================================
set -e
HOST="${HOST:-localhost}"
PORT="${PORT:-8000}"
TIMEOUT="${TIMEOUT:-5}"
AUTO_RESTART="${AUTO_RESTART:-false}"
LOG_DIR="${LOG_DIR:-/var/log/wanclaw}"
METRIC_FILE="$LOG_DIR/health_metrics.json"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

log_ok()   { echo -e "${GREEN}[OK]${NC}   $*"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $*" >&2; ((ERRORS++)); }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*" >&2; ((WARNINGS++)); }
log_info() { echo -e "${BLUE}[INFO]${NC}  $*"; }

check_http() {
    log_info "检查 HTTP 服务..."
    HTTP_CODE=$(curl -sf -m "$TIMEOUT" "http://$HOST:$PORT/" -o /dev/null -w '%{http_code}' 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" == "200" ]]; then
        log_ok "HTTP 服务正常 (状态码: $HTTP_CODE)"
        return 0
    elif [[ "$HTTP_CODE" == "000" ]]; then
        log_fail "HTTP 服务无响应 (curl 超时)"
        return 1
    else
        log_warn "HTTP 服务异常 (状态码: $HTTP_CODE)"
        return 1
    fi
}

check_health() {
    log_info "检查 /health 端点..."
    HEALTH=$(curl -sf -m "$TIMEOUT" "http://$HOST:$PORT/health" 2>/dev/null)
    if [[ -n "$HEALTH" ]]; then
        STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "unknown")
        if [[ "$STATUS" == "ok" ]]; then
            log_ok "健康检查通过: $HEALTH"
            return 0
        else
            log_warn "健康检查状态: $STATUS"
            return 1
        fi
    else
        log_fail "健康检查端点无响应"
        return 1
    fi
}

check_process() {
    log_info "检查进程状态..."
    if pgrep -f "uvicorn.*wanclaw.*im_adapter" > /dev/null 2>&1; then
        PID=$(pgrep -f "uvicorn.*wanclaw.*im_adapter" | head -1)
        CPU=$(ps -p "$PID" -o %cpu= 2>/dev/null || echo "0")
        MEM=$(ps -p "$PID" -o %mem= 2>/dev/null || echo "0")
        log_ok "进程运行中 (PID: $PID, CPU: ${CPU}%, MEM: ${MEM}%)"
        return 0
    else
        log_fail "WanClaw 进程未运行"
        return 1
    fi
}

check_port() {
    log_info "检查端口监听..."
    if command -v ss &>/dev/null; then
        if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
            log_ok "端口 $PORT 正在监听"
            return 0
        fi
    elif command -v netstat &>/dev/null; then
        if netstat -tlnp 2>/dev/null | grep -q ":$PORT "; then
            log_ok "端口 $PORT 正在监听"
            return 0
        fi
    fi
    if curl -sf -m 1 "http://$HOST:$PORT/" &>/dev/null; then
        log_ok "端口 $PORT 可访问"
        return 0
    fi
    log_fail "端口 $PORT 未监听"
    return 1
}

check_disk() {
    log_info "检查磁盘使用率..."
    DISK=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ "$DISK" -gt 90 ]]; then
        log_fail "磁盘使用率过高: ${DISK}%"
        return 1
    elif [[ "$DISK" -gt 80 ]]; then
        log_warn "磁盘使用率偏高: ${DISK}%"
        return 0
    else
        log_ok "磁盘使用率正常: ${DISK}%"
        return 0
    fi
}

check_memory() {
    log_info "检查内存使用..."
    MEM_TOTAL=$(free -m | awk 'NR==2 {print $2}')
    MEM_AVAIL=$(free -m | awk 'NR==2 {print $7}')
    if [[ "$MEM_TOTAL" -gt 0 ]]; then
        MEM_PCT=$(( (MEM_TOTAL - MEM_AVAIL) * 100 / MEM_TOTAL ))
        if [[ "$MEM_PCT" -gt 90 ]]; then
            log_fail "内存使用率过高: ${MEM_PCT}%"
            return 1
        elif [[ "$MEM_PCT" -gt 80 ]]; then
            log_warn "内存使用率偏高: ${MEM_PCT}%"
            return 0
        else
            log_ok "内存使用率正常: ${MEM_PCT}%"
            return 0
        fi
    fi
    return 0
}

check_log_size() {
    log_info "检查日志文件大小..."
    LOG_FILE="/var/log/wanclaw/wanclaw.log"
    if [[ -f "$LOG_FILE" ]]; then
        SIZE=$(du -h "$LOG_FILE" 2>/dev/null | awk '{print $1}')
        log_ok "日志文件大小: $SIZE"
    fi
}

check_pid_file() {
    log_info "检查 PID 文件..."
    PID_FILE="/var/run/wanclaw/wanclaw.pid"
    if [[ -f "$PID_FILE" ]]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            log_ok "PID 文件有效 (PID: $PID)"
        else
            log_warn "PID 文件存在但进程已不存在"
        fi
    fi
}

save_metrics() {
    mkdir -p "$LOG_DIR"
    TS=$(date +%s)
    echo "{\"ts\":$TS,\"errors\":$ERRORS,\"warnings\":$WARNINGS,\"port\":$PORT}" >> "$METRIC_FILE"
    tail -n 100 "$METRIC_FILE" > "$METRIC_FILE.tmp" && mv "$METRIC_FILE.tmp" "$METRIC_FILE"
}

auto_restart_service() {
    log_info "尝试自动重启服务..."
    if command -v systemctl &>/dev/null; then
        systemctl restart wanclaw
        sleep 3
        if systemctl is-active --quiet wanclaw; then
            log_ok "服务已自动重启"
            return 0
        else
            log_fail "自动重启失败"
            return 1
        fi
    fi
    return 1
}

print_summary() {
    echo ""
    if [[ "$ERRORS" -eq 0 ]] && [[ "$WARNINGS" -eq 0 ]]; then
        echo -e "${GREEN}✓ 所有检查通过${NC}"
        return 0
    elif [[ "$ERRORS" -eq 0 ]]; then
        echo -e "${YELLOW}⚠ $WARNINGS 个警告${NC}"
        return 0
    else
        echo -e "${RED}✗ $ERRORS 个错误，$WARNINGS 个警告${NC}"
        return 1
    fi
}

main() {
    echo "========================================"
    echo "  WanClaw 健康检查"
    echo "  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================"
    echo ""

    check_process
    check_port
    check_http
    check_health
    check_disk
    check_memory
    check_log_size
    check_pid_file

    save_metrics

    if [[ "$AUTO_RESTART" == "true" ]] && [[ "$ERRORS" -gt 0 ]]; then
        echo ""
        auto_restart_service
    fi

    echo ""
    print_summary
    exit $((ERRORS > 0 ? 1 : 0))
}

case "${1:-}" in
    --auto-restart) AUTO_RESTART=true; main ;;
    --check-only)   AUTO_RESTART=false; main ;;
    -h|--help)      echo "用法: $0 [--auto-restart]"; exit 0 ;;
    *)              AUTO_RESTART=false; main ;;
esac

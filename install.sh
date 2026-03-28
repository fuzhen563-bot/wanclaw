#!/bin/bash
# =============================================================================
#  WanClaw 一键安装脚本
#  版权所有 © 2025-2026 厦门亦梓科技有限公司
#  https://github.com/fuzhen563-bot/wanclaw
# =============================================================================
set -e

INSTALL_DIR="${INSTALL_DIR:-/opt/wanclaw}"
DATA_DIR="${DATA_DIR:-/var/lib/wanclaw}"
LOG_DIR="${LOG_DIR:-/var/log/wanclaw}"
RUN_DIR="${RUN_DIR:-/var/run/wanclaw}"
SERVICE_USER="${SERVICE_USER:-wanclaw}"
PORT="${PORT:-8000}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

confirm() {
    read -p "$1 [y/N]: " ans
    [[ "$ans" =~ ^[Yy]$ ]]
}

need_root() {
    if [[ $EUID -ne 0 ]]; then
        error "请使用 root 用户运行此脚本，或添加 sudo 前缀"
        exit 1
    fi
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS="$ID"
        VER="$VERSION_ID"
    elif [[ -f /etc/redhat-release ]]; then
        OS=$(awk '{print $1}' /etc/redhat-release | tr '[:upper:]' '[:lower:]')
    elif [[ -f /etc/debian_version ]]; then
        OS="debian"
    else
        OS="unknown"
    fi
    OS="${OS//\"/}"
}

check_python() {
    info "检查 Python 环境..."
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        error "Python 未安装，请先安装 Python 3.8+"
        exit 1
    fi
    VER=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    info "检测到 Python $VER"
    MAJ=${VER%%.*}
    MIN=${VER#*.}
    MIN=${MIN%%.*}
    if [[ "$MAJ" -lt 3 ]] || ([[ "$MAJ" -eq 3 ]] && [[ "$MIN" -lt 8 ]]); then
        error "需要 Python 3.8+，当前版本: $VER"
        exit 1
    fi
    success "Python 版本满足要求"
}

check_pip() {
    if ! $PYTHON_CMD -m pip --version &>/dev/null; then
        info "安装 pip..."
        $PYTHON_CMD -m ensurepip --upgrade 2>/dev/null || $PYTHON_CMD -m pip --version &>/dev/null || {
            if command -v apt-get &>/dev/null; then
                apt-get update -qq && apt-get install -y -qq python3-pip
            elif command -v yum &>/dev/null; then
                yum install -y python3-pip
            elif command -v dnf &>/dev/null; then
                dnf install -y python3-pip
            fi
        }
    fi
    success "pip 已就绪"
}

install_system_deps() {
    info "安装系统依赖..."
    if command -v apt-get &>/dev/null; then
        apt-get update -qq
        apt-get install -y -qq curl git ufw supervisor build-essential python3-dev
    elif command -v yum &>/dev/null; then
        yum install -y gcc python3-devel
        systemctl enable --now firewalld 2>/dev/null || true
    elif command -v dnf &>/dev/null; then
        dnf install -y gcc python3-devel
    fi
    success "系统依赖安装完成"
}

create_user() {
    if ! id "$SERVICE_USER" &>/dev/null 2>&1; then
        info "创建系统用户: $SERVICE_USER"
        useradd -r -m -d "$DATA_DIR" -s /bin/false "$SERVICE_USER" 2>/dev/null || useradd -r -m -d "$DATA_DIR" "$SERVICE_USER"
    fi
    success "用户 $SERVICE_USER 已就绪"
}

create_dirs() {
    info "创建目录结构..."
    for dir in "$INSTALL_DIR" "$DATA_DIR" "$LOG_DIR" "$RUN_DIR"; do
        mkdir -p "$dir"
        chown "$SERVICE_USER:$SERVICE_USER" "$dir"
    done
    mkdir -p "$DATA_DIR/workspace"
    mkdir -p "$DATA_DIR/plugins"
    mkdir -p "$DATA_DIR/skills"
    mkdir -p "$LOG_DIR"
    success "目录创建完成"
}

install_wanclaw() {
    info "安装 WanClaw 到 $INSTALL_DIR..."
    if [[ -d "$INSTALL_DIR/wanclaw" ]]; then
        warn "检测到已安装 WanClaw，将更新文件..."
    fi
    mkdir -p "$INSTALL_DIR"
    cp -r "$(dirname "$0")/wanclaw" "$INSTALL_DIR/"
    [[ -f "$(dirname "$0")/wanclaw.service" ]] && cp "$(dirname "$0")/wanclaw.service" "$INSTALL_DIR/"
    [[ -f "$(dirname "$0")/wanclaw-healthcheck.sh" ]] && cp "$(dirname "$0")/wanclaw-healthcheck.sh" "$INSTALL_DIR/"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    success "WanClaw 安装完成"
}

create_venv() {
    info "创建 Python 虚拟环境..."
    VENV_DIR="$INSTALL_DIR/.venv"
    if [[ ! -d "$VENV_DIR" ]] || [[ ! -f "$VENV_DIR/bin/activate" ]]; then
        $PYTHON_CMD -m venv "$VENV_DIR"
    fi
    success "虚拟环境已创建"
}

install_python_deps() {
    info "安装 Python 依赖..."
    PIP="$INSTALL_DIR/.venv/bin/pip"
    "$PIP" install --upgrade pip -q
    REQ="$INSTALL_DIR/wanclaw/requirements.txt"
    if [[ -f "$REQ" ]]; then
        "$PIP" install -r "$REQ" -q
    fi
    "$PIP" install fastapi uvicorn psutil pydantic pyyaml httpx websockets aiofiles structlog -q
    "$PIP" install python-telegram-bot python-dotenv Pillow openai volcengine -q 2>/dev/null || true
    success "Python 依赖安装完成"
}

install_systemd() {
    info "注册 systemd 服务..."
    UNIT_FILE="/etc/systemd/system/wanclaw.service"
    cat > "$UNIT_FILE" <<EOF
[Unit]
Description=WanClaw AI Assistant
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$INSTALL_DIR
ExecStart=$INSTALL_DIR/.venv/bin/python -m uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port $PORT
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=wanclaw
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF
    chmod 644 "$UNIT_FILE"
    systemctl daemon-reload
    success "systemd 服务已注册"
}

setup_firewall() {
    info "配置防火墙..."
    if command -v ufw &>/dev/null; then
        ufw allow "$PORT/tcp" comment 'WanClaw' 2>/dev/null || true
        ufw reload 2>/dev/null || true
    elif command -v firewall-cmd &>/dev/null; then
        firewall-cmd --permanent --add-port="$PORT/tcp" 2>/dev/null || true
        firewall-cmd --reload 2>/dev/null || true
    fi
    success "防火墙端口 $PORT 已开放"
}

start_service() {
    info "启动 WanClaw 服务..."
    systemctl enable wanclaw
    systemctl restart wanclaw
    sleep 2
    if systemctl is-active --quiet wanclaw; then
        success "WanClaw 服务已启动并设置开机自启"
    else
        error "服务启动失败，请检查日志: journalctl -u wanclaw -n 50"
        exit 1
    fi
}

print_next_steps() {
    IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${GREEN}WanClaw 安装完成!${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  首页:      ${BLUE}http://$IP:$PORT/${NC}"
    echo -e "  管理后台:  ${BLUE}http://$IP:$PORT/admin${NC}"
    echo -e "  API 文档:  ${BLUE}http://$IP:$PORT/docs${NC}"
    echo ""
    echo -e "  默认密码:   ${YELLOW}wanclaw${NC}"
    echo ""
    echo -e "  管理命令:"
    echo -e "    ${GREEN}systemctl start wanclaw${NC}      启动"
    echo -e "    ${GREEN}systemctl stop wanclaw${NC}       停止"
    echo -e "    ${GREEN}systemctl restart wanclaw${NC}    重启"
    echo -e "    ${GREEN}systemctl status wanclaw${NC}     状态"
    echo -e "    ${GREEN}journalctl -u wanclaw -f${NC}    实时日志"
    echo ""
    echo -e "  健康检查:"
    echo -e "    ${GREEN}$INSTALL_DIR/wanclaw-healthcheck.sh${NC}"
    echo ""
}

main() {
    need_root
    detect_os
    clear
    echo -e "${CYAN}"
    echo "  ██╗    ██╗███████╗██╗      ██████╗ ██████╗ ███╗   ███╗███████╗"
    echo "  ██║    ██║██╔════╝██║     ██╔════╝██╔═══██╗████╗ ████║██╔════╝"
    echo "  ██║ █╗ ██║█████╗  ██║     ██║     ██║   ██║██╔████╔██║█████╗  "
    echo "  ██║███╗██║██╔══╝  ██║     ██║     ██║   ██║██║╚██╔╝██║██╔══╝  "
    echo "  ╚███╔███╔╝███████╗███████╗╚██████╗╚██████╔╝██║ ╚═╝ ██║███████╗"
    echo "   ╚══╝╚══╝ ╚══════╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝"
    echo -e "${NC}"
    echo -e "  ${BLUE}WanClaw AI 个人助手 — 开源 · 自托管 · 多平台${NC}"
    echo ""
    echo -e "  安装目录: ${YELLOW}$INSTALL_DIR${NC}"
    echo -e "  运行用户: ${YELLOW}$SERVICE_USER${NC}"
    echo -e "  服务端口: ${YELLOW}$PORT${NC}"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    check_python
    check_pip
    install_system_deps
    create_user
    create_dirs
    install_wanclaw
    create_venv
    install_python_deps
    install_systemd
    setup_firewall
    start_service
    print_next_steps
}

main "$@"

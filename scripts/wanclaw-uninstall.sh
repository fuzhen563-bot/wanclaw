#!/bin/bash
# 版权所有 © 2025-2026 厦门万岳科技有限公司
SERVICE_NAME="wanclaw"
INSTALL_DIR="${INSTALL_DIR:-/opt/wanclaw}"
DATA_DIR="${DATA_DIR:-/var/lib/wanclaw}"
LOG_DIR="${LOG_DIR:-/var/log/wanclaw}"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}"
echo "  ████████╗██╗  ██╗███████╗"
echo "  ╚══██╔══╝██║  ██║██╔════╝"
echo "     ██║   ███████║█████╗  "
echo "     ██║   ██╔══██║██╔══╝  "
echo "     ██║   ██║  ██║███████╗"
echo "     ╚═╝   ╚═╝  ╚═╝╚══════╝"
echo -e "${NC}"
echo -e "  ${BLUE}WanClaw 卸载脚本${NC}"
echo ""

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[ERROR] 请使用 root 用户运行${NC}"
    exit 1
fi

echo -e "  警告: 此操作将:"
echo "  1. 停止并禁用 WanClaw 服务"
echo "  2. 删除安装目录: $INSTALL_DIR"
echo "  3. 删除数据目录: $DATA_DIR"
echo "  4. 删除日志目录: $LOG_DIR"
echo "  5. 删除 systemd 服务单元"
echo ""
read -p "  确认卸载? [y/N]: " ans
[[ "$ans" =~ ^[Yy]$ ]] || { echo "已取消"; exit 0; }

echo ""

echo "[*] 停止服务..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
systemctl disable "$SERVICE_NAME" 2>/dev/null || true
rm -f /etc/systemd/system/"$SERVICE_NAME.service"
systemctl daemon-reload
echo "[*] 删除服务文件..."
rm -f /etc/systemd/system/"$SERVICE_NAME.service"
echo "[*] 删除安装目录..."
rm -rf "$INSTALL_DIR"
echo "[*] 删除数据..."
rm -rf "$DATA_DIR"
echo "[*] 删除日志..."
rm -rf "$LOG_DIR"
rm -f /var/run/"$SERVICE_NAME".pid
rm -f /etc/supervisor/conf.d/"$SERVICE_NAME".conf 2>/dev/null || true
echo ""
echo -e "${GREEN}[*] WanClaw 已完全卸载${NC}"
echo ""
echo "  如需重新安装，请运行: ./install.sh"

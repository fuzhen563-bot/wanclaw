#!/bin/bash
#
# WanClaw 一键安装脚本 (支持 Linux/macOS/Windows WSL)
# 使用方法: curl -fsSL https://raw.githubusercontent.com/wanclaw/wanclaw/main/install.sh | bash
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if grep -qEi "Microsoft|WSL" /proc/version 2>/dev/null; then
            echo "wsl"
        else
            echo "linux"
        fi
    else
        echo "unknown"
    fi
}

# 检测包管理器
detect_pkg_manager() {
    local os=$1
    if [[ "$os" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            echo "brew"
        else
            echo "macports"
        fi
    elif [[ "$os" == "linux" ]] || [[ "$os" == "wsl" ]]; then
        if command -v apt-get &> /dev/null; then
            echo "apt"
        elif command -v yum &> /dev/null; then
            echo "yum"
        elif command -v dnf &> /dev/null; then
            echo "dnf"
        elif command -v pacman &> /dev/null; then
            echo "pacman"
        elif command -v zypper &> /dev/null; then
            echo "zypper"
        else
            echo "unknown"
        fi
    else
        echo "unknown"
    fi
}

# 安装 Python
install_python() {
    local os=$1
    local pkg=$2
    
    echo -e "${BLUE}安装 Python...${NC}"
    
    if [[ "$os" == "macos" ]]; then
        if command -v python3 &> /dev/null; then
            echo "Python 已安装: $(python3 --version)"
            return 0
        fi
        if [[ "$pkg" == "brew" ]]; then
            brew install python3
        else
            echo -e "${YELLOW}请从 https://www.python.org/downloads/mac-osx/ 下载 Python${NC}"
            return 1
        fi
    elif [[ "$os" == "linux" ]] || [[ "$os" == "wsl" ]]; then
        if command -v python3 &> /dev/null; then
            echo "Python 已安装: $(python3 --version)"
            return 0
        fi
        
        if [[ "$pkg" == "apt" ]]; then
            apt-get update && apt-get install -y python3 python3-pip python3-venv
        elif [[ "$pkg" == "yum" ]] || [[ "$pkg" == "dnf" ]]; then
            yum install -y python3 python3-pip || dnf install -y python3 python3-pip
        elif [[ "$pkg" == "pacman" ]]; then
            pacman -S --noconfirm python python-pip
        elif [[ "$pkg" == "zypper" ]]; then
            zypper install -y python3 python3-pip
        fi
    fi
    
    if command -v python3 &> /dev/null; then
        echo -e "${GREEN}Python 安装成功: $(python3 --version)${NC}"
    fi
}

# 安装系统依赖
install_dependencies() {
    local os=$1
    local pkg=$2
    
    echo -e "${BLUE}安装系统依赖...${NC}"
    
    if [[ "$os" == "macos" ]]; then
        if [[ "$pkg" == "brew" ]]; then
            brew install curl wget git sqlite3
        fi
    elif [[ "$os" == "linux" ]] || [[ "$os" == "wsl" ]]; then
        if [[ "$pkg" == "apt" ]]; then
            apt-get update && apt-get install -y curl wget git sqlite3 libsqlite3-dev
        elif [[ "$pkg" == "yum" ]] || [[ "$pkg" == "dnf" ]]; then
            yum install -y curl wget git sqlite sqlite-devel || dnf install -y curl wget git sqlite sqlite-devel
        elif [[ "$pkg" == "pacman" ]]; then
            pacman -S --noconfirm curl wget git sqlite
        elif [[ "$pkg" == "zypper" ]]; then
            zypper install -y curl wget git sqlite3
        fi
    fi
    
    echo -e "${GREEN}系统依赖安装完成${NC}"
}

# 安装 Python 依赖
install_python_deps() {
    echo -e "${BLUE}安装 Python 依赖...${NC}"
    
    cd /tmp
    
    if [[ ! -f "requirements.txt" ]]; then
        echo -e "${YELLOW}下载 requirements.txt...${NC}"
        curl -fsSL -o requirements.txt "https://raw.githubusercontent.com/wanclaw/wanclaw/main/requirements.txt" 2>/dev/null || \
        echo -e "${YELLOW}使用内置 requirements.txt${NC}"
    fi
    
    pip3 install --upgrade pip
    
    # 核心依赖
    pip3 install fastapi uvicorn httpx pyyaml python-multipart
    
    # 数据库
    pip3 install sqlalchemy aiosqlite
    
    # 工具
    pip3 install python-jose passlib python-dotenv
    
    # 可选依赖
    pip3 install psutil pydantic 2>/dev/null || true
    
    echo -e "${GREEN}Python 依赖安装完成${NC}"
}

# 下载 WanClaw
download_wanclaw() {
    local install_dir=$1
    
    echo -e "${BLUE}下载 WanClaw...${NC}"
    
    if [[ -d "$install_dir/wanclaw" ]]; then
        echo -e "${YELLOW}WanClaw 已存在，更新中...${NC}"
        cd "$install_dir/wanclaw"
        git pull 2>/dev/null || true
    else
        mkdir -p "$install_dir"
        cd "$install_dir"
        
        # 尝试从 GitHub 下载
        if command -v git &> /dev/null; then
            git clone https://github.com/fuzhen563-bot/wanclaw.git wanclaw || true
        fi
        
        # 如果 Git 失败，尝试下载压缩包
        if [[ ! -d "$install_dir/wanclaw" ]]; then
            echo -e "${YELLOW}下载 release 包...${NC}"
            curl -fsSL -o wanclaw.tar.gz "https://github.com/fuzhen563-bot/wanclaw/releases/latest/download/wanclaw-latest.tar.gz" 2>/dev/null || \
            echo -e "${YELLOW}无法下载，请手动解压到 $install_dir${NC}"
        fi
    fi
    
    if [[ -d "$install_dir/wanclaw" ]]; then
        echo -e "${GREEN}WanClaw 下载完成${NC}"
    fi
}

# 配置 WanClaw
configure_wanclaw() {
    local install_dir=$1
    
    echo -e "${BLUE}配置 WanClaw...${NC}"
    
    cd "$install_dir/wanclaw"
    
    # 创建配置目录
    mkdir -p ~/.wanclaw
    
    # 复制配置示例
    if [[ -f "wanclaw/backend/im_adapter/config/config.yaml" ]]; then
        if [[ ! -f "~/.wanclaw/config.yaml" ]]; then
            cp wanclaw/backend/im_adapter/config/config.yaml ~/.wanclaw/config.yaml
            echo -e "${GREEN}配置文件已创建: ~/.wanclaw/config.yaml${NC}"
        fi
    fi
    
    echo -e "${GREEN}配置完成${NC}"
}

# 创建启动脚本
create_systemd_service() {
    local install_dir=$1
    
    if [[ "$EUID" == 0 ]]; then
        echo -e "${BLUE}创建 systemd 服务...${NC}"
        
        cat > /etc/systemd/system/wanclaw.service << EOF
[Unit]
Description=WanClaw AI Assistant
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$install_dir/wanclaw
ExecStart=/usr/bin/python3 -m wanclaw.backend.im_adapter.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        systemctl daemon-reload
        systemctl enable wanclaw
        
        echo -e "${GREEN}systemd 服务已创建${NC}"
    fi
}

# 创建便捷脚本
create_scripts() {
    local install_dir=$1
    local bin_dir="/usr/local/bin"
    
    echo -e "${BLUE}创建快捷命令...${NC}"
    
    # 启动脚本
    cat > "$install_dir/wanclaw/wanclaw-start.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || true
python3 -m wanclaw.backend.im_adapter.main
EOF
    chmod +x "$install_dir/wanclaw/wanclaw-start.sh"
    
    # 停止脚本
    cat > "$install_dir/wanclaw/wanclaw-stop.sh" << 'EOF'
#!/bin/bash
pkill -f "wanclaw.backend.im_adapter" || echo "WanClaw 未运行"
EOF
    chmod +x "$install_dir/wanclaw/wanclaw-stop.sh"
    
    # 状态脚本
    cat > "$install_dir/wanclaw/wanclaw-status.sh" << 'EOF'
#!/bin/bash
if pgrep -f "wanclaw.backend.im_adapter" > /dev/null; then
    echo "WanClaw 运行中"
else
    echo "WanClaw 未运行"
fi
EOF
    chmod +x "$install_dir/wanclaw/wanclaw-status.sh"
    
    # 创建全局命令链接
    if [[ -w "$bin_dir" ]]; then
        ln -sf "$install_dir/wanclaw/wanclaw-start.sh" "$bin_dir/wanclaw"
        ln -sf "$install_dir/wanclaw/wanclaw-status.sh" "$bin_dir/wanclaw-status"
    fi
    
    echo -e "${GREEN}快捷命令已创建: wanclaw, wanclaw-status${NC}"
}

# 显示安装完成信息
show_completion() {
    local install_dir=$1
    local port=${2:-8000}
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  WanClaw 安装完成!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "  管理后台: ${BLUE}http://localhost:$port/admin${NC}"
    echo -e "  默认密码: ${YELLOW}wanclaw${NC}"
    echo -e "  API 文档: ${BLUE}http://localhost:$port/docs${NC}"
    echo ""
    echo "  启动命令:"
    echo "    $ cd $install_dir/wanclaw"
    echo "    $ python3 -m wanclaw.backend.im_adapter.main"
    echo ""
    echo "  或使用快捷命令:"
    echo "    $ wanclaw (后台运行)"
    echo "    $ wanclaw-status (查看状态)"
    echo ""
    echo -e "${YELLOW}首次使用请在管理后台配置 AI API Key${NC}"
    echo ""
}

# 主函数
main() {
    local install_dir="${1:-$HOME/wanclaw}"
    local port=8000
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  WanClaw AI 助手一键安装脚本${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    # 检测环境
    local os=$(detect_os)
    local pkg=$(detect_pkg_manager $os)
    
    echo -e "检测到系统: ${GREEN}$os${NC}"
    echo -e "包管理器: ${GREEN}$pkg${NC}"
    echo ""
    
    # 安装步骤
    install_dependencies $os $pkg
    install_python $os $pkg
    install_python_deps
    download_wanclaw "$install_dir"
    configure_wanclaw "$install_dir"
    create_scripts "$install_dir"
    
    # 启动服务
    echo ""
    echo -e "${BLUE}启动 WanClaw...${NC}"
    cd "$install_dir/wanclaw"
    
    if [[ "$os" == "macos" ]]; then
        nohup python3 -m wanclaw.backend.im_adapter.main --port $port > wanclaw.log 2>&1 &
    else
        nohup python3 -m wanclaw.backend.im_adapter.main --port $port > wanclaw.log 2>&1 &
    fi
    
    sleep 3
    
    # 检查是否启动成功
    if curl -s "http://localhost:$port/docs" &> /dev/null; then
        show_completion "$install_dir" $port
    else
        echo -e "${YELLOW}服务启动中，请稍后访问 http://localhost:$port${NC}"
        echo -e "日志: $install_dir/wanclaw/wanclaw.log"
    fi
}

# Windows PowerShell 安装脚本
windows_install() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  WanClaw Windows 安装指南${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "推荐使用 Docker 安装 (最简单的跨平台方式):"
    echo ""
    echo "1. 安装 Docker Desktop:"
    echo "   https://www.docker.com/products/docker-desktop"
    echo ""
    echo "2. 创建 docker-compose.yml:"
    echo ""
    cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  wanclaw:
    image: wanclaw/wanclaw:latest
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config
    environment:
      - WANCLAW_PASSWORD=wanclaw
    restart: unless-stopped
EOF
    echo ""
    echo "3. 启动:"
    echo "   docker-compose up -d"
    echo ""
    echo "或使用 WSL (Linux 子系统):"
    echo "   请运行上面的 Linux 安装脚本"
}

# macOS Homebrew 安装脚本
macos_install() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  WanClaw macOS 安装指南${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    # 检查 Homebrew
    if ! command -v brew &> /dev/null; then
        echo "安装 Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    # 安装依赖
    brew install python3 git sqlite3
    
    # 克隆项目
    cd ~
    git clone https://github.com/fuzhen563-bot/wanclaw.git wanclaw
    cd wanclaw
    
    # 安装 Python 依赖
    pip3 install -r requirements.txt 2>/dev/null || true
    
    # 启动
    echo ""
    echo -e "${GREEN}安装完成!${NC}"
    echo "启动: cd ~/wanclaw && python3 -m wanclaw.backend.im_adapter.main"
    echo "访问: http://localhost:8000/admin"
}

# 显示使用帮助
usage() {
    cat << EOF
用法: $0 [选项]

选项:
    -h, --help              显示帮助
    -d, --dir <目录>        安装目录 (默认: ~/wanclaw)
    -p, --port <端口>      服务端口 (默认: 8000)
    --win                   Windows 安装指南
    --mac                   macOS 安装指南
    --linux                 Linux 安装脚本

示例:
    $0 -d /opt/wanclaw -p 8080
    $0 --mac
    $0 --win
EOF
}

# 解析参数
case "${1:-}" in
    -h|--help)
        usage
        exit 0
        ;;
    --win)
        windows_install
        exit 0
        ;;
    --mac)
        macos_install
        exit 0
        ;;
    --linux)
        shift
        main "$@"
        ;;
    *)
        # 如果没有参数，交互式选择
        if [[ -z "$1" ]]; then
            local os=$(detect_os)
            if [[ "$os" == "macos" ]]; then
                macos_install
            else
                main "$@"
            fi
        else
            main "$@"
        fi
        ;;
esac

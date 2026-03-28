#!/bin/bash
# WanClaw IM适配器启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "命令 $1 未找到，请先安装"
        return 1
    fi
    return 0
}

# 检查Python环境
check_python() {
    log_info "检查Python环境..."
    if check_command "python3"; then
        PYTHON_CMD="python3"
    elif check_command "python"; then
        PYTHON_CMD="python"
    else
        log_error "未找到Python，请先安装Python 3.8+"
        exit 1
    fi
    
    # 检查Python版本
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    log_info "Python版本: $PYTHON_VERSION"
    
    # 解析版本号
    IFS='.' read -r MAJOR MINOR PATCH <<< "$PYTHON_VERSION"
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
        log_error "需要Python 3.8+，当前版本: $PYTHON_VERSION"
        exit 1
    fi
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖包..."
    
    # 检查pip
    if ! check_command "pip3" && ! check_command "pip"; then
        log_error "未找到pip，请先安装pip"
        exit 1
    fi
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        log_warning "虚拟环境不存在，将创建新的虚拟环境"
        $PYTHON_CMD -m venv venv
    fi
    
    # 激活虚拟环境
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
    else
        log_error "无法激活虚拟环境"
        exit 1
    fi
    
    # 安装依赖
    log_info "安装依赖包..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        log_success "依赖包安装完成"
    else
        log_error "依赖包安装失败"
        exit 1
    fi
}

# 检查配置文件
check_config() {
    log_info "检查配置文件..."
    
    CONFIG_FILE="config/config.yaml"
    EXAMPLE_FILE="config/example_config.yaml"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log_warning "配置文件 $CONFIG_FILE 不存在"
        
        if [ -f "$EXAMPLE_FILE" ]; then
            log_info "从示例文件创建配置文件..."
            cp "$EXAMPLE_FILE" "$CONFIG_FILE"
            log_success "配置文件已创建，请编辑 $CONFIG_FILE 配置平台参数"
        else
            log_error "示例配置文件也不存在"
            exit 1
        fi
    else
        log_success "配置文件已存在"
    fi
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    mkdir -p logs
    mkdir -p data
    mkdir -p config
    
    log_success "目录创建完成"
}

# 启动服务
start_service() {
    log_info "启动IM适配器服务..."
    
    MODE=${1:-"api"}  # 默认启动API模式
    
    case $MODE in
        "api")
            log_info "启动API服务模式..."
            uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000 --reload &
            API_PID=$!
            echo $API_PID > api.pid
            log_success "API服务已启动 (PID: $API_PID)"
            log_info "API文档: http://localhost:8000/docs"
            ;;
        "cli")
            log_info "启动CLI模式..."
            PYTHONPATH=/app $PYTHON_CMD -m wanclaw.backend.im_adapter.main &
            CLI_PID=$!
            echo $CLI_PID > cli.pid
            log_success "CLI服务已启动 (PID: $CLI_PID)"
            ;;
        "all")
            log_info "启动所有服务..."
            PYTHONPATH=/app $PYTHON_CMD -m wanclaw.backend.im_adapter.main &
            CLI_PID=$!
            echo $CLI_PID > cli.pid
            
            sleep 2  # 等待CLI服务初始化
            
            uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000 &
            API_PID=$!
            echo $API_PID > api.pid
            
            log_success "所有服务已启动"
            log_info "CLI服务 PID: $CLI_PID"
            log_info "API服务 PID: $API_PID"
            log_info "API文档: http://localhost:8000/docs"
            ;;
        *)
            log_error "未知模式: $MODE"
            log_info "可用模式: api, cli, all"
            exit 1
            ;;
    esac
}

# 停止服务
stop_service() {
    log_info "停止服务..."
    
    if [ -f "api.pid" ]; then
        API_PID=$(cat api.pid)
        if kill -0 $API_PID 2>/dev/null; then
            kill $API_PID
            log_success "API服务已停止 (PID: $API_PID)"
        fi
        rm -f api.pid
    fi
    
    if [ -f "cli.pid" ]; then
        CLI_PID=$(cat cli.pid)
        if kill -0 $CLI_PID 2>/dev/null; then
            kill $CLI_PID
            log_success "CLI服务已停止 (PID: $CLI_PID)"
        fi
        rm -f cli.pid
    fi
}

# 重启服务
restart_service() {
    log_info "重启服务..."
    stop_service
    sleep 2
    start_service "$1"
}

# 查看状态
status_service() {
    log_info "服务状态..."
    
    RUNNING=false
    
    if [ -f "api.pid" ]; then
        API_PID=$(cat api.pid)
        if kill -0 $API_PID 2>/dev/null; then
            log_success "API服务运行中 (PID: $API_PID)"
            RUNNING=true
        else
            log_warning "API服务PID文件存在但进程未运行"
            rm -f api.pid
        fi
    else
        log_info "API服务未运行"
    fi
    
    if [ -f "cli.pid" ]; then
        CLI_PID=$(cat cli.pid)
        if kill -0 $CLI_PID 2>/dev/null; then
            log_success "CLI服务运行中 (PID: $CLI_PID)"
            RUNNING=true
        else
            log_warning "CLI服务PID文件存在但进程未运行"
            rm -f cli.pid
        fi
    else
        log_info "CLI服务未运行"
    fi
    
    if [ "$RUNNING" = false ]; then
        log_info "所有服务均未运行"
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    if [ -f "api.pid" ]; then
        API_PID=$(cat api.pid)
        if kill -0 $API_PID 2>/dev/null; then
            log_info "检查API服务健康..."
            curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || log_warning "API服务健康检查失败"
        fi
    fi
}

# 测试功能
test_service() {
    log_info "测试服务功能..."
    
    # 检查Python环境
    if ! check_command "python3"; then
        PYTHON_CMD="python"
    else
        PYTHON_CMD="python3"
    fi
    
    # 测试配置文件
    $PYTHON_CMD -c "import yaml; yaml.safe_load(open('config/config.yaml'))" && \
        log_success "配置文件语法正确"
    
    # 测试导入模块
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PYTHONPATH="$SCRIPT_DIR/../../../" $PYTHON_CMD -c "from wanclaw.backend.im_adapter.gateway import get_gateway; print('模块导入成功')" && \
        log_success "模块导入成功"
    
    # 测试健康检查
    if [ -f "api.pid" ]; then
        API_PID=$(cat api.pid)
        if kill -0 $API_PID 2>/dev/null; then
            log_info "测试API接口..."
            curl -s http://localhost:8000/health > /dev/null && \
                log_success "API接口测试成功"
        fi
    fi
}

# 清理
cleanup() {
    log_info "清理..."
    
    # 停止服务
    stop_service
    
    # 清理日志文件（保留最近7天）
    find logs -name "*.log" -mtime +7 -delete 2>/dev/null || true
    
    # 清理PID文件
    rm -f *.pid 2>/dev/null || true
    
    log_success "清理完成"
}

# 显示帮助
show_help() {
    echo -e "${BLUE}WanClaw IM适配器管理脚本${NC}"
    echo ""
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "命令:"
    echo "  start [mode]     启动服务 (mode: api, cli, all, 默认: api)"
    echo "  stop             停止服务"
    echo "  restart [mode]   重启服务"
    echo "  status           查看服务状态"
    echo "  health           健康检查"
    echo "  test             测试服务功能"
    echo "  setup            初始设置（检查环境、安装依赖）"
    echo "  cleanup          清理"
    echo "  help             显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 setup         初始设置"
    echo "  $0 start api     启动API服务"
    echo "  $0 start all     启动所有服务"
    echo "  $0 status        查看状态"
    echo "  $0 health        健康检查"
    echo ""
}

# 主函数
main() {
    COMMAND=${1:-"help"}
    OPTION=${2:-""}
    
    case $COMMAND in
        "start")
            check_python
            check_config
            create_directories
            check_dependencies
            start_service "$OPTION"
            ;;
        "stop")
            stop_service
            ;;
        "restart")
            restart_service "$OPTION"
            ;;
        "status")
            status_service
            ;;
        "health")
            health_check
            ;;
        "test")
            test_service
            ;;
        "setup")
            check_python
            create_directories
            check_config
            check_dependencies
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            log_error "未知命令: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
#!/bin/bash
# WanClaw 一键部署脚本

set -e  # 出错时退出

echo "=========================================="
echo "      WanClaw SME AI Assistant"
echo "            部署脚本"
echo "=========================================="
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    echo "参考: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 Docker Compose 是否安装 (支持两种格式: docker-compose 和 docker compose)
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    echo "参考: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker 和 Docker Compose 已安装"

# 创建必要目录
echo "📁 创建数据目录..."
mkdir -p data/{logs,backups,config}
mkdir -p logs

# 检查配置文件
echo "🔧 检查配置文件..."
if [ ! -f "wanclaw/backend/im_adapter/config/config.yaml" ]; then
    echo "⚠️  配置文件不存在，正在创建示例配置..."
    if [ -f "wanclaw/backend/im_adapter/config/example_config.yaml" ]; then
        cp wanclaw/backend/im_adapter/config/example_config.yaml wanclaw/backend/im_adapter/config/config.yaml
        echo "✅ 已创建示例配置文件，请根据需要修改:"
        echo "   wanclaw/backend/im_adapter/config/config.yaml"
    else
        echo "❌ 示例配置文件不存在，请确保项目文件完整"
        exit 1
    fi
else
    echo "✅ 配置文件已存在"
fi

# 构建和启动服务
echo "🚀 启动 WanClaw 服务..."
echo ""
echo "选项:"
echo "1. 开发模式 (使用 docker-compose.dev.yml)"
echo "2. 生产模式 (使用 docker-compose.yml)"
echo ""
read -p "请选择部署模式 (1/2): " mode

# 检测 docker compose 命令格式
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ 未找到 Docker Compose 命令"
    exit 1
fi

case $mode in
    1)
        echo "🔧 启动开发模式..."
        if [ -f "docker-compose.dev.yml" ]; then
            $DOCKER_COMPOSE -f docker-compose.dev.yml up -d --build
        else
            echo "❌ 开发配置文件不存在"
            echo "正在使用生产配置..."
            $DOCKER_COMPOSE up -d --build
        fi
        ;;
    2)
        echo "🏭 启动生产模式..."
        $DOCKER_COMPOSE up -d --build
        ;;
    *)
        echo "❌ 无效选项，使用默认生产模式"
        $DOCKER_COMPOSE up -d --build
        ;;
esac

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "📊 检查服务状态..."
if $DOCKER_COMPOSE ps | grep -q "Up"; then
    echo "✅ WanClaw 服务已启动!"
    
    # 显示服务信息
    echo ""
    echo "=========================================="
    echo "           部署完成!"
    echo "=========================================="
    echo ""
    echo "📋 服务信息:"
    echo "   - Web API: http://localhost:8000"
    echo "   - API 文档: http://localhost:8000/docs"
    echo "   - 健康检查: http://localhost:8000/health"
    echo ""
    echo "📁 数据目录:"
    echo "   - 日志: ./logs/"
    echo "   - 数据: ./data/"
    echo "   - 配置: ./wanclaw/backend/im_adapter/config/"
    echo ""
    echo "🔧 管理命令:"
    echo "   - 查看日志: $DOCKER_COMPOSE logs -f"
    echo "   - 停止服务: $DOCKER_COMPOSE down"
    echo "   - 重启服务: $DOCKER_COMPOSE restart"
    echo "   - 更新服务: $DOCKER_COMPOSE pull && $DOCKER_COMPOSE up -d"
    echo ""
    echo "⚠️  下一步:"
    echo "   1. 修改配置文件以配置IM平台"
    echo "   2. 重启服务使配置生效: $DOCKER_COMPOSE restart"
    echo "   3. 访问API文档测试接口"
    echo ""
    echo "📚 文档: 查看 README.md 获取详细使用说明"
    
else
    echo "❌ 服务启动失败，请检查日志:"
    $DOCKER_COMPOSE logs
    exit 1
fi

echo ""
echo "✨ WanClaw 部署完成! ✨"
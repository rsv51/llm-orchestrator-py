#!/bin/bash
# LLM Orchestrator 启动脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 和 Docker Compose
check_dependencies() {
    print_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装,请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装,请先安装 Docker Compose"
        exit 1
    fi
    
    print_info "依赖检查通过"
}

# 检查并创建 .env 文件
check_env_file() {
    print_info "检查环境配置..."
    
    if [ ! -f .env ]; then
        print_warn ".env 文件不存在,从 .env.example 创建..."
        cp .env.example .env
        print_info ".env 文件已创建,请编辑配置后重新启动"
        print_warn "建议修改以下配置:"
        print_warn "  - AUTH_TOKEN: API 认证令牌"
        print_warn "  - ADMIN_KEY: 管理员密钥"
        print_warn "  - 数据库和 Redis 配置"
        exit 0
    fi
    
    print_info "环境配置文件存在"
}

# 创建必要的目录
create_directories() {
    print_info "创建必要的目录..."
    
    mkdir -p data logs
    
    print_info "目录创建完成"
}

# 启动服务
start_services() {
    print_info "启动服务..."
    
    # 构建镜像
    print_info "构建 Docker 镜像..."
    docker-compose build
    
    # 启动服务
    print_info "启动容器..."
    docker-compose up -d
    
    # 等待服务启动
    print_info "等待服务启动..."
    sleep 5
    
    # 检查服务状态
    if docker-compose ps | grep -q "Up"; then
        print_info "服务启动成功!"
    else
        print_error "服务启动失败,请检查日志"
        docker-compose logs
        exit 1
    fi
}

# 显示服务信息
show_info() {
    print_info "=========================================="
    print_info "LLM Orchestrator 已启动!"
    print_info "=========================================="
    echo ""
    print_info "服务地址:"
    print_info "  - API: http://localhost:8000"
    print_info "  - 文档: http://localhost:8000/docs"
    print_info "  - 健康检查: http://localhost:8000/health"
    echo ""
    print_info "常用命令:"
    print_info "  - 查看日志: docker-compose logs -f"
    print_info "  - 停止服务: docker-compose stop"
    print_info "  - 重启服务: docker-compose restart"
    print_info "  - 停止并删除: docker-compose down"
    echo ""
    print_warn "首次使用请先配置提供商:"
    print_warn "  1. 访问 http://localhost:8000/docs"
    print_warn "  2. 使用 /admin/providers 端点添加提供商"
    print_warn "  3. 使用管理员密钥进行认证"
    echo ""
}

# 主函数
main() {
    echo "=========================================="
    echo "  LLM Orchestrator 启动脚本"
    echo "=========================================="
    echo ""
    
    # 切换到项目根目录
    cd "$(dirname "$0")/.."
    
    # 执行检查和启动
    check_dependencies
    check_env_file
    create_directories
    start_services
    show_info
}

# 执行主函数
main "$@"
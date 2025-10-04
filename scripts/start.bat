@echo off
REM LLM Orchestrator Windows 启动脚本

setlocal enabledelayedexpansion

REM 设置颜色代码 (Windows 10+)
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "NC=[0m"

echo ==========================================
echo   LLM Orchestrator 启动脚本 (Windows)
echo ==========================================
echo.

REM 切换到项目根目录
cd /d "%~dp0\.."

REM 检查 Docker
call :print_info "检查 Docker..."
docker --version >nul 2>&1
if errorlevel 1 (
    call :print_error "Docker 未安装或未启动"
    echo 请先安装 Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM 检查 Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    call :print_error "Docker Compose 未安装"
    pause
    exit /b 1
)

call :print_info "依赖检查通过"
echo.

REM 检查 .env 文件
call :print_info "检查环境配置..."
if not exist .env (
    call :print_warn ".env 文件不存在,从 .env.example 创建..."
    copy .env.example .env
    call :print_info ".env 文件已创建"
    echo.
    call :print_warn "请编辑 .env 文件配置以下项:"
    echo   - AUTH_TOKEN: API 认证令牌
    echo   - ADMIN_KEY: 管理员密钥
    echo   - 数据库和 Redis 配置
    echo.
    pause
    exit /b 0
)

call :print_info "环境配置文件存在"
echo.

REM 创建必要的目录
call :print_info "创建必要的目录..."
if not exist data mkdir data
if not exist logs mkdir logs
call :print_info "目录创建完成"
echo.

REM 构建镜像
call :print_info "构建 Docker 镜像..."
docker-compose build
if errorlevel 1 (
    call :print_error "镜像构建失败"
    pause
    exit /b 1
)

REM 启动服务
call :print_info "启动容器..."
docker-compose up -d
if errorlevel 1 (
    call :print_error "服务启动失败"
    echo 查看日志: docker-compose logs
    pause
    exit /b 1
)

REM 等待服务启动
call :print_info "等待服务启动..."
timeout /t 5 /nobreak >nul

REM 检查服务状态
docker-compose ps | findstr "Up" >nul
if errorlevel 1 (
    call :print_error "服务启动失败,请检查日志"
    docker-compose logs
    pause
    exit /b 1
)

REM 显示服务信息
echo.
call :print_info "=========================================="
call :print_info "LLM Orchestrator 已启动!"
call :print_info "=========================================="
echo.
call :print_info "服务地址:"
echo   - API: http://localhost:8000
echo   - 文档: http://localhost:8000/docs
echo   - 健康检查: http://localhost:8000/health
echo.
call :print_info "常用命令:"
echo   - 查看日志: docker-compose logs -f
echo   - 停止服务: docker-compose stop
echo   - 重启服务: docker-compose restart
echo   - 停止并删除: docker-compose down
echo.
call :print_warn "首次使用请先配置提供商:"
echo   1. 访问 http://localhost:8000/docs
echo   2. 使用 /admin/providers 端点添加提供商
echo   3. 使用管理员密钥进行认证
echo.

REM 询问是否打开浏览器
set /p OPEN_BROWSER="是否打开浏览器查看文档? (Y/N): "
if /i "%OPEN_BROWSER%"=="Y" (
    start http://localhost:8000/docs
)

echo.
pause
exit /b 0

REM 函数定义
:print_info
echo %GREEN%[INFO]%NC% %~1
goto :eof

:print_warn
echo %YELLOW%[WARN]%NC% %~1
goto :eof

:print_error
echo %RED%[ERROR]%NC% %~1
goto :eof
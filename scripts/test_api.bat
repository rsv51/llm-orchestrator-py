@echo off
REM API 测试工具启动脚本 (Windows)

echo ================================
echo LLM Orchestrator API 测试工具
echo ================================
echo.

REM 激活虚拟环境
if exist ..\venv\Scripts\activate.bat (
    call ..\venv\Scripts\activate.bat
    echo 已激活虚拟环境
) else (
    echo 警告: 未找到虚拟环境，使用系统 Python
)

echo.
echo 运行测试...
echo.

python test_api.py %*

pause
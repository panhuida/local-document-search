@echo off
REM 快速启动脚本 - Windows 批处理版本
REM 用于快速检查环境并启动本地文档搜索系统

setlocal enabledelayedexpansion

REM Set PYTHONPATH to include src directory
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"

echo.
echo ========================================
echo   本地文档搜索系统 - 快速启动
echo ========================================
echo.

REM 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo [1/4] 检查环境...
python scripts/check_environment.py --fix
if errorlevel 1 (
    echo.
    echo [错误] 环境检查未通过，请根据上述提示修复问题
    echo.
    echo 常见问题：
    echo   - PostgreSQL 服务未启动：以管理员身份运行此脚本
    echo   - 缺少配置文件：已自动创建 .env，请编辑后重新运行
    echo   - 缺少 Python 包：请运行 uv sync 或 pip install .
    echo.
    pause
    exit /b 1
)

echo.
echo [2/4] 检查 PostgreSQL 服务...
python scripts/start_services.py --check
if errorlevel 1 (
    echo.
    echo [警告] PostgreSQL 服务检查失败
    choice /C YN /M "是否尝试启动服务（需要管理员权限）"
    if !errorlevel! equ 1 (
        echo 正在尝试启动服务...
        python scripts/start_services.py
    )
)

echo.
echo [3/4] 最后检查...
python scripts/check_environment.py
if errorlevel 1 (
    echo.
    echo [错误] 环境仍有问题，无法启动应用
    pause
    exit /b 1
)

echo.
echo [4/4] 启动应用...
echo.
echo ========================================
echo   系统正在启动，请稍候...
echo   访问地址: http://127.0.0.1:5000
echo   按 Ctrl+C 停止服务
echo ========================================
echo.

python -m local_document_search.app

pause

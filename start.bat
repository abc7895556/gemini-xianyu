@echo off
chcp 65001 >nul
echo ========================================
echo   闲鱼商品智能分析系统 - 启动脚本
echo ========================================
echo.

cd /d %~dp0

echo [1/3] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
echo ✅ Python环境正常

echo.
echo [2/3] 检查依赖包...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  正在升级pip...
    python -m pip install --upgrade pip
    echo.
    echo ⚠️  正在安装依赖包...
    echo 这可能需要几分钟，请耐心等待...
    python -m pip install -r requirements.txt --upgrade
    if errorlevel 1 (
        echo.
        echo ❌ 依赖安装失败
        echo.
        echo 💡 尝试手动安装：
        echo    pip install --upgrade pip
        echo    pip install flask flask-cors playwright google-genai requests
        echo    playwright install chromium
        echo.
        pause
        exit /b 1
    )
)
echo ✅ 依赖包检查完成

echo.
echo [2.5/3] 检查Playwright浏览器...
python -c "from playwright.sync_api import sync_playwright" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Playwright未安装，跳过浏览器检查
) else (
    python -c "from playwright.sync_api import sync_playwright; p = sync_playwright(); p.start(); p.stop()" >nul 2>&1
    if errorlevel 1 (
        echo ⚠️  正在安装Playwright浏览器（这可能需要几分钟）...
        playwright install chromium
    )
)

echo.
echo [3/3] 启动服务器...
echo.
echo 🌐 服务器地址: http://localhost:5000
echo 💡 请在浏览器中打开上述地址
echo.
echo 按 Ctrl+C 停止服务器
echo.

cd backend
python app.py

pause


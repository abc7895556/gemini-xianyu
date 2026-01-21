@echo off
chcp 65001 >nul
echo ========================================
echo   依赖安装脚本（使用国内镜像源）
echo ========================================
echo.

cd /d %~dp0

echo [1/4] 检查Python环境...
python --version
if errorlevel 1 (
    echo ❌ 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
echo ✅ Python环境正常
echo.

echo [2/4] 升级pip（使用清华镜像）...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.

echo [3/4] 安装Python依赖包（使用清华镜像）...
echo 正在安装：flask, flask-cors, playwright, google-genai, requests
echo.
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple flask flask-cors playwright google-genai requests --upgrade
if errorlevel 1 (
    echo.
    echo ❌ 依赖安装失败
    echo.
    echo 💡 如果仍然失败，请检查：
    echo    1. 网络连接是否正常
    echo    2. Python版本是否为3.8+
    echo    3. 是否有足够的磁盘空间
    echo.
    pause
    exit /b 1
)
echo ✅ Python依赖包安装完成
echo.

echo [4/4] 安装Playwright浏览器...
echo 这可能需要几分钟，请耐心等待...
playwright install chromium
if errorlevel 1 (
    echo ⚠️  Playwright浏览器安装失败，但可以稍后手动安装
    echo    运行命令: playwright install chromium
) else (
    echo ✅ Playwright浏览器安装完成
)
echo.

echo ========================================
echo   安装完成！
echo ========================================
echo.
echo 现在可以运行 start.bat 启动服务器
echo.
pause



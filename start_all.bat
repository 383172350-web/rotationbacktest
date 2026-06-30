@echo off
chcp 65001 >nul
:: ============================================================
:: 统一启动脚本：启动4个系统
:: ============================================================

cd /d "%~dp0"

echo ============================================================
echo   统一回测系统启动器
echo ============================================================
echo.
echo 选择要启动的系统：
echo   [1] 旧版 Flask API  (端口 8001)
echo   [2] 旧版策略生成器 (端口 8503)
echo   [3] 新版策略生成器 (端口 8502)
echo   [4] 全品类资产轮动机器人 (独立脚本)
echo   [5] 启动全部 (4个窗口)
echo   [0] 退出
echo.

set /p choice="请输入数字 (0-5): "

if "%choice%"=="1" goto start_flask
if "%choice%"=="2" goto start_legacy
if "%choice%"=="3" goto start_rotation
if "%choice%"=="4" goto start_bot
if "%choice%"=="5" goto start_all
if "%choice%"=="0" goto end

echo 无效输入，退出...
goto end

:start_flask
echo.
echo [启动] 旧版 Flask API (端口 8001)...
cd "%~dp0\backtest_cloud"
start "Flask 8001" cmd /c "C:\Users\38317\AppData\Local\Programs\Python\Python313\python.exe -m flask run --host=0.0.0.0 --port=8001"
echo ✓ 已启动 http://localhost:8001
goto end

:start_legacy
echo.
echo [启动] 旧版策略生成器 (端口 8503)...
cd "%~dp0\backtest_cloud"
start "Streamlit 8503" cmd /c "C:\Users\38317\AppData\Local\Programs\Python\Python313\python.exe -m streamlit run streamlit_app.py --server.port 8503 --server.headless true"
echo ✓ 已启动 http://localhost:8503
goto end

:start_rotation
echo.
echo [启动] 新版策略生成器 (端口 8502)...
cd "%~dp0\rotation-web"
start "Streamlit 8502" cmd /c "C:\Users\38317\AppData\Local\Programs\Python\Python313\python.exe -m streamlit run streamlit_app.py --server.port 8502 --server.headless true"
echo ✓ 已启动 http://localhost:8502
goto end

:start_bot
echo.
echo [启动] 全品类资产轮动机器人...
cd "%~dp0"
start "Rotation Bot" cmd /c "C:\Users\38317\AppData\Local\Programs\Python\Python313\python.exe 全品类资产轮动双模式.py"
echo ✓ 已启动
goto end

:start_all
echo.
echo [启动] 全部系统...
cd "%~dp0\backtest_cloud"
start "Flask 8001" cmd /c "C:\Users\38317\AppData\Local\Programs\Python\Python313\python.exe -m flask run --host=0.0.0.0 --port=8001"
start "Streamlit 8503" cmd /c "C:\Users\38317\AppData\Local\Programs\Python\Python313\python.exe -m streamlit run streamlit_app.py --server.port 8503 --server.headless true"
cd "%~dp0\rotation-web"
start "Streamlit 8502" cmd /c "C:\Users\38317\AppData\Local\Programs\Python\Python313\python.exe -m streamlit run streamlit_app.py --server.port 8502 --server.headless true"
cd "%~dp0"
start "Rotation Bot" cmd /c "C:\Users\38317\AppData\Local\Programs\Python\Python313\python.exe 全品类资产轮动双模式.py"
echo.
echo ✓ Flask API:     http://localhost:8001
echo ✓ 旧版策略生成器: http://localhost:8503
echo ✓ 新版策略生成器: http://localhost:8502
echo ✓ 全品类机器人:   已启动
goto end

:end
echo.
pause

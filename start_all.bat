@echo off
:: ============================================================
:: Unified Backtest System Launcher
:: ============================================================

cd /d "%~dp0"

:: Python path
set PYTHON=C:\Users\38317\AppData\Local\Programs\Python\Python313\python.exe

echo ============================================================
echo   Unified Backtest System Launcher
echo ============================================================
echo.
echo Select system to start:
echo   [1] Flask API        (port 8001)
echo   [2] Legacy Generator (port 8503)
echo   [3] Modern Generator (port 8502)
echo   [4] Start ALL        (3 windows)
echo   [0] Exit
echo.

set /p choice="Enter number (0-4): "

if "%choice%"=="1" goto start_flask
if "%choice%"=="2" goto start_legacy
if "%choice%"=="3" goto start_rotation
if "%choice%"=="4" goto start_all
if "%choice%"=="0" goto end

echo Invalid input, exiting...
goto end

:start_flask
echo.
echo [Starting] Flask API (port 8001)...
cd /d "%~dp0\backtest_cloud"
start "Flask 8001" cmd /k %PYTHON% -m flask run --app app.py --host=0.0.0.0 --port=8001
echo Started http://localhost:8001
goto end

:start_legacy
echo.
echo [Starting] Legacy Strategy Generator (port 8503)...
cd /d "%~dp0\backtest_cloud"
start "Streamlit 8503" cmd /k %PYTHON% -m streamlit run streamlit_app.py --server.port 8503 --server.headless true
echo Started http://localhost:8503
goto end

:start_rotation
echo.
echo [Starting] Modern Strategy Generator (port 8502)...
cd /d "%~dp0\rotation-web"
start "Streamlit 8502" cmd /k %PYTHON% -m streamlit run streamlit_app.py --server.port 8502 --server.headless true
echo Started http://localhost:8502
goto end

:start_all
echo.
echo [Starting] ALL systems...
cd /d "%~dp0\backtest_cloud"
start "Flask 8001" cmd /k %PYTHON% -m flask run --app app.py --host=0.0.0.0 --port=8001
start "Streamlit 8503" cmd /k %PYTHON% -m streamlit run streamlit_app.py --server.port 8503 --server.headless true
cd /d "%~dp0\rotation-web"
start "Streamlit 8502" cmd /k %PYTHON% -m streamlit run streamlit_app.py --server.port 8502 --server.headless true
echo.
echo ==========================================
echo   All services started
echo ==========================================
echo   Flask API:      http://localhost:8001
echo   Legacy Gen:     http://localhost:8503
echo   Modern Gen:     http://localhost:8502
echo ==========================================
goto end

:end
echo.
pause

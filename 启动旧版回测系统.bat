@echo off
chcp 65001 >nul

cd /d "C:\Users\Administrator\Documents\kimi\workspace\rotation-web"

echo =========================================
echo  启动轮动策略回测系统
echo =========================================
echo.

"C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe" -m streamlit run streamlit_app.py --server.port 8501

echo.
pause

@echo off
cd /d "C:\Users\Administrator\Documents\kimi\workspace\rotation-web"
echo 正在安装依赖 (streamlit, plotly)...
python -m pip install streamlit plotly pandas numpy
echo.
echo 安装完成，按回车键启动服务...
pause
streamlit run streamlit_app.py --server.port 8502
pause

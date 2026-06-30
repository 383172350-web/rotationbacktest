@echo off
cd /d "C:\Users\Administrator\Documents\kimi\workspace\rotation-web"
echo 正在启动 Streamlit 回测系统...
echo 端口: 8502
echo 数据目录: D:\qmt_data\ETF\1d
echo.
echo 浏览器访问: http://localhost:8502
echo.
pause
echo 正在启动...
streamlit run streamlit_app.py --server.port 8502
pause

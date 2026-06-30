# -*- coding: utf-8 -*-
"""
入口文件：旧版策略生成器
适配 Streamlit Cloud 部署
"""
import sys
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(base_dir, 'backtest_cloud')
sys.path.insert(0, app_dir)

# 直接执行 streamlit_app.py，确保 __name__ == '__main__'
__file__ = os.path.join(app_dir, 'streamlit_app.py')
__name__ = '__main__'
with open(__file__, 'r', encoding='utf-8') as f:
    exec(compile(f.read(), __file__, 'exec'))

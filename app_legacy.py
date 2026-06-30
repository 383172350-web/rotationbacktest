# -*- coding: utf-8 -*-
"""
入口文件：旧版策略生成器
适配 Streamlit Cloud 部署
"""
import sys
import os

# 添加 backtest_cloud 到 Python 路径
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, 'backtest_cloud'))

# 执行旧版策略生成器
import streamlit_app

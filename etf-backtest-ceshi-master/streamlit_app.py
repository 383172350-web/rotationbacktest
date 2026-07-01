# -*- coding: utf-8 -*-
"""
ETF数据获取测试 — 极简版
验证：本地pkl + akshare 两个数据源
"""
import streamlit as st
import pandas as pd
from data_fetcher import fetch_data, LOCAL_PKL_DIR
import os

st.set_page_config(page_title="ETF数据获取测试", layout="wide")
st.title("🧪 ETF数据获取测试")

# 显示环境信息
st.sidebar.markdown("**环境信息**")
st.sidebar.write(f"本地pkl目录: `{LOCAL_PKL_DIR}`")
st.sidebar.write(f"目录存在: `{os.path.exists(LOCAL_PKL_DIR)}`")
if os.path.exists(LOCAL_PKL_DIR):
    files = [f for f in os.listdir(LOCAL_PKL_DIR) if f.endswith("_1d.pkl")]
    st.sidebar.write(f"pkl文件数: `{len(files)}`")

st.sidebar.markdown("---")
st.sidebar.markdown("**测试说明**")
st.sidebar.write("1. 输入ETF代码（如 sh510300）")
st.sidebar.write("2. 选择数据源")
st.sidebar.write("3. 点击获取数据")
st.sidebar.write("4. 查看结果")

# 输入区域
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    code = st.text_input("ETF代码", value="sh510300", help="格式：sh510300 或 sz159915")
with col2:
    source = st.selectbox("数据源", ["auto", "local", "eastmoney", "tencent", "findb"], help="auto=先本地后东方财富后腾讯后findb")
with col3:
    st.write("")
    st.write("")
    go = st.button("📥 获取数据", type="primary")

# 日期范围
c1, c2 = st.columns(2)
with c1:
    start_date = st.date_input("开始日期", value=pd.to_datetime("2024-01-01")).strftime("%Y-%m-%d")
with c2:
    end_date = st.date_input("结束日期", value=pd.to_datetime("2024-06-30")).strftime("%Y-%m-%d")

if go:
    with st.spinner("获取数据中..."):
        result = fetch_data(code, start_date, end_date, source)
    
    if result["error"]:
        st.error(f"❌ 获取失败: {result['error']}")
    else:
        st.success(f"✅ 成功！数据源: `{result['source']}` | 行数: `{result['rows']}`")
        
        df = result["df"]
        st.write(f"日期范围: `{df['date'].iloc[0]}` ~ `{df['date'].iloc[-1]}`")
        st.write(f"列名: `{list(df.columns)}`")
        st.dataframe(df.head(10), use_container_width=True)
        
        # 显示统计
        st.markdown("---")
        st.markdown("**数据统计**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("收盘价最新", f"{df['close'].iloc[-1]:.3f}")
        c2.metric("收盘价最高", f"{df['close'].max():.3f}")
        c3.metric("收盘价最低", f"{df['close'].min():.3f}")
        c4.metric("平均成交量", f"{df['volume'].mean():.0f}")

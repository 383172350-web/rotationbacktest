# -*- coding: utf-8 -*-
"""
入口文件：全品类资产轮动机器人
适配 Streamlit Cloud 部署
"""
import sys
import os

# 添加当前目录到路径
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

# 导入全品类资产轮动核心函数
import 全品类资产轮动双模式 as bot

# 导入 Streamlit
import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="全品类资产轮动机器人")

st.title("全品类资产轮动机器人")
st.markdown("基于DIFv动量的全自动交易机器人")

# 参数配置
with st.sidebar:
    st.header("策略参数")
    initial_capital = st.number_input("初始资金", value=1000000, step=100000)
    real_capital = st.number_input("实盘资金", value=200000, step=10000)
    start_date = st.text_input("回测起始日期", value="2020-03-12")
    
    st.divider()
    st.markdown("**标的池**")
    st.code("""
159949.SZ 创业板50
159980.SZ 有色ETF
159981.SZ 能源化工
159985.SZ 豆粕ETF
510300.SH 沪深300
513030.SH 德国ETF
513050.SH 中概互联
513100.SH 纳指ETF
513500.SH 标普500
513520.SH 日经ETF
512100.SH 中证1000
501018.SH 南方原油
518880.SH 黄金ETF
    """)

# 主界面
col1, col2 = st.columns(2)

with col1:
    st.subheader("回测结果")
    if st.button("🚀 运行回测", use_container_width=True):
        with st.spinner("正在运行回测..."):
            try:
                # 运行回测
                bot.INITIAL_CAPITAL = initial_capital
                bot.REAL_CAPITAL = real_capital
                bot.STRATEGY_START = start_date
                
                pkl_dir = bot._detect_pkl_dir()
                data_df = bot._load_data_from_pkl(pkl_dir)
                
                if data_df is not None:
                    data_dict = bot._build_data_dict(data_df)
                    data_dict, common_dates = bot._align_dates(data_dict)
                    stock_tickers = [t for t in data_dict.keys() if t != bot.BOND_TICKER]
                    all_tickers = list(data_dict.keys())
                    signals = bot._calc_signals(data_dict, all_tickers)
                    
                    nav_df, trade_df, hold_df, holdings, cash = bot._run_backtest(
                        signals, stock_tickers, bot.BOND_TICKER, all_tickers, common_dates,
                        initial_capital, start_date=start_date
                    )
                    
                    perf = bot._compute_performance(nav_df, trade_df, initial_capital)
                    
                    # 显示关键指标
                    st.success("回测完成!")
                    
                    metrics = st.columns(4)
                    with metrics[0]:
                        st.metric("总收益率", f"{perf['total_return']:.2%}")
                    with metrics[1]:
                        st.metric("年化收益率", f"{perf['annual_return']:.2%}")
                    with metrics[2]:
                        st.metric("最大回撤", f"{perf['max_drawdown']:.2%}")
                    with metrics[3]:
                        st.metric("交易次数", len(trade_df))
                    
                    # 显示交易记录
                    st.subheader("交易记录")
                    st.dataframe(trade_df, use_container_width=True)
                    
                else:
                    st.error("数据加载失败，请检查 pkl 数据目录")
            except Exception as e:
                st.error(f"运行失败: {e}")

with col2:
    st.subheader("交易计划")
    if st.button("📋 生成交易计划", use_container_width=True):
        with st.spinner("正在生成交易计划..."):
            try:
                pkl_dir = bot._detect_pkl_dir()
                data_df = bot._load_data_from_pkl(pkl_dir)
                
                if data_df is not None:
                    data_dict = bot._build_data_dict(data_df)
                    data_dict, common_dates = bot._align_dates(data_dict)
                    stock_tickers = [t for t in data_dict.keys() if t != bot.BOND_TICKER]
                    all_tickers = list(data_dict.keys())
                    signals = bot._calc_signals(data_dict, all_tickers)
                    
                    nav_df, trade_df, hold_df, holdings, cash = bot._run_backtest(
                        signals, stock_tickers, bot.BOND_TICKER, all_tickers, common_dates,
                        initial_capital, start_date=start_date
                    )
                    
                    last_date = common_dates[-1]
                    next_date = last_date + pd.Timedelta(days=1)
                    while next_date.weekday() >= 5:
                        next_date += pd.Timedelta(days=1)
                    
                    rows = bot._generate_trade_plan(
                        signals, holdings, cash, stock_tickers, last_date, next_date, 
                        real_capital, common_dates
                    )
                    
                    if rows:
                        df = pd.DataFrame(rows)
                        st.dataframe(df, use_container_width=True)
                        
                        # 下载CSV
                        csv = df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📥 下载交易计划CSV",
                            data=csv,
                            file_name='trade_plan.csv',
                            mime='text/csv',
                        )
                    else:
                        st.info("无交易计划")
                else:
                    st.error("数据加载失败")
            except Exception as e:
                st.error(f"生成失败: {e}")

st.divider()
st.caption("全品类DIFv轮动策略 | 数据来源: 本地pkl / AKShare")

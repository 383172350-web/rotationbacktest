# -*- coding: utf-8 -*-
"""
ETF轮动策略回测系统 —— Streamlit 主界面
==========================================
五大模块：股票池选择、轮动排序规格、买入条件、卖出条件、基础配置
支持新版表达式解析引擎
"""
from __future__ import print_function, division

import io
import os
import json
import datetime
import traceback
import re

import streamlit as st
import pandas as pd
import numpy as np

from engine import (
    scan_pkl_dir,
    build_data_dict,
    ETF_NAMES,
    calc_all_indicators,
    compute_indicators_for_df,
    run_backtest,
    compute_performance,
    plot_nav_curve,
    plot_drawdown,
    compute_yearly_returns,
)
from engine.expression_parser import evaluate_condition, evaluate_score

# ============================================================
#  页面配置
# ============================================================
st.set_page_config(layout="wide", page_title="ETF轮动策略回测系统")

# ============================================================
#  缓存：扫描 pkl 目录
# ============================================================
@st.cache_data
def cached_scan_pkl_dir():
    return scan_pkl_dir()


# ============================================================
#  系统指标库（新版表达式引擎）
# ============================================================
INDICATORS = {
    "MA(n)": {"name": "均线MA", "params": [{"name": "n", "label": "周期", "default": 20, "min": 1, "max": 250}]},
    "EMA(n)": {"name": "指数均线EMA", "params": [{"name": "n", "label": "周期", "default": 12, "min": 1, "max": 250}]},
    "RSI(n)": {"name": "RSI", "params": [{"name": "n", "label": "周期", "default": 14, "min": 1, "max": 100}]},
    "MACD_DIF(fast,slow,signal)": {"name": "MACD快线", "params": [
        {"name": "fast", "label": "快线", "default": 12, "min": 1, "max": 50},
        {"name": "slow", "label": "慢线", "default": 26, "min": 1, "max": 50},
        {"name": "signal", "label": "信号线", "default": 9, "min": 1, "max": 50}]},
    "MACD_DEA(fast,slow,signal)": {"name": "MACD慢线", "params": [
        {"name": "fast", "label": "快线", "default": 12, "min": 1, "max": 50},
        {"name": "slow", "label": "慢线", "default": 26, "min": 1, "max": 50},
        {"name": "signal", "label": "信号线", "default": 9, "min": 1, "max": 50}]},
    "MACD_HIST(fast,slow,signal)": {"name": "MACD柱", "params": [
        {"name": "fast", "label": "快线", "default": 12, "min": 1, "max": 50},
        {"name": "slow", "label": "慢线", "default": 26, "min": 1, "max": 50},
        {"name": "signal", "label": "信号线", "default": 9, "min": 1, "max": 50}]},
    "ATR(n)": {"name": "ATR波动", "params": [{"name": "n", "label": "周期", "default": 26, "min": 1, "max": 100}]},
    "BOLL(n)": {"name": "布林带中轨", "params": [{"name": "n", "label": "周期", "default": 20, "min": 1, "max": 100}]},
    "BOLL_upper(n,std)": {"name": "布林上轨", "params": [
        {"name": "n", "label": "周期", "default": 20, "min": 1, "max": 100},
        {"name": "std", "label": "标准差倍数", "default": 2, "min": 1, "max": 5}]},
    "BOLL_lower(n,std)": {"name": "布林下轨", "params": [
        {"name": "n", "label": "周期", "default": 20, "min": 1, "max": 100},
        {"name": "std", "label": "标准差倍数", "default": 2, "min": 1, "max": 5}]},
    "KDJ_K(n,m1,m2)": {"name": "KDJ-K", "params": [
        {"name": "n", "label": "N日", "default": 9, "min": 1, "max": 50},
        {"name": "m1", "label": "M1", "default": 3, "min": 1, "max": 20},
        {"name": "m2", "label": "M2", "default": 3, "min": 1, "max": 20}]},
    "KDJ_D(n,m1,m2)": {"name": "KDJ-D", "params": [
        {"name": "n", "label": "N日", "default": 9, "min": 1, "max": 50},
        {"name": "m1", "label": "M1", "default": 3, "min": 1, "max": 20},
        {"name": "m2", "label": "M2", "default": 3, "min": 1, "max": 20}]},
    "KDJ_J(n,m1,m2)": {"name": "KDJ-J", "params": [
        {"name": "n", "label": "N日", "default": 9, "min": 1, "max": 50},
        {"name": "m1", "label": "M1", "default": 3, "min": 1, "max": 20},
        {"name": "m2", "label": "M2", "default": 3, "min": 1, "max": 20}]},
    "returns(n)": {"name": "N日涨幅", "params": [{"name": "n", "label": "天数", "default": 20, "min": 1, "max": 250}]},
    "BIAS(n)": {"name": "乖离率", "params": [{"name": "n", "label": "周期", "default": 20, "min": 1, "max": 250}]},
    "quality_score(n)": {"name": "质量得分", "params": [{"name": "n", "label": "周期", "default": 20, "min": 1, "max": 250}]},
    "volatility(n)": {"name": "波动率", "params": [{"name": "n", "label": "周期", "default": 20, "min": 1, "max": 250}]},
    "gain_percentile(n)": {"name": "涨幅百分位", "params": [{"name": "n", "label": "周期", "default": 250, "min": 1, "max": 500}]},
    "volume_percentile(n)": {"name": "成交量百分位", "params": [{"name": "n", "label": "周期", "default": 250, "min": 1, "max": 500}]},
    "RSRS_slope(n)": {"name": "RSRS斜率", "params": [{"name": "n", "label": "斜率周期", "default": 18, "min": 1, "max": 100}]},
    "RSRS_zscore(n,period)": {"name": "RSRS标准分", "params": [
        {"name": "n", "label": "斜率周期", "default": 18, "min": 1, "max": 100},
        {"name": "period", "label": "标准化窗口", "default": 600, "min": 100, "max": 1000}]},
    "RSRS_right_zscore(n,period)": {"name": "RSRS右偏标准分", "params": [
        {"name": "n", "label": "斜率周期", "default": 18, "min": 1, "max": 100},
        {"name": "period", "label": "标准化窗口", "default": 600, "min": 100, "max": 1000}]},
    "penalty(days,threshold,penalty_value)": {"name": "惩罚项（跌幅扣分）", "params": [
        {"name": "days", "label": "检查天数", "default": 3, "min": 1, "max": 30},
        {"name": "threshold", "label": "跌幅阈值", "default": -0.05, "min": -0.5, "max": 0.0, "step": 0.01},
        {"name": "penalty_value", "label": "惩罚分数", "default": -300, "min": -1000, "max": 0, "step": 10}]},
}

BASIC_FIELDS = {
    "close": "收盘价", "open": "开盘价", "high": "最高价", "low": "最低价",
    "volume": "成交量", "amount": "成交额",
}

SPECIAL_VARS = {
    "rank": "当前排名", "profit": "持仓收益率", "hold_days": "持仓天数", "buy_price": "买入价格",
}


# ============================================================
#  预设策略定义（新版表达式格式）
# ============================================================
PRESET_STRATEGIES = {
    "自定义": {},
    "全品类DIFv轮动": {
        "strategy_type": "difv",
        "stock_tickers": [
            "159949.SZ", "159980.SZ", "159981.SZ", "159985.SZ",
            "510300.SH", "513030.SH", "513050.SH", "513100.SH",
            "513500.SH", "513520.SH", "512100.SH", "501018.SH",
            "518880.SH",
        ],
        "bond_ticker": "511880.SH",
        "start_date": "2020-03-12",
        "sort": {
            "rank_formula": "(MACD_DIF(12,26,9) / ATR(26)) * 100",
            "rank_direction": "desc",
        },
        "buy": {
            "buy_match_mode": "all",
            "buy_rules": [
                {"condition": "close > MA(5)", "description": "close>MA5"},
                {"condition": "close > MA(20)", "description": "close>MA20"},
                {"condition": "MA(10) > MA(20)", "description": "MA10>MA20"},
                {"condition": "MA(5) > MA(10)", "description": "MA5>MA10"},
                {"condition": "(MACD_DIF(12,26,9) / ATR(26)) * 100 < 120", "description": "DIFv<120"},
            ],
        },
        "sell": {
            "sell_match_mode": "any",
            "sell_rules": [
                {"condition": "rank > 6", "description": "rank>6"},
                {"condition": "returns(1) < -0.03", "description": "日跌幅>3%"},
                {"condition": "returns(20) > 0.25", "description": "20日涨幅>25%"},
            ],
            "stop_loss": 0.0,
            "sell_if_buy_fails": False,
        },
        "position": {
            "mode": "equal_weight",
            "max_holdings": 5,
            "position_pct": 0.20,
            "rebalance_days": 2,
            "new_rank_limit": 0,
        },
    },
    "五斗米动量轮动": {
        "strategy_type": "wdm",
        "stock_tickers": [
            "510050.SH", "510300.SH", "588000.SH", "159915.SZ", "562500.SH",
        ],
        "start_date": "2020-03-01",
        "sort": {
            "rank_formula": "close / MA(12) * 100 - 100",
            "rank_direction": "desc",
        },
        "buy": {
            "buy_match_mode": "all",
            "buy_rules": [
                {"condition": "close > BOLL_upper(17,2)", "description": "above_band"},
                {"condition": "close / MA(12) * 100 - 100 > 0", "description": "wdm_momentum>0"},
            ],
        },
        "sell": {
            "sell_match_mode": "any",
            "sell_rules": [
                {"condition": "close / MA(12) * 100 - 100 < 0", "description": "wdm_momentum<0"},
            ],
            "stop_loss": 0.0,
            "sell_if_buy_fails": True,
        },
        "position": {
            "mode": "single",
            "max_holdings": 1,
            "position_pct": 1.0,
            "rebalance_days": 1,
            "new_rank_limit": 0,
        },
    },
    "科技成长DIFv轮动": {
        "strategy_type": "difv",
        "stock_tickers": [
            "159509.SZ", "515070.SH", "515880.SH", "515000.SH", "159611.SZ",
            "515990.SH", "512480.SH", "159766.SH", "588250.SH", "159869.SZ",
            "159551.SZ", "512660.SH", "159967.SZ", "515120.SH", "159898.SZ",
            "159380.SZ", "159871.SZ", "515790.SH", "159806.SZ", "159995.SZ",
            "159566.SZ", "515400.SH", "560913.SH", "560200.SH", "159786.SZ",
            "159732.SZ",
        ],
        "start_date": "2024-02-08",
        "sort": {
            "rank_formula": "(MACD_DIF(12,26,9) / ATR(26)) * 100",
            "rank_direction": "desc",
        },
        "buy": {
            "buy_match_mode": "all",
            "buy_rules": [
                {"condition": "(MACD_DIF(12,26,9) / ATR(26)) * 100 > 0", "description": "DIFv>0"},
                {"condition": "(MACD_DIF(12,26,9) / ATR(26)) * 100 < 120", "description": "DIFv<120"},
                {"condition": "close > MA(5)", "description": "close>MA5"},
            ],
        },
        "sell": {
            "sell_match_mode": "any",
            "sell_rules": [
                {"condition": "(MACD_DIF(12,26,9) / ATR(26)) * 100 < 0", "description": "DIFv<0"},
            ],
            "stop_loss": 0.0,
            "sell_if_buy_fails": False,
        },
        "position": {
            "mode": "incremental",
            "max_holdings": 10,
            "position_pct": 0.10,
            "rebalance_days": 1,
            "new_rank_limit": 0,
        },
    },
    "DIFv动量轮动": {
        "strategy_type": "difv",
        "stock_tickers": [
            "512690.SH", "515880.SH", "159605.SZ", "513100.SH", "513500.SH",
            "513520.SH", "513030.SH", "518880.SH",
        ],
        "start_date": "2020-03-12",
        "sort": {
            "rank_formula": "(MACD_DIF(12,26,9) / ATR(26)) * 100",
            "rank_direction": "desc",
        },
        "buy": {
            "buy_match_mode": "all",
            "buy_rules": [
                {"condition": "(MACD_DIF(12,26,9) / ATR(26)) * 100 > 0", "description": "DIFv>0"},
                {"condition": "(MACD_DIF(12,26,9) / ATR(26)) * 100 < 120", "description": "DIFv<120"},
                {"condition": "close > MA(5)", "description": "close>MA5"},
            ],
        },
        "sell": {
            "sell_match_mode": "any",
            "sell_rules": [
                {"condition": "(MACD_DIF(12,26,9) / ATR(26)) * 100 < 0", "description": "DIFv<0"},
            ],
            "stop_loss": 0.0,
            "sell_if_buy_fails": False,
        },
        "position": {
            "mode": "incremental",
            "max_holdings": 5,
            "position_pct": 0.20,
            "rebalance_days": 1,
            "new_rank_limit": 0,
        },
    },
    "RSRS动量轮动": {
        "strategy_type": "rsrs",
        "stock_tickers": [
            "518880.SH", "513100.SH", "588200.SH", "159915.SZ", "511090.SH",
        ],
        "start_date": "2020-03-01",
        "sort": {
            "rank_formula": "rsrs_momentum_score(20) + penalty(3, -0.05, -8)",
            "rank_direction": "desc",
        },
        "buy": {
            "buy_match_mode": "any",
            "buy_rules": [
                {
                    "condition": "momentum_score > 0 AND momentum_score < 7 AND volume_ratio <= 2 AND (rsrs_pass AND rsrs_strength > 0.15 OR rsrs_pass AND rsrs_strength > 0.03 AND close > MA(5) OR close >= MA(10))",
                    "description": "原始app.py RSRS动量轮动"
                },
            ],
        },
        "sell": {
            "sell_match_mode": "any",
            "sell_rules": [],
            "stop_loss": 0.03,
            "sell_if_buy_fails": True,
        },
        "position": {
            "mode": "single",
            "max_holdings": 1,
            "position_pct": 1.0,
            "rebalance_days": 1,
            "new_rank_limit": 0,
        },
    },
    "精选LOF轮动": {
        "strategy_type": "lof",
        "stock_tickers": [
            "163402.SZ", "163417.SZ", "161903.SZ", "162703.SZ", "161005.SZ",
        ],
        "start_date": "2020-03-01",
        "sort": {
            "rank_formula": "std_momentum",
            "rank_direction": "desc",
        },
        "buy": {
            "buy_match_mode": "all",
            "buy_rules": [
                {"condition": "return_20 > 0.05", "description": "20日涨幅>5%"},
                {"condition": "sort_value > 0", "description": "sort_value>0"},
            ],
        },
        "sell": {
            "sell_match_mode": "any",
            "sell_rules": [
                {"condition": "return_20 < 0", "description": "20日涨幅<0"},
                {"condition": "rank > 1", "description": "rank>1"},
            ],
            "stop_loss": 0.0,
            "sell_if_buy_fails": True,
        },
        "position": {
            "mode": "single",
            "max_holdings": 1,
            "position_pct": 1.0,
            "rebalance_days": 1,
            "new_rank_limit": 0,
        },
    },
}

# 预设组合（股票池快捷按钮）
PRESET_POOLS = {
    "全品类(14只)": [
        "159949.SZ", "159980.SZ", "159981.SZ", "159985.SZ",
        "510300.SH", "513030.SH", "513050.SH", "513100.SH",
        "513500.SH", "513520.SH", "512100.SH", "501018.SH",
        "518880.SH", "511880.SH",
    ],
    "科技成长(26只)": [
        "159509.SZ", "515070.SH", "515880.SH", "515000.SH", "159611.SZ",
        "515990.SH", "512480.SH", "159766.SH", "588250.SH", "159869.SZ",
        "159551.SZ", "512660.SH", "159967.SZ", "515120.SH", "159898.SZ",
        "159380.SZ", "159871.SZ", "515790.SH", "159806.SZ", "159995.SZ",
        "159566.SZ", "515400.SH", "560913.SH", "560200.SH", "159786.SZ",
        "159732.SZ",
    ],
    "五斗米(5只)": [
        "510050.SH", "510300.SH", "588000.SH", "159915.SZ", "562500.SH",
    ],
    "RSRS(5只)": [
        "518880.SH", "513100.SH", "588000.SH", "159915.SZ", "511260.SH",
    ],
    "LOF(5只)": [
        "163402.SZ", "163417.SZ", "161903.SZ", "162703.SZ", "161005.SZ",
    ],
}

# ETF分组定义（用于分组选择）
ETF_GROUPS = {
    "全品类(13只)": ["159949.SZ","159980.SZ","159981.SZ","159985.SZ","510300.SH","513030.SH","513050.SH","513100.SH","513500.SH","513520.SH","512100.SH","501018.SH","518880.SH"],
    "科技成长(26只)": ["159509.SZ","515070.SH","515880.SH","515000.SH","159611.SZ","515990.SH","512480.SH","159766.SH","588250.SH","159869.SZ","159551.SZ","512660.SH","159967.SZ","515120.SH","159898.SZ","159380.SZ","159871.SZ","515790.SH","159806.SZ","159995.SZ","159566.SZ","515400.SH","560913.SH","560200.SH","159786.SZ","159732.SZ"],
    "五斗米(5只)": ["510050.SH","510300.SH","588000.SH","159915.SZ","562500.SH"],
    "RSRS(5只)": ["518880.SH","513100.SH","588000.SH","159915.SZ","511260.SH"],
    "LOF(5只)": ["163402.SZ","163417.SZ","161903.SZ","162703.SZ","161005.SZ"],
}


# ============================================================
#  策略持久化
# ============================================================
SAVED_STRATEGIES_FILE = os.path.join(os.path.dirname(__file__), 'saved_strategies.json')


def _is_old_format(config):
    """检测策略配置是否为旧版格式"""
    if not isinstance(config, dict):
        return False
    sort_cfg = config.get("sort", {})
    buy_cfg = config.get("buy", {})
    sell_cfg = config.get("sell", {})
    if "indicator" in sort_cfg or "mode" in buy_cfg or "mode" in sell_cfg:
        return True
    return False


def _migrate_old_strategy(config):
    """将旧版策略配置自动转换为新版表达式格式"""
    migrated = dict(config)

    # 迁移排序配置
    sort_cfg = config.get("sort", {})
    if "indicator" in sort_cfg:
        indicator = sort_cfg.get("indicator", "return_n")
        direction = sort_cfg.get("direction", "desc")
        if indicator == "return_n":
            window = sort_cfg.get("window", 21)
            rank_formula = f"returns({window})"
        elif indicator == "momentum_score":
            window = sort_cfg.get("window", 20)
            rank_formula = f"returns({window})"
        elif indicator == "difv":
            ema_short = sort_cfg.get("ema_short", 12)
            ema_long = sort_cfg.get("ema_long", 26)
            atr_period = sort_cfg.get("atr_period", 26)
            rank_formula = f"(MACD_DIF({ema_short},{ema_long},9) / ATR({atr_period})) * 100"
        elif indicator == "logbias":
            ema_period = sort_cfg.get("ema_period", 20)
            multiplier = sort_cfg.get("multiplier", 100)
            rank_formula = f"(close - EMA({ema_period})) / EMA({ema_period}) * {multiplier}"
        elif indicator == "std_momentum":
            window = sort_cfg.get("window", 20)
            rank_formula = f"returns({window})"
        elif indicator == "wdm_momentum":
            shift = sort_cfg.get("shift", 12)
            rank_formula = f"close / MA({shift}) * 100 - 100"
        else:
            rank_formula = indicator
        # 处理大跌惩罚
        drop_penalty = sort_cfg.get("drop_penalty", False)
        if drop_penalty:
            threshold = sort_cfg.get("drop_threshold", 0.05)
            penalty_expr = f"penalty(3, {-threshold}, -300)"
            if rank_formula.strip():
                rank_formula = f"{rank_formula} + {penalty_expr}"
            else:
                rank_formula = penalty_expr
        migrated["sort"] = {
            "rank_formula": rank_formula,
            "rank_direction": direction,
        }

    # 迁移买入配置
    buy_cfg = config.get("buy", {})
    if "mode" in buy_cfg:
        buy_mode = buy_cfg.get("mode", "switch")
        buy_rules = []
        if buy_mode == "switch":
            conditions = buy_cfg.get("conditions", [])
            for cond in conditions:
                if not cond.get("enabled", True):
                    continue
                ind = cond.get("indicator", "")
                op = cond.get("op", ">")
                value = cond.get("value", 0)
                name = cond.get("name", "")
                # 转换值
                if isinstance(value, str):
                    if value.startswith("ma") and value[2:].isdigit():
                        value = f"MA({value[2:]})"
                    elif value.startswith("boll"):
                        if value == "boll_upper":
                            value = "BOLL_upper(20,2)"
                        elif value == "boll_mid":
                            value = "BOLL(20)"
                        elif value == "boll_lower":
                            value = "BOLL_lower(20,2)"
                else:
                    value = str(value)
                # 构建表达式
                if ind == "close" and isinstance(value, str) and value.startswith("MA("):
                    condition = f"close {op} {value}"
                elif ind == "ma10" and value == "MA(20)":
                    condition = f"MA(10) {op} MA(20)"
                elif ind == "ma5" and value == "MA(10)":
                    condition = f"MA(5) {op} MA(10)"
                elif ind == "daily_return":
                    condition = f"returns(1) {op} {value}"
                elif ind == "return_20":
                    condition = f"returns(20) {op} {value}"
                elif ind == "return_21":
                    condition = f"returns(21) {op} {value}"
                elif ind == "volume_ratio":
                    condition = f"volume_ratio {op} {value}"
                elif ind == "wdm_momentum":
                    condition = f"close / MA(12) * 100 - 100 {op} {value}"
                elif ind == "momentum_score":
                    condition = f"returns(20) {op} {value}"
                elif ind == "std_momentum":
                    condition = f"returns(20) {op} {value}"
                elif ind == "difv":
                    condition = f"(MACD_DIF(12,26,9) / ATR(26)) * 100 {op} {value}"
                elif ind == "sort_value":
                    condition = f"sort_value {op} {value}"
                elif ind == "rank":
                    condition = f"rank {op} {value}"
                elif ind == "above_ma5" and op in ("is_true", "is_false"):
                    condition = "close > MA(5)" if op == "is_true" else "close <= MA(5)"
                elif ind == "above_ma10" and op in ("is_true", "is_false"):
                    condition = "close > MA(10)" if op == "is_true" else "close <= MA(10)"
                elif ind == "above_ma20" and op in ("is_true", "is_false"):
                    condition = "close > MA(20)" if op == "is_true" else "close <= MA(20)"
                elif ind == "rsrs_pass" and op in ("is_true", "is_false"):
                    condition = "RSRS_right_zscore(18) > 0.15" if op == "is_true" else "RSRS_right_zscore(18) <= 0.15"
                elif op in ("is_true", "is_false"):
                    condition = f"{ind} > 0" if op == "is_true" else f"{ind} <= 0"
                else:
                    condition = f"{ind} {op} {value}"
                desc = name if name else condition
                buy_rules.append({"condition": condition, "description": desc})
            migrated["buy"] = {"buy_match_mode": "all", "buy_rules": buy_rules}
        elif buy_mode == "free":
            groups = buy_cfg.get("condition_groups", [])
            for group in groups:
                for rule in group.get("rules", []):
                    ind = rule.get("indicator", "")
                    op = rule.get("op", ">")
                    value = rule.get("value", 0)
                    if isinstance(value, str):
                        if value.startswith("ma") and value[2:].isdigit():
                            value = f"MA({value[2:]})"
                        elif value.startswith("boll"):
                            if value == "boll_upper":
                                value = "BOLL_upper(20,2)"
                            elif value == "boll_mid":
                                value = "BOLL(20)"
                            elif value == "boll_lower":
                                value = "BOLL_lower(20,2)"
                    else:
                        value = str(value)
                    if op in ("is_true", "is_false"):
                        if ind == "rsrs_pass":
                            condition = "RSRS_right_zscore(18) > 0.15" if op == "is_true" else "RSRS_right_zscore(18) <= 0.15"
                        elif ind == "above_ma5":
                            condition = "close > MA(5)" if op == "is_true" else "close <= MA(5)"
                        elif ind == "above_ma10":
                            condition = "close > MA(10)" if op == "is_true" else "close <= MA(10)"
                        elif ind == "above_ma20":
                            condition = "close > MA(20)" if op == "is_true" else "close <= MA(20)"
                        else:
                            condition = f"{ind} > 0" if op == "is_true" else f"{ind} <= 0"
                    else:
                        condition = f"{ind} {op} {value}"
                    buy_rules.append({"condition": condition, "description": condition})
            migrated["buy"] = {"buy_match_mode": "any" if len(groups) > 1 else "all", "buy_rules": buy_rules}

    # 迁移卖出配置
    sell_cfg = config.get("sell", {})
    if "mode" in sell_cfg:
        sell_mode = sell_cfg.get("mode", "switch")
        stop_loss = sell_cfg.get("stop_loss", 0)
        sell_if_buy_fails = sell_cfg.get("sell_if_buy_fails", False)
        sell_rules = []
        if sell_mode == "switch":
            conditions = sell_cfg.get("conditions", [])
            for cond in conditions:
                if not cond.get("enabled", True):
                    continue
                ind = cond.get("indicator", "")
                op = cond.get("op", ">")
                value = cond.get("value", 0)
                name = cond.get("name", "")
                if isinstance(value, str):
                    if value.startswith("ma") and value[2:].isdigit():
                        value = f"MA({value[2:]})"
                    elif value.startswith("boll"):
                        if value == "boll_upper":
                            value = "BOLL_upper(20,2)"
                        elif value == "boll_mid":
                            value = "BOLL(20)"
                        elif value == "boll_lower":
                            value = "BOLL_lower(20,2)"
                else:
                    value = str(value)
                if ind == "daily_return":
                    condition = f"returns(1) {op} {value}"
                elif ind == "return_20":
                    condition = f"returns(20) {op} {value}"
                elif ind == "rank":
                    condition = f"rank {op} {value}"
                elif ind == "wdm_momentum":
                    condition = f"close / MA(12) * 100 - 100 {op} {value}"
                elif ind == "difv":
                    condition = f"(MACD_DIF(12,26,9) / ATR(26)) * 100 {op} {value}"
                elif ind == "close":
                    condition = f"close {op} {value}"
                elif ind == "momentum_score":
                    condition = f"returns(20) {op} {value}"
                elif ind == "std_momentum":
                    condition = f"returns(20) {op} {value}"
                elif op in ("is_true", "is_false"):
                    condition = f"{ind} > 0" if op == "is_true" else f"{ind} <= 0"
                else:
                    condition = f"{ind} {op} {value}"
                desc = name if name else condition
                sell_rules.append({"condition": condition, "description": desc})
            migrated["sell"] = {"sell_match_mode": "any", "sell_rules": sell_rules, "stop_loss": stop_loss, "sell_if_buy_fails": sell_if_buy_fails}
        elif sell_mode == "free":
            groups = sell_cfg.get("condition_groups", [])
            for group in groups:
                for rule in group.get("rules", []):
                    ind = rule.get("indicator", "")
                    op = rule.get("op", ">")
                    value = rule.get("value", 0)
                    if isinstance(value, str):
                        if value.startswith("ma") and value[2:].isdigit():
                            value = f"MA({value[2:]})"
                    else:
                        value = str(value)
                    if op in ("is_true", "is_false"):
                        if ind == "rsrs_pass":
                            condition = "RSRS_right_zscore(18) > 0.15" if op == "is_true" else "RSRS_right_zscore(18) <= 0.15"
                        elif ind == "above_ma5":
                            condition = "close > MA(5)" if op == "is_true" else "close <= MA(5)"
                        elif ind == "above_ma10":
                            condition = "close > MA(10)" if op == "is_true" else "close <= MA(10)"
                        elif ind == "above_ma20":
                            condition = "close > MA(20)" if op == "is_true" else "close <= MA(20)"
                        else:
                            condition = f"{ind} > 0" if op == "is_true" else f"{ind} <= 0"
                    else:
                        condition = f"{ind} {op} {value}"
                    sell_rules.append({"condition": condition, "description": condition})
            migrated["sell"] = {"sell_match_mode": "any" if len(groups) > 1 else "all", "sell_rules": sell_rules, "stop_loss": stop_loss, "sell_if_buy_fails": sell_if_buy_fails}

    return migrated


def load_saved_strategies():
    """加载用户保存的策略，自动迁移旧格式"""
    if os.path.exists(SAVED_STRATEGIES_FILE):
        with open(SAVED_STRATEGIES_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        migrated = {}
        need_save = False
        for name, config in saved.items():
            if _is_old_format(config):
                migrated[name] = _migrate_old_strategy(config)
                need_save = True
            else:
                migrated[name] = config
        if need_save:
            with open(SAVED_STRATEGIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(migrated, f, ensure_ascii=False, indent=2)
        return migrated
    return {}


def save_strategy(name, config):
    """保存策略配置（始终保存为新格式）"""
    saved = load_saved_strategies()
    saved[name] = config
    with open(SAVED_STRATEGIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(saved, f, ensure_ascii=False, indent=2)


def delete_strategy(name):
    """删除策略配置"""
    saved = load_saved_strategies()
    if name in saved:
        del saved[name]
        with open(SAVED_STRATEGIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(saved, f, ensure_ascii=False, indent=2)


# ============================================================
#  辅助函数
# ============================================================
def format_ticker_label(thscode):
    """格式化代码显示为 '代码 名称' """
    name = ETF_NAMES.get(thscode, "")
    code = thscode.split(".")[0]
    if name:
        return f"{code} {name}"
    return f"{code} (未命名)"


def _sync_multiselect_from_tickers(tickers, thscode_to_label, session_state):
    """将 selected_tickers 同步为 multiselect 的 labels，并存入 session_state"""
    labels = []
    for t in tickers:
        label = thscode_to_label.get(t, format_ticker_label(t))
        if label:
            labels.append(label)
    session_state["stock_multiselect"] = labels

def parse_thscode_from_label(label):
    """从 '代码 名称' 标签解析出 thscode"""
    code = label.split(" ")[0]
    return code


def _append_to_formula(formula_key, text):
    """可靠地追加文本到公式，处理空格"""
    current = st.session_state.get(formula_key, "")
    if current and not current.endswith((" ", "(", "+", "-", "*", "/", ">", "<", "=")):
        current += " "
    st.session_state[formula_key] = current + text


def _get_element_desc(x):
    """获取元素描述"""
    if x in BASIC_FIELDS:
        return BASIC_FIELDS[x]
    if x in SPECIAL_VARS:
        return SPECIAL_VARS[x]
    return x


def render_indicator_params(key_prefix, selected_indicator):
    """渲染指标参数输入控件"""
    if not selected_indicator or selected_indicator not in INDICATORS:
        return ""
    info = INDICATORS[selected_indicator]
    params = {}
    cols = st.columns(len(info["params"]))
    for i, p in enumerate(info["params"]):
        with cols[i]:
            step = p.get("step")
            kwargs = {"min_value": p["min"], "max_value": p["max"], "value": p["default"]}
            if step is not None:
                kwargs["step"] = step
            params[p["name"]] = st.number_input(
                p["label"], key=f"{key_prefix}_{selected_indicator}_param_{p['name']}", **kwargs
            )
    param_str = ",".join(str(params[p["name"]]) for p in info["params"])
    func_name = selected_indicator.split("(")[0]
    return f"{func_name}({param_str})"


def formula_editor(key_prefix, preset_formula=""):
    """万能公式编辑器：下拉选择 + 插入按钮
    核心策略：按钮回调设置pending标志，rerun后在text_area渲染前更新session_state缓存
    """
    formula_key = f"{key_prefix}_formula_text"
    editor_key = f"{key_prefix}_editor"
    pending_key = f"{key_prefix}_pending"
    
    # 初始化
    if formula_key not in st.session_state:
        st.session_state[formula_key] = preset_formula
        st.session_state[editor_key] = preset_formula
    
    # 关键：在widget渲染前处理待更新
    if pending_key in st.session_state:
        new_val = st.session_state[pending_key]
        st.session_state[formula_key] = new_val
        st.session_state[editor_key] = new_val
        del st.session_state[pending_key]
    
    # 显示公式编辑区
    st.markdown("**当前公式**")
    current = st.text_area(
        "编辑公式",
        value=st.session_state[formula_key],
        key=editor_key,
        placeholder="点击下方选择元素插入...",
        height=64,
        label_visibility="collapsed"
    )
    # 同步用户手动编辑
    st.session_state[formula_key] = current
    
    # 选择元素插入
    st.markdown("**选择元素插入到公式**")
    
    categories = {
        "基础字段": ["close", "open", "high", "low", "volume", "amount"],
        "特殊变量": ["rank", "profit", "hold_days", "buy_price"],
        "运算符": ["+", "-", "*", "/", ">", "<", ">=", "<=", "==", "!=", "AND", "OR", "(", ")"],
    }
    
    cat = st.selectbox("选择分类", ["系统指标"] + list(categories.keys()),
                       key=f"{key_prefix}_cat_select")
    
    if cat in categories:
        element = st.selectbox("选择元素", categories[cat],
                               format_func=lambda x: f"{x}  ({_get_element_desc(x)})",
                               key=f"{key_prefix}_element_select")
        param_expr = element
    else:
        ind_options = list(INDICATORS.keys())
        selected_ind = st.selectbox("选择指标", ind_options,
                                    format_func=lambda x: f"{INDICATORS[x]['name']} ({x.split('(')[0]})",
                                    key=f"{key_prefix}_ind_select")
        
        info = INDICATORS[selected_ind]
        params = {}
        cols = st.columns(len(info["params"]))
        for i, p in enumerate(info["params"]):
            with cols[i]:
                step = p.get("step")
                kwargs = {"min_value": p["min"], "max_value": p["max"], "value": p["default"]}
                if step is not None:
                    kwargs["step"] = step
                params[p["name"]] = st.number_input(
                    p["label"], key=f"{key_prefix}_{selected_ind}_param_{p['name']}", **kwargs
                )
        param_str = ",".join(str(params[p["name"]]) for p in info["params"])
        func_name = selected_ind.split("(")[0]
        param_expr = f"{func_name}({param_str})"
    
    # 插入按钮
    if st.button(f"➕ 插入 '{param_expr}'", key=f"{key_prefix}_insert", type="primary", use_container_width=True):
        cur = st.session_state[formula_key]
        if cur and not cur.endswith((" ", "(", "+", "-", "*", "/", ">", "<", "=")):
            cur += " "
        new_formula = cur + param_expr + " "
        st.session_state[pending_key] = new_formula
        st.rerun()
    
    return st.session_state[formula_key]


def rule_builder(key_prefix, existing_rules, title, color="green"):
    """规则构建器：已有规则列表（可删除）+ 公式编辑器（添加新规则）"""
    # 向后兼容：字符串列表转字典列表
    rules = []
    for r in existing_rules:
        if isinstance(r, str):
            rules.append({"condition": r, "description": r})
        elif isinstance(r, dict):
            rules.append(r)
    
    rules_key = f"{key_prefix}_rules_list"
    if rules_key not in st.session_state:
        st.session_state[rules_key] = rules
    
    current_rules = st.session_state[rules_key]
    
    # 已有规则（展开）
    with st.expander(f"📋 已有 {len(current_rules)} 条规则", expanded=True):
        for i, rule in enumerate(current_rules):
            c1, c2 = st.columns([8, 1])
            with c1:
                display = rule.get('description', rule.get('condition', ''))
                border_color = "#4CAF50" if color == "green" else "#F44336"
                st.markdown(f'<div style="background:#f8f9fa; padding:6px 10px; border-radius:4px; margin:2px 0; border-left:3px solid {border_color}; font-size:0.82rem;"><b>{i+1}.</b> {display}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("🗑️", key=f"{key_prefix}_del_{i}"):
                    current_rules.pop(i)
                    st.session_state[rules_key] = current_rules
                    st.rerun()
        if not current_rules:
            st.caption("暂无规则")
    
    # 添加新规则
    st.markdown(f"**➕ 添加新{'买入' if color=='green' else '卖出'}规则**")
    formula = formula_editor(key_prefix, "")
    
    if st.button(f"✅ 添加", key=f"{key_prefix}_add_rule", type="primary", use_container_width=True):
        if formula.strip():
            current_rules.append({"condition": formula.strip(), "description": formula.strip()})
            st.session_state[rules_key] = current_rules
            st.session_state[f"{key_prefix}_formula_text"] = ""
            st.rerun()
        else:
            st.error("公式不能为空")
    
    return current_rules


def init_session_state_defaults():
    """初始化 session_state 中的默认值"""
    defaults = {
        "preset_name": "自定义",
        "selected_tickers": [],
        "start_date": datetime.date(2020, 1, 2),
        "initial_capital": 1000000,
        "fee_rate": 0.0001,
        "cash_substitute": "511880.SH",
        "position_mode": "等权",
        "max_holdings": 5,
        "position_pct": 0.20,
        "rebalance_days": 2,
        "sort_rank_formula": "returns(20)",
        "sort_rank_direction": "desc",
        "buy_match_mode": "all",
        "buy_rules": [],
        "sell_match_mode": "any",
        "sell_rules": [],
        "sell_stop_loss": 0.0,
        "sell_if_buy_fails": False,
        "drop_penalty": False,
        "drop_threshold": 5.0,
    }
    # 保留旧字段默认值，避免其他引用报错（向后兼容）
    legacy_defaults = {
        "sort_indicator_label": "N日涨幅",
        "sort_direction": "降序",
        "sort_window": 21,
        "sort_momentum_window": 20,
        "sort_ema_short": 12,
        "sort_ema_long": 26,
        "sort_atr_period": 26,
        "sort_logbias_ema": 20,
        "sort_logbias_multiplier": 100,
        "sort_std_window": 20,
        "sort_wdm_shift": 12,
        "sort_wdm_smooth": 3,
    }
    defaults.update(legacy_defaults)
    
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    # 同步 multiselect 状态
    if "stock_multiselect" not in st.session_state:
        st.session_state["stock_multiselect"] = []


def apply_preset(name, config=None, available_tickers=None):
    """将预设策略的参数写入 session_state。可传入config用于加载保存的策略"""
    preset = config if config is not None else PRESET_STRATEGIES.get(name, {})
    if not preset:
        return

    # 自动迁移旧格式
    if _is_old_format(preset):
        preset = _migrate_old_strategy(preset)

    st.session_state["preset_name"] = name

    # 股票池（过滤本地不存在的标的）
    tickers = list(preset.get("stock_tickers", []))
    if available_tickers is not None:
        tickers = [t for t in tickers if t in available_tickers]
    st.session_state["selected_tickers"] = tickers
    # 同步 multiselect labels
    st.session_state["stock_multiselect"] = [format_ticker_label(t) for t in tickers]

    # 排序（新版表达式）
    sort_cfg = preset.get("sort", {})
    rank_formula = sort_cfg.get("rank_formula", "returns(20)")
    st.session_state["sort_rank_formula"] = rank_formula
    st.session_state["sort_rank_direction"] = sort_cfg.get("rank_direction", "desc")
    # 同步公式编辑器内部状态，避免缓存旧值
    st.session_state["sort_formula_text"] = rank_formula
    st.session_state["sort_editor"] = rank_formula
    for k in ["sort_pending", "buy_pending", "sell_pending"]:
        if k in st.session_state:
            del st.session_state[k]

    # 买入（新版规则）
    buy_cfg = preset.get("buy", {})
    buy_rules = buy_cfg.get("buy_rules", [])
    st.session_state["buy_match_mode"] = buy_cfg.get("buy_match_mode", "all")
    st.session_state["buy_rules"] = buy_rules
    st.session_state["buy_rules_list"] = buy_rules

    # 卖出（新版规则）
    sell_cfg = preset.get("sell", {})
    sell_rules = sell_cfg.get("sell_rules", [])
    st.session_state["sell_match_mode"] = sell_cfg.get("sell_match_mode", "any")
    st.session_state["sell_rules"] = sell_rules
    st.session_state["sell_rules_list"] = sell_rules
    st.session_state["sell_stop_loss"] = sell_cfg.get("stop_loss", 0) * 100
    st.session_state["sell_if_buy_fails"] = sell_cfg.get("sell_if_buy_fails", False)

    # 持仓
    pos_cfg = preset.get("position", {})
    mode_map = {"equal_weight": "等权", "single": "单标的", "incremental": "增量式"}
    st.session_state["position_mode"] = mode_map.get(pos_cfg.get("mode", "equal_weight"), "等权")
    st.session_state["max_holdings"] = pos_cfg.get("max_holdings", 5)
    st.session_state["position_pct"] = pos_cfg.get("position_pct", 0.20)
    st.session_state["rebalance_days"] = pos_cfg.get("rebalance_days", 2)

    # 基础配置（保存的策略可能包含这些字段）
    if "bond_ticker" in preset:
        bond_ticker = preset["bond_ticker"]
        st.session_state["cash_substitute"] = bond_ticker if bond_ticker else "cash"
    if "initial_capital" in preset:
        st.session_state["initial_capital"] = preset["initial_capital"]
    if "fee_rate" in preset:
        st.session_state["fee_rate"] = preset["fee_rate"]
    if "start_date" in preset:
        try:
            date_str = str(preset["start_date"])
            st.session_state["start_date"] = datetime.date.fromisoformat(date_str)
        except (ValueError, TypeError):
            pass

    st.session_state["_auto_run_backtest"] = True


def build_sort_config():
    """从 session_state 构建排序配置（新版表达式格式）"""
    return {
        "rank_formula": st.session_state.get("sort_rank_formula", "returns(20)"),
        "rank_direction": st.session_state.get("sort_rank_direction", "desc"),
    }


def build_buy_config():
    """从 session_state 构建买入配置（新版规则格式）"""
    rules = st.session_state.get("buy_rules", [])
    valid_rules = []
    for r in rules:
        if isinstance(r, dict):
            cond = r.get("condition", "")
            desc = r.get("description", cond)
            if cond.strip():
                valid_rules.append({"condition": cond, "description": desc})
        elif isinstance(r, str) and r.strip():
            valid_rules.append({"condition": r, "description": r})
    return {
        "buy_match_mode": st.session_state.get("buy_match_mode", "all"),
        "buy_rules": valid_rules,
    }


def build_sell_config():
    """从 session_state 构建卖出配置（新版规则格式）"""
    rules = st.session_state.get("sell_rules", [])
    valid_rules = []
    for r in rules:
        if isinstance(r, dict):
            cond = r.get("condition", "")
            desc = r.get("description", cond)
            if cond.strip():
                valid_rules.append({"condition": cond, "description": desc})
        elif isinstance(r, str) and r.strip():
            valid_rules.append({"condition": r, "description": r})
    return {
        "sell_match_mode": st.session_state.get("sell_match_mode", "any"),
        "sell_rules": valid_rules,
        "stop_loss": st.session_state.get("sell_stop_loss", 0) / 100.0,
        "sell_if_buy_fails": st.session_state.get("sell_if_buy_fails", False),
    }


def build_position_config():
    """从 session_state 构建持仓配置"""
    mode_map = {"等权": "equal_weight", "单标的": "single", "增量式": "incremental"}
    return {
        "mode": mode_map.get(st.session_state.position_mode, "equal_weight"),
        "max_holdings": st.session_state.max_holdings,
        "position_pct": st.session_state.position_pct,
        "rebalance_days": st.session_state.rebalance_days,
        "rebalance_mode": st.session_state.get("rebalance_mode", "incremental"),
        "new_rank_limit": 0,
    }


def build_backtest_config():
    """从 session_state 构建完整回测配置"""
    selected = st.session_state.get("selected_tickers", [])
    cash_sub = st.session_state.get("cash_substitute", "511880.SH")
    bond_ticker = cash_sub if cash_sub != "cash" else None

    config = {
        "stock_tickers": selected,
        "bond_ticker": bond_ticker,
        "initial_capital": st.session_state.initial_capital,
        "fee_rate": st.session_state.fee_rate,
        "start_date": str(st.session_state.start_date),
        "sort": build_sort_config(),
        "buy": build_buy_config(),
        "sell": build_sell_config(),
        "position": build_position_config(),
    }
    return config


def collect_current_config():
    """收集当前界面上的所有配置（格式与PRESET_STRATEGIES中的配置一致）"""
    cash_sub = st.session_state.get("cash_substitute", "511880.SH")
    bond_ticker = cash_sub if cash_sub != "cash" else None
    return {
        "stock_tickers": list(st.session_state.get("selected_tickers", [])),
        "bond_ticker": bond_ticker,
        "initial_capital": st.session_state.get("initial_capital", 1000000),
        "fee_rate": st.session_state.get("fee_rate", 0.0001),
        "start_date": str(st.session_state.get("start_date", "2020-01-02")),
        "sort": build_sort_config(),
        "buy": build_buy_config(),
        "sell": build_sell_config(),
        "position": build_position_config(),
    }


def _summarize_buy_conditions():
    """生成买入条件摘要文本"""
    rules = st.session_state.get("buy_rules", [])
    if not rules:
        return "无"
    parts = []
    for r in rules:
        if isinstance(r, dict):
            desc = r.get("description", r.get("condition", ""))
        elif isinstance(r, str):
            desc = r
        else:
            desc = ""
        if desc:
            parts.append(desc)
    return " AND ".join(parts)


def _summarize_sell_conditions():
    """生成卖出条件摘要文本"""
    parts = []
    stop_loss = st.session_state.get("sell_stop_loss", 0)
    if stop_loss > 0:
        parts.append(f"止损{stop_loss:.1f}%")
    if st.session_state.get("sell_if_buy_fails"):
        parts.append("不满足买入则卖出")
    rules = st.session_state.get("sell_rules", [])
    if rules:
        for r in rules:
            if isinstance(r, dict):
                desc = r.get("description", r.get("condition", ""))
            elif isinstance(r, str):
                desc = r
            else:
                desc = ""
            if desc:
                parts.append(desc)
    return " OR ".join(parts) if parts else "无"


def get_config_summary():
    """生成当前配置的文本摘要"""
    lines = []
    # 股票池
    tickers = st.session_state.get("selected_tickers", [])
    names = [ETF_NAMES.get(t, t.split(".")[0]) for t in tickers]
    lines.append(f"- 股票池: {len(tickers)}只 ({', '.join(names[:5])}{'...' if len(names) > 5 else ''})")
    # 排序
    rank_formula = st.session_state.get("sort_rank_formula", "returns(20)")
    rank_direction = st.session_state.get("sort_rank_direction", "desc")
    dir_text = "降序" if rank_direction == "desc" else "升序"
    lines.append(f"- 排序: {rank_formula} ({dir_text})")
    # 买入条件摘要
    buy_summary = _summarize_buy_conditions()
    lines.append(f"- 买入: {buy_summary}")
    # 卖出条件摘要
    sell_summary = _summarize_sell_conditions()
    lines.append(f"- 卖出: {sell_summary}")
    # 持仓
    pos_mode = st.session_state.get("position_mode", "等权")
    max_h = st.session_state.get("max_holdings", 5)
    pos_pct = st.session_state.get("position_pct", 0.20)
    rebal = st.session_state.get("rebalance_days", 2)
    lines.append(f"- 持仓: {pos_mode}{max_h}只, {pos_pct:.0%}比例, {rebal}日轮动")
    return "\n".join(lines)


def run_backtest_from_config(config):
    """执行回测并返回结果
    预设策略调用 legacy 原始硬编码函数（收益和 app.py 完全一致）
    自定义策略调用通用表达式引擎
    """
    stock_tickers = config.get("stock_tickers", [])
    if not stock_tickers:
        return None

    # 检测策略类型
    strategy_type = config.get("strategy_type", "custom")
    
    # 预设策略：调用 legacy 原始函数
    if strategy_type in ("difv", "wdm", "rsrs", "lof"):
        return _run_legacy_backtest(config, strategy_type)
    
    # 自定义策略：调用通用表达式引擎
    return _run_custom_backtest(config)


def _run_legacy_backtest(config, strategy_type):
    """调用 legacy 原始硬编码策略函数"""
    import engine.legacy as legacy
    
    stock_tickers = config.get("stock_tickers", [])
    start_date = config.get("start_date")
    initial_capital = config.get("initial_capital", 1000000)
    
    # 构建 ticker dicts
    ticker_dicts = {}
    for thscode in stock_tickers:
        parts = thscode.split(".")
        if len(parts) == 2:
            ticker_dicts[parts[0]] = {"suffix": parts[1], "thscode": thscode}
    
    # 加载数据
    pkl_dir = config.get("pkl_dir", r"D:\qmt_data\ETF\1d")
    data_dict = legacy.load_pkl_data(pkl_dir, ticker_dicts)
    data_dict, common_dates = legacy.build_data_dict(data_dict)
    
    if not data_dict or not common_dates:
        st.error("无法加载数据")
        return None
    
    # 根据策略类型计算指标和回测
    if strategy_type == "difv":
        signals = legacy.calc_difv_signals(data_dict, stock_tickers)
        bond_ticker = config.get("bond_ticker", "511880.SH")
        all_tickers = stock_tickers + ([bond_ticker] if bond_ticker else [])
        pos = config.get("position", {})
        nav_df, trade_df, hold_df, final_holdings, final_cash = legacy.run_difv_backtest(
            data_dict, signals, stock_tickers, bond_ticker, all_tickers, common_dates,
            initial_capital, start_date,
            pos.get("max_holdings", 5),
            pos.get("position_pct", 0.2),
            pos.get("rebalance_days", 2),
            config.get("sell", {}).get("sell_rank_gt", 6),
            config.get("sell", {}).get("sell_daily_drop", 0.03),
            config.get("sell", {}).get("sell_return_20", 0.25),
            config.get("buy", {}).get("buy_difv_max", 120),
            config.get("buy", {}).get("buy_rank_lt", 999),
            config.get("buy", {}).get("ma_conditions", {}),
            ticker_dicts,
        )
    elif strategy_type == "wdm":
        signals = legacy.calc_wdm_signals(data_dict, stock_tickers)
        nav_df, trade_df, hold_df, final_holdings, final_cash = legacy.run_wdm_backtest(
            data_dict, signals, stock_tickers, common_dates, initial_capital, start_date, ticker_dicts
        )
    elif strategy_type == "rsrs":
        signals = legacy.calc_rsrs_signals(data_dict, stock_tickers)
        nav_df, trade_df, hold_df, final_holdings, final_cash = legacy.run_rsrs_backtest(
            data_dict, signals, stock_tickers, common_dates, initial_capital, start_date,
            config.get("sell", {}).get("stop_loss", 0.03), ticker_dicts
        )
    elif strategy_type == "lof":
        signals = legacy.calc_lof_signals(data_dict, stock_tickers)
        nav_df, trade_df, hold_df, final_holdings, final_cash = legacy.run_lof_backtest(
            data_dict, signals, stock_tickers, common_dates, initial_capital, start_date, ticker_dicts
        )
    else:
        return None
    
    # 转换为统一格式
    if nav_df is None or nav_df.empty:
        return None
    
    return {
        "nav_df": nav_df,
        "trade_log": trade_df.to_dict("records") if not trade_df.empty else [],
        "hold_history": hold_df.to_dict("records") if hold_df is not None and not hold_df.empty else [],
        "final_holdings": final_holdings,
        "final_cash": final_cash,
    }


def _run_custom_backtest(config):
    """自定义策略：调用通用表达式引擎"""
    stock_tickers = config.get("stock_tickers", [])
    
    # 构建 ticker 列表用于 build_data_dict
    ticker_dicts = []
    for thscode in stock_tickers:
        parts = thscode.split(".")
        if len(parts) == 2:
            ticker_dicts.append({"code": parts[0], "suffix": parts[1]})

    bond_ticker = config.get("bond_ticker")
    if bond_ticker:
        parts = bond_ticker.split(".")
        if len(parts) == 2:
            ticker_dicts.append({"code": parts[0], "suffix": parts[1]})

    start_date = config.get("start_date")

    with st.spinner("正在加载数据..."):
        data_dict = build_data_dict(ticker_dicts, start_date=start_date)

    if not data_dict:
        st.error("无法加载任何数据，请检查 pkl 目录和数据文件。")
        return None

    with st.spinner("正在计算指标..."):
        signals = {}
        # 提取所有需要的表达式，只计算用到的指标（大幅提升性能）
        all_exprs = [config['sort']['rank_formula']]
        for rule in config.get('buy', {}).get('buy_rules', []):
            cond = rule.get('condition', '') if isinstance(rule, dict) else str(rule)
            if cond.strip():
                all_exprs.append(cond)
        for rule in config.get('sell', {}).get('sell_rules', []):
            cond = rule.get('condition', '') if isinstance(rule, dict) else str(rule)
            if cond.strip():
                all_exprs.append(cond)
        for ticker, df in data_dict.items():
            signals[ticker] = compute_indicators_for_df(df, all_exprs)

    with st.spinner("正在运行回测..."):
        result = run_backtest(data_dict, signals, config)

    return result


# ============================================================
#  初始化 session_state
# ============================================================
init_session_state_defaults()

# ============================================================
#  页面标题
# ============================================================
st.title("ETF轮动策略回测系统")

# ============================================================
#  侧边栏
# ============================================================
# 获取所有可用的 pkl 文件（提前构建映射，侧边栏和主区域都用）
_all_pkl_items = cached_scan_pkl_dir()
_thscode_to_label = {}
_label_to_thscode = {}
for _item in _all_pkl_items:
    _thscode = _item["thscode"]
    _label = format_ticker_label(_thscode)
    _thscode_to_label[_thscode] = _label
    _label_to_thscode[_label] = _thscode

_available_thscodes = set(_item["thscode"] for _item in _all_pkl_items)

with st.sidebar:
    st.header("策略配置")

    # ---- 1. 预设策略选择 ----
    st.subheader("预设策略")
    saved_strategies = load_saved_strategies()
    saved_names = list(saved_strategies.keys())
    # 构建选项列表：预设策略 + 分隔线 + 保存的策略
    preset_keys = list(PRESET_STRATEGIES.keys())
    if saved_names:
        all_preset_options = preset_keys + ["── 保存的策略 ──"] + saved_names
    else:
        all_preset_options = preset_keys
    current_preset_idx = all_preset_options.index(st.session_state.preset_name) if st.session_state.preset_name in all_preset_options else 0
    selected_preset = st.selectbox(
        "选择预设策略",
        all_preset_options,
        index=current_preset_idx,
        key="preset_selectbox",
    )
    if selected_preset != st.session_state.get("_last_preset", "自定义"):
        if selected_preset == "── 保存的策略 ──":
            st.session_state["_last_preset"] = selected_preset
        elif selected_preset != "自定义":
            if selected_preset in PRESET_STRATEGIES:
                apply_preset(selected_preset, available_tickers=_available_thscodes)
            elif selected_preset in saved_strategies:
                apply_preset(selected_preset, saved_strategies[selected_preset], available_tickers=_available_thscodes)
            st.session_state["_last_preset"] = selected_preset
            
            config = build_backtest_config()
            if config.get("stock_tickers"):
                with st.spinner("正在运行回测..."):
                    try:
                        result = run_backtest_from_config(config)
                        if result is not None:
                            st.session_state["backtest_result"] = result
                            st.session_state["backtest_config"] = config
                    except Exception as e:
                        st.error(f"回测出错：{e}")
            
            st.rerun()
        else:
            st.session_state["_last_preset"] = selected_preset
            st.rerun()

    st.divider()

    # ---- 2. 股票池选择（分组优化） ----
    st.subheader("股票池选择")

    # 分组选择 → 一键添加
    group_names = list(ETF_GROUPS.keys())
    selected_group = st.selectbox(
        "选择分组",
        ["（选择分组后点击添加）"] + group_names,
        key="etf_group_select",
    )
    col_add_group, col_clear_group = st.columns(2)
    with col_add_group:
        if st.button("➕ 添加该组", use_container_width=True, key="btn_add_group"):
            if selected_group in ETF_GROUPS:
                current_set = set(st.session_state.get("selected_tickers", []))
                # 只添加本地存在的标的
                group_tickers = set(ETF_GROUPS[selected_group]) & _available_thscodes
                new_tickers = current_set | group_tickers
                new_list = sorted(new_tickers)
                st.session_state.selected_tickers = new_list
                st.session_state["stock_multiselect"] = [format_ticker_label(t) for t in new_list]
                st.rerun()
    with col_clear_group:
        if st.button("🗑️ 清空已选", use_container_width=True, key="btn_clear_group"):
            st.session_state.selected_tickers = []
            st.session_state["stock_multiselect"] = []
            st.rerun()

    # 搜索框
    search_text = st.text_input("搜索ETF", value="", key="etf_search")

    # 当前已选标的用multiselect展示（可逐个增删）
    all_labels = list(_label_to_thscode.keys())
    if search_text:
        filtered_labels = [l for l in all_labels if search_text.upper() in l.upper()]
    else:
        filtered_labels = all_labels

    # 确保 session_state 中的 multiselect 值也在 options 中（避免 Streamlit 报错）
    for label in st.session_state.get("stock_multiselect", []):
        if label not in filtered_labels:
            filtered_labels.append(label)

    # 渲染 multiselect（不手动设置 session_state，让 Streamlit 自动管理）
    selected_labels = st.multiselect(
        f"已选标的 ({len(st.session_state.selected_tickers)}只)",
        filtered_labels,
        key="stock_multiselect",
    )

    # 同步回 selected_tickers
    st.session_state.selected_tickers = [_label_to_thscode[l] for l in selected_labels if l in _label_to_thscode]

    st.divider()

    # ---- 3. 基础配置 ----
    st.subheader("基础配置")

    st.session_state.start_date = st.date_input(
        "起始日期",
        value=st.session_state.start_date,
        key="start_date_input",
    )

    col_capital, col_fee = st.columns(2)
    with col_capital:
        st.session_state.initial_capital = st.number_input(
            "初始资金",
            min_value=10000,
            max_value=100000000,
            value=st.session_state.initial_capital,
            step=100000,
            key="initial_capital_input",
        )
    with col_fee:
        st.session_state.fee_rate = st.number_input(
            "手续费率",
            min_value=0.0,
            max_value=0.01,
            value=st.session_state.fee_rate,
            format="%.4f",
            key="fee_rate_input",
        )

    cash_sub_options = {"银华日利511880": "511880.SH", "纯现金": "cash"}
    cash_sub_labels = list(cash_sub_options.keys())
    current_cash_sub_label = "纯现金" if st.session_state.cash_substitute == "cash" else "银华日利511880"
    cash_sub_idx = cash_sub_labels.index(current_cash_sub_label) if current_cash_sub_label in cash_sub_labels else 0
    selected_cash_sub = st.selectbox(
        "空仓替代",
        cash_sub_labels,
        index=cash_sub_idx,
        key="cash_substitute_select",
    )
    st.session_state.cash_substitute = cash_sub_options[selected_cash_sub]

    st.divider()

    # ---- 4. 持仓配置 ----
    st.subheader("持仓配置")

    col_pos_mode, col_holdings = st.columns(2)
    with col_pos_mode:
        position_modes = ["等权", "单标的", "增量式"]
        pos_mode_idx = position_modes.index(st.session_state.position_mode) if st.session_state.position_mode in position_modes else 0
        st.session_state.position_mode = st.selectbox(
            "持仓模式",
            position_modes,
            index=pos_mode_idx,
            key="position_mode_select",
        )
    with col_holdings:
        st.session_state.max_holdings = st.number_input(
            "最大持仓数",
            min_value=1,
            max_value=20,
            value=st.session_state.max_holdings,
            key="max_holdings_input",
        )

    col_pct, col_rebal, col_rebal_mode = st.columns(3)
    with col_pct:
        st.session_state.position_pct = st.number_input(
            "仓位比例",
            min_value=0.01,
            max_value=1.0,
            value=st.session_state.position_pct,
            step=0.05,
            format="%.2f",
            key="position_pct_input",
        )
    with col_rebal:
        st.session_state.rebalance_days = st.number_input(
            "轮动周期(日)",
            min_value=1,
            max_value=20,
            value=st.session_state.rebalance_days,
            key="rebalance_days_input",
        )
    with col_rebal_mode:
        rebal_modes = ["增量式", "全量式"]
        rebal_mode_map = {"增量式": "incremental", "全量式": "full"}
        current_rebal_mode = st.session_state.get("rebalance_mode", "incremental")
        current_label = "增量式" if current_rebal_mode == "incremental" else "全量式"
        selected_label = st.selectbox(
            "再平衡模式",
            rebal_modes,
            index=rebal_modes.index(current_label) if current_label in rebal_modes else 0,
            key="rebalance_mode_select",
        )
        st.session_state.rebalance_mode = rebal_mode_map.get(selected_label, "incremental")

    st.divider()

    # ---- 5. 策略管理（折叠） ----
    with st.expander("策略管理（保存/加载/删除）"):
        strategy_save_name = st.text_input("策略名称（用于保存）", value="", key="strategy_save_name")

        if st.button("💾 保存当前策略", use_container_width=True):
            if not strategy_save_name.strip():
                st.warning("请输入策略名称！")
            else:
                config = collect_current_config()
                save_strategy(strategy_save_name.strip(), config)
                st.success(f"策略「{strategy_save_name.strip()}」已保存！")
                st.session_state["_last_preset"] = strategy_save_name.strip()
                st.rerun()

        saved_strategies_for_manage = load_saved_strategies()
        saved_strategy_names = list(saved_strategies_for_manage.keys())

        if saved_strategy_names:
            selected_saved_strategy = st.selectbox(
                "已保存的策略",
                saved_strategy_names,
                key="saved_strategy_select",
            )

            col_load, col_del = st.columns(2)
            with col_load:
                if st.button("📂 加载选中策略", use_container_width=True):
                    if selected_saved_strategy in saved_strategies_for_manage:
                        apply_preset(selected_saved_strategy, saved_strategies_for_manage[selected_saved_strategy], available_tickers=_available_thscodes)
                        st.session_state["_last_preset"] = selected_saved_strategy
                        st.rerun()
            with col_del:
                if st.button("🗑️ 删除选中策略", use_container_width=True):
                    delete_strategy(selected_saved_strategy)
                    st.success(f"策略「{selected_saved_strategy}」已删除！")
                    if st.session_state.get("preset_name") == selected_saved_strategy:
                        st.session_state["preset_name"] = "自定义"
                        st.session_state["_last_preset"] = "自定义"
                    st.rerun()
        else:
            st.info("暂无保存的策略")

# ============================================================
#  主区域 —— Tabs
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs(["轮动排序规格", "买入条件", "卖出条件", "回测结果"])

# ============================================================
#  Tab1: 轮动排序规格（新版公式编辑器）
# ============================================================
with tab1:
    st.header("轮动排序规格")
    st.caption("使用公式编辑器构建排序表达式，如：(MACD_DIF(12,26,9) / ATR(26)) * 100")
    
    # 排名方向
    rank_direction = st.radio(
        "排名方向",
        ["desc", "asc"],
        index=0 if st.session_state.get("sort_rank_direction", "desc") == "desc" else 1,
        format_func=lambda x: "分数越大越好（降序）" if x == "desc" else "分数越小越好（升序）",
        key="sort_rank_direction_radio",
        horizontal=True,
    )
    st.session_state["sort_rank_direction"] = rank_direction
    
    st.divider()
    
    # 公式编辑器
    formula = formula_editor("sort", st.session_state.get("sort_rank_formula", "returns(20)"))
    st.session_state["sort_rank_formula"] = formula


# ============================================================
#  Tab2: 买入条件（新版规则构建器）
# ============================================================
with tab2:
    st.header("买入条件")
    st.caption("使用规则构建器添加买入条件，所有条件取 AND（全部满足）逻辑")
    
    # 匹配模式
    buy_match_mode = st.radio(
        "匹配模式",
        ["all", "any"],
        index=0 if st.session_state.get("buy_match_mode", "all") == "all" else 1,
        format_func=lambda x: "全部满足（AND）" if x == "all" else "任一满足（OR）",
        key="buy_match_mode_radio",
        horizontal=True,
    )
    st.session_state["buy_match_mode"] = buy_match_mode
    
    st.divider()
    
    # 规则构建器
    buy_rules = rule_builder("buy", st.session_state.get("buy_rules", []), "🟢 买入规则", "green")
    st.session_state["buy_rules"] = buy_rules


# ============================================================
#  Tab3: 卖出条件（新版规则构建器）
# ============================================================
with tab3:
    st.header("卖出条件")
    st.caption("使用规则构建器添加卖出条件，可配置匹配模式、止损和额外选项")
    
    # 匹配模式
    sell_match_mode = st.radio(
        "匹配模式",
        ["any", "all"],
        index=0 if st.session_state.get("sell_match_mode", "any") == "any" else 1,
        format_func=lambda x: "任一满足即卖出（OR）" if x == "any" else "全部满足才卖出（AND）",
        key="sell_match_mode_radio",
        horizontal=True,
    )
    st.session_state["sell_match_mode"] = sell_match_mode
    
    st.divider()
    
    # 止损 + 不满足买入条件则卖出
    col_extra1, col_extra2 = st.columns(2)
    with col_extra1:
        st.session_state.sell_stop_loss = st.number_input(
            "止损比例(%)",
            min_value=0.0,
            max_value=50.0,
            value=st.session_state.sell_stop_loss,
            step=0.5,
            format="%.1f",
            key="sell_stop_loss_input",
        )
    with col_extra2:
        st.session_state.sell_if_buy_fails = st.checkbox(
            "不满足买入条件则卖出",
            value=st.session_state.sell_if_buy_fails,
            key="sell_if_buy_fails_checkbox",
        )
    
    st.divider()
    
    # 规则构建器
    sell_rules = rule_builder("sell", st.session_state.get("sell_rules", []), "🔴 卖出规则", "red")
    st.session_state["sell_rules"] = sell_rules


# ============================================================
#  Tab4: 回测结果
# ============================================================
with tab4:
    st.header("回测结果")

    # 配置概要
    with st.expander("📋 当前配置概要", expanded=True):
        st.code(get_config_summary())

    # 醒目的运行按钮（主区域顶部）
    run_btn_main = st.button("🚀 运行回测", type="primary", use_container_width=True, key="run_backtest_main")

    # 检查是否需要自动运行回测
    auto_run = st.session_state.get("_auto_run_backtest", False)
    if auto_run:
        st.session_state["_auto_run_backtest"] = False

    # 运行回测（主区域按钮或自动触发）
    if run_btn_main or auto_run:
        config = build_backtest_config()
        if not config.get("stock_tickers"):
            st.warning("请先选择股票池中的标的！")
        else:
            try:
                result = run_backtest_from_config(config)
                if result is not None:
                    st.session_state["backtest_result"] = result
                    st.session_state["backtest_config"] = config
            except Exception as e:
                st.error(f"回测出错：{e}")
                st.code(traceback.format_exc())

    # 显示结果
    if "backtest_result" in st.session_state:
        result = st.session_state["backtest_result"]
        nav_df = result.get("nav_df", pd.DataFrame())
        trade_log = result.get("trade_log", [])

        if nav_df.empty:
            st.warning("回测结果为空，请检查参数设置。")
        else:
            # 绩效卡片
            perf = compute_performance(nav_df)

            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("总收益率", f"{perf['total_return']:.2f}%")
            with col2:
                st.metric("年化收益率", f"{perf['annual_return']:.2f}%")
            with col3:
                st.metric("最大回撤", f"{perf['max_dd']:.2f}%")
            with col4:
                st.metric("夏普比率", f"{perf['sharpe']:.2f}")
            with col5:
                st.metric("卡尔玛比率", f"{perf['calmar']:.2f}")

            st.divider()

            # 净值曲线图
            st.subheader("净值曲线")
            try:
                fig_nav = plot_nav_curve(nav_df)
                st.pyplot(fig_nav)
            except Exception as e:
                st.error(f"绘制净值曲线失败：{e}")

            # 回撤图
            st.subheader("回撤图")
            try:
                fig_dd = plot_drawdown(nav_df)
                st.pyplot(fig_dd)
            except Exception as e:
                st.error(f"绘制回撤图失败：{e}")

            st.divider()

            # 年度收益表
            st.subheader("年度收益表")
            try:
                yearly_df = compute_yearly_returns(nav_df)
                if not yearly_df.empty:
                    # 格式化显示
                    display_df = yearly_df.copy()
                    display_df.columns = ["年份", "收益率(%)", "最大回撤(%)"]
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                else:
                    st.info("无年度收益数据")
            except Exception as e:
                st.error(f"计算年度收益失败：{e}")

            st.divider()

            # 交易记录表
            st.subheader("交易记录")
            if trade_log:
                trade_df = pd.DataFrame(trade_log)

                # 格式化显示
                display_trade = trade_df.copy()
                if 'date' in display_trade.columns:
                    display_trade['date'] = display_trade['date'].astype(str)
                if 'price' in display_trade.columns:
                    display_trade['price'] = display_trade['price'].round(4)
                if 'value' in display_trade.columns:
                    display_trade['value'] = display_trade['value'].round(2)
                if 'fee' in display_trade.columns:
                    display_trade['fee'] = display_trade['fee'].round(2)
                if 'pnl_pct' in display_trade.columns:
                    display_trade['pnl_pct'] = display_trade['pnl_pct'].round(2)
                if 'shares' in display_trade.columns:
                    display_trade['shares'] = display_trade['shares'].round(0)

                # 中文列名映射
                col_rename = {
                    'date': '日期',
                    'ticker': '代码',
                    'name': '名称',
                    'action': '操作',
                    'price': '价格',
                    'shares': '数量',
                    'value': '金额',
                    'fee': '手续费',
                    'pnl_pct': '盈亏(%)',
                    'hold_days': '持仓天数',
                    'reason': '原因',
                }
                display_trade = display_trade.rename(columns={k: v for k, v in col_rename.items() if k in display_trade.columns})

                st.dataframe(display_trade, use_container_width=True, hide_index=True)

                # CSV 下载
                csv_buffer = io.StringIO()
                trade_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                csv_data = csv_buffer.getvalue()

                st.download_button(
                    label="📥 下载交易记录 CSV",
                    data=csv_data,
                    file_name="trade_log.csv",
                    mime="text/csv",
                )
            else:
                st.info("暂无交易记录")

            # ====== 生成QMT实盘文件 ======
            st.divider()
            st.subheader("生成QMT实盘文件")
            st.caption("将当前策略配置生成可直接在QMT中运行的完整双模式py文件（回测+实盘一体化）")

            col_q1, col_q2 = st.columns(2)
            with col_q1:
                qmt_name = st.text_input("策略名称", value="自定义轮动策略", key="qmt_name")
                qmt_account = st.text_input("QMT账号", value="520000249836", key="qmt_account")
                qmt_capital = st.number_input("实盘资金(元)", value=10000.0, min_value=1000.0, key="qmt_capital")
            with col_q2:
                qmt_dir = st.text_input("输出目录", value=r"C:\自定义策略", key="qmt_dir")
                qmt_run_mode = st.selectbox("运行模式", ["live", "backtest"], index=0,
                                            format_func=lambda x: "实盘(live)" if x == "live" else "回测(backtest)",
                                            key="qmt_run_mode")

            if st.button("生成QMT实盘文件", type="primary", use_container_width=True):
                config = st.session_state.get("backtest_config", {})
                if not config.get("stock_tickers"):
                    st.warning("请先运行回测！")
                else:
                    with st.spinner("正在生成QMT文件..."):
                        try:
                            from qmt_generator import generate_qmt_file
                            os.makedirs(qmt_dir, exist_ok=True)
                            output_path = os.path.join(qmt_dir, f"{qmt_name}.py")
                            generate_qmt_file(config, output_path, qmt_name,
                                              account_id=qmt_account,
                                              real_capital=qmt_capital,
                                              script_dir=qmt_dir,
                                              run_mode=qmt_run_mode)
                            st.success(f"QMT文件已生成: {output_path}")

                            with open(output_path, 'r', encoding='utf-8') as f:
                                file_content = f.read()
                            st.download_button(
                                label="下载py文件",
                                data=file_content,
                                file_name=f"{qmt_name}.py",
                                mime="text/x-python",
                                use_container_width=True,
                            )
                            st.info(f"文件大小: {len(file_content)} 字符 | {file_content.count(chr(10))} 行")
                        except Exception as e:
                            st.error(f"生成失败: {e}")

            # 附加信息
            st.divider()
            with st.expander("回测配置详情"):
                if "backtest_config" in st.session_state:
                    config = st.session_state["backtest_config"]
                    st.json(config, expanded=False)
    else:
        st.info("请配置参数后点击上方 **🚀 运行回测** 按钮开始回测")

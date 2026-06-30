# -*- coding: utf-8 -*-
from .data_loader import scan_pkl_dir, load_pkl_data, build_data_dict, ETF_NAMES
from .indicators import (
    compute_all_indicators as calc_all_indicators,
    compute_indicators_for_df,
    MA, EMA, RSI, MACD, BOLL, KDJ, ATR, returns, BIAS,
    quality_score, volatility, gain_percentile, volume_percentile,
    RSRS_slope, RSRS_zscore, RSRS_right_zscore, penalty_score,
)
from .expression_parser import evaluate_condition, evaluate_score, ExpressionParser
from .precompiler import precompute_strategy, has_special_var, evaluate_fast
from .backtester import run_backtest
from .performance import compute_performance, plot_nav_curve, plot_drawdown, compute_yearly_returns

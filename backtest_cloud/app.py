# -*- coding: utf-8 -*-
"""
ETF轮动策略回测Web系统
端口: 8001
"""
from __future__ import print_function, division
import os
import json
import traceback
import datetime
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, Response

app = Flask(__name__)

# ========================================
#  数据目录
# ========================================
PKL_DIR = os.environ.get(
    "PKL_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ETF", "1d")
)

# ========================================
#  ETF配置
# ========================================
ETF_CONFIG_DIFV = {
    "159949": {"suffix": "SZ", "thscode": "159949.SZ", "name_cn": "创业板50"},
    "159980": {"suffix": "SZ", "thscode": "159980.SZ", "name_cn": "有色ETF"},
    "159981": {"suffix": "SZ", "thscode": "159981.SZ", "name_cn": "能源化工"},
    "159985": {"suffix": "SZ", "thscode": "159985.SZ", "name_cn": "豆粕ETF"},
    "510300": {"suffix": "SH", "thscode": "510300.SH", "name_cn": "沪深300"},
    "513030": {"suffix": "SH", "thscode": "513030.SH", "name_cn": "德国ETF"},
    "513050": {"suffix": "SH", "thscode": "513050.SH", "name_cn": "中概互联"},
    "513100": {"suffix": "SH", "thscode": "513100.SH", "name_cn": "纳指ETF"},
    "513500": {"suffix": "SH", "thscode": "513500.SH", "name_cn": "标普500"},
    "513520": {"suffix": "SH", "thscode": "513520.SH", "name_cn": "日经ETF"},
    "512100": {"suffix": "SH", "thscode": "512100.SH", "name_cn": "中证1000"},
    "501018": {"suffix": "SH", "thscode": "501018.SH", "name_cn": "南方原油"},
    "518880": {"suffix": "SH", "thscode": "518880.SH", "name_cn": "黄金ETF"},
    "511880": {"suffix": "SH", "thscode": "511880.SH", "name_cn": "银华日利"},
}

ETF_CONFIG_WDM = {
    "510050": {"suffix": "SH", "thscode": "510050.SH", "name_cn": "上证50"},
    "510300": {"suffix": "SH", "thscode": "510300.SH", "name_cn": "沪深300"},
    "588000": {"suffix": "SH", "thscode": "588000.SH", "name_cn": "科创50"},
    "159915": {"suffix": "SZ", "thscode": "159915.SZ", "name_cn": "创业板"},
    "159531": {"suffix": "SZ", "thscode": "159531.SZ", "name_cn": "中证2000"},
}

ETF_CONFIG_DCA = {
    "159938": {"suffix": "SZ", "thscode": "159938.SZ", "name_cn": "医药ETF", "start_date": "2020-03-12"},
    "513100": {"suffix": "SH", "thscode": "513100.SH", "name_cn": "纳指ETF", "start_date": "2020-03-12"},
    "513050": {"suffix": "SH", "thscode": "513050.SH", "name_cn": "中概互联", "start_date": "2020-03-12"},
    "159928": {"suffix": "SZ", "thscode": "159928.SZ", "name_cn": "消费ETF", "start_date": "2020-03-12"},
    "159740": {"suffix": "SZ", "thscode": "159740.SZ", "name_cn": "恒生科技", "start_date": "2021-05-27"},
}

ETF_CONFIG_DD_DCA = {
    "159938": {"suffix": "SZ", "thscode": "159938.SZ", "name_cn": "医药ETF", "tp": 0.50, "amount": 5000, "start_date": "2024-01-02"},
    "513100": {"suffix": "SH", "thscode": "513100.SH", "name_cn": "纳指ETF", "tp": 0.50, "amount": 500, "start_date": "2026-04-13"},
    "513050": {"suffix": "SH", "thscode": "513050.SH", "name_cn": "中概互联", "tp": 0.50, "amount": 5000, "start_date": "2020-12-21"},
    "159928": {"suffix": "SZ", "thscode": "159928.SZ", "name_cn": "消费ETF", "tp": 0.50, "amount": 1000, "start_date": "2023-09-02"},
    "159740": {"suffix": "SZ", "thscode": "159740.SZ", "name_cn": "恒生科技", "tp": 0.50, "amount": 1000, "start_date": "2021-05-27"},
}

ETF_CONFIG_VA_DCA = {
    "159938": {"suffix": "SZ", "thscode": "159938.SZ", "name_cn": "医药ETF", "tp": 0.50, "growth": 5000, "start_date": "2024-01-02"},
    "513100": {"suffix": "SH", "thscode": "513100.SH", "name_cn": "纳指ETF", "tp": 0.50, "growth": 500, "start_date": "2026-04-13"},
    "513050": {"suffix": "SH", "thscode": "513050.SH", "name_cn": "中概互联", "tp": 0.50, "growth": 5000, "start_date": "2020-12-21"},
    "159928": {"suffix": "SZ", "thscode": "159928.SZ", "name_cn": "消费ETF", "tp": 0.50, "growth": 1000, "start_date": "2023-09-02"},
    "159740": {"suffix": "SZ", "thscode": "159740.SZ", "name_cn": "恒生科技", "tp": 0.50, "growth": 1000, "start_date": "2021-05-27"},
}

ETF_CONFIG_LOF = {
    "163402": {"suffix": "SZ", "thscode": "163402.SZ", "name_cn": "兴全趋势LOF"},
    "163417": {"suffix": "SZ", "thscode": "163417.SZ", "name_cn": "兴全合宜LOF"},
    "161903": {"suffix": "SZ", "thscode": "161903.SZ", "name_cn": "万家行业优选LOF"},
    "162703": {"suffix": "SZ", "thscode": "162703.SZ", "name_cn": "广发小盘LOF"},
    "161005": {"suffix": "SZ", "thscode": "161005.SZ", "name_cn": "富国天惠LOF"},
}

ETF_CONFIG_TECH_DIFV = {
    "588200": {"suffix": "SH", "thscode": "588200.SH", "name_cn": "科创芯片"},
    "159819": {"suffix": "SZ", "thscode": "159819.SZ", "name_cn": "人工智能"},
    "515050": {"suffix": "SH", "thscode": "515050.SH", "name_cn": "通信ETF"},
    "515880": {"suffix": "SH", "thscode": "515880.SH", "name_cn": "通信ETF国泰"},
    "516510": {"suffix": "SH", "thscode": "516510.SH", "name_cn": "云计算"},
    "159852": {"suffix": "SZ", "thscode": "159852.SZ", "name_cn": "软件ETF"},
    "512480": {"suffix": "SH", "thscode": "512480.SH", "name_cn": "半导体"},
    "159732": {"suffix": "SZ", "thscode": "159732.SZ", "name_cn": "消费电子"},
    "588250": {"suffix": "SH", "thscode": "588250.SH", "name_cn": "科创医药"},
    "516010": {"suffix": "SH", "thscode": "516010.SH", "name_cn": "游戏ETF"},
    "562500": {"suffix": "SH", "thscode": "562500.SH", "name_cn": "机器人"},
    "512660": {"suffix": "SH", "thscode": "512660.SH", "name_cn": "军工ETF"},
    "159667": {"suffix": "SZ", "thscode": "159667.SZ", "name_cn": "工业母机"},
    "159992": {"suffix": "SZ", "thscode": "159992.SZ", "name_cn": "创新药"},
    "159883": {"suffix": "SZ", "thscode": "159883.SZ", "name_cn": "医疗器械"},
    "516800": {"suffix": "SH", "thscode": "516800.SH", "name_cn": "智能制造"},
    "588010": {"suffix": "SH", "thscode": "588010.SH", "name_cn": "科创新材料"},
    "515790": {"suffix": "SH", "thscode": "515790.SH", "name_cn": "光伏ETF"},
    "515700": {"suffix": "SH", "thscode": "515700.SH", "name_cn": "新能源车"},
    "159755": {"suffix": "SZ", "thscode": "159755.SZ", "name_cn": "电池ETF"},
    "159566": {"suffix": "SZ", "thscode": "159566.SZ", "name_cn": "储能电池"},
    "515400": {"suffix": "SH", "thscode": "515400.SH", "name_cn": "大数据"},
    "159542": {"suffix": "SZ", "thscode": "159542.SZ", "name_cn": "工程机械"},
    "563010": {"suffix": "SH", "thscode": "563010.SH", "name_cn": "电信ETF"},
    "159786": {"suffix": "SZ", "thscode": "159786.SZ", "name_cn": "虚拟现实"},
    "159997": {"suffix": "SZ", "thscode": "159997.SZ", "name_cn": "电子ETF"},
}

ETF_CONFIG_DIFV_MOM = {
    "512890": {"suffix": "SH", "thscode": "512890.SH", "name_cn": "红利低波"},
    "515050": {"suffix": "SH", "thscode": "515050.SH", "name_cn": "通信ETF"},
    "513310": {"suffix": "SH", "thscode": "513310.SH", "name_cn": "中韩半导体"},
    "513100": {"suffix": "SH", "thscode": "513100.SH", "name_cn": "纳指ETF"},
    "513500": {"suffix": "SH", "thscode": "513500.SH", "name_cn": "标普500"},
    "513520": {"suffix": "SH", "thscode": "513520.SH", "name_cn": "日经ETF"},
    "513030": {"suffix": "SH", "thscode": "513030.SH", "name_cn": "德国ETF"},
    "518880": {"suffix": "SH", "thscode": "518880.SH", "name_cn": "黄金ETF"},
}

ETF_CONFIG_RSRS = {
    "518880": {"suffix": "SH", "thscode": "518880.SH", "name_cn": "黄金ETF"},
    "513100": {"suffix": "SH", "thscode": "513100.SH", "name_cn": "纳指ETF"},
    "588220": {"suffix": "SH", "thscode": "588220.SH", "name_cn": "科创100"},
    "159915": {"suffix": "SZ", "thscode": "159915.SZ", "name_cn": "创业板"},
    "511090": {"suffix": "SH", "thscode": "511090.SH", "name_cn": "30年国债"},
}

BOND_TICKER = "511880.SH"
FEE_RATE = 0.0001


# ========================================
#  数据加载
# ========================================
def load_pkl_data(pkl_dir, tickers):
    result = {}
    for code, cfg in tickers.items():
        pkl_file = os.path.join(pkl_dir, "{}_{}_1d.pkl".format(code, cfg['suffix']))
        if not os.path.exists(pkl_file):
            continue
        try:
            df = pd.read_pickle(pkl_file).reset_index()
            df['time'] = pd.to_datetime(df['stime'].astype(str), format='%Y%m%d')
            df = df[(df['close'] > 0) & (df['open'] > 0) & (df['volume'] > 0)].copy()
            result[cfg['thscode']] = df.set_index('time')[['open', 'high', 'low', 'close', 'volume']]
        except Exception:
            continue
    return result


def build_data_dict(data_dict):
    """对齐日期"""
    common = None
    for t, df in data_dict.items():
        common = set(df.index) if common is None else common.intersection(set(df.index))
    if common is None:
        return data_dict, []
    common = sorted(list(common))
    for t in data_dict:
        data_dict[t] = data_dict[t].loc[data_dict[t].index.isin(common)]
    return data_dict, common


def build_rotation_data_dict(data_dict, rotation_tickers):
    """只对齐轮动标的的日期（DCA标的保留各自完整日期范围，让回测更早开始）"""
    common = None
    for t in rotation_tickers:
        if t in data_dict:
            common = set(data_dict[t].index) if common is None else common.intersection(set(data_dict[t].index))
    if common is None:
        return data_dict, []
    common = sorted(list(common))
    # 不裁剪DCA标的——保留完整日期范围，回测中按需检查
    for t in rotation_tickers:
        if t in data_dict:
            data_dict[t] = data_dict[t].loc[data_dict[t].index.isin(common)]
    return data_dict, common


def get_ticker_name(thscode, etf_config):
    for cfg in etf_config.values():
        if cfg['thscode'] == thscode:
            return cfg['name_cn']
    return thscode


# ========================================
#  信号计算
# ========================================
def calc_difv_signals(data_dict, tickers):
    sig = {}
    for t in tickers:
        if t not in data_dict:
            continue
        df = data_dict[t].copy()
        c = df['close']
        ema12 = c.ewm(span=12, adjust=False).mean()
        ema26 = c.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        prev_close = c.shift(1)
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - prev_close).abs(),
            (df['low'] - prev_close).abs()
        ], axis=1).max(axis=1)
        atr26 = tr.rolling(26).mean()
        df['difv'] = (dif / atr26 * 100).replace([np.inf, -np.inf], np.nan)
        df['ma5'] = c.rolling(5).mean()
        df['ma10'] = c.rolling(10).mean()
        df['ma20'] = c.rolling(20).mean()
        df['daily_return'] = c.pct_change()
        df['return_20'] = c.pct_change(20)
        df['dif'] = dif
        df['atr26'] = atr26
        sig[t] = df
    return sig


def calc_wdm_signals(data_dict, tickers, momentum_shift=12, momentum_smooth=3, boll_period=17, boll_std=2):
    sig = {}
    for t in tickers:
        if t not in data_dict:
            continue
        df = data_dict[t].copy()
        close = df['close']
        ref_avg = close.shift(momentum_shift).rolling(window=momentum_smooth).mean()
        df['momentum'] = close / ref_avg * 100 - 100
        df['upper_band'] = close.rolling(window=boll_period).mean() + boll_std * close.rolling(window=boll_period).std()
        df['ma17'] = close.rolling(window=boll_period).mean()
        sig[t] = df
    return sig


def calc_lof_signals(data_dict, tickers, momentum_window=20, penalty_score=8, penalty_days=3, penalty_threshold=-0.03):
    sig = {}
    for t in tickers:
        if t not in data_dict:
            continue
        df = data_dict[t].copy()
        close = df['close']
        df['ma20'] = close.rolling(window=momentum_window).mean()
        df['std20'] = close.rolling(window=momentum_window).std()
        df['return_20'] = close / close.shift(momentum_window) - 1
        df['daily_ret'] = close.pct_change()
        df['momentum_std'] = (close - df['ma20']) / df['std20']
        df['penalty'] = (df['daily_ret'] < penalty_threshold).rolling(window=penalty_days).max().fillna(0)
        df['penalized_momentum'] = df['momentum_std'] - df['penalty'] * penalty_score
        sig[t] = df
    return sig


def calc_rsrs_signals(data_dict, tickers, momentum_days=20, momentum_score_limit=7,
                      rsrs_strong=0.15, rsrs_medium=0.03, volume_ratio_limit=2):
    sig = {}
    for t in tickers:
        if t not in data_dict:
            continue
        df = data_dict[t].copy()
        close = df['close']
        n = len(df)
        df['ma5'] = close.rolling(5).mean()
        df['ma10'] = close.rolling(10).mean()
        df['ma20'] = close.rolling(20).mean()
        df['daily_return'] = close.pct_change()

        # ---- 动量得分: 向量化滚动加权回归 ----
        momentum_scores = np.full(n, np.nan)
        log_prices = np.log(close.values)
        x_vals = np.arange(momentum_days, dtype=float)
        weights = np.linspace(1, 2, momentum_days)
        w_mean = np.average(x_vals, weights=weights)
        w_std = np.sqrt(np.average((x_vals - w_mean) ** 2, weights=weights))
        w_x_centered = (x_vals - w_mean) / w_std if w_std > 0 else x_vals - w_mean

        for i in range(momentum_days - 1, n):
            y = log_prices[i - momentum_days + 1:i + 1]
            if np.any(np.isnan(y)) or np.any(np.isinf(y)):
                continue
            # 加权最小二乘: slope = sum(w * x_c * y_c) / sum(w * x_c^2)
            y_mean = np.average(y, weights=weights)
            y_centered = y - y_mean
            slope = np.sum(weights * w_x_centered * y_centered) / np.sum(weights * w_x_centered ** 2) / w_std if w_std > 0 else 0
            intercept = y_mean - slope * w_mean
            predicted = slope * x_vals + intercept
            ss_res = np.sum(weights * (y - predicted) ** 2)
            ss_tot = np.sum(weights * (y - y_mean) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            annualized_return = np.exp(slope * 250) - 1
            ms = annualized_return * r2
            # 连跌惩罚
            prices = close.values[i - momentum_days + 1:i + 1]
            if len(prices) >= 4:
                if min(prices[-1] / prices[-2], prices[-2] / prices[-3], prices[-3] / prices[-4]) < 0.95:
                    ms = -8
            momentum_scores[i] = ms
        df['momentum_score'] = momentum_scores

        # ---- RSRS强度: 滚动窗口计算斜率 ----
        rsrs_days = 18
        rsrs_window = 20
        lookback_days = 250

        # 预计算所有20日窗口的low->high回归斜率
        low_vals = df['low'].values
        high_vals = df['high'].values
        all_slopes = np.full(n, np.nan)
        for i in range(rsrs_window - 1, n):
            lv = low_vals[i - rsrs_window + 1:i + 1]
            hv = high_vals[i - rsrs_window + 1:i + 1]
            if np.std(lv) == 0 or np.std(hv) == 0:
                continue
            try:
                all_slopes[i] = np.polyfit(lv, hv, 1)[0]
            except:
                pass

        # 滚动均值/标准差计算RSRS强度
        rsrs_strengths = np.full(n, np.nan)
        rsrs_pass_list = np.zeros(n, dtype=bool)

        for i in range(n):
            if i < rsrs_days - 1:
                continue
            # 当前rsrs_days窗口的斜率
            cur_slope = all_slopes[i]
            if np.isnan(cur_slope):
                continue
            # lookback窗口内的斜率统计
            start_j = max(rsrs_window - 1, i - lookback_days + 1)
            slope_window = all_slopes[start_j:i + 1]
            valid_slopes = slope_window[~np.isnan(slope_window)]
            if len(valid_slopes) < 2:
                continue
            mean_slope = np.mean(valid_slopes)
            std_slope = np.std(valid_slopes)
            beta = mean_slope - 2 * std_slope
            strength = (cur_slope - beta) / abs(beta) if beta != 0 else 0
            rsrs_pass = cur_slope > beta
            rsrs_pass_list[i] = rsrs_pass
            if rsrs_pass:
                rsrs_strengths[i] = strength

        df['rsrs_strength'] = rsrs_strengths
        df['rsrs_pass'] = rsrs_pass_list

        # ---- MA条件 ----
        df['above_ma5'] = (close > df['ma5']).fillna(False)
        df['above_ma10'] = (close >= df['ma10']).fillna(False)
        df['above_ma20'] = (close > df['ma20']).fillna(False)

        # ---- 量比 ----
        vol = df['volume']
        vol_ma7 = vol.rolling(7).mean()
        vol_ratio = vol / vol_ma7
        df['volume_ratio'] = np.where(vol_ratio > volume_ratio_limit, vol_ratio, np.nan)

        # ---- 买入信号 ----
        ms = df['momentum_score']
        rsrs_p = df['rsrs_pass']
        rsrs_s = df['rsrs_strength']
        above5 = df['above_ma5']
        above10 = df['above_ma10']

        buy_signal = np.zeros(n, dtype=bool)
        for i in range(n):
            m = ms.iloc[i] if hasattr(ms, 'iloc') else ms[i]
            if np.isnan(m) or m <= 0 or m >= momentum_score_limit:
                continue
            vr = df['volume_ratio'].iloc[i] if hasattr(df['volume_ratio'], 'iloc') else df['volume_ratio'][i]
            if not np.isnan(vr):
                continue
            rp = rsrs_p.iloc[i] if hasattr(rsrs_p, 'iloc') else rsrs_p[i]
            rs = rsrs_s.iloc[i] if hasattr(rsrs_s, 'iloc') else rsrs_s[i]
            a5 = above5.iloc[i] if hasattr(above5, 'iloc') else above5[i]
            a10 = above10.iloc[i] if hasattr(above10, 'iloc') else above10[i]
            if rp and not np.isnan(rs) and rs > rsrs_strong:
                buy_signal[i] = True
            elif rp and not np.isnan(rs) and rs > rsrs_medium and a5:
                buy_signal[i] = True
            elif a10:
                buy_signal[i] = True
        df['buy_signal'] = buy_signal

        sig[t] = df
    return sig


# ========================================
#  全品类DIFv回测
# ========================================
def run_difv_backtest(data_dict, signals, stock_tickers, bond_ticker, all_tickers, dates,
                      initial_capital, start_date, max_holdings, position_pct, rebalance_days,
                      sell_rank_gt, sell_daily_drop, sell_return_20, buy_difv_max, buy_rank_lt,
                      ma_conditions, etf_config):
    if start_date:
        start_date = pd.Timestamp(start_date)
        dates = [d for d in dates if d >= start_date]
    if not dates:
        return None, None, None, None, None

    # 对齐起始
    valid_start = None
    for d in dates:
        ok = True
        for t in stock_tickers:
            if t in signals and d in signals[t].index:
                c = signals[t].loc[d, 'close']
                if pd.isna(c) or c <= 0:
                    ok = False
                    break
            else:
                ok = False
                break
        if ok:
            valid_start = d
            break
    if valid_start:
        dates = [d for d in dates if d >= valid_start]
    if not dates:
        return None, None, None, None, None

    cash = float(initial_capital)
    holdings = {}
    nav_history = []
    trade_log = []
    hold_history = []
    rebalance_dates = set([dates[i] for i in range(0, len(dates), rebalance_days)])

    for i, date in enumerate(dates):
        nav = cash
        for t, pos in holdings.items():
            c = signals[t].loc[date, 'close']
            nav += pos['shares'] * (c if c > 0 else 0)
        nav_history.append({'date': date, 'nav': nav})
        active = [t for t in holdings if t != bond_ticker]
        hold_history.append({'date': date, 'holdings': len(active), 'hold_tickers': active})

        if i + 1 >= len(dates):
            continue
        next_date = dates[i + 1]

        difv_values = {}
        for t in stock_tickers:
            v = signals[t].loc[date, 'difv']
            if pd.notna(v):
                difv_values[t] = v
        ranked = sorted(difv_values.items(), key=lambda x: x[1], reverse=True)
        rank_map = {t: idx + 1 for idx, (t, _) in enumerate(ranked)}

        # 卖出
        sell_list = []
        for t in list(holdings.keys()):
            if t == bond_ticker:
                continue
            if t not in signals or date not in signals[t].index:
                continue
            s = signals[t].loc[date]
            reason = None
            if t in rank_map and rank_map[t] > sell_rank_gt:
                reason = "排名>{}".format(sell_rank_gt)
            elif s['daily_return'] < -sell_daily_drop:
                reason = "日跌>{:.0f}%".format(sell_daily_drop * 100)
            elif pd.notna(s['return_20']) and s['return_20'] > sell_return_20:
                reason = "20日涨>{:.0f}%".format(sell_return_20 * 100)
            if reason:
                sell_list.append((t, reason))

        for t, reason in sell_list:
            if t not in holdings:
                continue
            o = signals[t].loc[next_date, 'open']
            if o <= 0:
                continue
            pos = holdings[t]
            sv = pos['shares'] * o
            fee = sv * FEE_RATE if t != bond_ticker else 0.0
            cash += (sv - fee)
            bp = pos['cost']
            pnl = (o - bp) / bp * 100 if bp > 0 else 0
            hd = (date - pos['buy_date']).days
            trade_log.append({
                'date': next_date, 'ticker': t, 'action': 'SELL', 'price': o,
                'shares': round(pos['shares']), 'value': round(sv), 'fee': round(fee, 2),
                'pnl_pct': round(pnl, 2), 'hold_days': hd, 'reason': reason,
                'name': get_ticker_name(t, etf_config)
            })
            del holdings[t]

        if date not in rebalance_dates:
            if cash > 1e-6 and bond_ticker in signals and next_date in signals[bond_ticker].index:
                o = signals[bond_ticker].loc[next_date, 'open']
                if o > 0:
                    if bond_ticker in holdings:
                        old = holdings[bond_ticker]
                        add = cash / o
                        old['shares'] += add
                        old['cost'] = (old['shares'] * old['cost'] + cash) / old['shares']
                    else:
                        holdings[bond_ticker] = {'shares': cash / o, 'cost': o, 'buy_date': next_date}
                    cash = 0.0
            continue

        target = [t for t in holdings if t != bond_ticker]
        candidates = []
        for t in stock_tickers:
            if t in target:
                continue
            if t not in signals or date not in signals[t].index:
                continue
            s = signals[t].loc[date]
            checks = []
            if ma_conditions.get('close_gt_ma20', True):
                checks.append(s['close'] > s['ma20'])
            if ma_conditions.get('close_gt_ma5', True):
                checks.append(s['close'] > s['ma5'])
            if ma_conditions.get('ma10_gt_ma20', True):
                checks.append(s['ma10'] > s['ma20'])
            if ma_conditions.get('ma5_gt_ma10', True):
                checks.append(s['ma5'] > s['ma10'])
            checks.append(pd.notna(s['difv']) and s['difv'] < buy_difv_max)
            checks.append(t in rank_map and rank_map[t] < buy_rank_lt)
            if all(checks):
                candidates.append((t, s['difv'], rank_map[t]))
        candidates.sort(key=lambda x: x[1], reverse=True)
        slots = max_holdings - len(target)
        for t, _, _ in candidates[:slots]:
            if t not in target:
                target.append(t)

        need_rebal = any(t not in holdings for t in target)

        if need_rebal:
            for t in list(holdings.keys()):
                if t in signals and next_date in signals[t].index:
                    p = signals[t].loc[next_date, 'open']
                    if p > 0:
                        cash += holdings[t]['shares'] * p
                del holdings[t]
            total = cash
            for t in target:
                tv = total * position_pct
                fee = tv * FEE_RATE
                o = signals[t].loc[next_date, 'open']
                if o <= 0:
                    continue
                sh = tv / o
                bv = sh * o
                cash -= (bv + fee)
                holdings[t] = {'shares': sh, 'cost': o, 'buy_date': next_date}
                trade_log.append({
                    'date': next_date, 'ticker': t, 'action': 'BUY', 'price': o,
                    'shares': round(sh), 'value': round(bv), 'fee': round(fee, 2),
                    'pnl_pct': 0, 'hold_days': 0, 'reason': '建仓/再平衡',
                    'name': get_ticker_name(t, etf_config)
                })
            if cash > 1e-6 and bond_ticker in signals and next_date in signals[bond_ticker].index:
                o = signals[bond_ticker].loc[next_date, 'open']
                if o > 0:
                    sh = cash / o
                    holdings[bond_ticker] = {'shares': sh, 'cost': o, 'buy_date': next_date}
                    cash = 0.0
        else:
            for t in list(holdings.keys()):
                if t != bond_ticker and t not in target:
                    o = signals[t].loc[next_date, 'open']
                    if o <= 0:
                        continue
                    sv = holdings[t]['shares'] * o
                    fee = sv * FEE_RATE
                    cash += (sv - fee)
                    trade_log.append({
                        'date': next_date, 'ticker': t, 'action': 'SELL', 'price': o,
                        'shares': round(holdings[t]['shares']), 'value': round(sv), 'fee': round(fee, 2),
                        'pnl_pct': round((o - holdings[t]['cost']) / holdings[t]['cost'] * 100, 2),
                        'hold_days': (next_date - holdings[t]['buy_date']).days, 'reason': '轮动调出',
                        'name': get_ticker_name(t, etf_config)
                    })
                    del holdings[t]
            if cash > 1e-6 and bond_ticker in signals and next_date in signals[bond_ticker].index:
                o = signals[bond_ticker].loc[next_date, 'open']
                if o > 0:
                    if bond_ticker in holdings:
                        old = holdings[bond_ticker]
                        add = cash / o
                        old['shares'] += add
                        old['cost'] = (old['shares'] * old['cost'] + cash) / old['shares']
                    else:
                        holdings[bond_ticker] = {'shares': cash / o, 'cost': o, 'buy_date': next_date}
                    cash = 0.0

    nav_df = pd.DataFrame(nav_history).set_index('date') if nav_history else None
    if nav_df is not None and len(nav_df) > 0 and nav_df['nav'].iloc[0] > 0:
        nav_df['nav'] = nav_df['nav'] / nav_df['nav'].iloc[0]
    trade_df = pd.DataFrame(trade_log) if trade_log else pd.DataFrame()
    hold_df = pd.DataFrame(hold_history).set_index('date') if hold_history else None

    return nav_df, trade_df, hold_df, holdings, cash


# ========================================
#  五斗米动量回测
# ========================================
def run_wdm_backtest(data_dict, signals, stock_tickers, dates, initial_capital, start_date, etf_config):
    if start_date:
        start_date = pd.Timestamp(start_date)
        dates = [d for d in dates if d >= start_date]
    if not dates:
        return None, None, None, None

    valid_start = None
    for d in dates:
        ok = True
        for t in stock_tickers:
            if t in signals and d in signals[t].index:
                c = signals[t].loc[d, 'close']
                if pd.isna(c) or c <= 0:
                    ok = False
                    break
            else:
                ok = False
                break
        if ok:
            valid_start = d
            break
    if valid_start:
        dates = [d for d in dates if d >= valid_start]
    if not dates:
        return None, None, None, None

    cash = float(initial_capital)
    nav_history = []
    trade_log = []
    hold_history = []
    current_holding = None
    buy_price = None
    buy_date = None
    shares = 0.0

    for i, date in enumerate(dates):
        nav = cash
        if current_holding and current_holding in signals:
            c = signals[current_holding].loc[date, 'close']
            nav += shares * (c if c > 0 else 0)
        nav_history.append({'date': date, 'nav': nav})
        active = [current_holding] if current_holding else []
        hold_history.append({'date': date, 'holdings': len(active), 'hold_tickers': active})

        if i + 1 >= len(dates):
            continue
        next_date = dates[i + 1]

        stock_metrics_list = []
        for t in stock_tickers:
            if t not in signals or date not in signals[t].index:
                continue
            s = signals[t].loc[date]
            if pd.isna(s['close']) or pd.isna(s.get('momentum', np.nan)) or pd.isna(s.get('upper_band', np.nan)):
                continue
            stock_metrics_list.append({
                'ticker': t, 'close': s['close'], 'momentum': s['momentum'],
                'upper_band': s['upper_band'], 'above_band': s['close'] > s['upper_band'],
            })

        if not stock_metrics_list:
            continue

        stock_metrics = pd.DataFrame(stock_metrics_list)
        stock_metrics = stock_metrics.sort_values('momentum', ascending=False).reset_index(drop=True)
        buy_candidates = stock_metrics[stock_metrics['above_band'] == True]
        buy_target = buy_candidates.iloc[0]['ticker'] if len(buy_candidates) > 0 else None

        h_momentum = None
        if current_holding:
            holding_row = stock_metrics[stock_metrics['ticker'] == current_holding]
            if len(holding_row) > 0:
                h_momentum = holding_row['momentum'].values[0]

        if current_holding and h_momentum is not None and h_momentum < 0:
            open_price = signals[current_holding].loc[next_date, 'open']
            if open_price > 0 and not pd.isna(open_price):
                sell_value = shares * open_price
                fee = sell_value * FEE_RATE
                cash += (sell_value - fee)
                pnl_pct = (open_price - buy_price) / buy_price * 100 if buy_price and buy_price > 0 else 0
                hold_days = (date - buy_date).days if buy_date else 0
                trade_log.append({
                    'date': next_date, 'ticker': current_holding, 'action': 'SELL',
                    'price': open_price, 'shares': round(shares), 'value': round(sell_value),
                    'fee': round(fee, 2), 'pnl_pct': round(pnl_pct, 2), 'hold_days': hold_days,
                    'reason': "持仓动量为负({:.2f})".format(h_momentum),
                    'name': get_ticker_name(current_holding, etf_config)
                })
                current_holding = None
                shares = 0.0
                buy_price = None
                buy_date = None

        elif current_holding and buy_target is not None and buy_target != current_holding:
            open_price = signals[current_holding].loc[next_date, 'open']
            if open_price > 0 and not pd.isna(open_price):
                sell_value = shares * open_price
                fee = sell_value * FEE_RATE
                cash += (sell_value - fee)
                pnl_pct = (open_price - buy_price) / buy_price * 100 if buy_price and buy_price > 0 else 0
                hold_days = (date - buy_date).days if buy_date else 0
                trade_log.append({
                    'date': next_date, 'ticker': current_holding, 'action': 'SELL',
                    'price': open_price, 'shares': round(shares), 'value': round(sell_value),
                    'fee': round(fee, 2), 'pnl_pct': round(pnl_pct, 2), 'hold_days': hold_days,
                    'reason': '轮动切换',
                    'name': get_ticker_name(current_holding, etf_config)
                })
                current_holding = buy_target
                open_price = signals[current_holding].loc[next_date, 'open']
                if open_price > 0 and not pd.isna(open_price):
                    buy_price = open_price
                    buy_date = next_date
                    shares = cash / open_price
                    buy_value = shares * open_price
                    fee = buy_value * FEE_RATE
                    cash -= (buy_value + fee)
                    trade_log.append({
                        'date': next_date, 'ticker': current_holding, 'action': 'BUY',
                        'price': open_price, 'shares': round(shares), 'value': round(buy_value),
                        'fee': round(fee, 2), 'pnl_pct': 0, 'hold_days': 0, 'reason': '轮动买入',
                        'name': get_ticker_name(current_holding, etf_config)
                    })
                else:
                    current_holding = None

        elif current_holding is None and buy_target is not None:
            current_holding = buy_target
            open_price = signals[current_holding].loc[next_date, 'open']
            if open_price > 0 and not pd.isna(open_price):
                buy_price = open_price
                buy_date = next_date
                shares = cash / open_price
                buy_value = shares * open_price
                fee = buy_value * FEE_RATE
                cash -= (buy_value + fee)
                trade_log.append({
                    'date': next_date, 'ticker': current_holding, 'action': 'BUY',
                    'price': open_price, 'shares': round(shares), 'value': round(buy_value),
                    'fee': round(fee, 2), 'pnl_pct': 0, 'hold_days': 0, 'reason': '建仓',
                    'name': get_ticker_name(current_holding, etf_config)
                })
            else:
                current_holding = None

    nav_df = pd.DataFrame(nav_history).set_index('date') if nav_history else None
    if nav_df is not None and len(nav_df) > 0 and nav_df['nav'].iloc[0] > 0:
        nav_df['nav'] = nav_df['nav'] / nav_df['nav'].iloc[0]
    trade_df = pd.DataFrame(trade_log) if trade_log else pd.DataFrame()
    hold_df = pd.DataFrame(hold_history).set_index('date') if hold_history else None
    return nav_df, trade_df, hold_df, current_holding


# ========================================
#  定投+轮动组合回测
# ========================================
def run_combo_backtest(data_dict, signals, stock_tickers, bond_ticker, all_rotation_tickers,
                       dca_config, dates, total_capital, start_date, dca_weekly_amount,
                       dca_tp, max_holdings, position_pct, rebalance_days,
                       sell_rank_gt, sell_daily_drop, sell_return_20, buy_difv_max, buy_rank_lt,
                       etf_config):
    if start_date:
        start_date = pd.Timestamp(start_date)
        dates = [d for d in dates if d >= start_date]
    if not dates:
        return None, None, None

    valid_start = None
    for d in dates:
        ok = True
        for t in stock_tickers:
            if t in signals and d in signals[t].index:
                c = signals[t].loc[d, 'close']
                if pd.isna(c) or c <= 0:
                    ok = False
                    break
            else:
                ok = False
                break
        if ok:
            valid_start = d
            break
    if valid_start:
        dates = [d for d in dates if d >= valid_start]
    if not dates:
        return None, None, None

    dca_holdings = {cfg['thscode']: [] for cfg in dca_config.values()}
    dca_total_injected = 0.0
    dca_tp_total = 0.0
    rot_cash = float(total_capital)
    rot_holdings = {}
    rebalance_dates = set([dates[i] for i in range(0, len(dates), rebalance_days)])
    dca_reserve = 20000.0
    nav_history = []
    trade_log = []

    for i, date in enumerate(dates):
        dca_holdings_value = 0.0
        for t, positions in dca_holdings.items():
            if t in data_dict and date in data_dict[t].index:
                price = data_dict[t].loc[date, 'close']
                if pd.notna(price) and price > 0:
                    dca_holdings_value += sum(pos['shares'] * price for pos in positions)
        dca_nav = dca_holdings_value + dca_tp_total

        rot_holdings_value = 0.0
        for t, pos in rot_holdings.items():
            if t in signals and date in signals[t].index:
                c = signals[t].loc[date, 'close']
                rot_holdings_value += pos['shares'] * (c if c > 0 else 0)
        rot_nav = rot_holdings_value + rot_cash
        total_nav = dca_holdings_value + rot_nav

        nav_history.append({'date': date, 'nav': total_nav, 'dca_nav': dca_nav, 'rot_nav': rot_nav})

        if i + 1 >= len(dates):
            continue
        next_date = dates[i + 1]

        # 定投（每周二）
        weekday = date.weekday()
        if weekday == 1:
            for cfg in dca_config.values():
                t = cfg['thscode']
                start_dt = pd.Timestamp(cfg.get('start_date', start_date))
                if date < start_dt:
                    continue
                if t not in data_dict or next_date not in data_dict[t].index:
                    continue
                buy_price = data_dict[t].loc[next_date, 'open']
                if pd.isna(buy_price) or buy_price <= 0:
                    continue
                amount = dca_weekly_amount
                if rot_cash >= amount:
                    rot_cash -= amount
                elif bond_ticker in rot_holdings and rot_holdings[bond_ticker]['shares'] > 0:
                    bond_price = data_dict[bond_ticker].loc[next_date, 'open'] if bond_ticker in data_dict and next_date in data_dict[bond_ticker].index else 0
                    if bond_price > 0:
                        need = amount - rot_cash
                        sell_shares = need / bond_price
                        avail = rot_holdings[bond_ticker]['shares']
                        actual_sell = min(sell_shares, avail)
                        rot_cash += actual_sell * bond_price
                        rot_holdings[bond_ticker]['shares'] -= actual_sell
                        if rot_holdings[bond_ticker]['shares'] < 1e-6:
                            del rot_holdings[bond_ticker]
                    if rot_cash >= amount:
                        rot_cash -= amount
                    else:
                        continue
                else:
                    continue

                sh = amount / buy_price
                dca_holdings[t].append({
                    'buy_date': next_date, 'shares': sh,
                    'cost': buy_price, 'amount': amount
                })
                dca_total_injected += amount
                trade_log.append({
                    'date': next_date, 'ticker': t, 'strategy': 'DCA',
                    'action': 'BUY', 'price': buy_price, 'shares': round(sh),
                    'value': amount, 'fee': 0, 'reason': '周定投',
                    'name': get_ticker_name(t, etf_config)
                })

        # 定投止盈
        for t in list(dca_holdings.keys()):
            if t not in data_dict or date not in data_dict[t].index:
                continue
            price = data_dict[t].loc[date, 'close']
            if pd.isna(price) or price <= 0:
                continue
            remaining = []
            for pos in dca_holdings[t]:
                ret = (price - pos['cost']) / pos['cost']
                if ret >= dca_tp:
                    sell_value = pos['shares'] * price
                    rot_cash += sell_value
                    dca_tp_total += sell_value
                    trade_log.append({
                        'date': date, 'ticker': t, 'strategy': 'DCA',
                        'action': 'TP_SELL', 'price': price, 'shares': round(pos['shares']),
                        'value': round(sell_value), 'fee': 0, 'reason': '止盈{:.0f}%'.format(ret * 100),
                        'name': get_ticker_name(t, etf_config)
                    })
                else:
                    remaining.append(pos)
            dca_holdings[t] = remaining

        # 轮动逻辑
        difv_values = {}
        for t in stock_tickers:
            if t in signals and date in signals[t].index:
                v = signals[t].loc[date, 'difv']
                if pd.notna(v):
                    difv_values[t] = v
        ranked = sorted(difv_values.items(), key=lambda x: x[1], reverse=True)
        rank_map = {t: idx + 1 for idx, (t, _) in enumerate(ranked)}

        sell_list = []
        for t in list(rot_holdings.keys()):
            if t == bond_ticker:
                continue
            if t not in signals or date not in signals[t].index:
                continue
            s = signals[t].loc[date]
            reason = None
            if t in rank_map and rank_map[t] > sell_rank_gt:
                reason = "排名>{}".format(sell_rank_gt)
            elif s['daily_return'] < -sell_daily_drop:
                reason = "日跌>{:.0f}%".format(sell_daily_drop * 100)
            elif pd.notna(s['return_20']) and s['return_20'] > sell_return_20:
                reason = "20日涨>{:.0f}%".format(sell_return_20 * 100)
            if reason:
                sell_list.append((t, reason))

        for t, reason in sell_list:
            if t not in rot_holdings:
                continue
            o = signals[t].loc[next_date, 'open'] if next_date in signals[t].index else 0
            if o <= 0:
                continue
            pos = rot_holdings[t]
            sv = pos['shares'] * o
            fee = sv * FEE_RATE
            rot_cash += (sv - fee)
            trade_log.append({
                'date': next_date, 'ticker': t, 'strategy': 'ROT',
                'action': 'SELL', 'price': o, 'shares': round(pos['shares']),
                'value': round(sv), 'fee': round(fee, 2), 'reason': reason,
                'name': get_ticker_name(t, etf_config)
            })
            del rot_holdings[t]

        if date not in rebalance_dates:
            if rot_cash > 1e-6 and bond_ticker in data_dict and next_date in data_dict[bond_ticker].index:
                o = data_dict[bond_ticker].loc[next_date, 'open']
                if o > 0:
                    if bond_ticker in rot_holdings:
                        old = rot_holdings[bond_ticker]
                        add = rot_cash / o
                        old['shares'] += add
                        old['cost'] = (old['shares'] * old['cost'] + rot_cash) / old['shares']
                    else:
                        rot_holdings[bond_ticker] = {'shares': rot_cash / o, 'cost': o, 'buy_date': next_date}
                    rot_cash = 0.0
            continue

        target = [t for t in rot_holdings if t != bond_ticker]
        candidates = []
        for t in stock_tickers:
            if t in target:
                continue
            if t not in signals or date not in signals[t].index:
                continue
            s = signals[t].loc[date]
            c1 = s['close'] > s['ma20']
            c2 = s['close'] > s['ma5']
            c3 = s['ma10'] > s['ma20']
            c4 = s['ma5'] > s['ma10']
            c5 = pd.notna(s['difv']) and s['difv'] < buy_difv_max
            c6 = t in rank_map and rank_map[t] < buy_rank_lt
            if c1 and c2 and c3 and c4 and c5 and c6:
                candidates.append((t, s['difv'], rank_map[t]))
        candidates.sort(key=lambda x: x[1], reverse=True)
        slots = max_holdings - len(target)
        for t, _, _ in candidates[:slots]:
            if t not in target:
                target.append(t)

        need_rebal = any(t not in rot_holdings for t in target)

        if need_rebal:
            for t in list(rot_holdings.keys()):
                if t in signals and next_date in signals[t].index:
                    p = signals[t].loc[next_date, 'open']
                    if p > 0:
                        rot_cash += rot_holdings[t]['shares'] * p
                elif t in data_dict and next_date in data_dict[t].index:
                    p = data_dict[t].loc[next_date, 'open']
                    if p > 0:
                        rot_cash += rot_holdings[t]['shares'] * p
                del rot_holdings[t]
            total = rot_cash
            available = total - dca_reserve
            if available < total * 0.1:
                available = total
            for t in target:
                tv = available * position_pct
                fee = tv * FEE_RATE
                if t not in signals or next_date not in signals[t].index:
                    continue
                o = signals[t].loc[next_date, 'open']
                if o <= 0:
                    continue
                sh = tv / o
                bv = sh * o
                rot_cash -= (bv + fee)
                rot_holdings[t] = {'shares': sh, 'cost': o, 'buy_date': next_date}
                trade_log.append({
                    'date': next_date, 'ticker': t, 'strategy': 'ROT',
                    'action': 'BUY', 'price': o, 'shares': round(sh),
                    'value': round(bv), 'fee': round(fee, 2), 'reason': '建仓/再平衡',
                    'name': get_ticker_name(t, etf_config)
                })
            if rot_cash > 1e-6 and bond_ticker in data_dict and next_date in data_dict[bond_ticker].index:
                o = data_dict[bond_ticker].loc[next_date, 'open']
                if o > 0:
                    rot_holdings[bond_ticker] = {'shares': rot_cash / o, 'cost': o, 'buy_date': next_date}
                    rot_cash = 0.0
        else:
            for t in list(rot_holdings.keys()):
                if t != bond_ticker and t not in target:
                    if t in signals and next_date in signals[t].index:
                        o = signals[t].loc[next_date, 'open']
                        if o <= 0:
                            continue
                        sv = rot_holdings[t]['shares'] * o
                        fee = sv * FEE_RATE
                        rot_cash += (sv - fee)
                        trade_log.append({
                            'date': next_date, 'ticker': t, 'strategy': 'ROT',
                            'action': 'SELL', 'price': o, 'shares': round(rot_holdings[t]['shares']),
                            'value': round(sv), 'fee': round(fee, 2), 'reason': '轮动调出',
                            'name': get_ticker_name(t, etf_config)
                        })
                    del rot_holdings[t]
            if rot_cash > 1e-6 and bond_ticker in data_dict and next_date in data_dict[bond_ticker].index:
                o = data_dict[bond_ticker].loc[next_date, 'open']
                if o > 0:
                    if bond_ticker in rot_holdings:
                        old = rot_holdings[bond_ticker]
                        add = rot_cash / o
                        old['shares'] += add
                    else:
                        rot_holdings[bond_ticker] = {'shares': rot_cash / o, 'cost': o, 'buy_date': next_date}
                    rot_cash = 0.0

    nav_df = pd.DataFrame(nav_history).set_index('date') if nav_history else None
    if nav_df is not None and len(nav_df) > 0 and nav_df['nav'].iloc[0] > 0:
        nav_df['nav'] = nav_df['nav'] / nav_df['nav'].iloc[0]
    trade_df = pd.DataFrame(trade_log) if trade_log else pd.DataFrame()
    return nav_df, trade_df, rot_holdings


# ========================================
#  懂懂定投回测
# ========================================
def run_dd_dca_backtest(data_dict, dca_config, dates, initial_capital, start_date,
                        dca_weekday, etf_config):
    if start_date:
        start_date = pd.Timestamp(start_date)
        dates = [d for d in dates if d >= start_date]
    if not dates:
        return None, pd.DataFrame()

    cash_pool = 0.0
    total_injected = 0.0
    holdings = {cfg['thscode']: [] for cfg in dca_config.values()}
    nav_history = []
    trade_log = []

    for i, date in enumerate(dates):
        weekday = date.weekday()
        # 周定投（指定周几买入）
        if weekday == dca_weekday:
            for code, cfg in dca_config.items():
                t = cfg['thscode']
                start_dt = pd.Timestamp(cfg.get('start_date', start_date))
                if date < start_dt:
                    continue
                if t not in data_dict or date not in data_dict[t].index:
                    continue
                price = data_dict[t].loc[date, 'close']
                if pd.isna(price) or price <= 0:
                    continue
                amount = cfg.get('amount', 1000)
                if cash_pool >= amount:
                    cash_pool -= amount
                else:
                    need = amount - cash_pool
                    total_injected += need
                    cash_pool = 0
                sh = amount / price
                holdings[t].append({'buy_date': date, 'shares': sh, 'cost': price, 'amount': amount})
                trade_log.append({
                    'date': date, 'ticker': t, 'action': 'BUY', 'price': price,
                    'shares': round(sh), 'value': amount, 'fee': 0, 'reason': '周定投',
                    'name': get_ticker_name(t, etf_config)
                })

        # 止盈检查
        for code, cfg in dca_config.items():
            t = cfg['thscode']
            tp = cfg.get('tp', 0.50)
            if t not in data_dict or date not in data_dict[t].index:
                continue
            price = data_dict[t].loc[date, 'close']
            if pd.isna(price) or price <= 0:
                continue
            remaining = []
            for pos in holdings[t]:
                ret = (price - pos['cost']) / pos['cost']
                if ret >= tp:
                    sv = pos['shares'] * price
                    cash_pool += sv
                    trade_log.append({
                        'date': date, 'ticker': t, 'action': 'TP_SELL', 'price': price,
                        'shares': round(pos['shares']), 'value': round(sv), 'fee': 0,
                        'reason': '止盈{:.0f}%'.format(ret * 100),
                        'name': get_ticker_name(t, etf_config)
                    })
                else:
                    remaining.append(pos)
            holdings[t] = remaining

        # 计算净值
        holdings_value = 0.0
        for t, positions in holdings.items():
            if t in data_dict and date in data_dict[t].index:
                price = data_dict[t].loc[date, 'close']
                if pd.notna(price) and price > 0:
                    holdings_value += sum(pos['shares'] * price for pos in positions)
        total_asset = holdings_value + cash_pool
        # 归一化NAV：总资产/总投入，投入为0时NAV=1.0
        nav_val = total_asset / total_injected if total_injected > 0 else 1.0
        nav_history.append({'date': date, 'nav': nav_val, 'injected': total_injected})

    nav_df = pd.DataFrame(nav_history).set_index('date') if nav_history else None
    trade_df = pd.DataFrame(trade_log) if trade_log else pd.DataFrame()
    return nav_df, trade_df


# ========================================
#  价值平均定投回测
# ========================================
def run_va_dca_backtest(data_dict, dca_config, dates, initial_capital, start_date,
                        dca_weekday, etf_config):
    if start_date:
        start_date = pd.Timestamp(start_date)
        dates = [d for d in dates if d >= start_date]
    if not dates:
        return None, pd.DataFrame()

    cash_pool = 0.0
    total_injected = 0.0
    ticker_shares = {cfg['thscode']: 0.0 for cfg in dca_config.values()}
    ticker_avg_cost = {cfg['thscode']: 0.0 for cfg in dca_config.values()}
    ticker_period_count = {cfg['thscode']: 0 for cfg in dca_config.values()}
    nav_history = []
    trade_log = []

    for i, date in enumerate(dates):
        weekday = date.weekday()
        # 价值平均调仓（指定周几）
        if weekday == dca_weekday:
            for code, cfg in dca_config.items():
                t = cfg['thscode']
                start_dt = pd.Timestamp(cfg.get('start_date', start_date))
                if date < start_dt:
                    continue
                if t not in data_dict or date not in data_dict[t].index:
                    continue
                price = data_dict[t].loc[date, 'close']
                if pd.isna(price) or price <= 0:
                    continue
                growth = cfg.get('growth', 1000)
                ticker_period_count[t] += 1
                target_value = growth * ticker_period_count[t]
                current_shares = ticker_shares.get(t, 0)
                current_value = current_shares * price
                diff = target_value - current_value

                if diff > 0:
                    if cash_pool >= diff:
                        cash_pool -= diff
                    else:
                        need = diff - cash_pool
                        total_injected += need
                        cash_pool = 0
                    buy_shares = diff / price
                    old_cost = ticker_avg_cost.get(t, 0) * current_shares
                    new_cost = old_cost + diff
                    ticker_shares[t] = current_shares + buy_shares
                    ticker_avg_cost[t] = new_cost / ticker_shares[t] if ticker_shares[t] > 0 else price
                    trade_log.append({
                        'date': date, 'ticker': t, 'action': 'BUY', 'price': price,
                        'shares': round(buy_shares), 'value': round(diff), 'fee': 0,
                        'reason': '价值平均买入', 'name': get_ticker_name(t, etf_config)
                    })
                elif diff < 0:
                    sell_amount = abs(diff)
                    sell_shares = sell_amount / price
                    if sell_shares > current_shares:
                        sell_shares = current_shares
                        sell_amount = sell_shares * price
                    ticker_shares[t] = current_shares - sell_shares
                    cash_pool += sell_amount
                    if ticker_shares[t] <= 0:
                        ticker_shares[t] = 0
                        ticker_avg_cost[t] = 0
                    trade_log.append({
                        'date': date, 'ticker': t, 'action': 'SELL', 'price': price,
                        'shares': round(sell_shares), 'value': round(sell_amount), 'fee': 0,
                        'reason': '价值平均卖出', 'name': get_ticker_name(t, etf_config)
                    })

        # 止盈检查
        for code, cfg in dca_config.items():
            t = cfg['thscode']
            tp = cfg.get('tp', 0.50)
            if t not in data_dict or date not in data_dict[t].index:
                continue
            price = data_dict[t].loc[date, 'close']
            if pd.isna(price) or price <= 0:
                continue
            current_shares = ticker_shares.get(t, 0)
            avg_cost = ticker_avg_cost.get(t, 0)
            if current_shares > 0 and avg_cost > 0:
                ret = (price - avg_cost) / avg_cost
                if ret >= tp:
                    sv = current_shares * price
                    cash_pool += sv
                    trade_log.append({
                        'date': date, 'ticker': t, 'action': 'TP_SELL', 'price': price,
                        'shares': round(current_shares), 'value': round(sv), 'fee': 0,
                        'reason': '止盈{:.0f}%'.format(ret * 100),
                        'name': get_ticker_name(t, etf_config)
                    })
                    ticker_shares[t] = 0
                    ticker_avg_cost[t] = 0
                    ticker_period_count[t] = 0

        # 计算净值
        holdings_value = sum(ticker_shares.get(t, 0) * data_dict[t].loc[date, 'close']
                             for t in ticker_shares
                             if t in data_dict and date in data_dict[t].index
                             and pd.notna(data_dict[t].loc[date, 'close']))
        total_asset = holdings_value + cash_pool
        # 归一化NAV：总资产/总投入，投入为0时NAV=1.0
        nav_val = total_asset / total_injected if total_injected > 0 else 1.0
        nav_history.append({'date': date, 'nav': nav_val, 'injected': total_injected})

    nav_df = pd.DataFrame(nav_history).set_index('date') if nav_history else None
    trade_df = pd.DataFrame(trade_log) if trade_log else pd.DataFrame()
    return nav_df, trade_df


# ========================================
#  LOF单标的轮动回测
# ========================================
def run_lof_backtest(data_dict, signals, stock_tickers, dates, initial_capital, start_date,
                     buy_min_return_20, buy_min_momentum, sell_return_20, rank_exit, etf_config):
    if start_date:
        start_date = pd.Timestamp(start_date)
        dates = [d for d in dates if d >= start_date]
    if not dates:
        return None, None, None, None

    valid_start = None
    for d in dates:
        ok = True
        for t in stock_tickers:
            if t in signals and d in signals[t].index:
                c = signals[t].loc[d, 'close']
                if pd.isna(c) or c <= 0:
                    ok = False
                    break
            else:
                ok = False
                break
        if ok:
            valid_start = d
            break
    if valid_start:
        dates = [d for d in dates if d >= valid_start]
    if not dates:
        return None, None, None, None

    cash = float(initial_capital)
    nav_history = []
    trade_log = []
    hold_history = []
    current_holding = None
    buy_price = None
    buy_date = None
    shares = 0.0

    for i, date in enumerate(dates):
        nav = cash
        if current_holding and current_holding in signals:
            c = signals[current_holding].loc[date, 'close']
            nav += shares * (c if c > 0 else 0)
        nav_history.append({'date': date, 'nav': nav})
        active = [current_holding] if current_holding else []
        hold_history.append({'date': date, 'holdings': len(active), 'hold_tickers': active})

        if i + 1 >= len(dates):
            continue
        next_date = dates[i + 1]

        # 计算排名
        stock_metrics_list = []
        for t in stock_tickers:
            if t not in signals or date not in signals[t].index:
                continue
            s = signals[t].loc[date]
            if pd.isna(s['close']) or pd.isna(s.get('ma20', np.nan)) or pd.isna(s.get('std20', np.nan)):
                continue
            raw_momentum = s.get('momentum_std', np.nan)
            penalized = s.get('penalized_momentum', np.nan)
            r20 = s.get('return_20', np.nan)
            if pd.isna(raw_momentum) or pd.isna(r20):
                continue
            stock_metrics_list.append({
                'ticker': t, 'close': s['close'],
                'raw_momentum': raw_momentum, 'penalized_momentum': penalized,
                'return_20': r20, 'penalty': int(s.get('penalty', 0))
            })

        if not stock_metrics_list:
            continue

        stock_metrics = pd.DataFrame(stock_metrics_list)
        stock_metrics = stock_metrics.sort_values('penalized_momentum', ascending=False).reset_index(drop=True)
        stock_metrics['rank'] = range(1, len(stock_metrics) + 1)

        buy_candidates = stock_metrics[
            (stock_metrics['return_20'] > buy_min_return_20) &
            (stock_metrics['raw_momentum'] > buy_min_momentum)
        ]
        target_ticker = buy_candidates.iloc[0]['ticker'] if len(buy_candidates) > 0 else None

        # 卖出检查
        need_sell = False
        sell_reason = ""
        if current_holding:
            holding_row = stock_metrics[stock_metrics['ticker'] == current_holding]
            if len(holding_row) > 0:
                h_return_20 = holding_row['return_20'].values[0]
                h_rank = holding_row['rank'].values[0]
                if h_return_20 < sell_return_20:
                    need_sell = True
                    sell_reason = "20日涨幅<{:.0f}%".format(sell_return_20 * 100)
                elif h_rank > rank_exit:
                    need_sell = True
                    sell_reason = "排名掉出前{}".format(rank_exit)
            else:
                need_sell = True
                sell_reason = "数据缺失"

        # T+1卖出
        if need_sell and current_holding:
            o = signals[current_holding].loc[next_date, 'open']
            if o > 0 and not pd.isna(o):
                sv = shares * o
                fee = sv * FEE_RATE
                cash += (sv - fee)
                pnl_pct = (o - buy_price) / buy_price * 100 if buy_price and buy_price > 0 else 0
                hd = (date - buy_date).days if buy_date else 0
                trade_log.append({
                    'date': next_date, 'ticker': current_holding, 'action': 'SELL', 'price': o,
                    'shares': round(shares), 'value': round(sv), 'fee': round(fee, 2),
                    'pnl_pct': round(pnl_pct, 2), 'hold_days': hd, 'reason': sell_reason,
                    'name': get_ticker_name(current_holding, etf_config)
                })
            current_holding = None
            shares = 0.0
            buy_price = None
            buy_date = None

        # T+1买入
        if current_holding is None and target_ticker is not None:
            current_holding = target_ticker
            o = signals[current_holding].loc[next_date, 'open']
            if o > 0 and not pd.isna(o):
                buy_price = o
                buy_date = next_date
                shares = cash / o
                bv = shares * o
                fee = bv * FEE_RATE
                cash -= (bv + fee)
                trade_log.append({
                    'date': next_date, 'ticker': current_holding, 'action': 'BUY', 'price': o,
                    'shares': round(shares), 'value': round(bv), 'fee': round(fee, 2),
                    'pnl_pct': 0, 'hold_days': 0, 'reason': '建仓',
                    'name': get_ticker_name(current_holding, etf_config)
                })
            else:
                current_holding = None
        elif current_holding and target_ticker is not None and target_ticker != current_holding and not need_sell:
            # 换仓
            o = signals[current_holding].loc[next_date, 'open']
            if o > 0 and not pd.isna(o):
                sv = shares * o
                fee = sv * FEE_RATE
                cash += (sv - fee)
                pnl_pct = (o - buy_price) / buy_price * 100 if buy_price and buy_price > 0 else 0
                hd = (date - buy_date).days if buy_date else 0
                trade_log.append({
                    'date': next_date, 'ticker': current_holding, 'action': 'SELL', 'price': o,
                    'shares': round(shares), 'value': round(sv), 'fee': round(fee, 2),
                    'pnl_pct': round(pnl_pct, 2), 'hold_days': hd, 'reason': '轮动切换',
                    'name': get_ticker_name(current_holding, etf_config)
                })
                current_holding = target_ticker
                o2 = signals[current_holding].loc[next_date, 'open']
                if o2 > 0 and not pd.isna(o2):
                    buy_price = o2
                    buy_date = next_date
                    shares = cash / o2
                    bv = shares * o2
                    fee = bv * FEE_RATE
                    cash -= (bv + fee)
                    trade_log.append({
                        'date': next_date, 'ticker': current_holding, 'action': 'BUY', 'price': o2,
                        'shares': round(shares), 'value': round(bv), 'fee': round(fee, 2),
                        'pnl_pct': 0, 'hold_days': 0, 'reason': '轮动买入',
                        'name': get_ticker_name(current_holding, etf_config)
                    })
                else:
                    current_holding = None

    nav_df = pd.DataFrame(nav_history).set_index('date') if nav_history else None
    if nav_df is not None and len(nav_df) > 0 and nav_df['nav'].iloc[0] > 0:
        nav_df['nav'] = nav_df['nav'] / nav_df['nav'].iloc[0]
    trade_df = pd.DataFrame(trade_log) if trade_log else pd.DataFrame()
    hold_df = pd.DataFrame(hold_history).set_index('date') if hold_history else None
    return nav_df, trade_df, hold_df, current_holding


# ========================================
#  科技成长DIFv回测（增量式多标的）
# ========================================
def run_tech_difv_backtest(data_dict, signals, stock_tickers, dates, initial_capital, start_date,
                           max_holdings, position_pct, buy_difv_max, etf_config):
    if start_date:
        start_date = pd.Timestamp(start_date)
        dates = [d for d in dates if d >= start_date]
    if not dates:
        return None, None, None, None, None

    cash = float(initial_capital)
    holdings = {}
    nav_history = []
    trade_log = []
    hold_history = []

    for i, date in enumerate(dates):
        nav = cash
        for t, pos in holdings.items():
            if t in signals and date in signals[t].index:
                c = signals[t].loc[date, 'close']
                nav += pos['shares'] * (c if c > 0 else 0)
        nav_history.append({'date': date, 'nav': nav})
        active = [t for t in holdings if t != BOND_TICKER]
        hold_history.append({'date': date, 'holdings': len(active), 'hold_tickers': active})

        if i + 1 >= len(dates):
            continue
        next_date = dates[i + 1]

        # DIFv排名
        difv_values = {}
        for t in stock_tickers:
            if t in signals and date in signals[t].index:
                v = signals[t].loc[date, 'difv']
                if pd.notna(v):
                    difv_values[t] = v
        ranked = sorted(difv_values.items(), key=lambda x: x[1], reverse=True)
        rank_map = {t: idx + 1 for idx, (t, _) in enumerate(ranked)}

        # 卖出：DIFv<0或排名最弱的超持仓
        current_stocks = [t for t in holdings if t != BOND_TICKER]
        sell_list = []
        for t in current_stocks:
            if t not in signals or date not in signals[t].index:
                continue
            s = signals[t].loc[date]
            if pd.notna(s['difv']) and s['difv'] < 0:
                sell_list.append((t, "DIFv<0"))

        # 增量式：如果有空位，买入新候选；如果满仓，卖最弱买最强
        candidates = []
        for t in stock_tickers:
            if t in holdings:
                continue
            if t not in signals or date not in signals[t].index:
                continue
            s = signals[t].loc[date]
            if pd.notna(s['difv']) and 0 < s['difv'] < buy_difv_max and s['close'] > s.get('ma5', s['close']):
                candidates.append((t, s['difv']))
        candidates.sort(key=lambda x: x[1], reverse=True)

        if len(current_stocks) < max_holdings:
            # 不满仓：卖出标记的+买入新候选
            slots = max_holdings - len(current_stocks) + len(sell_list)
            for t, _ in candidates[:slots]:
                if t not in [x[0] for x in sell_list]:
                    pass  # will buy
        elif candidates:
            # 满仓：卖最弱买最强
            if sell_list:
                pass  # 已有卖出
            else:
                weakest = min(current_stocks, key=lambda t: difv_values.get(t, -999))
                if candidates[0][1] > difv_values.get(weakest, -999):
                    sell_list.append((weakest, "被更强标的替换"))

        # 执行卖出
        for t, reason in sell_list:
            if t not in holdings:
                continue
            o = signals[t].loc[next_date, 'open']
            if o <= 0:
                continue
            pos = holdings[t]
            sv = pos['shares'] * o
            fee = sv * FEE_RATE
            cash += (sv - fee)
            bp = pos['cost']
            pnl = (o - bp) / bp * 100 if bp > 0 else 0
            hd = (date - pos['buy_date']).days
            trade_log.append({
                'date': next_date, 'ticker': t, 'action': 'SELL', 'price': o,
                'shares': round(pos['shares']), 'value': round(sv), 'fee': round(fee, 2),
                'pnl_pct': round(pnl, 2), 'hold_days': hd, 'reason': reason,
                'name': get_ticker_name(t, etf_config)
            })
            del holdings[t]

        # 执行买入
        current_stocks = [t for t in holdings if t != BOND_TICKER]
        slots = max_holdings - len(current_stocks)
        for t, _ in candidates[:slots]:
            if t in holdings:
                continue
            o = signals[t].loc[next_date, 'open']
            if o <= 0:
                continue
            tv = cash * position_pct if slots > 0 else cash
            fee = tv * FEE_RATE
            sh = tv / o
            bv = sh * o
            cash -= (bv + fee)
            holdings[t] = {'shares': sh, 'cost': o, 'buy_date': next_date}
            trade_log.append({
                'date': next_date, 'ticker': t, 'action': 'BUY', 'price': o,
                'shares': round(sh), 'value': round(bv), 'fee': round(fee, 2),
                'pnl_pct': 0, 'hold_days': 0, 'reason': '建仓',
                'name': get_ticker_name(t, etf_config)
            })

    nav_df = pd.DataFrame(nav_history).set_index('date') if nav_history else None
    if nav_df is not None and len(nav_df) > 0 and nav_df['nav'].iloc[0] > 0:
        nav_df['nav'] = nav_df['nav'] / nav_df['nav'].iloc[0]
    trade_df = pd.DataFrame(trade_log) if trade_log else pd.DataFrame()
    hold_df = pd.DataFrame(hold_history).set_index('date') if hold_history else None
    return nav_df, trade_df, hold_df, holdings, cash


# ========================================
#  DIFv动量轮动回测（增量式8标的）
# ========================================
def run_difv_mom_backtest(data_dict, signals, stock_tickers, dates, initial_capital, start_date,
                          max_holdings, position_pct, buy_difv_max, etf_config):
    # 与科技成长逻辑相同，参数不同
    return run_tech_difv_backtest(data_dict, signals, stock_tickers, dates, initial_capital, start_date,
                                  max_holdings, position_pct, buy_difv_max, etf_config)


# ========================================
#  RSRS动量轮动回测（单标的）
# ========================================
def run_rsrs_backtest(data_dict, signals, stock_tickers, dates, initial_capital, start_date,
                      stop_loss_limit, etf_config):
    if start_date:
        start_date = pd.Timestamp(start_date)
        dates = [d for d in dates if d >= start_date]
    if not dates:
        return None, None, None, None

    valid_start = None
    for d in dates:
        ok = True
        for t in stock_tickers:
            if t in signals and d in signals[t].index:
                c = signals[t].loc[d, 'close']
                if pd.isna(c) or c <= 0:
                    ok = False
                    break
            else:
                ok = False
                break
        if ok:
            valid_start = d
            break
    if valid_start:
        dates = [d for d in dates if d >= valid_start]
    if not dates:
        return None, None, None, None

    cash = float(initial_capital)
    nav_history = []
    trade_log = []
    hold_history = []
    current_holding = None
    shares = 0.0
    buy_price = 0.0
    buy_date = None

    def _check_buy(row):
        ms = row.get('momentum_score', np.nan)
        if pd.isna(ms) or ms <= 0 or ms >= 7:
            return False
        vr = row.get('volume_ratio', np.nan)
        if pd.notna(vr):
            return False
        rsrs_pass = row.get('rsrs_pass', False)
        strength = row.get('rsrs_strength', np.nan)
        above_ma5 = row.get('above_ma5', False)
        above_ma10 = row.get('above_ma10', False)
        if rsrs_pass and pd.notna(strength) and strength > 0.15:
            return True
        if rsrs_pass and pd.notna(strength) and strength > 0.03 and above_ma5:
            return True
        if above_ma10:
            return True
        return False

    for i, date in enumerate(dates):
        nav = cash
        if current_holding and current_holding in signals:
            c = signals[current_holding].loc[date, 'close']
            nav += shares * (c if c > 0 else 0)
        nav_history.append({'date': date, 'nav': nav})
        hold_tickers = [current_holding] if current_holding else []
        hold_history.append({'date': date, 'holdings': len(hold_tickers), 'hold_tickers': hold_tickers})

        if i + 1 >= len(dates):
            continue
        next_date = dates[i + 1]

        # 卖出检查
        should_sell = False
        sell_reason = ""
        if current_holding:
            if current_holding not in signals or date not in signals[current_holding].index:
                current_holding = None
                shares = 0
            else:
                s = signals[current_holding].loc[date]
                cur_close = s['close']
                if buy_price > 0:
                    pnl = (cur_close - buy_price) / buy_price
                    if pnl < stop_loss_limit:
                        should_sell = True
                        sell_reason = "相对买入价跌幅{:.1f}%".format(pnl * 100)
                if not should_sell:
                    if not _check_buy(s):
                        should_sell = True
                        sell_reason = "不满足买入条件"

        # 计算买入候选
        buy_candidates = []
        momentum_all = {}
        for t in stock_tickers:
            if t not in signals or date not in signals[t].index:
                continue
            s = signals[t].loc[date]
            ms = s.get('momentum_score', np.nan)
            if pd.notna(ms):
                momentum_all[t] = ms
                if _check_buy(s):
                    buy_candidates.append((t, ms))
        buy_candidates.sort(key=lambda x: x[1], reverse=True)
        best_candidate = buy_candidates[0] if buy_candidates else None

        # 执行交易
        if current_holding:
            if should_sell:
                o = signals[current_holding].loc[next_date, 'open']
                if o > 0:
                    sv = shares * o
                    fee = sv * FEE_RATE
                    cash += (sv - fee)
                    pnl = (o - buy_price) / buy_price * 100 if buy_price > 0 else 0
                    hd = (date - buy_date).days if buy_date else 0
                    trade_log.append({
                        'date': next_date, 'ticker': current_holding, 'action': 'SELL', 'price': o,
                        'shares': round(shares), 'value': round(sv), 'fee': round(fee, 2),
                        'pnl_pct': round(pnl, 2), 'hold_days': hd, 'reason': sell_reason,
                        'name': get_ticker_name(current_holding, etf_config)
                    })
                current_holding = None
                shares = 0
                buy_price = 0
                buy_date = None
                # 买入最优
                if best_candidate:
                    t = best_candidate[0]
                    o2 = signals[t].loc[next_date, 'open']
                    if o2 > 0 and cash > 0:
                        sh = cash / o2
                        bv = sh * o2
                        fee2 = bv * FEE_RATE
                        cash -= (bv + fee2)
                        current_holding = t
                        shares = sh
                        buy_price = o2
                        buy_date = next_date
                        trade_log.append({
                            'date': next_date, 'ticker': t, 'action': 'BUY', 'price': o2,
                            'shares': round(sh), 'value': round(bv), 'fee': round(fee2, 2),
                            'pnl_pct': 0, 'hold_days': 0, 'reason': '换仓买入',
                            'name': get_ticker_name(t, etf_config)
                        })
            else:
                if best_candidate and best_candidate[0] != current_holding:
                    # 换仓
                    o = signals[current_holding].loc[next_date, 'open']
                    if o > 0:
                        sv = shares * o
                        fee = sv * FEE_RATE
                        cash += (sv - fee)
                        pnl = (o - buy_price) / buy_price * 100 if buy_price > 0 else 0
                        hd = (date - buy_date).days if buy_date else 0
                        trade_log.append({
                            'date': next_date, 'ticker': current_holding, 'action': 'SELL', 'price': o,
                            'shares': round(shares), 'value': round(sv), 'fee': round(fee, 2),
                            'pnl_pct': round(pnl, 2), 'hold_days': hd, 'reason': '被更强标的替换',
                            'name': get_ticker_name(current_holding, etf_config)
                        })
                        best_t = best_candidate[0]
                        o2 = signals[best_t].loc[next_date, 'open']
                        if o2 > 0 and cash > 0:
                            sh = cash / o2
                            bv = sh * o2
                            fee2 = bv * FEE_RATE
                            cash -= (bv + fee2)
                            current_holding = best_t
                            shares = sh
                            buy_price = o2
                            buy_date = next_date
                            trade_log.append({
                                'date': next_date, 'ticker': best_t, 'action': 'BUY', 'price': o2,
                                'shares': round(sh), 'value': round(bv), 'fee': round(fee2, 2),
                                'pnl_pct': 0, 'hold_days': 0, 'reason': '换仓买入',
                                'name': get_ticker_name(best_t, etf_config)
                            })
        else:
            if best_candidate:
                t = best_candidate[0]
                o = signals[t].loc[next_date, 'open']
                if o > 0 and cash > 0:
                    sh = cash / o
                    bv = sh * o
                    fee = bv * FEE_RATE
                    cash -= (bv + fee)
                    current_holding = t
                    shares = sh
                    buy_price = o
                    buy_date = next_date
                    trade_log.append({
                        'date': next_date, 'ticker': t, 'action': 'BUY', 'price': o,
                        'shares': round(sh), 'value': round(bv), 'fee': round(fee, 2),
                        'pnl_pct': 0, 'hold_days': 0, 'reason': '建仓',
                        'name': get_ticker_name(t, etf_config)
                    })

    nav_df = pd.DataFrame(nav_history).set_index('date') if nav_history else None
    if nav_df is not None and len(nav_df) > 0 and nav_df['nav'].iloc[0] > 0:
        nav_df['nav'] = nav_df['nav'] / nav_df['nav'].iloc[0]
    trade_df = pd.DataFrame(trade_log) if trade_log else pd.DataFrame()
    hold_df = pd.DataFrame(hold_history).set_index('date') if hold_history else None
    return nav_df, trade_df, hold_df, current_holding


# ========================================
#  绩效计算
# ========================================
def compute_performance(nav_df, initial_capital):
    if nav_df is None or len(nav_df) == 0:
        return {}
    nav = nav_df['nav']
    # NAV已归一化（从1.0开始），直接计算收益
    if nav.iloc[0] == 0:
        return {}
    total_return = (nav.iloc[-1] / nav.iloc[0] - 1) * 100
    years = len(nav) / 252
    if years <= 0:
        years = 0.01
    annual_return = ((nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1) * 100

    dd_series = (nav / nav.cummax()) - 1
    max_dd = dd_series.min() * 100
    max_dd_date = str(dd_series.idxmin().date()) if hasattr(dd_series.idxmin(), 'date') else str(dd_series.idxmin())

    daily_ret = nav.pct_change().dropna()
    if len(daily_ret) > 0 and daily_ret.std() > 0:
        sharpe = (daily_ret.mean() * 252 - 0.03) / (daily_ret.std() * np.sqrt(252))
    else:
        sharpe = 0

    calmar = annual_return / abs(max_dd) if max_dd != 0 else 0

    start_d = str(nav_df.index[0].date()) if hasattr(nav_df.index[0], 'date') else str(nav_df.index[0])
    end_d = str(nav_df.index[-1].date()) if hasattr(nav_df.index[-1], 'date') else str(nav_df.index[-1])
    return {
        'total_return': round(total_return, 2),
        'annual_return': round(annual_return, 2),
        'max_dd': round(max_dd, 2),
        'max_dd_date': max_dd_date,
        'sharpe': round(sharpe, 2),
        'calmar': round(calmar, 2),
        'start_date': start_d,
        'end_date': end_d,
        'trading_days': len(nav),
    }


# ========================================
#  数据转换
# ========================================
def nav_df_to_list(nav_df, initial_capital):
    if nav_df is None:
        return []
    result = []
    for idx, row in nav_df.iterrows():
        d = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
        # NAV已归一化，直接显示
        result.append({'date': d, 'nav': round(float(row['nav']), 4)})
    return result


def compute_drawdown(nav_df):
    if nav_df is None:
        return []
    nav = nav_df['nav']
    dd = (nav / nav.cummax() - 1) * 100
    result = []
    for idx, val in dd.items():
        d = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
        result.append({'date': d, 'dd': round(val, 2)})
    return result


def compute_yearly_returns(nav_df):
    if nav_df is None:
        return []
    nav = nav_df['nav']
    yearly = nav.resample('YE').last()
    yearly_prev = nav.resample('YE').first()
    result = []
    for i in range(len(yearly)):
        if i == 0:
            first_val = nav.iloc[0]
            year_label = str(yearly.index[i].year)
            ret = (yearly.iloc[i] / first_val - 1) * 100
        else:
            year_label = str(yearly.index[i].year)
            ret = (yearly.iloc[i] / yearly_prev.iloc[i] - 1) * 100 if yearly_prev.iloc[i] > 0 else 0
        # max dd in year
        year_start = yearly.index[i].replace(month=1, day=1)
        year_end = yearly.index[i].replace(month=12, day=31)
        year_nav = nav[(nav.index >= year_start) & (nav.index <= year_end)]
        if len(year_nav) > 0:
            year_dd = (year_nav / year_nav.cummax() - 1).min() * 100
        else:
            year_dd = 0
        result.append({'year': year_label, 'return': round(ret, 2), 'max_dd': round(year_dd, 2)})
    return result


def compute_holdings_timeline(hold_df, etf_config):
    if hold_df is None:
        return []
    ticker_name_map = {}
    for cfg in etf_config.values():
        ticker_name_map[cfg['thscode']] = cfg['name_cn']

    result = []
    for idx, row in hold_df.iterrows():
        d = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
        tickers = row.get('hold_tickers', [])
        if isinstance(tickers, list):
            for t in tickers:
                name = ticker_name_map.get(t, t)
                result.append({'date': d, 'ticker': name, 'code': t})
    return result


# ========================================
#  获取可用pkl列表
# ========================================
def get_available_tickers():
    if not os.path.exists(PKL_DIR):
        return []
    result = []
    all_configs = {**ETF_CONFIG_DIFV, **ETF_CONFIG_WDM, **ETF_CONFIG_DCA,
                   **ETF_CONFIG_DD_DCA, **ETF_CONFIG_VA_DCA, **ETF_CONFIG_LOF,
                   **ETF_CONFIG_TECH_DIFV, **ETF_CONFIG_DIFV_MOM, **ETF_CONFIG_RSRS}
    for f in os.listdir(PKL_DIR):
        if f.endswith("_1d.pkl"):
            parts = f.replace("_1d.pkl", "").split("_")
            if len(parts) == 2:
                code, suffix = parts
                thscode = code + "." + suffix
                # 查找名称
                name = thscode
                for cfg in all_configs.values():
                    if cfg['thscode'] == thscode:
                        name = cfg['name_cn']
                        break
                result.append({'code': code, 'suffix': suffix, 'thscode': thscode, 'name': name})
    return result


# ========================================
#  API路由
# ========================================
@app.route('/')
def index():
    return Response(HTML_PAGE, mimetype='text/html')


@app.route('/api/strategies')
def api_strategies():
    strategies = [
        {
            'id': 'difv',
            'name': '全品类DIFv轮动',
            'desc': '多标的等权轮动，DIF/ATR动量排名，银华日利空仓替代',
            'params': {
                'start_date': '2020-03-12',
                'initial_capital': 1000000,
                'max_holdings': 5,
                'position_pct': 20,
                'rebalance_days': 2,
                'buy_difv_max': 120,
                'sell_rank_gt': 6,
                'sell_daily_drop': 3,
                'sell_return_20': 25,
                'ma_close_gt_ma20': True,
                'ma_close_gt_ma5': True,
                'ma_ma10_gt_ma20': True,
                'ma_ma5_gt_ma10': True,
            }
        },
        {
            'id': 'wdm',
            'name': '五斗米动量轮动',
            'desc': '单标的轮动，动量+布林带突破，空仓持现金',
            'params': {
                'start_date': '2020-03-01',
                'initial_capital': 1000000,
                'momentum_shift': 12,
                'boll_period': 17,
                'boll_std': 2,
            }
        },
        {
            'id': 'combo',
            'name': '定投+轮动组合',
            'desc': '定投5品种周投1万+全品类DIFv轮动，止盈50%回收',
            'params': {
                'start_date': '2020-03-12',
                'total_capital': 2500000,
                'dca_weekly_amount': 2000,
                'dca_tp': 0.50,
                'max_holdings': 5,
                'position_pct': 20,
                'rebalance_days': 2,
                'buy_difv_max': 120,
                'sell_rank_gt': 6,
                'sell_daily_drop': 3,
                'sell_return_20': 25,
            }
        },
        {
            'id': 'custom',
            'name': '自定义策略',
            'desc': '自选标的+参数，基于DIFv轮动逻辑',
            'params': {
                'start_date': '2020-03-12',
                'initial_capital': 1000000,
                'tickers': '510300,513100,518880,159949,512100',
                'max_holdings': 3,
                'position_pct': 33,
                'rebalance_days': 2,
                'buy_difv_max': 120,
                'sell_rank_gt': 6,
                'sell_daily_drop': 3,
                'sell_return_20': 25,
            }
        },
        {
            'id': 'dd_dca',
            'name': '懂懂定投',
            'desc': '5品种周定投，固定金额买入，单笔收益>=50%止盈',
            'params': {
                'start_date': '2020-12-21',
                'initial_capital': 0,
                'dca_weekday': 1,
            }
        },
        {
            'id': 'va_dca',
            'name': '价值平均定投',
            'desc': '5品种周调仓，目标市值线性增长，整体收益>=50%止盈重置',
            'params': {
                'start_date': '2020-12-21',
                'initial_capital': 0,
                'dca_weekday': 1,
            }
        },
        {
            'id': 'lof',
            'name': '精选LOF轮动',
            'desc': '5只LOF单标的轮动，20日涨幅+标准化动量+惩罚机制',
            'params': {
                'start_date': '2020-03-01',
                'initial_capital': 1000000,
                'buy_min_return_20': 5,
                'buy_min_momentum': 0,
                'sell_return_20': 0,
                'rank_exit': 1,
            }
        },
        {
            'id': 'tech_difv',
            'name': '科技成长DIFv轮动',
            'desc': '26只科技ETF增量式轮动，DIFv>0且<120，最大持仓10只',
            'params': {
                'start_date': '2024-02-08',
                'initial_capital': 1000000,
                'max_holdings': 10,
                'position_pct': 10,
                'buy_difv_max': 120,
            }
        },
        {
            'id': 'difv_mom',
            'name': 'DIFv动量轮动',
            'desc': '8只ETF增量式轮动，红利低波/通信/半导体/纳指等',
            'params': {
                'start_date': '2020-03-12',
                'initial_capital': 1000000,
                'max_holdings': 5,
                'position_pct': 20,
                'buy_difv_max': 120,
            }
        },
        {
            'id': 'rsrs',
            'name': 'RSRS动量轮动',
            'desc': '5只ETF单标的轮动，对数价格回归+RSRS强度标准化',
            'params': {
                'start_date': '2020-03-01',
                'initial_capital': 1000000,
                'stop_loss_limit': 3,
            }
        },
    ]
    return jsonify(strategies)


@app.route('/api/tickers')
def api_tickers():
    q = request.args.get('q', '')
    all_tickers = get_available_tickers()
    if q:
        q = q.lower()
        all_tickers = [t for t in all_tickers if q in t['code'].lower() or q in t['name'].lower()]
    return jsonify(all_tickers[:50])


@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    try:
        params = request.json
        strategy = params.get('strategy', 'difv')

        if strategy == 'difv':
            return run_difv_backtest_api(params)
        elif strategy == 'wdm':
            return run_wdm_backtest_api(params)
        elif strategy == 'combo':
            return run_combo_backtest_api(params)
        elif strategy == 'custom':
            return run_custom_backtest_api(params)
        elif strategy == 'dd_dca':
            return run_dd_dca_backtest_api(params)
        elif strategy == 'va_dca':
            return run_va_dca_backtest_api(params)
        elif strategy == 'lof':
            return run_lof_backtest_api(params)
        elif strategy == 'tech_difv':
            return run_tech_difv_backtest_api(params)
        elif strategy == 'difv_mom':
            return run_difv_mom_backtest_api(params)
        elif strategy == 'rsrs':
            return run_rsrs_backtest_api(params)
        else:
            return jsonify({'error': '未知策略'}), 400
    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


def run_difv_backtest_api(params):
    start_date = params.get('start_date', '2020-03-12')
    initial_capital = float(params.get('initial_capital', 1000000))
    max_holdings = int(params.get('max_holdings', 5))
    position_pct = float(params.get('position_pct', 20)) / 100
    rebalance_days = int(params.get('rebalance_days', 2))
    buy_difv_max = float(params.get('buy_difv_max', 120))
    sell_rank_gt = int(params.get('sell_rank_gt', 6))
    sell_daily_drop = float(params.get('sell_daily_drop', 3)) / 100
    sell_return_20 = float(params.get('sell_return_20', 25)) / 100
    ma_conditions = {
        'close_gt_ma20': params.get('ma_close_gt_ma20', True),
        'close_gt_ma5': params.get('ma_close_gt_ma5', True),
        'ma10_gt_ma20': params.get('ma_ma10_gt_ma20', True),
        'ma5_gt_ma10': params.get('ma_ma5_gt_ma10', True),
    }

    etf_config = ETF_CONFIG_DIFV
    stock_tickers = [v['thscode'] for k, v in etf_config.items() if v['thscode'] != BOND_TICKER]
    all_tickers = [v['thscode'] for v in etf_config.values()]

    data_dict = load_pkl_data(PKL_DIR, etf_config)
    if not data_dict:
        return jsonify({'error': '无法加载pkl数据，请检查数据目录'}), 500

    data_dict, common_dates = build_data_dict(data_dict)
    signals = calc_difv_signals(data_dict, all_tickers)

    nav_df, trade_df, hold_df, holdings, cash = run_difv_backtest(
        data_dict, signals, stock_tickers, BOND_TICKER, all_tickers, common_dates,
        initial_capital, start_date, max_holdings, position_pct, rebalance_days,
        sell_rank_gt, sell_daily_drop, sell_return_20, buy_difv_max, len(stock_tickers),
        ma_conditions, etf_config
    )

    perf = compute_performance(nav_df, initial_capital)
    nav_curve = nav_df_to_list(nav_df, initial_capital)
    drawdown = compute_drawdown(nav_df)
    yearly = compute_yearly_returns(nav_df)
    hold_timeline = compute_holdings_timeline(hold_df, etf_config)

    trades = []
    if not trade_df.empty:
        for _, row in trade_df.iterrows():
            trades.append({
                'date': row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                'ticker': row.get('ticker', ''),
                'name': row.get('name', ''),
                'action': row.get('action', ''),
                'price': row.get('price', 0),
                'shares': row.get('shares', 0),
                'value': row.get('value', 0),
                'fee': row.get('fee', 0),
                'reason': row.get('reason', ''),
            })

    # DIFv排名
    last_date = common_dates[-1] if common_dates else None
    rankings = []
    if last_date and signals:
        difv_values = {}
        for t in stock_tickers:
            if t in signals and last_date in signals[t].index:
                v = signals[t].loc[last_date, 'difv']
                if pd.notna(v):
                    difv_values[t] = v
        ranked = sorted(difv_values.items(), key=lambda x: x[1], reverse=True)
        for i, (t, v) in enumerate(ranked):
            rankings.append({
                'rank': i + 1, 'ticker': t,
                'name': get_ticker_name(t, etf_config),
                'difv': round(v, 2)
            })

    # 当前持仓
    current_holdings = []
    if holdings:
        for t, pos in holdings.items():
            current_holdings.append({
                'ticker': t,
                'name': get_ticker_name(t, etf_config),
                'shares': round(pos['shares']),
                'cost': round(pos['cost'], 4),
            })

    # 基准（沪深300）
    benchmark = []
    if '510300.SH' in data_dict:
        bm = data_dict['510300.SH']['close']
        bm = bm[bm.index >= pd.Timestamp(start_date)]
        if len(bm) > 0:
            base = bm.iloc[0]
            for idx, val in bm.items():
                d = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
                benchmark.append({'date': d, 'nav': round(val / base, 4)})

    return jsonify({
        'nav_curve': nav_curve,
        'benchmark': benchmark,
        'drawdown': drawdown,
        'performance': perf,
        'yearly_returns': yearly,
        'holdings_timeline': hold_timeline,
        'trades': trades,
        'current_holdings': current_holdings,
        'rankings': rankings,
    })


def run_wdm_backtest_api(params):
    start_date = params.get('start_date', '2020-03-01')
    initial_capital = float(params.get('initial_capital', 1000000))
    momentum_shift = int(params.get('momentum_shift', 12))
    boll_period = int(params.get('boll_period', 17))
    boll_std = float(params.get('boll_std', 2))

    etf_config = ETF_CONFIG_WDM
    stock_tickers = [v['thscode'] for v in etf_config.values()]

    data_dict = load_pkl_data(PKL_DIR, etf_config)
    if not data_dict:
        return jsonify({'error': '无法加载pkl数据'}), 500

    data_dict, common_dates = build_data_dict(data_dict)
    signals = calc_wdm_signals(data_dict, stock_tickers, momentum_shift, 3, boll_period, boll_std)

    nav_df, trade_df, hold_df, current_holding = run_wdm_backtest(
        data_dict, signals, stock_tickers, common_dates, initial_capital, start_date, etf_config
    )

    perf = compute_performance(nav_df, initial_capital)
    nav_curve = nav_df_to_list(nav_df, initial_capital)
    drawdown = compute_drawdown(nav_df)
    yearly = compute_yearly_returns(nav_df)
    hold_timeline = compute_holdings_timeline(hold_df, etf_config)

    trades = []
    if not trade_df.empty:
        for _, row in trade_df.iterrows():
            trades.append({
                'date': row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                'ticker': row.get('ticker', ''),
                'name': row.get('name', ''),
                'action': row.get('action', ''),
                'price': row.get('price', 0),
                'shares': row.get('shares', 0),
                'value': row.get('value', 0),
                'fee': row.get('fee', 0),
                'reason': row.get('reason', ''),
            })

    current_holdings = []
    if current_holding:
        current_holdings.append({
            'ticker': current_holding,
            'name': get_ticker_name(current_holding, etf_config),
        })

    # 动量排名
    last_date = common_dates[-1] if common_dates else None
    rankings = []
    if last_date and signals:
        mom_values = {}
        for t in stock_tickers:
            if t in signals and last_date in signals[t].index:
                v = signals[t].loc[last_date, 'momentum']
                if pd.notna(v):
                    mom_values[t] = v
        ranked = sorted(mom_values.items(), key=lambda x: x[1], reverse=True)
        for i, (t, v) in enumerate(ranked):
            rankings.append({
                'rank': i + 1, 'ticker': t,
                'name': get_ticker_name(t, etf_config),
                'momentum': round(v, 2)
            })

    benchmark = []
    if '510300.SH' in data_dict:
        bm = data_dict['510300.SH']['close']
        bm = bm[bm.index >= pd.Timestamp(start_date)]
        if len(bm) > 0:
            base = bm.iloc[0]
            for idx, val in bm.items():
                d = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
                benchmark.append({'date': d, 'nav': round(val / base, 4)})

    return jsonify({
        'nav_curve': nav_curve,
        'benchmark': benchmark,
        'drawdown': drawdown,
        'performance': perf,
        'yearly_returns': yearly,
        'holdings_timeline': hold_timeline,
        'trades': trades,
        'current_holdings': current_holdings,
        'rankings': rankings,
    })


def run_combo_backtest_api(params):
    start_date = params.get('start_date', '2020-03-12')
    total_capital = float(params.get('total_capital', 2500000))
    dca_weekly_amount = float(params.get('dca_weekly_amount', 2000))
    dca_tp = float(params.get('dca_tp', 0.50))
    max_holdings = int(params.get('max_holdings', 5))
    position_pct = float(params.get('position_pct', 20)) / 100
    rebalance_days = int(params.get('rebalance_days', 2))
    buy_difv_max = float(params.get('buy_difv_max', 120))
    sell_rank_gt = int(params.get('sell_rank_gt', 6))
    sell_daily_drop = float(params.get('sell_daily_drop', 3)) / 100
    sell_return_20 = float(params.get('sell_return_20', 25)) / 100

    # 合并配置
    etf_config = {}
    etf_config.update(ETF_CONFIG_DCA)
    etf_config.update(ETF_CONFIG_DIFV)
    # 去重
    seen = set()
    unique_config = {}
    for k, v in etf_config.items():
        if k not in seen:
            seen.add(k)
            unique_config[k] = v
    etf_config = unique_config

    # 修正159740的suffix
    if "159740" in etf_config:
        etf_config["159740"]["suffix"] = "SZ"
        etf_config["159740"]["thscode"] = "159740.SZ"

    stock_tickers = [v['thscode'] for k, v in ETF_CONFIG_DIFV.items() if v['thscode'] != BOND_TICKER]
    all_rotation_tickers = [v['thscode'] for v in ETF_CONFIG_DIFV.values()]

    data_dict = load_pkl_data(PKL_DIR, etf_config)
    if not data_dict:
        return jsonify({'error': '无法加载pkl数据'}), 500

    data_dict, common_dates = build_rotation_data_dict(data_dict, all_rotation_tickers)
    signals = calc_difv_signals(data_dict, all_rotation_tickers)

    # DCA配置
    dca_config = {}
    for code, cfg in ETF_CONFIG_DCA.items():
        dca_config[code] = {
            'thscode': cfg['thscode'],
            'amount': dca_weekly_amount,
            'tp': dca_tp,
            'start_date': cfg.get('start_date', start_date),
        }

    nav_df, trade_df, rot_holdings = run_combo_backtest(
        data_dict, signals, stock_tickers, BOND_TICKER, all_rotation_tickers,
        dca_config, common_dates, total_capital, start_date, dca_weekly_amount,
        dca_tp, max_holdings, position_pct, rebalance_days,
        sell_rank_gt, sell_daily_drop, sell_return_20, buy_difv_max, len(stock_tickers),
        etf_config
    )

    perf = compute_performance(nav_df, total_capital)
    nav_curve = nav_df_to_list(nav_df, total_capital)
    drawdown = compute_drawdown(nav_df)
    yearly = compute_yearly_returns(nav_df)

    trades = []
    if not trade_df.empty:
        for _, row in trade_df.iterrows():
            trades.append({
                'date': row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                'ticker': row.get('ticker', ''),
                'name': row.get('name', ''),
                'action': row.get('action', ''),
                'price': row.get('price', 0),
                'shares': row.get('shares', 0),
                'value': row.get('value', 0),
                'fee': row.get('fee', 0),
                'reason': row.get('reason', ''),
                'strategy': row.get('strategy', ''),
            })

    current_holdings = []
    if rot_holdings:
        for t, pos in rot_holdings.items():
            current_holdings.append({
                'ticker': t,
                'name': get_ticker_name(t, etf_config),
                'shares': round(pos['shares']),
                'strategy': 'ROT',
            })

    last_date = common_dates[-1] if common_dates else None
    rankings = []
    if last_date and signals:
        difv_values = {}
        for t in stock_tickers:
            if t in signals and last_date in signals[t].index:
                v = signals[t].loc[last_date, 'difv']
                if pd.notna(v):
                    difv_values[t] = v
        ranked = sorted(difv_values.items(), key=lambda x: x[1], reverse=True)
        for i, (t, v) in enumerate(ranked):
            rankings.append({
                'rank': i + 1, 'ticker': t,
                'name': get_ticker_name(t, etf_config),
                'difv': round(v, 2)
            })

    benchmark = []
    if '510300.SH' in data_dict:
        bm = data_dict['510300.SH']['close']
        bm = bm[bm.index >= pd.Timestamp(start_date)]
        if len(bm) > 0:
            base = bm.iloc[0]
            for idx, val in bm.items():
                d = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
                benchmark.append({'date': d, 'nav': round(val / base, 4)})

    return jsonify({
        'nav_curve': nav_curve,
        'benchmark': benchmark,
        'drawdown': drawdown,
        'performance': perf,
        'yearly_returns': yearly,
        'holdings_timeline': [],
        'trades': trades,
        'current_holdings': current_holdings,
        'rankings': rankings,
    })


def run_custom_backtest_api(params):
    start_date = params.get('start_date', '2020-03-12')
    initial_capital = float(params.get('initial_capital', 1000000))
    tickers_str = params.get('tickers', '510300,513100,518880,159949,512100')
    max_holdings = int(params.get('max_holdings', 3))
    position_pct = float(params.get('position_pct', 33)) / 100
    rebalance_days = int(params.get('rebalance_days', 2))
    buy_difv_max = float(params.get('buy_difv_max', 120))
    sell_rank_gt = int(params.get('sell_rank_gt', 6))
    sell_daily_drop = float(params.get('sell_daily_drop', 3)) / 100
    sell_return_20 = float(params.get('sell_return_20', 25)) / 100

    # 构建自定义配置
    ticker_codes = [t.strip() for t in tickers_str.split(',') if t.strip()]
    available = get_available_tickers()
    avail_map = {t['code']: t for t in available}

    etf_config = {}
    for code in ticker_codes:
        if code in avail_map:
            info = avail_map[code]
            etf_config[code] = {
                'suffix': info['suffix'],
                'thscode': info['thscode'],
                'name_cn': info['name'],
            }
        else:
            # 尝试推断
            suffix = 'SH' if code.startswith(('5', '6', '11')) else 'SZ'
            etf_config[code] = {
                'suffix': suffix,
                'thscode': code + '.' + suffix,
                'name_cn': code,
            }

    # 添加银华日利
    if '511880' not in etf_config:
        etf_config['511880'] = {'suffix': 'SH', 'thscode': '511880.SH', 'name_cn': '银华日利'}

    stock_tickers = [v['thscode'] for k, v in etf_config.items() if v['thscode'] != BOND_TICKER]
    all_tickers = [v['thscode'] for v in etf_config.values()]

    data_dict = load_pkl_data(PKL_DIR, etf_config)
    if not data_dict:
        return jsonify({'error': '无法加载pkl数据，请检查标的代码'}), 500

    data_dict, common_dates = build_data_dict(data_dict)
    signals = calc_difv_signals(data_dict, all_tickers)

    ma_conditions = {
        'close_gt_ma20': True,
        'close_gt_ma5': True,
        'ma10_gt_ma20': True,
        'ma5_gt_ma10': True,
    }

    nav_df, trade_df, hold_df, holdings, cash = run_difv_backtest(
        data_dict, signals, stock_tickers, BOND_TICKER, all_tickers, common_dates,
        initial_capital, start_date, max_holdings, position_pct, rebalance_days,
        sell_rank_gt, sell_daily_drop, sell_return_20, buy_difv_max, len(stock_tickers),
        ma_conditions, etf_config
    )

    perf = compute_performance(nav_df, initial_capital)
    nav_curve = nav_df_to_list(nav_df, initial_capital)
    drawdown = compute_drawdown(nav_df)
    yearly = compute_yearly_returns(nav_df)
    hold_timeline = compute_holdings_timeline(hold_df, etf_config)

    trades = []
    if not trade_df.empty:
        for _, row in trade_df.iterrows():
            trades.append({
                'date': row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                'ticker': row.get('ticker', ''),
                'name': row.get('name', ''),
                'action': row.get('action', ''),
                'price': row.get('price', 0),
                'shares': row.get('shares', 0),
                'value': row.get('value', 0),
                'fee': row.get('fee', 0),
                'reason': row.get('reason', ''),
            })

    current_holdings = []
    if holdings:
        for t, pos in holdings.items():
            current_holdings.append({
                'ticker': t,
                'name': get_ticker_name(t, etf_config),
                'shares': round(pos['shares']),
                'cost': round(pos['cost'], 4),
            })

    last_date = common_dates[-1] if common_dates else None
    rankings = []
    if last_date and signals:
        difv_values = {}
        for t in stock_tickers:
            if t in signals and last_date in signals[t].index:
                v = signals[t].loc[last_date, 'difv']
                if pd.notna(v):
                    difv_values[t] = v
        ranked = sorted(difv_values.items(), key=lambda x: x[1], reverse=True)
        for i, (t, v) in enumerate(ranked):
            rankings.append({
                'rank': i + 1, 'ticker': t,
                'name': get_ticker_name(t, etf_config),
                'difv': round(v, 2)
            })

    benchmark = []
    if '510300.SH' in data_dict:
        bm = data_dict['510300.SH']['close']
        bm = bm[bm.index >= pd.Timestamp(start_date)]
        if len(bm) > 0:
            base = bm.iloc[0]
            for idx, val in bm.items():
                d = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
                benchmark.append({'date': d, 'nav': round(val / base, 4)})

    return jsonify({
        'nav_curve': nav_curve,
        'benchmark': benchmark,
        'drawdown': drawdown,
        'performance': perf,
        'yearly_returns': yearly,
        'holdings_timeline': hold_timeline,
        'trades': trades,
        'current_holdings': current_holdings,
        'rankings': rankings,
    })


def _build_common_response(nav_df, trade_df, initial_capital, start_date, data_dict, etf_config, signals=None,
                           stock_tickers=None, rankings_key='difv', current_holdings_data=None,
                           hold_df=None, extra_rankings_fn=None):
    """通用响应构建器"""
    # NAV已归一化（从1.0开始），无需特殊处理injected
    perf = compute_performance(nav_df, initial_capital)
    nav_curve = nav_df_to_list(nav_df, initial_capital)
    drawdown = compute_drawdown(nav_df)
    yearly = compute_yearly_returns(nav_df)
    hold_timeline = compute_holdings_timeline(hold_df, etf_config) if hold_df is not None else []

    trades = []
    if not trade_df.empty:
        for _, row in trade_df.iterrows():
            d = row['date']
            d_str = d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)
            trades.append({
                'date': d_str, 'ticker': row.get('ticker', ''),
                'name': row.get('name', ''), 'action': row.get('action', ''),
                'price': row.get('price', 0), 'shares': row.get('shares', 0),
                'value': row.get('value', 0), 'fee': row.get('fee', 0),
                'reason': row.get('reason', ''), 'strategy': row.get('strategy', ''),
            })

    # 排名
    rankings = []
    if extra_rankings_fn:
        rankings = extra_rankings_fn()

    # 当前持仓
    current_holdings = current_holdings_data or []

    # 基准
    benchmark = []
    if '510300.SH' in data_dict:
        bm = data_dict['510300.SH']['close']
        bm = bm[bm.index >= pd.Timestamp(start_date)]
        if len(bm) > 0:
            base = bm.iloc[0]
            for idx, val in bm.items():
                d = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
                benchmark.append({'date': d, 'nav': round(val / base, 4)})

    return jsonify({
        'nav_curve': nav_curve, 'benchmark': benchmark, 'drawdown': drawdown,
        'performance': perf, 'yearly_returns': yearly, 'holdings_timeline': hold_timeline,
        'trades': trades, 'current_holdings': current_holdings, 'rankings': rankings,
    })


def run_dd_dca_backtest_api(params):
    start_date = params.get('start_date', '2020-12-21')
    dca_weekday = int(params.get('dca_weekday', 1))

    etf_config = ETF_CONFIG_DD_DCA
    dca_config = etf_config
    stock_tickers = [v['thscode'] for v in etf_config.values()]

    data_dict = load_pkl_data(PKL_DIR, etf_config)
    if not data_dict:
        return jsonify({'error': '无法加载pkl数据'}), 500

    data_dict, common_dates = build_data_dict(data_dict)

    nav_df, trade_df = run_dd_dca_backtest(
        data_dict, dca_config, common_dates, 0, start_date, dca_weekday, etf_config
    )

    return _build_common_response(nav_df, trade_df, 0, start_date, data_dict, etf_config,
                                  current_holdings_data=[], hold_df=None)


def run_va_dca_backtest_api(params):
    start_date = params.get('start_date', '2020-12-21')
    dca_weekday = int(params.get('dca_weekday', 1))

    etf_config = ETF_CONFIG_VA_DCA
    dca_config = etf_config
    stock_tickers = [v['thscode'] for v in etf_config.values()]

    data_dict = load_pkl_data(PKL_DIR, etf_config)
    if not data_dict:
        return jsonify({'error': '无法加载pkl数据'}), 500

    data_dict, common_dates = build_data_dict(data_dict)

    nav_df, trade_df = run_va_dca_backtest(
        data_dict, dca_config, common_dates, 0, start_date, dca_weekday, etf_config
    )

    return _build_common_response(nav_df, trade_df, 0, start_date, data_dict, etf_config,
                                  current_holdings_data=[], hold_df=None)


def run_lof_backtest_api(params):
    start_date = params.get('start_date', '2020-03-01')
    initial_capital = float(params.get('initial_capital', 1000000))
    buy_min_return_20 = float(params.get('buy_min_return_20', 5)) / 100
    buy_min_momentum = float(params.get('buy_min_momentum', 0))
    sell_return_20 = float(params.get('sell_return_20', 0)) / 100
    rank_exit = int(params.get('rank_exit', 1))

    etf_config = ETF_CONFIG_LOF
    stock_tickers = [v['thscode'] for v in etf_config.values()]

    data_dict = load_pkl_data(PKL_DIR, etf_config)
    if not data_dict:
        return jsonify({'error': '无法加载pkl数据'}), 500

    data_dict, common_dates = build_data_dict(data_dict)
    signals = calc_lof_signals(data_dict, stock_tickers)

    nav_df, trade_df, hold_df, current_holding = run_lof_backtest(
        data_dict, signals, stock_tickers, common_dates, initial_capital, start_date,
        buy_min_return_20, buy_min_momentum, sell_return_20, rank_exit, etf_config
    )

    current_holdings = []
    if current_holding:
        current_holdings.append({
            'ticker': current_holding,
            'name': get_ticker_name(current_holding, etf_config),
        })

    def _rankings():
        last_date = common_dates[-1] if common_dates else None
        if not last_date or not signals:
            return []
        mom_values = {}
        for t in stock_tickers:
            if t in signals and last_date in signals[t].index:
                v = signals[t].loc[last_date, 'penalized_momentum']
                if pd.notna(v):
                    mom_values[t] = v
        ranked = sorted(mom_values.items(), key=lambda x: x[1], reverse=True)
        return [{'rank': i + 1, 'ticker': t, 'name': get_ticker_name(t, etf_config),
                 'momentum': round(v, 2)} for i, (t, v) in enumerate(ranked)]

    return _build_common_response(nav_df, trade_df, initial_capital, start_date, data_dict, etf_config,
                                  current_holdings_data=current_holdings, hold_df=hold_df,
                                  extra_rankings_fn=_rankings)


def run_tech_difv_backtest_api(params):
    start_date = params.get('start_date', '2024-02-08')
    initial_capital = float(params.get('initial_capital', 1000000))
    max_holdings = int(params.get('max_holdings', 10))
    position_pct = float(params.get('position_pct', 10)) / 100
    buy_difv_max = float(params.get('buy_difv_max', 120))

    etf_config = ETF_CONFIG_TECH_DIFV
    stock_tickers = [v['thscode'] for v in etf_config.values()]

    data_dict = load_pkl_data(PKL_DIR, etf_config)
    if not data_dict:
        return jsonify({'error': '无法加载pkl数据'}), 500

    data_dict, common_dates = build_data_dict(data_dict)
    signals = calc_difv_signals(data_dict, stock_tickers)

    nav_df, trade_df, hold_df, holdings, cash = run_tech_difv_backtest(
        data_dict, signals, stock_tickers, common_dates, initial_capital, start_date,
        max_holdings, position_pct, buy_difv_max, etf_config
    )

    current_holdings = []
    if holdings:
        for t, pos in holdings.items():
            current_holdings.append({
                'ticker': t, 'name': get_ticker_name(t, etf_config),
                'shares': round(pos['shares']), 'cost': round(pos['cost'], 4),
            })

    def _rankings():
        last_date = common_dates[-1] if common_dates else None
        if not last_date or not signals:
            return []
        difv_values = {}
        for t in stock_tickers:
            if t in signals and last_date in signals[t].index:
                v = signals[t].loc[last_date, 'difv']
                if pd.notna(v):
                    difv_values[t] = v
        ranked = sorted(difv_values.items(), key=lambda x: x[1], reverse=True)
        return [{'rank': i + 1, 'ticker': t, 'name': get_ticker_name(t, etf_config),
                 'difv': round(v, 2)} for i, (t, v) in enumerate(ranked)]

    return _build_common_response(nav_df, trade_df, initial_capital, start_date, data_dict, etf_config,
                                  current_holdings_data=current_holdings, hold_df=hold_df,
                                  extra_rankings_fn=_rankings)


def run_difv_mom_backtest_api(params):
    start_date = params.get('start_date', '2020-03-12')
    initial_capital = float(params.get('initial_capital', 1000000))
    max_holdings = int(params.get('max_holdings', 5))
    position_pct = float(params.get('position_pct', 20)) / 100
    buy_difv_max = float(params.get('buy_difv_max', 120))

    etf_config = ETF_CONFIG_DIFV_MOM
    stock_tickers = [v['thscode'] for v in etf_config.values()]

    data_dict = load_pkl_data(PKL_DIR, etf_config)
    if not data_dict:
        return jsonify({'error': '无法加载pkl数据'}), 500

    data_dict, common_dates = build_data_dict(data_dict)
    signals = calc_difv_signals(data_dict, stock_tickers)

    nav_df, trade_df, hold_df, holdings, cash = run_difv_mom_backtest(
        data_dict, signals, stock_tickers, common_dates, initial_capital, start_date,
        max_holdings, position_pct, buy_difv_max, etf_config
    )

    current_holdings = []
    if holdings:
        for t, pos in holdings.items():
            current_holdings.append({
                'ticker': t, 'name': get_ticker_name(t, etf_config),
                'shares': round(pos['shares']), 'cost': round(pos['cost'], 4),
            })

    def _rankings():
        last_date = common_dates[-1] if common_dates else None
        if not last_date or not signals:
            return []
        difv_values = {}
        for t in stock_tickers:
            if t in signals and last_date in signals[t].index:
                v = signals[t].loc[last_date, 'difv']
                if pd.notna(v):
                    difv_values[t] = v
        ranked = sorted(difv_values.items(), key=lambda x: x[1], reverse=True)
        return [{'rank': i + 1, 'ticker': t, 'name': get_ticker_name(t, etf_config),
                 'difv': round(v, 2)} for i, (t, v) in enumerate(ranked)]

    return _build_common_response(nav_df, trade_df, initial_capital, start_date, data_dict, etf_config,
                                  current_holdings_data=current_holdings, hold_df=hold_df,
                                  extra_rankings_fn=_rankings)


def run_rsrs_backtest_api(params):
    start_date = params.get('start_date', '2020-03-01')
    initial_capital = float(params.get('initial_capital', 1000000))
    stop_loss_limit = float(params.get('stop_loss_limit', 3)) / 100

    etf_config = ETF_CONFIG_RSRS
    stock_tickers = [v['thscode'] for v in etf_config.values()]

    data_dict = load_pkl_data(PKL_DIR, etf_config)
    if not data_dict:
        return jsonify({'error': '无法加载pkl数据'}), 500

    data_dict, common_dates = build_data_dict(data_dict)
    signals = calc_rsrs_signals(data_dict, stock_tickers)

    nav_df, trade_df, hold_df, current_holding = run_rsrs_backtest(
        data_dict, signals, stock_tickers, common_dates, initial_capital, start_date,
        stop_loss_limit, etf_config
    )

    current_holdings = []
    if current_holding:
        current_holdings.append({
            'ticker': current_holding,
            'name': get_ticker_name(current_holding, etf_config),
        })

    def _rankings():
        last_date = common_dates[-1] if common_dates else None
        if not last_date or not signals:
            return []
        ms_values = {}
        for t in stock_tickers:
            if t in signals and last_date in signals[t].index:
                v = signals[t].loc[last_date, 'momentum_score']
                if pd.notna(v):
                    ms_values[t] = v
        ranked = sorted(ms_values.items(), key=lambda x: x[1], reverse=True)
        return [{'rank': i + 1, 'ticker': t, 'name': get_ticker_name(t, etf_config),
                 'momentum_score': round(v, 2)} for i, (t, v) in enumerate(ranked)]

    return _build_common_response(nav_df, trade_df, initial_capital, start_date, data_dict, etf_config,
                                  current_holdings_data=current_holdings, hold_df=hold_df,
                                  extra_rankings_fn=_rankings)


# ========================================
#  前端HTML
# ========================================
HTML_PAGE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ETF轮动策略回测系统</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#1a1a2e; color:#e0e0e0; font-family:'Microsoft YaHei','PingFang SC',sans-serif; display:flex; min-height:100vh; }
.sidebar { width:240px; background:#0f3460; padding:20px 16px; flex-shrink:0; display:flex; flex-direction:column; border-right:1px solid #1a3a6a; overflow-y:auto; }
.sidebar h2 { color:#00d2ff; font-size:18px; margin-bottom:20px; text-align:center; letter-spacing:2px; }
.sidebar .logo { text-align:center; margin-bottom:24px; }
.sidebar .logo span { font-size:28px; }
.strat-item { padding:12px 14px; margin-bottom:8px; border-radius:8px; cursor:pointer; background:#16213e; border:1px solid transparent; transition:all .2s; }
.strat-item:hover { border-color:#00d2ff; }
.strat-item.active { border-color:#00d2ff; background:#1a3a6a; box-shadow:0 0 12px rgba(0,210,255,.15); }
.strat-item .sname { font-weight:bold; font-size:14px; color:#00d2ff; margin-bottom:4px; }
.strat-item .sdesc { font-size:11px; color:#8899aa; line-height:1.4; }
.main { flex:1; overflow-y:auto; padding:20px 28px; }
.top-params { background:#16213e; border-radius:10px; padding:18px 22px; margin-bottom:20px; border:1px solid #1a3a6a; }
.top-params h3 { color:#00d2ff; margin-bottom:14px; font-size:15px; }
.param-grid { display:flex; flex-wrap:wrap; gap:12px 20px; align-items:end; }
.param-group { display:flex; flex-direction:column; gap:4px; }
.param-group label { font-size:11px; color:#8899aa; }
.param-group input, .param-group select { background:#0f3460; border:1px solid #1a3a6a; color:#e0e0e0; padding:6px 10px; border-radius:5px; font-size:13px; width:140px; }
.param-group input[type="checkbox"] { width:auto; }
.param-group .check-row { display:flex; align-items:center; gap:6px; }
.btn-run { background:linear-gradient(135deg,#00d2ff,#0078d4); color:#fff; border:none; padding:10px 32px; border-radius:8px; font-size:14px; font-weight:bold; cursor:pointer; transition:all .2s; letter-spacing:1px; }
.btn-run:hover { transform:scale(1.04); box-shadow:0 0 16px rgba(0,210,255,.3); }
.btn-run:disabled { opacity:.5; cursor:not-allowed; transform:none; }
.perf-cards { display:flex; gap:14px; margin-bottom:20px; flex-wrap:wrap; }
.perf-card { background:#16213e; border-radius:10px; padding:16px 22px; flex:1; min-width:140px; border:1px solid #1a3a6a; animation:fadeIn .5s; }
.perf-card .plabel { font-size:11px; color:#8899aa; margin-bottom:6px; }
.perf-card .pvalue { font-size:24px; font-weight:bold; }
.pos { color:#51cf8d; }
.neg { color:#ff6b6b; }
.chart-box { background:#16213e; border-radius:10px; padding:16px; margin-bottom:20px; border:1px solid #1a3a6a; }
.chart-box h3 { color:#00d2ff; margin-bottom:10px; font-size:14px; }
.chart-container { width:100%; height:420px; }
.chart-container-sm { width:100%; height:320px; }
.tables-row { display:flex; gap:20px; margin-bottom:20px; flex-wrap:wrap; }
.table-box { background:#16213e; border-radius:10px; padding:16px; flex:1; min-width:340px; border:1px solid #1a3a6a; animation:fadeIn .5s; }
.table-box h3 { color:#00d2ff; margin-bottom:10px; font-size:14px; }
table { width:100%; border-collapse:collapse; font-size:12px; }
th { background:#0f3460; color:#00d2ff; padding:8px 6px; text-align:left; position:sticky; top:0; }
td { padding:6px; border-bottom:1px solid #1a3a6a; }
tr:hover td { background:#1a3a6a; }
.tbl-scroll { max-height:320px; overflow-y:auto; }
.btn-csv { background:#0f3460; color:#00d2ff; border:1px solid #1a3a6a; padding:5px 14px; border-radius:5px; font-size:12px; cursor:pointer; margin-top:8px; }
.btn-csv:hover { background:#1a3a6a; }
.progress-bar { width:100%; height:4px; background:#0f3460; border-radius:2px; margin-bottom:16px; overflow:hidden; display:none; }
.progress-bar .fill { height:100%; background:linear-gradient(90deg,#00d2ff,#51cf8d); width:0%; transition:width .3s; animation:progAnim 2s infinite; }
@keyframes progAnim { 0%{width:0%} 50%{width:80%} 100%{width:100%} }
@keyframes fadeIn { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
.rank-pos { color:#51cf8d; }
.rank-neg { color:#ff6b6b; }
.filter-row { display:flex; gap:8px; margin-bottom:8px; }
.filter-row input, .filter-row select { background:#0f3460; border:1px solid #1a3a6a; color:#e0e0e0; padding:4px 8px; border-radius:4px; font-size:12px; }
</style>
</head>
<body>
<div class="sidebar">
  <div class="logo"><span>&#128200;</span></div>
  <h2>策略选择</h2>
  <div id="stratList"></div>
  <div style="margin-top:auto;padding-top:20px;font-size:10px;color:#556;text-align:center;">ETF轮动回测 v2.0</div>
</div>
<div class="main">
  <div class="top-params">
    <h3>&#9881; 参数配置</h3>
    <div class="param-grid" id="paramGrid"></div>
    <div style="margin-top:14px;display:flex;gap:12px;align-items:center;">
      <button class="btn-run" id="btnRun" onclick="runBacktest()">&#9654; 开始回测</button>
      <div class="progress-bar" id="progressBar"><div class="fill"></div></div>
    </div>
  </div>
  <div id="resultArea" style="display:none;">
    <div class="perf-cards" id="perfCards"></div>
    <div class="chart-box"><h3>&#128200; 净值曲线</h3><div id="navChart" class="chart-container"></div></div>
    <div class="chart-box"><h3>&#128201; 持仓时间线</h3><div id="holdChart" class="chart-container-sm"></div></div>
    <div class="tables-row">
      <div class="table-box"><h3>&#128197; 年度收益</h3><div class="tbl-scroll" id="yearlyTable"></div></div>
      <div class="table-box"><h3>&#127942; 排名/信号</h3><div class="tbl-scroll" id="rankTable"></div></div>
      <div class="table-box"><h3>&#128176; 当前持仓</h3><div class="tbl-scroll" id="holdingsTable"></div></div>
    </div>
    <div class="table-box">
      <h3>&#128221; 交易记录</h3>
      <div class="filter-row">
        <input type="text" id="tradeFilter" placeholder="筛选标的/操作..." oninput="filterTrades()">
        <select id="tradeActionFilter" onchange="filterTrades()">
          <option value="">全部操作</option><option value="BUY">买入</option><option value="SELL">卖出</option>
        </select>
        <button class="btn-csv" onclick="exportCSV()">&#128229; 导出CSV</button>
      </div>
      <div class="tbl-scroll" id="tradeTable"></div>
    </div>
  </div>
</div>

<script>
const STRATS = [
  {id:'difv', name:'全品类DIFv轮动', desc:'多标的等权轮动，DIF/ATR动量排名，银华日利空仓替代'},
  {id:'wdm', name:'五斗米动量轮动', desc:'单标的轮动，动量+布林带突破，空仓持现金'},
  {id:'combo', name:'定投+轮动组合', desc:'定投5品种周投1万+全品类DIFv轮动，止盈50%回收'},
  {id:'dd_dca', name:'懂懂定投', desc:'5品种周定投，固定金额买入，单笔收益>=50%止盈'},
  {id:'va_dca', name:'价值平均定投', desc:'5品种周调仓，目标市值线性增长，整体止盈50%重置'},
  {id:'lof', name:'精选LOF轮动', desc:'5只LOF单标的轮动，20日涨幅+标准化动量+惩罚机制'},
  {id:'tech_difv', name:'科技成长DIFv轮动', desc:'26只科技ETF增量式轮动，最大持仓10只'},
  {id:'difv_mom', name:'DIFv动量轮动', desc:'8只ETF增量式轮动，红利低波/通信/半导体/纳指等'},
  {id:'rsrs', name:'RSRS动量轮动', desc:'5只ETF单标的轮动，对数价格回归+RSRS强度'},
  {id:'custom', name:'自定义策略', desc:'自选标的+参数，基于DIFv轮动逻辑'},
];

let curStrat = 'difv';
let allTrades = [];
let navChartInst = null, holdChartInst = null;

function init() {
  const list = document.getElementById('stratList');
  list.innerHTML = STRATS.map(s => `<div class="strat-item${s.id===curStrat?' active':''}" data-id="${s.id}" onclick="selectStrat('${s.id}')"><div class="sname">${s.name}</div><div class="sdesc">${s.desc}</div></div>`).join('');
  renderParams();
}

function selectStrat(id) {
  curStrat = id;
  document.querySelectorAll('.strat-item').forEach(el => el.classList.toggle('active', el.dataset.id===id));
  renderParams();
  document.getElementById('resultArea').style.display = 'none';
}

function renderParams() {
  const g = document.getElementById('paramGrid');
  let h = '';
  h += pg('start_date','起始日期','2020-03-12','date');
  if(curStrat==='difv'||curStrat==='custom') {
    h += pg('initial_capital','初始资金','1000000','number');
    h += pg('max_holdings','最大持仓数','5','number');
    h += pg('position_pct','每只仓位%','20','number');
    h += pg('rebalance_days','轮动周期(天)','2','number');
    h += pg('buy_difv_max','DIFv买入上限','120','number');
    h += pg('sell_rank_gt','卖出排名>','6','number');
    h += pg('sell_daily_drop','日跌卖出%','3','number');
    h += pg('sell_return_20','20日涨幅卖出%','25','number');
  }
  if(curStrat==='difv') {
    h += `<div class="param-group"><label>均线条件</label><div class="check-row"><input type="checkbox" id="p_ma_close_gt_ma20" checked><label>close>ma20</label></div><div class="check-row"><input type="checkbox" id="p_ma_close_gt_ma5" checked><label>close>ma5</label></div><div class="check-row"><input type="checkbox" id="p_ma_ma10_gt_ma20" checked><label>ma10>ma20</label></div><div class="check-row"><input type="checkbox" id="p_ma_ma5_gt_ma10" checked><label>ma5>ma10</label></div></div>`;
  }
  if(curStrat==='wdm') {
    h += pg('initial_capital','初始资金','1000000','number');
    h += pg('momentum_shift','动量回看天数','12','number');
    h += pg('boll_period','布林带周期','17','number');
    h += pg('boll_std','布林带标准差','2','number');
  }
  if(curStrat==='combo') {
    h += pg('total_capital','总资金','2500000','number');
    h += pg('dca_weekly_amount','DCA周金额','2000','number');
    h += pg('dca_tp','DCA止盈%','0.5','number');
    h += pg('max_holdings','最大持仓数','5','number');
    h += pg('position_pct','每只仓位%','20','number');
    h += pg('rebalance_days','轮动周期(天)','2','number');
    h += pg('buy_difv_max','DIFv买入上限','120','number');
    h += pg('sell_rank_gt','卖出排名>','6','number');
    h += pg('sell_daily_drop','日跌卖出%','3','number');
    h += pg('sell_return_20','20日涨幅卖出%','25','number');
  }
  if(curStrat==='dd_dca') {
    h += pg('dca_weekday','定投日(0-4)','1','number');
  }
  if(curStrat==='va_dca') {
    h += pg('dca_weekday','定投日(0-4)','1','number');
  }
  if(curStrat==='lof') {
    h += pg('initial_capital','初始资金','1000000','number');
    h += pg('buy_min_return_20','20日涨幅买入%','5','number');
    h += pg('buy_min_momentum','动量买入下限','0','number');
    h += pg('sell_return_20','20日涨幅卖出%','0','number');
    h += pg('rank_exit','排名退出阈值','1','number');
  }
  if(curStrat==='tech_difv') {
    h += pg('initial_capital','初始资金','1000000','number');
    h += pg('max_holdings','最大持仓数','10','number');
    h += pg('position_pct','每只仓位%','10','number');
    h += pg('buy_difv_max','DIFv买入上限','120','number');
  }
  if(curStrat==='difv_mom') {
    h += pg('initial_capital','初始资金','1000000','number');
    h += pg('max_holdings','最大持仓数','5','number');
    h += pg('position_pct','每只仓位%','20','number');
    h += pg('buy_difv_max','DIFv买入上限','120','number');
  }
  if(curStrat==='rsrs') {
    h += pg('initial_capital','初始资金','1000000','number');
    h += pg('stop_loss_limit','止损线%','3','number');
  }
  if(curStrat==='custom') {
    h += `<div class="param-group" style="width:280px"><label>标的代码(逗号分隔)</label><input id="p_tickers" value="510300,513100,518880,159949,512100" style="width:260px"></div>`;
    h += pg('max_holdings','最大持仓数','3','number');
    h += pg('position_pct','每只仓位%','33','number');
    h += pg('rebalance_days','轮动周期(天)','2','number');
    h += pg('buy_difv_max','DIFv买入上限','120','number');
    h += pg('sell_rank_gt','卖出排名>','6','number');
    h += pg('sell_daily_drop','日跌卖出%','3','number');
    h += pg('sell_return_20','20日涨幅卖出%','25','number');
  }
  g.innerHTML = h;
}

function pg(id, label, def, type) {
  return `<div class="param-group"><label>${label}</label><input id="p_${id}" value="${def}" type="${type}"></div>`;
}

function getParams() {
  const v = id => { const el = document.getElementById('p_'+id); return el ? el.value : ''; };
  const n = id => parseFloat(v(id));
  const b = id => { const el = document.getElementById('p_'+id); return el ? el.checked : true; };
  const p = { strategy: curStrat, start_date: v('start_date') };
  if(curStrat==='difv') {
    p.initial_capital = n('initial_capital');
    p.max_holdings = n('max_holdings');
    p.position_pct = n('position_pct');
    p.rebalance_days = n('rebalance_days');
    p.buy_difv_max = n('buy_difv_max');
    p.sell_rank_gt = n('sell_rank_gt');
    p.sell_daily_drop = n('sell_daily_drop');
    p.sell_return_20 = n('sell_return_20');
    p.ma_close_gt_ma20 = b('ma_close_gt_ma20');
    p.ma_close_gt_ma5 = b('ma_close_gt_ma5');
    p.ma_ma10_gt_ma20 = b('ma_ma10_gt_ma20');
    p.ma_ma5_gt_ma10 = b('ma_ma5_gt_ma10');
  } else if(curStrat==='wdm') {
    p.initial_capital = n('initial_capital');
    p.momentum_shift = n('momentum_shift');
    p.boll_period = n('boll_period');
    p.boll_std = n('boll_std');
  } else if(curStrat==='combo') {
    p.total_capital = n('total_capital');
    p.dca_weekly_amount = n('dca_weekly_amount');
    p.dca_tp = n('dca_tp');
    p.max_holdings = n('max_holdings');
    p.position_pct = n('position_pct');
    p.rebalance_days = n('rebalance_days');
    p.buy_difv_max = n('buy_difv_max');
    p.sell_rank_gt = n('sell_rank_gt');
    p.sell_daily_drop = n('sell_daily_drop');
    p.sell_return_20 = n('sell_return_20');
  } else if(curStrat==='dd_dca') {
    p.dca_weekday = n('dca_weekday');
  } else if(curStrat==='va_dca') {
    p.dca_weekday = n('dca_weekday');
  } else if(curStrat==='lof') {
    p.initial_capital = n('initial_capital');
    p.buy_min_return_20 = n('buy_min_return_20');
    p.buy_min_momentum = n('buy_min_momentum');
    p.sell_return_20 = n('sell_return_20');
    p.rank_exit = n('rank_exit');
  } else if(curStrat==='tech_difv') {
    p.initial_capital = n('initial_capital');
    p.max_holdings = n('max_holdings');
    p.position_pct = n('position_pct');
    p.buy_difv_max = n('buy_difv_max');
  } else if(curStrat==='difv_mom') {
    p.initial_capital = n('initial_capital');
    p.max_holdings = n('max_holdings');
    p.position_pct = n('position_pct');
    p.buy_difv_max = n('buy_difv_max');
  } else if(curStrat==='rsrs') {
    p.initial_capital = n('initial_capital');
    p.stop_loss_limit = n('stop_loss_limit');
  } else if(curStrat==='custom') {
    p.initial_capital = n('initial_capital');
    p.tickers = v('tickers');
    p.max_holdings = n('max_holdings');
    p.position_pct = n('position_pct');
    p.rebalance_days = n('rebalance_days');
    p.buy_difv_max = n('buy_difv_max');
    p.sell_rank_gt = n('sell_rank_gt');
    p.sell_daily_drop = n('sell_daily_drop');
    p.sell_return_20 = n('sell_return_20');
  }
  return p;
}

async function runBacktest() {
  const btn = document.getElementById('btnRun');
  const prog = document.getElementById('progressBar');
  btn.disabled = true;
  prog.style.display = 'block';
  try {
    const resp = await fetch('/api/backtest', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(getParams())
    });
    const data = await resp.json();
    if(data.error) { alert('回测错误: '+data.error); return; }
    renderResult(data);
  } catch(e) {
    alert('请求失败: '+e.message);
  } finally {
    btn.disabled = false;
    prog.style.display = 'none';
  }
}

function renderResult(d) {
  document.getElementById('resultArea').style.display = 'block';
  // 绩效卡片
  const perf = d.performance || {};
  const cards = [
    {label:'总收益率', value:(perf.total_return||0).toFixed(2)+'%', cls:perf.total_return>=0?'pos':'neg'},
    {label:'年化收益率', value:(perf.annual_return||0).toFixed(2)+'%', cls:perf.annual_return>=0?'pos':'neg'},
    {label:'最大回撤', value:(perf.max_dd||0).toFixed(2)+'%', cls:'neg'},
    {label:'夏普比率', value:(perf.sharpe||0).toFixed(2), cls:perf.sharpe>=0?'pos':'neg'},
    {label:'卡尔玛比率', value:(perf.calmar||0).toFixed(2), cls:perf.calmar>=0?'pos':'neg'},
  ];
  document.getElementById('perfCards').innerHTML = cards.map(c => `<div class="perf-card"><div class="plabel">${c.label}</div><div class="pvalue ${c.cls}">${c.value}</div></div>`).join('');

  // 净值曲线
  renderNavChart(d);
  // 持仓时间线
  renderHoldChart(d);
  // 年度收益
  renderYearlyTable(d.yearly_returns||[]);
  // 排名
  renderRankTable(d.rankings||[]);
  // 当前持仓
  renderHoldingsTable(d.current_holdings||[]);
  // 交易记录
  allTrades = d.trades||[];
  renderTradeTable(allTrades);
}

function renderNavChart(d) {
  const el = document.getElementById('navChart');
  if(navChartInst) navChartInst.dispose();
  navChartInst = echarts.init(el, null, {renderer:'canvas'});

  const navData = (d.nav_curve||[]).map(p=>[p.date,p.nav]);
  const bmData = (d.benchmark||[]).map(p=>[p.date,p.nav]);
  const ddData = (d.drawdown||[]).map(p=>[p.date,p.dd]);

  const option = {
    backgroundColor:'#16213e',
    tooltip:{trigger:'axis',backgroundColor:'#0f3460',borderColor:'#1a3a6a',textStyle:{color:'#e0e0e0'}},
    legend:{data:['策略净值','沪深300','回撤'],textStyle:{color:'#8899aa'},top:5},
    grid:[{left:60,right:60,top:40,height:'55%'},{left:60,right:60,top:'70%',height:'22%'}],
    xAxis:[{type:'category',data:navData.map(p=>p[0]),gridIndex:0,axisLine:{lineStyle:{color:'#1a3a6a'}},axisLabel:{color:'#8899aa',fontSize:10}},{type:'category',data:ddData.map(p=>p[0]),gridIndex:1,axisLine:{lineStyle:{color:'#1a3a6a'}},axisLabel:{color:'#8899aa',fontSize:10}}],
    yAxis:[{type:'value',gridIndex:0,scale:true,axisLine:{lineStyle:{color:'#1a3a6a'}},axisLabel:{color:'#8899aa'},splitLine:{lineStyle:{color:'#1a3a6a'}}},{type:'value',gridIndex:1,axisLine:{lineStyle:{color:'#1a3a6a'}},axisLabel:{color:'#8899aa',formatter:'{value}%'},splitLine:{lineStyle:{color:'#1a3a6a'}}}],
    series:[
      {name:'策略净值',type:'line',xAxisIndex:0,yAxisIndex:0,data:navData.map(p=>p[1]),lineStyle:{color:'#00d2ff',width:2},showSymbol:false},
      {name:'沪深300',type:'line',xAxisIndex:0,yAxisIndex:0,data:bmData.map(p=>p[1]),lineStyle:{color:'#ff9800',width:1,type:'dashed'},showSymbol:false},
      {name:'回撤',type:'bar',xAxisIndex:1,yAxisIndex:1,data:ddData.map(p=>p[1]),itemStyle:{color:function(p){return p.value<0?'#ff6b6b':'#51cf8d'}},barWidth:'100%'}
    ],
    dataZoom:[{type:'inside',xAxisIndex:[0,1]},{type:'slider',xAxisIndex:[0,1],bottom:5,borderColor:'#1a3a6a',backgroundColor:'#0f3460',fillerColor:'#1a3a6a'}],
  };
  navChartInst.setOption(option);
}

function renderHoldChart(d) {
  const el = document.getElementById('holdChart');
  if(holdChartInst) holdChartInst.dispose();
  holdChartInst = echarts.init(el, null, {renderer:'canvas'});

  const tl = d.holdings_timeline||[];
  if(!tl.length) {
    holdChartInst.setOption({backgroundColor:'#16213e',title:{text:'暂无持仓数据',left:'center',top:'center',textStyle:{color:'#8899aa'}}});
    return;
  }

  // 构建散点图
  const tickers = [...new Set(tl.map(p=>p.ticker))];
  const buyTrades = (d.trades||[]).filter(t=>t.action==='BUY');
  const sellTrades = (d.trades||[]).filter(t=>t.action.includes('SELL'));

  const scatterData = tl.map(p => [p.date, tickers.indexOf(p.ticker), 1]);
  const buyPts = buyTrades.map(t => {
    const dt = t.date;
    const idx = tickers.indexOf(t.name||t.ticker);
    return idx>=0?[dt,idx]:null;
  }).filter(Boolean);
  const sellPts = sellTrades.map(t => {
    const dt = t.date;
    const idx = tickers.indexOf(t.name||t.ticker);
    return idx>=0?[dt,idx]:null;
  }).filter(Boolean);

  const option = {
    backgroundColor:'#16213e',
    tooltip:{trigger:'item',backgroundColor:'#0f3460',textStyle:{color:'#e0e0e0'},formatter:function(p){return p.value[0]+'<br/>'+tickers[p.value[1]]}},
    grid:{left:80,right:20,top:10,bottom:30},
    xAxis:{type:'category',data:[...new Set(tl.map(p=>p.date))],axisLabel:{color:'#8899aa',fontSize:9,interval:Math.floor(tl.length/tickers.length/8)},axisLine:{lineStyle:{color:'#1a3a6a'}}},
    yAxis:{type:'category',data:tickers,axisLabel:{color:'#8899aa',fontSize:10},axisLine:{lineStyle:{color:'#1a3a6a'}}},
    series:[
      {type:'scatter',symbolSize:6,data:scatterData,itemStyle:{color:'#00d2ff',opacity:0.4}},
      {type:'scatter',symbolSize:10,symbol:'circle',data:buyPts,itemStyle:{color:'#51cf8d'},name:'买入'},
      {type:'scatter',symbolSize:10,symbol:'diamond',data:sellPts,itemStyle:{color:'#ff6b6b'},name:'卖出'},
    ]
  };
  holdChartInst.setOption(option);
}

function renderYearlyTable(data) {
  if(!data.length) { document.getElementById('yearlyTable').innerHTML='<p style="color:#8899aa;padding:8px">暂无数据</p>'; return; }
  let h = '<table><tr><th>年度</th><th>收益率</th><th>最大回撤</th></tr>';
  data.forEach(r => {
    const rc = r.return>=0?'pos':'neg';
    h += `<tr><td>${r.year}</td><td class="${rc}">${r.return.toFixed(2)}%</td><td class="neg">${r.max_dd.toFixed(2)}%</td></tr>`;
  });
  h += '</table>';
  document.getElementById('yearlyTable').innerHTML = h;
}

function renderRankTable(data) {
  if(!data.length) { document.getElementById('rankTable').innerHTML='<p style="color:#8899aa;padding:8px">暂无数据</p>'; return; }
  const key = data[0].difv!==undefined ? 'difv' : (data[0].momentum_score!==undefined ? 'momentum_score' : 'momentum');
  const keyName = key==='difv' ? 'DIFv' : (key==='momentum_score' ? '动量得分' : '动量');
  let h = `<table><tr><th>排名</th><th>名称</th><th>${keyName}</th></tr>`;
  data.forEach(r => {
    const val = r[key];
    const cls = val>=0?'rank-pos':'rank-neg';
    h += `<tr><td>${r.rank}</td><td>${r.name}</td><td class="${cls}">${val.toFixed(2)}</td></tr>`;
  });
  h += '</table>';
  document.getElementById('rankTable').innerHTML = h;
}

function renderHoldingsTable(data) {
  if(!data.length) { document.getElementById('holdingsTable').innerHTML='<p style="color:#8899aa;padding:8px">空仓/银华日利</p>'; return; }
  let h = '<table><tr><th>标的</th><th>名称</th><th>股数</th></tr>';
  data.forEach(r => {
    h += `<tr><td>${r.ticker}</td><td>${r.name}</td><td>${r.shares||'-'}</td></tr>`;
  });
  h += '</table>';
  document.getElementById('holdingsTable').innerHTML = h;
}

function renderTradeTable(data) {
  if(!data.length) { document.getElementById('tradeTable').innerHTML='<p style="color:#8899aa;padding:8px">暂无交易</p>'; return; }
  let h = '<table><tr><th>日期</th><th>标的</th><th>操作</th><th>价格</th><th>数量</th><th>金额</th><th>手续费</th><th>原因</th></tr>';
  data.slice(0,500).forEach(r => {
    const ac = r.action.includes('BUY')?'pos':'neg';
    h += `<tr><td>${r.date}</td><td>${r.name||r.ticker}</td><td class="${ac}">${r.action}</td><td>${typeof r.price==='number'?r.price.toFixed(4):r.price}</td><td>${r.shares}</td><td>${typeof r.value==='number'?r.value.toFixed(0):r.value}</td><td>${typeof r.fee==='number'?r.fee.toFixed(2):r.fee}</td><td>${r.reason}</td></tr>`;
  });
  h += '</table>';
  if(data.length>500) h += `<p style="color:#8899aa;font-size:11px;margin-top:6px">仅显示前500条，共${data.length}条</p>`;
  document.getElementById('tradeTable').innerHTML = h;
}

function filterTrades() {
  const q = document.getElementById('tradeFilter').value.toLowerCase();
  const a = document.getElementById('tradeActionFilter').value;
  let filtered = allTrades;
  if(q) filtered = filtered.filter(t => (t.name||t.ticker||'').toLowerCase().includes(q) || (t.reason||'').toLowerCase().includes(q));
  if(a) filtered = filtered.filter(t => t.action.includes(a));
  renderTradeTable(filtered);
}

function exportCSV() {
  if(!allTrades.length) return;
  const headers = ['日期','标的','操作','价格','数量','金额','手续费','原因'];
  const rows = allTrades.map(t => [t.date, t.name||t.ticker, t.action, t.price, t.shares, t.value, t.fee, t.reason]);
  const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
  const blob = new Blob(['\uFEFF'+csv], {type:'text/csv;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'trades_'+curStrat+'_'+new Date().toISOString().slice(0,10)+'.csv';
  a.click();
  URL.revokeObjectURL(url);
}

window.addEventListener('resize', () => {
  if(navChartInst) navChartInst.resize();
  if(holdChartInst) holdChartInst.resize();
});

init();
</script>
</body>
</html>
'''


if __name__ == '__main__':
    print("=" * 60)
    print("ETF轮动策略回测Web系统")
    print("访问: http://localhost:8001/")
    print("=" * 60)
    app.run(host='0.0.0.0', port=8001, debug=False)

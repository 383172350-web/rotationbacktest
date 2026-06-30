# -*- coding: utf-8 -*-
"""
Legacy策略适配层 —— 从 app.py 提取的原始硬编码策略函数
策略生成器调用这些函数，确保收益和原始系统完全一致
"""
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional


# ========================================
#  配置常量（从 app.py 同步）
# ========================================
FEE_RATE = 0.0001


# ========================================
#  数据加载（原始函数）
# ========================================
def load_pkl_data(pkl_dir, tickers):
    """从pkl目录加载数据"""
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
    """只对齐轮动标的的日期"""
    common = None
    for t in rotation_tickers:
        if t in data_dict:
            common = set(data_dict[t].index) if common is None else common.intersection(set(data_dict[t].index))
    if common is None:
        return data_dict, []
    common = sorted(list(common))
    for t in data_dict:
        data_dict[t] = data_dict[t].loc[data_dict[t].index.isin(common)]
    return data_dict, common


def get_ticker_name(thscode, etf_config):
    """获取标的名称"""
    for cfg in etf_config.values():
        if cfg.get('thscode') == thscode:
            return cfg.get('name_cn', thscode)
    return thscode


# ========================================
#  DIFv 指标计算
# ========================================
def calc_difv_signals(data_dict, tickers):
    """DIFv指标计算：DIF/ATR*100"""
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


# ========================================
#  五斗米动量指标计算
# ========================================
def calc_wdm_signals(data_dict, tickers, momentum_shift=12, momentum_smooth=3, boll_period=17, boll_std=2):
    """五斗米动量指标计算"""
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


# ========================================
#  LOF 指标计算
# ========================================
def calc_lof_signals(data_dict, tickers, momentum_window=20, penalty_score=8, penalty_days=3, penalty_threshold=-0.03):
    """LOF轮动指标计算：动量标准差 + 连跌惩罚"""
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


# ========================================
#  RSRS 指标计算
# ========================================
def calc_rsrs_signals(data_dict, tickers, momentum_days=20, momentum_score_limit=7,
                      rsrs_strong=0.15, rsrs_medium=0.03, volume_ratio_limit=2):
    """RSRS动量指标计算：加权对数回归 + RSRS强度"""
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

        # 动量得分: 加权对数回归
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

        # RSRS强度
        rsrs_days = 18
        rsrs_window = 20
        lookback_days = 250

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

        rsrs_strengths = np.full(n, np.nan)
        rsrs_pass_list = np.zeros(n, dtype=bool)

        for i in range(n):
            if i < rsrs_days - 1:
                continue
            cur_slope = all_slopes[i]
            if np.isnan(cur_slope):
                continue
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
        df['above_ma5'] = (close > df['ma5']).fillna(False)
        df['above_ma10'] = (close >= df['ma10']).fillna(False)
        df['above_ma20'] = (close > df['ma20']).fillna(False)

        # 量比
        vol = df['volume']
        vol_ma7 = vol.rolling(7).mean()
        vol_ratio = vol / vol_ma7
        df['volume_ratio'] = np.where(vol_ratio > volume_ratio_limit, vol_ratio, np.nan)

        sig[t] = df
    return sig


# ========================================
#  回测函数（从 app.py 提取）
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




# -*- coding: utf-8 -*-
"""
通用回测引擎 —— 支持高度自定义的轮动策略
==========================================
核心函数: run_backtest(data_dict, signals, config) -> dict

与 v7 策略回测逻辑完全一致：
  - 每日检查卖出条件，T+1 开盘价执行卖出
  - 每轮动日检查买入条件，补充到 max_holdings 只
  - 有新标的买入时全量再平衡，无新标的时清理非目标持仓
  - 非轮动日卖出后资金转债券替代
  - nav 归一化为 1.0 起始
"""

from __future__ import print_function, division

import pandas as pd
import numpy as np

from .data_loader import ETF_NAMES
from .expression_parser import evaluate_condition, evaluate_score
from .precompiler import has_special_var
import sys, io

# Windows GBK 编码修复
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")



# ============================================================
#  辅助函数
# ============================================================

def get_ticker_name(ticker):
    """从 ETF_NAMES 获取 ticker 中文名，找不到则返回 ticker 本身"""
    return ETF_NAMES.get(ticker, ticker)


# ============================================================
#  条件评估引擎（表达式解析版）
# ============================================================

def _eval_buy_conditions(df, buy_rules, buy_match_mode, extra_vars=None, date=None):
    """
    使用表达式解析评估买入条件，优先读取预计算列（性能优化）。
    df: ticker 的完整 DataFrame（含OHLCV及指标列）
    buy_rules: 列表，每项为 {'condition': 'close > MA(5)', 'description': '...'}
    buy_match_mode: 'all' 或 'any'
    extra_vars: 特殊变量字典（如 rank）
    date: 当前日期，用于从预计算列中取值
    """
    if not buy_rules:
        return True
    extra_vars = extra_vars or {}
    results = []
    for i, rule in enumerate(buy_rules):
        cond = rule.get('condition', '') if isinstance(rule, dict) else str(rule)
        if not cond.strip():
            continue
        # 优先读取预计算列（性能优化：避免重复解析表达式）
        pc_col = f'__buy_{i}'
        if pc_col in df.columns and date is not None:
            try:
                result = bool(df.at[date, pc_col])
                results.append(result)
                continue
            except (KeyError, IndexError, ValueError):
                pass
        # 动态解析（含特殊变量或预计算失败时回退）
        try:
            result_series = evaluate_condition(cond, df, extra_vars)
            if date is not None and date in result_series.index:
                result = bool(result_series.loc[date])
            else:
                result = bool(result_series.iloc[-1]) if hasattr(result_series, 'iloc') else bool(result_series)
        except Exception:
            result = False
        results.append(result)

    if buy_match_mode == 'all':
        return all(results) if results else True
    else:  # 'any'
        return any(results) if results else False


def _eval_sell_conditions(df, sell_rules, sell_match_mode, extra_vars=None, date=None):
    """
    使用表达式解析评估卖出条件，优先读取预计算列（性能优化）。
    sell_rules: 列表，每项为 {'condition': 'rank > 6', 'description': '...'}
    sell_match_mode: 'all' 或 'any'
    extra_vars: 特殊变量字典（如 rank, profit, buy_price）
    date: 当前日期，用于从预计算列中取值
    返回 (should_sell, reasons)。
    """
    if not sell_rules:
        return False, []
    extra_vars = extra_vars or {}
    reasons = []

    # 收集每条规则的触发结果
    all_triggered = []
    for i, rule in enumerate(sell_rules):
        cond = rule.get('condition', '') if isinstance(rule, dict) else str(rule)
        desc = rule.get('description', cond) if isinstance(rule, dict) else cond
        if not cond.strip():
            continue
        # 优先读取预计算列
        pc_col = f'__sell_{i}'
        if pc_col in df.columns and date is not None:
            try:
                triggered = bool(df.at[date, pc_col])
                if triggered:
                    reasons.append(desc)
                all_triggered.append(triggered)
                continue
            except (KeyError, IndexError, ValueError):
                pass
        # 动态解析
        try:
            result_series = evaluate_condition(cond, df, extra_vars)
            if date is not None and date in result_series.index:
                triggered = bool(result_series.loc[date])
            else:
                triggered = bool(result_series.iloc[-1]) if hasattr(result_series, 'iloc') else bool(result_series)
        except Exception:
            triggered = False
        all_triggered.append(triggered)
        if triggered:
            reasons.append(desc)

    if sell_match_mode == 'all':
        should_sell = all(all_triggered) if all_triggered else False
    else:  # 'any'
        should_sell = any(all_triggered) if all_triggered else False

    return should_sell, reasons


# ============================================================
#  大跌惩罚
# ============================================================

def _apply_drop_penalty(signals, stock_tickers, sort_config):
    """对 signals 中的 sort_value 应用大跌惩罚"""
    drop_penalty = sort_config.get('drop_penalty', False)
    if not drop_penalty:
        return

    threshold = sort_config.get('drop_threshold', 0.05)
    penalty_value = -300  # 惩罚值，与 v7 一致

    for ticker in stock_tickers:
        if ticker not in signals:
            continue
        df = signals[ticker]
        if 'close' not in df.columns:
            continue
        close = df['close']
        # 最近3日任一日跌幅 > 阈值
        has_big_drop = (
            (close / close.shift(1) < 1 - threshold) |
            (close.shift(1) / close.shift(2) < 1 - threshold) |
            (close.shift(2) / close.shift(3) < 1 - threshold)
        )
        df.loc[has_big_drop, 'sort_value'] = penalty_value



# ============================================================
#  排名计算
# ============================================================

def _calc_rank_map(rank_matrix, stock_tickers, date_idx, sort_config):
    """
    计算某日的排名映射（向量化优化版）。
    返回 {ticker: rank}, rank 从 1 开始。
    """
    rank_formula = sort_config.get('rank_formula', 'returns(20)')
    direction = sort_config.get('rank_direction', 'desc')
    descending = (direction == 'desc')

    row = rank_matrix[date_idx]
    valid_mask = ~np.isnan(row)
    valid_indices = np.where(valid_mask)[0]
    if len(valid_indices) == 0:
        return {}, {}

    valid_values = row[valid_indices]
    sorted_order = np.argsort(valid_values)[::-1] if descending else np.argsort(valid_values)

    rank_map = {}
    sort_values = {}
    for i, idx in enumerate(sorted_order):
        ticker = stock_tickers[valid_indices[idx]]
        rank_map[ticker] = i + 1
        sort_values[ticker] = valid_values[idx]

    return rank_map, sort_values



# ============================================================
#  主回测函数
# ============================================================

def run_backtest(data_dict, signals, config):
    """
    通用回测引擎。

    Parameters
    ----------
    data_dict : dict[str, DataFrame]
        ticker -> DataFrame(index=datetime, columns=[open,high,low,close,volume,...])
    signals : dict[str, DataFrame]
        ticker -> DataFrame(index=datetime, 含 sort_value/ma5/ma10/ma20/daily_return/return_20/... 等指标列)
    config : dict
        回测配置，结构见模块文档。

    Returns
    -------
    dict
        nav_df: DataFrame(date, nav)，nav 归一化为 1.0 起始
        trade_log: list of dict，交易记录
        hold_history: list of dict，每日持仓
        final_holdings: dict，最终持仓
        final_cash: float，最终现金
    """
    # ---- 解析配置（新版表达式格式） ----
    stock_tickers = config['stock_tickers']
    bond_ticker = config.get('bond_ticker')
    initial_capital = config.get('initial_capital', 1000000)
    fee_rate = config.get('fee_rate', 0.0001)
    start_date_str = config.get('start_date')
    sort_config = config.get('sort', {'rank_formula': 'returns(20)', 'rank_direction': 'desc'})
    buy_config = config.get('buy', {'buy_match_mode': 'all', 'buy_rules': []})
    sell_config = config.get('sell', {'sell_match_mode': 'any', 'sell_rules': [], 'stop_loss': 0, 'sell_if_buy_fails': False})
    position_config = config.get('position', {
        'mode': 'equal_weight', 'max_holdings': 5,
        'position_pct': 0.20, 'rebalance_days': 2, 'new_rank_limit': 0
    })

    max_holdings = position_config.get('max_holdings', 5)
    position_pct = position_config.get('position_pct', 0.20)
    rebalance_days = position_config.get('rebalance_days', 2)
    new_rank_limit = position_config.get('new_rank_limit', 0)
    position_mode = position_config.get('mode', 'equal_weight')
    rebalance_mode = position_config.get('rebalance_mode', 'incremental')  # 'incremental' or 'full'

    stop_loss_pct = sell_config.get('stop_loss', 0)
    sell_if_buy_fails = sell_config.get('sell_if_buy_fails', False)

    buy_match_mode = buy_config.get('buy_match_mode', 'all')
    buy_rules = buy_config.get('buy_rules', [])
    sell_match_mode = sell_config.get('sell_match_mode', 'any')
    sell_rules = sell_config.get('sell_rules', [])
    rank_formula = sort_config.get('rank_formula', 'returns(20)')
    rank_direction = sort_config.get('rank_direction', 'desc')

    # ---- 预计算排序得分 ----
    for ticker in stock_tickers:
        if ticker not in signals:
            continue
        try:
            signals[ticker]['__rank_score'] = evaluate_score(rank_formula, signals[ticker])
        except Exception as e:
            signals[ticker]['__rank_score'] = np.nan
            print(f"[排序预计算失败] {ticker}: {e}")

    # ---- 预计算买入/卖出条件（不含特殊变量，大幅提升性能） ----
    from .precompiler import precompute_strategy
    for ticker in stock_tickers:
        if ticker not in signals:
            continue
        try:
            signals[ticker] = precompute_strategy(signals[ticker], {
                'rank_formula': rank_formula,
                'buy_rules': buy_rules,
                'sell_rules': sell_rules,
            })
        except Exception as e:
            print(f"[条件预计算失败] {ticker}: {e}")

    # ---- 应用大跌惩罚 ----
    _apply_drop_penalty(signals, stock_tickers, sort_config)

    # ---- 确定交易日期 ----
    all_tickers = list(stock_tickers)
    if bond_ticker:
        all_tickers.append(bond_ticker)

    # 取所有标的的日期交集
    date_sets = []
    for ticker in all_tickers:
        if ticker in signals and not signals[ticker].empty:
            date_sets.append(set(signals[ticker].index))
        elif ticker in data_dict and not data_dict[ticker].empty:
            date_sets.append(set(data_dict[ticker].index))

    if not date_sets:
        return {
            'nav_df': pd.DataFrame(columns=['nav']),
            'trade_log': [],
            'hold_history': [],
            'final_holdings': {},
            'final_cash': 0.0,
        }

    common_dates = sorted(list(set.intersection(*date_sets)))

    # 起始日期过滤
    if start_date_str:
        start_ts = pd.Timestamp(start_date_str)
        common_dates = [d for d in common_dates if d >= start_ts]
        if not common_dates:
            return {
                'nav_df': pd.DataFrame(columns=['nav']),
                'trade_log': [],
                'hold_history': [],
                'final_holdings': {},
                'final_cash': 0.0,
            }

    # ---- 对齐起始：从所有 stock_tickers 的 close > 0 且非 NaN 的第一天开始 ----
    valid_start = None
    for d in common_dates:
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
        common_dates = [d for d in common_dates if d >= valid_start]
    if not common_dates:
        return {
            'nav_df': pd.DataFrame(columns=['nav']),
            'trade_log': [],
            'hold_history': [],
            'final_holdings': {},
            'final_cash': 0.0,
        }

    # ---- 确定轮动日集合 ----
    rebalance_dates = set([common_dates[i] for i in range(0, len(common_dates), rebalance_days)])

    # ---- 预构建排名矩阵（向量化优化：避免回测循环中重复 pandas 索引） ----
    date_to_idx = {d: i for i, d in enumerate(common_dates)}
    rank_matrix = np.full((len(common_dates), len(stock_tickers)), np.nan)
    for j, ticker in enumerate(stock_tickers):
        if ticker in signals and '__rank_score' in signals[ticker].columns:
            s = signals[ticker]['__rank_score'].reindex(common_dates)
            rank_matrix[:, j] = s.values

    # ---- 初始化 ----
    cash = float(initial_capital)
    holdings = {}  # ticker -> {shares, cost, buy_date}
    nav_history = []
    trade_log = []
    hold_history = []

    # ============================================================
    #  主循环：逐日回测
    # ============================================================
    for i, date in enumerate(common_dates):
        # ---- 0. 跳过不在 signals 中的 ticker ----
        # （signals 中如果某 ticker 不在或 date 不在，跳过）

        # ---- 1. 计算当日净值（收盘价） ----
        nav = cash
        for t, pos in holdings.items():
            t_df = signals.get(t, data_dict.get(t))
            if t_df is not None and date in t_df.index:
                nav += pos['shares'] * t_df.loc[date, 'close']
        nav_history.append({'date': date, 'nav': nav})

        # 记录每日持仓
        active_tickers = [t for t in holdings if t != bond_ticker]
        hold_history.append({
            'date': date,
            'holdings': len(active_tickers),
            'hold_tickers': active_tickers,
        })

        # ---- 检查是否有下一个交易日（T+1） ----
        if i + 1 >= len(common_dates):
            continue
        next_date = common_dates[i + 1]

        # ---- 2. 计算当日排名 ----
        rank_map, sort_values = _calc_rank_map(rank_matrix, stock_tickers, i, sort_config)

        # ---- 3. 每日检查卖出（所有交易日） ----
        sell_list = []
        for ticker in list(holdings.keys()):
            if ticker == bond_ticker:
                continue
            t_df = signals.get(ticker)
            if t_df is None or date not in t_df.index:
                continue

            row = t_df.loc[date]
            rank = rank_map.get(ticker, 99)

            # 使用表达式解析评估卖出条件
            extra_vars = {
                'rank': rank,
                'buy_price': holdings[ticker]['cost'],
            }
            should_sell, reasons = _eval_sell_conditions(
                t_df, sell_rules, sell_match_mode, extra_vars=extra_vars, date=date
            )

            # sell_if_buy_fails: 不满足买入条件则卖出
            if sell_if_buy_fails and not should_sell:
                buy_ok = _eval_buy_conditions(
                    t_df, buy_rules, buy_match_mode, extra_vars={'rank': rank}, date=date
                )
                # 如果 rank 限制不满足，也视为买入条件不满足
                if new_rank_limit > 0 and rank > new_rank_limit:
                    buy_ok = False
                if not buy_ok:
                    should_sell = True
                    reasons.append('不满足买入条件')

            if should_sell:
                sell_list.append((ticker, "; ".join(reasons)))

        # single模式换仓：轮动日如果持仓标的排名不是第一且有更好的标的满足买入条件
        if position_mode == 'single' and sell_if_buy_fails and date in rebalance_dates:
            sold_tickers = set(t for t, _ in sell_list)
            holding_tickers = [t for t in holdings if t != bond_ticker and t not in sold_tickers]
            if holding_tickers:
                holding_ticker = holding_tickers[0]
                holding_rank = rank_map.get(holding_ticker, 999)
                # 检查是否有排名更靠前且满足买入条件的标的
                for t in stock_tickers:
                    if t == holding_ticker:
                        continue
                    t_df = signals.get(t)
                    if t_df is None or date not in t_df.index:
                        continue
                    t_rank = rank_map.get(t, 999)
                    extra_vars = {'rank': t_rank}
                    buy_ok = _eval_buy_conditions(t_df, buy_rules, buy_match_mode, extra_vars=extra_vars, date=date)
                    if new_rank_limit > 0 and t_rank > new_rank_limit:
                        buy_ok = False
                    if buy_ok and t_rank < holding_rank:
                        sell_list.append((holding_ticker, "轮动换仓"))
                        break

        # T+1 开盘价执行卖出
        for ticker, reason in sell_list:
            if ticker not in holdings:
                continue
            t_df = signals.get(ticker, data_dict.get(ticker))
            if t_df is None or next_date not in t_df.index:
                continue

            open_price = t_df.loc[next_date, 'open']
            if open_price <= 0:
                continue
            pos = holdings[ticker]
            sell_value = pos['shares'] * open_price
            fee = sell_value * fee_rate if ticker != bond_ticker else 0.0
            cash += (sell_value - fee)

            buy_price = pos['cost']
            pnl_pct = (open_price - buy_price) / buy_price * 100 if buy_price > 0 else 0
            hold_days = (date - pos['buy_date']).days if hasattr(date, '__sub__') else 0

            trade_log.append({
                'date': next_date,
                'ticker': ticker,
                'name': get_ticker_name(ticker),
                'action': 'SELL',
                'price': open_price,
                'shares': pos['shares'],
                'value': sell_value,
                'fee': fee,
                'pnl_pct': pnl_pct,
                'hold_days': hold_days,
                'reason': reason,
            })
            del holdings[ticker]

        # ---- 4. 非轮动日：卖出后资金转债券替代 ----
        if date not in rebalance_dates:
            if bond_ticker and cash > 1e-6:
                b_df = signals.get(bond_ticker, data_dict.get(bond_ticker))
                if b_df is not None and next_date in b_df.index:
                    open_price = b_df.loc[next_date, 'open']
                    if open_price <= 0:
                        pass
                    elif bond_ticker in holdings:
                        old = holdings[bond_ticker]
                        add_value = cash
                        fee = 0.0  # 债券替代免手续费
                        add_shares = add_value / open_price
                        new_shares = old['shares'] + add_shares
                        old_value = old['shares'] * old['cost']
                        old['shares'] = new_shares
                        old['cost'] = (old_value + add_value) / new_shares if new_shares > 0 else old['cost']
                        trade_log.append({
                            'date': next_date,
                            'ticker': bond_ticker,
                            'name': get_ticker_name(bond_ticker),
                            'action': 'ADD_BOND',
                            'price': open_price,
                            'shares': add_shares,
                            'value': add_value,
                            'fee': fee,
                            'pnl_pct': 0,
                            'hold_days': (next_date - old['buy_date']).days if hasattr(next_date, '__sub__') else 0,
                            'reason': '非轮动日资金归集',
                        })
                        cash = 0.0
                    else:
                        buy_value = cash
                        fee = 0.0
                        shares = buy_value / open_price
                        holdings[bond_ticker] = {
                            'shares': shares,
                            'cost': open_price,
                            'buy_date': next_date,
                        }
                        trade_log.append({
                            'date': next_date,
                            'ticker': bond_ticker,
                            'name': get_ticker_name(bond_ticker),
                            'action': 'BUY_BOND',
                            'price': open_price,
                            'shares': shares,
                            'value': buy_value,
                            'fee': fee,
                            'pnl_pct': 0,
                            'hold_days': 0,
                            'reason': '非轮动日空仓替代',
                        })
                        cash = 0.0
            continue

        # ============================================================
        #  5. 轮动日：买入 / 再平衡逻辑
        # ============================================================

        # 5.1 确定当前持仓（卖出后的剩余，不含债券替代）
        target_stocks = []
        for ticker in holdings:
            if ticker == bond_ticker:
                continue
            target_stocks.append(ticker)

        # 5.2 找新的买入候选
        candidates = []
        for ticker in stock_tickers:
            if ticker in target_stocks:
                continue
            t_df = signals.get(ticker)
            if t_df is None or date not in t_df.index:
                continue
            rank = rank_map.get(ticker, 99)
            extra_vars = {'rank': rank}

            # 买入条件检查
            buy_ok = _eval_buy_conditions(t_df, buy_rules, buy_match_mode, extra_vars=extra_vars, date=date)

            # 排名条件（新入选可单独限制）
            if new_rank_limit > 0:
                rank_ok = rank <= new_rank_limit
            else:
                rank_ok = True

            if buy_ok and rank_ok:
                sort_val = sort_values.get(ticker, np.nan)
                if pd.notna(sort_val):
                    candidates.append((ticker, sort_val, rank))

        # 按排序指标降序/升序排列候选
        direction = sort_config.get('direction', 'desc')
        candidates.sort(key=lambda x: x[1], reverse=(direction == 'desc'))

        # 补充到最多 max_holdings 只
        slots = max_holdings - len(target_stocks)

        # incremental满仓换仓：卖最弱买最强
        if position_mode == 'incremental' and slots <= 0 and candidates:
            # 找最弱持仓（sort_value最差的）
            weakest_ticker = None
            if direction == 'desc':
                weakest_sv = float('inf')
            else:
                weakest_sv = float('-inf')
            for t in target_stocks:
                if t in signals and date in signals[t].index:
                    sv = signals[t].loc[date, 'sort_value']
                    if pd.notna(sv):
                        if (direction == 'desc' and sv < weakest_sv) or \
                           (direction == 'asc' and sv > weakest_sv):
                            weakest_sv = sv
                            weakest_ticker = t
            # 找最强候选（已按sort_value排序，candidates[0]最强）
            best_ticker, best_sv, best_rank = candidates[0]
            # 比较最强候选是否优于最弱持仓
            is_better = (best_sv > weakest_sv) if direction == 'desc' else (best_sv < weakest_sv)
            if weakest_ticker and pd.notna(best_sv) and is_better:
                # 卖最弱持仓
                if weakest_ticker in holdings:
                    t_df = signals.get(weakest_ticker, data_dict.get(weakest_ticker))
                    if t_df is not None and next_date in t_df.index:
                        open_price = t_df.loc[next_date, 'open']
                        if open_price > 0:
                            pos = holdings[weakest_ticker]
                            sell_value = pos['shares'] * open_price
                            fee = sell_value * fee_rate
                            cash += (sell_value - fee)
                            buy_price = pos['cost']
                            pnl_pct = (open_price - buy_price) / buy_price * 100 if buy_price > 0 else 0
                            hold_days = (date - pos['buy_date']).days if hasattr(date, '__sub__') else 0
                            trade_log.append({
                                'date': next_date,
                                'ticker': weakest_ticker,
                                'name': get_ticker_name(weakest_ticker),
                                'action': 'SELL',
                                'price': open_price,
                                'shares': pos['shares'],
                                'value': sell_value,
                                'fee': fee,
                                'pnl_pct': pnl_pct,
                                'hold_days': hold_days,
                                'reason': '增量换仓',
                            })
                            del holdings[weakest_ticker]
                target_stocks.remove(weakest_ticker)
                slots = 1  # 腾出一个位置

        for ticker, sort_val, rank in candidates[:slots]:
            if ticker not in target_stocks:
                target_stocks.append(ticker)

        # 5.3 判断是否需要再平衡
        # incremental模式：只有目标中有新标的时才再平衡
        # full模式：轮动日总是全卖全买（和 legacy app.py 一致）
        if rebalance_mode == 'full':
            need_rebalance = True
        else:
            need_rebalance = any(t not in holdings for t in target_stocks)

        # 5.4 根据持仓模式执行
        if need_rebalance:
            # ---- 全量再平衡 ----
            # 先卖出所有持仓
            for t in list(holdings.keys()):
                t_df = signals.get(t, data_dict.get(t))
                if t_df is not None and next_date in t_df.index:
                    open_price = t_df.loc[next_date, 'open']
                    if open_price > 0:
                        cash += holdings[t]['shares'] * open_price
                del holdings[t]

            total_value = cash

            if position_mode == 'equal_weight':
                # 等权分配
                for ticker in target_stocks:
                    target_value = total_value * position_pct
                    t_df = signals.get(ticker, data_dict.get(ticker))
                    if t_df is None or next_date not in t_df.index:
                        continue
                    fee = target_value * fee_rate
                    open_price = t_df.loc[next_date, 'open']
                    if open_price <= 0:
                        continue
                    shares = target_value / open_price
                    buy_value = shares * open_price
                    cash -= (buy_value + fee)
                    holdings[ticker] = {
                        'shares': shares,
                        'cost': open_price,
                        'buy_date': next_date,
                    }
                    trade_log.append({
                        'date': next_date,
                        'ticker': ticker,
                        'name': get_ticker_name(ticker),
                        'action': 'BUY',
                        'price': open_price,
                        'shares': shares,
                        'value': buy_value,
                        'fee': fee,
                        'pnl_pct': 0,
                        'hold_days': 0,
                        'reason': '建仓/再平衡',
                    })

            elif position_mode == 'single':
                # 100% 单标的，只持最强的
                if target_stocks:
                    ticker = target_stocks[0]
                    t_df = signals.get(ticker, data_dict.get(ticker))
                    if t_df is not None and next_date in t_df.index:
                        target_value = total_value
                        fee = target_value * fee_rate
                        open_price = t_df.loc[next_date, 'open']
                        if open_price <= 0:
                            pass
                        else:
                            shares = target_value / open_price
                            buy_value = shares * open_price
                            cash -= (buy_value + fee)
                            holdings[ticker] = {
                                'shares': shares,
                                'cost': open_price,
                                'buy_date': next_date,
                            }
                            trade_log.append({
                                'date': next_date,
                                'ticker': ticker,
                                'name': get_ticker_name(ticker),
                                'action': 'BUY',
                                'price': open_price,
                                'shares': shares,
                                'value': buy_value,
                                'fee': fee,
                                'pnl_pct': 0,
                                'hold_days': 0,
                                'reason': '单标的建仓',
                            })

            elif position_mode == 'incremental':
                # 增量式：按排名依次买入，每只 position_pct 比例
                for ticker in target_stocks:
                    if cash < total_value * position_pct * 0.5:
                        break  # 剩余资金不足半仓，停止
                    target_value = total_value * position_pct
                    t_df = signals.get(ticker, data_dict.get(ticker))
                    if t_df is None or next_date not in t_df.index:
                        continue
                    fee = target_value * fee_rate
                    open_price = t_df.loc[next_date, 'open']
                    if open_price <= 0:
                        continue
                    shares = target_value / open_price
                    buy_value = shares * open_price
                    if cash < buy_value + fee:
                        # 余额不足，用剩余资金买入
                        buy_value = cash / (1 + fee_rate)
                        if buy_value <= 0:
                            continue
                        fee = buy_value * fee_rate
                        shares = buy_value / open_price
                    cash -= (buy_value + fee)
                    holdings[ticker] = {
                        'shares': shares,
                        'cost': open_price,
                        'buy_date': next_date,
                    }
                    trade_log.append({
                        'date': next_date,
                        'ticker': ticker,
                        'name': get_ticker_name(ticker),
                        'action': 'BUY',
                        'price': open_price,
                        'shares': shares,
                        'value': buy_value,
                        'fee': fee,
                        'pnl_pct': 0,
                        'hold_days': 0,
                        'reason': '增量建仓',
                    })

            # 余款买债券替代
            if bond_ticker and cash > 1e-6:
                b_df = signals.get(bond_ticker, data_dict.get(bond_ticker))
                if b_df is not None and next_date in b_df.index:
                    open_price = b_df.loc[next_date, 'open']
                    if open_price <= 0:
                        pass
                    else:
                        buy_value = cash
                        fee = 0.0  # 债券替代免手续费
                        shares = buy_value / open_price
                        holdings[bond_ticker] = {
                            'shares': shares,
                            'cost': open_price,
                            'buy_date': next_date,
                        }
                        trade_log.append({
                            'date': next_date,
                            'ticker': bond_ticker,
                            'name': get_ticker_name(bond_ticker),
                            'action': 'BUY_BOND',
                            'price': open_price,
                            'shares': shares,
                            'value': buy_value,
                            'fee': fee,
                            'pnl_pct': 0,
                            'hold_days': 0,
                            'reason': '空仓替代',
                        })
                        cash = 0.0

        else:
            # ---- 不需要再平衡：清理非目标持仓，资金转债券替代 ----
            for t in list(holdings.keys()):
                if t != bond_ticker and t not in target_stocks:
                    t_df = signals.get(t, data_dict.get(t))
                    if t_df is None or next_date not in t_df.index:
                        continue
                    open_price = t_df.loc[next_date, 'open']
                    if open_price <= 0:
                        continue
                    sell_value = holdings[t]['shares'] * open_price
                    fee = sell_value * fee_rate if t != bond_ticker else 0.0
                    cash += (sell_value - fee)
                    trade_log.append({
                        'date': next_date,
                        'ticker': t,
                        'name': get_ticker_name(t),
                        'action': 'SELL_CLEAR',
                        'price': open_price,
                        'shares': holdings[t]['shares'],
                        'value': sell_value,
                        'fee': fee,
                        'pnl_pct': (open_price - holdings[t]['cost']) / holdings[t]['cost'] * 100 if holdings[t]['cost'] > 0 else 0,
                        'hold_days': (next_date - holdings[t]['buy_date']).days if hasattr(next_date, '__sub__') else 0,
                        'reason': '轮动调出',
                    })
                    del holdings[t]

            # 剩余资金转债券替代
            if bond_ticker and cash > 1e-6:
                b_df = signals.get(bond_ticker, data_dict.get(bond_ticker))
                if b_df is not None and next_date in b_df.index:
                    open_price = b_df.loc[next_date, 'open']
                    if open_price <= 0:
                        pass
                    elif bond_ticker in holdings:
                        old = holdings[bond_ticker]
                        add_value = cash
                        fee = 0.0
                        add_shares = add_value / open_price
                        new_shares = old['shares'] + add_shares
                        old_value = old['shares'] * old['cost']
                        old['shares'] = new_shares
                        old['cost'] = (old_value + add_value) / new_shares if new_shares > 0 else old['cost']
                        trade_log.append({
                            'date': next_date,
                            'ticker': bond_ticker,
                            'name': get_ticker_name(bond_ticker),
                            'action': 'ADD_BOND',
                            'price': open_price,
                            'shares': add_shares,
                            'value': add_value,
                            'fee': fee,
                            'pnl_pct': 0,
                            'hold_days': (next_date - old['buy_date']).days if hasattr(next_date, '__sub__') else 0,
                            'reason': '轮动归集',
                        })
                        cash = 0.0
                    else:
                        buy_value = cash
                        fee = 0.0
                        shares = buy_value / open_price
                        holdings[bond_ticker] = {
                            'shares': shares,
                            'cost': open_price,
                            'buy_date': next_date,
                        }
                        trade_log.append({
                            'date': next_date,
                            'ticker': bond_ticker,
                            'name': get_ticker_name(bond_ticker),
                            'action': 'BUY_BOND',
                            'price': open_price,
                            'shares': shares,
                            'value': buy_value,
                            'fee': fee,
                            'pnl_pct': 0,
                            'hold_days': 0,
                            'reason': '空仓替代',
                        })
                        cash = 0.0

    # ============================================================
    #  构造返回值
    # ============================================================
    nav_df = pd.DataFrame(nav_history)
    if not nav_df.empty:
        nav_df = nav_df.set_index('date')
        # nav 归一化：nav_df['nav'] = nav_df['nav'] / nav_df['nav'].iloc[0]
        first_nav = nav_df['nav'].iloc[0]
        if first_nav > 0:
            nav_df['nav'] = nav_df['nav'] / first_nav
    else:
        nav_df = pd.DataFrame(columns=['nav'])

    return {
        'nav_df': nav_df,
        'trade_log': trade_log,
        'hold_history': hold_history,
        'final_holdings': holdings,
        'final_cash': cash,
    }

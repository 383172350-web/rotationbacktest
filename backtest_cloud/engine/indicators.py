"""
技术指标计算模块
支持动态参数的各种指标计算
"""
import numpy as np
import pandas as pd
from typing import Optional


def MA(close: pd.Series, period: int) -> pd.Series:
    """简单移动平均线"""
    return close.rolling(window=period, min_periods=period).mean()


def EMA(close: pd.Series, period: int) -> pd.Series:
    """指数移动平均线"""
    return close.ewm(span=period, adjust=False).mean()


def RSI(close: pd.Series, period: int = 14) -> pd.Series:
    """相对强弱指标"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def MACD(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """MACD指标"""
    ema_fast = EMA(close, fast)
    ema_slow = EMA(close, slow)
    dif = ema_fast - ema_slow
    dea = EMA(dif, signal)
    macd = (dif - dea) * 2
    return {
        'DIF': dif,
        'DEA': dea,
        'MACD': macd
    }


def BOLL(close: pd.Series, period: int = 20, std_dev: int = 2) -> dict:
    """布林带"""
    mid = MA(close, period)
    std = close.rolling(window=period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return {
        'upper': upper,
        'mid': mid,
        'lower': lower
    }


def KDJ(high: pd.Series, low: pd.Series, close: pd.Series,
        n: int = 9, m1: int = 3, m2: int = 3) -> dict:
    """KDJ指标"""
    lowest_low = low.rolling(window=n, min_periods=n).min()
    highest_high = high.rolling(window=n, min_periods=n).max()
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100

    k = rsv.ewm(com=m1-1, adjust=False).mean()
    d = k.ewm(com=m2-1, adjust=False).mean()
    j = 3 * k - 2 * d

    return {
        'K': k,
        'D': d,
        'J': j
    }


def ATR(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """平均真实波幅（标准ATR - 简单移动平均MA，对齐通达信公式 ATR:=MA(TR,26)）"""
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def returns(close: pd.Series, period: int) -> pd.Series:
    """区间涨幅（百分比）"""
    return (close - close.shift(period)) / close.shift(period)


def BIAS(close: pd.Series, period: int) -> pd.Series:
    """乖离率：收盘价偏离N日均线的百分比"""
    ma = MA(close, period)
    return (close - ma) / ma * 100


def quality_score(close: pd.Series, period: int = 20) -> pd.Series:
    """
    质量得分（加权动量R²）
    取过去N天的对数收盘价，用线性递增权重做加权线性回归，
    斜率转为年化收益率，乘以R²得到质量得分。
    得分越高说明趋势越稳定（方向一致且线性拟合好）。
    """
    n = len(close)
    result = pd.Series(np.nan, index=close.index)

    for i in range(period, n):
        prices = close.iloc[i - period + 1:i + 1].values
        log_prices = np.log(prices)
        x = np.arange(len(prices))
        w = np.linspace(1, 2, len(prices))
        slope, intercept = np.polyfit(x, log_prices, 1, w=w)
        ann_ret = np.exp(slope * 250) - 1
        y_pred = slope * x + intercept
        ss_res = np.sum(w * (log_prices - y_pred) ** 2)
        ss_tot = np.sum(w * (log_prices - np.mean(log_prices)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        result.iloc[i] = ann_ret * r2

    return result


def volatility(close: pd.Series, period: int = 20) -> pd.Series:
    """波动率"""
    return close.pct_change().rolling(window=period).std() * np.sqrt(252)


def gain_percentile(close: pd.Series, period: int = 250) -> pd.Series:
    """
    涨幅百分位：当前涨幅在过去M个周期中的百分位排名
    period: 回看窗口长度（默认250个交易日）
    """
    ret = close.pct_change()

    def _pct_rank(x):
        x = x[~np.isnan(x)]
        if len(x) == 0:
            return np.nan
        return np.sum(x <= x[-1]) / len(x)

    return ret.rolling(window=period, min_periods=period).apply(_pct_rank, raw=True)


def volume_percentile(volume: pd.Series, period: int = 250) -> pd.Series:
    """
    成交量百分位：当前成交量在过去N天中的百分位排名
    period: 回看窗口长度（默认250个交易日）
    """
    def _pct_rank(x):
        x = x[~np.isnan(x)]
        if len(x) == 0:
            return np.nan
        return np.sum(x <= x[-1]) / len(x)

    return volume.rolling(window=period, min_periods=period).apply(_pct_rank, raw=True)


def RSRS_slope(high: pd.Series, low: pd.Series, period: int = 18) -> pd.Series:
    """
    RSRS斜率：用每日最高价对最低价做线性回归的斜率beta
    采用解析公式: slope = Cov(high, low) / Var(low)
    period: 回归窗口长度（默认18个交易日）
    """
    hl = high * low
    l2 = low ** 2
    mean_h = high.rolling(window=period, min_periods=period).mean()
    mean_l = low.rolling(window=period, min_periods=period).mean()
    mean_hl = hl.rolling(window=period, min_periods=period).mean()
    mean_l2 = l2.rolling(window=period, min_periods=period).mean()
    cov = mean_hl - mean_h * mean_l
    var_l = mean_l2 - mean_l ** 2
    return cov / var_l


def RSRS_zscore(slope: pd.Series, period: int = 600) -> pd.Series:
    """
    RSRS标准分：斜率的z-score标准化
    zscore = (slope - rolling_mean) / rolling_std
    period: 标准化窗口长度（默认600个交易日）
    """
    mean = slope.rolling(window=period, min_periods=period).mean()
    std = slope.rolling(window=period, min_periods=period).std()
    return (slope - mean) / std


def RSRS_right_zscore(slope: pd.Series, period: int = 600) -> pd.Series:
    """
    RSRS右偏标准分：用标准分的右偏修正
    对z-score正半部分的分布标准差进行修正，消除右偏影响
    right_zscore = zscore * (std_all / std_positive)
    period: 标准化窗口长度（默认600个交易日）
    """
    z = RSRS_zscore(slope, period)

    def _right_scale(z_window):
        z_clean = z_window[~np.isnan(z_window)]
        z_pos = z_clean[z_clean > 0]
        if len(z_pos) < 2:
            return 1.0
        return np.std(z_clean, ddof=0) / np.std(z_pos, ddof=0)

    scale = z.rolling(window=period, min_periods=period).apply(_right_scale, raw=True)
    return z * scale


def momentum_std(close: pd.Series, window: int = 20) -> pd.Series:
    """
    动量标准差因子：(close - MA) / std
    类似Z-score，衡量价格偏离均线的标准差倍数
    LOF轮动策略使用
    """
    ma = close.rolling(window=window, min_periods=window).mean()
    std = close.rolling(window=window, min_periods=window).std()
    return (close - ma) / std


def wdm_momentum(close: pd.Series, shift: int = 12, smooth: int = 3) -> pd.Series:
    """
    五斗米动量因子：close / ref_avg * 100 - 100
    ref_avg = close.shift(shift).rolling(smooth).mean()
    五斗米动量策略使用
    """
    ref_avg = close.shift(shift).rolling(window=smooth, min_periods=smooth).mean()
    return close / ref_avg * 100 - 100


def volume_ratio_7(volume: pd.Series, limit: float = 2.0) -> pd.Series:
    """
    7日量比因子：volume / MA7(volume)
    超过 limit 时返回实际比值，否则返回 NaN（用于排除放量标的）
    RSRS动量策略使用
    """
    vol_ma7 = volume.rolling(window=7, min_periods=1).mean()
    ratio = volume / vol_ma7
    return np.where(ratio > limit, ratio, np.nan)


def rsrs_momentum_score(close: pd.Series, momentum_days: int = 20) -> pd.Series:
    """
    RSRS动量得分因子（纯得分）：加权对数回归
    1. 对 log(close) 做 weighted OLS（权重线性递增 1->2）
    2. 年化收益 * R^2 作为得分
    不包含连跌惩罚，惩罚请单独用 penalty_score() 添加
    RSRS动量策略使用
    """
    n = len(close)
    scores = np.full(n, np.nan)
    log_prices = np.log(close.values)
    x_vals = np.arange(momentum_days, dtype=float)
    weights = np.linspace(1, 2, momentum_days)
    w_mean = np.average(x_vals, weights=weights)
    w_std_sq = np.average((x_vals - w_mean) ** 2, weights=weights)
    w_std = np.sqrt(w_std_sq) if w_std_sq > 0 else 1.0
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
        scores[i] = annualized_return * r2
    return pd.Series(scores, index=close.index)


def rsrs_strength_full(high: pd.Series, low: pd.Series, close: pd.Series,
                       rsrs_window: int = 20, lookback_days: int = 250) -> pd.DataFrame:
    """
    RSRS强度因子（完整版）：low->high回归斜率的滚动统计
    1. 计算 rsrs_window 日 low->high 回归斜率
    2. 滚动 lookback_days 统计斜率均值/标准差
    3. 计算标准分：(cur_slope - beta) / abs(beta)，其中 beta = mean - 2*std
    返回 DataFrame: rsrs_strength, rsrs_pass
    RSRS动量策略使用
    """
    n = len(close)
    low_vals = low.values
    high_vals = high.values
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
    rsrs_pass = np.zeros(n, dtype=bool)

    for i in range(n):
        if i < rsrs_window - 1:
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
        rsrs_pass[i] = cur_slope > beta
        if rsrs_pass[i]:
            rsrs_strengths[i] = strength

    return pd.DataFrame({
        'rsrs_strength': rsrs_strengths,
        'rsrs_pass': rsrs_pass,
    }, index=close.index)


def penalty_score(close: pd.Series, days: int = 3, threshold: float = -0.05, penalty_value: float = -300) -> pd.Series:
    """
    惩罚项：最近days日任意一天跌幅<threshold，则返回penalty_value，否则返回0
    用于排序时惩罚近期大跌的标的
    days: 检查天数（默认3）
    threshold: 跌幅阈值（默认-0.05即-5%）
    penalty_value: 惩罚分数（默认-300）
    """
    daily_ret = close.pct_change()
    # 最近days日任意一天跌幅<threshold
    has_drop = (daily_ret < threshold).rolling(window=days, min_periods=1).max().fillna(0)
    return has_drop * penalty_value


def month_end(date_series: pd.Series) -> pd.Series:
    """
    判断是否月末（当月最后交易日）
    当下一个交易日的月份或年份与当前不同时，当前即为月末
    """
    dates = pd.to_datetime(date_series)
    next_dates = dates.shift(-1)
    is_end = (dates.dt.year != next_dates.dt.year) | (dates.dt.month != next_dates.dt.month)
    is_end = is_end & next_dates.notna()
    return is_end


def pre_holiday(date_series: pd.Series) -> pd.Series:
    """
    判断是否节前（国庆、春节等长假前最后一个交易日）
    当当前交易日与下一个交易日之间的日历天数>=4天时，
    视为节前最后一个交易日（正常周末间隔为3天：周五到周一）
    """
    dates = pd.to_datetime(date_series)
    next_dates = dates.shift(-1)
    gap = (next_dates - dates).dt.days
    return (gap >= 4) & gap.notna()


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有常用指标，添加到DataFrame中
    df必须包含: open, high, low, close, volume列
    """
    df = df.copy()

    # 均线系列
    for n in [5, 10, 20, 60, 120, 250]:
        df[f'MA_{n}'] = MA(df['close'], n)
        df[f'EMA_{n}'] = EMA(df['close'], n)

    # RSI
    for n in [6, 12, 14, 24]:
        df[f'RSI_{n}'] = RSI(df['close'], n)

    # MACD
    macd = MACD(df['close'])
    df['MACD_DIF'] = macd['DIF']
    df['MACD_DEA'] = macd['DEA']
    df['MACD_HIST'] = macd['MACD']

    # 布林带
    boll = BOLL(df['close'])
    df['BOLL_upper'] = boll['upper']
    df['BOLL_mid'] = boll['mid']
    df['BOLL_lower'] = boll['lower']

    # KDJ
    kdj = KDJ(df['high'], df['low'], df['close'])
    df['KDJ_K'] = kdj['K']
    df['KDJ_D'] = kdj['D']
    df['KDJ_J'] = kdj['J']

    # ATR
    for n in [14, 26]:
        df[f'ATR_{n}'] = ATR(df['high'], df['low'], df['close'], n)

    # 涨幅
    for n in [1, 3, 5, 10, 20, 60]:
        df[f'returns_{n}'] = returns(df['close'], n)

    # 波动率
    df['volatility_20'] = volatility(df['close'], 20)

    # 质量得分（加权动量R²）
    df['quality_score_20'] = quality_score(df['close'], period=20)

    # 涨幅百分位
    df['gain_percentile_250'] = gain_percentile(df['close'], period=250)

    # 成交量百分位
    df['volume_percentile_250'] = volume_percentile(df['volume'], period=250)

    # RSRS系列
    df['RSRS_slope'] = RSRS_slope(df['high'], df['low'], period=18)
    df['RSRS_zscore'] = RSRS_zscore(df['RSRS_slope'], period=600)
    df['RSRS_right_zscore'] = RSRS_right_zscore(df['RSRS_slope'], period=600)

    # ===========================
    #  旧版兼容指标（保持向后兼容）
    # ===========================
    # 小写列名兼容（旧版 backtester 使用 ma5/ma20 等）
    df['ma5'] = df['MA_5']
    df['ma10'] = df['MA_10']
    df['ma20'] = df['MA_20']
    df['ma60'] = df['MA_60']
    df['ma120'] = df['MA_120']
    df['ma250'] = df['MA_250']
    df['ema12'] = EMA(df['close'], 12)
    df['ema26'] = EMA(df['close'], 26)
    df['atr26'] = df['ATR_26']
    df['std20'] = df['close'].rolling(window=20).std()
    df['std60'] = df['close'].rolling(window=60).std()
    df['return_20'] = df['returns_20']
    df['return_21'] = df['returns_20']  # 近似
    df['daily_return'] = df['returns_1']
    df['boll_upper'] = df['BOLL_upper']
    df['boll_mid'] = df['BOLL_mid']
    df['boll_lower'] = df['BOLL_lower']
    df['bias5'] = BIAS(df['close'], 5)
    df['bias10'] = BIAS(df['close'], 10)
    df['bias20'] = BIAS(df['close'], 20)
    df['bias60'] = BIAS(df['close'], 60)

    # 均线位置（布尔）
    df['above_ma5'] = df['close'] > df['ma5']
    df['above_ma10'] = df['close'] > df['ma10']
    df['above_ma20'] = df['close'] > df['ma20']

    # 量比（volume_ratio）
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(window=7).mean()

    # momentum_score（旧版质量得分，与 quality_score 一致）
    df['momentum_score'] = df['quality_score_20']

    # std_momentum（旧版标准化动量）
    df['std_momentum'] = (df['close'] - df['ma20']) / df['std20']

    # rsrs_strength（旧版 RSRS 强度，对应 RSRS_slope）
    df['rsrs_strength'] = df['RSRS_slope']
    # rsrs_pass（旧版 RSRS 通过信号）
    df['rsrs_pass'] = df['RSRS_slope'] > 0.15

    # 大跌惩罚（旧版 big_drop_penalty）
    close = df['close']
    has_big_drop = (
        (close / close.shift(1) < 0.95) |
        (close.shift(1) / close.shift(2) < 0.95) |
        (close.shift(2) / close.shift(3) < 0.95)
    )
    df['big_drop_penalty'] = has_big_drop.astype(int) * -300

    return df

def compute_indicators_for_df(df: pd.DataFrame, expressions: list) -> pd.DataFrame:
    """
    按需计算指标：只解析表达式中用到的指标，大幅提速
    expressions: 策略中的公式/规则列表，如 ['(MACD_DIF(12,26,9) / ATR(26)) * 100', 'close > MA(5)', ...]
    """
    import re
    df = df.copy()
    c = df['close']
    h = df['high']
    l = df['low']
    v = df['volume']
    
    # 提取表达式中所有指标调用
    # 匹配 pattern: MA(5), ATR(26), MACD_DIF(12,26,9), returns(20), etc.
    pattern = r'(\w+)\s*\(([^)]*)\)'
    needed = {}
    for expr in expressions:
        if not expr:
            continue
        for m in re.finditer(pattern, expr):
            func_name = m.group(1)
            args_str = m.group(2).strip()
            args = [int(a.strip()) if a.strip().isdigit() else a.strip()
                    for a in args_str.split(',') if a.strip()]
            key = (func_name, tuple(args))
            needed[key] = (func_name, args)
        
        # 也识别直接列名引用（如 MA_5, RSI_14, returns_20 等），自动映射为函数调用
        col_name_map = {
            'MACD_DIF': ('MACD_DIF', [12, 26, 9]),
            'MACD_DEA': ('MACD_DEA', [12, 26, 9]),
            'MACD_HIST': ('MACD_HIST', [12, 26, 9]),
            'BOLL': ('BOLL', [20]),
            'KDJ_K': ('KDJ_K', [9, 3, 3]),
            'KDJ_D': ('KDJ_D', [9, 3, 3]),
            'KDJ_J': ('KDJ_J', [9, 3, 3]),
            'RSRS_slope': ('RSRS_slope', [18]),
            'RSRS_zscore': ('RSRS_zscore', [600]),
            'RSRS_right_zscore': ('RSRS_right_zscore', [600]),
        }
        # 匹配无下划线列名
        for col_name, (func_name, args) in col_name_map.items():
            if col_name in expr and col_name not in df.columns:
                key = (func_name, tuple(args))
                if key not in needed:
                    needed[key] = (func_name, args)
        # 匹配带下划线的列名（如 MA_5, RSI_14 等）
        for m in re.finditer(r'\b(MA|EMA|RSI|ATR|returns|BIAS|volatility|quality_score|gain_percentile|volume_percentile)_(\d+)\b', expr):
            func_name = m.group(1)
            n = int(m.group(2))
            key = (func_name, (n,))
            if key not in needed:
                needed[key] = (func_name, [n])
        # 匹配 BOLL_upper_20_2 等
        for m in re.finditer(r'\bBOLL_(upper|lower)_(\d+)_(\d+)\b', expr):
            func_name = f'BOLL_{m.group(1)}'
            n = int(m.group(2))
            std = int(m.group(3))
            key = (func_name, (n, std))
            if key not in needed:
                needed[key] = (func_name, [n, std])
        
        # 旧版兼容指标列名（momentum_score, volume_ratio, rsrs_pass, rsrs_strength, above_ma5, above_ma10, momentum_std）
        if 'momentum_score' in expr and 'momentum_score' not in df.columns:
            df['momentum_score'] = quality_score(c, 20)
        if 'volume_ratio' in expr and 'volume_ratio' not in df.columns:
            volume_ma = v.rolling(window=20, min_periods=1).mean()
            df['volume_ratio'] = v / volume_ma
        if 'rsrs_pass' in expr and 'rsrs_pass' not in df.columns:
            if 'RSRS_slope' not in df.columns:
                df['RSRS_slope'] = RSRS_slope(h, l, 18)
            df['rsrs_pass'] = df['RSRS_slope'] > 0.15
        if 'rsrs_strength' in expr and 'rsrs_strength' not in df.columns:
            if 'RSRS_slope' not in df.columns:
                df['RSRS_slope'] = RSRS_slope(h, l, 18)
            df['rsrs_strength'] = df['RSRS_slope'] / df['RSRS_slope'].rolling(window=20, min_periods=1).std()
        if 'above_ma5' in expr and 'above_ma5' not in df.columns:
            if 'MA_5' not in df.columns:
                df['MA_5'] = MA(c, 5)
            df['above_ma5'] = c > df['MA_5']
        if 'above_ma10' in expr and 'above_ma10' not in df.columns:
            if 'MA_10' not in df.columns:
                df['MA_10'] = MA(c, 10)
            df['above_ma10'] = c > df['MA_10']
        if 'momentum_std' in expr and 'momentum_std' not in df.columns:
            df['momentum_std'] = momentum_std(c, 20)
        if 'std20' in expr and 'std20' not in df.columns:
            df['std20'] = c.rolling(window=20, min_periods=20).std()
        if 'return_20' in expr and 'return_20' not in df.columns:
            df['return_20'] = c / c.shift(20) - 1
        if 'daily_ret' in expr and 'daily_ret' not in df.columns:
            df['daily_ret'] = c.pct_change()
        if 'penalty' in expr and 'penalty' not in df.columns:
            df['penalty'] = penalty_score(c, 3, -0.03, -8)
        if 'wdm_momentum' in expr and 'wdm_momentum' not in df.columns:
            df['wdm_momentum'] = wdm_momentum(c, 12, 3)
        if 'rsrs_momentum_score' in expr and 'rsrs_momentum_score' not in df.columns:
            df['rsrs_momentum_score'] = rsrs_momentum_score(c, 20)
        if 'momentum_score' in expr and 'momentum_score' not in df.columns:
            # RSRS动量得分 = 加权回归得分 + 连跌惩罚
            df['momentum_score'] = rsrs_momentum_score(c, 20) + penalty_score(c, 3, -0.05, -8)
        if 'volume_ratio' in expr and 'volume_ratio' not in df.columns:
            # 判断是 7日量比还是 20日量比
            if 'volume_ratio_7' in expr:
                df['volume_ratio'] = volume_ratio_7(v, 2.0)
            else:
                volume_ma = v.rolling(window=20, min_periods=1).mean()
                df['volume_ratio'] = v / volume_ma
        if 'rsrs_strength' in expr and 'rsrs_strength' not in df.columns:
            rsrs_df = rsrs_strength_full(h, l, c, 20, 250)
            df['rsrs_strength'] = rsrs_df['rsrs_strength']
            df['rsrs_pass'] = rsrs_df['rsrs_pass']
    
    # 去重并按依赖排序
    computed = {}
    
    def _compute(func_name, args):
        key = (func_name, tuple(args))
        if key in computed:
            return computed[key]
        
        # MA
        if func_name == 'MA':
            n = args[0]
            col = f'MA_{n}'
            if col not in df.columns:
                df[col] = MA(c, n)
            computed[key] = col
            return col
        
        # EMA
        if func_name == 'EMA':
            n = args[0]
            col = f'EMA_{n}'
            if col not in df.columns:
                df[col] = EMA(c, n)
            computed[key] = col
            return col
        
        # MACD_DIF
        if func_name == 'MACD_DIF':
            fast, slow, signal = args[0], args[1], args[2]
            col = 'MACD_DIF'
            if col not in df.columns:
                ema_f = EMA(c, fast)
                ema_s = EMA(c, slow)
                df[col] = ema_f - ema_s
            computed[key] = col
            return col
        
        # MACD_DEA
        if func_name == 'MACD_DEA':
            fast, slow, signal = args[0], args[1], args[2]
            col = 'MACD_DEA'
            if col not in df.columns:
                ema_f = EMA(c, fast)
                ema_s = EMA(c, slow)
                dif = ema_f - ema_s
                df[col] = EMA(dif, signal)
            computed[key] = col
            return col
        
        # MACD_HIST
        if func_name == 'MACD_HIST':
            fast, slow, signal = args[0], args[1], args[2]
            col = 'MACD_HIST'
            if col not in df.columns:
                ema_f = EMA(c, fast)
                ema_s = EMA(c, slow)
                dif = ema_f - ema_s
                dea = EMA(dif, signal)
                df[col] = (dif - dea) * 2
            computed[key] = col
            return col
        
        # RSI
        if func_name == 'RSI':
            n = args[0]
            col = f'RSI_{n}'
            if col not in df.columns:
                df[col] = RSI(c, n)
            computed[key] = col
            return col
        
        # ATR
        if func_name == 'ATR':
            n = args[0]
            col = f'ATR_{n}'
            if col not in df.columns:
                df[col] = ATR(h, l, c, n)
            computed[key] = col
            return col
        
        # BOLL
        if func_name == 'BOLL':
            n = args[0]
            col = 'BOLL'
            if col not in df.columns:
                df['BOLL'] = MA(c, n)
            computed[key] = 'BOLL'
            return 'BOLL'
        
        # BOLL_upper
        if func_name == 'BOLL_upper':
            n, std_dev = args[0], args[1] if len(args) > 1 else 2
            col = f'BOLL_upper_{n}_{std_dev}'
            if col not in df.columns:
                mid = MA(c, n)
                std = c.rolling(window=n).std()
                df[col] = mid + std_dev * std
            computed[key] = col
            return col
        
        # BOLL_lower
        if func_name == 'BOLL_lower':
            n, std_dev = args[0], args[1] if len(args) > 1 else 2
            col = f'BOLL_lower_{n}_{std_dev}'
            if col not in df.columns:
                mid = MA(c, n)
                std = c.rolling(window=n).std()
                df[col] = mid - std_dev * std
            computed[key] = col
            return col
        
        # KDJ_K
        if func_name == 'KDJ_K':
            n, m1, m2 = args[0], args[1], args[2]
            col = 'KDJ_K'
            if col not in df.columns:
                kdj = KDJ(h, l, c, n, m1, m2)
                df['KDJ_K'] = kdj['K']
                df['KDJ_D'] = kdj['D']
                df['KDJ_J'] = kdj['J']
            computed[key] = col
            return col
        
        # KDJ_D
        if func_name == 'KDJ_D':
            n, m1, m2 = args[0], args[1], args[2]
            col = 'KDJ_D'
            if col not in df.columns:
                kdj = KDJ(h, l, c, n, m1, m2)
                df['KDJ_K'] = kdj['K']
                df['KDJ_D'] = kdj['D']
                df['KDJ_J'] = kdj['J']
            computed[key] = col
            return col
        
        # KDJ_J
        if func_name == 'KDJ_J':
            n, m1, m2 = args[0], args[1], args[2]
            col = 'KDJ_J'
            if col not in df.columns:
                kdj = KDJ(h, l, c, n, m1, m2)
                df['KDJ_K'] = kdj['K']
                df['KDJ_D'] = kdj['D']
                df['KDJ_J'] = kdj['J']
            computed[key] = col
            return col
        
        # returns
        if func_name == 'returns':
            n = args[0]
            col = f'returns_{n}'
            if col not in df.columns:
                df[col] = returns(c, n)
            computed[key] = col
            return col
        
        # BIAS
        if func_name == 'BIAS':
            n = args[0]
            col = f'BIAS_{n}'
            if col not in df.columns:
                df[col] = BIAS(c, n)
            computed[key] = col
            return col
        
        # volatility
        if func_name == 'volatility':
            n = args[0]
            col = f'volatility_{n}'
            if col not in df.columns:
                df[col] = volatility(c, n)
            computed[key] = col
            return col
        
        # quality_score
        if func_name == 'quality_score':
            n = args[0]
            col = f'quality_score_{n}'
            if col not in df.columns:
                df[col] = quality_score(c, n)
            computed[key] = col
            return col
        
        # gain_percentile
        if func_name == 'gain_percentile':
            n = args[0]
            col = f'gain_percentile_{n}'
            if col not in df.columns:
                df[col] = gain_percentile(c, n)
            computed[key] = col
            return col
        
        # volume_percentile
        if func_name == 'volume_percentile':
            n = args[0]
            col = f'volume_percentile_{n}'
            if col not in df.columns:
                df[col] = volume_percentile(v, n)
            computed[key] = col
            return col
        
        # RSRS_slope
        if func_name == 'RSRS_slope':
            n = args[0]
            col = 'RSRS_slope'
            if col not in df.columns:
                df['RSRS_slope'] = RSRS_slope(h, l, n)
            computed[key] = col
            return col
        
        # RSRS_zscore
        if func_name == 'RSRS_zscore':
            n = args[0] if args else 600
            col = 'RSRS_zscore'
            if col not in df.columns:
                if 'RSRS_slope' not in df.columns:
                    df['RSRS_slope'] = RSRS_slope(h, l, 18)
                df['RSRS_zscore'] = RSRS_zscore(df['RSRS_slope'], n)
            computed[key] = col
            return col
        
        # RSRS_right_zscore
        if func_name == 'RSRS_right_zscore':
            n = args[0] if args else 600
            col = 'RSRS_right_zscore'
            if col not in df.columns:
                if 'RSRS_slope' not in df.columns:
                    df['RSRS_slope'] = RSRS_slope(h, l, 18)
                df['RSRS_right_zscore'] = RSRS_right_zscore(df['RSRS_slope'], n)
            computed[key] = col
            return col
        
        # 未知指标
        computed[key] = func_name
        return func_name
    
    # 计算所有需要的指标
    for key in needed:
        func_name, args = needed[key]
        _compute(func_name, args)
    
    return df

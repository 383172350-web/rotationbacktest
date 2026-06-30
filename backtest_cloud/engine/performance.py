"""
绩效计算和Matplotlib图表生成
"""

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.dates as mdates

# ── 中文字体设置 ──
font_candidates = ['Microsoft YaHei', 'SimHei', 'WenQuanYi Zen Hei']
available_fonts = [f.name for f in fm.fontManager.ttflist]
selected_font = None
for fc in font_candidates:
    if fc in available_fonts:
        selected_font = fc
        break
if selected_font:
    matplotlib.rcParams['font.family'] = [selected_font, 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False


def compute_performance(nav_df) -> dict:
    """
    计算策略绩效指标。

    Parameters
    ----------
    nav_df : DataFrame
        index 为 datetime，有 nav 列（已归一化从 1.0 开始）。

    Returns
    -------
    dict
        total_return, annual_return, max_dd, max_dd_date, sharpe, calmar,
        start_date, end_date, trading_days
    """
    if nav_df.empty or nav_df['nav'].iloc[0] == 0:
        return {
            'total_return': 0.0,
            'annual_return': 0.0,
            'max_dd': 0.0,
            'max_dd_date': None,
            'sharpe': 0.0,
            'calmar': 0.0,
            'start_date': None,
            'end_date': None,
            'trading_days': 0,
        }

    nav = nav_df['nav']
    start_date = nav_df.index[0]
    end_date = nav_df.index[-1]
    trading_days = len(nav_df)

    # 总收益率
    total_return = (nav.iloc[-1] / nav.iloc[0] - 1) * 100

    # 年化收益率
    years = (end_date - start_date).days / 365.25
    if years <= 0:
        annual_return = 0.0
    else:
        annual_return = ((nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1) * 100

    # 日收益率
    daily_returns = nav.pct_change().dropna()

    # 回撤序列
    cummax = nav.cummax()
    drawdown = (nav - cummax) / cummax
    max_dd = drawdown.min() * 100  # 负数
    max_dd_idx = drawdown.idxmin()
    max_dd_date = max_dd_idx

    # 夏普比率（无风险利率 3%）
    rf_daily = 0.03 / 252
    excess_returns = daily_returns - rf_daily
    if excess_returns.std() == 0:
        sharpe = 0.0
    else:
        sharpe = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)

    # 卡尔玛比率
    if max_dd == 0:
        calmar = 0.0
    else:
        calmar = annual_return / abs(max_dd)

    return {
        'total_return': round(total_return, 2),
        'annual_return': round(annual_return, 2),
        'max_dd': round(max_dd, 2),
        'max_dd_date': max_dd_date,
        'sharpe': round(sharpe, 2),
        'calmar': round(calmar, 2),
        'start_date': start_date,
        'end_date': end_date,
        'trading_days': trading_days,
    }


def plot_nav_curve(nav_df, benchmark_df=None) -> matplotlib.figure.Figure:
    """
    绘制净值曲线图。

    Parameters
    ----------
    nav_df : DataFrame
        index 为 datetime，有 nav 列。
    benchmark_df : DataFrame, optional
        index 为 datetime，有 nav 列，基准净值。

    Returns
    -------
    matplotlib.figure.Figure
    """
    fig, ax = plt.subplots(figsize=(12, 5))

    # 绘制策略净值
    ax.plot(nav_df.index, nav_df['nav'], label='策略净值', linewidth=1.2)

    # 绘制基准净值
    if benchmark_df is not None and not benchmark_df.empty:
        # 对齐基准起始点，归一化到策略同一起点
        aligned_bench = benchmark_df['nav'] / benchmark_df['nav'].iloc[0] * nav_df['nav'].iloc[0]
        ax.plot(benchmark_df.index, aligned_bench, label='基准净值',
                linewidth=1.0, linestyle='--', alpha=0.7)

    # 计算绩效标注
    perf = compute_performance(nav_df)
    textstr = (
        f"总收益: {perf['total_return']:.2f}%\n"
        f"年化: {perf['annual_return']:.2f}%\n"
        f"最大回撤: {perf['max_dd']:.2f}%\n"
        f"夏普: {perf['sharpe']:.2f}"
    )
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.02, 0.97, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props)

    ax.set_xlabel('日期')
    ax.set_ylabel('净值')
    ax.set_title('净值曲线')
    ax.legend(loc='upper right')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    fig.autofmt_xdate()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    return fig


def plot_drawdown(nav_df) -> matplotlib.figure.Figure:
    """
    绘制回撤图。

    Parameters
    ----------
    nav_df : DataFrame
        index 为 datetime，有 nav 列。

    Returns
    -------
    matplotlib.figure.Figure
    """
    fig, ax = plt.subplots(figsize=(12, 3))

    nav = nav_df['nav']
    cummax = nav.cummax()
    drawdown = (nav - cummax) / cummax * 100  # 百分比

    # 蓝色填充
    ax.fill_between(nav_df.index, drawdown, 0, color='steelblue', alpha=0.5, label='回撤')

    # 标注最大回撤
    max_dd_idx = drawdown.idxmin()
    max_dd_val = drawdown.min()
    ax.annotate(
        f'最大回撤: {max_dd_val:.2f}%',
        xy=(max_dd_idx, max_dd_val),
        xytext=(max_dd_idx, max_dd_val * 0.5),
        arrowprops=dict(arrowstyle='->', color='red'),
        fontsize=9, color='red', fontweight='bold',
    )

    # 标注当前回撤
    current_dd = drawdown.iloc[-1]
    ax.annotate(
        f'当前回撤: {current_dd:.2f}%',
        xy=(nav_df.index[-1], current_dd),
        xytext=(nav_df.index[-1], current_dd * 0.5),
        arrowprops=dict(arrowstyle='->', color='darkorange'),
        fontsize=9, color='darkorange', fontweight='bold',
    )

    ax.set_xlabel('日期')
    ax.set_ylabel('回撤 (%)')
    ax.set_title('回撤图')
    ax.legend(loc='lower left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    fig.autofmt_xdate()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    return fig


def compute_yearly_returns(nav_df) -> pd.DataFrame:
    """
    按年统计收益率和年内最大回撤。

    Parameters
    ----------
    nav_df : DataFrame
        index 为 datetime，有 nav 列。

    Returns
    -------
    DataFrame
        列: year, return_pct, max_dd_pct
    """
    if nav_df.empty:
        return pd.DataFrame(columns=['year', 'return_pct', 'max_dd_pct'])

    records = []
    for year, group in nav_df.resample('YE'):
        if group.empty:
            continue
        nav_year = group['nav']
        ret = (nav_year.iloc[-1] / nav_year.iloc[0] - 1) * 100
        cummax = nav_year.cummax()
        dd = ((nav_year - cummax) / cummax * 100).min()
        records.append({
            'year': year.year,
            'return_pct': round(ret, 2),
            'max_dd_pct': round(dd, 2),
        })

    return pd.DataFrame(records, columns=['year', 'return_pct', 'max_dd_pct'])

# -*- coding: utf-8 -*-
"""
数据加载模块 —— 统一数据获取方式（本地 pkl + 在线多源降级）
与 rotation-web 保持一致：交易时间强制在线，非交易时间优先本地+核对收盘价
"""
from __future__ import print_function, division

import os
import re
import datetime
import pandas as pd
import subprocess

# ============================================================
#  默认 pkl 目录
# ============================================================
PKL_DIR = os.environ.get(
    "PKL_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ETF", "1d")
)

# ============================================================
#  ETF 中文名称字典  (thscode -> name)
# ============================================================
ETF_NAMES = {
    # ---- 宽基 ----
    "510050.SH": "上证50",
    "510300.SH": "沪深300",
    "510500.SH": "中证500",
    "512100.SH": "中证1000",
    "159915.SZ": "创业板",
    "159949.SZ": "创业板50",
    "159958.SZ": "创业板ETF",
    "159922.SZ": "中证500ETF",
    "588000.SH": "科创50",
    "588220.SH": "科创100",
    "562500.SH": "中证2000",
    "159531.SZ": "中证2000ETF",
    "588250.SH": "科创医药",
    "159905.SZ": "深证红利",
    "510880.SH": "红利ETF",
    "512890.SH": "红利低波",
    # ---- 商品 / 另类 ----
    "159980.SZ": "有色ETF",
    "159981.SZ": "能源化工",
    "159985.SZ": "豆粕ETF",
    "501018.SH": "南方原油",
    "518880.SH": "黄金ETF",
    # ---- 债券 / 货币 ----
    "511880.SH": "银华日利",
    "511260.SH": "30年国债",
    "511010.SH": "国债ETF",
    "511090.SH": "30年国债ETF",
    # ---- 跨境 ----
    "513030.SH": "德国ETF",
    "513050.SH": "中概互联",
    "513100.SH": "纳指ETF",
    "513500.SH": "标普500",
    "513520.SH": "日经ETF",
    "513080.SH": "法国ETF",
    "513060.SH": "恒生ETF",
    "159740.SZ": "恒生科技",
    "513310.SH": "中韩半导体",
    # ---- 医药 ----
    "159938.SZ": "医药ETF",
    "512010.SH": "医药ETF",
    "159992.SZ": "创新药",
    "515120.SH": "创新药",
    "159898.SZ": "医疗器械",
    "159883.SZ": "医疗器械",
    # ---- 科技 / 半导体 ----
    "159509.SZ": "科创芯片",
    "588200.SH": "科创芯片",
    "512480.SH": "半导体",
    "159995.SZ": "半导体",
    "515070.SH": "人工智能",
    "159819.SZ": "人工智能",
    "515880.SH": "通信ETF",
    "515050.SH": "通信ETF国泰",
    "515000.SH": "科技ETF",
    "159611.SZ": "云计算",
    "516510.SH": "云计算",
    "515990.SH": "软件ETF",
    "159852.SZ": "软件ETF",
    "159766.SZ": "消费电子",
    "159732.SZ": "电子ETF",
    "159997.SZ": "电子ETF",
    # ---- 游戏 / 娱乐 / VR ----
    "159869.SZ": "游戏ETF",
    "516010.SH": "游戏ETF",
    "159786.SZ": "虚拟现实",
    # ---- 机器人 / 智造 ----
    "159551.SZ": "机器人",
    "562500.SH": "机器人",
    "516800.SH": "智能制造",
    "159380.SZ": "智能制造",
    # ---- 军工 ----
    "512660.SH": "军工ETF",
    "512560.SH": "军工ETF",
    # ---- 工业 ----
    "159967.SZ": "工业母机",
    "159667.SZ": "工业母机",
    "560913.SH": "工程机械",
    "159542.SZ": "工程机械",
    # ---- 新材料 ----
    "588010.SH": "科创新材料",
    "159871.SZ": "科创新材料",
    # ---- 新能源 ----
    "515790.SH": "光伏ETF",
    "159806.SZ": "新能源车",
    "515700.SH": "新能源车",
    "159755.SZ": "电池ETF",
    "159995.SZ": "电池ETF",
    "159566.SZ": "储能电池",
    # ---- 信息 / 数据 / 电信 ----
    "515400.SH": "大数据",
    "560200.SH": "电信ETF",
    "563010.SH": "电信ETF",
    # ---- 消费 / 白酒 ----
    "159928.SZ": "消费ETF",
    "512690.SH": "白酒ETF",
    # ---- 金融 ----
    "512070.SH": "非银ETF",
    # ---- LOF ----
    "163402.SZ": "兴全趋势LOF",
    "163417.SZ": "兴全合宜LOF",
    "161903.SZ": "万家行业优选LOF",
    "162703.SZ": "广发小盘LOF",
    "161005.SZ": "富国天惠LOF",
}

# pkl 文件名正则: {code}_{suffix}_1d.pkl
_PKL_PATTERN = re.compile(r"^(\d{6})_([A-Z]{2})_1d\.pkl$")


# ============================================================
#  scan_pkl_dir
# ============================================================
def scan_pkl_dir(pkl_dir=None):
    """扫描 pkl 目录，返回 [{code, suffix, thscode, name}] 列表，按 code 排序。

    当本地目录不存在时，自动使用 ETF_NAMES 生成默认股票池，
    支持 Streamlit Cloud 等无本地数据环境。

    Parameters
    ----------
    pkl_dir : str, optional
        pkl 文件所在目录，默认使用 PKL_DIR。

    Returns
    -------
    list[dict]
        每个 dict 含 code / suffix / thscode / name 四个字段。
    """
    if pkl_dir is None:
        pkl_dir = PKL_DIR

    if os.path.isdir(pkl_dir):
        items = []
        for fname in os.listdir(pkl_dir):
            m = _PKL_PATTERN.match(fname)
            if not m:
                continue
            code = m.group(1)
            suffix = m.group(2)
            thscode = f"{code}.{suffix}"
            name = ETF_NAMES.get(thscode, code)
            items.append({
                "code": code,
                "suffix": suffix,
                "thscode": thscode,
                "name": name,
            })
        items.sort(key=lambda x: x["code"])
        return items
    else:
        # 本地目录不存在：使用 ETF_NAMES 生成默认股票池
        items = []
        for thscode, name in ETF_NAMES.items():
            parts = thscode.split('.')
            if len(parts) == 2:
                items.append({
                    "code": parts[0],
                    "suffix": parts[1],
                    "thscode": thscode,
                    "name": name,
                })
        items.sort(key=lambda x: x["code"])
        return items


# ============================================================
#  _download_from_akshare
# ============================================================
def _download_from_akshare(code, suffix, start_date=None, end_date=None):
    """使用 akshare 下载 ETF 日线数据，返回标准格式 DataFrame。

    参数:
        code: 6位代码
        suffix: SH/SZ
        start_date: 开始日期 "YYYYMMDD"，默认20000101
        end_date: 结束日期 "YYYYMMDD"，默认20991231

    返回 DataFrame 索引为 datetime，列 open/high/low/close/volume。
    下载失败返回 None。
    """
    try:
        import akshare as ak
    except Exception:
        return None

    try:
        ak_code = f"{suffix.lower()}{code}"
        start = start_date if start_date else "20000101"
        end = end_date if end_date else "20991231"
        df = ak.fund_etf_hist_em(
            symbol=code,
            period="daily",
            start_date=start,
            end_date=end,
            adjust="qfq"
        )
        if df is None or df.empty:
            return None

        # 标准化列名
        df = df.rename(columns={
            '日期': 'time',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
        })
        df['time'] = pd.to_datetime(df['time'])
        df = df.set_index('time')[['open', 'high', 'low', 'close', 'volume']]
        df = df[(df['close'] > 0) & (df['open'] > 0) & (df['volume'] > 0)]
        return df
    except Exception:
        return None


# ============================================================
#  _download_akshare_recent (用于数据新鲜度核对)
# ============================================================
def _download_akshare_recent(code, suffix, days=10):
    """下载最近N天数据，用于核对本地数据新鲜度"""
    end = datetime.datetime.now().strftime('%Y%m%d')
    start = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y%m%d')
    return _download_from_akshare(code, suffix, start_date=start, end_date=end)


# ============================================================
#  _is_trading_time
# ============================================================
def _is_trading_time():
    """判断当前是否在交易时间（9:30-15:00）"""
    now = datetime.datetime.now()
    t = now.time()
    return datetime.time(9, 30) <= t <= datetime.time(15, 0)


# ============================================================
#  _download_westock
# ============================================================
def _download_westock(code, suffix):
    """使用 westock 命令行工具获取数据"""
    try:
        cmd = f"npx -y westock-data-clawhub@1.0.4 kline {suffix.lower()}{code} --period day --limit 3000 --fq qfq"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None

        # 解析 markdown 表格
        lines = result.stdout.strip().split('\n')
        table_start = -1
        for i, line in enumerate(lines):
            if '|' in line and (i + 1 < len(lines) and '---' in lines[i + 1]):
                table_start = i
                break
        if table_start == -1:
            return None

        header_line = lines[table_start].strip()
        if header_line.startswith('|'): header_line = header_line[1:]
        if header_line.endswith('|'): header_line = header_line[:-1]
        headers = [h.strip() for h in header_line.split('|')]

        rows = []
        for line in lines[table_start + 2:]:
            line = line.strip()
            if not line or '|' not in line:
                continue
            if line.startswith('|'): line = line[1:]
            if line.endswith('|'): line = line[:-1]
            values = [v.strip() for v in line.split('|')]
            if len(values) == len(headers):
                rows.append(dict(zip(headers, values)))

        if not rows:
            return None

        df = pd.DataFrame(rows)
        # 标准化列名
        col_map = {'Date': 'time', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df['time'] = pd.to_datetime(df['time'])
        df = df.set_index('time')[['open', 'high', 'low', 'close', 'volume']]
        df = df[(df['close'] > 0) & (df['open'] > 0)]
        return df
    except Exception:
        return None


# ============================================================
#  _download_eastmoney_direct
# ============================================================
def _download_eastmoney_direct(code, suffix):
    """直接调用东方财富API获取ETF K线，无需akshare依赖"""
    import requests

    # secid: 1=上海, 0=深圳
    secid = "1" if suffix == "SH" else "0"
    beg = "20000101"
    end = "20991231"

    url = (
        f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={secid}.{code}"
        f"&fields1=f1,f2,f3,f4,f5,f6"
        f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        f"&klt=101&fqt=1&beg={beg}&end={end}"
    )

    try:
        resp = requests.get(url, timeout=30)
        data = resp.json()

        if not data.get("data") or not data["data"].get("klines"):
            return None

        klines = data["data"]["klines"]
        rows = []
        for line in klines:
            parts = line.split(",")
            if len(parts) >= 6:
                rows.append({
                    "time": parts[0],
                    "open": float(parts[1]),
                    "close": float(parts[2]),
                    "low": float(parts[3]),
                    "high": float(parts[4]),
                    "volume": float(parts[5]),
                })

        if not rows:
            return None

        df = pd.DataFrame(rows)
        df['time'] = pd.to_datetime(df['time'])
        df = df.set_index('time')[['open', 'high', 'low', 'close', 'volume']]
        df = df[(df['close'] > 0) & (df['open'] > 0) & (df['volume'] > 0)]
        return df
    except Exception:
        return None


# ============================================================
#  _download_tencent
# ============================================================
def _download_tencent(code, suffix):
    """直接调用腾讯API获取ETF K线"""
    import requests

    tencent_code = f"{suffix.lower()}{code}"
    start_date = "2000-01-01"
    end_date = "2099-12-31"

    url = (
        f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        f"?param={tencent_code},day,{start_date},{end_date},640,qfq"
    )

    try:
        resp = requests.get(url, timeout=30)
        data = resp.json()

        key = f"{suffix.lower()}{code}"
        if not data.get("data") or not data["data"].get(key):
            return None

        klines = data["data"][key].get("day", [])
        if not klines:
            return None

        rows = []
        for item in klines:
            if isinstance(item, list) and len(item) >= 5:
                rows.append({
                    "time": item[0],
                    "open": float(item[1]),
                    "close": float(item[2]),
                    "low": float(item[3]),
                    "high": float(item[4]),
                    "volume": float(item[5]) if len(item) > 5 else 0,
                })

        if not rows:
            return None

        df = pd.DataFrame(rows)
        df['time'] = pd.to_datetime(df['time'])
        df = df.set_index('time')[['open', 'high', 'low', 'close', 'volume']]
        df = df[(df['close'] > 0) & (df['open'] > 0)]
        return df
    except Exception:
        return None


# ============================================================
#  _download_findb
# ============================================================
def _download_findb(code, suffix):
    """使用 findb API 获取数据"""
    import requests
    import datetime

    TOKEN = "sk_live_7orj6tBMMNiB.4eAcaTYc65icYsacCZksDfkHqvVvQyKfdbPf0X8aiR0"

    start_dt = datetime.datetime.strptime("2000-01-01", "%Y-%m-%d")
    end_dt = datetime.datetime.strptime("2099-12-31", "%Y-%m-%d")
    days = (end_dt - start_dt).days + 1
    limit = max(days, 3000)

    url = f"https://api.jiucaicat.icu:8443/api/bars?code={code}.{suffix}&freq=daily&limit={limit}&order=desc"
    headers = {"Authorization": f"Bearer {TOKEN}"}

    try:
        resp = requests.get(url, headers=headers, timeout=60)
        data = resp.json()

        records = data.get("data", []) if isinstance(data, dict) else data
        if not records or not isinstance(records, list):
            return None

        df = pd.DataFrame(records)
        df.columns = [c.lower() for c in df.columns]

        df = df.rename(columns={
            'datetime': 'time',
            'time': 'time',
        })

        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col not in df.columns:
                return None

        df['time'] = pd.to_datetime(df['time'])
        df = df.set_index('time')[['open', 'high', 'low', 'close', 'volume']]
        df = df[(df['close'] > 0) & (df['open'] > 0)]
        return df
    except Exception:
        return None


# ============================================================
#  _try_all_sources
# ============================================================
def _try_all_sources(code, suffix):
    """尝试所有数据源，按优先级依次尝试，返回第一个成功的 DataFrame。"""
    sources = [
        _download_from_akshare,
        _download_eastmoney_direct,
        _download_tencent,
        _download_findb,
        _download_westock,
    ]
    for source in sources:
        try:
            df = source(code, suffix)
            if df is not None and not df.empty:
                return df
        except Exception:
            continue
    return None


# ============================================================
#  _save_pkl
# ============================================================
def _save_pkl(code, suffix, df, pkl_dir=None):
    """将 DataFrame 保存为 pkl 格式，与现有数据格式一致。
    """
    if df is None or df.empty:
        return
    if pkl_dir is None:
        pkl_dir = PKL_DIR

    os.makedirs(pkl_dir, exist_ok=True)
    pkl_file = os.path.join(pkl_dir, f"{code}_{suffix}_1d.pkl")

    try:
        # 转换为现有格式：stime(YYYYMMDD字符串) 作为索引
        save_df = df.reset_index()
        save_df['stime'] = save_df['time'].dt.strftime('%Y%m%d')
        save_df = save_df.set_index('stime')[['open', 'high', 'low', 'close', 'volume']]
        save_df.to_pickle(pkl_file)
    except Exception:
        pass


# ============================================================
#  load_pkl_data —— 统一数据获取（与 rotation-web 保持一致）
# ============================================================
def load_pkl_data(code, suffix, pkl_dir=None, try_online=True):
    """加载单个 ETF 数据，统一为 rotation-web 数据获取方式。

    智能策略：
    - 交易时间（9:30-15:00）：始终从在线下载最新数据（多源自动降级）
    - 非交易时间：优先本地 pkl，核对收盘价是否一致，不一致则强制更新
    - 下载成功后自动保存到本地 pkl

    Parameters
    ----------
    code : str
        6 位代码，如 "510300"。
    suffix : str
        交易所后缀，如 "SH" / "SZ"。
    pkl_dir : str, optional
        pkl 文件所在目录，默认使用 PKL_DIR。
    try_online : bool, default True
        是否允许在线下载。

    Returns
    -------
    pd.DataFrame or None
        索引为 datetime，列为 open/high/low/close/volume。
    """
    if pkl_dir is None:
        pkl_dir = PKL_DIR

    today = pd.Timestamp(datetime.date.today())

    # ========== 交易时间：强制在线获取（多源自动降级）==========
    if _is_trading_time() and try_online:
        df = _try_all_sources(code, suffix)
        if df is not None and not df.empty:
            _save_pkl(code, suffix, df, pkl_dir)
        return df

    # ========== 非交易时间：优先本地，核对收盘价新鲜度 ==========
    pkl_file = os.path.join(pkl_dir, f"{code}_{suffix}_1d.pkl")

    if os.path.exists(pkl_file):
        try:
            df_local = pd.read_pickle(pkl_file).reset_index()
            df_local["time"] = pd.to_datetime(df_local["stime"].astype(str), format="%Y%m%d")
            df_local = df_local[(df_local["close"] > 0) & (df_local["open"] > 0) & (df_local["volume"] > 0)].copy()
            df_local = df_local.set_index("time")[["open", "high", "low", "close", "volume"]]

            if not df_local.empty and try_online:
                last_date = df_local.index[-1]

                # 如果本地数据明显过期（差2天以上），直接下载
                if last_date < today - pd.Timedelta(days=2):
                    pass  # fall through to download
                else:
                    # 核对收盘价：下载最近10天数据对比
                    try:
                        df_verify = _download_akshare_recent(code, suffix, days=10)
                        if df_verify is not None and not df_verify.empty:
                            # 找到最新共同交易日
                            common_dates = df_local.index.intersection(df_verify.index)
                            if len(common_dates) > 0:
                                latest_common = common_dates[-1]
                                local_close = float(df_local.loc[latest_common, "close"])
                                verify_close = float(df_verify.loc[latest_common, "close"])

                                if abs(local_close - verify_close) < 1e-6:
                                    # 收盘价一致，返回本地数据
                                    return df_local
                                else:
                                    # 收盘价不一致，强制更新完整数据
                                    print(f"[数据核对] {code}.{suffix}: close不一致 本地={local_close} 在线={verify_close}，强制更新")
                                    df_full = _try_all_sources(code, suffix)
                                    if df_full is not None and not df_full.empty:
                                        _save_pkl(code, suffix, df_full, pkl_dir)
                                        return df_full
                    except Exception as e:
                        print(f"[核对失败] {code}.{suffix}: {e}")

                    # 核对失败或不需要核对，返回本地数据
                    return df_local

            # 本地数据过期或不需要在线，尝试在线
            if try_online:
                pass  # fall through to download
            else:
                return df_local if not df_local.empty else None
        except Exception:
            pass

    # ========== 本地没有或过期，尝试在线下载（多源自动降级）==========
    if try_online:
        df = _try_all_sources(code, suffix)
        if df is not None and not df.empty:
            _save_pkl(code, suffix, df, pkl_dir)
        return df

    return None


# ============================================================
#  build_data_dict
# ============================================================
def build_data_dict(tickers, start_date=None, end_date=None, pkl_dir=None):
    """批量加载多标的数据并做日期交集对齐。

    Parameters
    ----------
    tickers : list[dict]
        每个元素为 {code, suffix, ...}，至少含 code 和 suffix。
    start_date : str or None
        起始日期，如 "2020-01-01"；None 表示不裁剪。
    end_date : str or None
        截止日期，如 "2025-12-31"；None 表示不裁剪。
    pkl_dir : str, optional
        pkl 文件所在目录，默认使用 PKL_DIR。

    Returns
    -------
    dict[str, pd.DataFrame]
        key 为 thscode，value 为对齐后的 DataFrame。
    """
    if pkl_dir is None:
        pkl_dir = PKL_DIR

    raw = {}
    for t in tickers:
        # 支持两种格式: "159949.SZ" 字符串 或 {"code":"159949","suffix":"SZ"} 字典
        if isinstance(t, str):
            code, suffix = t.split('.')
            thscode = t
        else:
            code = t["code"]
            suffix = t["suffix"]
            thscode = f"{code}.{suffix}"
        df = load_pkl_data(code, suffix, pkl_dir)
        if df is None or df.empty:
            continue
        # 日期范围裁剪
        if start_date is not None:
            df = df[df.index >= pd.Timestamp(start_date)]
        if end_date is not None:
            df = df[df.index <= pd.Timestamp(end_date)]
        if df.empty:
            continue
        raw[thscode] = df

    if not raw:
        return {}

    # 取所有标的的日期交集
    common = None
    for df in raw.values():
        idx_set = set(df.index)
        common = idx_set if common is None else common.intersection(idx_set)
    if not common:
        return {}

    common = sorted(common)

    result = {}
    for thscode, df in raw.items():
        aligned = df.loc[df.index.isin(common)]
        if not aligned.empty:
            result[thscode] = aligned

    return result

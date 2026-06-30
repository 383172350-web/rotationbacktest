# -*- coding: utf-8 -*-
"""
数据加载模块 —— 从 pkl 文件批量加载 ETF 日线数据
"""
from __future__ import print_function, division

import os
import re
import pandas as pd

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
    if not os.path.isdir(pkl_dir):
        return []

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


# ============================================================
#  load_pkl_data
# ============================================================
def load_pkl_data(code, suffix, pkl_dir=None):
    """加载单个 pkl 文件并做基本预处理。

    Parameters
    ----------
    code : str
        6 位代码，如 "510300"。
    suffix : str
        交易所后缀，如 "SH" / "SZ"。
    pkl_dir : str, optional
        pkl 文件所在目录，默认使用 PKL_DIR。

    Returns
    -------
    pd.DataFrame or None
        索引为 datetime，列为 open/high/low/close/volume。
        如果文件不存在或加载失败，返回 None。
    """
    if pkl_dir is None:
        pkl_dir = PKL_DIR

    pkl_file = os.path.join(pkl_dir, f"{code}_{suffix}_1d.pkl")
    if not os.path.exists(pkl_file):
        return None

    try:
        df = pd.read_pickle(pkl_file).reset_index()
        # 索引 stime(int) -> datetime
        df["time"] = pd.to_datetime(df["stime"].astype(str), format="%Y%m%d")
        # 过滤无效行情
        df = df[(df["close"] > 0) & (df["open"] > 0) & (df["volume"] > 0)].copy()
        df = df.set_index("time")[["open", "high", "low", "close", "volume"]]
        return df
    except Exception:
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

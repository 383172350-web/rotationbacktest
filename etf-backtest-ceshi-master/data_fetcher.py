"""
极简数据获取模块
测试：本地pkl + 东方财富API + 腾讯API
完全不用 akshare，绕过 numpy 2.0 兼容问题
"""
import pandas as pd
import requests
import os

# ========== 本地pkl目录 ==========
LOCAL_PKL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ETF", "1d")


def _extract_code_suffix(code: str) -> tuple:
    """从sh510300提取510300和SH"""
    code = code.strip().lower()
    if code.startswith('sh'):
        return code[2:], 'SH'
    elif code.startswith('sz'):
        return code[2:], 'SZ'
    elif code.startswith('hk'):
        return code[2:], 'HK'
    elif code.startswith('us'):
        return code[2:], 'US'
    elif code.isdigit():
        if code.startswith(('51', '56', '58', '59', '60')):
            return code, 'SH'
        return code, 'SZ'
    return None, None


# ========== 本地pkl ==========
def _fetch_local_pkl(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """从本地pkl读取K线数据"""
    pure_code, suffix = _extract_code_suffix(code)
    if not pure_code:
        return pd.DataFrame()
    
    fname = f"{pure_code}_{suffix}_1d.pkl"
    pkl_path = os.path.join(LOCAL_PKL_DIR, fname)
    
    if not os.path.exists(pkl_path):
        return pd.DataFrame()
    
    try:
        df = pd.read_pickle(pkl_path)
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        
        if 'stime' in df.columns:
            df['date'] = pd.to_datetime(df['stime'].astype(str), format='%Y%m%d').dt.strftime('%Y-%m-%d')
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col not in df.columns:
                return pd.DataFrame()
        
        df = df[(df['close'] > 0) & (df['open'] > 0)]
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']].sort_values('date').reset_index(drop=True)
        df['amount'] = df['volume'] * df['close']
        
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        return df
    except Exception:
        return pd.DataFrame()


# ========== 东方财富API ==========
def _fetch_eastmoney(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """直接调用东方财富API获取ETF K线"""
    pure_code, suffix = _extract_code_suffix(code)
    if not pure_code:
        return pd.DataFrame()
    
    # secid: 1=上海, 0=深圳
    secid = "1" if suffix == "SH" else "0"
    beg = start_date.replace("-", "")
    end = end_date.replace("-", "")
    
    url = (
        f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={secid}.{pure_code}"
        f"&fields1=f1,f2,f3,f4,f5,f6"
        f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        f"&klt=101&fqt=1&beg={beg}&end={end}"
    )
    
    try:
        resp = requests.get(url, timeout=30)
        data = resp.json()
        
        if not data.get("data") or not data["data"].get("klines"):
            return pd.DataFrame()
        
        klines = data["data"]["klines"]
        rows = []
        for line in klines:
            parts = line.split(",")
            if len(parts) >= 6:
                rows.append({
                    "date": parts[0],
                    "open": float(parts[1]),
                    "close": float(parts[2]),
                    "low": float(parts[3]),
                    "high": float(parts[4]),
                    "volume": float(parts[5]),
                })
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']].sort_values('date').reset_index(drop=True)
        df['amount'] = df['volume'] * df['close']
        return df
    except Exception as e:
        print(f"eastmoney error: {e}")
        return pd.DataFrame()


# ========== 腾讯API ==========
def _fetch_tencent(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """直接调用腾讯API获取ETF K线"""
    pure_code, suffix = _extract_code_suffix(code)
    if not pure_code:
        return pd.DataFrame()
    
    # 腾讯格式：sh510300
    tencent_code = f"{suffix.lower()}{pure_code}"
    
    url = (
        f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        f"?param={tencent_code},day,{start_date},{end_date},640,qfq"
    )
    
    try:
        resp = requests.get(url, timeout=30)
        data = resp.json()
        
        key = f"{suffix.lower()}{pure_code}"
        if not data.get("data") or not data["data"].get(key):
            return pd.DataFrame()
        
        klines = data["data"][key].get("day", [])
        if not klines:
            return pd.DataFrame()
        
        rows = []
        for item in klines:
            if isinstance(item, list) and len(item) >= 5:
                rows.append({
                    "date": item[0],
                    "open": float(item[1]),
                    "close": float(item[2]),
                    "low": float(item[3]),
                    "high": float(item[4]),
                    "volume": float(item[5]) if len(item) > 5 else 0,
                })
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']].sort_values('date').reset_index(drop=True)
        df['amount'] = df['volume'] * df['close']
        return df
    except Exception as e:
        print(f"tencent error: {e}")
        return pd.DataFrame()


# ========== findb API ==========
def _fetch_findb(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """使用 findb API 获取数据"""
    TOKEN = "sk_live_7orj6tBMMNiB.4eAcaTYc65icYsacCZksDfkHqvVvQyKfdbPf0X8aiR0"
    
    pure_code, suffix = _extract_code_suffix(code)
    if not pure_code:
        return pd.DataFrame()
    
    # 计算天数，但最小取500确保覆盖历史到近期
    import datetime
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    days = (end_dt - start_dt).days + 1
    limit = max(days, 3000)  # 至少3000条，确保覆盖12年历史到近期
    
    url = f"https://api.jiucaicat.icu:8443/api/bars?code={pure_code}.{suffix}&freq=daily&limit={limit}&order=desc"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=60)
        data = resp.json()
        
        # findb 返回格式: {"data": [{"datetime": "...", "open": ..., ...}]}
        records = data.get("data", []) if isinstance(data, dict) else data
        if not records or not isinstance(records, list):
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df.columns = [c.lower() for c in df.columns]
        
        # 重命名列
        df = df.rename(columns={
            'datetime': 'date',
            'time': 'date',
        })
        
        # 确保标准列名
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col not in df.columns:
                return pd.DataFrame()
        
        # 处理日期
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']].sort_values('date').reset_index(drop=True)
        df['amount'] = df['volume'] * df['close']
        
        # 按日期范围筛选
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        return df
    except Exception as e:
        print(f"findb error: {e}")
        return pd.DataFrame()


# ========== 统一入口 ==========
def fetch_data(code: str, start_date: str, end_date: str, source: str = "auto") -> dict:
    """
    获取数据，返回字典包含结果和状态
    source: "local" | "eastmoney" | "tencent" | "findb" | "auto"
    """
    result = {"source": source, "code": code, "rows": 0, "df": pd.DataFrame(), "error": None}
    
    if source in ("auto", "local"):
        df = _fetch_local_pkl(code, start_date, end_date)
        if not df.empty:
            result["source"] = "local"
            result["df"] = df
            result["rows"] = len(df)
            return result
    
    if source in ("auto", "eastmoney"):
        df = _fetch_eastmoney(code, start_date, end_date)
        if not df.empty:
            result["source"] = "eastmoney"
            result["df"] = df
            result["rows"] = len(df)
            return result
    
    if source in ("auto", "tencent"):
        df = _fetch_tencent(code, start_date, end_date)
        if not df.empty:
            result["source"] = "tencent"
            result["df"] = df
            result["rows"] = len(df)
            return result
    
    if source in ("auto", "findb"):
        df = _fetch_findb(code, start_date, end_date)
        if not df.empty:
            result["source"] = "findb"
            result["df"] = df
            result["rows"] = len(df)
            return result
    
    result["error"] = "无数据"
    return result

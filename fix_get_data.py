import re

with open('streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 定义新的 get_data 函数
new_get_data = '''# ============================================================
#  缓存数据获取
# ============================================================

# 交易时间判断：9:30-15:00（含早盘和下午盘）
def _is_trading_time():
    now = datetime.datetime.now()
    t = now.time()
    return datetime.time(9, 30) <= t <= datetime.time(15, 0)


def get_data(codes_list, start_date, end_date, alt_code=""):
    """获取数据：本地pkl优先，无本地或过期则在线获取并自动保存
    智能缓存：交易时间（9:30-15:00）始终检查更新，非交易时间缓存1小时
    """
    # 生成缓存键
    cache_key = f"data_cache_{hash(str(codes_list)+start_date+end_date+alt_code)}"
    
    # 非交易时间：尝试使用缓存（1小时有效）
    if not _is_trading_time():
        if cache_key in st.session_state:
            cached = st.session_state[cache_key]
            age = (datetime.datetime.now() - cached['time']).total_seconds()
            if age < 3600:  # 1小时内
                return cached['data']
    
    # 交易时间 或 缓存过期：重新获取数据
    all_codes = list(codes_list)
    if alt_code and alt_code.strip():
        all_codes.append({"code": alt_code.strip(), "name": "替代资产"})
    
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    warmup = (start_dt - pd.Timedelta(days=400)).strftime('%Y-%m-%d')
    
    all_data = {}
    for item in all_codes:
        code = item['code'] if isinstance(item, dict) else item
        try:
            df = fetch_kline(code, warmup, end_date, auto_save=True)
            if not df.empty and len(df) > 60:
                df['date'] = pd.to_datetime(df['date'])
                all_data[code] = df
            elif code != alt_code:
                st.warning(f"{code} 数据不足或为空，已跳过")
        except Exception as e:
            if code != alt_code:
                st.warning(f"获取 {code} 失败: {e}")
    
    # 保存到缓存（供非交易时间使用）
    st.session_state[cache_key] = {
        'data': all_data,
        'time': datetime.datetime.now()
    }
    return all_data


# ============================================================
#  构建配置
# ============================================================'''

# 使用正则替换
pattern = r'# =+\n#  缓存数据获取\n# =+\n@st\.cache_data\(ttl=0, show_spinner=False\)\ndef get_data\(codes_list, start_date, end_date, alt_code=""\):\n    """获取数据：本地pkl优先，无本地或过期则在线获取并自动保存"""\n    all_codes = list\(codes_list\)\n    if alt_code and alt_code\.strip\(\):\n        all_codes\.append\(\{"code": alt_code\.strip\(\), "name": "替代资产"\}\)\n    \n    start_dt = datetime\.datetime\.strptime\(start_date, "%Y-%m-%d"\)\n    warmup = \(start_dt - pd\.Timedelta\(days=400\)\)\.strftime\(\'%Y-%m-%d\'\)\n    \n    all_data = \{\}\n    for item in all_codes:\n        code = item\[\'code\'\] if isinstance\(item, dict\) else item\n        try:\n            df = fetch_kline\(code, warmup, end_date, auto_save=True\)\n            if not df\.empty and len\(df\) > 60:\n                df\[\'date\'\] = pd\.to_datetime\(df\[\'date\'\]\)\n                all_data\[code\] = df\n            elif code != alt_code:\n                st\.warning\(f"\{code\} 数据不足或为空，已跳过"\)\n        except Exception as e:\n            if code != alt_code:\n                st\.warning\(f"获取 \{code\} 失败: \{e\}"\)\n    return all_data\n\n\n# =+\n#  构建配置\n# =+'

if re.search(pattern, content):
    content = re.sub(pattern, new_get_data, content)
    with open('streamlit_app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Replaced successfully')
else:
    print('Pattern not found, trying simpler approach...')
    # 备用方案：查找 get_data 函数定义位置
    idx = content.find('@st.cache_data(ttl=0, show_spinner=False)')
    if idx >= 0:
        start = content.rfind('# =', 0, idx)
        end = content.find('#  构建配置', idx)
        if start >= 0 and end >= 0:
            end = content.find('\n# =', end)  # 找到下一个分隔线结束
            content = content[:start] + new_get_data + content[end:]
            with open('streamlit_app.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print('Replaced using index approach')
        else:
            print('Could not find boundaries')
    else:
        print('Could not find @st.cache_data')

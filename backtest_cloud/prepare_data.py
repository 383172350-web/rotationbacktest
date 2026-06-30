# -*- coding: utf-8 -*-
"""
数据准备脚本 —— 将本地 pkl 数据复制到部署目录
"""
import os
import shutil
import sys

# 源数据目录（请根据你的实际路径修改）
SOURCE_DATA_DIR = r"D:\qmt_data\ETF\1d"

# 目标目录（部署目录下的 data/ETF/1d）
TARGET_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ETF", "1d")

def prepare_data():
    if not os.path.exists(SOURCE_DATA_DIR):
        print(f"错误: 源数据目录不存在: {SOURCE_DATA_DIR}")
        print("请修改脚本中的 SOURCE_DATA_DIR 为你的实际数据路径")
        sys.exit(1)
    
    os.makedirs(TARGET_DATA_DIR, exist_ok=True)
    
    files = [f for f in os.listdir(SOURCE_DATA_DIR) if f.endswith(".pkl")]
    if not files:
        print("警告: 未找到任何 .pkl 文件")
        return
    
    print(f"准备复制 {len(files)} 个 pkl 文件...")
    copied = 0
    for fname in files:
        src = os.path.join(SOURCE_DATA_DIR, fname)
        dst = os.path.join(TARGET_DATA_DIR, fname)
        shutil.copy2(src, dst)
        copied += 1
    
    # 计算总大小
    total_size = sum(os.path.getsize(os.path.join(TARGET_DATA_DIR, f)) for f in os.listdir(TARGET_DATA_DIR) if f.endswith(".pkl"))
    print(f"\n✓ 完成！复制了 {copied} 个文件，总大小 {total_size / 1024 / 1024:.1f} MB")
    print(f"  目标目录: {TARGET_DATA_DIR}")
    print(f"\n现在你可以将此目录上传到 GitHub 并部署到 Streamlit Cloud 了。")

if __name__ == "__main__":
    prepare_data()

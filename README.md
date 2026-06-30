# ETF轮动策略回测系统 — 统一仓库

## 三个独立应用

| 应用 | 入口文件 | 说明 | 端口 |
|------|----------|------|------|
| **旧版策略生成器** | `app_legacy.py` | 原始硬编码策略 + 表达式引擎 | 8503 |
| **新版策略生成器** | `app_rotation.py` | 全新表达式引擎 + 可视化 | 8502 |
| **全品类资产轮动** | `app_bot.py` | DIFv轮动全自动交易机器人 | - |

## 本地启动

```bash
# 一键启动全部（4个系统）
start_all.bat

# 或单独启动
# 旧版 Flask API
python -m flask run --host=0.0.0.0 --port=8001

# 旧版策略生成器
python -m streamlit run backtest_cloud/streamlit_app.py --server.port 8503

# 新版策略生成器
python -m streamlit run rotation-web/streamlit_app.py --server.port 8502

# 全品类资产轮动
python 全品类资产轮动双模式.py
```

## Streamlit Cloud 部署

1. 连接 GitHub 仓库到 [Streamlit Cloud](https://share.streamlit.io/)
2. 选择入口文件：
   - `app_legacy.py` → 旧版策略生成器
   - `app_rotation.py` → 新版策略生成器
   - `app_bot.py` → 全品类资产轮动
3. 设置环境变量 `PKL_DIR`（pkl 数据目录路径）

## 数据说明

- 本地 pkl 数据路径：`D:\qmt_data\ETF\1d`
- Streamlit Cloud 上需要设置 `PKL_DIR` 环境变量指向正确的数据目录
- 或上传数据到 GitHub（不推荐，数据量较大）

## 目录结构

```
workspace/
├── backtest_cloud/          # 旧版系统
│   ├── app.py               # Flask API (端口 8001)
│   ├── streamlit_app.py     # 旧版策略生成器
│   └── engine/              # 回测引擎
├── rotation-web/            # 新版系统
│   ├── streamlit_app.py     # 新版策略生成器
│   ├── backtest_engine.py   # 回测引擎
│   └── ...
├── 全品类资产轮动双模式.py  # 独立机器人脚本
├── app_legacy.py            # Streamlit Cloud 入口：旧版
├── app_rotation.py          # Streamlit Cloud 入口：新版
├── app_bot.py               # Streamlit Cloud 入口：机器人
├── start_all.bat            # 一键启动脚本
└── requirements.txt         # 统一依赖
```

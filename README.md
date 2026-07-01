# Rotation Backtest — ETF轮动策略回测系统

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)

一个统一的 ETF 轮动策略回测与生成平台，整合**旧版硬编码策略**和**新版表达式引擎**两大系统。

## 两大应用

| 应用 | 入口文件 | 说明 | 本地端口 |
|------|----------|------|---------|
| **旧版策略生成器** | `app_legacy.py` | 原始硬编码策略（DIFv/WDM/RSRS/LOF）+ 表达式引擎 | 8503 |
| **新版策略生成器** | `app_rotation.py` | 全新表达式引擎 + 可视化策略构建 | 8502 |

## 核心特性

- **双引擎回测**：Legacy 硬编码函数保证收益一致性，通用表达式引擎支持灵活定制
- **策略生成器**：拖拽式指标组合，实时表达式验证，可视化回测结果
- **QMT 集成**：自动生成交易计划，对接迅投 QMT 量化平台
- **Streamlit Cloud 一键部署**：3 个独立入口，按需部署

## 快速开始

### 本地启动

```bash
# 一键启动全部（2 个系统）
start_all.bat

# 或单独启动
# 旧版 Flask API
python -m flask run --host=0.0.0.0 --port=8001

# 旧版策略生成器
python -m streamlit run backtest_cloud/streamlit_app.py --server.port 8503

# 新版策略生成器
python -m streamlit run rotation-web/streamlit_app.py --server.port 8502
```

### Streamlit Cloud 部署

1. Fork 本仓库到个人 GitHub
2. 访问 [share.streamlit.io](https://share.streamlit.io/) 新建 App
3. 选择入口文件：
   - `app_legacy.py` → 旧版策略生成器
   - `app_rotation.py` → 新版策略生成器
4. 高级设置 → 设置环境变量 `PKL_DIR`（pkl 数据目录路径）

## 数据准备

系统支持本地 pkl 数据或在线数据源（akshare/yfinance）：

```bash
# 本地数据路径（Windows 示例）
set PKL_DIR=D:\qmt_data\ETF\1d

# 或 Linux/Mac
export PKL_DIR=/path/to/etf_data
```

Streamlit Cloud 上需要设置 `PKL_DIR` 环境变量指向数据目录，或启用在线数据自动下载。

## 目录结构

```
rotationbacktest/
├── backtest_cloud/          # 旧版系统（硬编码策略 + 适配层）
│   ├── app.py               # Flask API (端口 8001)
│   ├── streamlit_app.py     # 旧版策略生成器
│   └── engine/              # 回测引擎 + legacy.py 适配层
├── rotation-web/            # 新版系统（表达式引擎）
│   ├── streamlit_app.py     # 新版策略生成器
│   ├── backtest_engine.py   # 回测引擎
│   └── ...
├── app_legacy.py            # Streamlit Cloud 入口：旧版
├── app_rotation.py          # Streamlit Cloud 入口：新版
├── start_all.bat            # 一键启动脚本
└── requirements.txt         # 统一依赖
```

## 预设策略

| 策略 | 类型 | 核心逻辑 |
|------|------|----------|
| DIFv 轮动 | 旧版 | DIF 差值 + 大盘择时 + 自动择债 |
| 五斗米动量 | 旧版 | 动量 + 波动率 + 动量 cutoff |
| RSRS 动量 | 旧版 | 质量得分 + 连跌惩罚 + 量比过滤 |
| LOF 轮动 | 旧版 | 动量标准分 + 排名 + 连跌惩罚 |
| 大盘择时 | 通用 | 沪深300 + 500日趋势 + 5连跌 |
| 底部动量 | 通用 | 20日动量 + 波动率 + 均值回归 |
| 自定义策略 | 通用 | 表达式引擎自由组合 |

## 技术栈

- **Python 3.8+**
- **Streamlit** — 交互式 Web 界面
- **Flask** — REST API 服务
- **Pandas / NumPy** — 数据计算
- **Plotly** — 可视化图表

## 许可证

MIT

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**money-get** 是一个 A股投资辅助 Agent，基于 Python + LangGraph + MiniMax API 构建，通过 CLI 与用户交互，用于股票分析、历史操作复盘和市场数据分析。

## 技术栈

- Python 3.10+
- LangChain / LangGraph (Agent 框架)
- MiniMax API (LLM)
- akshare (股票数据获取)
- FAISS / Chroma (向量存储)
- 钉钉 Webhook / 飞书 (消息推送)

## 项目结构

```
money-get/
├── src/money_get/
│   ├── main.py          # CLI 入口
│   ├── config.py        # 配置
│   ├── agent/           # Agent 核心
│   │   ├── state.py    # AgentState 定义
│   │   ├── nodes.py    # 节点实现
│   │   ├── graph.py    # LangGraph 图构建
│   │   └── tools.py    # 工具定义
│   ├── data/            # 数据层
│   │   ├── stock.py    # 股票数据获取
│   │   ├── trade.py    # 交易记录
│   │   └── storage.py  # JSON 文件存储
│   └── services/        # 服务层
│       ├── analyzer.py # 分析服务
│       └── reporter.py # 报告生成
├── data/                # 数据目录
├── tests/               # 测试
└── pyproject.toml       # 项目配置
```

## 开发指南

项目使用 **entire** 框架进行任务管理，相关钩子已在 `.claude/settings.json` 中配置。

### 安装依赖

```bash
pip install -e ".[dev]"
```

### CLI 命令

```bash
# 分析股票
python -m money_get analyze 600519

# 复盘
python -m money_get review

# 市场热点
python -m money_get market

# 交易记录
python -m money_get trades add --code 600519 --name 茅台 --direction buy --price 1800 --quantity 100 --date 2024-01-15
python -m money_get trades list

# Agent 对话
python -m money_get chat "分析一下茅台"
```

### Agent 设计规范

详见 [Agent.md](./Agent.md)，包含 Agent 的状态定义、节点设计、工具规范等。

## 配置说明

- `MINIMAX_API_KEY` - MiniMax API 密钥
- `DINGTALK_WEBHOOK` - 钉钉 Webhook
- `FEISHU_WEBHOOK` - 飞书 Webhook

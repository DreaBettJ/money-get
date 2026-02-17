# Agent 设计规范

## 概述

基于 LangGraph 的股票分析 Agent，通过 CLI 与用户交互。

## 状态定义 (State)

```python
class AgentState(TypedDict):
    messages: HumanMessage | AIMessage | SystemMessage  # 对话历史
    task: str                                           # 当前任务
    context: dict                                       # 上下文数据
    result: Any                                         # 执行结果
```

## 节点设计

| 节点 | 职责 |
|-----|------|
| `classifier` | 意图分类，判断用户意图 |
| `planner` | 任务规划，分解执行步骤 |
| `data_fetcher` | 获取股票数据 |
| `analyzer` | 执行分析 |
| `reporter` | 生成报告 |
| `responder` | 返回结果给用户 |

## 工具 (Tools)

Agent 通过 Tools 调用外部能力：

- `get_stock_price` - 获取实时行情
- `get_kline` - 获取 K 线数据
- `get_stock_info` - 获取股票基本信息
- `get_sector_flow` - 获取板块资金流向
- `save_trade` - 保存交易记录
- `get_trades` - 查询交易记录

## 工作流

```
用户输入 → classifier → planner → [data_fetcher → analyzer → reporter] → responder → 输出
```

## CLI 交互

使用 Click 或 Typer 构建 CLI，交互模式：

- `analyze <股票代码>` - 分析指定股票
- `review` - 复盘历史操作
- `market` - 市场热点分析
- `trades add` - 记录交易
- `trades list` - 查看交易记录
- `help` - 帮助信息

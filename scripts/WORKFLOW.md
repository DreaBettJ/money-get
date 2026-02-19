# money-get 每日工作流

## 使用方法

```bash
cd /home/lijiang/code/money-get
source .venv/bin/activate
PYTHONPATH=src python3 scripts/daily_workflow.py
```

## 工作流说明

### 场景1: 每日推荐
```python
from money_get.selector import select_stocks
stocks = select_stocks(use_policy=True, use_llm=True, top_n=5)
```

### 场景2: 分析股票
```python
from money_get.agent import StockAgent
agent = StockAgent()
result = agent.analyze("600519")
```

### 场景3: 决策调仓
```bash
# 记录买入
PYTHONPATH=src python3 cli.py buy 600519 1800 100 --reason "金叉"

# 记录卖出  
PYTHONPATH=src python3 cli.py sell 600519 1900 50 --reason "止盈"
```

### 场景4: 收益率计算
```bash
# 查看持仓
PYTHONPATH=src python3 cli.py portfolio

# 交易统计
PYTHONPATH=src python3 cli.py stats
```

## 定时任务 (可选)

设置每日收盘后自动运行:
```bash
# 添加 cron 任务
crontab -e

# 每天 15:30 运行
30 15 * * 1-5 cd /home/lijiang/code/money-get && source .venv/bin/activate && PYTHONPATH=src python3 scripts/daily_workflow.py >> logs/daily.log 2>&1
```

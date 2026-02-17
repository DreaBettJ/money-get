"""Agent 节点实现"""
from money_get.agent.state import AgentState
from money_get.agent.tools import TOOLS


def classifier(state: AgentState) -> AgentState:
    """意图分类节点"""
    task = state["task"]

    # 简单规则分类
    if "分析" in task or "analyze" in task.lower():
        intent = "analyze"
    elif "复盘" in task or "review" in task.lower():
        intent = "review"
    elif "市场" in task or "热点" in task:
        intent = "market"
    elif "交易" in task or "买卖" in task:
        intent = "trade"
    else:
        intent = "general"

    state["context"] = {"intent": intent}
    return state


def planner(state: AgentState) -> AgentState:
    """任务规划节点"""
    intent = state["context"].get("intent", "general")

    # 根据意图规划步骤
    if intent == "analyze":
        steps = ["fetch_data", "analyze", "report"]
    elif intent == "review":
        steps = ["fetch_trades", "analyze", "report"]
    elif intent == "market":
        steps = ["fetch_sector", "analyze", "report"]
    else:
        steps = ["general"]

    state["context"]["steps"] = steps
    return state


def data_fetcher(state: AgentState) -> AgentState:
    """数据获取节点"""
    task = state["task"]

    # 提取股票代码
    import re

    codes = re.findall(r"\d{6}", task)
    if codes:
        state["context"]["stock_code"] = codes[0]

    state["result"] = {"data": "fetched"}
    return state


def analyzer(state: AgentState) -> AgentState:
    """分析节点"""
    from money_get.services.analyzer import analyze_stock

    stock_code = state["context"].get("stock_code")
    if stock_code:
        result = analyze_stock(stock_code, 30)
        state["result"] = result
    else:
        state["result"] = "请提供股票代码"

    return state


def reporter(state: AgentState) -> AgentState:
    """报告生成节点"""
    from money_get.services.reporter import generate_report

    result = generate_report(state["result"])
    state["result"] = result
    return state


def responder(state: AgentState) -> AgentState:
    """响应节点"""
    return state


def should_fetch_data(state: AgentState) -> str:
    """判断是否需要获取数据"""
    steps = state["context"].get("steps", [])
    if "fetch_data" in steps or "fetch_trades" in steps:
        return "fetch"
    return "analyze"

"""LangGraph 图构建"""
from langgraph.graph import StateGraph, END
from money_get.agent.state import AgentState
from money_get.agent.nodes import (
    classifier,
    planner,
    data_fetcher,
    analyzer,
    reporter,
    responder,
    should_fetch_data,
)


def build_graph() -> StateGraph:
    """构建 Agent 图"""
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("classifier", classifier)
    graph.add_node("planner", planner)
    graph.add_node("data_fetcher", data_fetcher)
    graph.add_node("analyzer", analyzer)
    graph.add_node("reporter", reporter)
    graph.add_node("responder", responder)

    # 设置入口
    graph.set_entry_point("classifier")

    # 添加边
    graph.add_edge("classifier", "planner")
    graph.add_edge("planner", "data_fetcher")
    graph.add_edge("data_fetcher", "analyzer")
    graph.add_edge("analyzer", "reporter")
    graph.add_edge("reporter", "responder")
    graph.add_edge("responder", END)

    return graph.compile()


# 全局图实例
_graph = None


def get_graph() -> StateGraph:
    """获取图实例"""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph

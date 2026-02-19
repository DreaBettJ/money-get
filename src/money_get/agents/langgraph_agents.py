"""LangGraph 多Agent股票分析系统

基于 LangGraph 的状态化工作流：
- 状态自动传递
- 内置 Langfuse 追踪
- 可视化流程
"""
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langfuse import Langfuse

from money_get.agents import (
    FundAgent, NewsAgent, SentimentAgent, 
    ResearchAgent, DecisionAgent
)
from money_get.agents.base import get_api_config
from money_get.logger import logger as _logger


class AgentState(TypedDict):
    """分析状态"""
    stock_code: str
    fund_result: str
    news_result: str
    sentiment_result: str
    research_result: str
    decision: str
    error: str


def create_llm():
    """创建 LangGraph 兼容的 LLM"""
    from langchain_openai import ChatOpenAI
    config = get_api_config()
    
    # 从 URL 提取基础 URL
    url = config.get("url", "https://api.minimax.chat/v1")
    base_url = url.replace("/text/chatcompletion_v2", "")
    
    llm = ChatOpenAI(
        model=config.get("model", "MiniMax-M2.5"),
        api_key=config.get("api_key", ""),
        base_url=base_url,
        temperature=0.3,
        max_tokens=4000
    )
    return llm


def fund_node(state: AgentState) -> AgentState:
    """资金分析节点"""
    stock_code = state["stock_code"]
    _logger.info(f"🔶 [LangGraph] FundAgent 开始: {stock_code}")
    
    try:
        agent = FundAgent()
        result = agent.analyze(stock_code)
        state["fund_result"] = result
        _logger.info(f"✅ [LangGraph] FundAgent 完成")
    except Exception as e:
        state["error"] = str(e)
        _logger.error(f"❌ [LangGraph] FundAgent 失败: {e}")
    
    return state


def news_node(state: AgentState) -> AgentState:
    """新闻分析节点"""
    stock_code = state["stock_code"]
    _logger.info(f"🔶 [LangGraph] NewsAgent 开始: {stock_code}")
    
    try:
        agent = NewsAgent()
        result = agent.analyze(stock_code)
        state["news_result"] = result
        _logger.info(f"✅ [LangGraph] NewsAgent 完成")
    except Exception as e:
        state["error"] = str(e)
        _logger.error(f"❌ [LangGraph] NewsAgent 失败: {e}")
    
    return state


def sentiment_node(state: AgentState) -> AgentState:
    """情绪分析节点"""
    stock_code = state["stock_code"]
    _logger.info(f"🔶 [LangGraph] SentimentAgent 开始: {stock_code}")
    
    try:
        agent = SentimentAgent()
        result = agent.analyze(stock_code)
        state["sentiment_result"] = result
        _logger.info(f"✅ [LangGraph] SentimentAgent 完成")
    except Exception as e:
        state["error"] = str(e)
        _logger.error(f"❌ [LangGraph] SentimentAgent 失败: {e}")
    
    return state


def research_node(state: AgentState) -> AgentState:
    """研究分析节点"""
    stock_code = state["stock_code"]
    _logger.info(f"🔶 [LangGraph] ResearchAgent 开始: {stock_code}")
    
    try:
        agent = ResearchAgent()
        result = agent.analyze(stock_code,
            fund_analysis=state.get("fund_result", ""),
            news_analysis=state.get("news_result", ""),
            sentiment_analysis=state.get("sentiment_result", ""))
        state["research_result"] = result
        _logger.info(f"✅ [LangGraph] ResearchAgent 完成")
    except Exception as e:
        state["error"] = str(e)
        _logger.error(f"❌ [LangGraph] ResearchAgent 失败: {e}")
    
    return state


def decision_node(state: AgentState) -> AgentState:
    """决策节点"""
    stock_code = state["stock_code"]
    _logger.info(f"🔶 [LangGraph] DecisionAgent 开始: {stock_code}")
    
    try:
        agent = DecisionAgent()
        result = agent.analyze(stock_code,
            fund_analysis=state.get("fund_result", ""),
            news_analysis=state.get("news_result", ""),
            sentiment_analysis=state.get("sentiment_result", ""),
            research_result=state.get("research_result", ""))
        state["decision"] = result
        _logger.info(f"✅ [LangGraph] DecisionAgent 完成")
    except Exception as e:
        state["error"] = str(e)
        _logger.error(f"❌ [LangGraph] DecisionAgent 失败: {e}")
    
    return state


def create_stock_graph() -> StateGraph:
    """创建股票分析图"""
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("fund", fund_node)
    workflow.add_node("news", news_node)
    workflow.add_node("sentiment", sentiment_node)
    workflow.add_node("research", research_node)
    workflow.add_node("decision", decision_node)
    
    # 设置入口
    workflow.set_entry_point("fund")
    
    # 添加边（串行）
    workflow.add_edge("fund", "news")
    workflow.add_edge("news", "sentiment")
    workflow.add_edge("sentiment", "research")
    workflow.add_edge("research", "decision")
    workflow.add_edge("decision", END)
    
    return workflow


def create_stock_graph_parallel() -> StateGraph:
    """创建并行股票分析图"""
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("fund", fund_node)
    workflow.add_node("news", news_node)
    workflow.add_node("sentiment", sentiment_node)
    workflow.add_node("research", research_node)
    workflow.add_node("decision", decision_node)
    
    # 设置入口
    workflow.set_entry_point("parallel_analysis")
    
    # 添加并行节点
    workflow.add_node("parallel_analysis", lambda state: state)
    workflow.add_conditional_edges(
        "parallel_analysis",
        lambda x: "fund",
        ["fund", "news", "sentiment"]
    )
    
    # 并行完成后进入研究
    workflow.add_edge("fund", "research")
    workflow.add_edge("news", "research")
    workflow.add_edge("sentiment", "research")
    
    # 研究后决策
    workflow.add_edge("research", "decision")
    workflow.add_edge("decision", END)
    
    return workflow


class LangGraphAgents:
    """LangGraph 多Agent系统"""
    
    def __init__(self, mode: str = "sequential"):
        self.mode = mode
        self.graph = None
        self._build_graph()
    
    def _build_graph(self):
        """构建图"""
        if self.mode == "sequential":
            wf = create_stock_graph()
        else:
            wf = create_stock_graph_parallel()
        
        # 编译（带检查点）
        checkpointer = MemorySaver()
        self.graph = wf.compile(checkpointer=checkpointer)
    
    def analyze(self, stock_code: str) -> dict:
        """执行分析"""
        _logger.info(f"🔄 [LangGraph] 开始分析: {stock_code}, 模式: {self.mode}")
        
        initial_state = {
            "stock_code": stock_code,
            "fund_result": "",
            "news_result": "",
            "sentiment_result": "",
            "research_result": "",
            "decision": "",
            "error": ""
        }
        
        # 配置（带 thread_id）
        config = {"configurable": {"thread_id": f"stock_{stock_code}"}}
        
        # 执行
        result = self.graph.invoke(initial_state, config)
        
        _logger.info(f"✅ [LangGraph] 分析完成: {stock_code}")
        
        return {
            "fund": result.get("fund_result", ""),
            "news": result.get("news_result", ""),
            "sentiment": result.get("sentiment_result", ""),
            "research": result.get("research_result", ""),
            "decision": result.get("decision", ""),
            "error": result.get("error", "")
        }
    
    def get_graph_image(self) -> str:
        """获取图的图片（Mermaid格式）"""
        return self.graph.get_graph().draw_mermaid()


# 便捷函数
def langgraph_analyze(stock_code: str, mode: str = "sequential") -> dict:
    """LangGraph 分析"""
    agents = LangGraphAgents(mode=mode)
    return agents.analyze(stock_code)

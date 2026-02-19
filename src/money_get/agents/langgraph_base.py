"""LangGraph Agent 基类 - 带完整可观测性"""
from abc import ABC, abstractmethod
from typing import TypedDict, Dict, Any, List, Optional
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain.agents import create_agent
from langfuse import Langfuse
import json
from pathlib import Path

from ..logger import logger as _logger

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


def get_api_config() -> dict:
    """获取 API 配置"""
    config_path = PROJECT_ROOT.parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    llm_cfg = config.get("llm", {})
    llm_cfg["langfuse"] = config.get("langfuse", {})
    return llm_cfg


class AgentState(TypedDict):
    """Agent 状态"""
    stock_code: str
    data: dict
    analysis: str
    error: str
    messages: list


def create_base_llm():
    """创建基础 LLM"""
    config = get_api_config()
    
    url = config.get("url", "https://api.minimax.chat/v1")
    base_url = url.replace("/text/chatcompletion_v2", "")
    
    llm = ChatOpenAI(
        model=config.get("model", "MiniMax-M2.5"),
        api_key=config.get("api_key", ""),
        base_url=base_url,
        temperature=0.3
    )
    return llm


def get_langfuse_handler():
    """获取 Langfuse 处理器"""
    config = get_api_config()
    langfuse_cfg = config.get("langfuse", {})
    
    if not langfuse_cfg.get("public_key"):
        return None
    
    return Langfuse(
        public_key=langfuse_cfg["public_key"],
        secret_key=langfuse_cfg["secret_key"]
    )


class LangGraphAgent:
    """LangGraph Agent 基类"""
    
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self.llm = create_base_llm()
        self.graph = None
        self._build_graph()
    
    @abstractmethod
    def get_tools(self) -> List:
        """获取工具列表 - 子类实现"""
        pass
    
    def _build_graph(self):
        """构建图"""
        from langchain.agents import create_agent
        
        tools = self.get_tools()
        self.agent = create_agent(
            self.llm,
            tools,
            system_prompt=self.system_prompt,
            checkpointer=MemorySaver()
        )
        
        _logger.info(f"🤖 [{self.name}] LangGraph Agent 已创建")
        _logger.info(f"   工具: {[t.name for t in tools]}")
    
    def analyze(self, stock_code: str, data: dict = None) -> str:
        """分析股票"""
        _logger.info(f"🔶 [{self.name}] 开始分析: {stock_code}")
        
        data = data or {}
        messages = [HumanMessage(content=self._build_prompt(stock_code, data))]
        
        config = {"configurable": {"thread_id": f"{self.name}_{stock_code}"}}
        
        try:
            result = self.agent.invoke({"messages": messages}, config)
            
            # 获取最终响应
            response = result["messages"][-1].content
            
            _logger.info(f"✅ [{self.name}] 完成: {stock_code}")
            _logger.info(f"   消息数: {len(result['messages'])}")
            
            return response
            
        except Exception as e:
            _logger.error(f"❌ [{self.name}] 失败: {e}")
            return f"分析失败: {str(e)}"
    
    def _build_prompt(self, stock_code: str, data: dict) -> str:
        """构建提示词 - 子类实现"""
        return f"分析股票 {stock_code}"
    
    def get_graph_diagram(self) -> str:
        """获取图结构（Mermaid）"""
        return self.agent.get_graph().draw_mermaid()


# 便捷装饰器
def data_tool(func):
    """数据工具装饰器"""
    return tool(func)

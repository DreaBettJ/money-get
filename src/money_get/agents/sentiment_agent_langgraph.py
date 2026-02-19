"""情绪分析 Agent - LangGraph 版本"""
import logging
from langchain_core.tools import tool
from langchain.agents import create_agent
from money_get.agents.langgraph_base import LangGraphAgent
from money_get.scraper import get_hot_sectors
from money_get.db import get_stock
from money_get.logger import logger as _logger

logger = logging.getLogger(__name__)


# ============ 工具定义 ============

@tool
def get_market_sentiment() -> str:
    """获取市场情绪数据
    
    返回龙虎榜数据、热点板块等市场情绪指标。
    """
    try:
        result = "市场情绪数据:\n\n"
        
        # 热点板块
        sectors = get_hot_sectors(limit=5)
        if sectors:
            result += "热点板块:\n"
            for s in sectors:
                result += f"  - {s.get('name')}: {s.get('change')}%\n"
        else:
            result += "热点板块: 暂无数据\n"
        
        return result
    except Exception as e:
        return f"获取市场情绪失败: {e}"


@tool
def get_stock_sentiment(stock_code: str) -> str:
    """获取个股情绪数据
    
    Args:
        stock_code: 股票代码
    """
    try:
        result = f"股票 {stock_code} 情绪数据:\n"
        
        # 基础信息
        stock = get_stock(stock_code)
        if stock:
            result += f"名称: {stock.get('name')}\n"
            result += f"现价: {stock.get('price')}\n"
        
        return result
    except Exception as e:
        return f"获取个股情绪失败: {e}"


@tool
def do_sentiment_analysis(market_sentiment: str, stock_sentiment: str) -> str:
    """分析市场情绪
    
    Args:
        market_sentiment: 市场情绪数据
        stock_sentiment: 个股情绪数据
    """
    return f"请分析以下情绪数据：\n\n市场情绪:\n{market_sentiment}\n\n个股情绪:\n{stock_sentiment}"


# ============ Agent 定义 ============

SENTIMENT_SYSTEM_PROMPT = """你是市场情绪分析师，专门分析股票的市场情绪。

你的职责：
1. 使用工具获取龙虎榜数据
2. 分析热点板块轮动
3. 判断市场情绪（恐慌/中性/乐观）
4. 给出操作建议

重要：
- 必须使用工具获取数据
- 关注资金流向和情绪指标
- 给出明确操作建议"""


class SentimentAgentLangGraph(LangGraphAgent):
    """情绪 Agent - LangGraph 版本"""
    
    def __init__(self):
        super().__init__("情绪Agent", SENTIMENT_SYSTEM_PROMPT)
    
    def get_tools(self):
        return [get_market_sentiment, get_stock_sentiment, do_sentiment_analysis]
    
    def _build_prompt(self, stock_code: str, data: dict) -> str:
        return f"""请分析股票 {stock_code} 的市场情绪：

1. 使用 get_market_sentiment 工具获取市场情绪
2. 使用 get_stock_sentiment 工具获取个股情绪
3. 综合分析给出操作建议

注意：必须调用工具获取数据。"""


# 便捷函数
def analyze_sentiment(stock_code: str) -> str:
    """分析情绪"""
    agent = SentimentAgentLangGraph()
    return agent.analyze(stock_code)


if __name__ == "__main__":
    result = analyze_sentiment("600519")
    logger.info(result)

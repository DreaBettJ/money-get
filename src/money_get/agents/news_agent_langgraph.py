"""新闻分析 Agent - LangGraph 版本"""
from langchain_core.tools import tool
from langchain.agents import create_agent
from money_get.agents.langgraph_base import LangGraphAgent
from money_get.scraper import get_realtime_news, get_hot_sectors
from money_get.logger import logger as _logger


# ============ 工具定义 ============

@tool
def get_news(stock_code: str) -> str:
    """获取股票相关新闻
    
    Args:
        stock_code: 股票代码，如 600519
    """
    try:
        news = get_realtime_news(limit=10)
        if not news:
            return f"{stock_code}: 暂无新闻"
        
        result = f"股票新闻:\n"
        for i, n in enumerate(news[:10], 1):
            result += f"{i}. {n.get('title', '无标题')}\n"
            result += f"   来源: {n.get('source', '')} | 时间: {n.get('time', '')}\n"
        
        return result
    except Exception as e:
        return f"获取新闻失败: {e}"


@tool
def get_market_news() -> str:
    """获取市场重大新闻
    
    返回今日市场重要新闻和公告。
    """
    try:
        news = get_realtime_news(limit=5)
        if not news:
            return "暂无市场新闻"
        
        result = "今日市场重大新闻:\n"
        for i, n in enumerate(news[:5], 1):
            result += f"{i}. {n.get('title', '无标题')}\n"
            result += f"   {n.get('source', '')}\n"
        
        return result
    except Exception as e:
        return f"获取市场新闻失败: {e}"


@tool
def analyze_news_impact(news_data: str, market_news: str) -> str:
    """分析新闻影响
    
    Args:
        news_data: 新闻数据
        market_news: 市场新闻
    """
    return f"请分析以下新闻的影响：\n\n新闻:\n{news_data}\n\n市场新闻:\n{market_news}"


# ============ Agent 定义 ============

NEWS_SYSTEM_PROMPT = """你是资深财经新闻分析师，专门分析股票相关的新闻和公告。

你的职责：
1. 使用工具获取相关新闻
2. 分析公司新闻（业绩、并购、减持等）
3. 分析行业政策影响
4. 判断利好/利空
5. 评估影响程度

重要：
- 必须使用工具获取数据
- 识别重大利空（减持、亏损、诉讼等）
- 给出明确操作建议"""


class NewsAgentLangGraph(LangGraphAgent):
    """新闻 Agent - LangGraph 版本"""
    
    def __init__(self):
        super().__init__("新闻Agent", NEWS_SYSTEM_PROMPT)
    
    def get_tools(self):
        return [get_news, get_market_news, analyze_news_impact]
    
    def _build_prompt(self, stock_code: str, data: dict) -> str:
        return f"""请分析股票 {stock_code} 的新闻：

1. 使用 get_news 工具获取个股新闻
2. 使用 get_market_news 工具获取市场新闻
3. 分析新闻影响
4. 给出操作建议

注意：必须调用工具获取数据。"""


# 便捷函数
def analyze_news(stock_code: str) -> str:
    """分析新闻"""
    agent = NewsAgentLangGraph()
    return agent.analyze(stock_code)


if __name__ == "__main__":
    result = analyze_news("600519")
    print(result)

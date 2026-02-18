"""
money-get 多Agent股票分析系统

架构说明:
- 5个专业Agent: 资金/新闻/情绪/研究/决策
- 支持3种协作模式: parallel/sequential/hybrid  
- 上下文隔离: 每个股票的记忆独立
- 异动监控: 自动检测重大利好/利空
"""
from .base import BaseAgent

# 分析Agent
from .fund_agent import FundAgent, analyze_fund
from .news_agent import NewsAgent, analyze_news
from .sentiment_agent import SentimentAgent, analyze_sentiment
from .research_agent import ResearchAgent, research
from .decision_agent import DecisionAgent, decide
from .alert_agent import MarketAlertAgent, analyze_market_movement, quick_market_check

# 协作与工具
from .cache import clear_cache
from .collaboration import (
    AgentTeam,
    MultiAgentOrchestrator,
    parallel_analyze,
    hybrid_analyze,
    COLLABORATION_MODES
)
from ..context import ContextScope, get_isolated_context, add_stock_summary


class TradingAgents:
    """多Agent交易系统 - 核心入口"""
    
    def __init__(self, mode: str = "hybrid"):
        """
        Args:
            mode: 协作模式 (parallel/sequential/hybrid)
        """
        self.mode = mode
        self.fund = FundAgent()
        self.news = NewsAgent()
        self.sentiment = SentimentAgent()
        self.research = ResearchAgent()
        self.decision = DecisionAgent()
        self.orchestrator = MultiAgentOrchestrator(mode=mode)
    
    def analyze(self, stock_code: str) -> dict:
        """完整分析"""
        with ContextScope(stock_code):
            results = self.orchestrator.analyze(stock_code, {
                "fund": self.fund,
                "news": self.news,
                "sentiment": self.sentiment,
                "research": self.research,
                "decision": self.decision
            })
            # 保存记忆
            try:
                add_stock_summary(stock_code, f"决策: {results.get('decision','')[:200]}")
            except:
                pass
            return results
    
    def quick(self, stock_code: str) -> str:
        """快速决策"""
        return self.analyze(stock_code).get('decision', '')


# 便捷函数
analyze = lambda code: TradingAgents().analyze(code)
quick_decide = lambda code: TradingAgents().quick(code)
market_check = quick_market_check
market_analysis = analyze_market_movement


__all__ = [
    # 核心类
    'TradingAgents',
    'BaseAgent',
    # Agent
    'FundAgent',
    'NewsAgent', 
    'SentimentAgent',
    'ResearchAgent',
    'DecisionAgent',
    'MarketAlertAgent',
    # 便捷函数
    'analyze',
    'quick_decide',
    'market_check',
    'market_analysis',
    # 协作
    'MultiAgentOrchestrator',
    'hybrid_analyze',
    'parallel_analyze',
    # 工具
    'ContextScope',
    'clear_cache',
]

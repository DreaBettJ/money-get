"""多Agent股票分析系统"""
from .base import BaseAgent
from .fund_agent import FundAgent, analyze_fund
from .news_agent import NewsAgent, analyze_news
from .sentiment_agent import SentimentAgent, analyze_sentiment
from .research_agent import ResearchAgent, research
from .decision_agent import DecisionAgent, decide
from .cache import clear_cache


class TradingAgents:
    """多Agent交易系统"""
    
    def __init__(self):
        self.fund_agent = FundAgent()
        self.news_agent = NewsAgent()
        self.sentiment_agent = SentimentAgent()
        self.research_agent = ResearchAgent()
        self.decision_agent = DecisionAgent()
    
    def analyze(self, stock_code: str, use_cache: bool = True) -> dict:
        """完整分析流程
        
        Args:
            stock_code: 股票代码
            use_cache: 是否使用缓存
        
        Returns:
            dict: 各Agent的分析结果
        """
        results = {
            'stock_code': stock_code,
        }
        
        # 1. 资金Agent
        results['fund'] = self.fund_agent.analyze(stock_code)
        
        # 2. 消息Agent
        results['news'] = self.news_agent.analyze(stock_code)
        
        # 3. 情绪Agent
        results['sentiment'] = self.sentiment_agent.analyze(stock_code)
        
        # 4. 研究Agent（多空辩论）
        results['research'] = self.research_agent.analyze(
            stock_code,
            fund_analysis=results['fund'],
            news_analysis=results['news'],
            sentiment_analysis=results['sentiment']
        )
        
        # 5. 决策Agent（最终决策）
        results['decision'] = self.decision_agent.analyze(
            stock_code,
            fund_analysis=results['fund'],
            news_analysis=results['news'],
            sentiment_analysis=results['sentiment'],
            research_result=results['research']
        )
        
        return results
    
    def quick_decide(self, stock_code: str) -> str:
        """快速决策（直接输出结论）"""
        results = self.analyze(stock_code)
        return results['decision']


def analyze(stock_code: str) -> dict:
    """便捷函数 - 完整分析"""
    return TradingAgents().analyze(stock_code)


def quick_decide(stock_code: str) -> str:
    """便捷函数 - 快速决策"""
    return TradingAgents().quick_decide(stock_code)


__all__ = [
    'TradingAgents',
    'analyze',
    'quick_decide',
    'analyze_fund',
    'analyze_news', 
    'analyze_sentiment',
    'research',
    'decide',
    'clear_cache'
]

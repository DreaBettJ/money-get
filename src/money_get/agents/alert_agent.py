"""市场异动Agent - 监控全市场新闻异动"""
from .base import BaseAgent
from money_get.market_alert import (
    get_breaking_news,
    format_alert,
    filter_market_news,
    detect_news_sentiment
)
from money_get.db import get_news


class MarketAlertAgent(BaseAgent):
    """市场异动Agent - 监控全市场异动"""
    
    def __init__(self):
        super().__init__("异动Agent")
    
    def get_system_prompt(self) -> str:
        return """你是市场异动监控专家，专门分析全市场新闻异动。

你的职责：
1. 识别重大利好新闻（并购、业绩大增、回购、涨价等）
2. 识别重大利空新闻（减持、亏损、诉讼等）
3. 判断异动级别（一般/较大/重大）
4. 给出操作建议

输出格式：
- 先列出异动新闻
- 然后给出分析结论"""
    
    def analyze(self, stock_code: str = None, **kwargs) -> str:
        """分析异动
        
        Args:
            stock_code: 可选，指定股票代码
        """
        # 获取异动新闻
        breaking = get_breaking_news(limit=30)
        
        if not breaking:
            return self.format_output("📊 市场异动", "今日无重大异动新闻")
        
        # 按股票分组
        stock_alerts = {}
        for news in breaking:
            code = news.get("code", "unknown")
            if code not in stock_alerts:
                stock_alerts[code] = []
            stock_alerts[code].append(news)
        
        # 构建提示
        prompt = self._build_prompt(stock_alerts)
        
        # 调用LLM
        result = self.call_llm(prompt)
        
        return self.format_output("📊 市场异动监控", result)
    
    def _build_prompt(self, stock_alerts: dict) -> str:
        """构建异动提示"""
        lines = ["发现以下市场异动新闻：\n"]
        
        for code, news_list in list(stock_alerts.items())[:10]:
            sentiment = news_list[0].get("sentiment", "中性")
            emoji = "🔥" if sentiment == "利好" else "⚠️"
            
            lines.append(f"\n{emoji} {code}")
            
            for news in news_list[:2]:
                title = news.get("title", "")[:50]
                reason = news.get("reason", "")
                lines.append(f"  - {title}")
                if reason:
                    lines.append(f"    原因: {reason}")
        
        lines.append("\n\n请分析：")
        lines.append("1. 这些异动的级别（一般/较大/重大）")
        lines.append("2. 哪些值得买入/需要回避")
        lines.append("3. 给出操作建议")
        
        return "\n".join(lines)
    
    def quick_check(self) -> str:
        """快速检查（不调用LLM）"""
        breaking = get_breaking_news(limit=30)
        return format_alert(breaking)


def analyze_market_movement() -> str:
    """便捷函数 - 分析市场异动"""
    return MarketAlertAgent().analyze()


def quick_market_check() -> str:
    """快速检查（不调用LLM）"""
    return MarketAlertAgent().quick_check()

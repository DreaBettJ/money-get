"""研究Agent - 多空辩论"""
from .base import BaseAgent


class ResearchAgent(BaseAgent):
    """研究Agent - 多空辩论"""
    
    def __init__(self):
        super().__init__("研究Agent")
    
    def get_system_prompt(self) -> str:
        return """你是资深股票研究员，负责多空辩论。

你的职责：
1. 汇总各维度分析
2. 进行多空辩论
3. 给出平衡观点

注意：要同时考虑买入理由和风险点。"""
    
    def analyze(self, stock_code: str, fund_analysis: str = "", 
                news_analysis: str = "", sentiment_analysis: str = "", **kwargs) -> str:
        """多空辩论"""
        
        # 构建提示词
        prompt = self._build_prompt(stock_code, fund_analysis, 
                                    news_analysis, sentiment_analysis)
        
        # 调用LLM
        result = self.call_llm(prompt)
        
        return self.format_output(f"🔬 研究辩论 - {stock_code}", result)
    
    def _build_prompt(self, stock_code: str, fund: str, news: str, sentiment: str) -> str:
        """构建多空辩论提示词"""
        
        prompt = f"""股票代码: {stock_code}

请基于以下分析进行多空辩论：

=== 资金面分析 ===
{fund}

=== 新闻面分析 ===
{news}

=== 情绪面分析 ===
{sentiment}

请按以下格式输出辩论结果：

## 多方观点（买入理由）
1. ...
2. ...

## 空方观点（风险点）
1. ...
2. ...

## 平衡结论
- 当前状态：看多/看空/震荡
- 主要理由：...
- 风险提示：...

注意：只输出辩论结论，不要输出代码。"""
        
        return prompt


def research(stock_code: str, fund: str, news: str, sentiment: str) -> str:
    """便捷函数"""
    return ResearchAgent().analyze(stock_code, fund, news, sentiment)

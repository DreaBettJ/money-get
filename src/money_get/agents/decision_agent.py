"""决策Agent - 最终决策（含原则+风控）"""
from .base import BaseAgent


class DecisionAgent(BaseAgent):
    """决策Agent - 最终决策"""
    
    def __init__(self):
        super().__init__("决策Agent")
    
    def get_system_prompt(self) -> str:
        return """你是资深股票交易员，负责最终决策。

你的交易原则：
1. 只买行业龙头
2. 不追高，只低吸
3. 阶梯止盈：10%卖20%，15%卖20%，20%卖20%，30%清仓
4. 止损：-5%

输出要求：
- 简洁明确
- 给出具体价格
- 严格执行原则"""
    
    def analyze(self, stock_code: str, 
                fund_analysis: str = "", 
                news_analysis: str = "",
                sentiment_analysis: str = "",
                research_result: str = "",
                **kwargs) -> str:
        """最终决策"""
        
        # 获取用户的交易原则
        principles = self._get_principles()
        
        # 构建提示词
        prompt = self._build_prompt(stock_code, fund_analysis, 
                                    news_analysis, sentiment_analysis,
                                    research_result, principles)
        
        # 调用LLM
        result = self.call_llm(prompt)
        
        return self.format_output(f"⚖️ 决策 - {stock_code}", result)
    
    def _get_principles(self) -> str:
        """获取用户原则"""
        try:
            from money_get.memory import get_shared_memory
            principles = get_shared_memory('principles')
            patterns = get_shared_memory('patterns')
            
            result = "【交易原则】\n"
            for p in principles:
                result += f"- {p}\n"
            
            result += "\n【交易规律】\n"
            for p in patterns:
                result += f"- {p}\n"
            
            return result
        except:
            return """【默认原则】
- 只买行业龙头
- 不追高，只低吸
- 阶梯止盈：10%卖20%，15%卖20%，20%卖20%，30%清仓
- 止损：-5%"""
    
    def _build_prompt(self, stock_code: str, fund: str, news: str, 
                      sentiment: str, research: str, principles: str) -> str:
        """构建决策提示词"""
        
        prompt = f"""股票代码: {stock_code}

{principles}

=== 资金面分析 ===
{fund}

=== 新闻面分析 ===
{news}

=== 情绪面分析 ===
{sentiment}

=== 研究辩论结论 ===
{research}

请给出最终决策：

## 决策
- 操作：买入/卖出/观望
- 买入价：
- 止损价：
- 目标价（阶梯）：
- 仓位建议：

## 决策理由
（简述核心逻辑）

注意：
1. 严格执行止盈止损原则
2. 不追高（涨幅>5%不追）
3. 达到止损必须卖出
4. 只输出决策结论"""
        
        return prompt


def decide(stock_code: str, fund: str, news: str, sentiment: str, research: str) -> str:
    """便捷函数"""
    return DecisionAgent().analyze(stock_code, fund, news, sentiment, research)

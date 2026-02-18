"""资金Agent - 分析资金流向"""
from .base import BaseAgent
from .cache import get_cache_key, get_cached_result, save_cache, CACHE_CONFIG
from money_get.db import get_fund_flow_data, get_kline, get_stock, get_realtime_price
import logging

logger = logging.getLogger("money_get")


class FundAgent(BaseAgent):
    """资金Agent - 分析资金流向"""
    
    def __init__(self):
        super().__init__("资金Agent")
    
    def get_system_prompt(self) -> str:
        return """你是资深资金分析师，专门分析股票的资金流向。

你的职责：
1. 分析主力资金净流入/流出
2. 判断资金活跃度
3. 识别资金建仓/出货迹象

输出格式要求：
- 用中文输出
- 数据要具体
- 给出明确结论"""
    
    def analyze(self, stock_code: str, **kwargs) -> str:
        """分析资金流向"""
        # 获取数据
        fund_data = get_fund_flow_data(stock_code, limit=10)
        klines = get_kline(stock_code, limit=30)
        stock = get_stock(stock_code) or {}
        
        # 尝试获取实时价格
        realtime = get_realtime_price(stock_code)
        
        # 准备数据
        data = {
            'stock_code': stock_code,
            'stock_name': stock.get('name') or stock_code,
            'fund_flow': [dict(f) for f in fund_data] if fund_data else [],
            'price_data': [dict(k) for k in klines] if klines else [],
            'realtime': realtime if realtime else {}
        }
        
        # 生成key
        prompt = "分析以下股票的资金流向，给出买入/卖出/观望建议："
        cache_key = get_cache_key(data, prompt)
        
        # 尝试缓存
        cached = get_cached_result(cache_key, max_age_days=CACHE_CONFIG['fund_agent'])
        if cached:
            return f"[资金Agent - 缓存]\n{cached}"
        
        # 构建提示词
        prompt = self._build_prompt(data)
        
        # 调用LLM
        result = self.call_llm(prompt)
        
        # 缓存结果
        save_cache(cache_key, result)
        
        return self.format_output(f"💰 资金分析 - {stock.get('name', stock_code)}", result)
    
    def _build_prompt(self, data: dict) -> str:
        """构建提示词"""
        stock_name = data.get('stock_name', '')
        fund_flow = data.get('fund_flow', [])
        realtime = data.get('realtime', {})
        
        # 实时价格
        price_info = ""
        if realtime:
            price_info = f"""当前价格:
- 最新价: {realtime.get('price', 'N/A')}
- 涨跌: {realtime.get('change', 'N/A')}
- 涨跌幅: {realtime.get('pct', 'N/A')}%
- 成交量: {realtime.get('volume', 'N/A')}
- 成交额: {realtime.get('amount', 'N/A')}

"""
        
        # 整理资金数据
        fund_info = f"股票: {stock_name}\n\n{price_info}资金流向(近10日):\n"
        for f in fund_flow:
            date = f.get('date', '')
            net_main = f.get('net_main', 'N/A')
            net_huge = f.get('net_huge', 'N/A')
            net_large = f.get('net_large', 'N/A')
            fund_info += f"- {date}: 主力={net_main}, 大单={net_large}, 超大单={net_huge}\n"
        
        prompt = f"""{fund_info}

请分析：
1. 资金整体流向（流入/流出）
2. 主力动向（建仓/出货）
3. 当前状态（活跃/观望）
4. 给出操作建议（买入/卖出/观望）及理由

注意：只输出分析结论，不要输出代码。"""
        
        return prompt


def analyze_fund(stock_code: str) -> str:
    """便捷函数"""
    return FundAgent().analyze(stock_code)

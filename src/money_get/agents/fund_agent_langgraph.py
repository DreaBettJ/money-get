"""资金分析 Agent - LangGraph 版本"""
from langchain_core.tools import tool
from langchain.agents import create_agent
from money_get.agents.langgraph_base import (
    LangGraphAgent, create_base_llm, get_langfuse_handler, data_tool
)
from money_get.db import get_fund_flow_data, get_kline, get_stock, get_realtime_price
from money_get.logger import logger as _logger


# ============ 工具定义 ============

@tool
def get_fund_flow(stock_code: str) -> str:
    """获取股票资金流向数据（近10日）
    
    Args:
        stock_code: 股票代码，如 600519
    """
    try:
        data = get_fund_flow_data(stock_code, limit=10)
        if not data:
            return f"{stock_code}: 暂无资金流向数据"
        
        result = f"股票 {stock_code} 资金流向（近10日）:\n"
        for item in data[:10]:
            result += f"- {item.get('date')}: 主力净流入={item.get('net_main')}, 大单净流入={item.get('net_large')}\n"
        
        return result
    except Exception as e:
        return f"获取资金流向失败: {e}"


@tool
def get_price_data(stock_code: str, days: int = 30) -> str:
    """获取股票价格和K线数据
    
    Args:
        stock_code: 股票代码
        days: 获取天数，默认30天
    """
    try:
        klines = get_kline(stock_code, limit=days)
        stock = get_stock(stock_code) or {}
        
        result = f"股票 {stock_code} ({stock.get('name', '')}) 价格数据:\n"
        
        # 最新价
        realtime = get_realtime_price(stock_code)
        if realtime:
            result += f"最新价: {realtime.get('price')}元, "
            result += f"涨跌: {realtime.get('change')}元, "
            result += f"涨跌幅: {realtime.get('pct')}%\n"
        
        # K线数据
        if klines:
            result += f"\n最近{klines.__len__()}日行情:\n"
            for k in klines[:5]:
                result += f"- {k.get('date')}: 收盘{k.get('close')}元, 成交量{k.get('volume')}\n"
        
        return result
    except Exception as e:
        return f"获取价格数据失败: {e}"


@tool
def analyze_fund_flow(fund_data: str, price_data: str) -> str:
    """分析资金流向和价格数据
    
    这个工具会结合资金流向和价格数据给出分析结论。
    
    Args:
        fund_data: 资金流向数据字符串
        price_data: 价格数据字符串
    """
    # 这个工具只是标记，实际分析由 LLM 完成
    return f"请分析以下数据并给出资金流向判断：\n\n资金数据:\n{fund_data}\n\n价格数据:\n{price_data}"


# ============ Agent 定义 ============

FUND_SYSTEM_PROMPT = """你是资深资金分析师，专门分析股票的资金流向。

你的职责：
1. 使用工具获取资金流向数据
2. 分析主力资金净流入/流出
3. 判断资金活跃度
4. 识别资金建仓/出货迹象

重要：
- 必须使用工具获取数据
- 数据不足时明确说明
- 给出明确操作建议（买入/卖出/观望）"""


class FundAgentLangGraph(LangGraphAgent):
    """资金 Agent - LangGraph 版本"""
    
    def __init__(self):
        super().__init__("资金Agent", FUND_SYSTEM_PROMPT)
    
    def get_tools(self):
        return [get_fund_flow, get_price_data, analyze_fund_flow]
    
    def _build_prompt(self, stock_code: str, data: dict) -> str:
        return f"""请分析股票 {stock_code} 的资金流向：

1. 首先使用 get_fund_flow 工具获取资金流向数据
2. 使用 get_price_data 工具获取价格数据
3. 分析资金流向和价格关系
4. 给出操作建议

注意：必须调用工具获取数据，不要假设。"""


# 便捷函数
def analyze_fund(stock_code: str) -> str:
    """分析资金流向"""
    agent = FundAgentLangGraph()
    return agent.analyze(stock_code)


if __name__ == "__main__":
    # 测试
    result = analyze_fund("300719")
    print(result)

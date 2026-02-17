"""LLM 分析服务

基于 MiniMax API 提供股票分析能力
"""
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

# 读取配置
def get_config() -> dict:
    # 项目根目录的 config.json
    config_path = Path(__file__).parent.parent.parent.parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_llm_client():
    """获取 LLM 客户端"""
    try:
        from langchain_openai import ChatOpenAI
        config = get_config()
        llm_config = config.get("llm", {})
        
        return ChatOpenAI(
            model=llm_config.get("model", "MiniMax-M2.5"),
            openai_api_key=llm_config.get("api_key", ""),
            openai_api_base=llm_config.get("url", "https://api.minimax.chat/v1"),
            temperature=0.7,
        )
    except Exception as e:
        print(f"LLM init error: {e}")
        return None


def build_prompt(stock_code: str, data: Dict) -> str:
    """构建分析提示词"""
    
    # 提取数据
    kline = data.get("kline", [])
    indicators = data.get("indicators", {})
    fund_flow = data.get("fund_flow", {})
    news = data.get("news", [])
    lhb = data.get("lhb", [])
    sectors = data.get("sectors", [])
    
    # 格式化 K线
    kline_text = ""
    if kline:
        kline_text = "## 近期K线\n"
        for k in kline[-5:]:
            kline_text += f"- {k.get('date')}: 开盘 {k.get('open')}, 收盘 {k.get('close')}, 成交量 {k.get('volume')}\n"
    
    # 格式化指标
    indicators_text = ""
    if indicators:
        indicators_text = f"""## 技术指标
- MA5: {indicators.get('ma5', 'N/A')}
- MA20: {indicators.get('ma20', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}
- RSI: {indicators.get('rsi24', 'N/A')}
"""
    
    # 格式化资金流向
    fund_text = ""
    if fund_flow:
        fund_text = f"""## 资金流向
- 主力净流入: {fund_flow.get('main_net_inflow', 'N/A')}
- 超大单净流入: {fund_flow.get('super_net_inflow', 'N/A')}
- 大单净流入: {fund_flow.get('large_net_inflow', 'N/A')}
"""
    
    # 格式化新闻
    news_text = ""
    if news:
        news_text = "## 近期新闻\n"
        for n in news[:5]:
            news_text += f"- {n.get('title', '')}\n"
    
    # 格式化龙虎榜
    lhb_text = ""
    if lhb:
        lhb_text = "## 龙虎榜\n"
        for l in lhb[:3]:
            lhb_text += f"- {l.get('name', '')}: 净买入 {l.get('net_amount', 'N/A')}\n"
    
    # 格式化热点板块
    sector_text = ""
    if sectors:
        sector_text = "## 热点板块\n"
        for s in sectors[:5]:
            sector_text += f"- {s.get('板块名称', '')}: 涨跌幅 {s.get('涨跌幅', 'N/A')}%\n"
    
    prompt = f"""你是一位专业的A股分析师。请根据以下数据对股票 {stock_code} 进行全面分析：

{kline_text}

{indicators_text}

{fund_text}

{news_text}

{lhb_text}

{sector_text}

请给出：
1. 短期走势判断（上涨/下跌/震荡）
2. 关键技术信号
3. 资金面分析
4. 消息面影响
5. 综合操作建议（买入/卖出/持有）

注意：
- 用简洁的中文回答
- 每个部分不超过 2 句话
- 最后给出明确的操作建议
"""
    return prompt


def analyze_stock(stock_code: str) -> Dict[str, Any]:
    """分析股票"""
    from money_get.db import (
        get_kline, get_indicators, get_fund_flow_data,
        get_news, get_lhb_data, get_hot_sectors
    )
    
    # 获取本地数据
    kline = get_kline(stock_code, limit=10)
    indicators = get_indicators(stock_code)
    fund_flow = get_fund_flow_data(stock_code, limit=1)
    news = get_news(stock_code, limit=10)
    lhb = get_lhb_data(stock_code, limit=10)
    sectors = get_hot_sectors(limit=10)
    
    # 构建数据字典
    data = {
        "kline": kline,
        "indicators": indicators,
        "fund_flow": fund_flow[0] if fund_flow else {},
        "news": news,
        "lhb": lhb,
        "sectors": sectors
    }
    
    # 构建提示词
    prompt = build_prompt(stock_code, data)
    
    # 调用 LLM
    llm = get_llm_client()
    if not llm:
        return {"error": "LLM 初始化失败"}
    
    try:
        response = llm.invoke(prompt)
        return {
            "stock_code": stock_code,
            "analysis": response.content,
            "data": data
        }
    except Exception as e:
        return {"error": str(e)}


def analyze_market() -> str:
    """分析整体市场"""
    from money_get.db import get_hot_sectors, get_north_money, get_lhb_data
    
    sectors = get_hot_sectors(limit=10)
    north = get_north_money(limit=5)
    lhb = get_lhb_data(limit=20)
    
    # 热点板块
    sector_text = "## 热点板块\n"
    if sectors:
        for s in sectors[:5]:
            sector_text += f"- {s.get('sector_name', '')}: {s.get('change_percent', 'N/A')}%\n"
    
    # 北向资金
    north_text = "## 北向资金\n"
    if north:
        for n in north[:3]:
            north_text += f"- {n.get('date', '')}: 沪股通 {n.get('hk_sh_inflow', 0)}, 深股通 {n.get('hk_sz_inflow', 0)}\n"
    
    prompt = f"""你是一位专业的A股市场分析师。请根据以下数据对当前市场进行整体分析：

{sector_text}

{north_text}

请给出：
1. 市场整体走势判断
2. 资金面分析
3. 热点板块机会
4. 风险提示

注意：用简洁的中文回答，每个部分不超过 2 句话。
"""
    
    llm = get_llm_client()
    if not llm:
        return "LLM 初始化失败"
    
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"分析失败: {e}"

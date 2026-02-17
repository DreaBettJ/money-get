"""分析服务"""
from typing import Optional

from money_get.data.stock import fetch_price, fetch_kline, fetch_info
from money_get.data.trade import get_trades, get_stats


def analyze_stock(stock_code: str, days: int = 30) -> str:
    """分析股票"""
    # 获取数据
    price_data = fetch_price(stock_code)
    kline_data = fetch_kline(stock_code, days)

    if price_data.get("error"):
        return f"获取数据失败: {price_data['error']}"

    # 简单分析
    name = price_data.get("name", stock_code)
    price = price_data.get("price", 0)
    change = price_data.get("change", 0)

    kline_list = kline_data.get("data", [])
    if kline_list:
        latest = kline_list[-1]
        volume = latest.get("成交量", 0)
        amount = latest.get("成交额", 0)
    else:
        volume = amount = 0

    report = f"""## {name} ({stock_code}) 分析

### 实时行情
- 最新价: {price}
- 涨跌幅: {change}%

### K线数据 (近 {days} 天)
- 成交量: {volume:,}
- 成交额: {amount:,}

### 建议
{get_suggestion(change, volume)}
"""
    return report


def get_suggestion(change: float, volume: int) -> str:
    """基于数据给出建议"""
    if change > 5:
        return "涨幅较大，注意风险"
    elif change < -5:
        return "跌幅较大，关注支撑位"
    elif change > 0:
        return "震荡上行趋势"
    else:
        return "震荡下行趋势"


def review_trades(trades: list) -> str:
    """复盘交易"""
    if not trades:
        return "暂无交易记录"

    stats = get_stats()

    report = f"""## 交易复盘

### 总体统计
- 总交易次数: {stats['total']}
- 盈利次数: {stats['wins']}
- 亏损次数: {stats['losses']}
- 胜率: {stats['win_rate']:.1%}
- 盈亏比: {stats['profit_ratio']:.2f}

### 交易明细
"""
    for t in trades:
        direction = "买入" if t["direction"] == "buy" else "卖出"
        report += f"- {t['date']} {direction} {t['stock_name']} @ {t['price']} x {t['quantity']}\n"

    return report


def analyze_market() -> str:
    """市场分析"""
    from money_get.data.stock import fetch_sector_flow, fetch_hot_sectors

    flow = fetch_sector_flow()
    hot = fetch_hot_sectors()

    report = "## 市场分析\n\n### 资金流向\n"
    if flow.get("data"):
        for item in flow["data"][:10]:
            report += f"- {item.get('名称')}: {item.get('涨跌幅')}%\n"

    report += "\n### 热点板块\n"
    if hot.get("data"):
        for item in hot["data"][:10]:
            report += f"- {item.get('板块名称')}: {item.get('涨跌幅')}%\n"

    return report

"""Agent 工具定义"""
from langchain_core.tools import tool
from money_get.data.stock import fetch_price, fetch_kline, fetch_info, fetch_sector_flow
from money_get.data.trade import save_trade, get_trades


@tool
def get_stock_price(stock_code: str) -> dict:
    """获取股票实时行情"""
    return fetch_price(stock_code)


@tool
def get_kline(stock_code: str, days: int = 30) -> dict:
    """获取股票K线数据"""
    return fetch_kline(stock_code, days)


@tool
def get_stock_info(stock_code: str) -> dict:
    """获取股票基本信息"""
    return fetch_info(stock_code)


@tool
def get_sector_flow() -> dict:
    """获取板块资金流向"""
    return fetch_sector_flow()


@tool
def save_trade_record(
    stock_code: str,
    stock_name: str,
    direction: str,
    price: float,
    quantity: int,
    date: str,
    reason: str = "",
    notes: str = "",
) -> str:
    """保存交易记录"""
    from money_get.data.trade import Trade

    trade = Trade(
        stock_code=stock_code,
        stock_name=stock_name,
        direction=direction,
        price=price,
        quantity=quantity,
        date=date,
        reason=reason,
        notes=notes,
    )
    save_trade(trade)
    return f"已保存交易记录: {direction} {stock_code} @ {price}"


@tool
def get_trade_records(stock_code: str = "") -> list:
    """查询交易记录"""
    return get_trades(stock_code)


TOOLS = [
    get_stock_price,
    get_kline,
    get_stock_info,
    get_sector_flow,
    save_trade_record,
    get_trade_records,
]

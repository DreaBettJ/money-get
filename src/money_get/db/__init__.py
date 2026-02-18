"""数据库模块

功能：
- 自动迁移
- 股票、K线、指标、交易记录的 CRUD
- 实时数据爬取（东方财富）
"""
from .db import (
    init_db,
    get_connection,
    # 股票
    upsert_stock,
    get_stock,
    get_all_stocks,
    # K线
    insert_kline,
    get_kline,
    # 指标
    insert_indicators,
    get_indicators,
    # 交易
    insert_trade,
    get_trades,
    get_trade_stats,
    # 同步
    sync_stock_data,
    # 资金流向
    insert_fund_flow,
    get_fund_flow_data,
    # 龙虎榜
    insert_lhb,
    get_lhb_data,
    # 北向资金
    insert_north_money,
    get_north_money,
    # 新闻
    insert_news,
    get_news,
    # 热点板块
    insert_hot_sector,
    get_hot_sectors,
)

# 实时数据爬取
from ..scraper import (
    get_stock_price,
    get_fund_flow as scrape_fund_flow,
    get_hot_sectors as scrape_hot_sectors,
    get_realtime_news,
)


def get_realtime_price(code: str) -> dict:
    """获取实时价格（从东方财富爬取）
    
    Args:
        code: 股票代码
    
    Returns:
        dict: 价格数据
    """
    return get_stock_price(code)


def refresh_hot_sectors() -> list:
    """刷新热点板块（从东方财富爬取）
    
    Returns:
        list: 热点板块列表
    """
    from datetime import datetime
    
    sectors = scrape_hot_sectors()
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 存入数据库
    for s in sectors:
        insert_hot_sector(
            sector_name=s.get('name', ''),
            date=today,
            data=s
        )
    
    return sectors


__all__ = [
    "init_db",
    "get_connection",
    # 股票
    "upsert_stock",
    "get_stock",
    "get_all_stocks",
    # K线
    "insert_kline",
    "get_kline",
    # 指标
    "insert_indicators",
    "get_indicators",
    # 交易
    "insert_trade",
    "get_trades",
    "get_trade_stats",
    # 同步
    "sync_stock_data",
    # 资金流向
    "insert_fund_flow",
    "get_fund_flow_data",
    # 龙虎榜
    "insert_lhb",
    "get_lhb_data",
    # 北向资金
    "insert_north_money",
    "get_north_money",
    # 新闻
    "insert_news",
    "get_news",
    # 热点板块
    "insert_hot_sector",
    "get_hot_sectors",
    # 实时数据
    "get_realtime_price",
    "refresh_hot_sectors",
]

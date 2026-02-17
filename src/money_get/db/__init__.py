"""数据库模块

功能：
- 自动迁移
- 股票、K线、指标、交易记录的 CRUD
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
]

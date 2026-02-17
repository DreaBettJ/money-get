"""数据库管理模块

功能：
- 数据库连接
- 自动迁移
- CRUD 操作
"""
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 数据库路径
DB_DIR = Path(__file__).parent.parent.parent.parent / "data" / "db"
DB_PATH = DB_DIR / "money_get.db"


def get_db_path() -> Path:
    """获取数据库路径"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(str(get_db_path()))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库 - 运行所有迁移"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取已执行的迁移
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
    """)
    cursor.execute("SELECT version FROM schema_migrations")
    applied = set(row[0] for row in cursor.fetchall())
    
    # 获取迁移文件
    migrations_dir = Path(__file__).parent / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    # 执行未应用的迁移
    for mf in migration_files:
        version = mf.stem  # e.g., "001_initial"
        if version not in applied:
            logger.info(f"Applying migration: {version}")
            sql = mf.read_text(encoding="utf-8")
            cursor.executescript(sql)
            conn.commit()
            logger.info(f"Migration {version} applied")
    
    conn.close()
    logger.info(f"Database initialized at: {get_db_path()}")


# ==================== 股票操作 ====================

def upsert_stock(code: str, name: str, industry: str = None, market: str = None) -> bool:
    """插入或更新股票"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO stocks (code, name, industry, market, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(code) DO UPDATE SET
            name = excluded.name,
            industry = excluded.industry,
            market = excluded.market,
            updated_at = datetime('now')
    """, (code, name, industry, market))
    conn.commit()
    conn.close()
    return True


def get_stock(code: str) -> Optional[Dict]:
    """获取股票信息"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stocks WHERE code = ?", (code,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_stocks() -> List[Dict]:
    """获取所有股票"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stocks ORDER BY code")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ==================== K线操作 ====================

def insert_kline(code: str, date: str, open: float, high: float, low: float, 
                  close: float, volume: int, amount: float) -> bool:
    """插入K线数据"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO daily_kline 
        (code, date, open, high, low, close, volume, amount, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (code, date, open, high, low, close, volume, amount))
    conn.commit()
    conn.close()
    return True


def get_kline(code: str, start_date: str = None, end_date: str = None, limit: int = 100) -> List[Dict]:
    """获取K线数据"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM daily_kline WHERE code = ?"
    params = [code]
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    
    query += " ORDER BY date DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ==================== 指标操作 ====================

def insert_indicators(code: str, date: str, indicators: Dict) -> bool:
    """插入技术指标"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO indicators 
        (code, date, ma5, ma10, ma20, ma60, dif, dea, macd, 
         rsi6, rsi12, rsi24, k, d, j, boll_upper, boll_middle, boll_lower, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        code, date,
        indicators.get("ma5"), indicators.get("ma10"), 
        indicators.get("ma20"), indicators.get("ma60"),
        indicators.get("dif"), indicators.get("dea"), indicators.get("macd"),
        indicators.get("rsi6"), indicators.get("rsi12"), indicators.get("rsi24"),
        indicators.get("k"), indicators.get("d"), indicators.get("j"),
        indicators.get("boll_upper"), indicators.get("boll_middle"), indicators.get("boll_lower")
    ))
    conn.commit()
    conn.close()
    return True


def get_indicators(code: str, date: str = None) -> Optional[Dict]:
    """获取技术指标"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if date:
        cursor.execute("SELECT * FROM indicators WHERE code = ? AND date = ?", (code, date))
    else:
        cursor.execute("SELECT * FROM indicators WHERE code = ? ORDER BY date DESC LIMIT 1", (code,))
    
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ==================== 交易记录操作 ====================

def insert_trade(stock_code: str, stock_name: str, direction: str, 
                 price: float, quantity: int, trade_date: str,
                 reason: str = None, notes: str = None) -> int:
    """插入交易记录"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trades 
        (stock_code, stock_name, direction, price, quantity, trade_date, reason, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (stock_code, stock_name, direction, price, quantity, trade_date, reason, notes))
    conn.commit()
    trade_id = cursor.lastrowid
    conn.close()
    return trade_id


def get_trades(stock_code: str = None, limit: int = 100) -> List[Dict]:
    """获取交易记录"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if stock_code:
        cursor.execute("""
            SELECT * FROM trades 
            WHERE stock_code = ? 
            ORDER BY trade_date DESC LIMIT ?
        """, (stock_code, limit))
    else:
        cursor.execute("SELECT * FROM trades ORDER BY trade_date DESC LIMIT ?", (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_trade_stats() -> Dict:
    """获取交易统计"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 总交易次数
    cursor.execute("SELECT COUNT(*) FROM trades")
    total = cursor.fetchone()[0]
    
    # 盈利次数
    # 需要匹配买卖对计算盈亏，这里简化处理
    cursor.execute("""
        SELECT direction, COUNT(*) as cnt, AVG(price) as avg_price 
        FROM trades GROUP BY direction
    """)
    stats = cursor.fetchall()
    conn.close()
    
    result = {"total": total}
    for row in stats:
        result[row["direction"]] = row["cnt"]
    
    return result


# ==================== 资金流向操作 ====================

def insert_fund_flow(code: str, date: str, data: Dict) -> bool:
    """插入资金流向数据"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO fund_flow 
        (code, date, main_net_inflow, small_net_inflow, medium_net_inflow, 
         large_net_inflow, super_net_inflow, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        code, date,
        data.get("主力净流入"),
        data.get("小单净流入"),
        data.get("中单净流入"),
        data.get("大单净流入"),
        data.get("超大单净流入")
    ))
    conn.commit()
    conn.close()
    return True


def get_fund_flow_data(code: str, limit: int = 10) -> List[Dict]:
    """获取资金流向数据"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM fund_flow 
        WHERE code = ? 
        ORDER BY date DESC LIMIT ?
    """, (code, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ==================== 龙虎榜操作 ====================

def insert_lhb(code: str, name: str, date: str, data: Dict) -> bool:
    """插入龙虎榜数据"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO lhb_data 
        (code, name, date, reason, buy_amount, sell_amount, net_amount, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        code, name, date,
        data.get("上榜原因"),
        data.get("买入金额"),
        data.get("卖出金额"),
        data.get("净买入额")
    ))
    conn.commit()
    conn.close()
    return True


def get_lhb_data(code: str = None, limit: int = 10) -> List[Dict]:
    """获取龙虎榜数据"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if code:
        cursor.execute("""
            SELECT * FROM lhb_data 
            WHERE code = ? 
            ORDER BY date DESC LIMIT ?
        """, (code, limit))
    else:
        cursor.execute("""
            SELECT * FROM lhb_data 
            ORDER BY date DESC LIMIT ?
        """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ==================== 北向资金操作 ====================

def insert_north_money(date: str, data: Dict) -> bool:
    """插入北向资金数据"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO north_money 
        (date, hk_sh_inflow, hk_sz_inflow, total_inflow, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
    """, (
        date,
        data.get("沪股通流入"),
        data.get("深股通流入"),
        data.get("北向资金流入")
    ))
    conn.commit()
    conn.close()
    return True


def get_north_money(limit: int = 30) -> List[Dict]:
    """获取北向资金数据"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM north_money 
        ORDER BY date DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ==================== 新闻操作 ====================

def insert_news(code: str, title: str, content: str, pub_date: str, source: str = None) -> bool:
    """插入新闻数据"""
    # 处理空日期
    if not pub_date:
        from datetime import datetime
        pub_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 如果 content 为空，用 title 填充
    if not content:
        content = title
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO stock_news 
        (code, title, content, pub_date, source, created_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    """, (code, title[:500], content[:5000], pub_date[:50], source))
    conn.commit()
    conn.close()
    return True


def get_news(code: str = None, limit: int = 20) -> List[Dict]:
    """获取新闻数据"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if code:
        cursor.execute("""
            SELECT * FROM stock_news 
            WHERE code = ? 
            ORDER BY pub_date DESC LIMIT ?
        """, (code, limit))
    else:
        cursor.execute("""
            SELECT * FROM stock_news 
            ORDER BY pub_date DESC LIMIT ?
        """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ==================== 热点板块操作 ====================

def insert_hot_sector(sector_name: str, date: str, data: Dict) -> bool:
    """插入热点板块数据"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO hot_sectors 
        (sector_name, date, change_percent, inflow, outflow, net_inflow, created_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        sector_name, date,
        data.get("涨跌幅"),
        data.get("流入"),
        data.get("流出"),
        data.get("净流入")
    ))
    conn.commit()
    conn.close()
    return True


def get_hot_sectors(date: str = None, limit: int = 20) -> List[Dict]:
    """获取热点板块数据"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if date:
        cursor.execute("""
            SELECT * FROM hot_sectors 
            WHERE date = ? 
            ORDER BY change_percent DESC LIMIT ?
        """, (date, limit))
    else:
        cursor.execute("""
            SELECT * FROM hot_sectors 
            ORDER BY date DESC, change_percent DESC LIMIT ?
        """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ==================== 数据同步 ====================

def sync_stock_data(stock_code: str, days: int = 30) -> Dict[str, Any]:
    """同步股票数据到本地"""
    from money_get.data import get_stock_data, get_indicators
    
    result = {"code": stock_code, "kline": 0, "indicators": 0}
    
    # 同步K线
    kline_data = get_stock_data(stock_code, days=days)
    if "data" in kline_data:
        for item in kline_data["data"]:
            insert_kline(
                code=stock_code,
                date=item.get("日期"),
                open=item.get("开盘"),
                high=item.get("最高"),
                low=item.get("最低"),
                close=item.get("收盘"),
                volume=int(item.get("成交量", 0)),
                amount=item.get("成交额", 0)
            )
            result["kline"] += 1
    
    # 同步指标
    ind_data = get_indicators(stock_code, days=days)
    if "indicators" in ind_data:
        from datetime import datetime, timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 扁平化指标数据
        ind = ind_data["indicators"]
        flat_indicators = {}
        
        # MA
        if "ma" in ind:
            for k, v in ind["ma"].items():
                flat_indicators[k] = float(v) if v is not None else None
        
        # MACD
        if "macd" in ind:
            for k, v in ind["macd"].items():
                flat_indicators[k] = float(v) if v is not None else None
        
        # RSI
        if "rsi" in ind:
            for k, v in ind["rsi"].items():
                flat_indicators[k] = float(v) if v is not None else None
        
        # KDJ
        if "kdj" in ind:
            for k, v in ind["kdj"].items():
                flat_indicators[k] = float(v) if v is not None else None
        
        # BOLL
        if "boll" in ind:
            for k, v in ind["boll"].items():
                flat_indicators[k] = float(v) if v is not None else None
        
        insert_indicators(stock_code, today, flat_indicators)
        result["indicators"] = 1
    
    return result

-- 001: 初始化数据库
-- 创建迁移记录表
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 创建股票基本信息表
CREATE TABLE IF NOT EXISTS stocks (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT,
    market TEXT,
    list_date TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 创建 K线数据表
CREATE TABLE IF NOT EXISTS daily_kline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    amount REAL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(code, date)
);

CREATE INDEX IF NOT EXISTS idx_kline_code_date ON daily_kline(code, date);

-- 创建技术指标表
CREATE TABLE IF NOT EXISTS indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    date TEXT NOT NULL,
    ma5 REAL, ma10 REAL, ma20 REAL, ma60 REAL,
    dif REAL, dea REAL, macd REAL,
    rsi6 REAL, rsi12 REAL, rsi24 REAL,
    k REAL, d REAL, j REAL,
    boll_upper REAL, boll_middle REAL, boll_lower REAL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(code, date)
);

CREATE INDEX IF NOT EXISTS idx_indicators_code_date ON indicators(code, date);

-- 创建资金流向表
CREATE TABLE IF NOT EXISTS fund_flow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    date TEXT NOT NULL,
    main_net_inflow REAL,
    small_net_inflow REAL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(code, date)
);

CREATE INDEX IF NOT EXISTS idx_fund_flow_code_date ON fund_flow(code, date);

-- 创建交易记录表
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    stock_name TEXT,
    direction TEXT NOT NULL,  -- buy/sell
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    trade_date TEXT NOT NULL,
    reason TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_trades_code ON trades(stock_code);
CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(trade_date);

-- 记录迁移
INSERT INTO schema_migrations (version, applied_at) VALUES ('001_initial', datetime('now'));

-- 002: 添加资金流向和龙虎榜表
-- 资金流向表
CREATE TABLE IF NOT EXISTS fund_flow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    date TEXT NOT NULL,
    main_net_inflow REAL,
    small_net_inflow REAL,
    medium_net_inflow REAL,
    large_net_inflow REAL,
    super_net_inflow REAL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(code, date)
);

CREATE INDEX IF NOT EXISTS idx_fund_flow_code_date ON fund_flow(code, date);

-- 龙虎榜表
CREATE TABLE IF NOT EXISTS lhb_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    name TEXT,
    date TEXT NOT NULL,
    reason TEXT,
    buy_amount REAL,
    sell_amount REAL,
    net_amount REAL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(code, date)
);

CREATE INDEX IF NOT EXISTS idx_lhb_code_date ON lhb_data(code, date);

-- 北向资金表
CREATE TABLE IF NOT EXISTS north_money (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    hk_sh_inflow REAL,
    hk_sz_inflow REAL,
    total_inflow REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_north_money_date ON north_money(date);

-- 板块资金表
CREATE TABLE IF NOT EXISTS sector_fund (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_name TEXT NOT NULL,
    date TEXT NOT NULL,
    inflow REAL,
    outflow REAL,
    net_inflow REAL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(sector_name, date)
);

CREATE INDEX IF NOT EXISTS idx_sector_fund_date ON sector_fund(date);

-- 记录迁移
INSERT INTO schema_migrations (version, applied_at) VALUES ('002_add_fund_flow', datetime('now'));

-- 003: 添加新闻和板块表
-- 股票新闻表
CREATE TABLE IF NOT EXISTS stock_news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
    title TEXT,
    content TEXT,
    pub_date TEXT,
    source TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(code, title, pub_date)
);

CREATE INDEX IF NOT EXISTS idx_stock_news_code_date ON stock_news(code, pub_date);

-- 热点板块表
CREATE TABLE IF NOT EXISTS hot_sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_name TEXT NOT NULL,
    date TEXT NOT NULL,
    change_percent REAL,
    inflow REAL,
    outflow REAL,
    net_inflow REAL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(sector_name, date)
);

CREATE INDEX IF NOT EXISTS idx_hot_sectors_date ON hot_sectors(date);

-- 记录迁移
INSERT INTO schema_migrations (version, applied_at) VALUES ('003_add_news_sectors', datetime('now'));

-- 004: 添加记忆模块表
-- 公共记忆表
CREATE TABLE IF NOT EXISTS shared_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,          -- 'principles', 'patterns', 'cases'
    content TEXT NOT NULL,
    source TEXT,                    -- 来源：llm_analysis, user_input, system
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_shared_memory_category ON shared_memory(category);

-- 股票上下文表
CREATE TABLE IF NOT EXISTS stock_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    context_type TEXT NOT NULL,      -- 'summary', 'history', 'decision'
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_stock_context_code ON stock_context(stock_code);

-- 记录迁移
INSERT INTO schema_migrations (version, applied_at) VALUES ('004_add_memory', datetime('now'));

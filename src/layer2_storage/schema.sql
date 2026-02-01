-- ===================================================================
-- SQLite schema for EventHorizon DAG System
-- Layer 2: Storage & Indexing
-- ===================================================================

-- ===================================================================
-- PART 1: RAG METADATA TABLES (существующий код, НЕ ТРОГАТЬ)
-- ===================================================================

-- Events table: Store IngestedEvent metadata for RAG system
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    embedding_text TEXT NOT NULL,
    canonical_form TEXT NOT NULL, -- JSON string
    authority REAL NOT NULL,
    freshness TIMESTAMP NOT NULL,
    data_period_start TIMESTAMP,
    data_period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (authority >= 0 AND authority <= 1)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);
CREATE INDEX IF NOT EXISTS idx_events_freshness ON events(freshness DESC);
CREATE INDEX IF NOT EXISTS idx_events_authority ON events(authority DESC);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC);

-- Composite index for common queries (source + freshness)
CREATE INDEX IF NOT EXISTS idx_events_source_freshness
    ON events(source, freshness DESC);

-- Full-text search index for embedding_text (SQLite FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
    event_id UNINDEXED,
    embedding_text,
    content='events',
    content_rowid='rowid'
);

-- Trigger to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS events_ai AFTER INSERT ON events BEGIN
    INSERT INTO events_fts(rowid, event_id, embedding_text)
    VALUES (new.rowid, new.event_id, new.embedding_text);
END;

CREATE TRIGGER IF NOT EXISTS events_ad AFTER DELETE ON events BEGIN
    DELETE FROM events_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS events_au AFTER UPDATE ON events BEGIN
    DELETE FROM events_fts WHERE rowid = old.rowid;
    INSERT INTO events_fts(rowid, event_id, embedding_text)
    VALUES (new.rowid, new.event_id, new.embedding_text);
END;

-- Query statistics table (for monitoring)
CREATE TABLE IF NOT EXISTS query_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    result_count INTEGER,
    latency_ms REAL,
    cache_hit BOOLEAN DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_query_stats_timestamp
    ON query_stats(timestamp DESC);

-- ===================================================================
-- PART 2: TRADING DATA TABLES (НОВЫЙ КОД - расширение для логов бота)
-- ===================================================================

-- 1. Trading events: детальные логи бота (каждый цикл решения)
CREATE TABLE IF NOT EXISTS trading_events (
    event_id TEXT PRIMARY KEY,  -- формат: YYYYMMDD_cycle_unixtime
    session_id TEXT NOT NULL,   -- формат: YYYYMMDD
    timestamp DATETIME NOT NULL,
    cycle INTEGER,
    
    -- Рыночные данные
    price REAL,
    rsi REAL,
    trend_ltf TEXT,  -- FLAT/UPTREND/DOWNTREND
    trend_htf TEXT,  -- NEUTRAL/BULLISH/BEARISH
    trend_override TEXT,
    
    -- Состояние позиции
    lots INTEGER,
    pnl_pct REAL,
    position_pnl_pct REAL,
    
    -- Решение AI
    ai_signal TEXT,
    ai_confidence INTEGER,
    bias TEXT,
    action TEXT,  -- NOOP/BUY1/BUY3/SELL1/SELLALL/CLOSE_SHORT/etc.
    reason TEXT,
    
    -- Метаданные (v2 format)
    sleeping_market BOOLEAN DEFAULT 0,
    sleeping_reason TEXT,
    cooldown_active BOOLEAN DEFAULT 0,
    cooldown_remaining INTEGER DEFAULT 0,
    adaptive_sl_multiplier REAL,
    sl_level REAL,
    
    -- Дневные лимиты (v2)
    daily_trades_count INTEGER DEFAULT 0,
    daily_pnl_total REAL DEFAULT 0.0,
    daily_trades_remaining INTEGER,
    daily_limit_blocked BOOLEAN DEFAULT 0,
    
    -- Timing
    minutes_to_clearing INTEGER,
    holding_hours REAL,
    forced_entry BOOLEAN DEFAULT 0,
    consecutive_signals INTEGER DEFAULT 0,
    avg_confidence REAL DEFAULT 0.0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- 2. Sessions: торговые сессии (группировка по дням)
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,  -- формат: YYYYMMDD
    date DATE NOT NULL UNIQUE,
    
    first_timestamp DATETIME,
    last_timestamp DATETIME,
    
    total_cycles INTEGER DEFAULT 0,
    total_trades INTEGER DEFAULT 0,  -- count(action != 'NOOP')
    
    initial_lots INTEGER DEFAULT 0,
    final_lots INTEGER DEFAULT 0,
    
    initial_pnl_pct REAL DEFAULT 0.0,
    final_pnl_pct REAL DEFAULT 0.0,
    
    -- Метрики сессии
    max_drawdown_pct REAL,
    max_profit_pct REAL,
    sleeping_market_cycles INTEGER DEFAULT 0,
    cooldown_cycles INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Trades: отдельные сделки (восстановленные из action)
CREATE TABLE IF NOT EXISTS trades (
    trade_id TEXT PRIMARY KEY,  -- event_id родительского события
    event_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    
    timestamp DATETIME NOT NULL,
    action TEXT NOT NULL,  -- BUY1/BUY3/SELL1/SELLALL/CLOSE_SHORT/CLOSE_LONG
    
    lots_before INTEGER,
    lots_after INTEGER,
    lots_changed INTEGER,  -- +3 для BUY3, -1 для SELL1, etc.
    
    price_usd REAL,
    reason TEXT,
    signal TEXT,
    confidence INTEGER,
    
    -- Финансовые метрики (из логов бота - обычно NULL)
    realized_pnl_rub REAL,
    unrealized_pnl_rub REAL,
    fees_rub REAL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (event_id) REFERENCES trading_events(event_id),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- 4. Broker trades: импорт из PDF-отчёта (для reconciliation)
CREATE TABLE IF NOT EXISTS broker_trades (
    broker_trade_id TEXT PRIMARY KEY,  -- номер сделки из PDF
    
    trade_date DATE NOT NULL,
    trade_time TEXT,
    settlement_date DATE,
    
    exchange TEXT,  -- ММВБ
    type TEXT,  -- Покупка/Продажа
    contract TEXT,  -- NRF6/NRG6
    
    price_usd REAL,
    qty INTEGER,
    
    amount_rub REAL,
    commission_broker_rub REAL,
    commission_exchange_rub REAL,
    commission_clearing_rub REAL,
    
    status TEXT,  -- К (исполнено)
    
    -- Reconciliation метаданные
    matched_trade_id TEXT,  -- связь с trades.trade_id
    reconciled BOOLEAN DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (matched_trade_id) REFERENCES trades(trade_id)
);

-- 5. Daily PnL: агрегированная дневная статистика
CREATE TABLE IF NOT EXISTS daily_pnl (
    summary_id TEXT PRIMARY KEY,  -- формат: YYYYMMDD
    session_id TEXT NOT NULL UNIQUE,
    date DATE NOT NULL UNIQUE,
    
    -- Данные из PDF (вариационная маржа)
    var_margin_credit_rub REAL DEFAULT 0.0,
    var_margin_debit_rub REAL DEFAULT 0.0,
    var_margin_net_rub REAL DEFAULT 0.0,
    
    -- Комиссии из PDF
    total_commission_broker_rub REAL DEFAULT 0.0,
    total_commission_exchange_rub REAL DEFAULT 0.0,
    total_commission_clearing_rub REAL DEFAULT 0.0,
    total_commission_rub REAL DEFAULT 0.0,
    
    -- Финансовый результат
    net_pnl_rub REAL DEFAULT 0.0,  -- var_margin_net - total_commission
    
    -- Метрики торговли
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- ===================================================================
-- INDEXES для trading tables
-- ===================================================================

-- trading_events indexes
CREATE INDEX IF NOT EXISTS idx_trading_events_session ON trading_events(session_id);
CREATE INDEX IF NOT EXISTS idx_trading_events_timestamp ON trading_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trading_events_action ON trading_events(action);
CREATE INDEX IF NOT EXISTS idx_trading_events_sleeping ON trading_events(sleeping_market, timestamp DESC);

-- Composite index для распространённых запросов
CREATE INDEX IF NOT EXISTS idx_trading_events_session_timestamp 
    ON trading_events(session_id, timestamp DESC);

-- trades indexes
CREATE INDEX IF NOT EXISTS idx_trades_session ON trades(session_id);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_event ON trades(event_id);

-- broker_trades indexes
CREATE INDEX IF NOT EXISTS idx_broker_trades_date ON broker_trades(trade_date);
CREATE INDEX IF NOT EXISTS idx_broker_trades_reconciled ON broker_trades(reconciled, trade_date);

-- sessions indexes
CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date DESC);

-- daily_pnl indexes
CREATE INDEX IF NOT EXISTS idx_daily_pnl_date ON daily_pnl(date DESC);

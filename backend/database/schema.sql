CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    event_time TEXT NOT NULL,
    ingestion_time TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    entities TEXT NOT NULL DEFAULT '[]',
    narratives TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL,
    raw_payload TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS signal_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    direction TEXT NOT NULL,
    signal_strength REAL NOT NULL,
    trust_score REAL NOT NULL,
    manipulation_risk REAL NOT NULL,
    late_hype_risk REAL NOT NULL,
    contradiction_score REAL NOT NULL,
    catalyst_score REAL NOT NULL,
    data_quality_score REAL NOT NULL,
    explanation TEXT NOT NULL,
    what_could_go_wrong TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sentiment_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT,
    ticker TEXT,
    general_sentiment TEXT NOT NULL,
    market_stance TEXT NOT NULL,
    intent TEXT NOT NULL,
    sentiment_score REAL NOT NULL,
    confidence REAL NOT NULL,
    evidence_terms TEXT NOT NULL DEFAULT '[]',
    explanation TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(event_id) REFERENCES events(event_id)
);

CREATE TABLE IF NOT EXISTS market_bars (
    ticker TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL,
    source TEXT NOT NULL,
    ingestion_time TEXT NOT NULL,
    PRIMARY KEY (ticker, timestamp, source)
);

CREATE TABLE IF NOT EXISTS backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT,
    ticker TEXT NOT NULL,
    signal_timestamp TEXT NOT NULL,
    evaluated_at TEXT NOT NULL,
    return_1h REAL,
    return_1d REAL,
    return_3d REAL,
    return_7d REAL,
    spy_adjusted_return_1d REAL,
    qqq_adjusted_return_1d REAL,
    spy_adjusted_return_3d REAL,
    qqq_adjusted_return_3d REAL,
    max_drawdown REAL,
    notes TEXT NOT NULL
);

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

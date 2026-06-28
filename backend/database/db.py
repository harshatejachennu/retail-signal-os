from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from backend.processing.events import Event
from backend.processing.sentiment import SentimentResult


DEFAULT_DATABASE_PATH = Path("retail_signal.db")


def database_path_from_url(database_url: str | None = None) -> Path:
    url = database_url or os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE_PATH}")
    if not url.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// URLs are supported by the initial foundation")
    return Path(url.removeprefix("sqlite:///"))


def connect(database_url: str | None = None) -> sqlite3.Connection:
    path = database_path_from_url(database_url)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    connection.commit()


def insert_event(connection: sqlite3.Connection, event: Event) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO events (
            event_id,
            source,
            event_time,
            ingestion_time,
            raw_text,
            entities,
            narratives,
            confidence,
            raw_payload
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event.event_id,
            event.source,
            event.event_time.isoformat(),
            event.ingestion_time.isoformat(),
            event.raw_text,
            json.dumps(event.entities, sort_keys=True),
            json.dumps(event.narratives, sort_keys=True),
            event.confidence,
            json.dumps(event.raw_payload, sort_keys=True, default=str),
        ),
    )
    connection.commit()


def insert_events(connection: sqlite3.Connection, events: list[Event]) -> None:
    for event in events:
        insert_event(connection, event)


def fetch_events(connection: sqlite3.Connection, limit: int | None = None) -> list[Event]:
    query = "SELECT * FROM events ORDER BY ingestion_time DESC"
    params: tuple[int, ...] = ()
    if limit is not None:
        query += " LIMIT ?"
        params = (limit,)

    rows = connection.execute(query, params).fetchall()
    return [
        Event(
            event_id=row["event_id"],
            source=row["source"],
            event_time=row["event_time"],
            ingestion_time=row["ingestion_time"],
            raw_text=row["raw_text"],
            entities=json.loads(row["entities"]),
            narratives=json.loads(row["narratives"]),
            confidence=row["confidence"],
            raw_payload=json.loads(row["raw_payload"]),
        )
        for row in rows
    ]


def insert_sentiment_result(
    connection: sqlite3.Connection,
    sentiment: SentimentResult,
    event_id: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO sentiment_results (
            event_id,
            ticker,
            general_sentiment,
            market_stance,
            intent,
            sentiment_score,
            confidence,
            evidence_terms,
            explanation,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            event_id,
            sentiment.ticker,
            sentiment.general_sentiment,
            sentiment.market_stance,
            sentiment.intent,
            sentiment.sentiment_score,
            sentiment.confidence,
            json.dumps(sentiment.evidence_terms, sort_keys=True),
            sentiment.explanation,
        ),
    )
    connection.commit()

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from backend.api.routes import live_signals, signal_for_ticker
from backend.database.db import connect, initialize, insert_events
from backend.processing.events import Event


def test_live_signals_returns_valid_signal_cards(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")

    payload = live_signals()

    assert payload
    assert {"ticker", "direction", "signal_strength", "trust_score"} <= set(payload[0])


def test_signal_ticker_handles_known_and_unknown_tickers(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'api_known.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    connection = connect(database_url)
    initialize(connection)
    insert_events(
        connection,
        [
            Event(
                event_id="api-tsla-1",
                source="reddit",
                event_time=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                ingestion_time=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
                raw_text="$TSLA buying calls after breakout.",
                confidence=0.8,
            )
        ],
    )
    connection.close()

    known = signal_for_ticker("TSLA")

    assert known["ticker"] == "TSLA"
    with pytest.raises(HTTPException) as exc_info:
        signal_for_ticker("XXXX")
    assert exc_info.value.status_code == 404

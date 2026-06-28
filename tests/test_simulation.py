from __future__ import annotations

from datetime import datetime, timezone

from backend.database.db import clear_demo_data, connect, fetch_events, initialize, insert_event
from backend.ml.dataset import build_ml_dataset
from backend.models.backtester import backtest_signal_cards_from_database
from backend.models.signal_engine import generate_signal_cards_from_database
from backend.processing.events import Event
from backend.research.dataset import assemble_research_dataset
from backend.simulation.replay import replay_synthetic_events
from backend.simulation.synthetic_history import (
    generate_synthetic_history,
    synthetic_status,
    write_synthetic_history,
)


def test_synthetic_generator_is_deterministic() -> None:
    first = generate_synthetic_history(days=30, signals=20)
    second = generate_synthetic_history(days=30, signals=20)

    assert first.events == second.events
    assert first.filings == second.filings
    assert first.market_bars == second.market_bars


def test_synthetic_generator_creates_enough_rows_and_multiple_tickers() -> None:
    history = generate_synthetic_history(days=60, signals=80)

    assert len(history.events) == 80
    assert len({event.raw_payload["scenario"] for event in history.events}) >= 8
    assert len({event.raw_text.split()[0].strip("$") for event in history.events}) > 3
    assert {event.source for event in history.events} == {"synthetic_reddit"}
    assert {bar.source for bar in history.market_bars} == {"synthetic_market"}
    assert {filing.source for filing in history.filings} == {"synthetic_sec"}


def test_clear_demo_data_preserves_non_synthetic_rows(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'safety.db'}"
    connection = connect(database_url)
    initialize(connection)
    insert_event(
        connection,
        Event(
            event_id="real-1",
            source="reddit",
            event_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ingestion_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            raw_text="$AAPL real row",
            confidence=0.8,
        ),
    )
    write_synthetic_history(generate_synthetic_history(days=10, signals=10), reset_demo_data=False, database_url=database_url)

    clear_demo_data(connection)
    remaining = fetch_events(connection)

    assert {event.event_id for event in remaining} == {"real-1"}
    connection.close()


def test_synthetic_history_supports_research_and_ml_targets(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'synthetic.db'}"
    write_synthetic_history(generate_synthetic_history(days=60, signals=70), reset_demo_data=True, database_url=database_url)
    cards = generate_signal_cards_from_database(database_url)
    backtest_signal_cards_from_database(database_url)
    research_rows = assemble_research_dataset(cards=cards, database_url=database_url)
    dataset = build_ml_dataset(research_rows=research_rows)

    assert len(cards) >= 60
    assert len(research_rows) >= 60
    assert dataset.target_distribution["positive_return_3d"][0] > 0
    assert dataset.target_distribution["positive_return_3d"][1] > 0


def test_replay_processes_events_chronologically_and_respects_ingestion_time(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'replay.db'}"
    write_synthetic_history(generate_synthetic_history(days=12, signals=12), reset_demo_data=True, database_url=database_url)

    result = replay_synthetic_events(database_url=database_url)

    assert result["status"] == "ok"
    assert result["events_replayed"] == 12
    counts = [batch["events_available"] for batch in result["batches"]]
    assert counts == sorted(counts)
    assert all("max_ingestion_time" in batch for batch in result["batches"])


def test_replay_handles_empty_dataset(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'empty_replay.db'}"
    connection = connect(database_url)
    initialize(connection)
    connection.close()

    result = replay_synthetic_events(database_url=database_url)

    assert result["status"] == "empty"


def test_simulation_status_returns_valid_structure(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'status.db'}"
    write_synthetic_history(generate_synthetic_history(days=10, signals=10), reset_demo_data=True, database_url=database_url)

    status = synthetic_status(database_url)

    assert status["synthetic"] is True
    assert status["synthetic_events"] == 10
    assert "target_distribution" in status

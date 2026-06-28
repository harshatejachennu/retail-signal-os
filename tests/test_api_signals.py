from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from backend.api.routes import (
    agents_health_endpoint,
    live_signals,
    ml_feature_importance,
    ml_summary,
    research_backtest_summary,
    research_event_study,
    research_granger_ticker,
    research_sec_filings,
    research_validation_summary,
    signal_backtest,
    signal_catalysts,
    signal_explanation,
    signal_for_ticker,
    signal_explanation_history,
    signal_ml_score,
    simulation_status,
)
from backend.database.db import connect, initialize, insert_events, insert_sec_filings
from backend.ingestion.sec_provider import MockSECProvider
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


def test_backtest_summary_returns_valid_structure(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'summary.db'}")

    summary = research_backtest_summary()

    assert {
        "signals_evaluated",
        "average_return_1d",
        "average_return_3d",
        "average_spy_adjusted_return_3d",
        "average_qqq_adjusted_return_3d",
        "win_rate_1d",
        "win_rate_3d",
    } <= set(summary)


def test_ticker_backtest_endpoint_handles_missing_data(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'missing_backtest.db'}")

    with pytest.raises(HTTPException) as exc_info:
        signal_backtest("TSLA")

    assert exc_info.value.status_code == 404


def test_research_sec_filings_returns_valid_structure(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'sec_api.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    connection = connect(database_url)
    initialize(connection)
    insert_sec_filings(
        connection,
        MockSECProvider().fetch_filings(
            ["AAPL"],
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 31, tzinfo=timezone.utc),
        ),
    )
    connection.close()

    payload = research_sec_filings()

    assert payload
    assert {"ticker", "form_type", "filed_at", "title", "summary"} <= set(payload[0])


def test_signal_catalysts_handles_known_and_unknown_tickers(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'catalyst_api.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    connection = connect(database_url)
    initialize(connection)
    insert_sec_filings(
        connection,
        MockSECProvider().fetch_filings(
            ["TSLA"],
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 31, tzinfo=timezone.utc),
        ),
    )
    connection.close()

    known = signal_catalysts("TSLA")

    assert known["ticker"] == "TSLA"
    assert "catalyst_score" in known
    with pytest.raises(HTTPException) as exc_info:
        signal_catalysts("XXXX")
    assert exc_info.value.status_code == 404


def test_research_validation_summary_returns_valid_structure(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'validation.db'}")

    summary = research_validation_summary()

    assert {
        "dataset_rows",
        "granger_summary",
        "lead_lag_summary",
        "event_study_summary",
        "negative_control_summary",
        "ablation_summary",
        "warnings",
    } <= set(summary)


def test_research_granger_ticker_handles_insufficient_data(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'granger.db'}")

    payload = research_granger_ticker("AMD")

    assert payload["ticker"] == "AMD"
    assert payload["results"]
    assert payload["results"][0]["interpretation"] == "insufficient_data"


def test_research_event_study_returns_valid_structure(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'event_study.db'}")

    payload = research_event_study()

    assert {"signals_evaluated", "average_post_event_return", "notes"} <= set(payload)


def test_ml_summary_returns_valid_structure(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ml_summary.db'}")

    payload = ml_summary()

    assert {"dataset_rows", "target_availability", "model_statuses", "latest_metrics", "warnings"} <= set(payload)


def test_ml_feature_importance_handles_missing_data(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ml_importance.db'}")

    payload = ml_feature_importance()

    assert payload["status"] in {"ok", "insufficient_data"}


def test_signal_ml_score_handles_insufficient_data(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ml_score.db'}")

    payload = signal_ml_score("AMD")

    assert payload["status"] == "insufficient_data"
    assert payload["ml_score_available"] is False


def test_agents_health_endpoint_returns_valid_structure() -> None:
    payload = agents_health_endpoint()

    assert payload["status"] == "ok"
    assert "BullAgent" in payload["agents"]


def test_signal_explanation_handles_unknown_ticker(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'explain_unknown.db'}")

    payload = signal_explanation("XXXX")

    assert payload["status"] == "insufficient_data"
    assert payload["ticker"] == "XXXX"


def test_signal_explanation_handles_known_ticker(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'explain_known.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    connection = connect(database_url)
    initialize(connection)
    insert_events(
        connection,
        [
            Event(
                event_id="explain-nvda-1",
                source="reddit",
                event_time=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                ingestion_time=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
                raw_text="NVDA bullish growth and strong demand.",
                confidence=0.8,
            )
        ],
    )
    connection.close()

    payload = signal_explanation("NVDA")

    assert payload["ticker"] == "NVDA"
    assert payload["not_financial_advice"]


def test_signal_explanation_history_returns_latest_note(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'explain_history.db'}")

    payload = signal_explanation_history("XXXX")

    assert payload["status"] == "insufficient_data"


def test_simulation_status_endpoint_returns_valid_structure(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'simulation_status.db'}")

    payload = simulation_status()

    assert {"synthetic_events", "signal_count", "research_dataset_rows", "ml_dataset_rows"} <= set(payload)

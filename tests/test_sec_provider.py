from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.database.db import (
    connect,
    fetch_sec_filings_for_ticker,
    fetch_sec_filings_near_time,
    initialize,
    insert_sec_filings,
)
from backend.ingestion.sec_provider import MockSECProvider, RealSECProvider, SECProviderError, ticker_to_cik


def test_mock_sec_provider_works_without_network() -> None:
    filings = MockSECProvider().fetch_filings(
        ["AAPL", "TSLA"],
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 31, tzinfo=timezone.utc),
    )

    assert filings
    assert {filing.source for filing in filings} == {"mock_sec"}
    assert {filing.ticker for filing in filings} == {"AAPL", "TSLA"}


def test_mock_sec_provider_generates_deterministic_filings() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 31, tzinfo=timezone.utc)

    first = MockSECProvider().fetch_filings(["NVDA"], start, end)
    second = MockSECProvider().fetch_filings(["NVDA"], start, end)

    assert first == second


def test_sec_filings_store_and_fetch_by_ticker(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'sec.db'}"
    connection = connect(database_url)
    initialize(connection)
    filings = MockSECProvider().fetch_filings(
        ["AAPL"],
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 31, tzinfo=timezone.utc),
    )

    insert_sec_filings(connection, filings)
    stored = fetch_sec_filings_for_ticker(connection, "AAPL")

    assert len(stored) == len(filings)
    assert all(filing.ticker == "AAPL" for filing in stored)
    connection.close()


def test_fetch_sec_filings_near_timestamp(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'near.db'}"
    connection = connect(database_url)
    initialize(connection)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    filings = MockSECProvider().fetch_filings(["TSLA"], start, start + timedelta(days=10))
    insert_sec_filings(connection, filings)

    nearby = fetch_sec_filings_near_time(connection, "TSLA", filings[0].filed_at, days_before=1, days_after=1)

    assert nearby
    assert nearby[0].ticker == "TSLA"
    connection.close()


def test_real_sec_mode_requires_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)

    with pytest.raises(SECProviderError, match="SEC_USER_AGENT"):
        RealSECProvider()


def test_ticker_to_cik_common_and_unknown() -> None:
    assert ticker_to_cik("AAPL") == "0000320193"
    assert ticker_to_cik("TSLA") == "0001318605"
    assert ticker_to_cik("UNKNOWN") is None

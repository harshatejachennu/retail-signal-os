from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.database.db import connect, fetch_market_bars, initialize, insert_market_bars
from backend.ingestion.market_data_provider import MockMarketDataProvider


def test_mock_provider_generates_deterministic_bars() -> None:
    provider = MockMarketDataProvider()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=2)

    first = provider.fetch_bars(["AAPL", "SPY"], start, end)
    second = provider.fetch_bars(["AAPL", "SPY"], start, end)

    assert first == second
    assert len(first) == 6


def test_market_bars_insert_fetch_works(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'market.db'}"
    connection = connect(database_url)
    initialize(connection)
    bars = MockMarketDataProvider().fetch_bars(
        ["TSLA"],
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 2, tzinfo=timezone.utc),
    )

    insert_market_bars(connection, bars)
    stored = fetch_market_bars(connection, "TSLA")

    assert stored == bars
    connection.close()


def test_spy_and_qqq_bars_are_supported() -> None:
    bars = MockMarketDataProvider().fetch_bars(
        ["SPY", "QQQ"],
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert {bar.ticker for bar in bars} == {"SPY", "QQQ"}

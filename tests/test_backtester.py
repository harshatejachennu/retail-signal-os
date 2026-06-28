from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.models.backtester import backtest_signal_card
from backend.models.market_data import MarketBar
from backend.models.signal_card import SignalCard


def bar(ticker: str, timestamp: datetime, close: float) -> MarketBar:
    return MarketBar(
        ticker=ticker,
        timestamp=timestamp,
        open=close,
        high=close + 1,
        low=max(close - 1, 0.01),
        close=close,
        volume=1000,
        source="test",
    )


def card(timestamp: datetime) -> SignalCard:
    return SignalCard(
        ticker="TSLA",
        timestamp=timestamp,
        direction="bullish",
        signal_strength=50,
        trust_score=50,
        manipulation_risk=10,
        late_hype_risk=10,
        contradiction_score=0,
        catalyst_score=0,
        data_quality_score=70,
        explanation="test",
        what_could_go_wrong="test",
    )


def test_calculates_simple_forward_return_correctly() -> None:
    timestamp = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    result = backtest_signal_card(
        card(timestamp),
        [
            bar("TSLA", timestamp + timedelta(hours=1), 100),
            bar("TSLA", timestamp + timedelta(days=1), 110),
        ],
    )

    assert result.return_1d == 0.1


def test_calculates_benchmark_adjusted_return_correctly() -> None:
    timestamp = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    result = backtest_signal_card(
        card(timestamp),
        [
            bar("TSLA", timestamp + timedelta(hours=1), 100),
            bar("TSLA", timestamp + timedelta(days=3), 120),
        ],
        spy_bars=[
            bar("SPY", timestamp + timedelta(hours=1), 100),
            bar("SPY", timestamp + timedelta(days=3), 105),
        ],
        qqq_bars=[
            bar("QQQ", timestamp + timedelta(hours=1), 100),
            bar("QQQ", timestamp + timedelta(days=3), 110),
        ],
    )

    assert result.spy_adjusted_return_3d == 0.15
    assert result.qqq_adjusted_return_3d == 0.1


def test_returns_none_when_bars_are_missing() -> None:
    timestamp = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    result = backtest_signal_card(card(timestamp), [])

    assert result.return_1d is None
    assert result.max_drawdown is None


def test_does_not_use_bars_before_signal_timestamp() -> None:
    timestamp = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    result = backtest_signal_card(
        card(timestamp),
        [
            bar("TSLA", timestamp - timedelta(days=1), 1),
            bar("TSLA", timestamp + timedelta(hours=1), 100),
            bar("TSLA", timestamp + timedelta(days=1), 110),
        ],
    )

    assert result.return_1d == 0.1


def test_max_drawdown_calculation_works() -> None:
    timestamp = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    result = backtest_signal_card(
        card(timestamp),
        [
            bar("TSLA", timestamp + timedelta(hours=1), 100),
            bar("TSLA", timestamp + timedelta(hours=2), 120),
            bar("TSLA", timestamp + timedelta(hours=3), 90),
        ],
    )

    assert result.max_drawdown == -0.25

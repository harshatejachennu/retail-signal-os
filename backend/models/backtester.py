from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from statistics import fmean

from pydantic import BaseModel

from backend.database.db import (
    connect,
    fetch_events,
    fetch_market_bars_after_timestamp,
    initialize,
    insert_backtest_results,
)
from backend.models.market_data import MarketBar
from backend.models.signal_card import SignalCard
from backend.processing.pipeline import generate_signal_cards_from_events


class BacktestResult(BaseModel):
    signal_id: str | None = None
    ticker: str
    signal_timestamp: datetime
    evaluated_at: datetime
    return_1h: float | None = None
    return_1d: float | None = None
    return_3d: float | None = None
    return_7d: float | None = None
    spy_adjusted_return_1d: float | None = None
    qqq_adjusted_return_1d: float | None = None
    spy_adjusted_return_3d: float | None = None
    qqq_adjusted_return_3d: float | None = None
    max_drawdown: float | None = None
    notes: str


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _first_bar_at_or_after(bars: list[MarketBar], timestamp: datetime) -> MarketBar | None:
    timestamp = _as_utc(timestamp)
    for bar in sorted(bars, key=lambda item: item.timestamp):
        if _as_utc(bar.timestamp) >= timestamp:
            return bar
    return None


def _forward_return(bars: list[MarketBar], signal_timestamp: datetime, horizon: timedelta) -> float | None:
    future_bars = [bar for bar in bars if _as_utc(bar.timestamp) > _as_utc(signal_timestamp)]
    if not future_bars:
        return None
    entry = future_bars[0]
    exit_bar = _first_bar_at_or_after(future_bars, _as_utc(signal_timestamp) + horizon)
    if exit_bar is None:
        return None
    return round((exit_bar.close - entry.close) / entry.close, 6)


def _max_drawdown_after_signal(bars: list[MarketBar], signal_timestamp: datetime) -> float | None:
    future_bars = sorted(
        [bar for bar in bars if _as_utc(bar.timestamp) > _as_utc(signal_timestamp)],
        key=lambda item: item.timestamp,
    )
    if not future_bars:
        return None
    running_peak = future_bars[0].close
    max_drawdown = 0.0
    for bar in future_bars:
        running_peak = max(running_peak, bar.close)
        drawdown = (bar.close - running_peak) / running_peak
        max_drawdown = min(max_drawdown, drawdown)
    return round(max_drawdown, 6)


def _adjusted(signal_return: float | None, benchmark_return: float | None) -> float | None:
    if signal_return is None or benchmark_return is None:
        return None
    return round(signal_return - benchmark_return, 6)


def backtest_signal_card(
    card: SignalCard,
    ticker_bars: list[MarketBar],
    spy_bars: list[MarketBar] | None = None,
    qqq_bars: list[MarketBar] | None = None,
) -> BacktestResult:
    spy_bars = spy_bars or []
    qqq_bars = qqq_bars or []
    return_1h = _forward_return(ticker_bars, card.timestamp, timedelta(hours=1))
    return_1d = _forward_return(ticker_bars, card.timestamp, timedelta(days=1))
    return_3d = _forward_return(ticker_bars, card.timestamp, timedelta(days=3))
    return_7d = _forward_return(ticker_bars, card.timestamp, timedelta(days=7))
    spy_return_1d = _forward_return(spy_bars, card.timestamp, timedelta(days=1))
    qqq_return_1d = _forward_return(qqq_bars, card.timestamp, timedelta(days=1))
    spy_return_3d = _forward_return(spy_bars, card.timestamp, timedelta(days=3))
    qqq_return_3d = _forward_return(qqq_bars, card.timestamp, timedelta(days=3))

    notes = []
    if not ticker_bars:
        notes.append("No market bars available for ticker.")
    if return_1d is None and return_3d is None:
        notes.append("Insufficient future bars after signal timestamp.")
    if not spy_bars or not qqq_bars:
        notes.append("Benchmark bars missing for SPY or QQQ.")
    notes.append("Educational backtest only; no trading advice.")

    return BacktestResult(
        signal_id=f"{card.ticker}:{card.timestamp.isoformat()}",
        ticker=card.ticker,
        signal_timestamp=card.timestamp,
        evaluated_at=datetime.now(timezone.utc),
        return_1h=return_1h,
        return_1d=return_1d,
        return_3d=return_3d,
        return_7d=return_7d,
        spy_adjusted_return_1d=_adjusted(return_1d, spy_return_1d),
        qqq_adjusted_return_1d=_adjusted(return_1d, qqq_return_1d),
        spy_adjusted_return_3d=_adjusted(return_3d, spy_return_3d),
        qqq_adjusted_return_3d=_adjusted(return_3d, qqq_return_3d),
        max_drawdown=_max_drawdown_after_signal(ticker_bars, card.timestamp),
        notes=" ".join(notes),
    )


def attach_backtest_to_card(card: SignalCard, result: BacktestResult | None) -> SignalCard:
    if result is None:
        return card
    update = card.model_dump()
    update.update(
        {
            "backtest_available": result.return_1d is not None or result.return_3d is not None,
            "return_1d": result.return_1d,
            "return_3d": result.return_3d,
            "spy_adjusted_return_3d": result.spy_adjusted_return_3d,
            "qqq_adjusted_return_3d": result.qqq_adjusted_return_3d,
            "backtest_notes": result.notes,
        }
    )
    return SignalCard(**update)


def backtest_signal_cards_from_database(database_url: str | None = None) -> list[BacktestResult]:
    connection = connect(database_url)
    initialize(connection)
    try:
        cards = generate_signal_cards_from_events(fetch_events(connection))
        spy_bars_by_card = {}
        qqq_bars_by_card = {}
        results: list[BacktestResult] = []
        for card in cards:
            ticker_bars = fetch_market_bars_after_timestamp(connection, card.ticker, card.timestamp)
            spy_bars = spy_bars_by_card.setdefault(
                card.timestamp.isoformat(),
                fetch_market_bars_after_timestamp(connection, "SPY", card.timestamp),
            )
            qqq_bars = qqq_bars_by_card.setdefault(
                card.timestamp.isoformat(),
                fetch_market_bars_after_timestamp(connection, "QQQ", card.timestamp),
            )
            results.append(backtest_signal_card(card, ticker_bars, spy_bars, qqq_bars))
        if results:
            insert_backtest_results(connection, results)
        return results
    finally:
        connection.close()


def backtest_summary(results: list[BacktestResult]) -> dict[str, float | int | None]:
    def average(values: list[float | None]) -> float | None:
        available = [value for value in values if value is not None]
        return round(fmean(available), 6) if available else None

    def win_rate(values: list[float | None]) -> float | None:
        available = [value for value in values if value is not None]
        return round(sum(1 for value in available if value > 0) / len(available), 3) if available else None

    return {
        "signals_evaluated": len(results),
        "average_return_1d": average([result.return_1d for result in results]),
        "average_return_3d": average([result.return_3d for result in results]),
        "average_spy_adjusted_return_3d": average([result.spy_adjusted_return_3d for result in results]),
        "average_qqq_adjusted_return_3d": average([result.qqq_adjusted_return_3d for result in results]),
        "win_rate_1d": win_rate([result.return_1d for result in results]),
        "win_rate_3d": win_rate([result.return_3d for result in results]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest generated Signal Cards against stored OHLCV bars.")
    parser.parse_args()
    results = backtest_signal_cards_from_database()
    summary = backtest_summary(results)
    print(f"signals evaluated: {summary['signals_evaluated']}")
    print(f"average return 1d: {summary['average_return_1d']}")
    print(f"average return 3d: {summary['average_return_3d']}")
    print(f"average SPY-adjusted return 3d: {summary['average_spy_adjusted_return_3d']}")
    print(f"average QQQ-adjusted return 3d: {summary['average_qqq_adjusted_return_3d']}")
    print(f"win rate 1d: {summary['win_rate_1d']}")
    print(f"win rate 3d: {summary['win_rate_3d']}")


if __name__ == "__main__":
    main()

from __future__ import annotations

from datetime import timedelta

from backend.database.db import connect, fetch_events, fetch_market_bars, initialize
from backend.models.market_data import MarketBar
from backend.models.signal_card import SignalCard
from backend.models.signal_engine import get_live_signal_cards
from backend.research.results import EventStudyResult
from backend.research.stats import average


def run_event_study(
    cards: list[SignalCard] | None = None,
    bars_by_ticker: dict[str, list[MarketBar]] | None = None,
    database_url: str | None = None,
) -> EventStudyResult:
    cards = cards if cards is not None else get_live_signal_cards(database_url)
    bars_by_ticker = bars_by_ticker if bars_by_ticker is not None else _load_bars(cards, database_url)
    pre_returns: list[float | None] = []
    post_returns: list[float | None] = []
    spy_abnormal: list[float | None] = []
    qqq_abnormal: list[float | None] = []

    for card in cards:
        ticker_bars = bars_by_ticker.get(card.ticker, [])
        pre = _window_return(ticker_bars, card.timestamp - timedelta(days=1), card.timestamp)
        post = _window_return(ticker_bars, card.timestamp, card.timestamp + timedelta(days=1))
        pre_returns.append(pre)
        post_returns.append(post)
        spy_post = _window_return(bars_by_ticker.get("SPY", []), card.timestamp, card.timestamp + timedelta(days=1))
        qqq_post = _window_return(bars_by_ticker.get("QQQ", []), card.timestamp, card.timestamp + timedelta(days=1))
        spy_abnormal.append(post - spy_post if post is not None and spy_post is not None else None)
        qqq_abnormal.append(post - qqq_post if post is not None and qqq_post is not None else None)

    return EventStudyResult(
        signals_evaluated=len(cards),
        average_pre_event_return=average(pre_returns),
        average_post_event_return=average(post_returns),
        average_abnormal_return_vs_spy=average(spy_abnormal),
        average_abnormal_return_vs_qqq=average(qqq_abnormal),
        notes="Simple event study using stored bars around Signal Card timestamps; no causal claim is made.",
    )


def _load_bars(cards: list[SignalCard], database_url: str | None) -> dict[str, list[MarketBar]]:
    tickers = {card.ticker for card in cards} | {"SPY", "QQQ"}
    connection = connect(database_url)
    initialize(connection)
    try:
        return {ticker: fetch_market_bars(connection, ticker) for ticker in tickers}
    finally:
        connection.close()


def _window_return(bars: list[MarketBar], start, end) -> float | None:
    ordered = sorted([bar for bar in bars if start <= bar.timestamp <= end], key=lambda bar: bar.timestamp)
    if len(ordered) < 2:
        return None
    return round((ordered[-1].close - ordered[0].close) / ordered[0].close, 6)

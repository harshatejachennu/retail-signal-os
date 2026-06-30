from __future__ import annotations

from typing import Any

from backend.models.backtester import BacktestResult, backtest_signal_cards_from_database
from backend.models.signal_card import SignalCard
from backend.models.signal_engine import get_live_signal_cards


FEATURE_COLUMNS = [
    "signal_strength",
    "trust_score",
    "manipulation_risk",
    "late_hype_risk",
    "contradiction_score",
    "catalyst_score",
    "data_quality_score",
    "sentiment_score",
    "bullish_ratio",
    "bearish_ratio",
    "mention_count",
    "source_event_count",
]

TARGET_COLUMNS = [
    "return_1d",
    "return_3d",
    "spy_adjusted_return_1d",
    "spy_adjusted_return_3d",
    "qqq_adjusted_return_1d",
    "qqq_adjusted_return_3d",
]


def assemble_research_dataset(
    cards: list[SignalCard] | None = None,
    backtest_results: list[BacktestResult] | None = None,
    database_url: str | None = None,
) -> list[dict[str, Any]]:
    cards = cards if cards is not None else get_live_signal_cards(database_url)
    backtest_results = (
        backtest_results
        if backtest_results is not None
        else backtest_signal_cards_from_database(database_url, persist_results=False)
    )
    backtests_by_key = {
        (result.ticker, result.signal_timestamp.isoformat()): result for result in backtest_results
    }

    rows: list[dict[str, Any]] = []
    for card in cards:
        result = backtests_by_key.get((card.ticker, card.timestamp.isoformat()))
        row = {
            "ticker": card.ticker,
            "signal_timestamp": card.timestamp,
            "direction": card.direction,
            "signal_strength": card.signal_strength,
            "trust_score": card.trust_score,
            "manipulation_risk": card.manipulation_risk,
            "late_hype_risk": card.late_hype_risk,
            "contradiction_score": card.contradiction_score,
            "catalyst_score": card.catalyst_score,
            "data_quality_score": card.data_quality_score,
            "sentiment_score": getattr(card, "sentiment_score", None),
            "bullish_ratio": getattr(card, "bullish_ratio", None),
            "bearish_ratio": getattr(card, "bearish_ratio", None),
            "mention_count": getattr(card, "mention_count", None),
            "source_event_count": getattr(card, "source_event_count", None),
            "return_1d": result.return_1d if result else card.return_1d,
            "return_3d": result.return_3d if result else card.return_3d,
            "spy_adjusted_return_1d": result.spy_adjusted_return_1d if result else None,
            "spy_adjusted_return_3d": result.spy_adjusted_return_3d if result else card.spy_adjusted_return_3d,
            "qqq_adjusted_return_1d": result.qqq_adjusted_return_1d if result else None,
            "qqq_adjusted_return_3d": result.qqq_adjusted_return_3d if result else card.qqq_adjusted_return_3d,
        }
        rows.append(row)

    return sorted(rows, key=lambda item: (item["signal_timestamp"], item["ticker"]))

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from backend.database.db import (
    connect,
    fetch_events,
    fetch_market_bars_after_timestamp,
    fetch_sec_filings_near_time,
    initialize,
)
from backend.features.catalyst import attach_catalyst_to_card, score_catalysts_for_signal
from backend.models.backtester import attach_backtest_to_card, backtest_signal_card
from backend.models.signal_card import SignalCard
from backend.processing.manipulation import score_manipulation_risk
from backend.processing.pipeline import generate_signal_cards_from_events
from backend.processing.sentiment import score_sentiment


def create_signal_card_from_text(ticker: str, text: str, timestamp: datetime | None = None) -> SignalCard:
    sentiment = score_sentiment(text)
    manipulation_risk = score_manipulation_risk(text)
    data_quality_score = 0.72 if text.strip() else 0.2
    signal_strength = min(abs(sentiment.sentiment_score) * 50 + 25, 100.0)
    trust_score = max(0.0, min(data_quality_score * 100 - manipulation_risk.risk_score * 0.35, 100.0))
    direction = "uncertain" if sentiment.market_stance == "unclear" else sentiment.market_stance

    return SignalCard(
        ticker=ticker.upper(),
        timestamp=timestamp or datetime.now(timezone.utc),
        direction=direction,
        signal_strength=signal_strength,
        trust_score=trust_score,
        manipulation_risk=manipulation_risk.risk_score,
        late_hype_risk=35.0,
        contradiction_score=20.0,
        catalyst_score=0.0,
        data_quality_score=data_quality_score * 100,
        sentiment_label=sentiment.general_sentiment,
        market_stance=sentiment.market_stance,
        intent=sentiment.intent,
        manipulation_risk_level=manipulation_risk.risk_level,
        manipulation_risk_reasons=manipulation_risk.reasons,
        explanation=(
            f"{ticker.upper()} placeholder Signal Card generated from deterministic text features: "
            f"stance={sentiment.market_stance}, sentiment={sentiment.sentiment_score:.2f}, "
            f"intent={sentiment.intent}, manipulation_risk={manipulation_risk.risk_level}."
        ),
        what_could_go_wrong=(
            "This is a research signal from limited text evidence. Price action may already reflect the "
            "narrative, source quality may be weak, and no causal relationship has been validated yet."
        ),
    )


def create_sample_signal_cards() -> list[SignalCard]:
    sample_time = datetime(2026, 1, 1, 14, 30, tzinfo=timezone.utc)
    return [
        create_signal_card_from_text(
            "NVDA",
            "NVDA bullish growth discussion with strong demand but no validated catalyst yet.",
            sample_time,
        ),
        create_signal_card_from_text(
            "TSLA",
            "$TSLA moon rocket squeeze!!!",
            sample_time,
        ),
    ]


def generate_signal_cards_from_database(database_url: str | None = None) -> list[SignalCard]:
    connection = connect(database_url)
    initialize(connection)
    try:
        events = fetch_events(connection)
        cards = generate_signal_cards_from_events(events)
        enriched: list[SignalCard] = []
        for card in cards:
            catalyst = score_catalysts_for_signal(
                card,
                fetch_sec_filings_near_time(connection, card.ticker, card.timestamp),
            )
            card = attach_catalyst_to_card(card, catalyst)
            result = backtest_signal_card(
                card,
                fetch_market_bars_after_timestamp(connection, card.ticker, card.timestamp),
                fetch_market_bars_after_timestamp(connection, "SPY", card.timestamp),
                fetch_market_bars_after_timestamp(connection, "QQQ", card.timestamp),
            )
            enriched.append(attach_backtest_to_card(card, result))
        return enriched
    finally:
        connection.close()


def get_live_signal_cards(database_url: str | None = None) -> list[SignalCard]:
    generated = generate_signal_cards_from_database(database_url)
    return generated or create_sample_signal_cards()


def get_signal_card_for_ticker(ticker: str, database_url: str | None = None) -> SignalCard | None:
    ticker = ticker.upper()
    for card in get_live_signal_cards(database_url):
        if card.ticker == ticker:
            return card
    return None


def get_signal_card_history(ticker: str, database_url: str | None = None) -> list[SignalCard]:
    card = get_signal_card_for_ticker(ticker, database_url)
    return [] if card is None else [card]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Signal Cards from stored events.")
    parser.parse_args()

    connection = connect()
    initialize(connection)
    try:
        events = fetch_events(connection)
    finally:
        connection.close()

    cards = generate_signal_cards_from_events(events)
    print(f"total events read: {len(events)}")
    print(f"tickers processed: {len(cards)}")
    print(f"Signal Cards generated: {len(cards)}")
    top_cards = cards[:5]
    if top_cards:
        print("top Signal Cards by signal_strength:")
        for card in top_cards:
            print(f"- {card.ticker}: {card.signal_strength:.1f} ({card.direction})")
    else:
        print("top Signal Cards by signal_strength: none")


if __name__ == "__main__":
    main()

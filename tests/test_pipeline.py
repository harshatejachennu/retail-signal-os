from __future__ import annotations

from datetime import datetime, timezone

from backend.processing.events import Event
from backend.processing.pipeline import (
    aggregate_processed_events,
    generate_signal_cards_from_events,
    process_events,
)


def event(event_id: str, text: str) -> Event:
    return Event(
        event_id=event_id,
        source="reddit",
        event_time=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        ingestion_time=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
        raw_text=text,
        confidence=0.8,
    )


def test_events_can_be_processed_into_ticker_aggregates() -> None:
    processed = process_events([event("e1", "$TSLA buying calls after breakout.")])
    aggregates = aggregate_processed_events(processed)

    assert len(processed) == 1
    assert aggregates[0].ticker == "TSLA"
    assert aggregates[0].mention_count == 1
    assert aggregates[0].bullish_count == 1


def test_signal_cards_are_generated_from_mock_like_events() -> None:
    cards = generate_signal_cards_from_events(
        [
            event("e1", "$TSLA buying calls after breakout."),
            event("e2", "NVDA revenue and margins support the thesis."),
        ]
    )

    assert {card.ticker for card in cards} == {"TSLA", "NVDA"}
    assert all(card.explanation for card in cards)


def test_multiple_events_for_same_ticker_aggregate_correctly() -> None:
    aggregates = aggregate_processed_events(
        process_events(
            [
                event("e1", "$TSLA buying calls after breakout."),
                event("e2", "Tesla is undervalued and I am buying shares."),
            ]
        )
    )

    assert len(aggregates) == 1
    assert aggregates[0].mention_count == 2
    assert aggregates[0].source_event_count == 2
    assert aggregates[0].bullish_ratio == 1.0


def test_insufficient_data_does_not_crash() -> None:
    cards = generate_signal_cards_from_events([event("e1", "Apple held a product discussion.")])

    assert len(cards) == 1
    assert cards[0].data_quality_score < 75
    assert "neutral fallback" in cards[0].explanation


def test_no_events_returns_empty_list() -> None:
    assert generate_signal_cards_from_events([]) == []


def test_bullish_event_group_creates_bullish_signal_card() -> None:
    card = generate_signal_cards_from_events(
        [
            event("e1", "$TSLA buying calls after breakout."),
            event("e2", "Tesla is bullish and undervalued."),
        ]
    )[0]

    assert card.ticker == "TSLA"
    assert card.direction == "bullish"


def test_bearish_event_group_creates_bearish_signal_card() -> None:
    card = generate_signal_cards_from_events(
        [
            event("e1", "$TSLA buying puts because it is overvalued."),
            event("e2", "Tesla looks cooked after the selloff."),
        ]
    )[0]

    assert card.ticker == "TSLA"
    assert card.direction == "bearish"


def test_high_manipulation_risk_lowers_trust_score() -> None:
    clean = generate_signal_cards_from_events(
        [event("e1", "$TSLA revenue and margins support a valuation thesis.")]
    )[0]
    spam = generate_signal_cards_from_events(
        [event("e2", "$TSLA YOLO YOLO ROCKET ROCKET MOON 🚀🚀🚀 FREE MONEY")]
    )[0]

    assert spam.manipulation_risk > clean.manipulation_risk
    assert spam.trust_score < clean.trust_score


def test_limited_data_lowers_data_quality_score() -> None:
    single = generate_signal_cards_from_events([event("e1", "$TSLA buying calls.")])[0]
    multiple = generate_signal_cards_from_events(
        [
            event("e1", "$TSLA buying calls."),
            event("e2", "Tesla is undervalued."),
            event("e3", "TSLA breakout looks bullish."),
        ]
    )[0]

    assert single.data_quality_score < multiple.data_quality_score


def test_mixed_bullish_bearish_events_increase_contradiction_score() -> None:
    mixed = generate_signal_cards_from_events(
        [
            event("e1", "$TSLA buying calls after breakout."),
            event("e2", "Tesla is cooked and overvalued."),
        ]
    )[0]
    bullish = generate_signal_cards_from_events(
        [
            event("e3", "$TSLA buying calls after breakout."),
            event("e4", "Tesla is undervalued."),
        ]
    )[0]

    assert mixed.contradiction_score > bullish.contradiction_score

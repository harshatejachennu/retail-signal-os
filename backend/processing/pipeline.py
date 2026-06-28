from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.features.zscore import rolling_zscore
from backend.models.signal_card import SignalCard
from backend.processing.events import Event
from backend.processing.manipulation import ManipulationRiskResult, score_manipulation_risk
from backend.processing.sentiment import SentimentResult, score_entity_sentiment
from backend.processing.ticker_resolver import resolve_tickers


@dataclass(frozen=True)
class ProcessedEventSignal:
    event: Event
    ticker: str
    sentiment: SentimentResult
    manipulation_risk: ManipulationRiskResult


@dataclass(frozen=True)
class TickerAggregate:
    ticker: str
    mention_count: int
    bullish_count: int
    bearish_count: int
    neutral_or_unclear_count: int
    bullish_ratio: float
    bearish_ratio: float
    average_sentiment_score: float
    average_confidence: float
    average_manipulation_risk: float
    highest_manipulation_risk: float
    top_intents: list[str]
    evidence_terms: list[str]
    source_event_count: int
    mention_z_score: float = 0.0
    latest_event_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def clamp_score(value: float) -> float:
    return round(max(0.0, min(value, 100.0)), 1)


def process_events(events: list[Event]) -> list[ProcessedEventSignal]:
    processed: list[ProcessedEventSignal] = []
    for event in events:
        matches = resolve_tickers(event.raw_text)
        if not matches:
            continue
        manipulation_risk = score_manipulation_risk(event.raw_text)
        for sentiment in score_entity_sentiment(event.raw_text, matches):
            if sentiment.ticker is None:
                continue
            processed.append(
                ProcessedEventSignal(
                    event=event,
                    ticker=sentiment.ticker,
                    sentiment=sentiment,
                    manipulation_risk=manipulation_risk,
                )
            )
    return processed


def aggregate_processed_events(processed: list[ProcessedEventSignal]) -> list[TickerAggregate]:
    grouped: dict[str, list[ProcessedEventSignal]] = defaultdict(list)
    for item in processed:
        grouped[item.ticker].append(item)

    aggregates: list[TickerAggregate] = []
    for ticker, items in grouped.items():
        mention_count = len(items)
        bullish_count = sum(1 for item in items if item.sentiment.market_stance == "bullish")
        bearish_count = sum(1 for item in items if item.sentiment.market_stance == "bearish")
        neutral_or_unclear_count = mention_count - bullish_count - bearish_count
        intents = Counter(item.sentiment.intent for item in items)
        evidence_terms = sorted(
            {term for item in items for term in item.sentiment.evidence_terms}
        )
        event_ids = {item.event.event_id for item in items}
        latest_event_time = max(item.event.event_time for item in items)

        aggregates.append(
            TickerAggregate(
                ticker=ticker,
                mention_count=mention_count,
                bullish_count=bullish_count,
                bearish_count=bearish_count,
                neutral_or_unclear_count=neutral_or_unclear_count,
                bullish_ratio=round(bullish_count / mention_count, 3),
                bearish_ratio=round(bearish_count / mention_count, 3),
                average_sentiment_score=round(
                    sum(item.sentiment.sentiment_score for item in items) / mention_count, 3
                ),
                average_confidence=round(
                    sum(item.sentiment.confidence for item in items) / mention_count, 3
                ),
                average_manipulation_risk=round(
                    sum(item.manipulation_risk.risk_score for item in items) / mention_count, 1
                ),
                highest_manipulation_risk=round(
                    max(item.manipulation_risk.risk_score for item in items), 1
                ),
                top_intents=[intent for intent, _count in intents.most_common(3)],
                evidence_terms=evidence_terms,
                source_event_count=len(event_ids),
                latest_event_time=latest_event_time,
            )
        )

    return _with_mention_z_scores(sorted(aggregates, key=lambda aggregate: aggregate.ticker))


def _with_mention_z_scores(aggregates: list[TickerAggregate]) -> list[TickerAggregate]:
    if len(aggregates) < 3:
        return aggregates
    zscores = rolling_zscore([float(aggregate.mention_count) for aggregate in aggregates], window=3)
    updated: list[TickerAggregate] = []
    for aggregate, zscore in zip(aggregates, zscores, strict=True):
        updated.append(
            TickerAggregate(
                **{
                    **aggregate.__dict__,
                    "mention_z_score": round(zscore or 0.0, 3),
                }
            )
        )
    return updated


def direction_from_aggregate(aggregate: TickerAggregate) -> str:
    if aggregate.source_event_count < 1 or aggregate.mention_count < 1:
        return "uncertain"
    if aggregate.bullish_ratio >= aggregate.bearish_ratio + 0.25 and aggregate.bullish_ratio >= 0.5:
        return "bullish"
    if aggregate.bearish_ratio >= aggregate.bullish_ratio + 0.25 and aggregate.bearish_ratio >= 0.5:
        return "bearish"
    return "neutral"


def _data_quality_score(aggregate: TickerAggregate) -> float:
    score = 35 + min(aggregate.source_event_count, 5) * 10 + aggregate.average_confidence * 25
    if aggregate.source_event_count <= 1:
        score -= 25
    if aggregate.evidence_terms:
        score += 5
    return clamp_score(score)


def _signal_strength(aggregate: TickerAggregate) -> float:
    directional_ratio = max(aggregate.bullish_ratio, aggregate.bearish_ratio)
    mention_component = min(aggregate.mention_count, 5) * 8
    ratio_component = directional_ratio * 25
    sentiment_component = abs(aggregate.average_sentiment_score) * 20
    confidence_component = aggregate.average_confidence * 15
    zscore_component = max(aggregate.mention_z_score, 0.0) * 5
    return clamp_score(mention_component + ratio_component + sentiment_component + confidence_component + zscore_component)


def _trust_score(aggregate: TickerAggregate, data_quality_score: float) -> float:
    score = data_quality_score * 0.55 + aggregate.average_confidence * 35
    score -= aggregate.average_manipulation_risk * 0.45
    if aggregate.source_event_count <= 1:
        score -= 15
    return clamp_score(score)


def _late_hype_risk(aggregate: TickerAggregate) -> float:
    hype_intents = {"meme_hype", "options_gamble", "short_squeeze"}
    hype_count = sum(1 for intent in aggregate.top_intents if intent in hype_intents)
    intent_component = (hype_count / max(len(aggregate.top_intents), 1)) * 45
    return clamp_score(intent_component + aggregate.average_manipulation_risk * 0.45)


def _contradiction_score(aggregate: TickerAggregate) -> float:
    mixed_direction_component = min(aggregate.bullish_ratio, aggregate.bearish_ratio) * 70
    sentiment_stance_disagreement = 0.0
    if aggregate.average_sentiment_score > 0.2 and aggregate.bearish_ratio > aggregate.bullish_ratio:
        sentiment_stance_disagreement = 20.0
    if aggregate.average_sentiment_score < -0.2 and aggregate.bullish_ratio > aggregate.bearish_ratio:
        sentiment_stance_disagreement = 20.0
    return clamp_score(mixed_direction_component + sentiment_stance_disagreement)


def signal_card_from_aggregate(aggregate: TickerAggregate) -> SignalCard:
    data_quality_score = _data_quality_score(aggregate)
    direction = direction_from_aggregate(aggregate)
    signal_strength = _signal_strength(aggregate)
    trust_score = _trust_score(aggregate, data_quality_score)
    late_hype_risk = _late_hype_risk(aggregate)
    contradiction_score = _contradiction_score(aggregate)
    manipulation_level = "high" if aggregate.highest_manipulation_risk >= 70 else "medium" if aggregate.highest_manipulation_risk >= 35 else "low"
    sentiment_label = "positive" if aggregate.average_sentiment_score > 0.15 else "negative" if aggregate.average_sentiment_score < -0.15 else "neutral"
    market_stance = direction if direction != "uncertain" else "unclear"
    top_intents = ", ".join(aggregate.top_intents) if aggregate.top_intents else "unknown"
    data_quality_note = (
        "Data quality is limited because only one source event is available. "
        if aggregate.source_event_count <= 1
        else ""
    )
    zscore_note = (
        "Mention z-score uses a neutral fallback because historical mention data is limited. "
        if aggregate.mention_z_score == 0.0
        else f"Mention z-score is {aggregate.mention_z_score:.2f}. "
    )

    return SignalCard(
        ticker=aggregate.ticker,
        timestamp=aggregate.latest_event_time,
        direction=direction,
        signal_strength=signal_strength,
        trust_score=trust_score,
        manipulation_risk=aggregate.average_manipulation_risk,
        late_hype_risk=late_hype_risk,
        contradiction_score=contradiction_score,
        catalyst_score=0.0,
        data_quality_score=data_quality_score,
        sentiment_label=sentiment_label,
        market_stance=market_stance,
        intent=aggregate.top_intents[0] if aggregate.top_intents else "unknown",
        manipulation_risk_level=manipulation_level,
        manipulation_risk_reasons=[],
        explanation=(
            f"{aggregate.ticker} Signal Card generated from {aggregate.source_event_count} stored social event(s) "
            f"and {aggregate.mention_count} ticker mention(s). Direction is {direction}; top intent type(s): "
            f"{top_intents}. Average manipulation risk is {aggregate.average_manipulation_risk:.1f}/100 "
            f"({manipulation_level}). {data_quality_note}{zscore_note}"
            "Market data, price/volume confirmation, and SEC/news catalysts are not included yet."
        ),
        what_could_go_wrong=(
            "Signal is based on limited mock/social data only. No price or volume confirmation is available yet. "
            "No SEC/news catalyst layer has been added yet. High manipulation risk may indicate hype or spam."
        ),
    )


def generate_signal_cards_from_events(events: list[Event]) -> list[SignalCard]:
    aggregates = aggregate_processed_events(process_events(events))
    return sorted(
        [signal_card_from_aggregate(aggregate) for aggregate in aggregates],
        key=lambda card: card.signal_strength,
        reverse=True,
    )

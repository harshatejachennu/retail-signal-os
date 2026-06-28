from __future__ import annotations

from datetime import datetime, timezone

from backend.models.signal_card import SignalCard
from backend.processing.manipulation import score_manipulation_risk
from backend.processing.sentiment import score_sentiment


def create_signal_card_from_text(ticker: str, text: str, timestamp: datetime | None = None) -> SignalCard:
    sentiment = score_sentiment(text)
    manipulation_risk = score_manipulation_risk(text)
    data_quality_score = 0.72 if text.strip() else 0.2
    signal_strength = min(abs(sentiment.sentiment_score) * 0.5 + 0.25, 1.0)
    trust_score = max(0.0, min(data_quality_score - manipulation_risk * 0.35, 1.0))

    return SignalCard(
        ticker=ticker.upper(),
        timestamp=timestamp or datetime.now(timezone.utc),
        direction=sentiment.market_stance,
        signal_strength=signal_strength,
        trust_score=trust_score,
        manipulation_risk=manipulation_risk,
        late_hype_risk=0.35,
        contradiction_score=0.2,
        catalyst_score=0.3,
        data_quality_score=data_quality_score,
        explanation=(
            f"{ticker.upper()} placeholder Signal Card generated from deterministic text features: "
            f"stance={sentiment.market_stance}, sentiment={sentiment.sentiment_score:.2f}."
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

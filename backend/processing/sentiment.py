from __future__ import annotations

from dataclasses import dataclass


POSITIVE_WORDS = {"bullish", "beat", "beats", "growth", "moon", "upside", "strong", "buy"}
NEGATIVE_WORDS = {"bearish", "miss", "misses", "weak", "fraud", "dump", "downside", "sell"}


@dataclass(frozen=True)
class SentimentResult:
    sentiment_score: float
    label: str
    market_stance: str


def score_sentiment(text: str) -> SentimentResult:
    """Simple placeholder sentiment scorer, separate from market stance extraction."""
    tokens = {token.strip(".,!?;:()[]{}").lower() for token in text.split()}
    positive_hits = len(tokens & POSITIVE_WORDS)
    negative_hits = len(tokens & NEGATIVE_WORDS)
    total_hits = positive_hits + negative_hits
    score = 0.0 if total_hits == 0 else (positive_hits - negative_hits) / total_hits

    if score > 0.2:
        label = "positive"
        stance = "bullish"
    elif score < -0.2:
        label = "negative"
        stance = "bearish"
    else:
        label = "neutral"
        stance = "uncertain"

    return SentimentResult(sentiment_score=score, label=label, market_stance=stance)

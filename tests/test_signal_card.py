from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.models.signal_card import SignalCard
from backend.models.signal_engine import create_signal_card_from_text
from backend.processing.manipulation import score_manipulation_risk


def test_signal_card_validation() -> None:
    card = SignalCard(
        ticker="AAPL",
        timestamp=datetime.now(timezone.utc),
        direction="bullish",
        signal_strength=0.6,
        trust_score=0.7,
        manipulation_risk=0.1,
        late_hype_risk=0.2,
        contradiction_score=0.3,
        catalyst_score=0.4,
        data_quality_score=0.8,
        explanation="Evidence is preliminary.",
        what_could_go_wrong="The narrative may already be priced in.",
    )
    assert card.ticker == "AAPL"


def test_signal_card_rejects_invalid_score() -> None:
    with pytest.raises(ValidationError):
        SignalCard(
            ticker="AAPL",
            timestamp=datetime.now(timezone.utc),
            direction="bullish",
            signal_strength=0.6,
            trust_score=1.2,
            manipulation_risk=0.1,
            late_hype_risk=0.2,
            contradiction_score=0.3,
            catalyst_score=0.4,
            data_quality_score=0.8,
            explanation="Evidence is preliminary.",
            what_could_go_wrong="The narrative may already be priced in.",
        )


def test_signal_engine_adds_explanation_and_risk_text() -> None:
    card = create_signal_card_from_text("NVDA", "NVDA bullish growth and strong upside")
    assert card.explanation
    assert card.what_could_go_wrong
    assert card.direction == "bullish"


def test_manipulation_risk_basic_behavior() -> None:
    low = score_manipulation_risk("Measured discussion about Microsoft revenue growth.")
    high = score_manipulation_risk("$TSLA $NVDA MOON ROCKET YOLO 🚀🚀🚀")
    assert high.risk_score > low.risk_score
    assert 0.0 <= low.risk_score <= 100.0
    assert 0.0 <= high.risk_score <= 100.0

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.features.catalyst import attach_catalyst_to_card, score_catalysts_for_signal
from backend.models.sec_filing import SECFiling
from backend.models.signal_card import SignalCard


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
        explanation="test explanation",
        what_could_go_wrong="test risk",
    )


def filing(form_type: str, filed_at: datetime, filing_id: str = "f1") -> SECFiling:
    return SECFiling(
        filing_id=filing_id,
        ticker="TSLA",
        cik="0001318605",
        form_type=form_type,
        filed_at=filed_at,
        accepted_at=filed_at + timedelta(minutes=5),
        accession_number=filing_id,
        filing_url="https://www.sec.gov/mock",
        title=f"TSLA {form_type}",
        summary="Mock filing",
        source="mock_sec",
    )


def test_nearby_8k_increases_score() -> None:
    timestamp = datetime(2026, 1, 10, tzinfo=timezone.utc)
    result = score_catalysts_for_signal(card(timestamp), [filing("8-K", timestamp - timedelta(hours=2))])

    assert result.catalyst_score > 0
    assert result.matched_filings[0]["form_type"] == "8-K"


def test_old_filing_scores_lower_than_recent_filing() -> None:
    timestamp = datetime(2026, 1, 10, tzinfo=timezone.utc)
    recent = score_catalysts_for_signal(card(timestamp), [filing("8-K", timestamp - timedelta(hours=1))])
    old = score_catalysts_for_signal(card(timestamp), [filing("8-K", timestamp - timedelta(days=6))])

    assert old.catalyst_score < recent.catalyst_score


def test_no_filing_gives_score_zero() -> None:
    result = score_catalysts_for_signal(card(datetime(2026, 1, 10, tzinfo=timezone.utc)), [])

    assert result.catalyst_score == 0
    assert result.matched_filings == []


def test_multiple_filings_cap_at_100() -> None:
    timestamp = datetime(2026, 1, 10, tzinfo=timezone.utc)
    filings = [filing("8-K", timestamp, f"f{index}") for index in range(4)]

    result = score_catalysts_for_signal(card(timestamp), filings)

    assert result.catalyst_score == 100
    assert len(result.matched_filings) == 4


def test_signal_card_can_include_catalyst_score_and_explanation() -> None:
    timestamp = datetime(2026, 1, 10, tzinfo=timezone.utc)
    catalyst = score_catalysts_for_signal(card(timestamp), [filing("Form 4", timestamp)])
    enriched = attach_catalyst_to_card(card(timestamp), catalyst)

    assert enriched.catalyst_score > 0
    assert enriched.catalyst_explanation
    assert enriched.catalyst_events


def test_no_sec_data_does_not_crash_signal_enrichment() -> None:
    timestamp = datetime(2026, 1, 10, tzinfo=timezone.utc)
    enriched = attach_catalyst_to_card(card(timestamp), score_catalysts_for_signal(card(timestamp), []))

    assert enriched.catalyst_score == 0
    assert enriched.catalyst_explanation

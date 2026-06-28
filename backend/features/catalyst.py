from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from backend.models.sec_filing import SECFiling
from backend.models.signal_card import SignalCard


FORM_BASE_SCORES = {
    "8-K": 45.0,
    "Form 4": 32.0,
    "10-Q": 28.0,
    "10-K": 24.0,
}


@dataclass(frozen=True)
class CatalystResult:
    catalyst_score: float
    matched_filings: list[dict[str, Any]]
    catalyst_explanation: str
    catalyst_limitations: str


def score_catalysts_for_signal(
    card: SignalCard,
    filings: list[SECFiling],
    days_before: int = 7,
    days_after: int = 1,
) -> CatalystResult:
    start = card.timestamp - timedelta(days=days_before)
    end = card.timestamp + timedelta(days=days_after)
    nearby = [
        filing
        for filing in filings
        if filing.ticker == card.ticker and start <= filing.filed_at <= end
    ]
    if not nearby:
        return CatalystResult(
            catalyst_score=0.0,
            matched_filings=[],
            catalyst_explanation="No nearby SEC filing was found in the catalyst window.",
            catalyst_limitations="No SEC catalyst match does not mean no catalyst exists; this layer only checks stored filings.",
        )

    scored = sorted(
        [(filing, _filing_score(card.timestamp, filing, days_before, days_after)) for filing in nearby],
        key=lambda item: item[1],
        reverse=True,
    )
    total_score = min(sum(score for _filing, score in scored), 100.0)
    matched = [
        {
            "filing_id": filing.filing_id,
            "ticker": filing.ticker,
            "form_type": filing.form_type,
            "filed_at": filing.filed_at.isoformat(),
            "title": filing.title,
            "summary": filing.summary,
            "filing_url": filing.filing_url,
            "source": filing.source,
            "score_contribution": round(score, 1),
        }
        for filing, score in scored
    ]
    form_types = ", ".join(sorted({filing.form_type for filing, _score in scored}))
    return CatalystResult(
        catalyst_score=round(total_score, 1),
        matched_filings=matched,
        catalyst_explanation=(
            f"Found {len(matched)} nearby SEC filing(s) for {card.ticker} in the catalyst window: {form_types}. "
            "This may strengthen context but does not prove the filing caused the social signal or any price move."
        ),
        catalyst_limitations=(
            "Catalyst scoring uses stored SEC metadata only, defaults to mock mode unless configured otherwise, "
            "and does not include full filing text, market reaction, or causal validation."
        ),
    )


def attach_catalyst_to_card(card: SignalCard, catalyst: CatalystResult) -> SignalCard:
    update = card.model_dump()
    update.update(
        {
            "catalyst_score": catalyst.catalyst_score,
            "catalyst_events": catalyst.matched_filings,
            "catalyst_explanation": catalyst.catalyst_explanation,
            "catalyst_limitations": catalyst.catalyst_limitations,
            "explanation": f"{card.explanation} {catalyst.catalyst_explanation}",
        }
    )
    return SignalCard(**update)


def _filing_score(
    signal_timestamp: datetime,
    filing: SECFiling,
    days_before: int,
    days_after: int,
) -> float:
    base = FORM_BASE_SCORES[filing.form_type]
    distance_seconds = abs((signal_timestamp - filing.filed_at).total_seconds())
    max_seconds = max((days_before + days_after) * 24 * 60 * 60, 1)
    recency_multiplier = max(0.35, 1.0 - distance_seconds / max_seconds)
    return base * recency_multiplier

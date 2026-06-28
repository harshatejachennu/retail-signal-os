from __future__ import annotations

from backend.research.results import LeadLagResult
from backend.research.stats import clean_pair_series, pearson_correlation


def lead_lag_correlation(
    rows: list[dict],
    feature: str,
    target: str,
    lags: list[int] | None = None,
) -> LeadLagResult:
    lags = lags or [1, 2, 3]
    ordered = sorted(rows, key=lambda row: row.get("signal_timestamp"))
    x, y = clean_pair_series(ordered, feature, target)
    if len(x) < max(lags, default=1) + 2:
        return LeadLagResult(
            feature=feature,
            target=target,
            status="insufficient_data",
            interpretation="insufficient_data",
            notes="Not enough paired observations for lead-lag correlation.",
        )

    correlations = {}
    for lag in lags:
        correlations[lag] = pearson_correlation(x[:-lag], y[lag:]) if lag > 0 else pearson_correlation(x, y)
    available = [abs(value) for value in correlations.values() if value is not None]
    interpretation = (
        "predictive_signal_detected"
        if available and max(available) >= 0.3
        else "no_significant_predictive_signal"
    )
    return LeadLagResult(
        feature=feature,
        target=target,
        correlations_by_lag=correlations,
        status="ok",
        interpretation=interpretation,
        notes="Lead-lag correlation is descriptive and does not establish causation.",
    )

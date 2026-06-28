from __future__ import annotations

from backend.research.results import NegativeControlResult
from backend.research.stats import clean_pair_series, pearson_correlation


def run_negative_control(
    rows: list[dict],
    feature: str = "signal_strength",
    control_target: str = "control_return_1d",
    control_ticker: str | None = None,
) -> NegativeControlResult:
    x, y = clean_pair_series(rows, feature, control_target)
    if len(x) < 5:
        return NegativeControlResult(
            status="insufficient_data",
            control_ticker=control_ticker,
            notes="Negative controls need unrelated ticker return rows to detect spurious relationships.",
        )
    correlation = pearson_correlation(x, y)
    warning = None
    if correlation is not None and abs(correlation) >= 0.5:
        warning = "Negative control shows suspiciously strong relationship; check for leakage or spurious structure."
    return NegativeControlResult(
        status="ok",
        control_ticker=control_ticker,
        strongest_abs_correlation=abs(correlation) if correlation is not None else None,
        warning=warning,
        notes="Negative controls help detect spurious relationships and do not prove or disprove causation.",
    )

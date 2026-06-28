from __future__ import annotations

from backend.research.results import GrangerResult
from backend.research.stats import clean_pair_series, pearson_correlation, rough_correlation_p_value


def run_granger_test(
    rows: list[dict],
    feature: str,
    target: str,
    max_lag: int = 3,
    ticker: str | None = None,
) -> GrangerResult:
    filtered = [row for row in rows if ticker is None or row.get("ticker") == ticker]
    ordered = sorted(filtered, key=lambda row: row.get("signal_timestamp"))
    x, y = clean_pair_series(ordered, feature, target)
    min_required = max_lag + 4
    if len(x) < min_required:
        return GrangerResult(
            ticker=ticker,
            feature=feature,
            target=target,
            max_lag=max_lag,
            status="insufficient_data",
            interpretation="insufficient_data",
            notes=f"Need at least {min_required} paired observations for Granger-style validation.",
        )

    statsmodels_result = _statsmodels_granger(x, y, max_lag)
    if statsmodels_result is not None:
        p_values = statsmodels_result
        status = "ok"
        notes = "Used statsmodels Granger causality tests. Results describe predictive usefulness, not true causation."
    else:
        p_values = _fallback_lag_p_values(x, y, max_lag)
        status = "fallback_correlation"
        notes = (
            "statsmodels is unavailable; used lagged correlation p-value approximation. "
            "This is Granger-style screening only and does not prove true causation."
        )

    best = min(p_values.values()) if p_values else None
    interpretation = (
        "predictive_signal_detected"
        if best is not None and best < 0.05
        else "no_significant_predictive_signal"
    )
    return GrangerResult(
        ticker=ticker,
        feature=feature,
        target=target,
        max_lag=max_lag,
        status=status,
        p_values=p_values,
        best_p_value=best,
        interpretation=interpretation,
        notes=notes,
    )


def _statsmodels_granger(x: list[float], y: list[float], max_lag: int) -> dict[int, float] | None:
    try:
        from statsmodels.tsa.stattools import grangercausalitytests
    except ImportError:
        return None
    data = [[target, feature] for feature, target in zip(x, y, strict=True)]
    try:
        raw = grangercausalitytests(data, maxlag=max_lag, verbose=False)
    except Exception:
        return None
    return {
        lag: round(float(result[0]["ssr_ftest"][1]), 6)
        for lag, result in raw.items()
    }


def _fallback_lag_p_values(x: list[float], y: list[float], max_lag: int) -> dict[int, float]:
    p_values: dict[int, float] = {}
    for lag in range(1, max_lag + 1):
        lagged_x = x[:-lag]
        future_y = y[lag:]
        correlation = pearson_correlation(lagged_x, future_y)
        p_value = rough_correlation_p_value(correlation, len(lagged_x))
        if p_value is not None:
            p_values[lag] = p_value
    return p_values

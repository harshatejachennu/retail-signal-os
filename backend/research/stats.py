from __future__ import annotations

import math
from statistics import fmean


def clean_pair_series(rows: list[dict], feature: str, target: str) -> tuple[list[float], list[float]]:
    x: list[float] = []
    y: list[float] = []
    for row in rows:
        feature_value = row.get(feature)
        target_value = row.get(target)
        if feature_value is None or target_value is None:
            continue
        x.append(float(feature_value))
        y.append(float(target_value))
    return x, y


def pearson_correlation(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y) or len(x) < 2:
        return None
    mean_x = fmean(x)
    mean_y = fmean(y)
    centered_x = [value - mean_x for value in x]
    centered_y = [value - mean_y for value in y]
    denom_x = math.sqrt(sum(value * value for value in centered_x))
    denom_y = math.sqrt(sum(value * value for value in centered_y))
    if denom_x == 0 or denom_y == 0:
        return None
    return round(sum(a * b for a, b in zip(centered_x, centered_y, strict=True)) / (denom_x * denom_y), 6)


def rough_correlation_p_value(correlation: float | None, n: int) -> float | None:
    if correlation is None or n < 4:
        return None
    bounded = max(-0.999999, min(0.999999, correlation))
    z_score = abs(bounded) * math.sqrt(n - 3)
    # Normal approximation; sufficient for deterministic fallback messaging, not publication-grade inference.
    p_value = math.erfc(z_score / math.sqrt(2))
    return round(max(0.0, min(p_value, 1.0)), 6)


def average(values: list[float | None]) -> float | None:
    available = [value for value in values if value is not None]
    return round(fmean(available), 6) if available else None

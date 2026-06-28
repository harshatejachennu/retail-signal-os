from __future__ import annotations

import statistics


def rolling_zscore(values: list[float], window: int) -> list[float | None]:
    if window <= 1:
        raise ValueError("window must be greater than 1")
    zscores: list[float | None] = []
    for index, value in enumerate(values):
        if index + 1 < window:
            zscores.append(None)
            continue
        sample = values[index + 1 - window : index + 1]
        mean = statistics.fmean(sample)
        std = statistics.pstdev(sample)
        zscores.append(0.0 if std == 0 else (value - mean) / std)
    return zscores

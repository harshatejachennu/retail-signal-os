from __future__ import annotations

import math


def exponential_time_decay(age_seconds: float, half_life_seconds: float) -> float:
    if age_seconds < 0:
        raise ValueError("age_seconds cannot be negative")
    if half_life_seconds <= 0:
        raise ValueError("half_life_seconds must be positive")
    return math.exp(-math.log(2) * age_seconds / half_life_seconds)

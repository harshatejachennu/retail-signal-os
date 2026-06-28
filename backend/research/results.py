from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Interpretation = Literal[
    "predictive_signal_detected",
    "no_significant_predictive_signal",
    "insufficient_data",
]


class GrangerResult(BaseModel):
    ticker: str | None = None
    feature: str
    target: str
    max_lag: int
    status: str
    p_values: dict[int, float] = Field(default_factory=dict)
    best_p_value: float | None = None
    interpretation: Interpretation
    notes: str


class LeadLagResult(BaseModel):
    feature: str
    target: str
    correlations_by_lag: dict[int, float | None] = Field(default_factory=dict)
    status: str
    interpretation: Interpretation
    notes: str


class EventStudyResult(BaseModel):
    signals_evaluated: int
    average_pre_event_return: float | None = None
    average_post_event_return: float | None = None
    average_abnormal_return_vs_spy: float | None = None
    average_abnormal_return_vs_qqq: float | None = None
    notes: str


class NegativeControlResult(BaseModel):
    status: str
    control_ticker: str | None = None
    strongest_abs_correlation: float | None = None
    warning: str | None = None
    notes: str


class AblationResult(BaseModel):
    feature_group: str
    metric_with_group: float | None = None
    metric_without_group: float | None = None
    delta: float | None = None
    interpretation: str

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ModelTrainingResult(BaseModel):
    status: str
    warnings: list[str] = Field(default_factory=list)
    model_name: str
    target_name: str
    row_count: int
    feature_columns: list[str] = Field(default_factory=list)
    metrics: dict[str, float | None] = Field(default_factory=dict)
    artifact_path: str | None = None
    interpretation: str


class ModelEvaluationResult(BaseModel):
    status: str
    warnings: list[str] = Field(default_factory=list)
    model_name: str
    target_name: str
    row_count: int
    feature_columns: list[str] = Field(default_factory=list)
    metrics: dict[str, float | None] = Field(default_factory=dict)
    interpretation: str


class WalkForwardResult(BaseModel):
    status: str
    warnings: list[str] = Field(default_factory=list)
    model_name: str
    target_name: str
    row_count: int
    feature_columns: list[str] = Field(default_factory=list)
    fold_count: int = 0
    metrics: dict[str, float | None] = Field(default_factory=dict)
    interpretation: str


class FeatureImportanceResult(BaseModel):
    status: str
    warnings: list[str] = Field(default_factory=list)
    model_name: str
    target_name: str
    row_count: int
    feature_columns: list[str] = Field(default_factory=list)
    importances: list[dict[str, Any]] = Field(default_factory=list)
    interpretation: str


class MLSignalScore(BaseModel):
    status: str
    ml_score_available: bool
    target_probabilities: dict[str, float] = Field(default_factory=dict)
    confidence_level: str
    warnings: list[str] = Field(default_factory=list)
    interpretation: str

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.research.dataset import assemble_research_dataset


ML_FEATURE_COLUMNS = [
    "signal_strength",
    "trust_score",
    "manipulation_risk",
    "late_hype_risk",
    "contradiction_score",
    "catalyst_score",
    "data_quality_score",
    "bullish_ratio",
    "bearish_ratio",
    "mention_count",
    "source_event_count",
    "sentiment_score",
]
FORBIDDEN_FEATURE_COLUMNS = {
    "return_1d",
    "return_3d",
    "spy_adjusted_return_1d",
    "spy_adjusted_return_3d",
    "qqq_adjusted_return_1d",
    "qqq_adjusted_return_3d",
    "outperform_spy_3d",
    "outperform_qqq_3d",
    "positive_return_3d",
}
TARGET_COLUMNS = ["outperform_spy_3d", "outperform_qqq_3d", "positive_return_3d"]


@dataclass(frozen=True)
class MLDataset:
    status: str
    rows: list[dict[str, Any]]
    feature_columns: list[str]
    target_columns: list[str]
    warnings: list[str]
    target_distribution: dict[str, dict[int, int]]


def build_ml_dataset(
    research_rows: list[dict[str, Any]] | None = None,
    database_url: str | None = None,
    min_rows: int = 8,
) -> MLDataset:
    source_rows = research_rows if research_rows is not None else assemble_research_dataset(database_url=database_url)
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for source in sorted(source_rows, key=lambda row: row.get("signal_timestamp")):
        row = {
            "ticker": source.get("ticker"),
            "signal_timestamp": source.get("signal_timestamp"),
        }
        for feature in ML_FEATURE_COLUMNS:
            row[feature] = _numeric_or_zero(source.get(feature))
        if source.get("spy_adjusted_return_3d") is not None:
            row["outperform_spy_3d"] = 1 if float(source["spy_adjusted_return_3d"]) > 0 else 0
        if source.get("qqq_adjusted_return_3d") is not None:
            row["outperform_qqq_3d"] = 1 if float(source["qqq_adjusted_return_3d"]) > 0 else 0
        if source.get("return_3d") is not None:
            row["positive_return_3d"] = 1 if float(source["return_3d"]) > 0 else 0
        rows.append(row)

    feature_columns = [column for column in ML_FEATURE_COLUMNS if column not in FORBIDDEN_FEATURE_COLUMNS]
    target_columns = [target for target in TARGET_COLUMNS if any(target in row for row in rows)]
    distribution = {
        target: {
            0: sum(1 for row in rows if row.get(target) == 0),
            1: sum(1 for row in rows if row.get(target) == 1),
        }
        for target in target_columns
    }

    status = "ok"
    if len(rows) < min_rows:
        status = "insufficient_data"
        warnings.append(f"Need at least {min_rows} rows for ML training.")
    for target in target_columns:
        classes = {row.get(target) for row in rows if row.get(target) is not None}
        if len(classes) < 2:
            warnings.append(f"Target {target} has only one class.")

    return MLDataset(
        status=status,
        rows=rows,
        feature_columns=feature_columns,
        target_columns=target_columns,
        warnings=warnings,
        target_distribution=distribution,
    )


def target_is_trainable(dataset: MLDataset, target: str, min_rows: int = 8) -> bool:
    rows = [row for row in dataset.rows if row.get(target) is not None]
    classes = {row[target] for row in rows}
    return len(rows) >= min_rows and len(classes) >= 2


def matrix_and_target(dataset: MLDataset, target: str) -> tuple[list[list[float]], list[int], list[dict[str, Any]]]:
    rows = [row for row in dataset.rows if row.get(target) is not None]
    x = [[float(row.get(feature, 0.0) or 0.0) for feature in dataset.feature_columns] for row in rows]
    y = [int(row[target]) for row in rows]
    return x, y, rows


def _numeric_or_zero(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

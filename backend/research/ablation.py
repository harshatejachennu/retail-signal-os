from __future__ import annotations

from backend.research.results import AblationResult
from backend.research.stats import pearson_correlation


FEATURE_GROUPS = {
    "social_strength": ["signal_strength", "bullish_ratio", "bearish_ratio", "mention_count"],
    "risk": ["manipulation_risk", "late_hype_risk", "contradiction_score"],
    "catalyst": ["catalyst_score"],
    "quality": ["trust_score", "data_quality_score"],
}


def run_ablation_tests(rows: list[dict], target: str = "return_3d") -> list[AblationResult]:
    if len(rows) < 8:
        return [
            AblationResult(
                feature_group=group,
                interpretation="insufficient_data",
            )
            for group in FEATURE_GROUPS
        ]

    results: list[AblationResult] = []
    for group, features in FEATURE_GROUPS.items():
        with_group = _group_metric(rows, features, target)
        without_features = [feature for other_group, group_features in FEATURE_GROUPS.items() if other_group != group for feature in group_features]
        without_group = _group_metric(rows, without_features, target)
        delta = None if with_group is None or without_group is None else round(with_group - without_group, 6)
        interpretation = "feature_group_helped" if delta is not None and delta > 0 else "no_improvement_detected"
        results.append(
            AblationResult(
                feature_group=group,
                metric_with_group=with_group,
                metric_without_group=without_group,
                delta=delta,
                interpretation=interpretation,
            )
        )
    return results


def _group_metric(rows: list[dict], features: list[str], target: str) -> float | None:
    scores: list[float] = []
    targets: list[float] = []
    for row in rows:
        target_value = row.get(target)
        values = [float(row[feature]) for feature in features if row.get(feature) is not None]
        if target_value is None or not values:
            continue
        scores.append(sum(values) / len(values))
        targets.append(float(target_value))
    correlation = pearson_correlation(scores, targets)
    return abs(correlation) if correlation is not None else None

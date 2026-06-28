from __future__ import annotations

import argparse

from backend.ml.dataset import TARGET_COLUMNS, build_ml_dataset
from backend.ml.models import evaluate_baseline, feature_importance, train_logistic_regression, train_random_forest
from backend.ml.walk_forward import run_walk_forward_validation


def run_training(save_artifacts: bool = True) -> dict:
    dataset = build_ml_dataset()
    target = _first_available_target(dataset.target_columns)
    warnings = list(dataset.warnings)
    if target is None:
        return {
            "dataset_rows": len(dataset.rows),
            "target_availability": dataset.target_distribution,
            "model_statuses": {},
            "latest_metrics": {},
            "feature_importance": feature_importance(dataset, "positive_return_3d").model_dump(mode="json"),
            "walk_forward": run_walk_forward_validation(dataset, "positive_return_3d").model_dump(mode="json"),
            "warnings": warnings + ["No ML targets are available."],
        }

    baseline = evaluate_baseline(dataset, target)
    logistic = train_logistic_regression(dataset, target, save_artifact=save_artifacts)
    forest = train_random_forest(dataset, target, save_artifact=save_artifacts)
    importance = feature_importance(dataset, target)
    walk_forward = run_walk_forward_validation(dataset, target)
    return {
        "dataset_rows": len(dataset.rows),
        "target_availability": dataset.target_distribution,
        "model_statuses": {
            "baseline": baseline.status,
            "logistic_regression": logistic.status,
            "random_forest": forest.status,
            "walk_forward": walk_forward.status,
        },
        "latest_metrics": {
            "baseline": baseline.metrics,
            "logistic_regression": logistic.metrics,
            "random_forest": forest.metrics,
            "walk_forward": walk_forward.metrics,
        },
        "feature_importance": importance.model_dump(mode="json"),
        "walk_forward": walk_forward.model_dump(mode="json"),
        "warnings": warnings + baseline.warnings + logistic.warnings + forest.warnings + walk_forward.warnings,
    }


def _first_available_target(targets: list[str]) -> str | None:
    for target in TARGET_COLUMNS:
        if target in targets:
            return target
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate lightweight ML signal scoring models.")
    parser.parse_args()
    summary = run_training(save_artifacts=True)
    print(f"dataset rows: {summary['dataset_rows']}")
    print(f"targets available: {summary['target_availability']}")
    print(f"model statuses: {summary['model_statuses']}")
    print(f"metrics: {summary['latest_metrics']}")
    print(f"warnings: {summary['warnings']}")
    print("Reminder: ML outputs are educational estimates, not financial advice or guaranteed predictions.")


if __name__ == "__main__":
    main()

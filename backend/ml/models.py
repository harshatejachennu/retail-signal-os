from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import fmean
from typing import Any

from backend.ml.dataset import MLDataset, matrix_and_target, target_is_trainable
from backend.ml.results import FeatureImportanceResult, ModelEvaluationResult, ModelTrainingResult
from backend.ml.split import chronological_train_test_split
from backend.research.stats import pearson_correlation


ARTIFACT_DIR = Path("artifacts/models")


def evaluate_baseline(dataset: MLDataset, target: str) -> ModelEvaluationResult:
    rows = [row for row in dataset.rows if row.get(target) is not None]
    if len(rows) < 3:
        return _insufficient_eval("baseline_majority", target, dataset, "Need at least 3 labeled rows.")
    split = chronological_train_test_split(rows, min_train=2, min_test=1)
    if split.status != "ok":
        return _insufficient_eval("baseline_majority", target, dataset, split.warnings[0])
    majority = 1 if sum(row[target] for row in split.train_rows) >= len(split.train_rows) / 2 else 0
    y_true = [int(row[target]) for row in split.test_rows]
    probabilities = [float(majority) for _row in split.test_rows]
    y_pred = [majority for _row in split.test_rows]
    return ModelEvaluationResult(
        status="ok",
        model_name="baseline_majority",
        target_name=target,
        row_count=len(rows),
        feature_columns=[],
        metrics=_classification_metrics(y_true, y_pred, probabilities),
        interpretation="Majority-class baseline for comparison; no predictive claim is made.",
    )


def train_logistic_regression(dataset: MLDataset, target: str, save_artifact: bool = False) -> ModelTrainingResult:
    if not target_is_trainable(dataset, target):
        return _insufficient_training("logistic_regression", target, dataset)
    rows = [row for row in dataset.rows if row.get(target) is not None]
    split = chronological_train_test_split(rows)
    if split.status != "ok":
        return _insufficient_training("logistic_regression", target, dataset, split.warnings)

    sklearn_result = _sklearn_logistic(dataset, target, split.train_rows, split.test_rows, save_artifact)
    if sklearn_result is not None:
        return sklearn_result
    model = _fit_linear_probability_model(dataset, target, split.train_rows)
    probabilities = [_predict_linear_probability(model, dataset, row) for row in split.test_rows]
    y_true = [int(row[target]) for row in split.test_rows]
    y_pred = [1 if probability >= 0.5 else 0 for probability in probabilities]
    artifact_path = _save_json_artifact("logistic_regression", target, model) if save_artifact else None
    return ModelTrainingResult(
        status="ok",
        warnings=["scikit-learn unavailable; used deterministic linear probability fallback."],
        model_name="logistic_regression",
        target_name=target,
        row_count=len(rows),
        feature_columns=dataset.feature_columns,
        metrics=_classification_metrics(y_true, y_pred, probabilities),
        artifact_path=artifact_path,
        interpretation="Estimated probability of historical outperformance; not a guaranteed prediction.",
    )


def train_random_forest(dataset: MLDataset, target: str, save_artifact: bool = False) -> ModelTrainingResult:
    if not target_is_trainable(dataset, target):
        return _insufficient_training("random_forest", target, dataset)
    rows = [row for row in dataset.rows if row.get(target) is not None]
    split = chronological_train_test_split(rows)
    if split.status != "ok":
        return _insufficient_training("random_forest", target, dataset, split.warnings)

    sklearn_result = _sklearn_random_forest(dataset, target, split.train_rows, split.test_rows, save_artifact)
    if sklearn_result is not None:
        return sklearn_result
    importances = _correlation_importances(dataset, target, split.train_rows)
    model = {"importances": importances}
    probabilities = [_predict_importance_vote(model, dataset, row) for row in split.test_rows]
    y_true = [int(row[target]) for row in split.test_rows]
    y_pred = [1 if probability >= 0.5 else 0 for probability in probabilities]
    artifact_path = _save_json_artifact("random_forest", target, model) if save_artifact else None
    return ModelTrainingResult(
        status="ok",
        warnings=["scikit-learn unavailable; used deterministic feature-importance fallback."],
        model_name="random_forest",
        target_name=target,
        row_count=len(rows),
        feature_columns=dataset.feature_columns,
        metrics=_classification_metrics(y_true, y_pred, probabilities),
        artifact_path=artifact_path,
        interpretation="Estimated probability of historical outperformance; not a guaranteed prediction.",
    )


def feature_importance(dataset: MLDataset, target: str, model_name: str = "random_forest") -> FeatureImportanceResult:
    if not target_is_trainable(dataset, target):
        return FeatureImportanceResult(
            status="insufficient_data",
            warnings=["Need enough rows and two target classes for feature importance."],
            model_name=model_name,
            target_name=target,
            row_count=len(dataset.rows),
            feature_columns=dataset.feature_columns,
            interpretation="Insufficient data for feature importance.",
        )
    importances = _correlation_importances(dataset, target, [row for row in dataset.rows if row.get(target) is not None])
    return FeatureImportanceResult(
        status="ok",
        model_name=model_name,
        target_name=target,
        row_count=len(dataset.rows),
        feature_columns=dataset.feature_columns,
        importances=[
            {"feature": feature, "importance": round(value, 6)}
            for feature, value in sorted(importances.items(), key=lambda item: item[1], reverse=True)
        ],
        interpretation="Feature importance is descriptive for this dataset and can be unstable on small samples.",
    )


def _classification_metrics(y_true: list[int], y_pred: list[int], probabilities: list[float]) -> dict[str, float | None]:
    if not y_true:
        return {"accuracy": None, "precision": None, "recall": None, "f1": None, "roc_auc": None}
    tp = sum(1 for truth, pred in zip(y_true, y_pred, strict=True) if truth == 1 and pred == 1)
    tn = sum(1 for truth, pred in zip(y_true, y_pred, strict=True) if truth == 0 and pred == 0)
    fp = sum(1 for truth, pred in zip(y_true, y_pred, strict=True) if truth == 0 and pred == 1)
    fn = sum(1 for truth, pred in zip(y_true, y_pred, strict=True) if truth == 1 and pred == 0)
    accuracy = (tp + tn) / len(y_true)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    return {
        "accuracy": round(accuracy, 6),
        "precision": round(precision, 6) if precision is not None else None,
        "recall": round(recall, 6) if recall is not None else None,
        "f1": round(f1, 6) if f1 is not None else None,
        "roc_auc": _roc_auc(y_true, probabilities),
    }


def _roc_auc(y_true: list[int], probabilities: list[float]) -> float | None:
    positives = [score for truth, score in zip(y_true, probabilities, strict=True) if truth == 1]
    negatives = [score for truth, score in zip(y_true, probabilities, strict=True) if truth == 0]
    if not positives or not negatives:
        return None
    wins = 0.0
    total = len(positives) * len(negatives)
    for pos in positives:
        for neg in negatives:
            wins += 1.0 if pos > neg else 0.5 if pos == neg else 0.0
    return round(wins / total, 6)


def _insufficient_eval(model_name: str, target: str, dataset: MLDataset, warning: str) -> ModelEvaluationResult:
    return ModelEvaluationResult(
        status="insufficient_data",
        warnings=[warning],
        model_name=model_name,
        target_name=target,
        row_count=len(dataset.rows),
        feature_columns=[],
        interpretation="Insufficient data for model evaluation.",
    )


def _insufficient_training(
    model_name: str,
    target: str,
    dataset: MLDataset,
    warnings: list[str] | None = None,
) -> ModelTrainingResult:
    return ModelTrainingResult(
        status="insufficient_data",
        warnings=warnings or ["Need enough rows and at least two target classes for training."],
        model_name=model_name,
        target_name=target,
        row_count=len(dataset.rows),
        feature_columns=dataset.feature_columns,
        interpretation="Insufficient data for ML training.",
    )


def _fit_linear_probability_model(dataset: MLDataset, target: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    weights = _correlation_importances(dataset, target, rows, signed=True)
    base_rate = sum(int(row[target]) for row in rows) / len(rows)
    means = {feature: fmean(float(row.get(feature, 0.0) or 0.0) for row in rows) for feature in dataset.feature_columns}
    return {"weights": weights, "base_rate": base_rate, "means": means}


def _predict_linear_probability(model: dict[str, Any], dataset: MLDataset, row: dict[str, Any]) -> float:
    score = math.log(model["base_rate"] / (1 - model["base_rate"])) if 0 < model["base_rate"] < 1 else 0.0
    for feature in dataset.feature_columns:
        score += model["weights"].get(feature, 0.0) * ((float(row.get(feature, 0.0) or 0.0) - model["means"].get(feature, 0.0)) / 100.0)
    return round(1 / (1 + math.exp(-score)), 6)


def _correlation_importances(
    dataset: MLDataset,
    target: str,
    rows: list[dict[str, Any]],
    signed: bool = False,
) -> dict[str, float]:
    output = {}
    target_values = [float(row[target]) for row in rows]
    for feature in dataset.feature_columns:
        feature_values = [float(row.get(feature, 0.0) or 0.0) for row in rows]
        corr = pearson_correlation(feature_values, target_values) or 0.0
        output[feature] = corr if signed else abs(corr)
    return output


def _predict_importance_vote(model: dict[str, Any], dataset: MLDataset, row: dict[str, Any]) -> float:
    importances = model["importances"]
    total = sum(importances.values()) or 1.0
    weighted = sum((float(row.get(feature, 0.0) or 0.0) / 100.0) * importances.get(feature, 0.0) for feature in dataset.feature_columns)
    return round(max(0.0, min(weighted / total, 1.0)), 6)


def _save_json_artifact(model_name: str, target: str, payload: dict[str, Any]) -> str:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / f"{model_name}_{target}.json"
    path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    return str(path)


def _sklearn_logistic(
    dataset: MLDataset,
    target: str,
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    save_artifact: bool,
) -> ModelTrainingResult | None:
    try:
        from joblib import dump
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        return None
    x_train = [[float(row.get(feature, 0.0) or 0.0) for feature in dataset.feature_columns] for row in train_rows]
    y_train = [int(row[target]) for row in train_rows]
    if len(set(y_train)) < 2:
        return None
    x_test = [[float(row.get(feature, 0.0) or 0.0) for feature in dataset.feature_columns] for row in test_rows]
    y_test = [int(row[target]) for row in test_rows]
    model = make_pipeline(StandardScaler(), LogisticRegression(random_state=42, max_iter=1000))
    model.fit(x_train, y_train)
    probabilities = [float(item[1]) for item in model.predict_proba(x_test)]
    y_pred = [int(item) for item in model.predict(x_test)]
    artifact_path = None
    if save_artifact:
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        artifact_path = str(ARTIFACT_DIR / f"logistic_regression_{target}.joblib")
        dump({"model": model, "feature_columns": dataset.feature_columns, "target": target}, artifact_path)
    return ModelTrainingResult(
        status="ok",
        model_name="logistic_regression",
        target_name=target,
        row_count=len(train_rows) + len(test_rows),
        feature_columns=dataset.feature_columns,
        metrics=_classification_metrics(y_test, y_pred, probabilities),
        artifact_path=artifact_path,
        interpretation="Estimated probability of historical outperformance; not a guaranteed prediction.",
    )


def _sklearn_random_forest(
    dataset: MLDataset,
    target: str,
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    save_artifact: bool,
) -> ModelTrainingResult | None:
    try:
        from joblib import dump
        from sklearn.ensemble import RandomForestClassifier
    except ImportError:
        return None
    x_train = [[float(row.get(feature, 0.0) or 0.0) for feature in dataset.feature_columns] for row in train_rows]
    y_train = [int(row[target]) for row in train_rows]
    if len(set(y_train)) < 2:
        return None
    x_test = [[float(row.get(feature, 0.0) or 0.0) for feature in dataset.feature_columns] for row in test_rows]
    y_test = [int(row[target]) for row in test_rows]
    model = RandomForestClassifier(n_estimators=50, max_depth=4, random_state=42)
    model.fit(x_train, y_train)
    probabilities = [float(item[1]) for item in model.predict_proba(x_test)]
    y_pred = [int(item) for item in model.predict(x_test)]
    artifact_path = None
    if save_artifact:
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        artifact_path = str(ARTIFACT_DIR / f"random_forest_{target}.joblib")
        dump({"model": model, "feature_columns": dataset.feature_columns, "target": target}, artifact_path)
    return ModelTrainingResult(
        status="ok",
        model_name="random_forest",
        target_name=target,
        row_count=len(train_rows) + len(test_rows),
        feature_columns=dataset.feature_columns,
        metrics=_classification_metrics(y_test, y_pred, probabilities),
        artifact_path=artifact_path,
        interpretation="Estimated probability of historical outperformance; not a guaranteed prediction.",
    )

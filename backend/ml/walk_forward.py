from __future__ import annotations

from backend.ml.dataset import MLDataset
from backend.ml.models import _classification_metrics, _fit_linear_probability_model, _predict_linear_probability
from backend.ml.results import WalkForwardResult


def run_walk_forward_validation(
    dataset: MLDataset,
    target: str,
    train_window: int = 6,
    test_window: int = 2,
) -> WalkForwardResult:
    rows = [row for row in dataset.rows if row.get(target) is not None]
    if len(rows) < train_window + test_window:
        return WalkForwardResult(
            status="insufficient_data",
            warnings=[f"Need at least {train_window + test_window} labeled rows for walk-forward validation."],
            model_name="logistic_regression",
            target_name=target,
            row_count=len(rows),
            feature_columns=dataset.feature_columns,
            interpretation="Insufficient data for walk-forward validation.",
        )

    y_true_all: list[int] = []
    y_pred_all: list[int] = []
    probabilities_all: list[float] = []
    fold_count = 0
    start = 0
    while start + train_window + test_window <= len(rows):
        train_rows = rows[start : start + train_window]
        test_rows = rows[start + train_window : start + train_window + test_window]
        if len({row[target] for row in train_rows}) < 2:
            start += test_window
            continue
        model = _fit_linear_probability_model(dataset, target, train_rows)
        probabilities = [_predict_linear_probability(model, dataset, row) for row in test_rows]
        y_true = [int(row[target]) for row in test_rows]
        y_pred = [1 if probability >= 0.5 else 0 for probability in probabilities]
        y_true_all.extend(y_true)
        y_pred_all.extend(y_pred)
        probabilities_all.extend(probabilities)
        fold_count += 1
        start += test_window

    if fold_count == 0:
        return WalkForwardResult(
            status="insufficient_data",
            warnings=["No walk-forward fold had two target classes in the training window."],
            model_name="logistic_regression",
            target_name=target,
            row_count=len(rows),
            feature_columns=dataset.feature_columns,
            interpretation="Insufficient class variation for walk-forward validation.",
        )
    return WalkForwardResult(
        status="ok",
        model_name="logistic_regression",
        target_name=target,
        row_count=len(rows),
        feature_columns=dataset.feature_columns,
        fold_count=fold_count,
        metrics=_classification_metrics(y_true_all, y_pred_all, probabilities_all),
        interpretation="Walk-forward validation uses older rows for training and newer rows for testing; no trading advice.",
    )

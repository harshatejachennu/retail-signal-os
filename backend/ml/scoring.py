from __future__ import annotations

from backend.ml.dataset import MLDataset, TARGET_COLUMNS, build_ml_dataset
from backend.ml.models import _fit_linear_probability_model, _predict_linear_probability
from backend.ml.results import MLSignalScore
from backend.models.signal_card import SignalCard


def score_signal_card(card: SignalCard, dataset: MLDataset | None = None) -> MLSignalScore:
    dataset = dataset or build_ml_dataset()
    if dataset.status != "ok":
        return MLSignalScore(
            status="insufficient_data",
            ml_score_available=False,
            confidence_level="none",
            warnings=dataset.warnings or ["Insufficient historical rows for ML scoring."],
            interpretation="ML score unavailable; more historical labeled Signal Cards are needed.",
        )

    card_row = _row_from_card(card, dataset)
    probabilities: dict[str, float] = {}
    warnings: list[str] = []
    for target in TARGET_COLUMNS:
        target_rows = [row for row in dataset.rows if row.get(target) is not None]
        if len(target_rows) < 8 or len({row[target] for row in target_rows}) < 2:
            warnings.append(f"Target {target} is not trainable.")
            continue
        model = _fit_linear_probability_model(dataset, target, target_rows)
        probabilities[target] = _predict_linear_probability(model, dataset, card_row)

    if not probabilities:
        return MLSignalScore(
            status="insufficient_data",
            ml_score_available=False,
            confidence_level="none",
            warnings=warnings,
            interpretation="ML score unavailable; no target has enough class variation.",
        )
    confidence = "low" if len(dataset.rows) < 30 else "medium" if len(dataset.rows) < 100 else "higher"
    return MLSignalScore(
        status="ok",
        ml_score_available=True,
        target_probabilities=probabilities,
        confidence_level=confidence,
        warnings=warnings + ["Probabilities are historical estimates, not buy/sell instructions."],
        interpretation="Estimated probabilities of historical outperformance; not a guaranteed prediction.",
    )


def _row_from_card(card: SignalCard, dataset: MLDataset) -> dict:
    return {
        "signal_timestamp": card.timestamp,
        "ticker": card.ticker,
        **{feature: float(getattr(card, feature, 0.0) or 0.0) for feature in dataset.feature_columns},
    }

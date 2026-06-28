from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.ml.dataset import FORBIDDEN_FEATURE_COLUMNS, build_ml_dataset
from backend.ml.models import evaluate_baseline, feature_importance, train_logistic_regression, train_random_forest
from backend.ml.scoring import score_signal_card
from backend.ml.split import chronological_train_test_split
from backend.ml.walk_forward import run_walk_forward_validation
from backend.models.signal_card import SignalCard


def research_rows(count: int = 14, one_class: bool = False) -> list[dict]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        positive = 1 if one_class else index % 2
        signed = 0.02 if positive else -0.01
        rows.append(
            {
                "ticker": "AMD",
                "signal_timestamp": start + timedelta(days=index),
                "direction": "bullish",
                "signal_strength": 30 + index,
                "trust_score": 45 + index,
                "manipulation_risk": 10,
                "late_hype_risk": 5,
                "contradiction_score": 2,
                "catalyst_score": index % 4,
                "data_quality_score": 70,
                "bullish_ratio": index / max(count - 1, 1),
                "bearish_ratio": 1 - index / max(count - 1, 1),
                "mention_count": index + 1,
                "source_event_count": index + 1,
                "sentiment_score": 0.1 * positive,
                "return_3d": signed,
                "spy_adjusted_return_3d": signed,
                "qqq_adjusted_return_3d": signed,
            }
        )
    return rows


def signal_card() -> SignalCard:
    return SignalCard(
        ticker="AMD",
        timestamp=datetime(2026, 2, 1, tzinfo=timezone.utc),
        direction="bullish",
        signal_strength=60,
        trust_score=65,
        manipulation_risk=10,
        late_hype_risk=5,
        contradiction_score=2,
        catalyst_score=20,
        data_quality_score=75,
        explanation="synthetic",
        what_could_go_wrong="synthetic",
    )


def test_ml_dataset_creates_features_and_targets() -> None:
    dataset = build_ml_dataset(research_rows=research_rows())

    assert dataset.status == "ok"
    assert dataset.rows
    assert "positive_return_3d" in dataset.target_columns
    assert "signal_strength" in dataset.feature_columns


def test_ml_dataset_prevents_target_leakage() -> None:
    dataset = build_ml_dataset(research_rows=research_rows())

    assert not (set(dataset.feature_columns) & FORBIDDEN_FEATURE_COLUMNS)


def test_ml_dataset_handles_missing_features() -> None:
    rows = research_rows(10)
    del rows[0]["signal_strength"]

    dataset = build_ml_dataset(research_rows=rows)

    assert dataset.rows[0]["signal_strength"] == 0.0


def test_one_class_target_is_insufficient_for_training() -> None:
    dataset = build_ml_dataset(research_rows=research_rows(one_class=True))
    result = train_logistic_regression(dataset, "positive_return_3d")

    assert result.status == "insufficient_data"


def test_chronological_train_test_split() -> None:
    split = chronological_train_test_split(research_rows(10), min_train=5, min_test=2)

    assert split.status == "ok"
    assert max(row["signal_timestamp"] for row in split.train_rows) < min(row["signal_timestamp"] for row in split.test_rows)


def test_baseline_returns_valid_metrics() -> None:
    dataset = build_ml_dataset(research_rows=research_rows())
    result = evaluate_baseline(dataset, "positive_return_3d")

    assert result.status == "ok"
    assert "accuracy" in result.metrics


def test_logistic_regression_handles_sufficient_synthetic_data() -> None:
    dataset = build_ml_dataset(research_rows=research_rows())
    result = train_logistic_regression(dataset, "positive_return_3d")

    assert result.status == "ok"
    assert result.metrics


def test_random_forest_handles_sufficient_synthetic_data() -> None:
    dataset = build_ml_dataset(research_rows=research_rows())
    result = train_random_forest(dataset, "positive_return_3d")

    assert result.status == "ok"
    assert result.metrics


def test_feature_importance_is_json_serializable() -> None:
    dataset = build_ml_dataset(research_rows=research_rows())
    result = feature_importance(dataset, "positive_return_3d")

    assert result.model_dump(mode="json")["importances"]


def test_walk_forward_handles_insufficient_and_sufficient_data() -> None:
    insufficient = run_walk_forward_validation(build_ml_dataset(research_rows=research_rows(5)), "positive_return_3d")
    sufficient = run_walk_forward_validation(build_ml_dataset(research_rows=research_rows(14)), "positive_return_3d")

    assert insufficient.status == "insufficient_data"
    assert sufficient.status in {"ok", "insufficient_data"}
    if sufficient.status == "ok":
        assert sufficient.fold_count > 0


def test_ml_scoring_returns_insufficient_without_enough_data() -> None:
    score = score_signal_card(signal_card(), build_ml_dataset(research_rows=research_rows(3)))

    assert score.status == "insufficient_data"
    assert not score.ml_score_available


def test_ml_scoring_returns_probabilities_with_synthetic_data() -> None:
    score = score_signal_card(signal_card(), build_ml_dataset(research_rows=research_rows(14)))

    assert score.status == "ok"
    assert score.ml_score_available
    assert score.target_probabilities

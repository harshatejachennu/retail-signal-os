from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.models.backtester import BacktestResult
from backend.models.market_data import MarketBar
from backend.models.signal_card import SignalCard
from backend.research.ablation import run_ablation_tests
from backend.research.dataset import assemble_research_dataset
from backend.research.event_study import run_event_study
from backend.research.granger import run_granger_test
from backend.research.lead_lag import lead_lag_correlation
from backend.research.negative_controls import run_negative_control


def card(index: int, ticker: str = "AMD") -> SignalCard:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index)
    return SignalCard(
        ticker=ticker,
        timestamp=timestamp,
        direction="bullish",
        signal_strength=20 + index,
        trust_score=50 + index,
        manipulation_risk=10,
        late_hype_risk=5,
        contradiction_score=2,
        catalyst_score=15,
        data_quality_score=70,
        explanation="synthetic",
        what_could_go_wrong="synthetic",
    )


def result(index: int, ticker: str = "AMD") -> BacktestResult:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index)
    return BacktestResult(
        signal_id=f"{ticker}:{index}",
        ticker=ticker,
        signal_timestamp=timestamp,
        evaluated_at=timestamp + timedelta(days=4),
        return_1d=0.01 * index,
        return_3d=0.015 * index,
        spy_adjusted_return_1d=0.005 * index,
        spy_adjusted_return_3d=0.007 * index,
        qqq_adjusted_return_1d=0.004 * index,
        qqq_adjusted_return_3d=0.006 * index,
        notes="synthetic",
    )


def rows(count: int = 12) -> list[dict]:
    dataset = assemble_research_dataset(
        cards=[card(index) for index in range(count)],
        backtest_results=[result(index) for index in range(count)],
    )
    for index, row in enumerate(dataset):
        row["bullish_ratio"] = min(index / max(count - 1, 1), 1.0)
        row["bearish_ratio"] = 1.0 - row["bullish_ratio"]
        row["mention_count"] = index + 1
        row["control_return_1d"] = 0.02 if index % 2 == 0 else -0.01
    return dataset


def bar(ticker: str, timestamp: datetime, close: float) -> MarketBar:
    return MarketBar(
        ticker=ticker,
        timestamp=timestamp,
        open=close,
        high=close + 1,
        low=max(close - 1, 0.01),
        close=close,
        volume=1000,
        source="test",
    )


def test_research_dataset_assembles_and_handles_missing_fields() -> None:
    dataset = assemble_research_dataset(cards=[card(1)], backtest_results=[])

    assert len(dataset) == 1
    assert dataset[0]["ticker"] == "AMD"
    assert dataset[0]["return_1d"] is None
    assert "sentiment_score" in dataset[0]


def test_granger_insufficient_data_returns_status() -> None:
    output = run_granger_test(rows(3), "signal_strength", "return_1d", max_lag=2)

    assert output.status == "insufficient_data"
    assert output.interpretation == "insufficient_data"


def test_granger_synthetic_predictive_series_returns_p_values_without_causation_claim() -> None:
    output = run_granger_test(rows(14), "signal_strength", "return_1d", max_lag=2)

    assert output.p_values
    assert output.best_p_value is not None
    assert "true causation" in output.notes


def test_lead_lag_returns_correlations_by_lag() -> None:
    output = lead_lag_correlation(rows(10), "signal_strength", "return_3d", lags=[1, 2])

    assert output.status == "ok"
    assert set(output.correlations_by_lag) == {1, 2}


def test_lead_lag_handles_constant_series_safely() -> None:
    dataset = rows(10)
    for row in dataset:
        row["signal_strength"] = 1
    output = lead_lag_correlation(dataset, "signal_strength", "return_3d", lags=[1])

    assert output.correlations_by_lag[1] is None


def test_lead_lag_handles_insufficient_data() -> None:
    output = lead_lag_correlation(rows(2), "signal_strength", "return_3d", lags=[1, 2])

    assert output.status == "insufficient_data"


def test_event_study_calculates_post_event_return_and_handles_missing_benchmarks() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    test_card = card(0)
    ticker_bars = [
        bar("AMD", timestamp - timedelta(days=1), 90),
        bar("AMD", timestamp, 100),
        bar("AMD", timestamp + timedelta(days=1), 110),
    ]
    output = run_event_study(cards=[test_card], bars_by_ticker={"AMD": ticker_bars})

    assert output.signals_evaluated == 1
    assert output.average_post_event_return == 0.1
    assert output.average_abnormal_return_vs_spy is None


def test_negative_controls_return_warning_structure_and_insufficient_status() -> None:
    insufficient = run_negative_control(rows(3))
    enough = run_negative_control(rows(10))

    assert insufficient.status == "insufficient_data"
    assert enough.status == "ok"
    assert hasattr(enough, "warning")


def test_ablation_returns_insufficient_and_feature_group_structure() -> None:
    insufficient = run_ablation_tests(rows(3))
    enough = run_ablation_tests(rows(10))

    assert all(result.interpretation == "insufficient_data" for result in insufficient)
    assert {result.feature_group for result in enough} == {"social_strength", "risk", "catalyst", "quality"}

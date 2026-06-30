from __future__ import annotations

from backend.processing.pipeline import generate_signal_cards_from_events
from backend.simulation.demo_pipeline import DemoPipelineConfig, run_demo_pipeline
from backend.simulation.synthetic_history import generate_synthetic_history


def test_demo_pipeline_runs_full_synthetic_sequence(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'demo_pipeline.db'}"

    result = run_demo_pipeline(
        DemoPipelineConfig(days=20, signals=24, ticker="NVDA", reset_demo_data=True, save_ml_artifacts=False),
        database_url=database_url,
    )

    assert result["status"] == "ok"
    assert result["synthetic_demo"] is True
    assert "Synthetic demo data only" in result["warning"]
    assert result["generated_events"] == 24
    assert result["replay"]["status"] == "ok"
    assert result["signal_cards_generated"] > 0
    assert result["backtest_summary"]["signals_evaluated"] > 0
    assert result["explanation_available"] is True


def test_synthetic_signal_cards_label_demo_evidence() -> None:
    history = generate_synthetic_history(days=5, signals=5)

    generated = generate_signal_cards_from_events(history.events)

    assert generated
    assert all("Synthetic demonstration data only" in card.explanation for card in generated)
    assert all("synthetic demo data" in card.what_could_go_wrong.lower() for card in generated)


def test_demo_pipeline_reset_keeps_backtest_rows_consistent(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'demo_pipeline_reset.db'}"
    config = DemoPipelineConfig(days=20, signals=24, ticker="NVDA", reset_demo_data=True, save_ml_artifacts=False)

    first = run_demo_pipeline(config, database_url=database_url)
    second = run_demo_pipeline(config, database_url=database_url)

    assert first["synthetic_status"]["backtest_count"] == 24
    assert second["synthetic_status"]["backtest_count"] == 24
    assert first["synthetic_status"]["backtest_count"] == second["synthetic_status"]["backtest_count"]

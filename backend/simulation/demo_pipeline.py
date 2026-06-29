from __future__ import annotations

import argparse
from dataclasses import dataclass

from backend.agents.explanation_engine import explain_ticker
from backend.ml.training import run_training
from backend.models.backtester import backtest_signal_cards_from_database, backtest_summary
from backend.models.signal_engine import generate_signal_cards_from_database
from backend.research.validation import validation_summary
from backend.simulation.replay import replay_synthetic_events
from backend.simulation.synthetic_history import generate_synthetic_history, synthetic_status, write_synthetic_history


@dataclass(frozen=True)
class DemoPipelineConfig:
    days: int = 60
    signals: int = 100
    ticker: str = "NVDA"
    reset_demo_data: bool = True
    run_replay: bool = True
    save_ml_artifacts: bool = True


def run_demo_pipeline(config: DemoPipelineConfig | None = None, database_url: str | None = None) -> dict:
    """Run the deterministic local demo pipeline without paid APIs or live credentials."""
    config = config or DemoPipelineConfig()
    history = generate_synthetic_history(days=config.days, signals=config.signals)
    write_synthetic_history(history, reset_demo_data=config.reset_demo_data, database_url=database_url)

    replay = replay_synthetic_events(database_url=database_url) if config.run_replay else {"status": "skipped"}
    cards = generate_signal_cards_from_database(database_url)
    backtests = backtest_signal_cards_from_database(database_url)
    research = validation_summary(database_url=database_url)
    ml = run_training(save_artifacts=config.save_ml_artifacts, database_url=database_url)
    explanation = explain_ticker(config.ticker, database_url=database_url)
    status = synthetic_status(database_url=database_url)

    return {
        "status": "ok",
        "synthetic_demo": True,
        "warning": "Synthetic demo data only; not real market evidence or financial advice.",
        "generated_events": len(history.events),
        "generated_filings": len(history.filings),
        "generated_market_bars": len(history.market_bars),
        "replay": replay,
        "signal_cards_generated": len(cards),
        "backtest_summary": backtest_summary(backtests),
        "research_dataset_rows": research["dataset_rows"],
        "ml_dataset_rows": ml["dataset_rows"],
        "explanation_ticker": config.ticker.upper(),
        "explanation_available": explanation is not None,
        "synthetic_status": status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full deterministic RetailSignal OS synthetic demo pipeline.")
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--signals", type=int, default=100)
    parser.add_argument("--ticker", default="NVDA")
    parser.add_argument("--no-reset-demo-data", action="store_true", help="Append synthetic rows instead of clearing previous demo rows.")
    parser.add_argument("--skip-replay", action="store_true")
    parser.add_argument("--no-save-ml-artifacts", action="store_true")
    args = parser.parse_args()

    result = run_demo_pipeline(
        DemoPipelineConfig(
            days=args.days,
            signals=args.signals,
            ticker=args.ticker,
            reset_demo_data=not args.no_reset_demo_data,
            run_replay=not args.skip_replay,
            save_ml_artifacts=not args.no_save_ml_artifacts,
        )
    )
    print("RetailSignal OS full demo pipeline complete")
    print(result["warning"])
    print(f"generated synthetic events: {result['generated_events']}")
    print(f"generated synthetic SEC filings: {result['generated_filings']}")
    print(f"generated synthetic market bars: {result['generated_market_bars']}")
    print(f"replay status: {result['replay']['status']}")
    print(f"Signal Cards generated: {result['signal_cards_generated']}")
    print(f"backtest signals evaluated: {result['backtest_summary']['signals_evaluated']}")
    print(f"research dataset rows: {result['research_dataset_rows']}")
    print(f"ML dataset rows: {result['ml_dataset_rows']}")
    print(f"explanation for {result['explanation_ticker']} available: {result['explanation_available']}")


if __name__ == "__main__":
    main()

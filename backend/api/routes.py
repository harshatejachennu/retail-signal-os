from fastapi import APIRouter, HTTPException

from backend.agents.explanation_engine import agents_health as get_agents_health, explain_signal_card, explain_ticker
from backend.database.db import (
    connect,
    fetch_sec_filings,
    fetch_sec_filings_for_ticker,
    fetch_sec_filings_near_time,
    initialize,
)
from backend.features.catalyst import score_catalysts_for_signal
from backend.ml.models import feature_importance
from backend.ml.scoring import score_signal_card
from backend.ml.dataset import build_ml_dataset
from backend.ml.training import run_training
from backend.models.backtester import backtest_signal_cards_from_database, backtest_summary
from backend.models.signal_engine import (
    get_live_signal_cards,
    get_signal_card_for_ticker,
    get_signal_card_history,
)
from backend.research.event_study import run_event_study
from backend.research.validation import granger_for_ticker, validation_summary
from backend.simulation.demo_pipeline import DemoPipelineConfig, run_demo_pipeline
from backend.simulation.synthetic_history import (
    generate_synthetic_history,
    synthetic_status,
    write_synthetic_history,
)

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "retailsignal-os"}


@router.get("/signals/live")
def live_signals() -> list[dict]:
    return [card.model_dump(mode="json") for card in get_live_signal_cards()]


@router.get("/signals/{ticker}")
def signal_for_ticker(ticker: str) -> dict:
    card = get_signal_card_for_ticker(ticker)
    if card is None:
        raise HTTPException(status_code=404, detail=f"No Signal Card available for {ticker.upper()}")
    return card.model_dump(mode="json")


@router.get("/signals/{ticker}/history")
def signal_history(ticker: str) -> list[dict]:
    history = get_signal_card_history(ticker)
    if not history:
        raise HTTPException(status_code=404, detail=f"No Signal Card history available for {ticker.upper()}")
    return [card.model_dump(mode="json") for card in history]


@router.get("/research/backtest-summary")
def research_backtest_summary() -> dict:
    return backtest_summary(backtest_signal_cards_from_database())


@router.get("/signals/{ticker}/backtest")
def signal_backtest(ticker: str) -> list[dict]:
    results = [
        result.model_dump(mode="json")
        for result in backtest_signal_cards_from_database()
        if result.ticker == ticker.upper()
    ]
    if not results:
        raise HTTPException(status_code=404, detail=f"No backtest results available for {ticker.upper()}")
    return results


@router.get("/research/sec-filings")
def research_sec_filings() -> list[dict]:
    connection = connect()
    initialize(connection)
    try:
        return [filing.model_dump(mode="json") for filing in fetch_sec_filings(connection, limit=50)]
    finally:
        connection.close()


@router.get("/signals/{ticker}/catalysts")
def signal_catalysts(ticker: str) -> dict:
    card = get_signal_card_for_ticker(ticker)
    connection = connect()
    initialize(connection)
    try:
        if card is None:
            filings = fetch_sec_filings_for_ticker(connection, ticker)
            if not filings:
                raise HTTPException(status_code=404, detail=f"No SEC catalysts available for {ticker.upper()}")
            return {
                "ticker": ticker.upper(),
                "signal_available": False,
                "filings": [filing.model_dump(mode="json") for filing in filings],
                "catalyst_score": None,
                "catalyst_explanation": "SEC filings exist, but no Signal Card is available for matching.",
            }
        result = score_catalysts_for_signal(
            card,
            fetch_sec_filings_near_time(connection, card.ticker, card.timestamp),
        )
        return {
            "ticker": card.ticker,
            "signal_available": True,
            "catalyst_score": result.catalyst_score,
            "matched_filings": result.matched_filings,
            "catalyst_explanation": result.catalyst_explanation,
            "catalyst_limitations": result.catalyst_limitations,
        }
    finally:
        connection.close()


@router.get("/research/validation-summary")
def research_validation_summary() -> dict:
    return validation_summary()


@router.get("/research/granger/{ticker}")
def research_granger_ticker(ticker: str) -> dict:
    return granger_for_ticker(ticker)


@router.get("/research/event-study")
def research_event_study() -> dict:
    return run_event_study().model_dump(mode="json")


@router.get("/ml/summary")
def ml_summary() -> dict:
    return run_training(save_artifacts=False)


@router.get("/ml/feature-importance")
def ml_feature_importance() -> dict:
    dataset = build_ml_dataset()
    target = dataset.target_columns[0] if dataset.target_columns else "positive_return_3d"
    return feature_importance(dataset, target).model_dump(mode="json")


@router.get("/signals/{ticker}/ml-score")
def signal_ml_score(ticker: str) -> dict:
    card = get_signal_card_for_ticker(ticker)
    if card is None:
        return {
            "status": "insufficient_data",
            "ml_score_available": False,
            "target_probabilities": {},
            "confidence_level": "none",
            "warnings": [f"No Signal Card available for {ticker.upper()}."],
            "interpretation": "ML score unavailable.",
        }
    return score_signal_card(card).model_dump(mode="json")


@router.get("/agents/health")
def agents_health_endpoint() -> dict:
    return get_agents_health()


@router.get("/signals/{ticker}/explanation")
def signal_explanation(ticker: str) -> dict:
    report = explain_ticker(ticker)
    if report is None:
        return {
            "status": "insufficient_data",
            "ticker": ticker.upper(),
            "warnings": [f"No Signal Card available for {ticker.upper()}."],
            "not_financial_advice": "This endpoint is for educational research only and is not financial advice.",
        }
    return report.model_dump(mode="json")


@router.get("/signals/{ticker}/explanation/history")
def signal_explanation_history(ticker: str) -> dict:
    history = get_signal_card_history(ticker)
    if not history:
        return {
            "status": "insufficient_data",
            "ticker": ticker.upper(),
            "reports": [],
            "note": "No Signal Card history is available for explanation.",
        }
    return {
        "status": "ok",
        "ticker": ticker.upper(),
        "reports": [explain_signal_card(card).model_dump(mode="json") for card in history],
        "note": "Current storage exposes generated latest history only.",
    }


@router.get("/simulation/status")
def simulation_status() -> dict:
    return synthetic_status()


@router.get("/simulation/generate-demo-data")
def simulation_generate_demo_data(reset_demo_data: bool = False, days: int = 60, signals: int = 100) -> dict:
    if not reset_demo_data:
        return {
            "status": "requires_confirmation",
            "message": "Pass reset_demo_data=true to generate synthetic demo data through the API. Demo rows are not real market evidence.",
        }
    history = generate_synthetic_history(days=days, signals=signals)
    write_synthetic_history(history, reset_demo_data=True)
    return {"status": "ok", **synthetic_status()}


@router.get("/simulation/run-demo-pipeline")
def simulation_run_demo_pipeline(reset_demo_data: bool = False, days: int = 60, signals: int = 100, ticker: str = "NVDA") -> dict:
    if not reset_demo_data:
        return {
            "status": "requires_confirmation",
            "message": "Pass reset_demo_data=true to run the synthetic demo pipeline. Demo rows are not real market evidence.",
        }
    return run_demo_pipeline(DemoPipelineConfig(days=days, signals=signals, ticker=ticker, reset_demo_data=True))

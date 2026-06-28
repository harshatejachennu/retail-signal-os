from fastapi import APIRouter, HTTPException

from backend.models.backtester import backtest_signal_cards_from_database, backtest_summary
from backend.models.signal_engine import (
    get_live_signal_cards,
    get_signal_card_for_ticker,
    get_signal_card_history,
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

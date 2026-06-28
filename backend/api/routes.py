from fastapi import APIRouter, HTTPException

from backend.database.db import (
    connect,
    fetch_sec_filings,
    fetch_sec_filings_for_ticker,
    fetch_sec_filings_near_time,
    initialize,
)
from backend.features.catalyst import score_catalysts_for_signal
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

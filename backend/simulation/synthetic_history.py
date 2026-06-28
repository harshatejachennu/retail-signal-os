from __future__ import annotations

import argparse
import random
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from backend.database.db import (
    clear_demo_data,
    connect,
    fetch_events,
    initialize,
    insert_events,
    insert_market_bars,
    insert_sec_filings,
)
from backend.ingestion.sec_provider import ticker_to_cik
from backend.ml.dataset import build_ml_dataset
from backend.ml.training import run_training
from backend.models.backtester import backtest_signal_cards_from_database
from backend.models.market_data import MarketBar
from backend.models.sec_filing import SECFiling
from backend.models.signal_engine import generate_signal_cards_from_database
from backend.processing.events import Event
from backend.research.dataset import assemble_research_dataset
from backend.research.validation import validation_summary


SYNTHETIC_SEED = 42
SIGNAL_TICKERS = ["AAPL", "TSLA", "NVDA", "AMD", "MSFT", "COIN", "PLTR"]
MARKET_TICKERS = [*SIGNAL_TICKERS, "SPY", "QQQ"]
SCENARIOS = [
    "early_bullish_signal_success",
    "bullish_hype_failure",
    "bearish_signal_success",
    "manipulation_heavy_false_positive",
    "catalyst_confirmed_move",
    "no_catalyst_noise",
    "mixed_signal_unclear",
    "late_hype_reversal",
    "high_quality_dd_success",
    "options_gamble_noise",
]


@dataclass(frozen=True)
class SyntheticHistory:
    events: list[Event]
    filings: list[SECFiling]
    market_bars: list[MarketBar]


def generate_synthetic_history(days: int = 60, signals: int = 100, seed: int = SYNTHETIC_SEED) -> SyntheticHistory:
    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    scenarios = []
    for index in range(signals):
        scenarios.append(
            {
                "index": index,
                "ticker": SIGNAL_TICKERS[index % len(SIGNAL_TICKERS)],
                "scenario": SCENARIOS[index % len(SCENARIOS)],
                "event_time": start + timedelta(days=index % days, hours=10 + index % 5),
            }
        )
    events = [_event_for_scenario(item) for item in scenarios]
    filings = [_filing_for_scenario(item) for item in scenarios if _scenario_has_filing(item["scenario"])]
    market_bars = _generate_market_bars(start, days + 10, scenarios, rng)
    return SyntheticHistory(events=events, filings=filings, market_bars=market_bars)


def write_synthetic_history(history: SyntheticHistory, reset_demo_data: bool = False, database_url: str | None = None) -> None:
    connection = connect(database_url)
    initialize(connection)
    try:
        if reset_demo_data:
            clear_demo_data(connection)
        insert_events(connection, history.events)
        insert_sec_filings(connection, history.filings)
        insert_market_bars(connection, history.market_bars)
    finally:
        connection.close()


def synthetic_status(database_url: str | None = None) -> dict:
    connection = connect(database_url)
    initialize(connection)
    try:
        synthetic_events = connection.execute(
            "SELECT COUNT(*) AS count FROM events WHERE source = 'synthetic_reddit'"
        ).fetchone()["count"]
        synthetic_filings = connection.execute(
            "SELECT COUNT(*) AS count FROM sec_filings WHERE source = 'synthetic_sec'"
        ).fetchone()["count"]
        synthetic_bars = connection.execute(
            "SELECT COUNT(*) AS count FROM market_bars WHERE source = 'synthetic_market'"
        ).fetchone()["count"]
        backtests = connection.execute(
            "SELECT COUNT(*) AS count FROM backtest_results WHERE notes LIKE '%synthetic_demo%'"
        ).fetchone()["count"]
    finally:
        connection.close()
    cards = generate_signal_cards_from_database(database_url)
    research_rows = assemble_research_dataset(database_url=database_url)
    ml_dataset = build_ml_dataset(database_url=database_url)
    return {
        "synthetic": True,
        "synthetic_events": synthetic_events,
        "synthetic_filings": synthetic_filings,
        "synthetic_market_bars": synthetic_bars,
        "signal_count": len(cards),
        "backtest_count": backtests,
        "research_dataset_rows": len(research_rows),
        "ml_dataset_rows": len(ml_dataset.rows),
        "target_distribution": ml_dataset.target_distribution,
    }


def _event_for_scenario(item: dict) -> Event:
    ticker = item["ticker"]
    scenario = item["scenario"]
    text_by_scenario = {
        "early_bullish_signal_success": f"${ticker} bullish revenue growth and buying shares before breakout.",
        "bullish_hype_failure": f"${ticker} YOLO rocket moon all in, no thesis just vibes.",
        "bearish_signal_success": f"{ticker} looks overvalued and buying puts after weak guidance.",
        "manipulation_heavy_false_positive": f"{ticker} MOON MOON ROCKET guaranteed free money 🚀🚀🚀",
        "catalyst_confirmed_move": f"{ticker} 8-K catalyst watch, bullish thesis improving.",
        "no_catalyst_noise": f"{ticker} discussion is mixed with no clear catalyst.",
        "mixed_signal_unclear": f"{ticker} is undervalued but also faces margin pressure.",
        "late_hype_reversal": f"{ticker} late hype squeeze after huge run, paper hands risk.",
        "high_quality_dd_success": f"{ticker} revenue margins free cash flow valuation thesis looks strong.",
        "options_gamble_noise": f"{ticker} calls puts strike expiry premium IV gamble.",
    }
    event_time = item["event_time"]
    return Event(
        event_id=f"synthetic:{item['index']:04d}",
        source="synthetic_reddit",
        event_time=event_time,
        ingestion_time=event_time + timedelta(minutes=5),
        raw_text=text_by_scenario[scenario],
        confidence=0.85,
        raw_payload={"scenario": scenario, "synthetic": True},
    )


def _filing_for_scenario(item: dict) -> SECFiling:
    ticker = item["ticker"]
    cik = ticker_to_cik(ticker) or "0000000000"
    scenario = item["scenario"]
    form_type = "8-K" if "catalyst" in scenario or "success" in scenario else "10-Q"
    filed_at = item["event_time"] - timedelta(hours=8)
    accession = f"{cik}-{filed_at:%Y%m%d}-{item['index']:04d}"
    return SECFiling(
        filing_id=f"synthetic-sec:{ticker}:{item['index']:04d}",
        ticker=ticker,
        cik=cik,
        form_type=form_type,
        filed_at=filed_at,
        accepted_at=filed_at + timedelta(minutes=10),
        ingestion_time=filed_at + timedelta(minutes=12),
        accession_number=accession,
        filing_url=f"https://www.sec.gov/synthetic/{ticker}/{accession}",
        title=f"{ticker} synthetic {form_type}",
        summary=f"Synthetic {form_type} filing for {scenario}.",
        source="synthetic_sec",
        raw_payload={"scenario": scenario, "synthetic": True},
    )


def _generate_market_bars(start: datetime, days: int, scenarios: list[dict], rng: random.Random) -> list[MarketBar]:
    scenario_returns: dict[tuple[str, int], float] = {}
    for item in scenarios:
        day = (item["event_time"].date() - start.date()).days
        effect = _scenario_return_effect(item["scenario"])
        for offset in range(1, 4):
            key = (item["ticker"], day + offset)
            scenario_returns[key] = scenario_returns.get(key, 0.0) + effect / 3

    prices = {ticker: 80.0 + index * 18 for index, ticker in enumerate(MARKET_TICKERS)}
    bars: list[MarketBar] = []
    for day in range(days):
        timestamp = start + timedelta(days=day)
        for ticker in MARKET_TICKERS:
            benchmark_drift = 0.001 if ticker in {"SPY", "QQQ"} else 0.0005
            noise = ((day + len(ticker)) % 5 - 2) * 0.001
            ret = benchmark_drift + noise + scenario_returns.get((ticker, day), 0.0)
            if ticker not in {"SPY", "QQQ"}:
                ret += rng.choice([-0.001, 0.0, 0.001])
            open_price = prices[ticker]
            close = max(1.0, open_price * (1 + ret))
            high = max(open_price, close) * 1.01
            low = min(open_price, close) * 0.99
            bars.append(
                MarketBar(
                    ticker=ticker,
                    timestamp=timestamp,
                    open=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close, 2),
                    volume=500_000 + day * 1000 + len(ticker) * 10_000,
                    source="synthetic_market",
                    ingestion_time=timestamp + timedelta(minutes=2),
                )
            )
            prices[ticker] = close
    return bars


def _scenario_return_effect(scenario: str) -> float:
    return {
        "early_bullish_signal_success": 0.06,
        "bullish_hype_failure": -0.05,
        "bearish_signal_success": -0.06,
        "manipulation_heavy_false_positive": -0.04,
        "catalyst_confirmed_move": 0.08,
        "no_catalyst_noise": 0.0,
        "mixed_signal_unclear": 0.005,
        "late_hype_reversal": -0.07,
        "high_quality_dd_success": 0.07,
        "options_gamble_noise": 0.0,
    }[scenario]


def _scenario_has_filing(scenario: str) -> bool:
    return scenario in {"early_bullish_signal_success", "catalyst_confirmed_move", "high_quality_dd_success"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic history for demo/research mode.")
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--signals", type=int, default=100)
    parser.add_argument("--reset-demo-data", action="store_true")
    args = parser.parse_args()

    history = generate_synthetic_history(days=args.days, signals=args.signals)
    write_synthetic_history(history, reset_demo_data=args.reset_demo_data)
    cards = generate_signal_cards_from_database()
    backtests = backtest_signal_cards_from_database()
    research = validation_summary()
    ml_summary = run_training(save_artifacts=True)
    status = synthetic_status()
    print(f"generated events: {len(history.events)}")
    print(f"generated filings: {len(history.filings)}")
    print(f"generated market bars: {len(history.market_bars)}")
    print(f"generated Signal Cards: {len(cards)}")
    print(f"backtest rows: {len(backtests)}")
    print(f"research dataset rows: {research['dataset_rows']}")
    print(f"ML dataset rows: {status['ml_dataset_rows']}")
    print(f"target distribution: {ml_summary['target_availability']}")
    print("Synthetic data is for demonstration only and is not real market evidence.")


if __name__ == "__main__":
    main()

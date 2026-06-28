from __future__ import annotations

import argparse

from backend.agents.backtest_agent import BacktestAgent
from backend.agents.bear_agent import BearAgent
from backend.agents.bull_agent import BullAgent
from backend.agents.catalyst_agent import CatalystAgent
from backend.agents.manipulation_agent import ManipulationAgent
from backend.agents.ml_agent import MLAgent
from backend.agents.models import SignalExplanationReport
from backend.agents.research_agent import ResearchAgent
from backend.agents.risk_agent import RiskAgent
from backend.agents.synthesizer import Synthesizer
from backend.ml.scoring import score_signal_card
from backend.models.signal_card import SignalCard
from backend.models.signal_engine import get_signal_card_for_ticker
from backend.research.validation import validation_summary


AGENT_NAMES = [
    "BullAgent",
    "BearAgent",
    "CatalystAgent",
    "ManipulationAgent",
    "BacktestAgent",
    "MLAgent",
    "ResearchAgent",
    "RiskAgent",
    "Synthesizer",
]


def explain_signal_card(card: SignalCard, validation: dict | None = None, database_url: str | None = None) -> SignalExplanationReport:
    ml_score = score_signal_card(card)
    validation = validation if validation is not None else validation_summary(database_url=database_url)
    return Synthesizer().run(
        card=card,
        bull_case=BullAgent().run(card),
        bear_case=BearAgent().run(card),
        catalyst_analysis=CatalystAgent().run(card),
        manipulation_analysis=ManipulationAgent().run(card),
        backtest_analysis=BacktestAgent().run(card),
        ml_analysis=MLAgent().run(ml_score),
        research_validation_analysis=ResearchAgent().run(validation),
        risk_summary=RiskAgent().run(card),
    )


def explain_ticker(ticker: str, database_url: str | None = None) -> SignalExplanationReport | None:
    card = get_signal_card_for_ticker(ticker, database_url=database_url)
    if card is None:
        return None
    return explain_signal_card(card, database_url=database_url)


def agents_health() -> dict:
    return {
        "status": "ok",
        "mode": "deterministic_rule_based",
        "external_llm_calls": False,
        "agents": AGENT_NAMES,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic evidence-grounded Signal Card explanation.")
    parser.add_argument("--ticker", required=True)
    args = parser.parse_args()
    report = explain_ticker(args.ticker)
    if report is None:
        print(f"No Signal Card available for {args.ticker.upper()}.")
        return
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()

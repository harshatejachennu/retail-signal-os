from __future__ import annotations

from backend.agents.models import AgentReport, SignalExplanationReport
from backend.models.signal_card import SignalCard


class Synthesizer:
    def run(
        self,
        card: SignalCard,
        bull_case: AgentReport,
        bear_case: AgentReport,
        catalyst_analysis: AgentReport,
        manipulation_analysis: AgentReport,
        backtest_analysis: AgentReport,
        ml_analysis: AgentReport,
        research_validation_analysis: AgentReport,
        risk_summary: AgentReport,
    ) -> SignalExplanationReport:
        support = bull_case.summary
        weakness = bear_case.summary
        unknown = "Confidence would improve with more historical labeled signals, live-quality market data, and richer source coverage."
        final = (
            f"{card.ticker} has direction={card.direction}, signal_strength={card.signal_strength:.1f}, "
            f"trust_score={card.trust_score:.1f}, and catalyst_score={card.catalyst_score:.1f}. "
            f"Supportive view: {support} Weakening view: {weakness} Unknowns: {unknown} "
            "This is an evidence summary, not a trading instruction."
        )
        limitations = [
            "Uses only fields already stored on the Signal Card and local validation outputs.",
            "No external LLM or external analyst judgement is used.",
            "Mock data and small samples can make conclusions unstable.",
            "Catalyst matches, ML scores, and Granger-style checks do not prove causation.",
        ]
        return SignalExplanationReport(
            ticker=card.ticker,
            signal_timestamp=card.timestamp,
            bull_case=bull_case,
            bear_case=bear_case,
            catalyst_analysis=catalyst_analysis,
            manipulation_analysis=manipulation_analysis,
            backtest_analysis=backtest_analysis,
            ml_analysis=ml_analysis,
            research_validation_analysis=research_validation_analysis,
            risk_summary=risk_summary,
            final_interpretation=final,
            limitations=limitations,
            not_financial_advice="This report is for educational research only and is not financial advice.",
        )

from __future__ import annotations

from backend.agents.models import AgentFinding, AgentReport
from backend.models.signal_card import SignalCard


class RiskAgent:
    name = "RiskAgent"

    def run(self, card: SignalCard) -> AgentReport:
        risks = []
        if card.manipulation_risk >= 35:
            risks.append(f"manipulation_risk={card.manipulation_risk:.1f}")
        if card.late_hype_risk >= 35:
            risks.append(f"late_hype_risk={card.late_hype_risk:.1f}")
        if card.contradiction_score >= 35:
            risks.append(f"contradiction_score={card.contradiction_score:.1f}")
        if card.data_quality_score < 60:
            risks.append(f"data_quality_score={card.data_quality_score:.1f}")
        if not card.backtest_available:
            risks.append("missing_backtest_confirmation")
        if not card.ml_score_available:
            risks.append("missing_or_insufficient_ml_score")
        if not risks:
            risks.append("No major deterministic risk threshold was triggered.")
        severity = "high" if len(risks) >= 4 else "medium" if len(risks) >= 2 else "low"
        return AgentReport(
            agent_name=self.name,
            summary="Primary uncertainty and failure modes are summarized.",
            findings=[
                AgentFinding(
                    title="What could go wrong",
                    finding_type="risk_summary",
                    severity=severity,
                    evidence=risks,
                    limitation="Risk thresholds are simple deterministic rules and may miss important context.",
                    confidence=0.65,
                )
            ],
            warnings=[card.what_could_go_wrong],
        )

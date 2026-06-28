from __future__ import annotations

from backend.agents.models import AgentFinding, AgentReport
from backend.models.signal_card import SignalCard


class ManipulationAgent:
    name = "ManipulationAgent"

    def run(self, card: SignalCard) -> AgentReport:
        level = card.manipulation_risk_level or ("high" if card.manipulation_risk >= 70 else "medium" if card.manipulation_risk >= 35 else "low")
        severity = "high" if level == "high" else "medium" if level == "medium" else "low"
        evidence = [f"manipulation_risk={card.manipulation_risk:.1f}", f"risk_level={level}"]
        evidence.extend(card.manipulation_risk_reasons or ["No detailed manipulation reasons attached."])
        return AgentReport(
            agent_name=self.name,
            summary=f"Manipulation and hype risk is {level}.",
            findings=[
                AgentFinding(
                    title="Manipulation risk assessment",
                    finding_type="manipulation_risk",
                    severity=severity,
                    evidence=evidence,
                    limitation="This is a probabilistic risk indicator, not an accusation.",
                    confidence=0.7,
                )
            ],
            warnings=["Manipulation risk should not be treated as a factual accusation."],
        )

from __future__ import annotations

from backend.agents.models import AgentFinding, AgentReport
from backend.models.signal_card import SignalCard


class BullAgent:
    name = "BullAgent"

    def run(self, card: SignalCard) -> AgentReport:
        findings: list[AgentFinding] = []
        evidence = []
        if card.direction == "bullish":
            evidence.append(f"direction={card.direction}")
        if card.signal_strength >= 60:
            evidence.append(f"signal_strength={card.signal_strength:.1f}")
        if card.trust_score >= 60:
            evidence.append(f"trust_score={card.trust_score:.1f}")
        if card.catalyst_score >= 40:
            evidence.append(f"catalyst_score={card.catalyst_score:.1f}")
        if card.manipulation_risk < 35:
            evidence.append(f"manipulation_risk={card.manipulation_risk:.1f}")
        if card.return_3d is not None and card.return_3d > 0:
            evidence.append(f"return_3d={card.return_3d:.4f}")
        if evidence:
            findings.append(
                AgentFinding(
                    title="Supportive signal evidence",
                    finding_type="supportive",
                    severity="info",
                    evidence=evidence,
                    limitation="Supportive fields are descriptive and do not establish future outperformance.",
                    confidence=0.65,
                )
            )
        return AgentReport(
            agent_name=self.name,
            summary="Supportive evidence is present." if findings else "No strong supportive evidence was found.",
            findings=findings,
            warnings=[] if findings else ["Bull case is limited by weak or unavailable supportive fields."],
        )

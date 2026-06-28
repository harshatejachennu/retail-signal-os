from __future__ import annotations

from backend.agents.models import AgentFinding, AgentReport
from backend.models.signal_card import SignalCard


class BearAgent:
    name = "BearAgent"

    def run(self, card: SignalCard) -> AgentReport:
        evidence = []
        if card.direction == "bearish":
            evidence.append(f"direction={card.direction}")
        if card.manipulation_risk >= 50:
            evidence.append(f"manipulation_risk={card.manipulation_risk:.1f}")
        if card.data_quality_score < 50:
            evidence.append(f"data_quality_score={card.data_quality_score:.1f}")
        if card.late_hype_risk >= 50:
            evidence.append(f"late_hype_risk={card.late_hype_risk:.1f}")
        if card.trust_score < 45:
            evidence.append(f"trust_score={card.trust_score:.1f}")
        if card.return_3d is not None and card.return_3d < 0:
            evidence.append(f"return_3d={card.return_3d:.4f}")
        findings = [
            AgentFinding(
                title="Weakening or downside evidence",
                finding_type="risk",
                severity="medium" if evidence else "info",
                evidence=evidence or ["No major downside field crossed the deterministic thresholds."],
                limitation="Absence of flagged downside fields is not evidence that risk is low.",
                confidence=0.6 if evidence else 0.45,
            )
        ]
        return AgentReport(
            agent_name=self.name,
            summary="Risk or weak-evidence factors are present." if evidence else "No major bearish threshold was triggered.",
            findings=findings,
            warnings=[],
        )

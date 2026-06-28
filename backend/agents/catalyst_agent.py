from __future__ import annotations

from backend.agents.models import AgentFinding, AgentReport
from backend.models.signal_card import SignalCard


class CatalystAgent:
    name = "CatalystAgent"

    def run(self, card: SignalCard) -> AgentReport:
        if card.catalyst_events:
            evidence = [
                f"{event.get('form_type')} filed_at={event.get('filed_at')} title={event.get('title')}"
                for event in card.catalyst_events
            ]
            summary = f"Nearby SEC filing context exists with catalyst_score={card.catalyst_score:.1f}."
        else:
            evidence = [f"catalyst_score={card.catalyst_score:.1f}", "No matched SEC filings on this Signal Card."]
            summary = "No nearby SEC catalyst is attached to this Signal Card."
        return AgentReport(
            agent_name=self.name,
            summary=summary,
            findings=[
                AgentFinding(
                    title="SEC catalyst context",
                    finding_type="catalyst",
                    severity="info" if card.catalyst_score < 50 else "medium",
                    evidence=evidence,
                    limitation="A filing match provides context only and does not prove causation.",
                    confidence=0.7 if card.catalyst_events else 0.5,
                )
            ],
            warnings=["Catalyst match does not prove causation."],
        )

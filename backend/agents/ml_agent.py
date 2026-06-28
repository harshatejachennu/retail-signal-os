from __future__ import annotations

from backend.agents.models import AgentFinding, AgentReport
from backend.ml.results import MLSignalScore


class MLAgent:
    name = "MLAgent"

    def run(self, ml_score: MLSignalScore) -> AgentReport:
        if not ml_score.ml_score_available:
            return AgentReport(
                agent_name=self.name,
                summary="ML score is unavailable because the labeled dataset is insufficient.",
                findings=[
                    AgentFinding(
                        title="ML unavailable",
                        finding_type="ml",
                        severity="info",
                        evidence=ml_score.warnings or ["No trainable model output is available."],
                        limitation="More labeled historical Signal Cards are needed before model scoring is useful.",
                        confidence=0.55,
                    )
                ],
                warnings=ml_score.warnings,
            )
        evidence = [f"{target}={probability:.3f}" for target, probability in ml_score.target_probabilities.items()]
        return AgentReport(
            agent_name=self.name,
            summary=f"ML score is available with {ml_score.confidence_level} confidence.",
            findings=[
                AgentFinding(
                    title="ML probability context",
                    finding_type="ml",
                    severity="info",
                    evidence=evidence,
                    limitation="Model probabilities are estimates from historical data, not certainty.",
                    confidence=0.6,
                )
            ],
            warnings=ml_score.warnings,
        )

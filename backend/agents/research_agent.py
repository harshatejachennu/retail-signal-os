from __future__ import annotations

from backend.agents.models import AgentFinding, AgentReport


class ResearchAgent:
    name = "ResearchAgent"

    def run(self, validation_summary: dict) -> AgentReport:
        granger = validation_summary.get("granger_summary", {})
        lead_lag = validation_summary.get("lead_lag_summary", {})
        event_study = validation_summary.get("event_study_summary", {})
        evidence = [
            f"dataset_rows={validation_summary.get('dataset_rows')}",
            f"granger={granger.get('interpretation')}",
            f"lead_lag={lead_lag.get('interpretation')}",
            f"event_study_signals={event_study.get('signals_evaluated')}",
        ]
        return AgentReport(
            agent_name=self.name,
            summary="Research validation context is included for historical usefulness checks.",
            findings=[
                AgentFinding(
                    title="Research validation summary",
                    finding_type="research_validation",
                    severity="info",
                    evidence=evidence,
                    limitation="Granger-style testing and lead-lag checks do not prove true causation.",
                    confidence=0.6,
                )
            ],
            warnings=validation_summary.get("warnings", []) + ["Research validation does not prove true causation."],
        )

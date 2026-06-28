from __future__ import annotations

from backend.agents.models import AgentFinding, AgentReport
from backend.models.signal_card import SignalCard


class BacktestAgent:
    name = "BacktestAgent"

    def run(self, card: SignalCard) -> AgentReport:
        if not card.backtest_available:
            return AgentReport(
                agent_name=self.name,
                summary="Backtest data is unavailable or insufficient for this Signal Card.",
                findings=[
                    AgentFinding(
                        title="Missing backtest context",
                        finding_type="backtest",
                        severity="info",
                        evidence=[card.backtest_notes or "No usable forward return fields are attached."],
                        limitation="Missing backtest data prevents historical outcome context.",
                        confidence=0.5,
                    )
                ],
                warnings=["Backtests on mock or small datasets are educational only."],
            )
        evidence = []
        for label, value in [
            ("return_1d", card.return_1d),
            ("return_3d", card.return_3d),
            ("spy_adjusted_return_3d", card.spy_adjusted_return_3d),
            ("qqq_adjusted_return_3d", card.qqq_adjusted_return_3d),
        ]:
            if value is not None:
                evidence.append(f"{label}={value:.4f}")
        return AgentReport(
            agent_name=self.name,
            summary="Backtest outcome fields are available for historical context.",
            findings=[
                AgentFinding(
                    title="Historical forward return context",
                    finding_type="backtest",
                    severity="info",
                    evidence=evidence,
                    limitation="Backtest outcomes do not guarantee repeatability and may reflect mock data.",
                    confidence=0.65,
                )
            ],
            warnings=["Backtest context is not a prediction."],
        )

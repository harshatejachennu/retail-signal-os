from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["low", "medium", "high", "info"]


class AgentFinding(BaseModel):
    title: str
    finding_type: str
    severity: Severity
    evidence: list[str] = Field(default_factory=list)
    limitation: str
    confidence: float = Field(ge=0.0, le=1.0)


class AgentReport(BaseModel):
    agent_name: str
    summary: str
    findings: list[AgentFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SignalExplanationReport(BaseModel):
    ticker: str
    signal_timestamp: datetime
    bull_case: AgentReport
    bear_case: AgentReport
    catalyst_analysis: AgentReport
    manipulation_analysis: AgentReport
    backtest_analysis: AgentReport
    ml_analysis: AgentReport
    research_validation_analysis: AgentReport
    risk_summary: AgentReport
    final_interpretation: str
    limitations: list[str] = Field(default_factory=list)
    not_financial_advice: str

from __future__ import annotations

from datetime import datetime, timezone

from backend.agents.backtest_agent import BacktestAgent
from backend.agents.bear_agent import BearAgent
from backend.agents.bull_agent import BullAgent
from backend.agents.catalyst_agent import CatalystAgent
from backend.agents.explanation_engine import agents_health, explain_signal_card
from backend.agents.manipulation_agent import ManipulationAgent
from backend.agents.ml_agent import MLAgent
from backend.agents.models import AgentFinding, AgentReport, SignalExplanationReport
from backend.agents.research_agent import ResearchAgent
from backend.agents.risk_agent import RiskAgent
from backend.ml.results import MLSignalScore
from backend.models.signal_card import SignalCard


def sample_card(**overrides) -> SignalCard:
    data = {
        "ticker": "NVDA",
        "timestamp": datetime(2026, 1, 1, 14, 30, tzinfo=timezone.utc),
        "direction": "bullish",
        "signal_strength": 72.0,
        "trust_score": 68.0,
        "manipulation_risk": 18.0,
        "late_hype_risk": 20.0,
        "contradiction_score": 10.0,
        "catalyst_score": 55.0,
        "catalyst_events": [
            {
                "form_type": "8-K",
                "filed_at": "2026-01-01T13:00:00+00:00",
                "title": "NVDA 8-K",
                "summary": "Mock current report",
            }
        ],
        "data_quality_score": 78.0,
        "manipulation_risk_level": "low",
        "backtest_available": True,
        "return_1d": 0.02,
        "return_3d": 0.04,
        "spy_adjusted_return_3d": 0.01,
        "qqq_adjusted_return_3d": 0.005,
        "explanation": "Evidence is preliminary.",
        "what_could_go_wrong": "Mock data may be unrepresentative.",
    }
    data.update(overrides)
    return SignalCard(**data)


def validation_summary() -> dict:
    return {
        "dataset_rows": 12,
        "granger_summary": {"interpretation": "no_significant_predictive_signal"},
        "lead_lag_summary": {"interpretation": "insufficient_data"},
        "event_study_summary": {"signals_evaluated": 12},
        "warnings": ["Granger-style testing does not prove true causation."],
    }


def test_agent_models_serialize() -> None:
    finding = AgentFinding(
        title="Test",
        finding_type="info",
        severity="info",
        evidence=["field=value"],
        limitation="limited",
        confidence=0.5,
    )
    report = AgentReport(agent_name="Agent", summary="summary", findings=[finding])
    explanation = SignalExplanationReport(
        ticker="NVDA",
        signal_timestamp=sample_card().timestamp,
        bull_case=report,
        bear_case=report,
        catalyst_analysis=report,
        manipulation_analysis=report,
        backtest_analysis=report,
        ml_analysis=report,
        research_validation_analysis=report,
        risk_summary=report,
        final_interpretation="balanced",
        limitations=["limited"],
        not_financial_advice="not financial advice",
    )

    assert explanation.model_dump(mode="json")["ticker"] == "NVDA"


def test_bull_agent_detects_supportive_evidence() -> None:
    report = BullAgent().run(sample_card())

    assert report.findings
    assert "Supportive" in report.findings[0].title


def test_bear_agent_detects_weak_evidence_high_risk() -> None:
    report = BearAgent().run(
        sample_card(
            direction="bearish",
            manipulation_risk=75,
            late_hype_risk=70,
            trust_score=30,
            data_quality_score=35,
        )
    )

    assert report.findings[0].severity == "medium"
    assert any("manipulation_risk" in item for item in report.findings[0].evidence)


def test_catalyst_agent_includes_causation_limitation() -> None:
    report = CatalystAgent().run(sample_card())

    assert "does not prove causation" in report.findings[0].limitation


def test_manipulation_agent_reports_high_risk_reasons() -> None:
    report = ManipulationAgent().run(
        sample_card(
            manipulation_risk=85,
            manipulation_risk_level="high",
            manipulation_risk_reasons=["repeated hype words"],
        )
    )

    assert report.findings[0].severity == "high"
    assert "repeated hype words" in report.findings[0].evidence


def test_backtest_agent_handles_missing_backtest_data() -> None:
    report = BacktestAgent().run(sample_card(backtest_available=False, return_1d=None, return_3d=None))

    assert "unavailable" in report.summary


def test_ml_agent_handles_insufficient_data() -> None:
    report = MLAgent().run(
        MLSignalScore(
            status="insufficient_data",
            ml_score_available=False,
            confidence_level="none",
            warnings=["Need more rows."],
            interpretation="unavailable",
        )
    )

    assert "unavailable" in report.summary


def test_research_agent_includes_no_true_causation_limitation() -> None:
    report = ResearchAgent().run(validation_summary())

    assert "do not prove true causation" in report.findings[0].limitation


def test_risk_agent_summarizes_multiple_risks() -> None:
    report = RiskAgent().run(
        sample_card(
            manipulation_risk=60,
            late_hype_risk=70,
            contradiction_score=50,
            data_quality_score=40,
            backtest_available=False,
        )
    )

    assert report.findings[0].severity == "high"


def test_explanation_engine_generates_full_report() -> None:
    report = explain_signal_card(sample_card(), validation_summary())

    assert report.ticker == "NVDA"
    assert report.not_financial_advice
    assert report.bull_case.findings


def test_final_report_has_no_buy_or_sell_directive_language() -> None:
    report = explain_signal_card(sample_card(), validation_summary())
    lowered = report.final_interpretation.lower()

    assert " buy " not in f" {lowered} "
    assert " sell " not in f" {lowered} "
    assert "not financial advice" in report.not_financial_advice


def test_agents_health_structure() -> None:
    health = agents_health()

    assert health["status"] == "ok"
    assert health["external_llm_calls"] is False

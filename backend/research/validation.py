from __future__ import annotations

import argparse

from backend.research.ablation import run_ablation_tests
from backend.research.dataset import FEATURE_COLUMNS, TARGET_COLUMNS, assemble_research_dataset
from backend.research.event_study import run_event_study
from backend.research.granger import run_granger_test
from backend.research.lead_lag import lead_lag_correlation
from backend.research.negative_controls import run_negative_control


def validation_summary(database_url: str | None = None) -> dict:
    rows = assemble_research_dataset(database_url=database_url)
    granger = run_granger_test(rows, "signal_strength", "return_3d", max_lag=2)
    lead_lag = lead_lag_correlation(rows, "signal_strength", "return_3d", lags=[1, 2, 3])
    event_study = run_event_study(database_url=database_url)
    negative_control = run_negative_control(rows)
    ablation = run_ablation_tests(rows)
    warnings = [
        "Research validation is educational and does not prove true causation.",
        "Small samples, mock data, and repeated testing can produce misleading results.",
    ]
    for result in [granger, lead_lag, negative_control, *ablation]:
        status = getattr(result, "status", None) or getattr(result, "interpretation", None)
        if status == "insufficient_data":
            warnings.append(f"Insufficient data for {result.__class__.__name__}.")

    return {
        "dataset_rows": len(rows),
        "granger_summary": granger.model_dump(mode="json"),
        "lead_lag_summary": lead_lag.model_dump(mode="json"),
        "event_study_summary": event_study.model_dump(mode="json"),
        "negative_control_summary": negative_control.model_dump(mode="json"),
        "ablation_summary": [result.model_dump(mode="json") for result in ablation],
        "warnings": warnings,
    }


def granger_for_ticker(ticker: str, database_url: str | None = None) -> dict:
    rows = assemble_research_dataset(database_url=database_url)
    ticker_rows = [row for row in rows if row.get("ticker") == ticker.upper()]
    results = [
        run_granger_test(ticker_rows, feature, target, max_lag=2, ticker=ticker.upper()).model_dump(mode="json")
        for feature in FEATURE_COLUMNS
        for target in TARGET_COLUMNS[:2]
    ]
    return {
        "ticker": ticker.upper(),
        "dataset_rows": len(ticker_rows),
        "results": results,
        "notes": "Granger-style validation describes predictive usefulness in this dataset, not true causation.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run research validation checks for generated Signal Cards.")
    parser.parse_args()
    summary = validation_summary()
    tests_run = 4 + len(summary["ablation_summary"])
    insufficient = [warning for warning in summary["warnings"] if "Insufficient" in warning]
    print(f"rows in research dataset: {summary['dataset_rows']}")
    print(f"tests run: {tests_run}")
    print(f"warnings/insufficient data notices: {len(insufficient)}")
    print("top findings:")
    print(f"- Granger: {summary['granger_summary']['interpretation']} ({summary['granger_summary']['status']})")
    print(f"- Lead-lag: {summary['lead_lag_summary']['interpretation']} ({summary['lead_lag_summary']['status']})")
    print(f"- Event study signals: {summary['event_study_summary']['signals_evaluated']}")
    print("Reminder: results show only possible predictive usefulness in this dataset, not true causation.")


if __name__ == "__main__":
    main()

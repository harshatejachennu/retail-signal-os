# RetailSignal OS Portfolio Summary

## One-Paragraph Summary

RetailSignal OS is a production-style Python research platform for converting retail/social market discussion into explainable, testable Signal Cards. It demonstrates an end-to-end alternative-data workflow: mock/synthetic ingestion, conservative ticker resolution, sentiment/stance/intent extraction, manipulation-risk scoring, SEC catalyst matching, benchmark-adjusted backtesting, statistical validation, lightweight ML evaluation, deterministic agent explanations, a FastAPI API, and a Streamlit dashboard. The project is explicitly educational and avoids financial advice, real-money trading, external LLM calls, and unsupported stock-prediction claims.

## Technical Skills Demonstrated

- Python package organization with replaceable modules.
- FastAPI route design for health, signals, catalysts, backtests, validation, ML, explanations, and simulation status.
- SQLite-first persistence with an isolated database layer for future PostgreSQL migration.
- Streamlit dashboard development for demo and analysis workflows.
- Deterministic synthetic data generation and replay.
- CLI design for repeatable local workflows.
- Pytest coverage for processing, ingestion, simulation, API, backtesting, research, ML, and agent behavior.
- Safety-oriented product constraints and clear user-facing disclaimers.

## AI / ML / Data Science Concepts Demonstrated

- Separation of sentiment, market stance, and intent.
- Feature engineering from text, source confidence, risk scores, catalysts, and backtest outcomes.
- Point-in-time validation using `event_time` and `ingestion_time`.
- Manipulation-risk scoring as a probabilistic risk signal.
- SPY/QQQ-adjusted outcome evaluation.
- Granger-style predictive-usefulness testing.
- Lead-lag correlation analysis.
- Event-study summaries.
- Negative controls to detect spurious relationships.
- Ablation testing across feature groups.
- Time-based model splits and walk-forward validation.
- Baseline, logistic regression, and random-forest style evaluation.
- Deterministic, evidence-grounded agent explanations without external LLM hallucination risk.

## Backend / API Skills Demonstrated

- FastAPI router organization and typed response payloads.
- Pydantic models for Signal Cards, market bars, SEC filings, backtest results, ML outputs, and explanation reports.
- SQLite schema management and insertion/fetch helpers.
- Provider interfaces for mock-first Reddit, market, and SEC data modes.
- CLI entry points for ingestion, simulation, replay, backtesting, validation, ML training, and explanations.
- Guarded demo endpoints that require explicit confirmation before mutating demo data.
- Testable functions that accept optional database URLs for isolated temporary test databases.

## Future Improvements

- Add a larger real historical dataset with compliant licensing and point-in-time availability metadata.
- Improve ticker resolution with exchange-aware symbol metadata and ambiguity handling.
- Replace deterministic placeholder sentiment with validated finance-domain NLP models.
- Add richer source quality features while avoiding factual accusations about manipulation.
- Expand walk-forward validation and out-of-sample reporting.
- Add calibrated probability estimates and model cards for ML outputs.
- Add durable Signal Card outcome tracking over longer horizons.
- Add role-specific dashboard views for research, model evaluation, and data health.
- Migrate from SQLite to PostgreSQL when multi-user or larger-scale workflows require it.

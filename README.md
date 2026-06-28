# RetailSignal OS

RetailSignal OS is an initial production-style foundation for a real-time alternative-data stock signal research platform. It is designed to ingest public signals, extract tickers and narratives, score risk and signal features, generate explainable Signal Cards, and later validate those signals through rigorous research workflows.

## What It Is Not

RetailSignal OS is not a real-money trading bot and does not provide financial advice. It is a research and paper-trading platform. Signals are uncertain research artifacts, not guaranteed predictions.

## Architecture

- `backend/api`: FastAPI app with health and sample signal endpoints.
- `backend/database`: SQLite schema and connection helper, structured for a later PostgreSQL migration.
- `backend/ingestion`: Placeholder providers for Reddit, market data, and SEC filings.
- `backend/processing`: Unified events, ticker resolution, sentiment, and manipulation risk scoring.
- `backend/features`: Rolling z-score, exponential time decay, and feature store placeholder.
- `backend/models`: Signal Card model and placeholder signal engine.
- `dashboard`: Streamlit dashboard for sample Signal Cards and future pages.
- `research`: Research and validation workspace.
- `tests`: Pytest coverage for core behavior.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Run Tests

```bash
pytest
```

## Run API

```bash
uvicorn backend.api.main:app --reload
```

Then open `http://127.0.0.1:8000/health` or `http://127.0.0.1:8000/signals/live`.

## Run Dashboard

```bash
streamlit run dashboard/app.py
```

## Roadmap

- Add real source ingestion only after the foundation is tested.
- Expand ticker resolution with exchange-aware symbol metadata.
- Replace placeholder sentiment with VADER, FinBERT, or a finance-specific classifier.
- Add market stance extraction separately from sentiment.
- Add persistent event and Signal Card storage.
- Add backtests, event studies, negative controls, ablations, and walk-forward validation.
- Add outcome tracking to Signal Cards.

## Disclaimer

This project is for research and educational use only. It is not financial advice, investment advice, or a recommendation to buy or sell securities.

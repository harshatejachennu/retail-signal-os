# RetailSignal OS

RetailSignal OS is an initial production-style foundation for a real-time alternative-data stock signal research platform. It is designed to ingest public signals, extract tickers and narratives, score risk and signal features, generate explainable Signal Cards, and later validate those signals through rigorous research workflows.

## What It Is Not

RetailSignal OS is not a real-money trading bot and does not provide financial advice. It is a research and paper-trading platform. Signals are uncertain research artifacts, not guaranteed predictions.

## Architecture

- `backend/api`: FastAPI app with health and sample signal endpoints.
- `backend/database`: SQLite schema and connection helper, structured for a later PostgreSQL migration.
- `backend/ingestion`: Mock-first Reddit, market data, and SEC providers.
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

## Reddit Ingestion

Reddit ingestion defaults to compliant mock mode, so local development and tests do not require Reddit API credentials:

```bash
python3 -m backend.ingestion.reddit_provider --limit 25
```

Real Reddit API mode is optional and uses PRAW only when `REDDIT_INGESTION_MODE=praw` and credentials are available in `.env`. Reddit API access may require developer registration or approval under Reddit's Responsible Builder Policy, Developer Terms, and Data API Terms. Use a truthful, descriptive `REDDIT_USER_AGENT`, respect Reddit rate limits and deletion/removal obligations, and do not redistribute raw Reddit content publicly. This project is for non-commercial educational research.

## Market Data And Backtesting

Market data defaults to deterministic mock mode and does not require paid APIs:

```bash
python3 -m backend.ingestion.market_data_provider --tickers AAPL,TSLA,NVDA,AMD,SPY,QQQ --days 10
python3 -m backend.models.backtester
```

Set `MARKET_DATA_MODE=mock` for offline development. Optional `MARKET_DATA_MODE=yfinance` is isolated behind the provider interface; if `yfinance` is unavailable or network access fails, use mock mode. Market data sources can have usage restrictions, licensing terms, and redistribution limits.

Backtests are educational research outputs only. They evaluate generated Signal Cards against stored future OHLCV bars and SPY/QQQ benchmarks, but they are not trading advice and do not prove causality.

## SEC Filings And Catalysts

SEC filings default to deterministic mock mode:

```bash
python3 -m backend.ingestion.sec_provider --tickers AAPL,TSLA,NVDA,AMD,MSFT,COIN,PLTR --days 30
```

Set `SEC_DATA_MODE=mock` for offline development and tests. Real SEC mode is optional with `SEC_DATA_MODE=real` and requires a descriptive `SEC_USER_AGENT` with contact information, for example `RetailSignalOS/0.1 contact:YOUR_EMAIL@example.com`. SEC EDGAR automated access has fair-access limits; request only what is needed, identify the client clearly, and avoid aggressive polling.

Catalyst scoring matches stored SEC filings near a Signal Card timestamp. A nearby 8-K, Form 4, 10-Q, or 10-K can raise `catalyst_score`, but the match is contextual only and does not prove the filing caused Reddit sentiment or any price move.

## Research Validation

Run the research validation layer after generating signals, market bars, and backtests:

```bash
python3 -m backend.research.validation
```

Validation asks whether past signal features helped forecast later returns in the stored dataset. Granger causality here means Granger-style predictive usefulness: past values of a feature may improve forecasting of a target series in this dataset. It does not mean true economic causation.

Lead-lag correlation compares feature values with future return series at configurable lags. Event studies summarize returns before and after Signal Card timestamps and abnormal returns versus SPY/QQQ when benchmarks exist. Negative controls compare features against unrelated returns to detect spurious relationships or leakage. Ablation tests compare simple feature-group metrics with and without social, risk, catalyst, and quality groups.

Avoid p-hacking and overclaiming: repeated tests on small or mock datasets can look meaningful by chance. Treat all validation outputs as educational research diagnostics, not financial advice or proof of a tradable edge.

## ML Signal Scoring

Run lightweight ML training and evaluation after generating signals and backtests:

```bash
python3 -m backend.ml.training
```

The ML layer estimates whether historical Signal Card features were associated with future outperformance targets such as SPY-adjusted 3-day return, QQQ-adjusted 3-day return, or positive 3-day return. It compares a majority-class baseline, logistic regression, and random forest style classifier, and reports feature importance when enough labeled rows exist.

The ML layer does not issue buy/sell instructions, guarantee prediction, or prove causality. It uses only features available at the Signal Card timestamp and excludes future return columns from model features to reduce target leakage.

Time-based splits are used because older observations should train the model and newer observations should test it. Walk-forward validation repeats that idea over rolling chronological windows. Small samples, mock data, class imbalance, overfitting, and repeated experimentation can all produce misleading results, so treat outputs as educational diagnostics only.

## Evidence-Grounded Explanations

Signal Card explanations are generated by deterministic, rule-based agents:

```bash
python3 -m backend.agents.explanation_engine --ticker NVDA
```

The explanation layer does not call external LLM APIs and does not use a generative model that can invent facts. Each section is grounded in existing Signal Card fields, catalyst matches, backtest fields, ML status, and research validation summaries. The agents produce bull-case, bear-case, catalyst, manipulation, backtest, ML, research, and risk sections, then a balanced final interpretation.

These reports explain evidence already inside the system. They do not make trading decisions, do not prove causation, and are not financial advice. Use `GET /signals/{ticker}/explanation`, `GET /signals/{ticker}/explanation/history`, and `GET /agents/health`, or open the Streamlit `Signal Explanation` page.

## Synthetic History And Replay

Synthetic history exists so the research validation and ML layers can be demonstrated without real Reddit credentials, real SEC network access, or paid market data:

```bash
python3 -m backend.simulation.synthetic_history --days 60 --signals 100 --reset-demo-data
python3 -m backend.simulation.replay --start 2026-01-01 --end 2026-03-31
```

The generator creates deterministic synthetic Reddit-like events, SEC-like filings, and market bars across multiple tickers and scenarios. It labels sources as `synthetic_reddit`, `synthetic_sec`, and `synthetic_market`. Synthetic outcomes are useful for testing Granger-style validation, lead-lag checks, ML target classes, and replay behavior, but they are not real market evidence.

Replay mode reads synthetic events in ingestion-time order and rebuilds available Signal Cards over time without looking ahead. Use the Streamlit `Demo Data / Replay` page or `GET /simulation/status` to inspect synthetic row counts.

Full demo pipeline:

```bash
python3 -m backend.simulation.synthetic_history --days 60 --signals 100 --reset-demo-data
python3 -m backend.research.validation
python3 -m backend.ml.training
python3 -m backend.agents.explanation_engine --ticker NVDA
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

- Expand source ingestion only after the foundation is tested.
- Expand ticker resolution with exchange-aware symbol metadata.
- Replace placeholder sentiment with VADER, FinBERT, or a finance-specific classifier.
- Add market stance extraction separately from sentiment.
- Add persistent event and Signal Card storage.
- Add backtests, event studies, negative controls, ablations, and walk-forward validation.
- Add outcome tracking to Signal Cards.

## Disclaimer

This project is for research and educational use only. It is not financial advice, investment advice, or a recommendation to buy or sell securities.

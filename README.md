# RetailSignal OS

RetailSignal OS is a production-style research platform for turning retail/social market chatter into explainable, testable **Signal Cards**. It ingests Reddit-like events, resolves tickers, separates text sentiment from market stance and intent, scores manipulation risk, checks market and SEC-style context, validates historical outcomes, evaluates lightweight ML models, and explains the result through deterministic rule-based agents.

It is intentionally **not** a stock-prediction shortcut. The project is designed to show how a serious alternative-data system should expose evidence, uncertainty, risk, validation results, and limitations instead of claiming guaranteed alpha.

## Why This Is More Than A Reddit Sentiment Tracker

A simple sentiment tracker usually stops at “people sound positive or negative about a ticker.” RetailSignal OS goes further by asking whether the signal is explainable, risky, testable, and time-valid:

- **Ticker resolution:** detects cashtags, conservative uppercase symbols, and common company names while avoiding false positives.
- **Sentiment vs market stance vs intent:** separates tone from implied market direction and user intent such as serious DD, meme hype, options gambling, or news reaction.
- **Manipulation-risk scoring:** treats hype, emoji density, repeated claims, and multi-ticker spam as probabilistic risk indicators, not accusations.
- **Signal Cards:** every signal is packaged with evidence, uncertainty, risk, catalyst context, backtest fields, ML status, and “what could go wrong.”
- **Point-in-time discipline:** events store both `event_time` and `ingestion_time` to reduce look-ahead bias.
- **Validation stack:** includes SPY/QQQ-adjusted backtesting, event-study style summaries, Granger-style predictive tests, lead-lag checks, negative controls, ablation tests, and ML evaluation with time-based splits.
- **Deterministic explanations:** rule-based agents summarize bull, bear, catalyst, manipulation, backtest, ML, research, and risk evidence without external LLM calls or hallucinated facts.

## Quickstart Demo

The demo is fully offline and deterministic. It does **not** require Reddit credentials, live SEC access, paid market data, or external LLM APIs.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python3 -m backend.simulation.demo_pipeline --days 60 --signals 100 --ticker NVDA
```

Start the API:

```bash
uvicorn backend.api.main:app --reload
```

Start the dashboard in another terminal:

```bash
streamlit run dashboard/app.py
```

Useful demo endpoints:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/signals/live`
- `http://127.0.0.1:8000/signals/NVDA/explanation`
- `http://127.0.0.1:8000/research/backtest-summary`
- `http://127.0.0.1:8000/research/validation-summary`
- `http://127.0.0.1:8000/ml/summary`
- `http://127.0.0.1:8000/simulation/status`

Run tests:

```bash
pytest
```

## Architecture

RetailSignal OS follows this pipeline:

```text
Social/Reddit-like events
→ ticker resolver
→ sentiment / market stance / intent
→ manipulation risk
→ Signal Cards
→ market data / backtesting
→ SEC catalysts
→ research validation
→ ML evaluation
→ deterministic agent explanations
→ dashboard / API
```

Implementation map:

- `backend/api`: FastAPI app with health, signal, catalyst, backtest, validation, ML, explanation, and simulation routes.
- `backend/database`: SQLite schema and connection helpers, isolated so PostgreSQL can replace it later.
- `backend/ingestion`: Mock-first Reddit, market data, and SEC providers with optional real modes behind interfaces.
- `backend/processing`: unified events, ticker resolution, sentiment/stance/intent, manipulation risk, and Signal Card generation pipeline.
- `backend/features`: rolling z-score, time decay, catalyst scoring, and feature-store placeholder.
- `backend/models`: Signal Card model, signal engine, market bars, SEC filings, and backtester.
- `backend/research`: validation datasets, Granger-style checks, lead-lag correlation, event studies, negative controls, and ablations.
- `backend/ml`: time-based splits, baseline/logistic/random-forest style evaluation, walk-forward validation, scoring, and feature importance.
- `backend/agents`: deterministic rule-based explanation agents; no external LLM calls.
- `backend/simulation`: synthetic history, replay, and the full demo pipeline.
- `dashboard`: Streamlit demo dashboard.
- `docs`: portfolio/demo walkthrough material.
- `tests`: pytest coverage for core behavior.

## Full Demo Pipeline

Use this single command for a complete local presentation:

```bash
python3 -m backend.simulation.demo_pipeline --days 60 --signals 100 --ticker NVDA
```

The pipeline runs:

1. Reset and generate deterministic synthetic Reddit-like events, SEC-like filings, and market bars.
2. Replay synthetic events in `ingestion_time` order.
3. Generate Signal Cards.
4. Run SPY/QQQ-aware educational backtests.
5. Run research validation diagnostics.
6. Train/evaluate lightweight ML scoring models.
7. Generate a deterministic evidence-grounded explanation for the chosen ticker.

Synthetic rows are clearly labeled with sources such as `synthetic_reddit`, `synthetic_sec`, and `synthetic_market`. Synthetic outcomes are useful for demonstrating pipeline behavior, replay, tests, dashboard states, validation plumbing, and ML target creation. They are **not real market evidence** and should not be used to claim predictive power.

To inspect stages manually:

```bash
python3 -m backend.simulation.synthetic_history --days 60 --signals 100 --reset-demo-data
python3 -m backend.simulation.replay --start 2026-01-01 --end 2026-03-31
python3 -m backend.models.signal_engine
python3 -m backend.models.backtester
python3 -m backend.research.validation
python3 -m backend.ml.training
python3 -m backend.agents.explanation_engine --ticker NVDA
```

## What Makes This Advanced

- **`event_time` vs `ingestion_time`:** stores when an event happened and when the system observed it, so historical features can avoid look-ahead bias.
- **Signal Cards:** converts every detected signal into a structured artifact with evidence, uncertainty, manipulation risk, catalyst context, backtest status, ML status, explanation, and downside reasoning.
- **Manipulation risk:** models hype/spam/manipulation indicators as a probabilistic risk score rather than a factual accusation.
- **Synthetic replay mode:** rebuilds signals through time from synthetic events in ingestion order to demonstrate point-in-time behavior.
- **SEC catalyst matching:** matches stored SEC-style filings near Signal Card timestamps to provide contextual catalyst evidence without claiming causation.
- **SPY/QQQ-adjusted backtesting:** compares forward returns with market/tech benchmarks instead of reporting raw returns alone.
- **Granger-style validation:** tests whether past feature values have predictive usefulness for later target series in the stored dataset.
- **Lead-lag correlation:** compares feature values with future returns at configurable lags.
- **Negative controls:** checks unrelated targets to reveal spurious relationships or leakage risk.
- **Ablation testing:** compares feature groups with and without social, risk, catalyst, and quality signals.
- **ML with time-based split:** evaluates simple classifiers chronologically so older rows train and newer rows test.
- **Deterministic agent explanations:** generates bull, bear, catalyst, manipulation, backtest, ML, research, and risk summaries using existing fields only.
- **No external LLM hallucination risk:** explanation agents are rule-based and do not call generative APIs.

## Optional Real Data Modes

Local development defaults to mock/synthetic data. Optional real modes are isolated behind provider interfaces and are not required for the demo.

### Reddit Ingestion

Mock Reddit ingestion requires no credentials:

```bash
python3 -m backend.ingestion.reddit_provider --limit 25
```

Real Reddit API mode is optional and uses PRAW only when `REDDIT_INGESTION_MODE=praw` and credentials are available in `.env`. Reddit API access may require developer registration or approval under Reddit policies. Use a truthful `REDDIT_USER_AGENT`, respect rate limits and deletion/removal obligations, and do not redistribute raw Reddit content publicly.

### Market Data And Backtesting

Market data defaults to deterministic mock mode and does not require paid APIs:

```bash
python3 -m backend.ingestion.market_data_provider --tickers AAPL,TSLA,NVDA,AMD,SPY,QQQ --days 10
python3 -m backend.models.backtester
```

Set `MARKET_DATA_MODE=mock` for offline development. Optional `MARKET_DATA_MODE=yfinance` is isolated behind the market data provider; if `yfinance` is unavailable or network access fails, use mock mode. Market data sources can have usage restrictions, licensing terms, and redistribution limits.

### SEC Filings And Catalysts

SEC filings default to deterministic mock mode:

```bash
python3 -m backend.ingestion.sec_provider --tickers AAPL,TSLA,NVDA,AMD,MSFT,COIN,PLTR --days 30
```

Set `SEC_DATA_MODE=mock` for offline development and tests. Optional `SEC_DATA_MODE=real` requires a descriptive `SEC_USER_AGENT` with contact information, for example `RetailSignalOS/0.1 contact:YOUR_EMAIL@example.com`. SEC EDGAR automated access has fair-access limits; request only what is needed and avoid aggressive polling.

Catalyst scoring matches stored SEC filings near a Signal Card timestamp. A nearby 8-K, Form 4, 10-Q, or 10-K can raise `catalyst_score`, but the match is contextual only and does not prove the filing caused social sentiment or a price move.

## Research Validation

Run validation after generating signals, market bars, and backtests:

```bash
python3 -m backend.research.validation
```

Validation asks whether past signal features helped forecast later returns in the stored dataset. Granger-style testing means predictive usefulness in this dataset; it does **not** prove true economic causation. Lead-lag correlation, event studies, negative controls, and ablations are educational diagnostics that help detect fragile patterns, leakage, or overfitting.

## ML Signal Scoring

Run lightweight ML training and evaluation after generating signals and backtests:

```bash
python3 -m backend.ml.training
```

The ML layer estimates whether historical Signal Card features were associated with future outperformance targets such as SPY-adjusted 3-day return, QQQ-adjusted 3-day return, or positive 3-day return. It compares a majority-class baseline, logistic regression, and random forest style classifier, reports feature importance when enough labeled rows exist, and uses time-based splits to reduce target leakage.

## Evidence-Grounded Explanations

Signal Card explanations are generated by deterministic, rule-based agents:

```bash
python3 -m backend.agents.explanation_engine --ticker NVDA
```

The explanation layer does not call external LLM APIs and does not use a generative model that can invent facts. Each section is grounded in existing Signal Card fields, catalyst matches, backtest fields, ML status, and research validation summaries. Use `GET /signals/{ticker}/explanation`, `GET /signals/{ticker}/explanation/history`, `GET /agents/health`, or the Streamlit `Signal Explanation` page.

## Limitations And Safety

- Synthetic/demo data is not real market evidence.
- RetailSignal OS is not financial advice, investment advice, or a recommendation to buy or sell securities.
- The project does not automate order execution, broker integration, or real-money trading.
- Reddit API access may require approval and must follow Reddit terms, rate limits, and data handling obligations.
- Optional real SEC mode requires proper identification and respectful fair-access behavior.
- Real model conclusions require real historical data, careful sampling, and out-of-sample validation before any research claims are credible.
- Granger-style testing can show predictive usefulness in a dataset, but it does not prove true causation.
- Backtests are educational diagnostics and can be misleading because of small samples, synthetic data, overfitting, transaction costs, slippage, missing data, and repeated experimentation.

## Roadmap

- Improve source ingestion only after mock/synthetic foundations are tested.
- Expand ticker resolution with exchange-aware symbol metadata.
- Replace placeholder sentiment with VADER, FinBERT, or a finance-specific classifier when appropriate.
- Add richer account/source quality signals without making factual accusations.
- Add persistent outcome tracking for every Signal Card.
- Add larger walk-forward and out-of-sample validation workflows.
- Keep PostgreSQL migration possible by preserving the isolated database layer.

## Disclaimer

This project is for research and educational use only. It is not financial advice, investment advice, or a recommendation to buy or sell securities. It does not claim guaranteed stock prediction or deterministic alpha.

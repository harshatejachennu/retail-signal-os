# RetailSignal OS

RetailSignal OS is a production-style research platform for turning retail/social market chatter into explainable, testable **Signal Cards**. It ingests Reddit-like events, resolves tickers, separates text sentiment from market stance and intent, scores manipulation risk, adds market and SEC-style context, validates outcomes, evaluates lightweight ML models, and explains results through deterministic rule-based agents.

The project is built to demonstrate how a serious alternative-data workflow should handle evidence, uncertainty, time validity, validation, and limitations. It is intentionally cautious: the goal is not to claim guaranteed stock prediction, but to show how signals can be structured, tested, and explained responsibly.

## What It Is Not

- Not a real-money trading bot.
- Not a broker integration or order-execution system.
- Not financial advice, investment advice, or a recommendation to buy or sell securities.
- Not a claim that Reddit/social chatter can reliably predict stocks.
- Not dependent on real Reddit credentials, live SEC access, paid APIs, or external LLM calls for the demo.

## Why This Is More Than A Reddit Sentiment Tracker

A simple sentiment tracker usually stops at “people sound positive or negative about a ticker.” RetailSignal OS goes further by asking whether each signal is explainable, risky, testable, and time-valid:

- **Ticker resolution:** detects cashtags, conservative uppercase symbols, and common company names while avoiding common false positives.
- **Sentiment, stance, and intent:** separates text tone from market direction and user intent such as serious DD, meme hype, options gambling, or news reaction.
- **Manipulation risk:** scores hype/spam-like behavior as a probabilistic risk signal, not a factual accusation.
- **Signal Cards:** packages every detected signal with evidence, uncertainty, risk, catalyst context, backtest fields, ML status, explanation, and “what could go wrong.”
- **Point-in-time discipline:** stores both `event_time` and `ingestion_time` so historical features can avoid look-ahead bias.
- **Validation stack:** includes benchmark-adjusted backtesting, Granger-style diagnostics, lead-lag checks, negative controls, ablation tests, and time-based ML evaluation.
- **Deterministic explanations:** summarizes evidence with rule-based agents and no external LLM hallucination risk.

## Architecture Pipeline

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

- `backend/api`: FastAPI routes for health, signals, catalysts, backtests, validation, ML, explanations, and simulation status.
- `backend/database`: SQLite-first schema and helpers, isolated for a future PostgreSQL migration.
- `backend/ingestion`: Mock-first Reddit, market data, and SEC providers with optional real modes behind interfaces.
- `backend/processing`: unified events, ticker resolution, sentiment/stance/intent, manipulation risk, and Signal Card generation.
- `backend/features`: rolling z-score, time decay, catalyst scoring, and feature-store placeholder.
- `backend/models`: Signal Cards, market bars, SEC filings, signal engine, and backtester.
- `backend/research`: validation datasets, Granger-style checks, lead-lag correlation, event studies, negative controls, and ablations.
- `backend/ml`: target datasets, time-based splits, baseline/model evaluation, walk-forward validation, scoring, and feature importance.
- `backend/agents`: deterministic evidence-grounded explanation agents.
- `backend/simulation`: synthetic history, ingestion-time replay, and full demo pipeline.
- `dashboard`: Streamlit demo dashboard.
- `docs`: demo walkthrough and portfolio summary.
- `tests`: pytest coverage for core behavior.

## Quickstart Demo

The demo is fully offline and deterministic.

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

## Full Demo Pipeline

Use one command for a complete local presentation:

```bash
python3 -m backend.simulation.demo_pipeline --days 60 --signals 100 --ticker NVDA
```

The pipeline runs:

1. Generate deterministic synthetic Reddit-like events, SEC-like filings, and market bars.
2. Replay synthetic events in `ingestion_time` order.
3. Generate Signal Cards.
4. Run SPY/QQQ-aware educational backtests.
5. Run research validation diagnostics.
6. Train and evaluate lightweight ML scoring models.
7. Generate a deterministic evidence-grounded explanation for the selected ticker.

Synthetic rows are labeled with sources such as `synthetic_reddit`, `synthetic_sec`, and `synthetic_market`. Synthetic data is useful for demonstrating pipeline mechanics, replay, tests, dashboard states, validation plumbing, and ML target creation. It is **not real market evidence** and should not be used to claim predictive power.

Manual stage commands, if you want to inspect each layer:

```bash
python3 -m backend.simulation.synthetic_history --days 60 --signals 100 --reset-demo-data
python3 -m backend.simulation.replay --start 2026-01-01 --end 2026-03-31
python3 -m backend.models.signal_engine
python3 -m backend.models.backtester
python3 -m backend.research.validation
python3 -m backend.ml.training
python3 -m backend.agents.explanation_engine --ticker NVDA
```

## Optional Real Data Modes

Local development defaults to mock/synthetic data. Optional real modes are isolated behind provider interfaces and are not required for the demo.

### Reddit

```bash
python3 -m backend.ingestion.reddit_provider --limit 25
```

Mock Reddit ingestion requires no credentials. Optional PRAW mode uses `REDDIT_INGESTION_MODE=praw` and credentials from environment variables or `.env`. Reddit API access may require approval; use a truthful `REDDIT_USER_AGENT`, respect rate limits and deletion/removal obligations, and do not redistribute raw Reddit content publicly.

### Market Data

```bash
python3 -m backend.ingestion.market_data_provider --tickers AAPL,TSLA,NVDA,AMD,SPY,QQQ --days 10
python3 -m backend.models.backtester
```

Market data defaults to deterministic mock mode and does not require paid APIs. Optional `MARKET_DATA_MODE=yfinance` is isolated behind the provider interface; use mock mode if `yfinance` is unavailable or network access fails.

### SEC Filings

```bash
python3 -m backend.ingestion.sec_provider --tickers AAPL,TSLA,NVDA,AMD,MSFT,COIN,PLTR --days 30
```

SEC filings default to deterministic mock mode. Optional `SEC_DATA_MODE=real` requires a descriptive `SEC_USER_AGENT` with contact information, for example `RetailSignalOS/0.1 contact:YOUR_EMAIL@example.com`. SEC catalyst matches are contextual only and do not prove that a filing caused social sentiment or a price move.

### Synthetic History And Replay

The generator creates deterministic synthetic Reddit-like events, SEC-like filings, and market bars across multiple tickers and scenarios. It labels sources as `synthetic_reddit`, `synthetic_sec`, and `synthetic_market`. Synthetic outcomes are useful for testing Granger-style validation, lead-lag checks, ML target classes, dashboard empty states, and replay behavior, but they are not real market evidence.

Replay mode reads synthetic events in ingestion-time order and rebuilds available Signal Cards over time without looking ahead. Use the Streamlit `Demo Data / Replay` page or `GET /simulation/status` to inspect synthetic row counts.

## What Makes This Advanced

- **`event_time` vs `ingestion_time`:** records when an event happened and when the system observed it.
- **Signal Cards:** turns every detected signal into a structured artifact with evidence, uncertainty, risks, and later outcome fields when available.
- **Manipulation risk:** models hype/spam indicators probabilistically rather than making accusations.
- **Synthetic replay mode:** rebuilds signals through time in ingestion order to demonstrate point-in-time behavior.
- **SEC catalyst matching:** adds filing context near Signal Card timestamps without claiming causation.
- **SPY/QQQ-adjusted backtesting:** compares forward returns against market and tech benchmarks.
- **Granger-style validation:** checks whether past feature values have predictive usefulness in the stored dataset.
- **Lead-lag correlation:** compares features against future returns at configurable lags.
- **Negative controls:** tests unrelated targets to reveal spurious relationships or leakage risk.
- **Ablation testing:** compares feature groups with and without social, risk, catalyst, and quality signals.
- **ML with time-based split:** trains on older rows and evaluates on newer rows to reduce leakage.
- **Deterministic agent explanations:** produces bull, bear, catalyst, manipulation, backtest, ML, research, and risk summaries from existing fields.
- **No external LLM hallucination risk:** explanation agents do not call generative APIs.

## Limitations And Safety

- Synthetic/demo data is not real market evidence.
- This project is educational research software, not financial advice.
- There is no order execution, broker integration, or real-money trading automation.
- Reddit API access may require approval and must follow Reddit terms, rate limits, and data handling obligations.
- Optional SEC real mode requires proper identification and fair-access behavior.
- Real model conclusions require real historical data, careful sampling, and out-of-sample validation.
- Granger-style tests can show predictive usefulness in a dataset, but they do not prove true causation.
- Backtests can be misleading because of small samples, synthetic data, overfitting, transaction costs, slippage, missing data, and repeated experimentation.

## Roadmap

- Improve source ingestion only after mock/synthetic foundations are tested.
- Expand ticker resolution with exchange-aware symbol metadata.
- Replace deterministic placeholder sentiment with validated finance-domain NLP models when appropriate.
- Add richer source quality signals while avoiding factual accusations about manipulation.
- Add persistent outcome tracking for every Signal Card.
- Expand walk-forward and out-of-sample validation workflows.
- Keep PostgreSQL migration possible by preserving the isolated database layer.

## Disclaimer

RetailSignal OS is for research and educational use only. It is not financial advice, investment advice, or a recommendation to buy or sell securities. It does not claim guaranteed stock prediction or deterministic alpha.

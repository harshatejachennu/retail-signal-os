# RetailSignal OS Project Context

## Project Goal

RetailSignal OS is a production-style foundation for a real-time alternative-data stock signal research platform. The platform will eventually ingest public signals from Reddit, market data, SEC filings, news-like public artifacts, and other sources; extract tickers and narratives; score sentiment, market stance, manipulation risk, statistical anomalies, and catalysts; generate explainable Signal Cards; and validate signals with backtesting, Granger causality, event studies, negative controls, ablation testing, and walk-forward validation.

## Core Principle

RetailSignal OS is a research and paper-trading platform, not a real-money trading bot. Every signal must expose evidence, uncertainty, risk, and later outcome. Never claim guaranteed prediction, deterministic alpha, or investment advice.

## Signal Card Definition

A Signal Card is the canonical user-facing output for a detected market signal. Every signal becomes a Signal Card with:

- Ticker and timestamp.
- Direction and signal strength.
- Trust score and uncertainty-oriented risk fields.
- Manipulation, late hype, contradiction, catalyst, and data quality scores.
- Plain-language explanation.
- Plain-language "what could go wrong" section.
- Later outcome fields when validation and tracking are added.

## Architecture

Initial foundation:

- `backend/api`: FastAPI app and HTTP routes.
- `backend/database`: SQLite-first database helpers and schema, designed so the storage layer can later move to PostgreSQL.
- `backend/ingestion`: Source providers for Reddit, market data, and SEC data. Providers are placeholders until integrations are explicitly added.
- `backend/processing`: Unified events, ticker resolution, sentiment, stance design, and manipulation risk.
- `backend/features`: Feature utilities such as rolling z-scores, time decay, and a future feature store.
- `backend/models`: Signal Card and signal engine models.
- `dashboard`: Streamlit dashboard.
- `research`: Research notes, validation plans, notebooks, and experiment documentation.
- `tests`: Pytest tests for core behavior.

## Data Source Roadmap

Planned sources, in order of maturity:

1. Synthetic/sample events for local development.
2. Public Reddit posts and comments.
3. Market price, volume, volatility, and benchmark data.
4. SEC filings and company disclosures.
5. Public news-like sources with clear licensing.
6. Derived validation datasets for event studies and backtests.

Do not add a Reddit API integration until explicitly requested.

## `event_time` vs `ingestion_time` Rule

Every event must store both:

- `event_time`: when the event happened or was published at the source.
- `ingestion_time`: when RetailSignal OS first observed or stored the event.

Validation, backtesting, and live signal logic must use only information available as of `ingestion_time`. Never use future data, revised data, or later outcomes to create historical features.

## Ticker Resolver Requirements

The ticker resolver must:

- Detect explicit cashtags such as `$TSLA`.
- Detect plain uppercase allowlisted tickers such as `AAPL`.
- Use a false-positive blacklist for terms such as `AI`, `DD`, `CEO`, `CFO`, `GDP`, `USA`, `IT`, `FOR`, `ON`, `ARE`, and `YOLO`.
- Support company-name mapping for common names such as Apple, Tesla, Nvidia, AMD, Microsoft, Google/Alphabet, Meta, and Palantir.
- Return ticker, detection method, confidence, and context window.
- Prefer explainable, conservative matches over aggressive recall.

## Sentiment and Stance Requirements

Sentiment and market stance are separate concepts:

- Sentiment captures tone or polarity in text.
- Market stance captures the implied market view, such as bullish, bearish, neutral, or uncertain.

The first implementation can be simple and deterministic, but the module must be easy to replace with VADER, FinBERT, or a domain-specific model later.

## Manipulation Risk Requirements

Manipulation risk should be modeled as a risk indicator, not an accusation. The initial module should consider:

- Caps ratio.
- Text length.
- Number of tickers mentioned.
- Repeated hype words.
- Emoji density.

Future versions should incorporate account history, coordinated posting patterns, link patterns, timing around price moves, and cross-community repetition.

## Feature Requirements

Feature modules should be deterministic, testable, and timestamp-aware. Initial helpers include:

- Rolling z-score.
- Exponential time decay.
- Feature store placeholder for later materialized features.

Features used in research or live signal generation must avoid look-ahead bias.

## Validation Requirements

Validation is a core product capability. Future work should include:

- Backtesting with point-in-time feature availability.
- Walk-forward validation.
- Event studies around signal timestamps.
- Granger causality tests where statistically appropriate.
- Negative controls.
- Ablation tests.
- Out-of-sample reporting.
- Later outcome tracking for every Signal Card.

## Dashboard Roadmap

The first Streamlit dashboard should show sample/live Signal Cards and placeholders for:

- Live Signals.
- Signal Card Detail.
- Ticker Deep Dive.
- Manipulation Monitor.
- Backtest Lab.
- Research Validation.
- Data Health.

## Safety and Ethics Rules

- Do not provide financial advice.
- Do not automate real-money trading.
- Do not claim guaranteed predictions.
- Display uncertainty and risk alongside every signal.
- Treat manipulation risk as probabilistic and explainable.
- Respect source terms, robots rules, and data licensing.
- Store secrets only in environment variables or secret managers.
- Do not hard-code API keys, tokens, passwords, or private credentials.

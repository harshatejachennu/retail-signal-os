# AGENTS.md

Instructions for future Codex and agentic development tasks in RetailSignal OS.

## Build Rules

- Build in small, testable steps.
- Use Python for backend, processing, features, research utilities, and tests.
- Use FastAPI for the backend API.
- Use SQLite first, but keep the database layer isolated so PostgreSQL can replace it later.
- Use Streamlit for the first dashboard.
- Use pytest for tests.
- Add tests for core behavior whenever adding or changing logic.
- Keep implementation deterministic unless randomness is explicitly required and seeded.

## Product Rules

- RetailSignal OS is not a real-money trading bot.
- Do not add order execution, broker integration, or real-money trading automation.
- Do not claim guaranteed stock prediction.
- Every signal becomes a Signal Card.
- Signal Cards must include evidence, uncertainty, risk, and later outcome when available.
- Include clear "what could go wrong" reasoning for generated signals.

## Time and Validation Rules

- Always avoid look-ahead bias.
- Every event stores both `event_time` and `ingestion_time`.
- Use `ingestion_time` to decide what information was available to the system.
- Do not use future prices, revised filings, later labels, or later outcomes in historical features.
- Validation work should prefer walk-forward, event-study, negative-control, ablation, and out-of-sample designs.

## Engineering Rules

- No hard-coded secrets.
- Keep configuration in environment variables and document them in `.env.example`.
- Keep modules small and replaceable.
- Separate text sentiment from market stance.
- Keep source providers behind interfaces or narrow functions so live integrations can be added safely later.
- Make ticker resolution conservative and explainable.
- Treat manipulation risk as a probabilistic risk score, not a factual accusation.
- Do not proceed to Reddit API integration unless explicitly requested.

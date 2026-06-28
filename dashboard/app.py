import streamlit as st

from backend.agents.explanation_engine import explain_signal_card
from backend.database.db import connect, fetch_sec_filings, initialize
from backend.ml.scoring import score_signal_card
from backend.ml.training import run_training
from backend.models.backtester import backtest_signal_cards_from_database, backtest_summary
from backend.models.signal_engine import get_live_signal_cards
from backend.research.validation import validation_summary
from backend.simulation.synthetic_history import synthetic_status


PAGES = [
    "Live Signals",
    "Signal Card Detail",
    "Signal Explanation",
    "Ticker Deep Dive",
    "Manipulation Monitor",
    "Backtest Lab",
    "Research Validation",
    "ML Evaluation",
    "Demo Data / Replay",
    "Data Health",
]


st.set_page_config(page_title="RetailSignal OS", layout="wide")
st.title("RetailSignal OS")
st.caption("Research and paper-trading Signal Cards. Demo data may be synthetic. Not financial advice.")

page = st.sidebar.radio("Page", PAGES)

if page == "Live Signals":
    st.subheader("Live Signals / Demo Signal Cards")
    st.info("If no stored events exist, this page shows sample placeholder Signal Cards. Synthetic demo rows are labeled in explanations and are not real evidence.")
    cards = get_live_signal_cards()
    for card in cards:
        with st.container(border=True):
            left, middle, right = st.columns([1, 2, 2])
            left.metric(card.ticker, card.direction)
            left.write(f"Sentiment: {card.sentiment_label or 'unknown'}")
            left.write(f"Intent: {card.intent or 'unknown'}")
            middle.metric("Signal Strength", f"{card.signal_strength:.0f}")
            middle.metric("Trust Score", f"{card.trust_score:.0f}")
            middle.write(f"Market stance: {card.market_stance or card.direction}")
            right.metric("Manipulation Risk", f"{card.manipulation_risk:.0f}")
            right.write(f"Risk level: {card.manipulation_risk_level or 'unknown'}")
            right.metric("Data Quality", f"{card.data_quality_score:.0f}")
            right.metric("Catalyst", f"{card.catalyst_score:.0f}")
            if card.catalyst_explanation:
                st.write(card.catalyst_explanation)
            if card.catalyst_events:
                st.dataframe(card.catalyst_events, use_container_width=True)
            if card.backtest_available:
                st.write(
                    f"Backtest: 1d={card.return_1d}, 3d={card.return_3d}, "
                    f"SPY adj 3d={card.spy_adjusted_return_3d}, QQQ adj 3d={card.qqq_adjusted_return_3d}"
                )
            ml_score = score_signal_card(card)
            st.write(f"ML score available: {ml_score.ml_score_available}")
            if ml_score.target_probabilities:
                st.write(f"ML probabilities: {ml_score.target_probabilities}")
            if ml_score.warnings:
                st.write("ML warnings: " + ", ".join(ml_score.warnings))
            report = explain_signal_card(card)
            st.write("Explanation")
            st.write(report.final_interpretation)
            st.write(card.explanation)
            if card.manipulation_risk_reasons:
                st.write("Risk reasons: " + ", ".join(card.manipulation_risk_reasons))
            st.warning(card.what_could_go_wrong)
elif page == "Backtest Lab":
    st.subheader("Backtest Lab")
    results = backtest_signal_cards_from_database()
    if not results:
        st.info(
            "No generated Signal Cards or market bars are available yet. Run "
            "`python3 -m backend.ingestion.reddit_provider --limit 25`, then "
            "`python3 -m backend.ingestion.market_data_provider --tickers AAPL,TSLA,NVDA,AMD,SPY,QQQ --days 10`."
        )
    else:
        summary = backtest_summary(results)
        cols = st.columns(6)
        cols[0].metric("Signals", summary["signals_evaluated"])
        cols[1].metric("Avg 1d", summary["average_return_1d"])
        cols[2].metric("Avg 3d", summary["average_return_3d"])
        cols[3].metric("SPY Adj 3d", summary["average_spy_adjusted_return_3d"])
        cols[4].metric("QQQ Adj 3d", summary["average_qqq_adjusted_return_3d"])
        cols[5].metric("Win 3d", summary["win_rate_3d"])
        st.dataframe([result.model_dump(mode="json") for result in results], use_container_width=True)
elif page == "Signal Explanation":
    st.subheader("Signal Explanation")
    cards = get_live_signal_cards()
    if not cards:
        st.info("No Signal Cards are available yet. Run the full synthetic demo pipeline or ingest mock local data first. Synthetic/demo output is not real market evidence.")
    else:
        tickers = [card.ticker for card in cards]
        selected = st.selectbox("Ticker", tickers)
        card = next(card for card in cards if card.ticker == selected)
        report = explain_signal_card(card)
        st.write(report.final_interpretation)
        st.warning(report.not_financial_advice)
        st.write("Bull Case")
        st.json(report.bull_case.model_dump(mode="json"))
        st.write("Bear Case")
        st.json(report.bear_case.model_dump(mode="json"))
        st.write("Catalyst Analysis")
        st.json(report.catalyst_analysis.model_dump(mode="json"))
        st.write("Manipulation Analysis")
        st.json(report.manipulation_analysis.model_dump(mode="json"))
        st.write("Backtest Analysis")
        st.json(report.backtest_analysis.model_dump(mode="json"))
        st.write("ML Analysis")
        st.json(report.ml_analysis.model_dump(mode="json"))
        st.write("Research Validation")
        st.json(report.research_validation_analysis.model_dump(mode="json"))
        st.write("Risk Summary")
        st.json(report.risk_summary.model_dump(mode="json"))
        st.write("Limitations")
        for limitation in report.limitations:
            st.info(limitation)
elif page == "Research Validation":
    st.subheader("Research Validation")
    summary = validation_summary()
    st.metric("Dataset Rows", summary["dataset_rows"])
    if summary["dataset_rows"] < 8:
        st.info(
            "Research validation requires more historical signal/backtest rows. Run the full synthetic demo pipeline for an offline demo, or run more mock ingestion/market/backtesting cycles. Synthetic results are demo diagnostics, not real evidence."
        )
    cols = st.columns(3)
    cols[0].write("Granger")
    cols[0].json(summary["granger_summary"])
    cols[1].write("Lead-Lag")
    cols[1].json(summary["lead_lag_summary"])
    cols[2].write("Event Study")
    cols[2].json(summary["event_study_summary"])
    st.write("Negative Controls")
    st.json(summary["negative_control_summary"])
    st.write("Ablation")
    st.dataframe(summary["ablation_summary"], use_container_width=True)
    st.write("Limitations")
    for warning in summary["warnings"]:
        st.warning(warning)

    st.subheader("SEC Catalysts")
    connection = connect()
    initialize(connection)
    try:
        filings = fetch_sec_filings(connection, limit=50)
    finally:
        connection.close()
    cards = {card.ticker: card for card in get_live_signal_cards()}
    if not filings:
        st.info(
            "No SEC filings are stored yet. Run "
            "`python3 -m backend.ingestion.sec_provider --tickers AAPL,TSLA,NVDA,AMD,MSFT,COIN,PLTR --days 30`."
        )
    else:
        rows = []
        for filing in filings:
            card = cards.get(filing.ticker)
            rows.append(
                {
                    "ticker": filing.ticker,
                    "form_type": filing.form_type,
                    "filed_at": filing.filed_at.isoformat(),
                    "title": filing.title,
                    "summary": filing.summary,
                    "matched_signal": card.ticker if card else None,
                    "catalyst_score": card.catalyst_score if card else None,
                    "catalyst_explanation": card.catalyst_explanation if card else None,
                }
            )
        st.dataframe(rows, use_container_width=True)
elif page == "ML Evaluation":
    st.subheader("ML Evaluation")
    summary = run_training(save_artifacts=False)
    st.metric("Dataset Rows", summary["dataset_rows"])
    st.write("Target Distribution")
    st.json(summary["target_availability"])
    st.write("Model Statuses")
    st.json(summary["model_statuses"])
    st.write("Baseline vs Logistic vs Random Forest Metrics")
    st.json(summary["latest_metrics"])
    st.write("Feature Importance")
    importance = summary["feature_importance"]
    if importance.get("importances"):
        st.dataframe(importance["importances"], use_container_width=True)
    else:
        st.info("Feature importance is unavailable until there is enough labeled data with two target classes.")
    st.write("Walk-Forward Validation")
    st.json(summary["walk_forward"])
    st.write("Limitations")
    for warning in summary["warnings"] or ["ML outputs are educational estimates, not financial advice."]:
        st.warning(warning)
elif page == "Demo Data / Replay":
    st.subheader("Demo Data / Replay")
    status = synthetic_status()
    st.warning("Synthetic history is demonstration data only and is not real market evidence.")
    cols = st.columns(5)
    cols[0].metric("Synthetic Events", status["synthetic_events"])
    cols[1].metric("Signal Cards", status["signal_count"])
    cols[2].metric("Backtests", status["backtest_count"])
    cols[3].metric("Research Rows", status["research_dataset_rows"])
    cols[4].metric("ML Rows", status["ml_dataset_rows"])
    st.write("Target Distribution")
    st.json(status["target_distribution"])
    st.code("python3 -m backend.simulation.demo_pipeline --days 60 --signals 100 --ticker NVDA")
    st.code("python3 -m backend.simulation.synthetic_history --days 60 --signals 100 --reset-demo-data")
    st.code("python3 -m backend.simulation.replay --start 2026-01-01 --end 2026-03-31")
else:
    st.subheader(page)
    st.info("This page is a planned dashboard area. Run `python3 -m backend.simulation.demo_pipeline --days 60 --signals 100 --ticker NVDA` to populate demo data. Synthetic results are labeled and are not real evidence.")

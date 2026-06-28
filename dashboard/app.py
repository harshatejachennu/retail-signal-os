import streamlit as st

from backend.models.signal_engine import create_sample_signal_cards


PAGES = [
    "Live Signals",
    "Signal Card Detail",
    "Ticker Deep Dive",
    "Manipulation Monitor",
    "Backtest Lab",
    "Research Validation",
    "Data Health",
]


st.set_page_config(page_title="RetailSignal OS", layout="wide")
st.title("RetailSignal OS")
st.caption("Research and paper-trading signal cards. Not financial advice.")

page = st.sidebar.radio("Page", PAGES)

if page == "Live Signals":
    st.subheader("Live Signals")
    cards = create_sample_signal_cards()
    for card in cards:
        with st.container(border=True):
            left, middle, right = st.columns([1, 2, 2])
            left.metric(card.ticker, card.direction)
            middle.metric("Signal Strength", f"{card.signal_strength:.2f}")
            middle.metric("Trust Score", f"{card.trust_score:.2f}")
            right.metric("Manipulation Risk", f"{card.manipulation_risk:.2f}")
            right.metric("Data Quality", f"{card.data_quality_score:.2f}")
            st.write(card.explanation)
            st.warning(card.what_could_go_wrong)
else:
    st.subheader(page)
    st.info("Placeholder for the next foundation milestone.")

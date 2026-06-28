from backend.processing.sentiment import score_entity_sentiment, score_sentiment


def test_bullish_stance_with_buying_calls() -> None:
    result = score_sentiment("I am buying calls on TSLA after the breakout.")
    assert result.market_stance == "bullish"
    assert result.general_sentiment == "positive"
    assert "buying calls" in result.evidence_terms


def test_bearish_stance_with_buying_puts() -> None:
    result = score_sentiment("I am buying puts because this looks overvalued.")
    assert result.market_stance == "bearish"
    assert result.general_sentiment == "negative"
    assert "buying puts" in result.evidence_terms


def test_meme_hype_intent() -> None:
    result = score_sentiment("YOLO all in, rocket to the moon for tendies.")
    assert result.intent == "meme_hype"
    assert result.market_stance == "bullish"


def test_serious_dd_intent() -> None:
    result = score_sentiment("Revenue, margins, and free cash flow support the valuation thesis.")
    assert result.intent == "serious_dd"
    assert result.confidence > 0.5


def test_options_gamble_intent() -> None:
    result = score_sentiment("Bought calls with a 500 strike and Friday expiry; premium is high.")
    assert result.intent == "options_gamble"
    assert result.market_stance == "bullish"


def test_neutral_unclear_text() -> None:
    result = score_sentiment("The company held a meeting today and people discussed the agenda.")
    assert result.general_sentiment == "neutral"
    assert result.market_stance == "unclear"
    assert result.intent == "unknown"
    assert result.confidence <= 0.45


def test_entity_level_sentiment_handles_contrast() -> None:
    results = score_entity_sentiment("AMD is undervalued but Intel is cooked.")
    by_ticker = {result.ticker: result for result in results}

    assert by_ticker["AMD"].market_stance == "bullish"
    assert by_ticker["AMD"].general_sentiment == "positive"
    assert by_ticker["INTC"].market_stance == "bearish"
    assert by_ticker["INTC"].general_sentiment == "negative"

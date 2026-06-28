from backend.processing.manipulation import score_manipulation_risk


def test_high_risk_for_all_caps_yolo_rocket_spam() -> None:
    result = score_manipulation_risk("TSLA YOLO YOLO ROCKET ROCKET MOON 🚀🚀🚀 FREE MONEY")
    assert result.risk_level == "high"
    assert result.risk_score >= 70
    assert result.reasons


def test_low_risk_for_normal_serious_dd() -> None:
    result = score_manipulation_risk(
        "Microsoft revenue growth, margins, and free cash flow support a measured valuation thesis."
    )
    assert result.risk_level == "low"
    assert result.risk_score < 35


def test_medium_or_high_risk_for_too_many_ticker_mentions() -> None:
    result = score_manipulation_risk("$TSLA $NVDA $AAPL $MSFT $AMD $COIN all moving now")
    assert result.risk_level in {"medium", "high"}
    assert "too many ticker mentions" in result.reasons


def test_risk_reasons_are_returned() -> None:
    result = score_manipulation_risk("AAPL MOON MOON rocket 🚀")
    assert result.reasons

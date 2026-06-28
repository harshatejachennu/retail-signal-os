from backend.processing.ticker_resolver import resolve_tickers


def tickers(text: str) -> set[str]:
    return {match.ticker for match in resolve_tickers(text)}


def test_false_positive_blacklist_excludes_common_terms() -> None:
    assert tickers("AI DD CEO CFO GDP USA IT FOR ON ARE YOLO") == set()


def test_detects_cashtag_and_uppercase_allowlist() -> None:
    matches = resolve_tickers("Watching $TSLA and NVDA into earnings.")
    by_ticker = {match.ticker: match for match in matches}
    assert {"TSLA", "NVDA"} <= set(by_ticker)
    assert by_ticker["TSLA"].detection_method == "cashtag"
    assert by_ticker["NVDA"].detection_method == "uppercase_allowlist"
    assert "earnings" in by_ticker["NVDA"].context_window


def test_apple_and_tesla_company_name_mapping() -> None:
    assert tickers("Apple and Tesla are both in focus.") == {"AAPL", "TSLA"}


def test_company_name_mapping() -> None:
    assert tickers("Tesla and Palantir are trending while Microsoft is quiet.") == {
        "TSLA",
        "PLTR",
        "MSFT",
    }


def test_nvidia_and_jensen_mapping() -> None:
    matches = resolve_tickers("Nvidia fans are watching Jensen after the keynote.")
    by_ticker = {match.ticker: match for match in matches}

    assert by_ticker["NVDA"].detection_method == "company_name"
    assert by_ticker["NVDA"].confidence == 0.78


def test_elon_maps_to_tesla_with_lower_confidence() -> None:
    matches = resolve_tickers("Elon commentary moved the thread.")
    assert matches[0].ticker == "TSLA"
    assert matches[0].detection_method == "nickname_product"
    assert matches[0].confidence < 0.78


def test_multi_ticker_detection() -> None:
    assert tickers("Apple, $TSLA, NVDA, Coinbase, and MicroStrategy are active.") == {
        "AAPL",
        "TSLA",
        "NVDA",
        "COIN",
        "MSTR",
    }

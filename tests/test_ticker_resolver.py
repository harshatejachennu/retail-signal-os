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


def test_company_name_mapping() -> None:
    assert tickers("Tesla and Palantir are trending while Microsoft is quiet.") == {
        "TSLA",
        "PLTR",
        "MSFT",
    }

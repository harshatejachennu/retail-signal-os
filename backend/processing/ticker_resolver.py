from __future__ import annotations

import re
from dataclasses import dataclass


ALLOWLIST = {"AAPL", "TSLA", "NVDA", "AMD", "MSFT", "GOOGL", "META", "PLTR"}
FALSE_POSITIVE_BLACKLIST = {"AI", "DD", "CEO", "CFO", "GDP", "USA", "IT", "FOR", "ON", "ARE", "YOLO"}
COMPANY_NAME_MAP = {
    "apple": "AAPL",
    "tesla": "TSLA",
    "nvidia": "NVDA",
    "advanced micro devices": "AMD",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "meta": "META",
    "facebook": "META",
    "palantir": "PLTR",
}


@dataclass(frozen=True)
class TickerMatch:
    ticker: str
    detection_method: str
    confidence: float
    context_window: str


def _context_window(text: str, start: int, end: int, radius: int = 40) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return text[left:right].strip()


def _add_match(
    matches: dict[str, TickerMatch],
    ticker: str,
    method: str,
    confidence: float,
    text: str,
    start: int,
    end: int,
) -> None:
    if ticker in FALSE_POSITIVE_BLACKLIST:
        return
    current = matches.get(ticker)
    candidate = TickerMatch(
        ticker=ticker,
        detection_method=method,
        confidence=confidence,
        context_window=_context_window(text, start, end),
    )
    if current is None or candidate.confidence > current.confidence:
        matches[ticker] = candidate


def resolve_tickers(text: str) -> list[TickerMatch]:
    matches: dict[str, TickerMatch] = {}

    for match in re.finditer(r"\$([A-Z]{1,5})(?![A-Z])", text):
        ticker = match.group(1)
        if ticker in ALLOWLIST:
            _add_match(matches, ticker, "cashtag", 0.98, text, match.start(), match.end())

    for match in re.finditer(r"\b[A-Z]{2,5}\b", text):
        ticker = match.group(0)
        if ticker in ALLOWLIST and ticker not in FALSE_POSITIVE_BLACKLIST:
            _add_match(matches, ticker, "uppercase_allowlist", 0.85, text, match.start(), match.end())

    lowered = text.lower()
    for company_name, ticker in COMPANY_NAME_MAP.items():
        for match in re.finditer(rf"\b{re.escape(company_name)}\b", lowered):
            _add_match(matches, ticker, "company_name", 0.78, text, match.start(), match.end())

    return sorted(matches.values(), key=lambda item: item.ticker)

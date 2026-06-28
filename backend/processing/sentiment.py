from __future__ import annotations

import re
from dataclasses import dataclass

from backend.processing.ticker_resolver import COMPANY_NAME_MAP, NICKNAME_PRODUCT_MAP, TickerMatch, resolve_tickers


POSITIVE_TERMS = {
    "beat",
    "beats",
    "breakout",
    "bullish",
    "diamond hands",
    "growth",
    "long",
    "moon",
    "strong",
    "undervalued",
    "upside",
}
NEGATIVE_TERMS = {
    "bagholding",
    "bankruptcy",
    "bearish",
    "cooked",
    "dead company",
    "downside",
    "dump",
    "fraud",
    "miss",
    "misses",
    "overvalued",
    "paper hands",
    "rug pull",
    "selloff",
    "weak",
}
BULLISH_TERMS = {
    "bought calls",
    "bought the dip",
    "buying calls",
    "buying shares",
    "calls",
    "diamond hands",
    "dip buying",
    "loading up",
    "long",
    "moon",
    "shares",
    "short squeeze",
    "squeeze",
    "to the moon",
} | POSITIVE_TERMS
BEARISH_TERMS = {
    "bought puts",
    "buying puts",
    "puts",
    "short",
    "shorting",
} | NEGATIVE_TERMS
OPTIONS_TERMS = {
    "calls",
    "contracts",
    "expiration",
    "expiry",
    "implied volatility",
    "iv",
    "premium",
    "puts",
    "strike",
}
SERIOUS_DD_TERMS = {
    "balance sheet",
    "cash flow",
    "debt",
    "earnings",
    "free cash flow",
    "guidance",
    "margin",
    "margins",
    "revenue",
    "thesis",
    "valuation",
}
MEME_HYPE_TERMS = {"all in", "apes", "diamond hands", "lambo", "moon", "rocket", "tendies", "yolo"}
EARNINGS_TERMS = {"earnings", "eps", "guidance", "quarter", "q1", "q2", "q3", "q4"}
NEWS_TERMS = {"announced", "approval", "downgrade", "lawsuit", "news", "report", "upgrade"}
TECHNICAL_TERMS = {"breakout", "moving average", "resistance", "rsi", "support", "technical", "trendline"}


@dataclass(frozen=True)
class SentimentResult:
    ticker: str | None
    general_sentiment: str
    market_stance: str
    intent: str
    sentiment_score: float
    confidence: float
    evidence_terms: list[str]
    explanation: str

    @property
    def label(self) -> str:
        return self.general_sentiment


def _normalized_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _find_terms(text: str, terms: set[str]) -> list[str]:
    normalized = _normalized_text(text)
    hits = []
    for term in sorted(terms):
        pattern = rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])"
        if re.search(pattern, normalized):
            hits.append(term)
    return hits


def _clamp(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(value, upper))


def _classify_intent(text: str, evidence: list[str]) -> str:
    meme_hits = _find_terms(text, MEME_HYPE_TERMS)
    options_hits = _find_terms(text, OPTIONS_TERMS)
    serious_hits = _find_terms(text, SERIOUS_DD_TERMS)

    if "short squeeze" in _find_terms(text, {"short squeeze"}):
        return "short_squeeze"
    if len(meme_hits) >= 2:
        return "meme_hype"
    if len(options_hits) >= 2 or ({"calls", "puts"} & set(options_hits) and {"strike", "expiry", "expiration"} & set(options_hits)):
        return "options_gamble"
    if len(serious_hits) >= 2:
        return "serious_dd"
    if _find_terms(text, TECHNICAL_TERMS):
        return "technical_analysis"
    if _find_terms(text, EARNINGS_TERMS):
        return "earnings_reaction"
    if _find_terms(text, NEWS_TERMS):
        return "news_reaction"
    if any(term in MEME_HYPE_TERMS for term in evidence):
        return "meme_hype"
    return "unknown"


def _classify_text(text: str, ticker: str | None = None) -> SentimentResult:
    positive_hits = _find_terms(text, POSITIVE_TERMS)
    negative_hits = _find_terms(text, NEGATIVE_TERMS)
    bullish_hits = _find_terms(text, BULLISH_TERMS)
    bearish_hits = _find_terms(text, BEARISH_TERMS)
    evidence = sorted(set(positive_hits + negative_hits + bullish_hits + bearish_hits))

    bullish_score = len(bullish_hits)
    bearish_score = len(bearish_hits)
    stance_delta = bullish_score - bearish_score
    total_stance_hits = bullish_score + bearish_score

    if stance_delta > 0:
        market_stance = "bullish"
    elif stance_delta < 0:
        market_stance = "bearish"
    elif total_stance_hits == 0:
        market_stance = "unclear"
    else:
        market_stance = "neutral"

    polarity_delta = len(positive_hits) - len(negative_hits)
    total_polarity_hits = len(positive_hits) + len(negative_hits)
    sentiment_score = 0.0 if total_polarity_hits == 0 else _clamp(polarity_delta / max(total_polarity_hits, 1))

    if sentiment_score > 0.15:
        general_sentiment = "positive"
    elif sentiment_score < -0.15:
        general_sentiment = "negative"
    else:
        general_sentiment = "neutral"

    intent = _classify_intent(text, evidence)
    confidence = min(0.35 + total_stance_hits * 0.14 + total_polarity_hits * 0.08 + len(_find_terms(text, OPTIONS_TERMS | SERIOUS_DD_TERMS | MEME_HYPE_TERMS)) * 0.04, 0.95)
    if market_stance == "unclear" and general_sentiment == "neutral" and intent == "unknown":
        confidence = min(confidence, 0.45)

    target = ticker or "overall text"
    if evidence:
        explanation = f"Classified {target} from deterministic evidence terms: {', '.join(evidence)}."
    else:
        explanation = f"Classified {target} as neutral/unclear because no finance stance terms were found."

    return SentimentResult(
        ticker=ticker,
        general_sentiment=general_sentiment,
        market_stance=market_stance,
        intent=intent,
        sentiment_score=round(sentiment_score, 3),
        confidence=round(confidence, 3),
        evidence_terms=evidence,
        explanation=explanation,
    )


def _entity_aliases(ticker: str) -> set[str]:
    aliases = {ticker, f"${ticker}"}
    aliases.update(name for name, mapped in COMPANY_NAME_MAP.items() if mapped == ticker)
    aliases.update(name for name, (mapped, _confidence) in NICKNAME_PRODUCT_MAP.items() if mapped == ticker)
    return aliases


def _segments(text: str) -> list[str]:
    return [segment.strip() for segment in re.split(r"\b(?:but|however|though|while|whereas)\b|[.;]", text, flags=re.IGNORECASE) if segment.strip()]


def _entity_context(text: str, match: TickerMatch) -> str:
    aliases = _entity_aliases(match.ticker)
    for segment in _segments(text):
        normalized = _normalized_text(segment)
        for alias in aliases:
            alias_pattern = rf"(?<![a-z0-9$]){re.escape(alias.lower())}(?![a-z0-9])"
            if re.search(alias_pattern, normalized):
                return segment
    return match.context_window


def score_sentiment(text: str) -> SentimentResult:
    """Deterministic first-pass sentiment scorer, separate from market stance extraction."""
    return _classify_text(text)


def score_entity_sentiment(text: str, ticker_matches: list[TickerMatch] | None = None) -> list[SentimentResult]:
    matches = ticker_matches if ticker_matches is not None else resolve_tickers(text)
    return [_classify_text(_entity_context(text, match), ticker=match.ticker) for match in matches]


def analyze_sentiment(text: str) -> list[SentimentResult]:
    return [score_sentiment(text), *score_entity_sentiment(text)]

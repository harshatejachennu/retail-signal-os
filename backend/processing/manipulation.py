from __future__ import annotations

from dataclasses import dataclass
import re

from backend.processing.ticker_resolver import resolve_tickers


HYPE_WORDS = {"moon", "mooning", "rocket", "rockets", "squeeze", "guaranteed", "pump", "lambo", "yolo", "tendies"}
PROMOTIONAL_TERMS = {"can't lose", "free money", "guaranteed", "next 100x", "risk free", "sure thing"}
REASONING_TERMS = {"balance sheet", "cash flow", "debt", "earnings", "free cash flow", "guidance", "margin", "revenue", "valuation"}
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF]")


@dataclass(frozen=True)
class ManipulationRiskResult:
    risk_score: float
    risk_level: str
    reasons: list[str]

    def normalized_score(self) -> float:
        return self.risk_score / 100.0


def _caps_ratio(text: str) -> float:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for char in letters if char.isupper()) / len(letters)


def _repeated_phrase_count(text: str) -> int:
    words = [word.strip(".,!?;:()[]{}").lower() for word in text.split()]
    phrases = [" ".join(words[index : index + 2]) for index in range(max(len(words) - 1, 0))]
    return len(phrases) - len(set(phrases))


def _risk_level(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def analyze_manipulation_risk(text: str, account_metadata: dict | None = None) -> ManipulationRiskResult:
    words = [word.strip(".,!?;:()[]{}").lower() for word in text.split()]
    word_count = max(len(words), 1)
    hype_hits = sum(1 for word in words if word in HYPE_WORDS)
    emoji_count = len(EMOJI_RE.findall(text))
    ticker_count = len(resolve_tickers(text))
    caps_ratio = _caps_ratio(text)
    repeated_phrases = _repeated_phrase_count(text)
    normalized = re.sub(r"\s+", " ", text.lower())
    promotional_hits = sum(1 for term in PROMOTIONAL_TERMS if term in normalized)
    reasoning_hits = sum(1 for term in REASONING_TERMS if term in normalized)

    score = 0.0
    reasons: list[str] = []

    if caps_ratio > 0.55 and word_count >= 3:
        component = min(caps_ratio * 25, 25)
        score += component
        reasons.append("excessive caps ratio")
    if word_count < 8 and (hype_hits > 0 or ticker_count > 0):
        score += 12
        reasons.append("very short low-quality comment")
    if hype_hits >= 2:
        score += min(hype_hits * 8, 28)
        reasons.append("repeated hype words")
    if emoji_count:
        score += min((emoji_count / word_count) * 60, 18)
        reasons.append("high emoji density")
    if ticker_count >= 4:
        score += min((ticker_count - 3) * 10 + 18, 35)
        reasons.append("too many ticker mentions")
    elif ticker_count >= 3:
        score += 14
        reasons.append("multiple ticker mentions")
    if repeated_phrases >= 2:
        score += min(repeated_phrases * 6, 18)
        reasons.append("repeated phrases")
    if promotional_hits:
        score += min(promotional_hits * 12, 24)
        reasons.append("suspiciously promotional wording")
    if reasoning_hits == 0 and word_count >= 5 and (hype_hits > 0 or promotional_hits > 0):
        score += 12
        reasons.append("lack of real reasoning")

    if account_metadata:
        if account_metadata.get("account_age_days") is not None and account_metadata["account_age_days"] < 14:
            score += 8
            reasons.append("new account metadata")
        if account_metadata.get("karma") is not None and account_metadata["karma"] < 10:
            score += 6
            reasons.append("low-karma account metadata")

    risk_score = round(min(score, 100.0), 1)
    return ManipulationRiskResult(risk_score=risk_score, risk_level=_risk_level(risk_score), reasons=reasons)


def score_manipulation_risk(text: str) -> ManipulationRiskResult:
    return analyze_manipulation_risk(text)

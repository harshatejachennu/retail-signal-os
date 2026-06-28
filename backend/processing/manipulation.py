from __future__ import annotations

import re

from backend.processing.ticker_resolver import resolve_tickers


HYPE_WORDS = {"moon", "mooning", "rocket", "squeeze", "guaranteed", "pump", "lambo", "yolo"}
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF]")


def _caps_ratio(text: str) -> float:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for char in letters if char.isupper()) / len(letters)


def score_manipulation_risk(text: str) -> float:
    words = [word.strip(".,!?;:()[]{}").lower() for word in text.split()]
    word_count = max(len(words), 1)
    hype_hits = sum(1 for word in words if word in HYPE_WORDS)
    emoji_count = len(EMOJI_RE.findall(text))
    ticker_count = len(resolve_tickers(text))

    caps_component = min(_caps_ratio(text) * 0.35, 0.35)
    short_text_component = 0.15 if word_count < 8 and hype_hits > 0 else 0.0
    ticker_component = min(max(ticker_count - 1, 0) * 0.08, 0.2)
    hype_component = min(hype_hits * 0.1, 0.25)
    emoji_component = min((emoji_count / word_count) * 0.5, 0.2)

    return min(caps_component + short_text_component + ticker_component + hype_component + emoji_component, 1.0)

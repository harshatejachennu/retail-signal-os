from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SignalCard(BaseModel):
    ticker: str = Field(pattern=r"^[A-Z]{1,5}$")
    timestamp: datetime
    direction: Literal["bullish", "bearish", "neutral", "uncertain"]
    signal_strength: float = Field(ge=0.0, le=1.0)
    trust_score: float = Field(ge=0.0, le=1.0)
    manipulation_risk: float = Field(ge=0.0, le=1.0)
    late_hype_risk: float = Field(ge=0.0, le=1.0)
    contradiction_score: float = Field(ge=0.0, le=1.0)
    catalyst_score: float = Field(ge=0.0, le=1.0)
    data_quality_score: float = Field(ge=0.0, le=1.0)
    sentiment_label: Literal["positive", "negative", "neutral"] | None = None
    market_stance: Literal["bullish", "bearish", "neutral", "unclear"] | None = None
    intent: (
        Literal[
            "serious_dd",
            "meme_hype",
            "options_gamble",
            "earnings_reaction",
            "news_reaction",
            "short_squeeze",
            "technical_analysis",
            "unknown",
        ]
        | None
    ) = None
    manipulation_risk_level: Literal["low", "medium", "high"] | None = None
    manipulation_risk_reasons: list[str] = Field(default_factory=list)
    explanation: str = Field(min_length=1)
    what_could_go_wrong: str = Field(min_length=1)

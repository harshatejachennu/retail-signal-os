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
    explanation: str = Field(min_length=1)
    what_could_go_wrong: str = Field(min_length=1)

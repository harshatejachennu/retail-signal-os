from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class MarketBar(BaseModel):
    ticker: str = Field(pattern=r"^[A-Z]{1,5}$")
    timestamp: datetime
    open: float = Field(gt=0.0)
    high: float = Field(gt=0.0)
    low: float = Field(gt=0.0)
    close: float = Field(gt=0.0)
    volume: int = Field(ge=0)
    source: str
    ingestion_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

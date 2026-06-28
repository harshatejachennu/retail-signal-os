from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    event_time: datetime
    ingestion_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_text: str
    entities: list[dict[str, Any]] = Field(default_factory=list)
    narratives: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    raw_payload: dict[str, Any] = Field(default_factory=dict)

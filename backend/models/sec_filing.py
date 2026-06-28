from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class SECFiling(BaseModel):
    filing_id: str
    ticker: str = Field(pattern=r"^[A-Z]{1,5}$")
    cik: str
    form_type: Literal["8-K", "10-Q", "10-K", "Form 4"]
    filed_at: datetime
    accepted_at: datetime | None = None
    ingestion_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accession_number: str
    filing_url: str
    title: str
    summary: str
    source: str
    raw_payload: dict[str, Any] = Field(default_factory=dict)

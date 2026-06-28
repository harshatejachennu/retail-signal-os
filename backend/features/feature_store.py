from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FeatureStore:
    """In-memory placeholder for point-in-time features."""

    features: dict[str, dict[str, Any]] = field(default_factory=dict)

    def put(self, entity_id: str, values: dict[str, Any]) -> None:
        self.features[entity_id] = values

    def get(self, entity_id: str) -> dict[str, Any] | None:
        return self.features.get(entity_id)

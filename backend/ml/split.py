from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChronologicalSplit:
    status: str
    train_rows: list[dict[str, Any]]
    test_rows: list[dict[str, Any]]
    warnings: list[str]


def chronological_train_test_split(
    rows: list[dict[str, Any]],
    test_fraction: float = 0.3,
    min_train: int = 5,
    min_test: int = 2,
) -> ChronologicalSplit:
    ordered = sorted(rows, key=lambda row: row.get("signal_timestamp"))
    if len(ordered) < min_train + min_test:
        return ChronologicalSplit(
            status="insufficient_data",
            train_rows=[],
            test_rows=[],
            warnings=[f"Need at least {min_train + min_test} rows for chronological split."],
        )
    test_size = max(min_test, int(round(len(ordered) * test_fraction)))
    test_size = min(test_size, len(ordered) - min_train)
    train_rows = ordered[:-test_size]
    test_rows = ordered[-test_size:]
    return ChronologicalSplit(status="ok", train_rows=train_rows, test_rows=test_rows, warnings=[])

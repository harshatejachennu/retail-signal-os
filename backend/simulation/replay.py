from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone

from backend.database.db import connect, fetch_events, initialize
from backend.processing.pipeline import generate_signal_cards_from_events


def replay_synthetic_events(start: datetime | None = None, end: datetime | None = None, database_url: str | None = None) -> dict:
    connection = connect(database_url)
    initialize(connection)
    try:
        events = [event for event in fetch_events(connection) if event.source == "synthetic_reddit"]
    finally:
        connection.close()
    events = sorted(events, key=lambda event: (event.ingestion_time, event.event_time))
    if start is not None:
        events = [event for event in events if event.ingestion_time >= start]
    if end is not None:
        events = [event for event in events if event.ingestion_time <= end]
    if not events:
        return {"status": "empty", "events_replayed": 0, "batches": [], "signal_cards_generated": 0}

    seen = []
    batches = []
    by_day = defaultdict(list)
    for event in events:
        by_day[event.ingestion_time.date().isoformat()].append(event)
    for day in sorted(by_day):
        seen.extend(by_day[day])
        cards = generate_signal_cards_from_events(seen)
        batches.append(
            {
                "day": day,
                "events_available": len(seen),
                "new_events": len(by_day[day]),
                "signal_cards_available": len(cards),
                "max_ingestion_time": max(event.ingestion_time for event in seen).isoformat(),
            }
        )
    return {
        "status": "ok",
        "events_replayed": len(events),
        "batches": batches,
        "signal_cards_generated": batches[-1]["signal_cards_available"],
    }


def _parse_date(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay synthetic events in ingestion-time order.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()
    result = replay_synthetic_events(_parse_date(args.start), _parse_date(args.end))
    print(f"replay status: {result['status']}")
    print(f"events replayed: {result['events_replayed']}")
    print(f"signal cards generated: {result['signal_cards_generated']}")
    for batch in result["batches"][:10]:
        print(
            f"{batch['day']}: events_available={batch['events_available']} "
            f"signal_cards_available={batch['signal_cards_available']}"
        )


if __name__ == "__main__":
    main()

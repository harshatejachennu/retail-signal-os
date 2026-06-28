from __future__ import annotations

from datetime import datetime

import pytest

from backend.database.db import connect, fetch_events, initialize, insert_events
from backend.ingestion.reddit_provider import RedditConfigurationError, RedditProvider


def test_mock_reddit_ingestion_works_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)
    monkeypatch.setenv("REDDIT_INGESTION_MODE", "mock")

    events = RedditProvider().fetch_events(limit=2)

    assert len(events) == 2
    assert all(event.source == "reddit" for event in events)
    assert any(entity["ticker"] == "TSLA" for event in events for entity in event.entities)


def test_praw_mode_gives_clear_missing_credentials_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDDIT_INGESTION_MODE", "praw")
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)

    with pytest.raises(RedditConfigurationError, match="REDDIT_CLIENT_ID"):
        RedditProvider().fetch_posts(limit=1)


def test_event_creation_from_mocked_reddit_post() -> None:
    post = {
        "id": "abc123",
        "title": "Apple and $TSLA watch",
        "selftext": "Tesla risks remain high.",
        "subreddit": "stocks",
        "author": "sample_user",
        "score": 12,
        "num_comments": 3,
        "permalink": "/r/stocks/comments/abc123/",
        "created_utc": 1_735_689_600,
    }

    event = RedditProvider(mode="mock").post_to_event(post)
    tickers = {entity["ticker"] for entity in event.entities}

    assert event.event_id == "reddit:abc123"
    assert event.event_time is not None
    assert event.ingestion_time is not None
    assert isinstance(event.event_time, datetime)
    assert isinstance(event.ingestion_time, datetime)
    assert "Apple and $TSLA watch" in event.raw_text
    assert tickers == {"AAPL", "TSLA"}
    assert event.raw_payload["subreddit"] == "stocks"
    assert event.raw_payload["author"] == "sample_user"
    assert event.raw_payload["score"] == 12
    assert event.raw_payload["num_comments"] == 3
    assert event.raw_payload["permalink"] == "/r/stocks/comments/abc123/"
    assert event.raw_payload["created_utc"] == 1_735_689_600


def test_insert_and_fetch_events(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'events.db'}"
    connection = connect(database_url)
    initialize(connection)
    events = RedditProvider(mode="mock").fetch_events(limit=1)

    insert_events(connection, events)
    stored = fetch_events(connection)

    assert len(stored) == 1
    assert stored[0].event_id == events[0].event_id
    assert stored[0].event_time is not None
    assert stored[0].ingestion_time is not None
    connection.close()

from __future__ import annotations

import argparse
import logging
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Protocol

from backend.database.db import connect, initialize, insert_events
from backend.processing.events import Event
from backend.processing.ticker_resolver import TickerMatch, resolve_tickers

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency may not be installed before setup refresh.
    load_dotenv = None


LOGGER = logging.getLogger(__name__)
DEFAULT_SUBREDDITS = ("wallstreetbets", "stocks", "investing", "options")
DEFAULT_MODE = "mock"


class RedditConfigurationError(RuntimeError):
    """Raised when real Reddit ingestion is requested without usable configuration."""


class RedditPostLike(Protocol):
    id: str
    title: str
    selftext: str
    subreddit: Any
    author: Any
    score: int
    num_comments: int
    permalink: str
    created_utc: float


MOCK_POSTS: list[dict[str, Any]] = [
    {
        "id": "mock_tsla_001",
        "title": "$TSLA delivery chatter into earnings",
        "selftext": "Tesla bulls are focused on margins, but the risk is that demand is already priced in.",
        "subreddit": "wallstreetbets",
        "author": "sample_researcher",
        "score": 142,
        "num_comments": 38,
        "permalink": "/r/wallstreetbets/comments/mock_tsla_001/",
        "created_utc": 1_735_689_600,
    },
    {
        "id": "mock_nvda_001",
        "title": "NVDA and Jensen keynote watch",
        "selftext": "Nvidia demand still looks strong, though export controls could pressure the narrative.",
        "subreddit": "stocks",
        "author": "sample_value",
        "score": 88,
        "num_comments": 21,
        "permalink": "/r/stocks/comments/mock_nvda_001/",
        "created_utc": 1_735_693_200,
    },
    {
        "id": "mock_aapl_001",
        "title": "Apple iPhone replacement cycle discussion",
        "selftext": "AAPL services strength may matter more than hardware this quarter.",
        "subreddit": "investing",
        "author": "sample_long_term",
        "score": 57,
        "num_comments": 14,
        "permalink": "/r/investing/comments/mock_aapl_001/",
        "created_utc": 1_735_696_800,
    },
    {
        "id": "mock_multi_001",
        "title": "Options flow watch: AMD, MSFT, and Coinbase",
        "selftext": "COIN and AMD are seeing attention, while Microsoft sentiment is more measured.",
        "subreddit": "options",
        "author": "sample_options",
        "score": 33,
        "num_comments": 9,
        "permalink": "/r/options/comments/mock_multi_001/",
        "created_utc": 1_735_700_400,
    },
]


def _load_environment() -> None:
    if load_dotenv is not None:
        load_dotenv()


def _utc_from_timestamp(timestamp: float | int) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _raw_text(title: str, selftext: str | None) -> str:
    return "\n\n".join(part for part in (title.strip(), (selftext or "").strip()) if part)


def _match_to_entity(match: TickerMatch) -> dict[str, Any]:
    return {
        "ticker": match.ticker,
        "detection_method": match.detection_method,
        "confidence": match.confidence,
        "context_window": match.context_window,
    }


def _confidence_from_matches(matches: list[TickerMatch]) -> float:
    if not matches:
        return 0.35
    return max(match.confidence for match in matches)


class RedditProvider:
    def __init__(self, mode: str | None = None, subreddits: tuple[str, ...] = DEFAULT_SUBREDDITS) -> None:
        _load_environment()
        self.mode = (mode or os.getenv("REDDIT_INGESTION_MODE", DEFAULT_MODE)).lower()
        self.subreddits = subreddits

    def fetch_posts(self, limit: int = 25) -> list[dict[str, Any]]:
        if self.mode == "mock":
            return self._fetch_mock_posts(limit)
        if self.mode == "praw":
            return self._fetch_praw_posts(limit)
        raise RedditConfigurationError(
            f"Unsupported REDDIT_INGESTION_MODE={self.mode!r}. Use 'mock' or 'praw'."
        )

    def fetch_events(self, limit: int = 25) -> list[Event]:
        return [self.post_to_event(post) for post in self.fetch_posts(limit)]

    def post_to_event(self, post: dict[str, Any]) -> Event:
        title = post.get("title", "")
        selftext = post.get("selftext", "")
        raw_text = _raw_text(title, selftext)
        matches = resolve_tickers(raw_text)
        created_utc = post.get("created_utc")
        event_time = _utc_from_timestamp(created_utc) if created_utc is not None else datetime.now(timezone.utc)

        return Event(
            event_id=f"reddit:{post.get('id', '')}",
            source="reddit",
            event_time=event_time,
            ingestion_time=datetime.now(timezone.utc),
            raw_text=raw_text,
            entities=[_match_to_entity(match) for match in matches],
            narratives=[],
            confidence=_confidence_from_matches(matches),
            raw_payload={
                "subreddit": post.get("subreddit"),
                "author": post.get("author"),
                "score": post.get("score"),
                "num_comments": post.get("num_comments"),
                "permalink": post.get("permalink"),
                "created_utc": created_utc,
            },
        )

    def _fetch_mock_posts(self, limit: int) -> list[dict[str, Any]]:
        LOGGER.info("Using mock Reddit ingestion mode.")
        return MOCK_POSTS[:limit]

    def _fetch_praw_posts(self, limit: int) -> list[dict[str, Any]]:
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        user_agent = os.getenv("REDDIT_USER_AGENT")

        missing = [
            name
            for name, value in (
                ("REDDIT_CLIENT_ID", client_id),
                ("REDDIT_CLIENT_SECRET", client_secret),
                ("REDDIT_USER_AGENT", user_agent),
            )
            if not value
        ]
        if missing:
            raise RedditConfigurationError(
                "REDDIT_INGESTION_MODE=praw requires "
                + ", ".join(missing)
                + ". Register an app if needed, set credentials in .env, or use REDDIT_INGESTION_MODE=mock."
            )

        try:
            import praw
        except ImportError as exc:
            raise RedditConfigurationError(
                "REDDIT_INGESTION_MODE=praw requires the optional PRAW dependency. "
                "Install project dependencies with python3 -m pip install -e '.[dev]'."
            ) from exc

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        per_subreddit_limit = max(1, limit // len(self.subreddits) + 1)
        posts: list[dict[str, Any]] = []
        LOGGER.info("Fetching recent Reddit posts from %s with limit=%s.", ", ".join(self.subreddits), limit)
        LOGGER.info("PRAW manages Reddit API rate-limit responses; this provider uses small listing limits.")

        for subreddit_name in self.subreddits:
            if len(posts) >= limit:
                break
            subreddit = reddit.subreddit(subreddit_name)
            for submission in subreddit.new(limit=per_subreddit_limit):
                posts.append(_post_from_praw_submission(submission))
                if len(posts) >= limit:
                    break

        return posts


def _post_from_praw_submission(submission: RedditPostLike) -> dict[str, Any]:
    return {
        "id": submission.id,
        "title": submission.title or "",
        "selftext": submission.selftext or "",
        "subreddit": str(submission.subreddit) if submission.subreddit is not None else None,
        "author": str(submission.author) if submission.author is not None else None,
        "score": submission.score,
        "num_comments": submission.num_comments,
        "permalink": submission.permalink,
        "created_utc": submission.created_utc,
    }


def fetch_recent_reddit_events(limit: int = 25) -> list[Event]:
    return RedditProvider().fetch_events(limit=limit)


def _print_summary(mode: str, posts: list[dict[str, Any]], events: list[Event]) -> None:
    ticker_counter: Counter[str] = Counter(
        entity["ticker"] for event in events for entity in event.entities if "ticker" in entity
    )
    print(f"ingestion mode: {mode}")
    print(f"total posts fetched: {len(posts)}")
    print(f"events created: {len(events)}")
    print(f"tickers detected: {sum(ticker_counter.values())}")
    top = ", ".join(f"{ticker}:{count}" for ticker, count in ticker_counter.most_common(10))
    print(f"top detected tickers: {top or 'none'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest recent Reddit-like stock posts into SQLite.")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    provider = RedditProvider()
    posts = provider.fetch_posts(limit=args.limit)
    events = [provider.post_to_event(post) for post in posts]

    connection = connect()
    initialize(connection)
    insert_events(connection, events)
    connection.close()

    _print_summary(provider.mode, posts, events)


if __name__ == "__main__":
    main()

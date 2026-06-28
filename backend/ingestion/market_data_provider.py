from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone
from typing import Protocol

from backend.database.db import connect, initialize, insert_market_bars
from backend.models.market_data import MarketBar

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


DEFAULT_MARKET_DATA_MODE = "mock"


class MarketDataProviderError(RuntimeError):
    pass


class MarketDataProvider(Protocol):
    def fetch_bars(
        self,
        tickers: list[str],
        start: datetime,
        end: datetime,
    ) -> list[MarketBar]:
        ...


class MockMarketDataProvider:
    source = "mock_market_data"

    def fetch_bars(
        self,
        tickers: list[str],
        start: datetime,
        end: datetime,
    ) -> list[MarketBar]:
        bars: list[MarketBar] = []
        current = _as_utc(start).replace(minute=0, second=0, microsecond=0)
        end = _as_utc(end).replace(minute=0, second=0, microsecond=0)
        while current <= end:
            hour_index = int(current.timestamp() // 3600)
            for ticker in sorted({ticker.upper() for ticker in tickers}):
                bars.append(_mock_bar(ticker, current, hour_index))
            current += timedelta(hours=1)
        return bars


class YFinanceMarketDataProvider:
    source = "yfinance"

    def fetch_bars(
        self,
        tickers: list[str],
        start: datetime,
        end: datetime,
    ) -> list[MarketBar]:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise MarketDataProviderError(
                "MARKET_DATA_MODE=yfinance requires yfinance. Install it explicitly or use MARKET_DATA_MODE=mock."
            ) from exc

        bars: list[MarketBar] = []
        try:
            for ticker in sorted({ticker.upper() for ticker in tickers}):
                frame = yf.download(
                    ticker,
                    start=_as_utc(start).date().isoformat(),
                    end=(_as_utc(end) + timedelta(days=1)).date().isoformat(),
                    interval="1h",
                    progress=False,
                    auto_adjust=False,
                )
                if frame.empty:
                    continue
                for index, row in frame.iterrows():
                    timestamp = index.to_pydatetime()
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                    timestamp = timestamp.astimezone(timezone.utc)
                    bars.append(
                        MarketBar(
                            ticker=ticker,
                            timestamp=timestamp,
                            open=float(row["Open"]),
                            high=float(row["High"]),
                            low=float(row["Low"]),
                            close=float(row["Close"]),
                            volume=int(row["Volume"]),
                            source=self.source,
                        )
                    )
        except Exception as exc:  # pragma: no cover - network/provider behavior is not deterministic.
            raise MarketDataProviderError(
                "yfinance market data fetch failed. Use MARKET_DATA_MODE=mock for offline deterministic development."
            ) from exc
        return bars


def _load_environment() -> None:
    if load_dotenv is not None:
        load_dotenv()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _ticker_seed(ticker: str) -> int:
    return sum((index + 1) * ord(char) for index, char in enumerate(ticker))


def _mock_bar(ticker: str, timestamp: datetime, hour_index: int) -> MarketBar:
    seed = _ticker_seed(ticker)
    base = 75 + seed % 180
    drift = (hour_index % 240) * (0.02 + (seed % 7) * 0.003)
    wave = ((hour_index + seed) % 11 - 5) * 0.08
    close = round(base + drift + wave, 2)
    open_price = round(close - 0.12 + (seed % 5) * 0.03, 2)
    high = round(max(open_price, close) + 0.4 + (seed % 3) * 0.05, 2)
    low = round(min(open_price, close) - 0.4 - (seed % 4) * 0.04, 2)
    volume = 100_000 + (seed * 97 + hour_index * 13) % 900_000
    return MarketBar(
        ticker=ticker,
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        source=MockMarketDataProvider.source,
        ingestion_time=timestamp,
    )


def get_market_data_provider(mode: str | None = None) -> MarketDataProvider:
    _load_environment()
    selected_mode = (mode or os.getenv("MARKET_DATA_MODE", DEFAULT_MARKET_DATA_MODE)).lower()
    if selected_mode == "mock":
        return MockMarketDataProvider()
    if selected_mode == "yfinance":
        return YFinanceMarketDataProvider()
    raise MarketDataProviderError(f"Unsupported MARKET_DATA_MODE={selected_mode!r}. Use 'mock' or 'yfinance'.")


def fetch_market_snapshot(ticker: str) -> dict:
    provider = get_market_data_provider("mock")
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    bars = provider.fetch_bars([ticker], now, now)
    latest = bars[0]
    return {"ticker": latest.ticker, "close": latest.close, "source": latest.source}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch or generate OHLCV market bars.")
    parser.add_argument("--tickers", required=True, help="Comma-separated tickers, e.g. AAPL,TSLA,SPY,QQQ")
    parser.add_argument("--days", type=int, default=10)
    args = parser.parse_args()

    _load_environment()
    mode = os.getenv("MARKET_DATA_MODE", DEFAULT_MARKET_DATA_MODE).lower()
    tickers = [ticker.strip().upper() for ticker in args.tickers.split(",") if ticker.strip()]
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    provider = get_market_data_provider(mode)
    bars = provider.fetch_bars(tickers, start, end)

    connection = connect()
    initialize(connection)
    try:
        insert_market_bars(connection, bars)
    finally:
        connection.close()

    if bars:
        timestamps = [bar.timestamp for bar in bars]
        time_range = f"{min(timestamps).isoformat()} to {max(timestamps).isoformat()}"
    else:
        time_range = "none"

    print(f"market data mode: {mode}")
    print(f"tickers processed: {len(set(tickers))}")
    print(f"bars created: {len(bars)}")
    print(f"time range: {time_range}")


if __name__ == "__main__":
    main()

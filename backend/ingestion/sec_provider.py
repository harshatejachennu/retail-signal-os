from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Protocol

from backend.database.db import connect, initialize, insert_sec_filings
from backend.models.sec_filing import SECFiling

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


DEFAULT_SEC_DATA_MODE = "mock"
SUPPORTED_FORMS = ("8-K", "10-Q", "10-K", "Form 4")

# Small checkpoint mapping only. A full ticker/CIK database belongs in a later data layer.
TICKER_TO_CIK = {
    "AAPL": "0000320193",
    "TSLA": "0001318605",
    "NVDA": "0001045810",
    "AMD": "0000002488",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "META": "0001326801",
    "AMZN": "0001018724",
    "NFLX": "0001065280",
    "INTC": "0000050863",
    "COIN": "0001679788",
    "MSTR": "0001050446",
    "PLTR": "0001321655",
}


class SECProviderError(RuntimeError):
    pass


class SECProvider(Protocol):
    def fetch_filings(self, tickers: list[str], start: datetime, end: datetime) -> list[SECFiling]:
        ...


class MockSECProvider:
    source = "mock_sec"

    def fetch_filings(self, tickers: list[str], start: datetime, end: datetime) -> list[SECFiling]:
        start = _as_utc(start)
        end = _as_utc(end)
        filings: list[SECFiling] = []
        for ticker in sorted({ticker.upper() for ticker in tickers}):
            cik = ticker_to_cik(ticker)
            if cik is None:
                continue
            for index, form_type in enumerate(_forms_for_ticker(ticker)):
                filed_at = _mock_filing_time(start, end, ticker, index)
                filings.append(_mock_filing(ticker, cik, form_type, filed_at, index))
        return filings


class RealSECProvider:
    source = "sec_edgar"

    def __init__(self, user_agent: str | None = None, pause_seconds: float = 0.2) -> None:
        self.user_agent = user_agent or os.getenv("SEC_USER_AGENT")
        self.pause_seconds = pause_seconds
        if not self.user_agent:
            raise SECProviderError(
                "SEC_DATA_MODE=real requires SEC_USER_AGENT with contact information. "
                "Set SEC_USER_AGENT or use SEC_DATA_MODE=mock."
            )

    def fetch_filings(self, tickers: list[str], start: datetime, end: datetime) -> list[SECFiling]:
        filings: list[SECFiling] = []
        for ticker in sorted({ticker.upper() for ticker in tickers}):
            cik = ticker_to_cik(ticker)
            if cik is None:
                continue
            filings.extend(self._fetch_submissions_for_ticker(ticker, cik, _as_utc(start), _as_utc(end)))
            time.sleep(self.pause_seconds)
        return filings

    def _fetch_submissions_for_ticker(
        self,
        ticker: str,
        cik: str,
        start: datetime,
        end: datetime,
    ) -> list[SECFiling]:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise SECProviderError(
                "SEC network fetch failed. Use SEC_DATA_MODE=mock for deterministic offline development."
            ) from exc

        recent = payload.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        accepted_dates = recent.get("acceptanceDateTime", [])
        accessions = recent.get("accessionNumber", [])
        documents = recent.get("primaryDocument", [])
        results: list[SECFiling] = []
        for index, form_type in enumerate(forms):
            if form_type not in SUPPORTED_FORMS:
                continue
            filed_at = datetime.fromisoformat(filing_dates[index]).replace(tzinfo=timezone.utc)
            if filed_at < start or filed_at > end:
                continue
            accession = accessions[index]
            accession_path = accession.replace("-", "")
            document = documents[index] if index < len(documents) else ""
            accepted_at = _parse_sec_acceptance(accepted_dates[index]) if index < len(accepted_dates) else None
            results.append(
                SECFiling(
                    filing_id=f"sec:{ticker}:{accession}",
                    ticker=ticker,
                    cik=cik,
                    form_type=form_type,
                    filed_at=filed_at,
                    accepted_at=accepted_at,
                    accession_number=accession,
                    filing_url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_path}/{document}",
                    title=f"{ticker} {form_type}",
                    summary=f"{form_type} filing from SEC EDGAR submissions feed.",
                    source=self.source,
                    raw_payload={"primaryDocument": document},
                )
            )
        return results


def _load_environment() -> None:
    if load_dotenv is not None:
        load_dotenv()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def ticker_to_cik(ticker: str) -> str | None:
    return TICKER_TO_CIK.get(ticker.upper())


def _forms_for_ticker(ticker: str) -> list[str]:
    forms = list(SUPPORTED_FORMS)
    offset = sum(ord(char) for char in ticker) % len(forms)
    return forms[offset:] + forms[:offset]


def _mock_filing_time(start: datetime, end: datetime, ticker: str, index: int) -> datetime:
    span_seconds = max(int((end - start).total_seconds()), 3600)
    seed = sum((position + 1) * ord(char) for position, char in enumerate(ticker)) + index * 1729
    return start + timedelta(seconds=seed % span_seconds)


def _mock_filing(ticker: str, cik: str, form_type: str, filed_at: datetime, index: int) -> SECFiling:
    accession = f"{cik}-{filed_at:%Y%m%d}-{index:04d}"
    accepted_at = filed_at + timedelta(minutes=7 + index)
    title = f"{ticker} {form_type} mock filing"
    summary_by_form = {
        "8-K": "Current report describing a potentially material company update.",
        "Form 4": "Insider transaction disclosure.",
        "10-Q": "Quarterly report with financial statements and management discussion.",
        "10-K": "Annual report with audited financial statements and risk factors.",
    }
    return SECFiling(
        filing_id=f"mock-sec:{ticker}:{accession}",
        ticker=ticker,
        cik=cik,
        form_type=form_type,
        filed_at=filed_at,
        accepted_at=accepted_at,
        ingestion_time=filed_at,
        accession_number=accession,
        filing_url=f"https://www.sec.gov/mock/{ticker}/{accession}",
        title=title,
        summary=summary_by_form[form_type],
        source=MockSECProvider.source,
        raw_payload={"mock": True, "sequence": index},
    )


def _parse_sec_acceptance(value: str) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def get_sec_provider(mode: str | None = None) -> SECProvider:
    _load_environment()
    selected_mode = (mode or os.getenv("SEC_DATA_MODE", DEFAULT_SEC_DATA_MODE)).lower()
    if selected_mode == "mock":
        return MockSECProvider()
    if selected_mode == "real":
        return RealSECProvider()
    raise SECProviderError(f"Unsupported SEC_DATA_MODE={selected_mode!r}. Use 'mock' or 'real'.")


def fetch_recent_filings(ticker: str) -> list[dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30)
    return [filing.model_dump(mode="json") for filing in get_sec_provider().fetch_filings([ticker], start, end)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch or generate SEC filing metadata.")
    parser.add_argument("--tickers", required=True, help="Comma-separated tickers, e.g. AAPL,TSLA,NVDA")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()

    _load_environment()
    mode = os.getenv("SEC_DATA_MODE", DEFAULT_SEC_DATA_MODE).lower()
    tickers = [ticker.strip().upper() for ticker in args.tickers.split(",") if ticker.strip()]
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    provider = get_sec_provider(mode)
    filings = provider.fetch_filings(tickers, start, end)

    connection = connect()
    initialize(connection)
    try:
        insert_sec_filings(connection, filings)
    finally:
        connection.close()

    form_counts = Counter(filing.form_type for filing in filings)
    if filings:
        timestamps = [filing.filed_at for filing in filings]
        time_range = f"{min(timestamps).isoformat()} to {max(timestamps).isoformat()}"
    else:
        time_range = "none"
    counts = ", ".join(f"{form}:{count}" for form, count in sorted(form_counts.items())) or "none"

    print(f"SEC data mode: {mode}")
    print(f"tickers processed: {len(set(tickers))}")
    print(f"filings created: {len(filings)}")
    print(f"form type counts: {counts}")
    print(f"time range: {time_range}")


if __name__ == "__main__":
    main()

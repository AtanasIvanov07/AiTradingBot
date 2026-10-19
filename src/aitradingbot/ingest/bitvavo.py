"""Bitvavo public candles API: the exact EUR markets the bot will trade.

``GET /v2/{market}/candles`` returns up to 1440 candles, **newest first**, as
``[open_time_ms, open, high, low, close, volume]`` with prices as strings. We page backwards from
``end`` until the start of the requested range (or the market's listing) is reached.
Public endpoint, no API key; rate limit is 1000 weight/minute and a candles call costs 1.
"""

from __future__ import annotations

import gzip
import json
import logging
import time
from pathlib import Path
from typing import Any

import pandas as pd

from aitradingbot.ingest.common import (
    OHLCV_COLUMNS,
    Dataset,
    HttpGet,
    clean,
    data_dir,
    drop_unclosed,
    http_get,
    normalize_ohlcv,
    sha256_file,
    write_atomic,
    write_clean,
)

log = logging.getLogger(__name__)

API = "https://api.bitvavo.com/v2"
MAX_LIMIT = 1440
PAUSE_SECONDS = 0.1


def market_to_pair(market: str) -> str:
    return market.replace("-", "/")


def fetch_candles(
    market: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    get: HttpGet = http_get,
    pause: float = PAUSE_SECONDS,
) -> list[list[Any]]:
    rows: list[list[Any]] = []
    cursor = end_ms
    while cursor >= start_ms:
        url = (
            f"{API}/{market}/candles?interval={interval}&limit={MAX_LIMIT}"
            f"&start={start_ms}&end={cursor}"
        )
        page = json.loads(get(url))
        if isinstance(page, dict):
            raise RuntimeError(f"Bitvavo error for {url}: {page}")
        if not page:
            break
        rows.extend(page)
        oldest = min(int(row[0]) for row in page)
        if len(page) < MAX_LIMIT or oldest <= start_ms:
            break
        cursor = oldest - 1
        time.sleep(pause)
    return rows


def parse_candles(rows: list[list[Any]]) -> pd.DataFrame:
    frame = pd.DataFrame([row[:6] for row in rows], columns=OHLCV_COLUMNS)
    frame["open_time"] = pd.to_datetime(frame["open_time"].astype("int64"), unit="ms", utc=True)
    return normalize_ohlcv(frame)


def ingest(
    markets: list[str],
    timeframes: list[str],
    start: str,
    end: str | None = None,
    root: Path | None = None,
    get: HttpGet = http_get,
) -> list[Path]:
    base = root or data_dir()
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ts = pd.Timestamp(end, tz="UTC") if end else pd.Timestamp.now(tz="UTC")
    end_ms = int(end_ts.timestamp() * 1000)
    downloaded_at = pd.Timestamp.now(tz="UTC").strftime("%Y%m%dT%H%M%SZ")
    written = []
    for market in markets:
        for timeframe in timeframes:
            rows = fetch_candles(market, timeframe, start_ms, end_ms, get)
            if not rows:
                raise FileNotFoundError(f"no Bitvavo candles for {market} {timeframe}")
            raw = base / "raw" / "bitvavo" / f"{market}_{timeframe}_{downloaded_at}.json.gz"
            write_atomic(raw, gzip.compress(json.dumps(rows).encode("utf-8")))
            frame = drop_unclosed(parse_candles(rows), timeframe)
            frame = frame[frame["open_time"] <= end_ts].reset_index(drop=True)
            frame, cleaning = clean(frame, timeframe)
            inputs = [{"raw_file": raw.name, "sha256": sha256_file(raw), "api": API}]
            notes = {"requested_start": start, "requested_end": end_ts.isoformat(), **cleaning}
            dataset = Dataset("bitvavo", market_to_pair(market), timeframe)
            path = write_clean(dataset, frame, inputs, root, notes)
            log.info("bitvavo %s %s: %d rows -> %s", market, timeframe, len(frame), path)
            written.append(path)
    return written

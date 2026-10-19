"""Binance public market data (data.binance.vision): monthly spot kline zips + SHA-256 checksums.

No account needed; Binance's EEA trading restrictions don't affect this public archive. Used for
long-horizon research in USDT (BTCUSDT/ETHUSDT from Aug 2017).

Format: no header (handled if present); first six columns are open_time, open, high, low, close,
volume. Timestamps are milliseconds up to Dec 2024 and **microseconds from Jan 2025**.
"""

from __future__ import annotations

import io
import logging
import zipfile
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
from pathlib import Path
from typing import Any

import pandas as pd

from aitradingbot.ingest.common import (
    OHLCV_COLUMNS,
    Dataset,
    HttpGet,
    clean,
    data_dir,
    http_get,
    normalize_ohlcv,
    sha256_bytes,
    sha256_file,
    write_atomic,
    write_clean,
)

log = logging.getLogger(__name__)

BASE_URL = "https://data.binance.vision/data/spot/monthly/klines"
QUOTES = ("USDT", "USDC", "EUR", "BTC")
MICROSECOND_THRESHOLD = 10**14  # ms timestamps are ~1.7e12, µs timestamps ~1.7e15


def month_range(start: str, end: str) -> list[str]:
    return [str(period) for period in pd.period_range(start, end, freq="M")]


def last_complete_month(now: pd.Timestamp | None = None) -> str:
    current = now if now is not None else pd.Timestamp.now(tz="UTC")
    return str(current.tz_localize(None).to_period("M") - 1)


def symbol_to_pair(symbol: str) -> str:
    for quote in QUOTES:
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return f"{symbol[: -len(quote)]}/{quote}"
    raise ValueError(f"unknown quote currency in {symbol}")


def archive_name(symbol: str, interval: str, month: str) -> str:
    return f"{symbol}-{interval}-{month}.zip"


def raw_path(root: Path, symbol: str, interval: str, month: str) -> Path:
    return (
        root / "raw" / "binance" / "spot" / "monthly" / "klines" / symbol / interval
    ) / archive_name(symbol, interval, month)


def download_month(
    symbol: str, interval: str, month: str, root: Path, get: HttpGet = http_get
) -> Path | None:
    """Download and checksum-verify one monthly zip. Returns None if Binance has no file for it.

    Raw files are immutable: an existing zip is re-verified against its saved checksum, not
    re-downloaded.
    """
    path = raw_path(root, symbol, interval, month)
    checksum_path = path.with_name(path.name + ".CHECKSUM")
    if path.exists() and checksum_path.exists():
        expected = checksum_path.read_text(encoding="utf-8").split()[0]
        if sha256_file(path) != expected:
            raise ValueError(f"local file corrupted (checksum mismatch): {path}")
        return path
    url = f"{BASE_URL}/{symbol}/{interval}/{archive_name(symbol, interval, month)}"
    try:
        archive = get(url)
    except FileNotFoundError:
        return None
    checksum_text = get(url + ".CHECKSUM").decode("utf-8")
    if sha256_bytes(archive) != checksum_text.split()[0]:
        raise ValueError(f"checksum mismatch for {url}")
    write_atomic(path, archive)
    write_atomic(checksum_path, checksum_text.encode("utf-8"))
    return path


def parse_kline_csv(data: bytes) -> pd.DataFrame:
    first_char = data.lstrip()[:1]
    header = None if first_char.isdigit() else 0
    frame = pd.read_csv(io.BytesIO(data), header=header, usecols=range(6), names=OHLCV_COLUMNS)
    raw_time = frame["open_time"].astype("int64")
    milliseconds = raw_time.where(raw_time < MICROSECOND_THRESHOLD, raw_time // 1000)
    frame["open_time"] = pd.to_datetime(milliseconds, unit="ms", utc=True)
    return normalize_ohlcv(frame)


def read_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        (member,) = archive.namelist()
        return parse_kline_csv(archive.read(member))


def ingest(
    symbols: list[str],
    timeframes: list[str],
    start: str,
    end: str,
    root: Path | None = None,
    get: HttpGet = http_get,
    workers: int = 8,
) -> list[Path]:
    base = root or data_dir()
    months = month_range(start, end)
    written = []
    for symbol in symbols:
        for timeframe in timeframes:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                paths = list(
                    pool.map(
                        download_month,
                        repeat(symbol),
                        repeat(timeframe),
                        months,
                        repeat(base),
                        repeat(get),
                    )
                )
            available = [(m, p) for m, p in zip(months, paths, strict=True) if p is not None]
            missing = [m for m, p in zip(months, paths, strict=True) if p is None]
            if not available:
                raise FileNotFoundError(f"no Binance data for {symbol} {timeframe}")
            frame = normalize_ohlcv(pd.concat([read_zip(p) for _, p in available]))
            frame, cleaning = clean(frame, timeframe)
            inputs: list[dict[str, Any]] = [
                {"archive": p.name, "sha256": sha256_file(p)} for _, p in available
            ]
            notes: dict[str, Any] = {
                "months_requested": f"{start}..{end}",
                "months_not_published": missing,
                **cleaning,
            }
            dataset = Dataset("binance", symbol_to_pair(symbol), timeframe)
            path = write_clean(dataset, frame, inputs, root, notes)
            log.info("binance %s %s: %d rows -> %s", symbol, timeframe, len(frame), path)
            written.append(path)
    return written

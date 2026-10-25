"""Binance USD-M perpetual funding rates (data.binance.vision): the H6 crowding signal.

Same public archive as the spot klines (monthly zips + SHA-256 checksums, no account). The perpetual
is only read as a signal; nothing here trades it. BTCUSDT and ETHUSDT files start in Jan 2020.

Format: a header ``calc_time,funding_interval_hours,last_funding_rate``. ``calc_time`` is the
settlement time in milliseconds, a few ms after the hour (e.g. 1748736000001). It's stored as
``funding_time`` rounded to the hour; a settlement more than ``SNAP_TOLERANCE`` off the hour is kept
as it is, so validation flags it instead of it being silently moved.
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from itertools import repeat
from pathlib import Path
from typing import Any

import pandas as pd

from aitradingbot.ingest.binance import MICROSECOND_THRESHOLD, download_verified, month_range
from aitradingbot.ingest.common import HttpGet, data_dir, http_get, sha256_file

log = logging.getLogger(__name__)

BASE_URL = "https://data.binance.vision/data/futures/um/monthly/fundingRate"
ARCHIVE_START = "2020-01"
SOURCE = "binance_funding"
FUNDING_COLUMNS = ["funding_time", "interval_hours", "rate"]
SNAP_TOLERANCE = pd.Timedelta(minutes=5)


def archive_name(symbol: str, month: str) -> str:
    return f"{symbol}-fundingRate-{month}.zip"


def raw_path(root: Path, symbol: str, month: str) -> Path:
    return (
        root / "raw" / "binance" / "futures" / "um" / "monthly" / "fundingRate" / symbol
    ) / archive_name(symbol, month)


def clean_path(symbol: str, root: Path | None = None) -> Path:
    return (root or data_dir()) / "clean" / SOURCE / f"{symbol}.parquet"


def manifest_path(symbol: str, root: Path | None = None) -> Path:
    return clean_path(symbol, root).with_suffix(".manifest.json")


def load(symbol: str, root: Path | None = None) -> pd.DataFrame:
    return pd.read_parquet(clean_path(symbol, root))


def list_symbols(root: Path | None = None) -> list[str]:
    folder = (root or data_dir()) / "clean" / SOURCE
    return [path.stem for path in sorted(folder.glob("*.parquet"))]


def download_month(symbol: str, month: str, root: Path, get: HttpGet = http_get) -> Path | None:
    url = f"{BASE_URL}/{symbol}/{archive_name(symbol, month)}"
    return download_verified(url, raw_path(root, symbol, month), get)


def snap_to_hour(times: pd.Series) -> pd.Series:
    """Round settlement times to the hour, unless they are more than SNAP_TOLERANCE off it."""
    rounded = times.dt.round("1h")
    snapped: pd.Series = rounded.where((times - rounded).abs() <= SNAP_TOLERANCE, times)
    return snapped


def normalize_funding(frame: pd.DataFrame) -> pd.DataFrame:
    """Coerce to the stored schema, sort by funding_time and drop exact duplicate rows.

    As with candles, rows sharing a time but differing in values are kept so validation reports
    them, and unparseable numbers become NaN.
    """
    out = frame.loc[:, FUNDING_COLUMNS].copy()
    out["funding_time"] = pd.to_datetime(out["funding_time"], utc=True)
    for column in FUNDING_COLUMNS[1:]:
        out[column] = pd.to_numeric(out[column], errors="coerce").astype("float64")
    out = out.drop_duplicates().sort_values("funding_time", kind="stable")
    return out.reset_index(drop=True)


def parse_funding_csv(data: bytes) -> pd.DataFrame:
    first_char = data.lstrip()[:1]
    header = None if first_char.isdigit() else 0
    frame = pd.read_csv(io.BytesIO(data), header=header, usecols=range(3), names=FUNDING_COLUMNS)
    raw_time = frame["funding_time"].astype("int64")
    milliseconds = raw_time.where(raw_time < MICROSECOND_THRESHOLD, raw_time // 1000)
    frame["funding_time"] = snap_to_hour(pd.to_datetime(milliseconds, unit="ms", utc=True))
    return normalize_funding(frame)


def read_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        (member,) = archive.namelist()
        return parse_funding_csv(archive.read(member))


def write_clean(
    symbol: str,
    frame: pd.DataFrame,
    inputs: list[dict[str, Any]],
    root: Path | None = None,
    notes: dict[str, Any] | None = None,
) -> Path:
    """Write one symbol's settlements as Parquet plus a JSON manifest, like the candle series."""
    path = clean_path(symbol, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    manifest: dict[str, Any] = {
        "source": SOURCE,
        "symbol": symbol,
        "timestamp_convention": "funding_time = settlement time, UTC, rounded to the hour",
        "rate_convention": "rate per settlement (fraction), paid by longs to shorts when > 0",
        "rows": len(frame),
        "first_funding_time": frame["funding_time"].min().isoformat() if len(frame) else None,
        "last_funding_time": frame["funding_time"].max().isoformat() if len(frame) else None,
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "parquet_sha256": sha256_file(path),
        "inputs": inputs,
        "notes": notes or {},
    }
    manifest_path(symbol, root).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return path


def ingest(
    symbols: list[str],
    start: str,
    end: str,
    root: Path | None = None,
    get: HttpGet = http_get,
    workers: int = 8,
) -> list[Path]:
    base = root or data_dir()
    months = month_range(max(start, ARCHIVE_START), end)
    written = []
    for symbol in symbols:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            paths = list(
                pool.map(download_month, repeat(symbol), months, repeat(base), repeat(get))
            )
        available = [(m, p) for m, p in zip(months, paths, strict=True) if p is not None]
        missing = [m for m, p in zip(months, paths, strict=True) if p is None]
        if not available:
            raise FileNotFoundError(f"no Binance funding data for {symbol}")
        frame = normalize_funding(pd.concat([read_zip(p) for _, p in available]))
        inputs: list[dict[str, Any]] = [
            {"archive": p.name, "sha256": sha256_file(p)} for _, p in available
        ]
        notes: dict[str, Any] = {
            "months_requested": f"{months[0]}..{months[-1]}",
            "months_not_published": missing,
        }
        path = write_clean(symbol, frame, inputs, root, notes)
        log.info("binance funding %s: %d settlements -> %s", symbol, len(frame), path)
        written.append(path)
    return written

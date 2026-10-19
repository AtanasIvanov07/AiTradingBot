"""Shared ingest helpers: canonical candle schema, HTTP with retries, storage and manifests.

Canonical schema for every source: ``open_time`` (UTC timestamp of the candle *open*) followed by
float64 ``open, high, low, close, volume``. Raw downloads under ``data/raw/`` are never edited;
``data/clean/`` is derived from them by these scripts and can be regenerated at any time.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

OHLCV_COLUMNS = ["open_time", "open", "high", "low", "close", "volume"]

TIMEFRAMES: dict[str, pd.Timedelta] = {
    "1h": pd.Timedelta(hours=1),
    "4h": pd.Timedelta(hours=4),
    "1d": pd.Timedelta(days=1),
}

USER_AGENT = "aitradingbot-research/0.1"
RETRY_STATUS = {429, 500, 502, 503, 504}

HttpGet = Callable[[str], bytes]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def data_dir() -> Path:
    """Root of the gitignored data store. Override with the AITB_DATA_DIR environment variable."""
    override = os.environ.get("AITB_DATA_DIR")
    return Path(override) if override else repo_root() / "data"


def http_get(url: str, *, timeout: float = 30.0, retries: int = 4) -> bytes:
    """GET ``url`` with exponential backoff on transient errors.

    HTTP 404 raises FileNotFoundError so callers can treat "not published" specially.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body: bytes = response.read()
                return body
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise FileNotFoundError(url) from exc
            if exc.code not in RETRY_STATUS or attempt == retries:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries:
                raise
        time.sleep(2**attempt)
    raise AssertionError("unreachable")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def write_atomic(path: Path, data: bytes) -> None:
    """Write via a temporary file so an interrupted download never leaves a truncated file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    partial.write_bytes(data)
    partial.replace(path)


def normalize_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    """Coerce to the canonical schema, sort by open_time and drop exact duplicate rows.

    Rows that share an open_time but differ in values are kept on purpose, so that validation
    reports them instead of one being silently discarded. Unparseable numbers become NaN for the
    same reason.
    """
    out = frame.loc[:, OHLCV_COLUMNS].copy()
    out["open_time"] = pd.to_datetime(out["open_time"], utc=True)
    for column in OHLCV_COLUMNS[1:]:
        out[column] = pd.to_numeric(out[column], errors="coerce").astype("float64")
    out = out.drop_duplicates().sort_values("open_time", kind="stable")
    return out.reset_index(drop=True)


def drop_unclosed(
    frame: pd.DataFrame, timeframe: str, now: pd.Timestamp | None = None
) -> pd.DataFrame:
    """Remove candles that have not closed yet (open_time + timeframe > now)."""
    current = now if now is not None else pd.Timestamp.now(tz="UTC")
    closed = frame["open_time"] + TIMEFRAMES[timeframe] <= current
    return frame.loc[closed].reset_index(drop=True)


def drop_misaligned(frame: pd.DataFrame, timeframe: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Drop candles whose open isn't on the UTC timeframe grid, and describe what was dropped.

    Example: after Binance's Feb 2018 outage its archive has hourly candles opening at 09:28:14.
    Snapping them to the hour would mislabel the period they cover, so they become a visible gap.
    """
    times = frame["open_time"]
    aligned = times.dt.floor(TIMEFRAMES[timeframe]) == times
    dropped = times[~aligned]
    note: dict[str, Any] = {}
    if len(dropped):
        note = {
            "count": len(dropped),
            "first": dropped.min().isoformat(),
            "last": dropped.max().isoformat(),
        }
    return frame.loc[aligned].reset_index(drop=True), note


def pair_stem(pair: str) -> str:
    return pair.replace("/", "_")


@dataclass(frozen=True)
class Dataset:
    """One clean candle series, e.g. Dataset("kraken", "BTC/EUR", "1d")."""

    source: str
    pair: str
    timeframe: str

    @property
    def stem(self) -> str:
        return f"{pair_stem(self.pair)}_{self.timeframe}"

    def clean_path(self, root: Path | None = None) -> Path:
        return (root or data_dir()) / "clean" / self.source / f"{self.stem}.parquet"

    def manifest_path(self, root: Path | None = None) -> Path:
        return self.clean_path(root).with_suffix(".manifest.json")

    def load(self, root: Path | None = None) -> pd.DataFrame:
        return pd.read_parquet(self.clean_path(root))


def write_clean(
    dataset: Dataset,
    frame: pd.DataFrame,
    inputs: list[dict[str, Any]],
    root: Path | None = None,
    notes: dict[str, Any] | None = None,
) -> Path:
    """Write a clean series as Parquet plus a JSON manifest describing where it came from."""
    path = dataset.clean_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    manifest: dict[str, Any] = {
        "source": dataset.source,
        "pair": dataset.pair,
        "timeframe": dataset.timeframe,
        "timestamp_convention": "open_time = candle open, UTC",
        "rows": len(frame),
        "first_open_time": frame["open_time"].min().isoformat() if len(frame) else None,
        "last_open_time": frame["open_time"].max().isoformat() if len(frame) else None,
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "parquet_sha256": sha256_file(path),
        "inputs": inputs,
        "notes": notes or {},
    }
    dataset.manifest_path(root).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return path


def list_clean_datasets(root: Path | None = None) -> list[Dataset]:
    """Discover every clean series under data/clean/<source>/<BASE>_<QUOTE>_<timeframe>.parquet."""
    clean = (root or data_dir()) / "clean"
    datasets = []
    for path in sorted(clean.glob("*/*.parquet")):
        pair_part, _, timeframe = path.stem.rpartition("_")
        if timeframe in TIMEFRAMES and pair_part.count("_") == 1:
            datasets.append(Dataset(path.parent.name, pair_part.replace("_", "/"), timeframe))
    return datasets

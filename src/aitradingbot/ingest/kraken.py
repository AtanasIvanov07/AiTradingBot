"""Kraken downloadable OHLCVT history: long EUR-denominated history (BTC/EUR since 2013).

Kraken publishes the full history as a ~10 GB zip split into parts, plus quarterly update zips
(support article 360047124832). Instead of downloading all of it, ``RangeFile`` reads only the
needed CSVs out of the remote archive with HTTP range requests. Local zips work too.

Format (per the archive's MANIFEST.json): no header; columns
``timestamp, open, high, low, close, volume, trades``; one file per pair and interval in minutes,
e.g. ``XBTEUR_1440.csv``. Kraken only writes candles for intervals that had trades, so a gap
means "no trades", not lost data.
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Literal

import pandas as pd

from aitradingbot.ingest.common import (
    OHLCV_COLUMNS,
    Dataset,
    clean,
    normalize_ohlcv,
    sha256_file,
    write_clean,
)
from aitradingbot.ingest.remote import RangeFile, remote_size

log = logging.getLogger(__name__)

CDN = "https://assets.kraken.com/marketing/institutions/"
FULL_PARTS = [f"Kraken_OHLCVT_Full.zip.part{i:02d}" for i in range(5)]
UPDATES = ["Kraken_OHLCVT_2026Q3.zip"]  # quarterly zips published after the full archive's cut-off

KRAKEN_NAMES = {"BTC/EUR": "XBTEUR", "ETH/EUR": "ETHEUR"}
INTERVAL_MINUTES = {"1h": 60, "4h": 240, "1d": 1440}


@dataclass
class Archive:
    """An opened OHLCVT zip, local or remote, plus provenance for the manifest."""

    label: str
    zip: zipfile.ZipFile
    provenance: dict[str, Any] = field(default_factory=dict)


def member_name(names: list[str], pair: str, timeframe: str) -> str | None:
    """Exact (case-insensitive) match on e.g. XBTEUR_1440.csv. Lookalikes such as XBTEURC_1440.csv
    are different markets and must not match."""
    target = f"{KRAKEN_NAMES[pair]}_{INTERVAL_MINUTES[timeframe]}.csv".lower()
    for name in names:
        if PurePosixPath(name).name.lower() == target:
            return name
    return None


def parse_ohlcvt_csv(data: bytes) -> pd.DataFrame:
    frame = pd.read_csv(io.BytesIO(data), header=None, usecols=range(6), names=OHLCV_COLUMNS)
    seconds = frame["open_time"].astype("int64")
    # The manifest doesn't state the unit; Kraken uses unix seconds. Guard against milliseconds.
    unit: Literal["s", "ms"] = "ms" if len(seconds) and int(seconds.max()) > 10**11 else "s"
    frame["open_time"] = pd.to_datetime(seconds, unit=unit, utc=True)
    return normalize_ohlcv(frame)


def read_manifest(archive: zipfile.ZipFile) -> dict[str, Any]:
    for name in archive.namelist():
        if PurePosixPath(name).name.upper() == "MANIFEST.JSON":
            manifest: dict[str, Any] = json.loads(archive.read(name))
            return manifest
    return {}


def open_remote(label: str, file_names: list[str]) -> Archive:
    urls = [CDN + name for name in file_names]
    sizes = [remote_size(url) for url in urls]
    handle = RangeFile(urls, sizes)
    archive = zipfile.ZipFile(handle)
    provenance = {
        "archive": label,
        "urls": urls,
        "bytes_total": sum(sizes),
        "archive_manifest": read_manifest(archive),
    }
    return Archive(label, archive, provenance)


def open_local(path: Path) -> Archive:
    archive = zipfile.ZipFile(path)
    provenance = {
        "archive": path.name,
        "path": str(path),
        "sha256": sha256_file(path),
        "archive_manifest": read_manifest(archive),
    }
    return Archive(path.name, archive, provenance)


def merge_archives(frames: list[pd.DataFrame]) -> tuple[pd.DataFrame, int]:
    """Combine series from several archives; later archives win on overlapping candles.

    Returns the merged frame and the number of overlapping candles whose values disagreed.
    """
    combined = pd.concat(frames, ignore_index=True)
    overlapping = combined[combined.duplicated("open_time", keep=False)]
    distinct_per_time = overlapping.drop_duplicates().groupby("open_time").size()
    conflicts = int((distinct_per_time > 1).sum())
    merged = combined.drop_duplicates("open_time", keep="last")
    return normalize_ohlcv(merged), conflicts


def ingest(
    archives: list[Archive],
    pairs: list[str],
    timeframes: list[str],
    root: Path | None = None,
) -> list[Path]:
    written = []
    for pair in pairs:
        for timeframe in timeframes:
            frames, inputs = [], []
            for archive in archives:
                name = member_name(archive.zip.namelist(), pair, timeframe)
                if name is None:
                    log.warning("%s: no %s %s file", archive.label, pair, timeframe)
                    continue
                info = archive.zip.getinfo(name)
                frame = parse_ohlcvt_csv(archive.zip.read(name))  # ZipFile verifies the CRC32 here
                frames.append(frame)
                inputs.append(
                    {
                        **archive.provenance,
                        "member": name,
                        "member_crc32": f"{info.CRC:08x}",
                        "rows": len(frame),
                    }
                )
            if not frames:
                raise FileNotFoundError(f"no Kraken data for {pair} {timeframe}")
            merged, conflicts = merge_archives(frames)
            merged, cleaning = clean(merged, timeframe)
            notes = {
                "overlap_conflicts": conflicts,
                "gaps_mean": "Kraken writes no candle for intervals without trades",
                **cleaning,
            }
            path = write_clean(Dataset("kraken", pair, timeframe), merged, inputs, root, notes)
            log.info("kraken %s %s: %d rows -> %s", pair, timeframe, len(merged), path)
            written.append(path)
    return written


def default_remote_archives() -> list[Archive]:
    return [open_remote("Kraken_OHLCVT_Full.zip", FULL_PARTS)] + [
        open_remote(name, [name]) for name in UPDATES
    ]

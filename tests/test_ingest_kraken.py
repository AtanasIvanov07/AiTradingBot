import io
import json
import random
import zipfile
from pathlib import Path

import pandas as pd

from aitradingbot.ingest import kraken
from aitradingbot.ingest.remote import RangeFile

FULL_ROWS = (
    b"1704067200,39000.0,39500.0,38800.0,39400.0,12.5,300\n"
    b"1704153600,39400.0,40000.0,39100.0,39900.0,10.0,250\n"
)
UPDATE_ROWS = (  # overlaps FULL_ROWS on 2024-01-02 with a different close
    b"1704153600,39400.0,40000.0,39100.0,39950.0,10.0,250\n"
    b"1704240000,39950.0,40100.0,39500.0,39800.0,8.0,200\n"
)


def make_zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


def test_member_name_matches_exactly() -> None:
    names = ["XBTEURC_1440.csv", "data/XBTEUR_1440.csv", "XBTEUR_60.csv", "MANIFEST.json"]
    assert kraken.member_name(names, "BTC/EUR", "1d") == "data/XBTEUR_1440.csv"
    assert kraken.member_name(names, "BTC/EUR", "1h") == "XBTEUR_60.csv"
    assert kraken.member_name(names, "ETH/EUR", "1d") is None


def test_parses_unix_seconds() -> None:
    frame = kraken.parse_ohlcvt_csv(FULL_ROWS)
    assert frame["open_time"].tolist() == [
        pd.Timestamp("2024-01-01", tz="UTC"),
        pd.Timestamp("2024-01-02", tz="UTC"),
    ]
    assert list(frame.columns) == ["open_time", "open", "high", "low", "close", "volume"]


def test_later_archive_wins_and_conflicts_are_counted() -> None:
    merged, conflicts = kraken.merge_archives(
        [kraken.parse_ohlcvt_csv(FULL_ROWS), kraken.parse_ohlcvt_csv(UPDATE_ROWS)]
    )
    assert len(merged) == 3
    assert merged.loc[1, "close"] == 39950.0  # the update's value
    assert conflicts == 1


def test_ingest_from_local_zips(tmp_path: Path) -> None:
    manifest = json.dumps({"coverage": {"start": "2024-01-01", "end": "2024-01-02"}}).encode()
    full = tmp_path / "full.zip"
    full.write_bytes(make_zip({"XBTEUR_1440.csv": FULL_ROWS, "MANIFEST.json": manifest}))
    update = tmp_path / "update.zip"
    update.write_bytes(make_zip({"XBTEUR_1440.csv": UPDATE_ROWS}))
    archives = [kraken.open_local(full), kraken.open_local(update)]
    (path,) = kraken.ingest(archives, ["BTC/EUR"], ["1d"], tmp_path / "data")
    assert len(pd.read_parquet(path)) == 3
    written = json.loads(path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
    assert written["notes"]["overlap_conflicts"] == 1
    assert written["inputs"][0]["archive_manifest"]["coverage"]["end"] == "2024-01-02"
    assert len(written["inputs"][0]["sha256"]) == 64


def test_range_file_reads_a_zip_split_into_parts() -> None:
    noise = random.Random(0).randbytes(50_000)  # incompressible, so the archive really is ~50 KB
    payload = make_zip({"XBTEUR_1440.csv": FULL_ROWS * 2000, "noise.bin": noise})
    cuts = [0, 7_000, 20_000, len(payload)]  # noise.bin spans both part boundaries
    parts = {f"part{i}": payload[cuts[i] : cuts[i + 1]] for i in range(3)}
    requested: set[str] = set()

    def get_range(url: str, first: int, last: int) -> bytes:
        requested.add(url)
        return parts[url][first : last + 1]

    handle = RangeFile(list(parts), [len(p) for p in parts.values()], get_range)
    with zipfile.ZipFile(handle) as archive:  # ZipFile verifies each member's CRC32 on read
        assert archive.read("XBTEUR_1440.csv") == FULL_ROWS * 2000
        assert archive.read("noise.bin") == noise
    assert requested == set(parts)

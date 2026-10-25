import json
from collections.abc import Callable
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest

from aitradingbot.ingest import bitvavo

DAY_MS = 86_400_000
START_MS = 1_704_067_200_000  # 2024-01-01


INTERVAL_MS = {"1h": 3_600_000, "4h": 14_400_000, "1d": DAY_MS}


def fake_api(candle_times: list[int], page_size: int) -> Callable[[str], bytes]:
    """Serve newest-first pages like Bitvavo: ``start`` filters on open time, ``end`` on close,
    and only the ``limit`` intervals before ``end`` are searched."""

    def get(url: str) -> bytes:
        query = parse_qs(urlparse(url).query)
        start, end = int(query["start"][0]), int(query["end"][0])
        step = INTERVAL_MS[query["interval"][0]]
        limit = min(int(query["limit"][0]), page_size)
        first = max(start, end - limit * step)
        hits = sorted((t for t in candle_times if t >= first and t + step <= end), reverse=True)
        # open == previous close, as in a continuous 24/7 market
        return json.dumps([[t, "1.5", "2", "1", "1.5", "10"] for t in hits]).encode()

    return get


def test_pages_backwards_until_listing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bitvavo, "MAX_LIMIT", 3)
    times = [START_MS + i * DAY_MS for i in range(8)]
    end = times[-1] + DAY_MS  # the close of the newest candle
    rows = bitvavo.fetch_candles(
        "BTC-EUR", "1d", START_MS - 30 * DAY_MS, end, fake_api(times, 3), pause=0
    )
    got = [int(r[0]) for r in rows]
    assert sorted(got) == times  # nothing lost at the page boundaries
    assert len(got) == len(set(got))  # and nothing fetched twice


def test_pages_past_gaps_and_empty_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bitvavo, "MAX_LIMIT", 3)
    listed = [START_MS + i * DAY_MS for i in range(20)]
    # A 1-day gap (short page) and a 5-day outage (a whole empty window) inside the history.
    times = [t for i, t in enumerate(listed) if i != 15 and not 5 <= i < 10]
    end = times[-1] + DAY_MS
    rows = bitvavo.fetch_candles(
        "BTC-EUR", "1d", START_MS - 30 * DAY_MS, end, fake_api(times, 3), pause=0
    )
    got = [int(r[0]) for r in rows]
    assert sorted(got) == times
    assert len(got) == len(set(got))


def test_end_day_is_inclusive(tmp_path: Path) -> None:
    times = [START_MS + i * DAY_MS for i in range(10)]  # 2024-01-01 .. 2024-01-10
    (path,) = bitvavo.ingest(
        ["BTC-EUR"], ["1d"], "2024-01-01", "2024-01-05", tmp_path, fake_api(times, 1440)
    )
    frame = pd.read_parquet(path)
    assert frame["open_time"].min() == pd.Timestamp("2024-01-01", tz="UTC")
    assert frame["open_time"].max() == pd.Timestamp("2024-01-05", tz="UTC")


def test_error_payload_raises() -> None:
    def get(url: str) -> bytes:
        return b'{"errorCode": 205, "error": "invalid market"}'

    with pytest.raises(RuntimeError, match="invalid market"):
        bitvavo.fetch_candles("NOPE-EUR", "1d", 0, 1, get, pause=0)


def test_ingest_drops_the_unclosed_candle(tmp_path: Path) -> None:
    now = pd.Timestamp.now(tz="UTC").floor("D")
    times = [
        int((now - pd.Timedelta(days=d)).timestamp() * 1000) for d in range(5)
    ]  # includes today
    start = (now - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    (path,) = bitvavo.ingest(["BTC-EUR"], ["1d"], start, None, tmp_path, fake_api(times, 1440))
    frame = pd.read_parquet(path)
    assert len(frame) == 4  # today's candle hasn't closed yet
    assert frame["open_time"].max() == now - pd.Timedelta(days=1)
    assert path.name == "BTC_EUR_1d.parquet"
    assert list((tmp_path / "raw" / "bitvavo").glob("BTC-EUR_1d_*.json.gz"))

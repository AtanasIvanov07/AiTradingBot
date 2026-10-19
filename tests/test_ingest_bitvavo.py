import json
from collections.abc import Callable
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest

from aitradingbot.ingest import bitvavo

DAY_MS = 86_400_000
START_MS = 1_704_067_200_000  # 2024-01-01


def fake_api(candle_times: list[int], page_size: int) -> Callable[[str], bytes]:
    """Serve newest-first pages like Bitvavo, honouring start/end/limit."""

    def get(url: str) -> bytes:
        query = parse_qs(urlparse(url).query)
        start, end = int(query["start"][0]), int(query["end"][0])
        limit = min(int(query["limit"][0]), page_size)
        hits = sorted((t for t in candle_times if start <= t <= end), reverse=True)[:limit]
        return json.dumps([[t, "1", "2", "0.5", "1.5", "10"] for t in hits]).encode()

    return get


def test_pages_backwards_until_listing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bitvavo, "MAX_LIMIT", 3)
    times = [START_MS + i * DAY_MS for i in range(8)]
    rows = bitvavo.fetch_candles(
        "BTC-EUR", "1d", START_MS - 30 * DAY_MS, times[-1], fake_api(times, 3), pause=0
    )
    assert sorted(int(r[0]) for r in rows) == times


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

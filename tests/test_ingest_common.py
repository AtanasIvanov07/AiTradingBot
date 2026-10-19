import json
from pathlib import Path

import pandas as pd
from conftest import MakeCandles

from aitradingbot.ingest.common import (
    Dataset,
    drop_misaligned,
    drop_unclosed,
    list_clean_datasets,
    normalize_ohlcv,
    write_clean,
)


def test_normalize_sorts_dedupes_and_keeps_conflicts(candles: MakeCandles) -> None:
    frame = candles(periods=3)
    messy = pd.concat([frame.iloc[::-1], frame.iloc[[0]], frame.iloc[[1]].assign(close=999.0)])
    out = normalize_ohlcv(messy)
    assert out["open_time"].is_monotonic_increasing
    assert len(out) == 4  # exact duplicate dropped, conflicting duplicate kept for validation
    assert out["close"].dtype == "float64"


def test_normalize_turns_garbage_into_nan(candles: MakeCandles) -> None:
    frame = candles(periods=2).astype({"close": "object"})
    frame.loc[0, "close"] = "n/a"
    assert normalize_ohlcv(frame)["close"].isna().sum() == 1


def test_drop_misaligned_removes_off_grid_candles(candles: MakeCandles) -> None:
    frame = candles(periods=6, timeframe="1h")
    frame.loc[3, "open_time"] = pd.Timestamp("2024-01-01 03:28", tz="UTC")  # off the hourly grid
    kept, note = drop_misaligned(frame, "1h")
    assert len(kept) == 5
    assert note["count"] == 1 and note["first"].startswith("2024-01-01T03:28")
    assert drop_misaligned(kept, "1h")[1] == {}


def test_drop_unclosed_removes_the_running_candle(candles: MakeCandles) -> None:
    frame = candles(start="2024-01-01", periods=3)
    now = pd.Timestamp("2024-01-03 12:00", tz="UTC")  # Jan 3 candle still open
    assert len(drop_unclosed(frame, "1d", now)) == 2


def test_write_clean_and_discover(tmp_path: Path, candles: MakeCandles) -> None:
    dataset = Dataset("kraken", "BTC/EUR", "1d")
    frame = candles(periods=5)
    path = write_clean(dataset, frame, [{"archive": "x.zip"}], tmp_path, {"note": 1})
    assert path == tmp_path / "clean" / "kraken" / "BTC_EUR_1d.parquet"
    manifest = json.loads(dataset.manifest_path(tmp_path).read_text(encoding="utf-8"))
    assert manifest["rows"] == 5
    assert manifest["first_open_time"].startswith("2024-01-01")
    assert manifest["inputs"] == [{"archive": "x.zip"}]
    assert list_clean_datasets(tmp_path) == [dataset]
    pd.testing.assert_frame_equal(dataset.load(tmp_path), frame)

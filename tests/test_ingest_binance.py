import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from aitradingbot.ingest import binance
from aitradingbot.ingest.common import sha256_bytes

MS_ROWS = (
    b"1733011200000,96407.99,97836.00,95693.88,97185.18,16938.60,1733097599999,0,0,0,0,0\n"
    b"1733097600000,97185.17,98130.00,94395.00,95840.62,37958.66,1733183999999,0,0,0,0,0\n"
)
US_ROWS = (
    b"1735689600000000,93576.00,95151.15,92888.00,94591.79,10373.32,1735775999999999,0,0,0,0,0\n"
    b"1735776000000000,94591.78,97839.50,94392.00,96984.79,21970.48,1735862399999999,0,0,0,0,0\n"
)


def zipped(name: str, payload: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name.replace(".zip", ".csv"), payload)
    return buffer.getvalue()


def test_parses_millisecond_and_microsecond_timestamps() -> None:
    ms = binance.parse_kline_csv(MS_ROWS)
    us = binance.parse_kline_csv(US_ROWS)
    assert ms["open_time"].tolist() == [
        pd.Timestamp("2024-12-01", tz="UTC"),
        pd.Timestamp("2024-12-02", tz="UTC"),
    ]
    assert us["open_time"].tolist() == [
        pd.Timestamp("2025-01-01", tz="UTC"),
        pd.Timestamp("2025-01-02", tz="UTC"),
    ]
    assert us.loc[1, "close"] == 96984.79


def test_skips_header_row_if_present() -> None:
    header = b"open_time,open,high,low,close,volume,close_time,a,b,c,d,e\n"
    assert len(binance.parse_kline_csv(header + MS_ROWS)) == 2


def test_month_helpers() -> None:
    assert binance.month_range("2024-11", "2025-02") == ["2024-11", "2024-12", "2025-01", "2025-02"]
    assert binance.last_complete_month(pd.Timestamp("2026-10-19", tz="UTC")) == "2026-09"
    assert binance.symbol_to_pair("BTCUSDT") == "BTC/USDT"
    assert binance.symbol_to_pair("ETHEUR") == "ETH/EUR"


class FakeHttp:
    def __init__(self, responses: dict[str, bytes]):
        self.responses = responses
        self.calls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.calls.append(url)
        if url not in self.responses:
            raise FileNotFoundError(url)
        return self.responses[url]


def month_responses(
    symbol: str, month: str, payload: bytes, checksum: str | None = None
) -> dict[str, bytes]:
    name = binance.archive_name(symbol, "1d", month)
    archive = zipped(name, payload)
    url = f"{binance.BASE_URL}/{symbol}/1d/{name}"
    digest = checksum or sha256_bytes(archive)
    return {url: archive, url + ".CHECKSUM": f"{digest}  {name}\n".encode()}


def test_download_verifies_checksum_and_caches(tmp_path: Path) -> None:
    http = FakeHttp(month_responses("BTCUSDT", "2024-12", MS_ROWS))
    path = binance.download_month("BTCUSDT", "1d", "2024-12", tmp_path, http)
    assert path is not None and path.exists()
    calls = len(http.calls)
    assert binance.download_month("BTCUSDT", "1d", "2024-12", tmp_path, http) == path
    assert len(http.calls) == calls  # second call served from the immutable raw store


def test_download_rejects_bad_checksum(tmp_path: Path) -> None:
    http = FakeHttp(month_responses("BTCUSDT", "2024-12", MS_ROWS, checksum="0" * 64))
    with pytest.raises(ValueError, match="checksum mismatch"):
        binance.download_month("BTCUSDT", "1d", "2024-12", tmp_path, http)
    assert not binance.raw_path(tmp_path, "BTCUSDT", "1d", "2024-12").exists()


def test_detects_local_corruption(tmp_path: Path) -> None:
    http = FakeHttp(month_responses("BTCUSDT", "2024-12", MS_ROWS))
    path = binance.download_month("BTCUSDT", "1d", "2024-12", tmp_path, http)
    assert path is not None
    path.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="corrupted"):
        binance.download_month("BTCUSDT", "1d", "2024-12", tmp_path, http)


def test_unpublished_month_returns_none(tmp_path: Path) -> None:
    assert binance.download_month("BTCUSDT", "1d", "2016-01", tmp_path, FakeHttp({})) is None


def test_ingest_combines_months_across_the_unit_change(tmp_path: Path) -> None:
    responses = {
        **month_responses("BTCUSDT", "2024-12", MS_ROWS),
        **month_responses("BTCUSDT", "2025-01", US_ROWS),
    }
    (path,) = binance.ingest(
        ["BTCUSDT"], ["1d"], "2024-11", "2025-01", tmp_path, FakeHttp(responses), workers=2
    )
    frame = pd.read_parquet(path)
    assert len(frame) == 4
    assert frame["open_time"].is_monotonic_increasing
    assert path.name == "BTC_USDT_1d.parquet"

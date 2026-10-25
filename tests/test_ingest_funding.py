import io
import json
import zipfile
from pathlib import Path

import pandas as pd

from aitradingbot.ingest import funding
from aitradingbot.ingest.common import list_clean_datasets, sha256_bytes

HEADER = b"calc_time,funding_interval_hours,last_funding_rate\n"
# 2020-01-01 00:00, 08:00 and 16:00 UTC, with the few-ms offsets Binance's archive has.
JAN_ROWS = b"1577836800000,8,-0.00012359\n1577865600003,8,-0.00012383\n1577894400001,8,0.00010000\n"
# 2020-02-01 00:00 and 08:00 UTC.
FEB_ROWS = b"1580515200000,8,0.00020000\n1580544000002,8,0.00030000\n"


def zipped(name: str, payload: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name.replace(".zip", ".csv"), payload)
    return buffer.getvalue()


class FakeHttp:
    def __init__(self, responses: dict[str, bytes]):
        self.responses = responses
        self.calls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.calls.append(url)
        if url not in self.responses:
            raise FileNotFoundError(url)
        return self.responses[url]


def month_responses(symbol: str, month: str, payload: bytes) -> dict[str, bytes]:
    name = funding.archive_name(symbol, month)
    archive = zipped(name, payload)
    url = f"{funding.BASE_URL}/{symbol}/{name}"
    return {url: archive, url + ".CHECKSUM": f"{sha256_bytes(archive)}  {name}\n".encode()}


def test_parses_and_snaps_settlements_to_the_hour() -> None:
    frame = funding.parse_funding_csv(HEADER + JAN_ROWS)
    assert list(frame.columns) == funding.FUNDING_COLUMNS
    assert frame["funding_time"].tolist() == [
        pd.Timestamp("2020-01-01 00:00", tz="UTC"),
        pd.Timestamp("2020-01-01 08:00", tz="UTC"),
        pd.Timestamp("2020-01-01 16:00", tz="UTC"),
    ]
    assert frame["interval_hours"].tolist() == [8.0, 8.0, 8.0]
    assert frame.loc[1, "rate"] == -0.00012383


def test_parses_microseconds_and_no_header() -> None:
    frame = funding.parse_funding_csv(b"1735689600000123,8,0.0001\n")
    assert frame["funding_time"].tolist() == [pd.Timestamp("2025-01-01", tz="UTC")]


def test_settlement_far_off_the_hour_is_kept_as_is() -> None:
    times = pd.Series(
        [
            pd.Timestamp("2020-01-01 08:00:00.003", tz="UTC"),
            pd.Timestamp("2020-01-01 08:20", tz="UTC"),
        ]
    )
    assert funding.snap_to_hour(times).tolist() == [
        pd.Timestamp("2020-01-01 08:00", tz="UTC"),
        pd.Timestamp("2020-01-01 08:20", tz="UTC"),
    ]


def test_ingest_writes_parquet_and_manifest(tmp_path: Path) -> None:
    responses = {
        **month_responses("BTCUSDT", "2020-01", HEADER + JAN_ROWS),
        **month_responses("BTCUSDT", "2020-02", HEADER + FEB_ROWS),
    }
    http = FakeHttp(responses)
    (path,) = funding.ingest(["BTCUSDT"], "2017-08", "2020-03", tmp_path, http, workers=2)

    frame = pd.read_parquet(path)
    assert len(frame) == 5
    assert frame["funding_time"].is_monotonic_increasing
    # Months before the archive starts aren't even requested.
    assert not any("2019-12" in url for url in http.calls)

    manifest = json.loads(funding.manifest_path("BTCUSDT", tmp_path).read_text(encoding="utf-8"))
    assert manifest["rows"] == 5
    assert manifest["notes"]["months_not_published"] == ["2020-03"]
    assert [entry["archive"] for entry in manifest["inputs"]] == [
        "BTCUSDT-fundingRate-2020-01.zip",
        "BTCUSDT-fundingRate-2020-02.zip",
    ]
    assert funding.list_symbols(tmp_path) == ["BTCUSDT"]


def test_funding_files_are_not_mistaken_for_candles(tmp_path: Path) -> None:
    http = FakeHttp(month_responses("BTCUSDT", "2020-01", HEADER + JAN_ROWS))
    funding.ingest(["BTCUSDT"], "2020-01", "2020-01", tmp_path, http, workers=1)
    assert list_clean_datasets(tmp_path) == []

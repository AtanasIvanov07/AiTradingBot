from pathlib import Path

from conftest import MakeCandles

from aitradingbot.ingest.common import Dataset, write_clean
from aitradingbot.validate.__main__ import build_report, main


def test_report_summarises_and_cross_checks(tmp_path: Path, candles: MakeCandles) -> None:
    frame = candles(periods=40)
    write_clean(Dataset("kraken", "BTC/EUR", "1d"), frame, [], tmp_path)
    write_clean(Dataset("bitvavo", "BTC/EUR", "1d"), frame, [], tmp_path)
    text, ok = build_report(tmp_path, max_missing_fraction=0.01, tolerance=0.005)
    assert ok
    assert "| bitvavo | BTC/EUR | 1d | 40 |" in text
    assert "bitvavo vs kraken" in text
    assert "**Overall: no errors**" in text


def test_cli_exit_code_reflects_errors(tmp_path: Path, candles: MakeCandles) -> None:
    broken = candles(periods=10)
    broken.loc[3, "high"] = 1.0  # breaks the OHLC invariant
    write_clean(Dataset("kraken", "ETH/EUR", "1d"), broken, [], tmp_path)
    out = tmp_path / "report.md"
    assert main(["--root", str(tmp_path), "--out", str(out)]) == 1
    assert "ERRORS FOUND" in out.read_text(encoding="utf-8")


def test_empty_store_is_not_ok(tmp_path: Path) -> None:
    text, ok = build_report(tmp_path, 0.01, 0.005)
    assert not ok and "No clean datasets" in text

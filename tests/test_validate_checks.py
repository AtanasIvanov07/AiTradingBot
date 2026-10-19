import pandas as pd
from conftest import MakeCandles

from aitradingbot.validate.checks import (
    cross_source,
    find_gaps,
    misaligned,
    ohlc_violations,
    outlier_moves,
    validate,
)


def test_clean_series_passes(candles: MakeCandles) -> None:
    report = validate(candles(periods=30), "1d")
    assert report.ok
    assert report.findings == []
    assert report.rows == 30


def test_empty_series_is_an_error(candles: MakeCandles) -> None:
    report = validate(candles(periods=0), "1d")
    assert not report.ok
    assert report.errors[0].check == "empty"


def test_duplicate_timestamps_are_errors(candles: MakeCandles) -> None:
    frame = candles(periods=5)
    frame = pd.concat([frame, frame.iloc[[2]].assign(close=999.0, high=1000.0)], ignore_index=True)
    frame = frame.sort_values("open_time", kind="stable").reset_index(drop=True)
    checks = {f.check for f in validate(frame, "1d").errors}
    assert "duplicates" in checks


def test_unsorted_series_is_an_error(candles: MakeCandles) -> None:
    frame = candles(periods=5).iloc[::-1].reset_index(drop=True)
    assert "order" in {f.check for f in validate(frame, "1d").errors}


def test_nan_is_an_error(candles: MakeCandles) -> None:
    frame = candles(periods=5)
    frame.loc[1, "close"] = float("nan")
    assert "nan" in {f.check for f in validate(frame, "1d").errors}


def test_ohlc_violations_are_detected(candles: MakeCandles) -> None:
    frame = candles(periods=5)
    frame.loc[1, "high"] = 95.0  # below that candle's close of 101
    frame.loc[3, "volume"] = -1.0
    assert list(ohlc_violations(frame).index) == [1, 3]
    assert "ohlc" in {f.check for f in validate(frame, "1d").errors}


def test_gap_detection_reports_exact_span(candles: MakeCandles) -> None:
    frame = candles(periods=10).drop(index=[3, 4, 5]).reset_index(drop=True)
    gaps = find_gaps(frame, "1d")
    assert len(gaps) == 1
    assert gaps[0].first_missing == pd.Timestamp("2024-01-04", tz="UTC")
    assert gaps[0].last_missing == pd.Timestamp("2024-01-06", tz="UTC")
    assert gaps[0].missing == 3


def test_small_gaps_warn_large_gaps_error(candles: MakeCandles) -> None:
    frame = candles(periods=1000).drop(index=[500]).reset_index(drop=True)
    report = validate(frame, "1d")
    assert report.ok and report.missing_candles == 1
    assert "gaps" in {f.check for f in report.warnings}

    holey = candles(periods=1000).drop(index=range(100, 200)).reset_index(drop=True)
    assert "gaps" in {f.check for f in validate(holey, "1d").errors}


def test_open_jump_is_an_error(candles: MakeCandles) -> None:
    frame = candles(periods=5)
    frame.loc[3, ["open", "high"]] = [175.0, 175.0]  # bad print, OHLC still consistent
    report = validate(frame, "1d")
    assert "open_jump" in {f.check for f in report.errors}


def test_no_candles_in_assessed_window_is_an_error(candles: MakeCandles) -> None:
    frame = candles(start="2015-01-01", periods=100)
    report = validate(frame, "1d", assess_from=pd.Timestamp("2017-08-01", tz="UTC"))
    assert "window" in {f.check for f in report.errors}


def test_gaps_before_assess_from_only_warn(candles: MakeCandles) -> None:
    frame = candles(start="2015-01-01", periods=1500)
    frame[["open", "close", "high", "low"]] = [100.0, 100.0, 101.0, 99.0]  # flat: no jumps at gaps
    frame = frame.drop(index=range(10, 100)).reset_index(drop=True)  # 2015 holes
    assert not validate(frame, "1d").ok  # 90 of 1500 missing overall: error
    report = validate(frame, "1d", assess_from=pd.Timestamp("2016-01-01", tz="UTC"))
    assert report.ok
    assert report.missing_candles == 0
    assert "early_gaps" in {f.check for f in report.warnings}
    assert report.first == pd.Timestamp("2015-01-01", tz="UTC")  # range still reports full data


def test_misaligned_daily_candles_are_errors(candles: MakeCandles) -> None:
    frame = candles(periods=5)
    frame["open_time"] = frame["open_time"] + pd.Timedelta(hours=1)  # e.g. a local-time daily close
    assert misaligned(frame, "1d") == 5
    assert "alignment" in {f.check for f in validate(frame, "1d").errors}


def test_four_hour_grid_alignment(candles: MakeCandles) -> None:
    assert misaligned(candles(periods=12, timeframe="4h"), "4h") == 0


def test_outliers_flag_big_moves_and_wicks(candles: MakeCandles) -> None:
    frame = candles(periods=6)
    frame.loc[3, ["open", "close", "high", "low"]] = [102.0, 140.0, 141.0, 101.0]  # +37% close
    frame.loc[4, ["open", "close", "high", "low"]] = [140.0, 104.0, 141.0, 103.0]  # -26% close
    frame.loc[5, "low"] = 10.0  # 90% lower wick
    flagged = outlier_moves(frame, "1d")
    assert sorted(flagged["open_time"].dt.day.tolist()) == [4, 5, 6]  # day 5 is the move back down
    report = validate(frame, "1d")
    assert report.ok  # outliers are warnings for review, not errors
    assert "outliers" in {f.check for f in report.warnings}


def test_zero_volume_is_a_warning(candles: MakeCandles) -> None:
    frame = candles(periods=5)
    frame.loc[2, "volume"] = 0.0
    report = validate(frame, "1d")
    assert report.ok and report.zero_volume == 1


def test_coverage(candles: MakeCandles) -> None:
    report = validate(candles(start="2024-01-01", periods=31), "1d")
    jan_1 = pd.Timestamp("2024-01-01", tz="UTC")
    assert report.covers(jan_1, pd.Timestamp("2024-01-31", tz="UTC"))
    assert not report.covers(jan_1, pd.Timestamp("2024-02-01", tz="UTC"))
    hourly = validate(candles(start="2024-01-01", periods=24, timeframe="1h"), "1h")
    assert hourly.covers(jan_1, jan_1)  # last candle 23:00 completes the day


def test_cross_source_measures_divergence(candles: MakeCandles) -> None:
    a = candles(periods=100)
    b = a.copy()
    b.loc[10, "close"] = 112.2  # a's close there is 110: one 2% disagreement
    check = cross_source(a, b, tolerance=0.005)
    assert check.common == 100
    assert check.median_diff == 0.0
    assert abs(check.max_diff - 2.2 / 112.2) < 1e-9
    assert check.share_over_tolerance == 0.01
    assert check.worst.loc[0, "open_time"] == a.loc[10, "open_time"]

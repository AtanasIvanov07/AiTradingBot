import pandas as pd

from aitradingbot.validate.checks import missing_settlements, validate_funding


def settlements(start: str = "2024-01-01", periods: int = 30, hours: int = 8) -> pd.DataFrame:
    """A gap-free funding series on the UTC grid of its interval."""
    times = pd.date_range(start, periods=periods, freq=f"{hours}h", tz="UTC")
    return pd.DataFrame({"funding_time": times, "interval_hours": float(hours), "rate": 0.0001})


def checks(frame: pd.DataFrame) -> set[tuple[str, str]]:
    return {(f.check, f.severity) for f in validate_funding(frame).findings}


def test_clean_series_passes() -> None:
    report = validate_funding(settlements())
    assert report.ok and not report.findings
    assert report.rows == 30 and report.missing == 0


def test_empty_series_is_an_error() -> None:
    assert ("empty", "error") in checks(settlements().iloc[0:0])


def test_structural_errors() -> None:
    frame = settlements()
    duplicated = pd.concat([frame, frame.iloc[[3]]]).sort_values("funding_time")
    assert ("duplicates", "error") in checks(duplicated.reset_index(drop=True))
    assert ("order", "error") in checks(frame.iloc[::-1].reset_index(drop=True))
    with_nan = frame.copy()
    with_nan.loc[5, "rate"] = float("nan")
    assert ("nan", "error") in checks(with_nan)
    odd_interval = frame.copy()
    odd_interval.loc[5, "interval_hours"] = 6.0
    assert ("interval", "error") in checks(odd_interval)


def test_settlement_off_its_grid_is_an_error() -> None:
    frame = settlements()
    frame.loc[4, "funding_time"] = pd.Timestamp("2024-01-02 09:00", tz="UTC")  # 8-hour schedule
    assert ("alignment", "error") in checks(frame)
    frame = settlements()
    frame.loc[4, "funding_time"] = pd.Timestamp("2024-01-02 08:20", tz="UTC")  # left unsnapped
    assert ("alignment", "error") in checks(frame)


def test_missing_settlements_warn_then_error() -> None:
    long = settlements(periods=400)
    one_missing = long.drop(index=100).reset_index(drop=True)
    assert missing_settlements(one_missing) == 1
    assert ("gaps", "warning") in checks(one_missing)
    many_missing = long.drop(index=range(100, 110)).reset_index(drop=True)
    assert missing_settlements(many_missing) == 10
    assert ("gaps", "error") in checks(many_missing)


def test_interval_change_is_not_a_gap() -> None:
    eight = settlements(start="2024-01-01", periods=9, hours=8)  # ends 2024-01-03 16:00
    four = settlements(start="2024-01-04", periods=12, hours=4)
    report = validate_funding(pd.concat([eight, four], ignore_index=True))
    assert report.ok and report.missing == 0


def test_extreme_rates_are_flagged() -> None:
    frame = settlements()
    frame.loc[7, "rate"] = -0.0075
    report = validate_funding(frame)
    assert report.ok and report.extreme == 1
    assert report.max_abs_rate == 0.0075
    assert ("extreme", "warning") in checks(frame)


def test_coverage_needs_the_last_settlement_of_the_end_day() -> None:
    report = validate_funding(settlements(start="2024-01-01", periods=9))  # through 01-03 16:00
    jan_1 = pd.Timestamp("2024-01-01", tz="UTC")
    assert report.covers(jan_1, pd.Timestamp("2024-01-03", tz="UTC"))
    assert not report.covers(jan_1, pd.Timestamp("2024-01-04", tz="UTC"))

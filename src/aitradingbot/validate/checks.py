"""Data-quality checks for canonical candle frames (PROJECT_PLAN.md §4.3–4.4).

Errors are structural problems that make a series unusable until fixed: duplicates, broken OHLC
invariants, NaNs, misaligned timestamps, too many missing candles. Warnings need a human look but
don't block research on their own: isolated gaps, extreme moves, zero-volume candles.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from aitradingbot.ingest.common import OHLCV_COLUMNS, OPEN_JUMP_LIMITS, TIMEFRAMES, bad_opens
from aitradingbot.splits import WARMUP_START

ERROR = "error"
WARNING = "warning"

# A candle moving more than this (close-to-close, or a wick beyond the body) is flagged for review.
OUTLIER_THRESHOLDS = {"1h": 0.10, "4h": 0.15, "1d": 0.25}
DEFAULT_MAX_MISSING_FRACTION = 0.01

# Where gap, outlier and zero-volume checks start, per source (default: the research warm-up start).
# Bitvavo listed BTC/EUR and ETH/EUR in March 2019 and ETH/EUR traded thinly that year: 8.5% of its
# hours had no trade, so no 1h candle. Like Kraken's thin 2013-2015 years, those early gaps are
# reported as a warning but don't fail the series. Bitvavo is a confirmation source at 1d only.
ASSESS_FROM = {"bitvavo": pd.Timestamp("2020-01-01", tz="UTC")}


def assess_from(source: str) -> pd.Timestamp:
    return ASSESS_FROM.get(source, WARMUP_START)


@dataclass(frozen=True)
class Gap:
    first_missing: pd.Timestamp
    last_missing: pd.Timestamp
    missing: int


@dataclass(frozen=True)
class Finding:
    check: str
    severity: str
    message: str


@dataclass
class Report:
    timeframe: str
    rows: int
    first: pd.Timestamp | None
    last: pd.Timestamp | None
    gaps: list[Gap]
    missing_candles: int
    missing_fraction: float
    outliers: pd.DataFrame
    zero_volume: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    def covers(self, start: pd.Timestamp, end: pd.Timestamp) -> bool:
        """True if the series spans every candle from ``start`` through the end of day ``end``."""
        if self.first is None or self.last is None:
            return False
        last_needed = end + pd.Timedelta(days=1) - TIMEFRAMES[self.timeframe]
        return self.first <= start and self.last >= last_needed


def duplicate_times(frame: pd.DataFrame) -> int:
    return int(frame["open_time"].duplicated().sum())


def is_sorted(frame: pd.DataFrame) -> bool:
    return bool(frame["open_time"].is_monotonic_increasing)


def nan_rows(frame: pd.DataFrame) -> int:
    return int(frame[OHLCV_COLUMNS].isna().any(axis=1).sum())


def ohlc_violations(frame: pd.DataFrame) -> pd.DataFrame:
    """Rows where low/high don't bracket open/close, prices aren't positive, or volume < 0."""
    body_low = frame[["open", "close"]].min(axis=1)
    body_high = frame[["open", "close"]].max(axis=1)
    bad = (
        (frame["low"] > body_low)
        | (frame["high"] < body_high)
        | (frame["low"] > frame["high"])
        | (frame[["open", "high", "low", "close"]] <= 0).any(axis=1)
        | (frame["volume"] < 0)
    )
    return frame.loc[bad]


def misaligned(frame: pd.DataFrame, timeframe: str) -> int:
    """Candles whose open isn't on the UTC grid (e.g. daily candles not at 00:00 UTC).

    ``dt.floor`` anchors fixed frequencies at the Unix epoch, so 4h candles must open at
    00:00, 04:00, … UTC and daily candles at midnight UTC.
    """
    times = frame["open_time"]
    return int((times.dt.floor(TIMEFRAMES[timeframe]) != times).sum())


def find_gaps(frame: pd.DataFrame, timeframe: str) -> list[Gap]:
    step = TIMEFRAMES[timeframe]
    times = frame["open_time"].drop_duplicates().sort_values().reset_index(drop=True)
    deltas = times.diff()
    gaps = []
    for index in deltas.index[deltas > step]:
        previous, current = times[index - 1], times[index]
        missing = int((current - previous) / step) - 1
        if missing > 0:
            gaps.append(Gap(previous + step, current - step, missing))
    return gaps


def expected_candles(first: pd.Timestamp, last: pd.Timestamp, timeframe: str) -> int:
    return int((last - first) / TIMEFRAMES[timeframe]) + 1


def outlier_moves(
    frame: pd.DataFrame, timeframe: str, threshold: float | None = None
) -> pd.DataFrame:
    limit = threshold if threshold is not None else OUTLIER_THRESHOLDS[timeframe]
    close_move = frame["close"].pct_change().abs()
    upper_wick = frame["high"] / frame[["open", "close"]].max(axis=1) - 1
    lower_wick = 1 - frame["low"] / frame[["open", "close"]].min(axis=1)
    flagged = (close_move > limit) | (upper_wick > limit) | (lower_wick > limit)
    out = frame.loc[flagged, ["open_time", "open", "high", "low", "close"]].copy()
    out["close_move"] = close_move[flagged]
    out["max_wick"] = pd.concat([upper_wick, lower_wick], axis=1).max(axis=1)[flagged]
    return out.reset_index(drop=True)


def validate(
    frame: pd.DataFrame,
    timeframe: str,
    max_missing_fraction: float = DEFAULT_MAX_MISSING_FRACTION,
    assess_from: pd.Timestamp | None = None,
) -> Report:
    """Check a candle series.

    Structural checks always cover the whole series. Gap, outlier and zero-volume checks cover
    candles from ``assess_from`` on (e.g. the research warm-up start), so that years of thin
    trading before the data is ever used (Kraken's 2013-2015 EUR markets) don't fail the series.
    Gaps before ``assess_from`` are still reported as a warning.
    """
    findings: list[Finding] = []

    def error(check: str, message: str) -> None:
        findings.append(Finding(check, ERROR, message))

    def warning(check: str, message: str) -> None:
        findings.append(Finding(check, WARNING, message))

    if frame.empty:
        error("empty", "no rows")
        return Report(timeframe, 0, None, None, [], 0, 0.0, frame.iloc[0:0], 0, findings)

    if (count := nan_rows(frame)) > 0:
        error("nan", f"{count} rows with missing values")
    if (count := duplicate_times(frame)) > 0:
        error("duplicates", f"{count} duplicate open_time values")
    if not is_sorted(frame):
        error("order", "open_time is not increasing")
    if (count := len(ohlc_violations(frame))) > 0:
        error("ohlc", f"{count} rows break OHLC invariants (low ≤ open/close ≤ high, prices > 0)")
    if (count := misaligned(frame, timeframe)) > 0:
        error("alignment", f"{count} candles not aligned to the UTC {timeframe} grid")
    if (count := int(bad_opens(frame, timeframe).sum())) > 0:
        limit = OPEN_JUMP_LIMITS[timeframe]
        error("open_jump", f"{count} bad opens (> {limit:.0%} from previous and own close)")

    first, last = frame["open_time"].min(), frame["open_time"].max()
    window = frame
    scope = ""
    if assess_from is not None and first < assess_from:
        early = find_gaps(frame.loc[frame["open_time"] < assess_from], timeframe)
        if early:
            warning(
                "early_gaps",
                f"{sum(g.missing for g in early)} missing candles before "
                f"{assess_from:%Y-%m-%d} (not used for research)",
            )
        window = frame.loc[frame["open_time"] >= assess_from]
        scope = f" since {assess_from:%Y-%m-%d}"
        if window.empty:  # all data predates the period we use: nothing usable left
            error("window", f"no candles{scope}")

    gaps: list[Gap] = []
    missing, fraction = 0, 0.0
    if not window.empty:
        gaps = find_gaps(window, timeframe)
        missing = sum(gap.missing for gap in gaps)
        window_first, window_last = window["open_time"].min(), window["open_time"].max()
        fraction = missing / expected_candles(window_first, window_last, timeframe)
    if fraction > max_missing_fraction:
        error("gaps", f"{missing} missing candles{scope} ({fraction:.2%}) in {len(gaps)} gaps")
    elif gaps:
        largest = max(gaps, key=lambda gap: gap.missing)
        warning(
            "gaps",
            f"{missing} missing candles{scope} ({fraction:.3%}) in {len(gaps)} gaps; "
            f"largest {largest.missing} from {largest.first_missing:%Y-%m-%d %H:%M}",
        )

    outliers = outlier_moves(window, timeframe)
    if not outliers.empty:
        limit = OUTLIER_THRESHOLDS[timeframe]
        warning("outliers", f"{len(outliers)} candles{scope} with moves > {limit:.0%}")
    zero_volume = int((window["volume"] == 0).sum())
    if zero_volume:
        warning("zero_volume", f"{zero_volume} candles{scope} with zero volume")

    return Report(
        timeframe, len(frame), first, last, gaps, missing, fraction, outliers, zero_volume, findings
    )


@dataclass(frozen=True)
class CrossCheck:
    common: int
    median_diff: float
    p99_diff: float
    max_diff: float
    share_over_tolerance: float
    worst: pd.DataFrame


def cross_source(a: pd.DataFrame, b: pd.DataFrame, tolerance: float = 0.005) -> CrossCheck:
    """Compare closes of the same pair from two sources on their common candles."""
    merged = a[["open_time", "close"]].merge(
        b[["open_time", "close"]], on="open_time", suffixes=("_a", "_b")
    )
    if merged.empty:
        return CrossCheck(0, 0.0, 0.0, 0.0, 0.0, merged)
    diff = (merged["close_a"] - merged["close_b"]).abs() / merged["close_b"]
    merged["rel_diff"] = diff
    return CrossCheck(
        common=len(merged),
        median_diff=float(diff.median()),
        p99_diff=float(diff.quantile(0.99)),
        max_diff=float(diff.max()),
        share_over_tolerance=float((diff > tolerance).mean()),
        worst=merged.nlargest(5, "rel_diff").reset_index(drop=True),
    )


# Funding rates (H6 signal, src/aitradingbot/ingest/funding.py). A settlement beyond this, in either
# direction, is flagged for review: at 8-hourly settlements it's about 330% a year.
FUNDING_EXTREME_RATE = 0.003
FUNDING_INTERVALS = {1.0, 2.0, 4.0, 8.0}
FUNDING_COLUMNS = ["funding_time", "interval_hours", "rate"]


@dataclass
class FundingReport:
    rows: int
    first: pd.Timestamp | None
    last: pd.Timestamp | None
    missing: int
    missing_fraction: float
    extreme: int
    max_abs_rate: float
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    def covers(self, start: pd.Timestamp, end: pd.Timestamp) -> bool:
        """True if settlements run from ``start`` through the last 8-hourly one of day ``end``."""
        if self.first is None or self.last is None:
            return False
        return self.first <= start and self.last >= end + pd.Timedelta(hours=16)


def missing_settlements(frame: pd.DataFrame) -> int:
    """Settlements missing between consecutive rows, given each row's funding interval.

    Across an interval change (e.g. 8h → 4h) the longer of the two intervals is the expected step,
    so the switch itself isn't counted as a gap.
    """
    hours = frame["funding_time"].diff().dt.total_seconds() / 3600
    step = pd.concat([frame["interval_hours"], frame["interval_hours"].shift(1)], axis=1).max(
        axis=1
    )
    missing = (hours // step - 1).where(hours > step, 0)
    return int(missing.fillna(0).sum())


def validate_funding(
    frame: pd.DataFrame, max_missing_fraction: float = DEFAULT_MAX_MISSING_FRACTION
) -> FundingReport:
    """Check one symbol's funding settlements: structure, alignment, gaps and extreme rates."""
    findings: list[Finding] = []

    def error(check: str, message: str) -> None:
        findings.append(Finding(check, ERROR, message))

    def warning(check: str, message: str) -> None:
        findings.append(Finding(check, WARNING, message))

    if frame.empty:
        error("empty", "no rows")
        return FundingReport(0, None, None, 0, 0.0, 0, 0.0, findings)

    if (count := int(frame[FUNDING_COLUMNS].isna().any(axis=1).sum())) > 0:
        error("nan", f"{count} rows with missing values")
    if (count := int(frame["funding_time"].duplicated().sum())) > 0:
        error("duplicates", f"{count} duplicate funding_time values")
    if not frame["funding_time"].is_monotonic_increasing:
        error("order", "funding_time is not increasing")
    if (count := int((~frame["interval_hours"].dropna().isin(FUNDING_INTERVALS)).sum())) > 0:
        error("interval", f"{count} settlements with an unknown funding interval")
    times = frame["funding_time"]
    off_grid = (times.dt.floor("1h") != times) | (times.dt.hour % frame["interval_hours"] != 0)
    if (count := int(off_grid.sum())) > 0:
        error("alignment", f"{count} settlements not on their interval's UTC grid")

    missing = missing_settlements(frame)
    fraction = missing / (len(frame) + missing)
    if fraction > max_missing_fraction:
        error("gaps", f"{missing} missing settlements ({fraction:.2%})")
    elif missing:
        warning("gaps", f"{missing} missing settlements ({fraction:.3%})")

    extreme = int((frame["rate"].abs() > FUNDING_EXTREME_RATE).sum())
    if extreme:
        warning("extreme", f"{extreme} settlements beyond ±{FUNDING_EXTREME_RATE:.1%}")

    return FundingReport(
        rows=len(frame),
        first=times.min(),
        last=times.max(),
        missing=missing,
        missing_fraction=fraction,
        extreme=extreme,
        max_abs_rate=float(frame["rate"].abs().max()),
        findings=findings,
    )

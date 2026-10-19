"""Data-quality checks for canonical candle frames (PROJECT_PLAN.md §4.3–4.4).

Errors are structural problems that make a series unusable until fixed: duplicates, broken OHLC
invariants, NaNs, misaligned timestamps, too many missing candles. Warnings need a human look but
don't block research on their own: isolated gaps, extreme moves, zero-volume candles.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from aitradingbot.ingest.common import OHLCV_COLUMNS, OPEN_JUMP_LIMITS, TIMEFRAMES, bad_opens

ERROR = "error"
WARNING = "warning"

# A candle moving more than this (close-to-close, or a wick beyond the body) is flagged for review.
OUTLIER_THRESHOLDS = {"1h": 0.10, "4h": 0.15, "1d": 0.25}
DEFAULT_MAX_MISSING_FRACTION = 0.01


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

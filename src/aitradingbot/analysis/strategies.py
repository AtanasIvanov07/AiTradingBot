"""Target-exposure rules for the registered hypotheses (research/hypotheses/H1.md – H6.md).

Each function sees closes **up to and including** the decision candle only (rolling windows and
shifts into the past). The engine executes the decision at the next candle's open. Tests perturb
future prices to prove that no function looks ahead.

Inputs are the candles that actually exist. Callers reindex the result onto a regular calendar and
forward-fill, so a missing candle means "no new decision", as the conventions require.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

SUNDAY = 6


def h1_trend_filter(close: pd.Series, n: int, band: float) -> pd.Series:
    """H1: long (1.0) above SMA(n)·(1+band), flat (0.0) below SMA(n)·(1−band), else unchanged."""
    sma = close.rolling(n, min_periods=n).mean()
    state = pd.Series(np.nan, index=close.index)
    state[close > sma * (1 + band)] = 1.0
    state[close < sma * (1 - band)] = 0.0
    return state.ffill().fillna(0.0)


def h2_dual_momentum(
    closes: pd.DataFrame, lookback: int, buffer: float, weekday: int = SUNDAY
) -> pd.DataFrame:
    """H2: weekly, hold 100% of the asset with the higher positive ``lookback``-candle return.

    Cash when neither return is positive. Switching from one held asset to the other requires the
    other's return to be higher by more than ``buffer`` (absolute, e.g. 0.05 = 5 percentage points).
    ``closes`` must be on a regular daily calendar (NaN for missing days).
    """
    filled = closes.ffill()
    momentum = filled / filled.shift(lookback) - 1
    weights = pd.DataFrame(0.0, index=closes.index, columns=closes.columns)
    holding: str | None = None
    for time, row in momentum.iterrows():
        assert isinstance(time, pd.Timestamp)
        if time.dayofweek == weekday and not row.isna().any():
            best = str(row.idxmax())
            if float(row[best]) <= 0:
                holding = None  # rule 1: neither positive -> cash (never buffered)
            else:
                from_cash_or_same = holding is None or holding == best
                beats_buffer = holding is not None and float(row[best] - row[holding]) > buffer
                if from_cash_or_same or beats_buffer:  # rules 2 and 3
                    holding = best
        if holding is not None:
            weights.loc[time, holding] = 1.0
    return weights


def h4_trend_vol(
    close: pd.Series,
    n: int,
    band: float,
    target_vol: float,
    lookback: int,
    periods_per_year: float,
) -> pd.Series:
    """H4: H1's trend state (1 or 0) times H3's volatility-scaled size, so flat in downtrends."""
    trend = h1_trend_filter(close, n, band)
    size = h3_vol_target(close, target_vol, lookback, periods_per_year)
    exposure: pd.Series = trend * size
    return exposure


def h3_vol_target(
    close: pd.Series, target_vol: float, lookback: int, periods_per_year: float
) -> pd.Series:
    """H3: exposure = min(1, target_vol / realised_vol), realised vol from ``lookback`` returns."""
    log_returns = np.log(close).diff()
    realised = log_returns.rolling(lookback, min_periods=lookback).std()
    realised = realised * math.sqrt(periods_per_year)
    exposure: pd.Series = (target_vol / realised).clip(upper=1.0)
    exposure = exposure.replace([np.inf, -np.inf], 1.0).fillna(0.0)
    return exposure


DAYS_PER_YEAR = 365


def daily_funding(settlements: pd.DataFrame) -> pd.Series:
    """H6: funding paid per UTC day, the sum of that day's settlement rates.

    A day is the daily candle opening at its 00:00 UTC, so a settlement at exactly 00:00 belongs to
    the day it opens. The one at the candle's close (the next 00:00) belongs to the next day, as H6
    registers. Days without settlements are NaN on a full calendar: no data, so no signal update.
    """
    times = settlements["funding_time"]
    sums = settlements["rate"].groupby(times.dt.floor("D")).sum()
    calendar = pd.date_range(sums.index.min(), sums.index.max(), freq="D", tz="UTC")
    daily: pd.Series = sums.reindex(calendar)
    return daily


def h6_funding_signal(daily: pd.Series, lookback: int) -> pd.Series:
    """H6's F: the mean of the last ``lookback`` daily funding sums, annualised (× 365)."""
    signal: pd.Series = daily.rolling(lookback, min_periods=lookback).mean() * DAYS_PER_YEAR
    return signal


def h6_crowded(signal: pd.Series, theta: float, hysteresis: float) -> pd.Series:
    """H6: crowded (1.0) when F ≥ θ, not (0.0) when F < θ − hysteresis, else unchanged.

    A NaN signal (warm-up, or a day without settlements) changes nothing.
    """
    state = pd.Series(np.nan, index=signal.index)
    state[signal >= theta] = 1.0
    state[signal < theta - hysteresis] = 0.0
    return state.ffill().fillna(0.0)


def h6_exposure(crowded: pd.Series, base: float, multiplier: float) -> pd.Series:
    """H6's target: ``base`` when not crowded, ``multiplier × base`` when crowded."""
    exposure: pd.Series = base * (1 - (1 - multiplier) * crowded)
    return exposure

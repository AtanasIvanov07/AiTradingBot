"""Performance metrics, exactly as defined in research/hypotheses/_CONVENTIONS.md §6.

All metrics take an equity curve marked at candle closes plus the starting capital, which is the
value just before the first candle's open. Returns therefore include the first candle.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import pandas as pd

from aitradingbot.analysis.engine import BacktestResult

DAYS_PER_YEAR = 365.0


def with_start(equity: pd.Series, initial: float, step: pd.Timedelta) -> pd.Series:
    """Equity indexed by the moment it was measured: ``initial`` at the first candle's open,
    then each mark at its candle's close."""
    times = [equity.index[0], *(t + step for t in equity.index)]
    return pd.Series([initial, *equity.to_list()], index=pd.DatetimeIndex(times), dtype=float)


def total_days(equity: pd.Series, step: pd.Timedelta) -> float:
    span = equity.index[-1] + step - equity.index[0]
    return float(span / pd.Timedelta(days=1))


def cagr(equity: pd.Series, initial: float, step: pd.Timedelta) -> float:
    final = float(equity.iloc[-1])
    if final <= 0:
        return -1.0
    return float((final / initial) ** (DAYS_PER_YEAR / total_days(equity, step)) - 1)


def max_drawdown(equity: pd.Series, initial: float, step: pd.Timedelta) -> float:
    """Largest peak-to-trough fall, as a negative fraction (e.g. -0.35)."""
    curve = with_start(equity, initial, step)
    return float((curve / curve.cummax() - 1).min())


def period_returns(equity: pd.Series, initial: float, step: pd.Timedelta) -> pd.Series:
    curve = with_start(equity, initial, step)
    returns = curve.pct_change().iloc[1:]
    returns.index = equity.index  # label each return by the candle that produced it
    return returns


def sharpe(equity: pd.Series, initial: float, step: pd.Timedelta) -> float:
    returns = period_returns(equity, initial, step)
    std = float(returns.std())
    if std == 0 or math.isnan(std):
        return 0.0
    periods_per_year = pd.Timedelta(days=DAYS_PER_YEAR) / step
    return float(returns.mean()) / std * math.sqrt(periods_per_year)


def calmar(equity: pd.Series, initial: float, step: pd.Timedelta) -> float:
    drawdown = abs(max_drawdown(equity, initial, step))
    growth = cagr(equity, initial, step)
    if drawdown == 0:  # e.g. never invested: no risk, but no reward either
        return math.inf if growth > 0 else 0.0
    return growth / drawdown


def candle_years(returns: pd.Series) -> pd.Index:
    return pd.DatetimeIndex(returns.index).year


def yearly_returns(equity: pd.Series, initial: float, step: pd.Timedelta) -> pd.Series:
    returns = period_returns(equity, initial, step)
    by_year = (1 + returns).groupby(candle_years(returns)).prod() - 1
    return by_year.astype(float)


def cagr_without_best_year(equity: pd.Series, initial: float, step: pd.Timedelta) -> float:
    """CAGR after deleting every return from the best calendar year (§7, criterion 7)."""
    returns = period_returns(equity, initial, step)
    best = yearly_returns(equity, initial, step).idxmax()
    rest = returns[candle_years(returns) != best]
    if rest.empty:
        return 0.0
    growth = float((1 + rest).to_numpy().prod())
    days = len(rest) * (step / pd.Timedelta(days=1))
    return growth ** (DAYS_PER_YEAR / days) - 1 if growth > 0 else -1.0


@dataclass(frozen=True)
class Metrics:
    cagr: float
    max_drawdown: float
    sharpe: float
    calmar: float
    worst_year: float
    cagr_without_best_year: float
    round_trips: int
    trades: int
    time_in_market: float
    turnover_per_year: float  # traded notional ÷ average equity, per year

    def as_dict(self) -> dict[str, float]:
        return {key: float(value) for key, value in asdict(self).items()}


def round_trips(result: BacktestResult) -> int:
    """Number of times exposure in an asset went from positive back to zero."""
    count = 0
    for asset in result.exposure.columns:
        held = result.exposure[asset] > 0
        count += int((held.shift(1, fill_value=False) & ~held).sum())
    return count


def summarize(result: BacktestResult) -> Metrics:
    equity, initial, step = result.equity, result.initial, result.step
    years = total_days(equity, step) / DAYS_PER_YEAR
    traded = float(result.trades["notional"].abs().sum()) if len(result.trades) else 0.0
    average_equity = float(with_start(equity, initial, step).mean())
    return Metrics(
        cagr=cagr(equity, initial, step),
        max_drawdown=max_drawdown(equity, initial, step),
        sharpe=sharpe(equity, initial, step),
        calmar=calmar(equity, initial, step),
        worst_year=float(yearly_returns(equity, initial, step).min()),
        cagr_without_best_year=cagr_without_best_year(equity, initial, step),
        round_trips=round_trips(result),
        trades=len(result.trades),
        time_in_market=float((result.exposure.sum(axis=1) > 0).mean()),
        turnover_per_year=traded / average_equity / years if average_equity > 0 else 0.0,
    )

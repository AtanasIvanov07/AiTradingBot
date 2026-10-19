import math

import pandas as pd
import pytest

from aitradingbot.analysis.metrics import (
    cagr,
    cagr_without_best_year,
    calmar,
    max_drawdown,
    period_returns,
    sharpe,
    yearly_returns,
)

DAY = pd.Timedelta(days=1)


def curve(values: list[float], start: str = "2024-01-01") -> pd.Series:
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq=DAY, tz="UTC"))


def test_drawdown_and_returns_include_the_first_candle() -> None:
    equity = curve([110, 99, 120])
    assert max_drawdown(equity, 100, DAY) == pytest.approx(99 / 110 - 1)
    assert period_returns(equity, 100, DAY).to_list() == pytest.approx([0.1, -0.1, 120 / 99 - 1])
    assert max_drawdown(curve([90, 95]), 100, DAY) == pytest.approx(-0.1)  # loss on day one counts


def test_cagr_annualises_over_calendar_days() -> None:
    one_year = curve([100.0] * 364 + [121.0])  # 365 daily candles
    assert cagr(one_year, 100, DAY) == pytest.approx(0.21)
    assert cagr(curve([50.0] * 730), 100, DAY) == pytest.approx(0.5**0.5 - 1)


def test_sharpe_uses_sqrt_365() -> None:
    equity = curve([101, 100, 101, 100])
    returns = period_returns(equity, 100, DAY)
    expected = returns.mean() / returns.std() * math.sqrt(365)
    assert sharpe(equity, 100, DAY) == pytest.approx(expected)
    assert sharpe(curve([100, 100]), 100, DAY) == 0.0


def test_calmar_edge_cases() -> None:
    assert calmar(curve([100, 100, 100]), 100, DAY) == 0.0  # never invested: no reward
    assert math.isinf(calmar(curve([101, 102]), 100, DAY))  # gains without a drawdown
    equity = curve([120, 90, 130])  # 25% drawdown from 120 to 90
    assert calmar(equity, 100, DAY) == pytest.approx(cagr(equity, 100, DAY) / 0.25)


def test_best_year_removal() -> None:
    equity = curve([110, 121, 121, 121], start="2023-12-30")  # +21% in 2023, flat in 2024
    years = yearly_returns(equity, 100, DAY)
    assert years.to_dict() == pytest.approx({2023: 0.21, 2024: 0.0})
    assert cagr_without_best_year(equity, 100, DAY) == pytest.approx(0.0)

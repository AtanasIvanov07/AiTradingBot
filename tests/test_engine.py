import math

import pandas as pd
import pytest

from aitradingbot.analysis.engine import run_backtest
from aitradingbot.analysis.metrics import summarize

DAY = pd.Timedelta(days=1)
D0 = pd.Timestamp("2024-01-01", tz="UTC")  # warm-up candle: its close makes the first decision


def frame(values: list[float], column: str = "BTC") -> pd.DataFrame:
    return pd.DataFrame({column: values}, index=pd.date_range(D0, periods=len(values), freq=DAY))


def test_hand_calculated_round_trip() -> None:
    """Every number below is worked out by hand. Cost 1% per side, start with 1000.

    day   open  close  decided at close   what happens at the open
    D0    100   100    0                  (warm-up, not evaluated)
    D1    100   100    1                  D0 said 0 -> nothing        equity 1000
    D2    100   110    1                  D1 said 1 -> buy 990.099 + 9.901 fee = 9.90099 units
                                                                       equity 9.90099*110 = 1089.109
    D3    110   121    0                  already 100% -> no trade     equity 1198.020
    D4    120   125    0                  D3 said 0 -> sell 1188.119, 11.881 fee -> 1176.238
    """
    opens = frame([100, 100, 100, 110, 120])
    closes = frame([100, 100, 110, 121, 125])
    targets = frame([0, 1, 1, 0, 0])
    result = run_backtest(opens, closes, targets, 0.01, D0 + DAY, D0 + 4 * DAY, DAY, initial=1000)

    expected = [1000.0, 1000 / 1.01 * 1.10, 1000 / 1.01 * 1.21, 1000 / 1.01 * 1.20 * 0.99]
    assert result.equity.to_list() == pytest.approx(expected)
    assert result.equity.iloc[-1] == pytest.approx(1176.2376, abs=1e-4)
    assert result.trades["notional"].to_list() == pytest.approx([990.0990, -1188.1188], abs=1e-4)
    assert result.trades["cost"].sum() == pytest.approx(9.90099 + 11.881188, abs=1e-5)
    metrics = summarize(result)
    assert metrics.round_trips == 1
    assert metrics.time_in_market == 0.5
    assert metrics.max_drawdown == pytest.approx(1176.2376 / 1198.0198 - 1, abs=1e-6)


def test_decision_is_never_filled_in_its_own_candle() -> None:
    """A signal at D1's close can only trade at D2's open, even if D1's close is far better."""
    opens = frame([100, 100, 200])
    closes = frame([100, 100, 200])
    targets = frame([0, 1, 1])
    result = run_backtest(opens, closes, targets, 0.0, D0 + DAY, D0 + 2 * DAY, DAY, initial=1)
    assert result.trades["time"].to_list() == [D0 + 2 * DAY]
    assert result.equity.to_list() == pytest.approx([1.0, 1.0])  # bought at 200, closed at 200


def test_switch_sells_before_buying() -> None:
    """Rotating 100% from A to B: proceeds of the sale fund the purchase, both legs pay 1%."""
    opens = pd.concat([frame([10, 10, 10], "A"), frame([5, 5, 5], "B")], axis=1)
    closes = opens.copy()
    targets = pd.concat([frame([1, 0, 0], "A"), frame([0, 1, 1], "B")], axis=1)
    result = run_backtest(opens, closes, targets, 0.01, D0 + DAY, D0 + 2 * DAY, DAY, initial=100)
    # D1: buy A with 100 -> 100/1.01 worth. D2: sell it (x0.99), buy B (÷1.01).
    assert result.equity.iloc[-1] == pytest.approx(100 / 1.01 * 0.99 / 1.01)
    assert result.exposure.iloc[-1].to_list() == pytest.approx([0.0, 1.0])
    assert (result.trades["notional"] < 0).sum() == 1


def test_rebalance_band_skips_small_changes() -> None:
    opens = frame([100] * 5)
    targets = frame([0.6, 0.65, 0.8, 0.8, 0.8])
    result = run_backtest(
        opens, opens, targets, 0.0, D0 + DAY, D0 + 4 * DAY, DAY, rebalance_band=0.1
    )
    assert len(result.trades) == 2  # 0 -> 0.6, then 0.6 -> 0.8; the 0.05 step is ignored
    assert result.exposure["BTC"].iloc[-1] == pytest.approx(0.8)


def test_full_exit_ignores_the_band() -> None:
    opens = frame([100] * 4)
    targets = frame([0.05, 0.0, 0.0, 0.0])
    result = run_backtest(
        opens, opens, targets, 0.0, D0 + DAY, D0 + 3 * DAY, DAY, rebalance_band=0.1
    )
    assert result.exposure["BTC"].iloc[-1] == 0.0


def test_missing_candle_delays_the_trade() -> None:
    opens = frame([100, 100, math.nan, 100])
    closes = frame([100, 100, math.nan, 100])
    targets = frame([0, 1, 1, 1])
    result = run_backtest(opens, closes, targets, 0.0, D0 + DAY, D0 + 3 * DAY, DAY, initial=1)
    assert result.trades["time"].to_list() == [D0 + 3 * DAY]


def test_future_prices_cannot_change_the_past() -> None:
    opens = frame([100, 101, 102, 103, 104, 105])
    targets = frame([1, 1, 0, 1, 1, 1])
    base = run_backtest(opens, opens, targets, 0.003, D0 + DAY, D0 + 5 * DAY, DAY)
    shocked_prices = frame([100, 101, 102, 103, 999, 1])
    shocked = run_backtest(
        shocked_prices, shocked_prices, targets, 0.003, D0 + DAY, D0 + 5 * DAY, DAY
    )
    pd.testing.assert_series_equal(base.equity.iloc[:3], shocked.equity.iloc[:3])


def test_leverage_is_rejected() -> None:
    opens = pd.concat([frame([1, 1], "A"), frame([1, 1], "B")], axis=1)
    targets = pd.concat([frame([0.7, 0.7], "A"), frame([0.7, 0.7], "B")], axis=1)
    with pytest.raises(ValueError, match="leverage"):
        run_backtest(opens, opens, targets, 0.0, D0 + DAY, D0 + DAY, DAY)

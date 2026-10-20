"""The Freqtrade H5 strategy must trade exactly the rule the research code tested."""

import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd
import pytest

from aitradingbot.analysis import prescreen as ps
from aitradingbot.analysis.strategies import h1_trend_filter, h3_vol_target, h4_trend_vol

STRATEGY_FILE = Path(__file__).parents[1] / "user_data" / "strategies" / "h5_trend_vol.py"


def load_strategy() -> ModuleType:
    spec = importlib.util.spec_from_file_location("h5_trend_vol", STRATEGY_FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def random_candles(days: int = 900, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.04, days)))
    dates = pd.date_range("2019-01-01", periods=days, freq="D", tz="UTC")
    open_ = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame(
        {
            "date": dates,
            "open": open_,
            "high": np.maximum(open_, close) * 1.01,
            "low": np.minimum(open_, close) * 0.99,
            "close": close,
            "volume": 1.0,
        }
    )


def test_settings_match_the_registered_card() -> None:
    h5 = load_strategy()
    n, target_vol = (value for _, value in ps.FIXED["H5"])
    assert (n, target_vol) == (h5.N, h5.TARGET_VOL)
    assert (h5.BAND, h5.VOL_LOOKBACK) == (ps.H4_BAND, ps.H4_VOL_LOOKBACK)
    assert ps.REBALANCE_BANDS["H5"] == h5.REBALANCE_BAND
    assert h5.SLEEVE == 0.5
    strategy = h5.H5TrendVol({})
    assert strategy.timeframe == "1d" and not strategy.can_short
    assert strategy.position_adjustment_enable
    assert strategy.startup_candle_count >= h5.N


@pytest.mark.parametrize("seed", [3, 11, 29])
def test_indicators_equal_the_research_functions(seed: int) -> None:
    h5 = load_strategy()
    close = random_candles(seed=seed).set_index("date")["close"]
    exposure = h5.target_exposure(close)
    research = h4_trend_vol(close, 150, 0.02, 0.30, 30, 365)
    pd.testing.assert_series_equal(exposure["target"], research, check_names=False)
    trend = h1_trend_filter(close, 150, 0.02)
    pd.testing.assert_series_equal(exposure["trend"], trend, check_names=False)
    size = h3_vol_target(close, 0.30, 30, 365)
    pd.testing.assert_series_equal(exposure["size"], size, check_names=False)
    assert exposure["target"].gt(0).any() and exposure["target"].eq(0).any()


@pytest.mark.parametrize("cut", [200, 450, 700])
def test_indicators_never_look_ahead(cut: int) -> None:
    h5 = load_strategy()
    close = random_candles().set_index("date")["close"]
    shocked = close.copy()
    shocked.iloc[cut + 1 :] *= 4  # change only the future
    before = h5.target_exposure(close).iloc[: cut + 1]
    pd.testing.assert_frame_equal(before, h5.target_exposure(shocked).iloc[: cut + 1])


class FakeTrade:
    """The few Trade attributes adjust_trade_position uses."""

    def __init__(self, amount: float, stake_amount: float) -> None:
        self.pair = "BTC/EUR"
        self.amount = amount
        self.stake_amount = stake_amount  # cost basis, not market value
        self.has_open_orders = False
        self.data: dict[str, object] = {}

    def get_custom_data(self, key: str, default: object = None) -> object:
        return self.data.get(key, default)

    def set_custom_data(self, key: str, value: object) -> None:
        self.data[key] = value


def adjust(
    target: float, trade: FakeTrade, equity: float, rate: float, day: str = "2019-04-03"
) -> object:
    h5 = load_strategy()
    strategy = h5.H5TrendVol({})
    candle = pd.Series({"date": pd.Timestamp(day, tz="UTC"), "target": target})
    strategy.last_candle = lambda pair: candle
    strategy.sleeve_equity = lambda pair, current_rate: equity
    return strategy.adjust_trade_position(
        trade, pd.Timestamp(day, tz="UTC"), rate, 0.0, 5.0, 10_000.0, rate, rate, 0.0, 0.0
    )


def test_resize_down_sells_market_value_not_cost_basis() -> None:
    # Held at market: 2391 × 2.0 = 4782 of a 4782 sleeve (100%). Bought cheaper, cost basis 3900.
    trade = FakeTrade(amount=2391.0, stake_amount=3900.0)
    result = adjust(0.48, trade, equity=4782.0, rate=2.0)
    assert isinstance(result, tuple) and result[1] == "resize_down"
    stake = result[0]
    units_sold = abs(stake) * trade.amount / trade.stake_amount  # how Freqtrade converts it
    assert units_sold * 2.0 == pytest.approx(0.52 * 4782.0)  # leaves exactly 48% exposure


def test_resize_up_within_band_and_once_per_candle() -> None:
    trade = FakeTrade(amount=1000.0, stake_amount=2000.0)  # 2000 held of 5000 = 40%
    assert adjust(0.55, trade, equity=5000.0, rate=2.0) == (pytest.approx(750.0), "resize_up")
    assert adjust(0.55, trade, equity=5000.0, rate=2.0) is None  # same candle: already checked
    assert adjust(0.55, trade, equity=5000.0, rate=2.0, day="2019-04-04") is not None
    assert adjust(0.49, FakeTrade(1000.0, 2000.0), equity=5000.0, rate=2.0) is None  # 9 points
    assert adjust(0.0, FakeTrade(1000.0, 2000.0), equity=5000.0, rate=2.0) is None  # exit signal


def test_signals_follow_the_target() -> None:
    h5 = load_strategy()
    strategy = h5.H5TrendVol({})
    frame = strategy.populate_indicators(random_candles(), {"pair": "BTC/EUR"})
    frame = strategy.populate_entry_trend(frame, {"pair": "BTC/EUR"})
    frame = strategy.populate_exit_trend(frame, {"pair": "BTC/EUR"})
    enter = frame["enter_long"].fillna(0) == 1
    exit_ = frame["exit_long"].fillna(0) == 1
    assert (enter == (frame["target"] > h5.REBALANCE_BAND)).all()
    assert (exit_ == (frame["target"] <= 0)).all()
    assert not (enter & exit_).any() and enter.any() and exit_.any()
    assert set(frame.loc[enter, "enter_tag"]) == {"trend_on"}

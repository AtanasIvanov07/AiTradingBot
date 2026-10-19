import math

import numpy as np
import pandas as pd
import pytest

from aitradingbot.analysis.strategies import h1_trend_filter, h2_dual_momentum, h3_vol_target

DAY = pd.Timedelta(days=1)


def series(values: list[float], start: str = "2024-01-01") -> pd.Series:
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq=DAY, tz="UTC"))


def test_h1_hysteresis_by_hand() -> None:
    # n=3, band=5%. idx3: SMA 105, 115 > 110.25 -> in. idx4: 105 inside the band -> stay in.
    # idx5: SMA 105, 95 < 99.75 -> out. idx7: SMA 93.3, 100 > 98 -> in again.
    close = series([100, 100, 100, 115, 105, 95, 85, 100])
    assert h1_trend_filter(close, 3, 0.05).to_list() == [0, 0, 0, 1, 1, 0, 0, 1]


def test_h1_without_band_flips_on_every_cross() -> None:
    close = series([100, 100, 101, 99, 101, 99])
    assert h1_trend_filter(close, 2, 0.0).to_list() == [0, 0, 1, 0, 1, 0]


def h1_rule(close: pd.Series) -> pd.Series:
    return h1_trend_filter(close, 10, 0.02)


def h3_rule(close: pd.Series) -> pd.Series:
    return h3_vol_target(close, 0.5, 10, 365)


@pytest.mark.parametrize("cut", [5, 20, 40])
def test_signals_never_look_ahead(cut: int) -> None:
    rng = np.random.default_rng(1)
    close = series(list(100 * np.exp(np.cumsum(rng.normal(0, 0.03, 60)))))
    shocked = close.copy()
    shocked.iloc[cut + 1 :] = shocked.iloc[cut + 1 :] * 5  # change only the future
    for rule in (h1_rule, h3_rule):
        pd.testing.assert_series_equal(rule(close).iloc[: cut + 1], rule(shocked).iloc[: cut + 1])
    pair = pd.DataFrame({"BTC": close, "ETH": close.iloc[::-1].to_numpy()}, index=close.index)
    shocked_pair = pair.copy()
    shocked_pair.iloc[cut + 1 :] *= 3
    pd.testing.assert_frame_equal(
        h2_dual_momentum(pair, 7, 0.0).iloc[: cut + 1],
        h2_dual_momentum(shocked_pair, 7, 0.0).iloc[: cut + 1],
    )


def two_assets() -> pd.DataFrame:
    """Daily closes from Monday 2024-01-01. Sundays are Jan 7, 14 and 21."""
    index = pd.date_range("2024-01-01", "2024-01-21", freq=DAY, tz="UTC")
    btc = pd.Series(100.0, index=index)
    eth = pd.Series(100.0, index=index)
    btc["2024-01-07":] = 102.0  # Sunday 7th: BTC +2% on the day, ETH -1%
    eth["2024-01-07":] = 99.0
    btc["2024-01-14":] = 103.02  # Sunday 14th: BTC +1%, ETH +4% (3 points better)
    eth["2024-01-14":] = 102.96
    btc["2024-01-21":] = 103.02 * 0.99  # Sunday 21st: both negative
    eth["2024-01-21":] = 102.96 * 0.98
    return pd.DataFrame({"BTC": btc, "ETH": eth})


def held(weights: pd.DataFrame, day: str) -> str:
    row = weights.loc[pd.Timestamp(day, tz="UTC")]
    return "cash" if row.sum() == 0 else str(row.idxmax())


def test_h2_rules_by_hand() -> None:
    no_buffer = h2_dual_momentum(two_assets(), lookback=1, buffer=0.0)
    assert held(no_buffer, "2024-01-06") == "cash"  # no Sunday decision yet
    assert held(no_buffer, "2024-01-07") == "BTC"
    assert held(no_buffer, "2024-01-13") == "BTC"  # weekdays never change the holding
    assert held(no_buffer, "2024-01-14") == "ETH"  # 3 points better, no buffer -> switch
    assert held(no_buffer, "2024-01-21") == "cash"  # neither positive -> cash, unbuffered

    buffered = h2_dual_momentum(two_assets(), lookback=1, buffer=0.05)
    assert held(buffered, "2024-01-14") == "BTC"  # 3 points < 5-point buffer -> stay
    assert held(buffered, "2024-01-21") == "cash"


def test_h3_exposure_by_hand() -> None:
    # Log returns alternate +1%, -1%: sample std over 2 returns = 0.01·√2.
    log_close = np.cumsum([0.0] + [0.01 if i % 2 == 0 else -0.01 for i in range(9)])
    close = series(list(np.exp(log_close)))
    vol = 0.01 * math.sqrt(2) * math.sqrt(365)
    exposure = h3_vol_target(close, vol / 2, lookback=2, periods_per_year=365)
    assert exposure.iloc[:2].to_list() == [0.0, 0.0]  # warm-up: not enough returns yet
    assert exposure.iloc[2:].to_list() == pytest.approx([0.5] * 8)
    assert h3_vol_target(close, vol * 3, 2, 365).iloc[-1] == 1.0  # capped, never leveraged

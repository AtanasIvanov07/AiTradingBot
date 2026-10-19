from collections.abc import Callable

import pandas as pd
import pytest

from aitradingbot.ingest.common import TIMEFRAMES

MakeCandles = Callable[..., pd.DataFrame]


def make_candles(
    start: str = "2024-01-01", periods: int = 10, timeframe: str = "1d"
) -> pd.DataFrame:
    """A valid, gap-free canonical candle frame with a gentle up-trend."""
    times = pd.date_range(start, periods=periods, freq=TIMEFRAMES[timeframe], tz="UTC")
    close = pd.Series([100.0 + i for i in range(periods)])
    return pd.DataFrame(
        {
            "open_time": times,
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 10.0,
        }
    )


@pytest.fixture
def candles() -> MakeCandles:
    return make_candles

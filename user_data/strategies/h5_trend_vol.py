"""H5: H4's trend filter with volatility sizing, fixed at N=150 and 30% target vol.

Learning-only path (PROJECT_PLAN.md amendment A1): dry-run only, not evidence of an edge. H5 was
killed at Gate 1 (research/hypotheses/H5.md). The rule mirrors the research code
(``aitradingbot.analysis.strategies.h4_trend_vol`` and the engine's sleeve logic). This file is
self-contained, because the Docker image has no ``aitradingbot`` package.
``tests/test_freqtrade_strategy.py`` checks the two stay identical.

Each pair is an independent sleeve worth 50% of the starting capital plus that pair's own P&L.
Decisions use the last closed daily candle; orders go out at the next candle's open:

- target exposure = trend (1/0: SMA(150) with a 2% band) × min(1, 30% / 30-day realised vol);
- enter when flat and the target is above the 10-point rebalance band;
- resize once per candle, when the target and the current exposure differ by more than 10 points;
- exit fully when the target drops to 0 (trend off).

Differences from the research engine, accepted for this path:
- Freqtrade fills missing candles (previous close, zero volume); the research engine skips them.
- The current exposure includes Freqtrade's estimate of the exit fee.
- Exchange minimum orders apply (€5 on Bitvavo), so small resizes can be skipped.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy
from pandas import DataFrame

N = 150
BAND = 0.02
TARGET_VOL = 0.30
VOL_LOOKBACK = 30
PERIODS_PER_YEAR = 365
REBALANCE_BAND = 0.10
SLEEVE = 0.5
CHECKED_KEY = "resize_checked_candle"


def target_exposure(close: pd.Series) -> DataFrame:
    """Trend state, volatility size and their product, from closes up to each candle only."""
    sma = close.rolling(N, min_periods=N).mean()
    state = pd.Series(np.nan, index=close.index)
    state[close > sma * (1 + BAND)] = 1.0
    state[close < sma * (1 - BAND)] = 0.0
    trend = state.ffill().fillna(0.0)
    realised = np.log(close).diff().rolling(VOL_LOOKBACK, min_periods=VOL_LOOKBACK).std()
    size = (TARGET_VOL / (realised * math.sqrt(PERIODS_PER_YEAR))).clip(upper=1.0)
    size = size.replace([np.inf, -np.inf], 1.0).fillna(0.0)
    return DataFrame({"trend": trend, "size": size, "target": trend * size}, index=close.index)


class H5TrendVol(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1d"
    can_short = False

    minimal_roi = {"0": 1000.0}  # no take-profit: only the trend rule exits
    stoploss = -0.99  # no stop-loss: the card exits on daily closes only
    trailing_stop = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    process_only_new_candles = True
    position_adjustment_enable = True
    max_entry_position_adjustment = -1
    # SMA(150) plus room for the band state to settle; recursive-analysis checks this.
    startup_candle_count = 400

    def populate_indicators(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        exposure = target_exposure(dataframe["close"])
        dataframe["trend"] = exposure["trend"]
        dataframe["size"] = exposure["size"]
        dataframe["target"] = exposure["target"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        dataframe.loc[dataframe["target"] > REBALANCE_BAND, ["enter_long", "enter_tag"]] = (
            1,
            "trend_on",
        )
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict[str, Any]) -> DataFrame:
        dataframe.loc[dataframe["target"] <= 0, ["exit_long", "exit_tag"]] = (1, "trend_off")
        return dataframe

    # --- sizing ---------------------------------------------------------------------------------

    def last_candle(self, pair: str) -> pd.Series | None:
        """The last closed candle (in backtesting, the one before the candle being traded)."""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return None
        return dataframe.iloc[-1]

    def starting_capital(self) -> float:
        """Fixed capital from the config.

        Not ``wallets.get_starting_balance()``: that one already includes the open trades' realised
        profit, which ``sleeve_equity`` adds itself.
        """
        capital = self.config.get("available_capital", self.config.get("dry_run_wallet", 0.0))
        if isinstance(capital, dict):  # multi-currency dry-run wallet
            capital = capital.get(self.config["stake_currency"], 0.0)
        return float(capital)

    def sleeve_equity(self, pair: str, rate: float) -> float:
        """50% of the starting capital plus this pair's realised and unrealised P&L."""
        equity = SLEEVE * self.starting_capital()
        for trade in Trade.get_trades_proxy(pair=pair, is_open=False):
            equity += trade.close_profit_abs or 0.0
        for trade in Trade.get_trades_proxy(pair=pair, is_open=True):
            equity += trade.realized_profit + trade.calc_profit(rate)
        return equity

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs: Any,
    ) -> float:
        candle = self.last_candle(pair)
        if candle is None:
            return 0.0
        stake = float(candle["target"]) * self.sleeve_equity(pair, current_rate)
        return min(stake, max_stake)

    def adjust_trade_position(
        self,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        min_stake: float | None,
        max_stake: float,
        current_entry_rate: float,
        current_exit_rate: float,
        current_entry_profit: float,
        current_exit_profit: float,
        **kwargs: Any,
    ) -> tuple[float | None, str | None] | None:
        candle = self.last_candle(trade.pair)
        if candle is None or trade.has_open_orders:
            return None
        candle_date = str(candle["date"])
        if trade.get_custom_data(CHECKED_KEY) == candle_date:
            return None  # once per candle, as in research: not on every intraday loop
        trade.set_custom_data(CHECKED_KEY, candle_date)

        target = float(candle["target"])
        if target <= 0:
            return None  # the exit signal closes the whole position
        equity = self.sleeve_equity(trade.pair, current_rate)
        held = trade.amount * current_rate
        if equity <= 0 or abs(target - held / equity) <= REBALANCE_BAND:
            return None
        delta = target * equity - held
        if delta > 0:
            return min(delta, max_stake), "resize_up"
        # Freqtrade sells |stake| × amount / trade.stake_amount, i.e. a share of the cost basis,
        # not of market value. Convert, so that `delta` euros of market value are sold.
        return delta * trade.stake_amount / held, "resize_down"

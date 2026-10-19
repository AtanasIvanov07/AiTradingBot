"""Minimal long-only spot backtest engine for the pre-screen (_CONVENTIONS.md §3–4).

Timing, the rule that matters most for avoiding look-ahead bias:
- ``targets`` holds the exposure decided at the **close** of each candle (indexed by its open time).
- That decision executes at the **open of the next candle**, never within the candle that made it.
- Equity is marked at each candle's close.

Exposure means value held ÷ portfolio equity, per asset, between 0 and 1 (no leverage, no shorts).
Costs (fee + slippage) are a fraction of traded notional, charged on every side. Sells execute
before buys at the same open, so a switch can fund itself.

Deliberately a plain loop over candles: it handles stateful rebalancing (bands, cash limits,
missing candles) more transparently than vectorised tricks, and is fast enough at our data size.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

EPSILON = 1e-9  # ignore exposure differences smaller than this (floating-point noise)


@dataclass
class BacktestResult:
    equity: pd.Series  # marked at each candle close, index = candle open time
    exposure: pd.DataFrame  # per-asset value ÷ equity at each close
    trades: pd.DataFrame  # columns: time, asset, notional (signed: + buy, − sell), cost
    initial: float
    step: pd.Timedelta


def run_backtest(
    opens: pd.DataFrame,
    closes: pd.DataFrame,
    targets: pd.DataFrame,
    cost: float,
    start: pd.Timestamp,
    end: pd.Timestamp,
    step: pd.Timedelta,
    rebalance_band: float = 0.0,
    initial: float = 1.0,
) -> BacktestResult:
    """Simulate trading ``targets`` over the candles opening from ``start`` to ``end`` inclusive.

    The decision executed at ``start``'s open is the one made at the close of the candle before it,
    so warm-up history must extend at least one candle before ``start``. Missing candles (NaN open)
    block trading in that asset for that candle; the pending target is retried at the next open.
    Holdings are marked with the last known close. A trade happens when target and current
    exposure differ by more than ``rebalance_band``, or when the target is a full exit to zero.
    """
    assets = list(targets.columns)
    index = pd.date_range(start - step, end, freq=step)
    decided = targets.reindex(index).ffill().fillna(0.0)[assets].to_numpy(dtype=float)
    open_prices = opens.reindex(index)[assets].to_numpy(dtype=float)
    marks = closes.reindex(index)[assets].ffill().to_numpy(dtype=float)
    if not (decided >= -EPSILON).all() or (decided.sum(axis=1) > 1 + EPSILON).any():
        raise ValueError("targets must be ≥ 0 per asset and sum to ≤ 1 (no leverage)")

    cash = initial
    units = [0.0] * len(assets)
    equity_values: list[float] = []
    exposure_rows: list[list[float]] = []
    trade_rows: list[tuple[pd.Timestamp, str, float, float]] = []

    for t in range(1, len(index)):
        prices = [
            open_prices[t][a] if not math.isnan(open_prices[t][a]) else marks[t - 1][a]
            for a in range(len(assets))
        ]
        held_value = sum(
            u * p for u, p in zip(units, prices, strict=True) if u and not math.isnan(p)
        )
        equity_open = cash + held_value
        tradable = [not math.isnan(open_prices[t][a]) for a in range(len(assets))]
        deltas = [0.0] * len(assets)
        for a in range(len(assets)):
            if not tradable[a] or equity_open <= 0:
                continue
            current = units[a] * prices[a] / equity_open if units[a] else 0.0
            target = decided[t - 1][a]
            full_exit = target <= EPSILON and units[a] > 0
            if full_exit or abs(target - current) > max(rebalance_band, EPSILON):
                deltas[a] = target * equity_open - units[a] * prices[a]

        for a in range(len(assets)):  # sells first, so their proceeds can fund buys
            if deltas[a] < 0:
                notional = -deltas[a]
                if decided[t - 1][a] <= EPSILON:
                    notional = units[a] * prices[a]  # exact full exit, no dust left behind
                units[a] = 0.0 if decided[t - 1][a] <= EPSILON else units[a] - notional / prices[a]
                cash += notional * (1 - cost)
                trade_rows.append((index[t], assets[a], -notional, notional * cost))

        wanted = sum(d for d in deltas if d > 0)
        if wanted > 0:
            scale = min(1.0, cash / (wanted * (1 + cost)))  # never spend cash we don't have
            for a in range(len(assets)):
                if deltas[a] > 0:
                    notional = deltas[a] * scale
                    units[a] += notional / prices[a]
                    cash -= notional * (1 + cost)
                    trade_rows.append((index[t], assets[a], notional, notional * cost))

        values = [u * m if u else 0.0 for u, m in zip(units, marks[t], strict=True)]
        equity = cash + sum(values)
        equity_values.append(equity)
        exposure_rows.append([v / equity if equity > 0 else 0.0 for v in values])

    evaluated = index[1:]
    trades = pd.DataFrame(trade_rows, columns=["time", "asset", "notional", "cost"])
    return BacktestResult(
        equity=pd.Series(equity_values, index=evaluated, name="equity"),
        exposure=pd.DataFrame(exposure_rows, index=evaluated, columns=assets),
        trades=trades,
        initial=initial,
        step=step,
    )

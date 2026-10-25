import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aitradingbot.analysis import gate2 as g2
from aitradingbot.analysis import h6
from aitradingbot.analysis import prescreen as ps
from aitradingbot.analysis.metrics import Metrics
from aitradingbot.analysis.strategies import (
    daily_funding,
    h6_crowded,
    h6_exposure,
    h6_funding_signal,
)
from aitradingbot.ingest import funding
from aitradingbot.ingest.common import Dataset, write_clean

DAY = pd.Timedelta(days=1)


def utc(text: str) -> pd.Timestamp:
    return pd.Timestamp(text, tz="UTC")


def settlements(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "funding_time": [utc(t) for t, _ in rows],
            "interval_hours": 8.0,
            "rate": [r for _, r in rows],
        }
    )


# --- registered settings ------------------------------------------------------------------------


def test_registered_settings() -> None:
    variants = h6.grid_variants()
    assert len(variants) == 18
    assert h6.GRID == {"lookback": [3, 7, 14], "theta": [0.20, 0.35, 0.50], "x": [0.0, 0.5]}
    assert (h6.BASE, h6.HYSTERESIS, h6.REBALANCE_BAND) == (0.50, 0.10, 0.10)
    assert h6.CORNER == (("lookback", 3), ("theta", 0.20), ("x", 0.0))
    assert (utc("2020-02-01"), utc("2024-12-31")) == h6.DEVELOPMENT
    assert [w[0] for w in h6.WINDOWS] == [
        f"{y}H{half}" for y in range(2020, 2025) for half in (1, 2)
    ]
    assert h6.WINDOWS[0] == ("2020H1", "2020-02-01", "2020-06-30")
    assert (h6.MIN_POSITIVE_WINDOWS, h6.MIN_EPISODES, h6.R1_SHARPE_SHARE) == (6, 3, 0.7)
    assert (h6.RANDOM_RUNS, h6.MC_PATHS, h6.MC_BLOCK, h6.SEED) == (1000, 10000, 20, 20261025)
    assert h6.MC_DAYS == g2.holdout_days() == 638
    assert h6.TRIALS_BEFORE == 67
    assert (h6.COST_R2, h6.COST_R4, h6.COST_R5) == (0.006, 0.003, 0.006)


def test_neighbours() -> None:
    middle = (("lookback", 7), ("theta", 0.35), ("x", 0.0))
    assert sorted(h6.neighbours(middle)) == sorted(
        [
            (("lookback", 3), ("theta", 0.35), ("x", 0.0)),
            (("lookback", 14), ("theta", 0.35), ("x", 0.0)),
            (("lookback", 7), ("theta", 0.20), ("x", 0.0)),
            (("lookback", 7), ("theta", 0.50), ("x", 0.0)),
            (("lookback", 7), ("theta", 0.35), ("x", 0.5)),
        ]
    )
    assert len(h6.neighbours(h6.CORNER)) == 3


def test_robustness_variants_round_halves_up() -> None:
    def lookbacks(lookback: int) -> list[float]:
        variants = h6.robustness_variants((("lookback", lookback), ("theta", 0.35), ("x", 0.0)))
        return [h6.param(v, "lookback") for v in variants[:2]]

    assert lookbacks(3) == [2, 4]  # 2.25, 3.75
    assert lookbacks(7) == [5, 9]  # 5.25, 8.75
    assert lookbacks(14) == [11, 18]  # 10.5, 17.5
    variants = h6.robustness_variants((("lookback", 7), ("theta", 0.35), ("x", 0.5)))
    assert [h6.param(v, "theta") for v in variants[2:]] == [0.2625, 0.4375]
    assert all(h6.param(v, "x") == 0.5 for v in variants)


# --- the signal, checked by hand ----------------------------------------------------------------


def test_daily_funding_assigns_midnight_to_the_day_it_opens() -> None:
    daily = daily_funding(
        settlements(
            [
                ("2024-01-01 00:00", 0.0001),
                ("2024-01-01 08:00", 0.0002),
                ("2024-01-01 16:00", 0.0003),
                ("2024-01-02 00:00", 0.0010),  # the 2024-01-01 candle's close: next day
                ("2024-01-04 08:00", 0.0004),  # 2024-01-03 has no settlement
            ]
        )
    )
    assert daily.index.tolist() == [utc(f"2024-01-0{d}") for d in (1, 2, 3, 4)]
    assert daily.iloc[0] == pytest.approx(0.0006)
    assert daily.iloc[1] == pytest.approx(0.0010)
    assert math.isnan(daily.iloc[2])
    assert daily.iloc[3] == pytest.approx(0.0004)


def test_signal_is_the_annualised_lookback_mean() -> None:
    days = pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC")
    daily = pd.Series([0.0003, 0.0006, 0.0009, float("nan")], index=days)
    signal = h6_funding_signal(daily, 2)
    assert math.isnan(signal.iloc[0])  # warm-up
    assert signal.iloc[1] == pytest.approx(0.00045 * 365)  # 16.4%
    assert signal.iloc[2] == pytest.approx(0.00075 * 365)  # 27.4%
    assert math.isnan(signal.iloc[3])  # a day without data: no update


def test_crowded_state_has_hysteresis() -> None:
    days = pd.date_range("2024-01-01", periods=8, freq="D", tz="UTC")
    signal = pd.Series([0.30, 0.35, 0.30, 0.26, 0.25, 0.24, float("nan"), 0.40], index=days)
    state = h6_crowded(signal, theta=0.35, hysteresis=0.10)
    # on at ≥ 35%, held down to 25% (not below θ − 10), off below 25%, NaN changes nothing
    assert state.tolist() == [0, 1, 1, 1, 1, 0, 0, 1]


def test_exposure_levels() -> None:
    state = pd.Series([0.0, 1.0, 0.0])
    assert h6_exposure(state, 0.5, 0.0).tolist() == [0.5, 0.0, 0.5]
    assert h6_exposure(state, 0.5, 0.5).tolist() == [0.5, 0.25, 0.5]


def test_signal_never_looks_ahead() -> None:
    rng = np.random.default_rng(3)
    times = pd.date_range("2024-01-01", periods=60 * 3, freq="8h", tz="UTC")
    rates = rng.normal(0.0003, 0.0003, len(times))  # F swings around θ
    base = pd.DataFrame({"funding_time": times, "interval_hours": 8.0, "rate": rates})
    cutoff = utc("2024-02-01")
    changed = base.copy()
    future = changed["funding_time"] >= cutoff  # includes the 2024-01-31 candle's close
    changed.loc[future, "rate"] = 0.05
    before = h6_crowded(h6_funding_signal(daily_funding(base), 7), 0.35, 0.10)
    after = h6_crowded(h6_funding_signal(daily_funding(changed), 7), 0.35, 0.10)
    decided = before.index < cutoff
    assert before[decided].equals(after[decided])
    assert not before.equals(after)


# --- R2, R5 and selection ------------------------------------------------------------------------


def test_window_returns_measure_each_half_year() -> None:
    days = pd.date_range("2020-02-01", "2024-12-31", freq="D", tz="UTC")
    equity = pd.Series(np.linspace(1.01, 2.0, len(days)), index=days)
    found = h6.window_returns(equity, 1.0, DAY)
    assert list(found) == [w[0] for w in h6.WINDOWS]
    # 2020H1 runs from the initial 1.0 at 1 Feb to the 30 Jun close
    assert found["2020H1"] == pytest.approx(float(equity[utc("2020-06-30")]) - 1)


def test_random_crowded_targets_keep_lengths_and_levels() -> None:
    days = pd.date_range("2022-01-01", periods=100, freq="D", tz="UTC")
    rng = np.random.default_rng(5)
    for _ in range(50):
        found = h6.random_crowded_targets({"BTC": ([3, 10, 1], 0.5), "ETH": ([], 0.0)}, days, rng)
        btc = found["BTC"]
        assert set(btc.unique()) <= {0.5, 0.25}
        crowded = (btc == 0.25).astype(float)
        assert sorted(length for _, length in g2.positions(crowded)) == [1, 3, 10]
        assert (found["ETH"] == 0.5).all()


def metrics(calmar: float, trades: int = 10) -> Metrics:
    return Metrics(0.1, -0.2, 1.0, calmar, -0.1, 0.05, 5, trades, 0.5, 2.0)


def test_selection_prefers_a_plateau_over_a_spike() -> None:
    spike = (("lookback", 3), ("theta", 0.20), ("x", 0.0))
    center = (("lookback", 7), ("theta", 0.35), ("x", 0.5))
    plateau = {center, *h6.neighbours(center)}
    evaluations = {}
    for params in h6.grid_variants():
        value = 5.0 if params == spike else 1.5 if params in plateau else 0.2
        per_asset = {"BTC": metrics(value), "ETH": metrics(value)}
        evaluations[params] = ps.Evaluation(params, 0.006, metrics(value), per_asset)
    scores = h6.selection_scores(evaluations)
    assert scores[center] == 1.5 and scores[spike] == 0.2  # the spike's neighbours are poor
    selected = h6.select(evaluations)
    assert selected != spike and scores[selected] == max(scores.values())


def test_selection_ties_go_to_fewer_trades() -> None:
    quiet = (("lookback", 14), ("theta", 0.50), ("x", 0.5))
    evaluations = {}
    for params in h6.grid_variants():
        trades = 3 if params == quiet else 10
        per_asset = {"BTC": metrics(1.0), "ETH": metrics(1.0)}
        evaluations[params] = ps.Evaluation(params, 0.006, metrics(1.0, trades), per_asset)
    assert h6.select(evaluations) == quiet


# --- end to end on synthetic data ---------------------------------------------------------------


def write_synthetic(root: Path, *, shock_after_development: bool = False) -> None:
    """Prices for all three sources and funding with crowded spells, through 2026-09-30.

    With ``shock_after_development``, everything after 2024-12-31 is replaced by a crash and
    extreme funding: the gate must not notice.
    """
    rng = np.random.default_rng(11)
    times = pd.date_range("2019-01-01", "2026-09-30", freq="D", tz="UTC")
    after = times > h6.last_day()
    for source in ("kraken", "binance", "bitvavo"):
        for asset, drift in (("BTC", 0.0009), ("ETH", 0.0011)):
            close = 100 * np.exp(np.cumsum(rng.normal(drift, 0.03, len(times))))
            if shock_after_development:
                close = np.where(after, close[~after][-1] * 0.1, close)
            open_ = np.concatenate([[close[0]], close[:-1]])
            frame = pd.DataFrame(
                {
                    "open_time": times,
                    "open": open_,
                    "high": np.maximum(open_, close) * 1.01,
                    "low": np.minimum(open_, close) * 0.99,
                    "close": close,
                    "volume": 1.0,
                }
            )
            write_clean(Dataset(source, f"{asset}/{ps.QUOTES[source]}", "1d"), frame, [], root)
    stamps = pd.date_range("2020-01-01", "2026-09-30 16:00", freq="8h", tz="UTC")
    for symbol in h6.SYMBOLS.values():
        spells = np.sin(np.arange(len(stamps)) / 90.0)  # about 190-day cycles
        rate = 0.0001 + 0.0006 * np.clip(spells, 0, None) + rng.normal(0, 0.00005, len(stamps))
        if shock_after_development:
            rate = np.where(stamps >= h6.last_day() + DAY, 0.003, rate)
        frame = pd.DataFrame({"funding_time": stamps, "interval_hours": 8.0, "rate": rate})
        funding.write_clean(symbol, frame, [], root)


def test_end_to_end_on_synthetic_data(tmp_path: Path) -> None:
    write_synthetic(tmp_path)
    gate = h6.gate1(tmp_path, random_runs=20, mc_paths=200)
    assert len(gate.evaluations) == 18 and len(gate.robustness) == 4
    assert gate.window == (utc("2020-02-01"), utc("2024-12-31"))
    names = [c.criterion for c in gate.checks]
    for prefix in ("1 ", "2 ", "3 ", "4 ", "6 Plateau", "7 ", "R1", "R2", "R5", "R6", "H6 kill"):
        assert any(n.startswith(prefix) for n in names), prefix
    assert sum(n.startswith("R1") for n in names) == 4
    assert len(gate.windows) == 10 and 0 < gate.mc_p95 < 1
    assert all(count >= 1 for count in gate.episode_counts.values())
    assert gate.passed == all(c.passed for c in gate.checks)
    text = h6.render(gate)
    assert "Gate 1′ H6" in text and "R2 half-years" in text

    # Timing: with x = 0, a crowded decision at a close empties the sleeve at the next open.
    params = (("lookback", 7), ("theta", 0.35), ("x", 0.0))
    result = gate.evaluations[params].result
    assert result is not None
    market = h6.load_market("kraken", tmp_path)
    daily = h6.load_funding(tmp_path)
    assert market.closes.index.max() == h6.last_day()  # nothing from the holdout is loaded
    assert all(series.index.max() == h6.last_day() for series in daily.values())
    state = h6.crowded(daily["BTC"], params, market)
    held = result.exposure["BTC"]
    decided = state.shift(1).reindex(held.index)
    assert (decided == 1).sum() > 0
    assert (held[decided == 1] == 0).all()
    assert (held[decided == 0] > 0).all()


def test_data_after_development_cannot_change_the_result(tmp_path: Path) -> None:
    clean, shocked = tmp_path / "clean", tmp_path / "shocked"
    write_synthetic(clean)
    write_synthetic(shocked, shock_after_development=True)
    first = h6.gate1(clean, random_runs=5, mc_paths=50)
    second = h6.gate1(shocked, random_runs=5, mc_paths=50)
    assert first.selected == second.selected
    for params, evaluation in first.evaluations.items():
        assert evaluation.portfolio == second.evaluations[params].portfolio
    assert [c.detail for c in first.checks] == [c.detail for c in second.checks]

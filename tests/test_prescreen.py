from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aitradingbot.analysis import prescreen as ps
from aitradingbot.analysis.engine import BacktestResult
from aitradingbot.analysis.metrics import Metrics
from aitradingbot.ingest.common import Dataset, write_clean


def test_grids_match_the_registered_cards() -> None:
    assert [len(ps.grid_variants(h)) for h in ("H1", "H2", "H3", "H4")] == [18, 15, 12, 16]
    assert ps.grid_variants("H1")[0] == (("n", 50), ("band", 0.0))
    assert ps.GRIDS["H4"] == {"n": [50, 100, 150, 200], "target_vol": [0.30, 0.40, 0.50, 0.60]}
    assert (ps.H4_BAND, ps.H4_VOL_LOOKBACK, ps.REBALANCE_BANDS["H4"]) == (0.02, 30, 0.10)


def test_neighbours_are_one_step_in_one_parameter() -> None:
    corner = (("n", 50), ("band", 0.0))
    assert sorted(ps.neighbours("H1", corner)) == sorted(
        [(("n", 75), ("band", 0.0)), (("n", 50), ("band", 0.02))]
    )
    assert len(ps.neighbours("H1", (("n", 125), ("band", 0.02)))) == 4


def metrics(calmar: float, trades: int = 10) -> Metrics:
    return Metrics(0.1, -0.2, 1.0, calmar, -0.1, 0.05, 5, trades, 0.5, 2.0)


def test_selection_prefers_a_plateau_over_a_spike() -> None:
    evaluations = {}
    for params in ps.grid_variants("H1"):
        value = 0.5
        if params == (("n", 50), ("band", 0.04)):
            value = 3.0  # isolated spike: best raw Calmar, but its neighbours are poor
        if dict(params)["n"] in (100, 125, 150):
            value = 1.0  # broad plateau: many variants tie on the smoothed score
        trades = 5 if params == (("n", 125), ("band", 0.02)) else 10  # registered tie-break
        per_asset = {"BTC": metrics(value), "ETH": metrics(value)}
        evaluations[params] = ps.Evaluation(params, 0.006, metrics(value, trades), per_asset)
    scores = ps.selection_scores("H1", evaluations)
    assert scores[(("n", 50), ("band", 0.04))] == 0.5  # median of 3.0, 0.5, 0.5
    assert ps.select("H1", evaluations) == (("n", 125), ("band", 0.02))


def test_holding_concentration() -> None:
    index = pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC")
    exposure = pd.DataFrame({"BTC": [1, 1, 0, 0], "ETH": [0, 0, 1, 1]}, index=index, dtype=float)
    equity = pd.Series([1.1, 1.2, 1.25, 1.3], index=index)  # +0.2 holding BTC, +0.1 holding ETH
    result = BacktestResult(equity, exposure, pd.DataFrame(), 1.0, pd.Timedelta(days=1))
    assert ps.holding_concentration(result) == pytest.approx(0.2 / 0.3)


def write_synthetic_market(root: Path, source: str = "kraken", quote: str = "EUR") -> None:
    rng = np.random.default_rng(7)
    times = pd.date_range("2016-06-01", "2022-12-31", freq="D", tz="UTC")
    for asset, drift in (("BTC", 0.0008), ("ETH", 0.001)):
        close = 100 * np.exp(np.cumsum(rng.normal(drift, 0.035, len(times))))
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
        write_clean(Dataset(source, f"{asset}/{quote}", "1d"), frame, [], root)


def test_h4_targets_are_trend_times_size(tmp_path: Path) -> None:
    write_synthetic_market(tmp_path)
    market = ps.load_market("kraken", "1d", tmp_path)
    params = (("n", 100), ("target_vol", 0.40))
    h4 = ps.sleeve_targets("H4", params, market, "BTC")
    trend = ps.sleeve_targets("H1", (("n", 100), ("band", 0.02)), market, "BTC")
    size = ps.sleeve_targets("H3", (("target_vol", 0.40), ("lookback", 30)), market, "BTC")
    pd.testing.assert_series_equal(h4, trend * size, check_names=False)
    assert (h4[trend == 0] == 0).all() and h4.max() <= 1.0
    assert ps.warmup("H4", params, market) == 100
    assert ps.warmup("H4", (("n", 50), ("target_vol", 0.3)), market) == 50


@pytest.mark.parametrize("hypothesis", ["H1", "H2", "H3", "H4"])
def test_end_to_end_on_synthetic_data(tmp_path: Path, hypothesis: str) -> None:
    write_synthetic_market(tmp_path)
    screen = ps.prescreen(hypothesis, tmp_path)
    assert screen.window[0] == pd.Timestamp("2018-01-01", tz="UTC")
    assert screen.window[1] == pd.Timestamp("2022-12-31", tz="UTC")
    assert screen.selected in screen.evaluations
    names = [c.criterion for c in screen.checks]
    assert any(n.startswith("7 ") for n in names)
    assert any("Plateau" in n for n in names)
    report = ps.render(screen)
    assert f"Pre-screen {hypothesis}" in report and "## Decision:" in report
    assert "Binance USDT (confirmation 1): data not available, skipped" in report
    if hypothesis in {"H1", "H4"}:  # no Binance data -> the registered kill check cannot pass
        binance = next(c for c in screen.checks if "Binance" in c.criterion)
        assert binance.criterion.startswith(f"{hypothesis} kill")
        assert not binance.passed and not screen.passed
    if hypothesis in {"H3", "H4"}:
        assert any(
            c.criterion == f"{hypothesis} kill: turnover ≤ 400% per year" for c in screen.checks
        )
    if hypothesis == "H4":  # exits to cash, so the standard drawdown bar applies, not H3's
        assert any(n.startswith("2 Max drawdown ≤ 40%") for n in names)
        assert not any("25% smaller" in n for n in names)


def test_confirmation_window_starts_after_warmup(tmp_path: Path) -> None:
    write_synthetic_market(tmp_path)
    market = ps.load_market("kraken", "1d", tmp_path)
    late = ps.Market(
        "late", "1d", market.opens, market.closes,
        {a: s["2019-03-08":] for a, s in market.raw_closes.items()}, market.step,
    )  # fmt: skip
    start, _ = ps.development_window(late, warmup_candles=200)
    assert start == pd.Timestamp("2019-09-25", tz="UTC")

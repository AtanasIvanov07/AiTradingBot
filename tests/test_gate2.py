import json
import math
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from aitradingbot.analysis import gate2 as g2
from aitradingbot.analysis import prescreen as ps
from aitradingbot.analysis.engine import BacktestResult
from aitradingbot.ingest.common import Dataset, write_clean

DAY = pd.Timedelta(days=1)


def write_market(root: Path, source: str = "kraken", start: str = "2016-06-01") -> None:
    """Synthetic BTC/ETH daily candles through the end of the holdout (2026-09-30)."""
    rng = np.random.default_rng(11)
    times = pd.date_range(start, "2026-09-30", freq="D", tz="UTC")
    quote = ps.QUOTES[source]
    for asset, drift in (("BTC", 0.0009), ("ETH", 0.0011)):
        close = 100 * np.exp(np.cumsum(rng.normal(drift, 0.03, len(times))))
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


def test_registered_settings() -> None:
    assert g2.H5 == (("n", 150), ("target_vol", 0.30))
    assert g2.ROBUSTNESS == [
        (("n", 113), ("target_vol", 0.30)),
        (("n", 188), ("target_vol", 0.30)),
        (("n", 150), ("target_vol", 0.225)),
        (("n", 150), ("target_vol", 0.375)),
    ]
    assert (g2.RANDOM_RUNS, g2.MC_PATHS, g2.MC_BLOCK, g2.SEED) == (1000, 10000, 20, 20261020)
    assert [w[0] for w in g2.WINDOWS] == ["2023H1", "2023H2", "2024H1", "2024H2"]
    assert g2.holdout_days() == 638 and g2.TRIALS == 67


def test_positions_are_runs_of_exposure() -> None:
    exposure = pd.Series([0.4, 0.4, 0, 0, 0.5, 0.5, 0.5, 0, 0.2])
    assert g2.positions(exposure) == [(0, 2), (4, 3), (8, 1)]  # open at the start and at the end
    assert g2.positions(pd.Series([0.0, 0.0])) == []


def test_random_layout_keeps_order_and_never_overlaps() -> None:
    rng = np.random.default_rng(0)
    durations, days = [3, 5, 2], 20
    firsts, lasts = set(), set()
    for _ in range(2000):
        starts = g2.random_layout(durations, days, rng)
        ends = [s + d for s, d in zip(starts, durations, strict=True)]
        assert starts[0] >= 0 and ends[-1] <= days
        assert all(ends[i] < starts[i + 1] for i in range(len(starts) - 1))  # >= 1 flat day
        firsts.add(starts[0])
        lasts.add(ends[-1])
    assert 0 in firsts and days in lasts  # every placement is reachable, edges included
    assert g2.random_layout([], 10, rng) == []
    with pytest.raises(ValueError):
        g2.random_layout([5, 5], 10, rng)  # 5 + 1 flat day + 5 > 10


def test_bootstrap_drawdowns() -> None:
    rising = np.full(100, 0.01)
    assert g2.bootstrap_drawdowns(rising, 50, 200, 20).max() == 0.0
    noisy = np.random.default_rng(1).normal(0, 0.03, 500)
    first = g2.bootstrap_drawdowns(noisy, 638, 300, 20)
    assert first.shape == (300,) and (first > 0).all() and (first < 1).all()
    assert np.array_equal(first, g2.bootstrap_drawdowns(noisy, 638, 300, 20))  # fixed seed


def test_window_returns_split_one_continuous_run() -> None:
    days = pd.date_range("2023-01-01", "2024-12-31", freq="D", tz="UTC")
    equity = pd.Series(1.0, index=days)
    equity[days >= pd.Timestamp("2023-07-01", tz="UTC")] = 1.1  # +10% on 2023-07-01
    result = BacktestResult(equity, pd.DataFrame(index=days), pd.DataFrame(), 1.0, DAY)
    returns = g2.window_returns(result)
    assert returns == pytest.approx({"2023H1": 0.0, "2023H2": 0.1, "2024H1": 0.0, "2024H2": 0.0})


def test_truncate_hides_everything_later(tmp_path: Path) -> None:
    write_market(tmp_path)
    market = ps.load_market("kraken", "1d", tmp_path)
    cut = g2.truncate(market, pd.Timestamp("2024-12-31", tz="UTC"))
    last = pd.Timestamp("2024-12-31", tz="UTC")
    assert cut.opens.index.max() == last and cut.closes.index.max() == last
    assert all(s.index.max() == last for s in cut.raw_closes.values())
    assert market.opens.index.max() == pd.Timestamp("2026-09-30", tz="UTC")  # original untouched


def test_deflated_sharpe_penalises_more_trials() -> None:
    rng = np.random.default_rng(2)
    returns = pd.Series(rng.normal(0.002, 0.03, 1500))
    trials = list(rng.normal(0.8, 0.3, 60))
    one = g2.deflated_sharpe(returns, trials, 1, 365)
    many = g2.deflated_sharpe(returns, trials, 67, 365)
    assert 0.5 < one <= 1 and many < one
    worse = g2.deflated_sharpe(returns - 0.002, trials, 67, 365)
    assert worse < many
    assert math.isnan(g2.deflated_sharpe(pd.Series([0.01, 0.01, 0.01]), trials, 67, 365))


def test_research_and_freqtrade_positions_compare(tmp_path: Path) -> None:
    days = pd.date_range("2023-01-01", periods=6, freq="D", tz="UTC")
    exposure = pd.DataFrame({"BTC": [0, 0.5, 0.5, 0, 0.4, 0.4]}, index=days, dtype=float)
    sleeve = BacktestResult(pd.Series(0.5, index=days), exposure, pd.DataFrame(), 0.5, DAY)
    run = g2.Run(sleeve, {"BTC": sleeve})
    assert g2.research_positions(run) == {
        ("BTC", "2023-01-02", "2023-01-04"),
        ("BTC", "2023-01-05", ""),  # still open at the end
    }
    trades = [
        {"pair": "BTC/EUR", "open_date": "2023-01-02 00:00:00+00:00",
         "close_date": "2023-01-04 00:00:00+00:00", "exit_reason": "trend_off"},
        {"pair": "BTC/EUR", "open_date": "2023-01-05 00:00:00+00:00",
         "close_date": "2023-01-06 00:00:00+00:00", "exit_reason": "force_exit"},
    ]  # fmt: skip
    result = tmp_path / "result.zip"
    with zipfile.ZipFile(result, "w") as archive:
        archive.writestr("r.json", json.dumps({"strategy": {"H5TrendVol": {"trades": trades}}}))
    assert g2.freqtrade_positions(result) == g2.research_positions(run)


@pytest.fixture
def market_root(tmp_path: Path) -> Path:
    write_market(tmp_path)
    write_market(tmp_path, "bitvavo", start="2019-03-08")
    return tmp_path


def quick_gate(
    root: Path, monkeypatch: pytest.MonkeyPatch, force: bool | None = None
) -> tuple[g2.Gate2, list[Any]]:
    """Run the gate on synthetic data, fast: few random runs, stubbed trial Sharpes."""
    monkeypatch.setattr(g2, "development_trial_sharpes", lambda market: [0.5, 0.8, 1.1])
    opened: list[Any] = []
    real_open = g2.open_holdout

    def spy(full: ps.Market, limit: float) -> g2.Holdout:
        opened.append(full)
        return real_open(full, limit)

    monkeypatch.setattr(g2, "open_holdout", spy)
    if force is not None:
        real = g2.criteria

        def forced(*args: Any) -> list[ps.Check]:
            return [ps.Check(c.criterion, force, c.detail) for c in real(*args)]

        monkeypatch.setattr(g2, "criteria", forced)
    return g2.gate2(root, freqtrade=False, random_runs=20), opened


def test_gate_structure_on_synthetic_data(
    market_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate, opened = quick_gate(market_root, monkeypatch)
    assert gate.window == (
        pd.Timestamp("2023-01-01", tz="UTC"),
        pd.Timestamp("2024-12-31", tz="UTC"),
    )
    names = [c.criterion for c in gate.checks]
    assert [n[:2] for n in names] == ["G1", "G2", "G3", "G4", "G4", "G4", "G4", "G5", "G6", "G7"]
    assert set(gate.windows) == {"2023H1", "2023H2", "2024H1", "2024H2"}
    assert gate.drawdown_limit > 0 and not math.isnan(gate.random_p95)
    assert (gate.holdout is not None) == gate.validation_passed == bool(opened)
    report = g2.render(gate)
    assert "# Gate 2 H5" in report and "## Decision:" in report and "G7 Bitvavo" in report


def test_holdout_opens_only_when_every_criterion_passes(
    market_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failed, opened = quick_gate(market_root, monkeypatch, force=False)
    assert failed.holdout is None and opened == [] and not failed.passed
    assert "stays closed" in g2.render(failed) and "KILL (validation)" in g2.render(failed)

    passed, opened = quick_gate(market_root, monkeypatch, force=True)
    assert passed.holdout is not None and len(opened) == 1
    assert [c.criterion[:1] for c in passed.holdout.checks] == ["H", "H"]
    assert passed.holdout.window[0] == pd.Timestamp("2025-01-01", tz="UTC")
    assert passed.holdout.drawdown_limit == passed.drawdown_limit
    report = g2.render(passed)
    assert "Holdout return ≥ 0" in report
    assert ("PASS" in report) == passed.holdout.passed


def test_missing_bitvavo_fails_g7(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_market(tmp_path)  # Kraken only
    gate, _ = quick_gate(tmp_path, monkeypatch)
    g7 = next(c for c in gate.checks if c.criterion.startswith("G7"))
    assert not g7.passed and g7.detail == "Bitvavo data missing"
    assert gate.holdout is None


def test_random_targets_match_h5_positions_and_time_in_market() -> None:
    decisions = pd.date_range("2022-12-31", "2024-12-31", freq="D", tz="UTC")
    plans = {"BTC": ([30, 120, 7], 0.45), "ETH": ([], 0.0)}
    rng = np.random.default_rng(3)
    for _ in range(50):
        targets = g2.random_targets(plans, decisions, rng)
        btc = targets["BTC"]
        assert (btc > 0).sum() == 157 and set(btc[btc > 0].round(6)) == {0.45}
        assert sorted(length for _, length in g2.positions(btc)) == [7, 30, 120]
        assert btc.iloc[-1] == 0 or btc.iloc[-2] == 0.45  # last decision day may close a run
        assert (targets["ETH"] == 0).all()


def test_validation_never_sees_later_data(
    market_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[pd.Timestamp] = []
    real = g2.run_h5

    def spy(market: ps.Market, *args: Any, **kwargs: Any) -> g2.Run:
        seen.append(market.opens.index.max())
        return real(market, *args, **kwargs)

    monkeypatch.setattr(g2, "run_h5", spy)
    gate, _ = quick_gate(market_root, monkeypatch, force=False)  # validation fails: no holdout
    assert gate.holdout is None and seen
    assert max(seen) <= pd.Timestamp("2024-12-31", tz="UTC")


def test_freqtrade_export_has_real_candles_and_nothing_later(tmp_path: Path) -> None:
    write_market(tmp_path)
    folder = tmp_path / "export"
    g2.export_candles(tmp_path, pd.Timestamp("2024-12-31", tz="UTC"), folder)
    btc = pd.read_feather(folder / "BTC_EUR-1d.feather")
    assert list(btc.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert btc["date"].max() == pd.Timestamp("2024-12-31", tz="UTC")
    assert (btc["high"] > btc[["open", "close"]].max(axis=1)).all()  # the real highs, not rebuilt

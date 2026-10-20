"""Gate 2 (Phase 2) out-of-sample test for H5, as registered in research/hypotheses/H5-gate2.md.

Usage:
    python -m aitradingbot.analysis.gate2 --out research/reports/gate2-H5.md

G1–G7 run on the validation split (2023–2024), with every market cut off at the split's last day,
so nothing later can leak in. Only if all seven pass does the same run open the holdout
(2025-01 → 2026-09), once, and judge it against the validation Monte Carlo. Exit code 0 only on a
Gate 2 PASS. Changing any rule here needs a dated amendment to the registered card first.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pandas as pd

from aitradingbot.analysis import prescreen as ps
from aitradingbot.analysis.engine import BacktestResult, run_backtest
from aitradingbot.analysis.metrics import Metrics, period_returns, summarize, with_start
from aitradingbot.ingest.common import Dataset
from aitradingbot.splits import DEVELOPMENT, HOLDOUT, VALIDATION

Params = ps.Params
Check = ps.Check
HYPOTHESIS = "H5"
H5 = ps.FIXED["H5"]
ROBUSTNESS: list[
    Params
] = [  # G4: ±25% in one parameter at a time (150 → 113, 188; 30% → 22.5, 37.5)
    (("n", 113), ("target_vol", 0.30)),
    (("n", 188), ("target_vol", 0.30)),
    (("n", 150), ("target_vol", 0.225)),
    (("n", 150), ("target_vol", 0.375)),
]
WINDOWS = [  # G6: fixed parameters, half-year windows of the continuous validation run
    ("2023H1", "2023-01-01", "2023-06-30"),
    ("2023H2", "2023-07-01", "2023-12-31"),
    ("2024H1", "2024-01-01", "2024-06-30"),
    ("2024H2", "2024-07-01", "2024-12-31"),
]
RANDOM_RUNS = 1_000
MC_PATHS = 10_000
MC_BLOCK = 20
SEED = 20261020
MIN_ORDERS = 50
TRIALS = 67  # 63 variants before Gate 2 + the 4 robustness variants
EULER_GAMMA = 0.5772156649015329
Window = tuple[pd.Timestamp, pd.Timestamp]


# --- running H5 (and any target series) on the research engine ------------------------------------


def truncate(market: ps.Market, last: pd.Timestamp) -> ps.Market:
    """The market as it was known at the close of ``last``: nothing after it exists."""
    cut = last + pd.Timedelta(days=1)
    return replace(
        market,
        opens=market.opens[market.opens.index < cut],
        closes=market.closes[market.closes.index < cut],
        raw_closes={a: s[s.index < cut] for a, s in market.raw_closes.items()},
    )


def window_for(market: ps.Market, split: Window) -> Window:
    return ps.split_window(market, split, ps.warmup(HYPOTHESIS, H5, market))


@dataclass(frozen=True)
class Run:
    portfolio: BacktestResult
    sleeves: dict[str, BacktestResult]

    @property
    def metrics(self) -> Metrics:
        return summarize(self.portfolio)

    def asset_metrics(self) -> dict[str, Metrics]:
        return {a: summarize(r) for a, r in self.sleeves.items()}


def run_targets(
    targets: dict[str, pd.Series], market: ps.Market, cost: float, window: Window
) -> Run:
    """50% sleeves, independent, with H5's rebalance band (conventions §3)."""
    start, end = window
    sleeves = {
        asset: run_backtest(
            market.opens[[asset]],
            market.closes[[asset]],
            target.to_frame(asset),
            cost,
            start,
            end,
            market.step,
            rebalance_band=ps.REBALANCE_BANDS[HYPOTHESIS],
            initial=0.5,
        )  # fmt: skip
        for asset, target in targets.items()
    }
    return Run(ps.combine_sleeves(sleeves), sleeves)


def run_h5(market: ps.Market, cost: float, window: Window, params: Params = H5) -> Run:
    targets = {a: ps.sleeve_targets(HYPOTHESIS, params, market, a) for a in ps.ASSETS}
    return run_targets(targets, market, cost, window)


# --- G5: random entries ---------------------------------------------------------------------------


def positions(exposure: pd.Series) -> list[tuple[int, int]]:
    """(first day offset, length in days) of each run of exposure > 0."""
    held = (exposure > 0).to_numpy()
    runs: list[tuple[int, int]] = []
    i = 0
    while i < len(held):
        if held[i]:
            j = i
            while j < len(held) and held[j]:
                j += 1
            runs.append((i, j - i))
            i = j
        else:
            i += 1
    return runs


def random_layout(durations: list[int], days: int, rng: np.random.Generator) -> list[int]:
    """Uniformly random start offsets for blocks of ``durations``, in that order.

    Consecutive blocks keep at least one flat day between them. Back-to-back blocks would merge
    into one position and change the trade count, which the card keeps equal to H5's.
    Stars and bars: once the k - 1 separating days are set aside, an arrangement of k blocks among
    the remaining free days is a choice of k slots out of free + k. The i-th chosen slot minus i
    is the number of extra free days before block i.
    """
    k = len(durations)
    if k == 0:
        return []
    free = days - sum(durations) - (k - 1)
    if free < 0:
        raise ValueError("the positions don't fit in the window")
    slots = np.sort(rng.choice(free + k, size=k, replace=False))
    gaps = slots - np.arange(k)
    before = np.concatenate([[0], np.cumsum(durations)[:-1]]).astype(int) + np.arange(k)
    return [int(g + b) for g, b in zip(gaps, before, strict=True)]


def random_entry_calmars(
    h5: Run, market: ps.Market, cost: float, window: Window, runs: int, seed: int = SEED
) -> npt.NDArray[np.float64]:
    """Calmars of random strategies with H5's position count, durations and time in market."""
    rng = np.random.default_rng(seed)
    start, end = window
    decisions = pd.date_range(start - market.step, end, freq=market.step)
    plans = {}
    for asset, sleeve in h5.sleeves.items():
        exposure = sleeve.exposure[asset]
        held = exposure[exposure > 0]
        level = float(held.mean()) if len(held) else 0.0
        plans[asset] = ([length for _, length in positions(exposure)], level)
    calmars = np.empty(runs)
    for run in range(runs):
        targets = random_targets(plans, decisions, rng)
        calmars[run] = run_targets(targets, market, cost, window).metrics.calmar
    return calmars


def random_targets(
    plans: dict[str, tuple[list[int], float]], decisions: pd.DatetimeIndex, rng: np.random.Generator
) -> dict[str, pd.Series]:
    """One random strategy: per asset, H5's durations shuffled and placed at random, held at
    H5's average in-position exposure. ``decisions`` runs from the day before the window."""
    days = len(decisions) - 1
    targets = {}
    for asset, (durations, level) in plans.items():
        order = [int(d) for d in rng.permutation(durations)] if durations else []
        target = pd.Series(0.0, index=decisions)
        for offset, length in zip(random_layout(order, days, rng), order, strict=True):
            target.iloc[offset : offset + length] = level  # decided the day before it's held
        targets[asset] = target
    return targets


# --- G6 and the holdout Monte Carlo ---------------------------------------------------------------


def window_returns(result: BacktestResult) -> dict[str, float]:
    """Net return of each registered half-year inside one continuous run."""
    curve = with_start(result.equity, result.initial, result.step)
    found = {}
    for name, first, last in WINDOWS:
        start = pd.Timestamp(first, tz="UTC")
        stop = pd.Timestamp(last, tz="UTC") + pd.Timedelta(days=1)  # mark after the last close
        if start in curve.index and stop in curve.index:
            found[name] = float(curve[stop] / curve[start] - 1)
    return found


def bootstrap_drawdowns(
    returns: npt.NDArray[np.float64], length: int, paths: int, block: int, seed: int = SEED
) -> npt.NDArray[np.float64]:
    """Max drawdown (positive fraction) of each circular-block-bootstrap path."""
    rng = np.random.default_rng(seed)
    n, blocks = len(returns), -(-length // block)
    starts = rng.integers(0, n, size=(paths, blocks))
    index = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
    sample = returns[index.reshape(paths, -1)[:, :length]]
    curve = np.concatenate([np.ones((paths, 1)), np.cumprod(1 + sample, axis=1)], axis=1)
    drawdown = 1 - curve / np.maximum.accumulate(curve, axis=1)
    result: npt.NDArray[np.float64] = drawdown.max(axis=1)
    return result


# --- deflated Sharpe ratio (reported only) --------------------------------------------------------


def deflated_sharpe(
    returns: pd.Series, trial_sharpes: list[float], trials: int, periods_per_year: float
) -> float:
    """Probability that the true Sharpe exceeds the best of ``trials`` lucky ones.

    Bailey & López de Prado (2014). The variance of the trial Sharpes estimates how far the best
    of ``trials`` independent tries would get by luck.
    """
    normal = statistics.NormalDist()
    r = returns.dropna().to_numpy(dtype=float)
    sd = float(r.std(ddof=1))
    if len(r) < 3 or sd == 0:
        return math.nan
    sr = float(r.mean()) / sd
    centred = r - r.mean()
    variance = float((centred**2).mean())
    skew = float((centred**3).mean()) / variance**1.5
    kurt = float((centred**4).mean()) / variance**2  # non-excess
    per_period = [s / math.sqrt(periods_per_year) for s in trial_sharpes]
    spread = statistics.pstdev(per_period) if len(per_period) > 1 else 0.0
    if trials > 1:
        expected_max = spread * (
            (1 - EULER_GAMMA) * normal.inv_cdf(1 - 1 / trials)
            + EULER_GAMMA * normal.inv_cdf(1 - 1 / (trials * math.e))
        )
    else:
        expected_max = 0.0
    denominator = 1 - skew * sr + (kurt - 1) / 4 * sr**2
    if denominator <= 0:
        return math.nan
    return normal.cdf((sr - expected_max) * math.sqrt(len(r) - 1) / math.sqrt(denominator))


def development_trial_sharpes(market: ps.Market) -> list[float]:
    """Annualised Sharpes of the Gate 1 grids (2× costs, development data), one per variant."""
    window = ps.development_window(market)
    sharpes = []
    for hypothesis in ("H1", "H2", "H3", "H4"):
        grid = ps.run_grid(hypothesis, market, ps.COST_STRESS, window)
        sharpes += [e.portfolio.sharpe for e in grid.values()]
    new_neighbour = (("n", 150), ("target_vol", 0.20))  # the only H5 run H4 didn't make
    evaluation = ps.run_variant(HYPOTHESIS, new_neighbour, market, ps.COST_STRESS, window)
    return [*sharpes, evaluation.portfolio.sharpe]


# --- Freqtrade implementation check ---------------------------------------------------------------


PositionKey = tuple[str, str, str]  # (asset, first day held, first day flat or "" if still open)


def research_positions(run: Run) -> set[PositionKey]:
    found = set()
    for asset, sleeve in run.sleeves.items():
        exposure = sleeve.exposure[asset]
        days = exposure.index
        for offset, length in positions(exposure):
            end = offset + length
            closed = str(days[end].date()) if end < len(days) else ""
            found.add((asset, str(days[offset].date()), closed))
    return found


def freqtrade_positions(result_zip: Path) -> set[PositionKey]:
    with zipfile.ZipFile(result_zip) as archive:
        name = next(
            n for n in archive.namelist()
            if n.endswith(".json") and "_config" not in n and "_market" not in n
        )  # fmt: skip
        data = json.loads(archive.read(name))
    found = set()
    for trade in data["strategy"]["H5TrendVol"]["trades"]:
        closed = "" if trade.get("exit_reason") == "force_exit" else trade["close_date"][:10]
        found.add((trade["pair"].split("/")[0], trade["open_date"][:10], closed))
    return found


def export_candles(root: Path | None, last_day: pd.Timestamp, folder: Path) -> None:
    """Clean Kraken BTC/ETH daily candles up to ``last_day``, in Freqtrade's feather format."""
    folder.mkdir(parents=True)
    columns = ["open_time", "open", "high", "low", "close", "volume"]
    for asset in ps.ASSETS:
        frame = Dataset(ps.PRIMARY, f"{asset}/{ps.QUOTES[ps.PRIMARY]}", "1d").load(root)
        frame = frame.loc[frame["open_time"] <= last_day, columns].reset_index(drop=True)
        frame.rename(columns={"open_time": "date"}).to_feather(folder / f"{asset}_EUR-1d.feather")


def freqtrade_backtest(
    root: Path | None, last_day: pd.Timestamp, window: Window, workdir: Path
) -> Path:
    """Backtest H5TrendVol in Freqtrade on the clean Kraken candles up to ``last_day``.

    The real highs and lows go in, not ones rebuilt from open and close. Freqtrade fills an
    order only if its (exchange-rounded) price lies inside the candle, so a high equal to the
    open made rounded exits "unfilled" and delayed them by days (found in a synthetic smoke test).
    """
    data = workdir / "kraken"
    export_candles(root, last_day, data)
    override = workdir / "override.json"
    override.write_text(
        json.dumps({"exchange": {"name": "kraken", "pair_whitelist": ["BTC/EUR", "ETH/EUR"]},
                    "dry_run_wallet": 10000}),
        encoding="utf-8",
    )  # fmt: skip
    results = workdir / "results"
    results.mkdir()
    first = window[0] - pd.Timedelta(days=1)  # Freqtrade can't trade a backtest's first candle
    last = window[1] + pd.Timedelta(days=1)
    name = "freqtrade.exe" if sys.platform == "win32" else "freqtrade"
    subprocess.run(
        [
            str(Path(sys.executable).with_name(name)), "backtesting",
            "--config", "user_data/config.json", "--config", str(override),
            "--userdir", "user_data", "--datadir", str(data), "--strategy", "H5TrendVol",
            "--timeframe", "1d", "--fee", str(ps.COST_BASE), "--export", "trades",
            "--backtest-directory", str(results),
            "--timerange", f"{first:%Y%m%d}-{last:%Y%m%d}",
        ],
        check=True, capture_output=True, encoding="utf-8", errors="replace",
    )  # fmt: skip
    latest = str(json.loads((results / ".last_result.json").read_text())["latest_backtest"])
    return results / latest


# --- the gate -------------------------------------------------------------------------------------


@dataclass
class Holdout:
    window: Window
    metrics: Metrics
    total_return: float
    drawdown_limit: float
    checks: list[Check]

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)


@dataclass
class Gate2:
    window: Window
    h5: Metrics
    per_asset: dict[str, Metrics]
    benchmarks: dict[str, Metrics]
    checks: list[Check]
    orders: int
    windows: dict[str, float]
    random_p95: float
    drawdown_limit: float
    holdout: Holdout | None
    informational: list[tuple[str, Metrics, Metrics | None]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    implementation: tuple[int, list[PositionKey], list[PositionKey]] | None = None
    deflated_sharpe: float = math.nan

    @property
    def validation_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def passed(self) -> bool:
        return self.validation_passed and self.holdout is not None and self.holdout.passed


def criteria(
    h5: Run, stress: Run, bench: dict[str, Metrics], variants: dict[Params, Metrics],
    windows: dict[str, float], random_p95: float, bitvavo: Metrics | None,
) -> list[Check]:  # fmt: skip
    m, b = h5.metrics, bench["50/50"]
    checks = [
        Check(
            "G1 Calmar ≥ 1.2× 50/50 buy & hold",
            m.calmar >= 1.2 * b.calmar,
            f"{m.calmar:.2f} vs 1.2 × {b.calmar:.2f} = {1.2 * b.calmar:.2f}",
        ),
        Check("G2 Max drawdown ≤ 35%", abs(m.max_drawdown) <= 0.35, f"{abs(m.max_drawdown):.1%}"),
        Check("G3 CAGR > 0 at 2× costs", stress.metrics.cagr > 0, f"{stress.metrics.cagr:.1%}"),
    ]
    for params, variant in variants.items():
        floor = 0.7 * m.sharpe
        checks.append(
            Check(
                f"G4 ±25%: {ps.label(params)} keeps ≥ 70% of Sharpe",
                m.sharpe > 0 and variant.sharpe >= floor,
                f"{variant.sharpe:.2f} vs 0.7 × {m.sharpe:.2f} = {floor:.2f}",
            )
        )
    checks.append(
        Check(
            f"G5 Calmar beats ≥ 95% of {RANDOM_RUNS:,} random-entry runs",
            m.calmar > random_p95,
            f"{m.calmar:.2f} vs 95th percentile {random_p95:.2f}",
        )
    )
    profitable = sum(r > 0 for r in windows.values())
    detail = ", ".join(f"{k} {v:+.1%}" for k, v in windows.items())
    checks.append(Check("G6 Profitable in ≥ 3 of 4 half-years", profitable >= 3, detail))
    checks.append(
        Check(
            "G7 Bitvavo EUR: CAGR > 0 at 2× costs",
            bitvavo is not None and bitvavo.cagr > 0,
            f"{bitvavo.cagr:.1%}" if bitvavo else "Bitvavo data missing",
        )
    )
    return checks


def holdout_days() -> int:
    return int((HOLDOUT[1] - HOLDOUT[0]) / pd.Timedelta(days=1)) + 1


def drawdown_limit(validation: Run) -> float:
    """95th-percentile Monte Carlo drawdown over a holdout-length path, from validation returns."""
    returns = period_returns(*_curve(validation)).to_numpy(dtype=float)
    drawdowns = bootstrap_drawdowns(returns, holdout_days(), MC_PATHS, MC_BLOCK)
    return float(np.percentile(drawdowns, 95))


def open_holdout(full: ps.Market, limit: float) -> Holdout:
    """The single look at 2025-01 → 2026-09, judged against the validation Monte Carlo."""
    window = window_for(full, HOLDOUT)
    run = run_h5(full, ps.COST_BASE, window)
    m = run.metrics
    total = float(run.portfolio.equity.iloc[-1] / run.portfolio.initial - 1)
    checks = [
        Check("H Holdout return ≥ 0", total >= 0, f"{total:+.1%}"),
        Check(
            "H Holdout max drawdown ≤ Monte Carlo 95th percentile",
            abs(m.max_drawdown) <= limit,
            f"{abs(m.max_drawdown):.1%} vs {limit:.1%}",
        ),
    ]
    return Holdout(window, m, total, limit, checks)


def gate2(
    root: Path | None = None, freqtrade: bool = True, random_runs: int = RANDOM_RUNS
) -> Gate2:
    full = ps.load_market(ps.PRIMARY, "1d", root)
    market = truncate(full, VALIDATION[1])  # validation stage: nothing after 2024-12-31 exists
    window = window_for(market, VALIDATION)
    h5 = run_h5(market, ps.COST_BASE, window)
    stress = run_h5(market, ps.COST_STRESS, window)
    bench = ps.run_benchmarks(market, ps.COST_BASE, window)
    variants = {p: run_h5(market, ps.COST_BASE, window, p).metrics for p in ROBUSTNESS}
    windows = window_returns(h5.portfolio)
    randoms = random_entry_calmars(h5, market, ps.COST_BASE, window, random_runs)
    random_p95 = float(np.percentile(randoms, 95))
    notes = [
        "Gate 1 exception (amendment A2): H5 failed Gate 1's plateau by 0.1 point.",
        "SOL/EUR: skipped (its data wasn't added before the run).",
    ]

    bitvavo = None
    other = ps.try_market("bitvavo", "1d", root)
    if other is not None:
        cut = truncate(other, VALIDATION[1])
        bitvavo = run_h5(cut, ps.COST_STRESS, window_for(cut, VALIDATION)).metrics
    checks = criteria(h5, stress, bench, variants, windows, random_p95, bitvavo)

    informational: list[tuple[str, Metrics, Metrics | None]] = [
        ("Primary at 0.60%/side", stress.metrics, None),
        ("Primary at 0.90%/side", run_h5(market, ps.COST_INFO, window).metrics, None),
    ]
    informational += [(f"Robustness {ps.label(p)}", m, None) for p, m in variants.items()]
    binance = ps.try_market("binance", "1d", root)
    if binance is not None:
        cut = truncate(binance, VALIDATION[1])
        bw = window_for(cut, VALIDATION)
        informational.append(
            (
                "Binance USDT at 0.60%/side",
                run_h5(cut, ps.COST_STRESS, bw).metrics,
                ps.run_benchmarks(cut, ps.COST_STRESS, bw)["50/50"],
            )
        )
    else:
        notes.append("Binance USDT: data not available, skipped")

    dev_market = truncate(full, DEVELOPMENT[1])
    dev_window = ps.development_window(dev_market)
    dev_returns = period_returns(*_curve(run_h5(dev_market, ps.COST_STRESS, dev_window)))
    dsr = deflated_sharpe(
        dev_returns, development_trial_sharpes(dev_market), TRIALS, market.periods_per_year
    )

    implementation = None
    if freqtrade:
        with tempfile.TemporaryDirectory() as tmp:
            ours = research_positions(h5)
            result = freqtrade_backtest(root, VALIDATION[1], window, Path(tmp))
            theirs = freqtrade_positions(result)
        implementation = (len(ours & theirs), sorted(ours - theirs), sorted(theirs - ours))
    else:
        notes.append("Freqtrade implementation check: not run (--no-freqtrade)")

    limit = drawdown_limit(h5)
    holdout = open_holdout(full, limit) if all(c.passed for c in checks) else None
    if holdout is None:
        notes.append("Holdout: not opened (a validation criterion failed); it stays closed.")
    return Gate2(
        window, h5.metrics, h5.asset_metrics(), bench, checks, len(h5.portfolio.trades), windows,
        random_p95, limit, holdout, informational, notes, implementation, dsr,
    )  # fmt: skip


def _curve(run: Run) -> tuple[pd.Series, float, pd.Timedelta]:
    return run.portfolio.equity, run.portfolio.initial, run.portfolio.step


# --- report ---------------------------------------------------------------------------------------


def render(gate: Gate2) -> str:
    start, end = gate.window
    if gate.passed:
        decision = "✅ PASS (Gate 2, by exception: H5 failed Gate 1's plateau)"
    elif gate.validation_passed:
        decision = "❌ KILL (holdout)"
    else:
        decision = "❌ KILL (validation)"
    confidence = "" if gate.orders >= MIN_ORDERS else " — **low confidence** (< 50 orders)"
    lines = [
        "# Gate 2 H5: out-of-sample test",
        "",
        f"Generated {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC "
        f"from code `{ps.git_revision()}`. "
        "Rules: [research/hypotheses/H5-gate2.md](../hypotheses/H5-gate2.md).",
        "",
        f"Validation: Kraken EUR 1d, {start:%Y-%m-%d} → {end:%Y-%m-%d}, modelled costs "
        f"{ps.COST_BASE:.2%} per side. Orders: **{gate.orders}**{confidence}.",
        "",
        f"## Decision: {decision}",
        "",
        "## H5 vs buy & hold (validation, modelled costs)",
        "",
        ps.row(["Series", *ps.METRIC_HEADER]),
        ps.row(["---"] + ["---:"] * len(ps.METRIC_HEADER)),
        ps.row(["H5 portfolio", *ps.metric_cells(gate.h5)]),
    ]
    lines += [ps.row([f"H5 {a}", *ps.metric_cells(m)]) for a, m in gate.per_asset.items()]
    lines += [ps.row([f"Buy & hold {n}", *ps.metric_cells(m)]) for n, m in gate.benchmarks.items()]
    lines += ["", "## Criteria (validation)", "", ps.row(["Criterion", "Result", "Detail"])]
    lines.append(ps.row(["---", "---", "---"]))
    lines += [ps.row([c.criterion, "✅" if c.passed else "❌", c.detail]) for c in gate.checks]
    lines += ["", "## Holdout (2025-01 → 2026-09)", ""]
    if gate.holdout is None:
        lines.append("Not opened: a validation criterion failed, so the holdout stays closed.")
    else:
        h = gate.holdout
        lines += [ps.row(["Criterion", "Result", "Detail"]), ps.row(["---", "---", "---"])]
        lines += [ps.row([c.criterion, "✅" if c.passed else "❌", c.detail]) for c in h.checks]
        lines += ["", ps.row(["Series", *ps.METRIC_HEADER])]
        lines.append(ps.row(["---"] + ["---:"] * len(ps.METRIC_HEADER)))
        lines.append(ps.row(["H5 holdout", *ps.metric_cells(h.metrics)]))
    lines += [
        "",
        "## Reported, not criteria",
        "",
        f"- Monte Carlo 95th-percentile drawdown over a holdout-length path (from validation): "
        f"{gate.drawdown_limit:.1%}. Cross-check against the §6.4 risk limits (20% / 30%).",
        f"- Deflated Sharpe ratio (development data, {TRIALS} trials): {gate.deflated_sharpe:.2f}",
        f"- Random-entry 95th-percentile Calmar: {gate.random_p95:.2f}",
    ]
    if gate.implementation is not None:
        same, ours, theirs = gate.implementation
        status = (
            "agree" if not (ours or theirs) else "**DIFFERENCES: investigate before accepting**"
        )
        lines.append(f"- Freqtrade implementation check: {same} identical positions; {status}")
        lines += [f"  - research only: {p}" for p in ours]
        lines += [f"  - Freqtrade only: {p}" for p in theirs]
    lines += ["", ps.row(["Run", "Series", *ps.METRIC_HEADER])]
    lines.append(ps.row(["---", "---"] + ["---:"] * len(ps.METRIC_HEADER)))
    for name, strategy, benchmark in gate.informational:
        lines.append(ps.row([name, "H5", *ps.metric_cells(strategy)]))
        if benchmark is not None:
            lines.append(ps.row([name, "50/50 buy & hold", *ps.metric_cells(benchmark)]))
    lines += ["", *[f"- {note}" for note in gate.notes], ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aitradingbot.analysis.gate2")
    parser.add_argument("--root", type=Path, default=None, help="data directory (default: ./data)")
    parser.add_argument("--out", type=Path, default=None, help="also write the report here")
    parser.add_argument("--no-freqtrade", action="store_true", help="skip the Freqtrade check")
    args = parser.parse_args(argv)
    gate = gate2(args.root, freqtrade=not args.no_freqtrade)
    text = render(gate)
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8", newline="\n")
    return 0 if gate.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

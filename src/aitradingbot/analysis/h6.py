"""Gate 1′ for H6, the funding-rate crowding filter, as registered in research/hypotheses/H6.md.

Usage:
    python -m aitradingbot.analysis.h6 --out research/reports/gate1-H6.md

PROJECT_PLAN.md amendment A3 step 3: the conventions §7 pass rule at 2× costs for the variant §8
selects, plus the card's in-sample checks R1–R6 and its kill rules. Development data only
(2020-02-01 → 2024-12-31): prices are cut at the last development day and funding at the last
settlement before 2025, so nothing from the holdout can leak in. Exit code 0 only on a Gate 1′ PASS.
Changing any rule here needs a dated amendment to the card first.
"""

from __future__ import annotations

import argparse
import math
import statistics
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pandas as pd

from aitradingbot.analysis import prescreen as ps
from aitradingbot.analysis.engine import run_backtest
from aitradingbot.analysis.gate2 import (
    Run,
    bootstrap_drawdowns,
    positions,
    random_layout,
    truncate,
)
from aitradingbot.analysis.metrics import Metrics, period_returns, with_start
from aitradingbot.analysis.strategies import (
    daily_funding,
    h6_crowded,
    h6_exposure,
    h6_funding_signal,
)
from aitradingbot.ingest import funding
from aitradingbot.splits import A3_DEVELOPMENT

Params = ps.Params
Check = ps.Check
Window = tuple[pd.Timestamp, pd.Timestamp]

HYPOTHESIS = "H6"
TITLE = "Funding-rate crowding filter"
DEVELOPMENT = (pd.Timestamp("2020-02-01", tz="UTC"), A3_DEVELOPMENT[1])  # card: Data / period
SYMBOLS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
GRID: dict[str, list[float]] = {
    "lookback": [3, 7, 14],  # L, days
    "theta": [0.20, 0.35, 0.50],  # annualised funding
    "x": [0.0, 0.5],  # crowded multiplier
}
VARIANT_CAP = 20
BASE = 0.50  # fixed: decision 1 at registration
HYSTERESIS = 0.10  # fixed: off when F < θ − 10 points
REBALANCE_BAND = 0.10  # card amendment 1: H4/H5's 10-point band
CORNER: Params = (("lookback", 3), ("theta", 0.20), ("x", 0.0))
MIN_EPISODES = 3
R1_SHARPE_SHARE = 0.7
WINDOWS = [  # R2: half-years of the continuous run, 2020H1 from 1 February
    ("2020H1", "2020-02-01", "2020-06-30"),
    ("2020H2", "2020-07-01", "2020-12-31"),
    ("2021H1", "2021-01-01", "2021-06-30"),
    ("2021H2", "2021-07-01", "2021-12-31"),
    ("2022H1", "2022-01-01", "2022-06-30"),
    ("2022H2", "2022-07-01", "2022-12-31"),
    ("2023H1", "2023-01-01", "2023-06-30"),
    ("2023H2", "2023-07-01", "2023-12-31"),
    ("2024H1", "2024-01-01", "2024-06-30"),
    ("2024H2", "2024-07-01", "2024-12-31"),
]
MIN_POSITIVE_WINDOWS = 6
RANDOM_RUNS = 1_000
RANDOM_PERCENTILE = 95
MC_PATHS = 10_000
MC_BLOCK = 20
MC_DAYS = 638  # the holdout's length
SEED = 20261025
TRIALS_BEFORE = 67  # H1–H5, journal #12
# Costs of the checks the card doesn't price (card amendment 1): pass/fail at 2×
# like every pre-screen criterion; the Monte Carlo at modelled costs, as the holdout will be judged.
COST_R2 = ps.COST_STRESS
COST_R4 = ps.COST_BASE
COST_R5 = ps.COST_STRESS


def param(params: Params, name: str) -> float:
    return dict(params)[name]


def label(params: Params) -> str:
    lookback, theta, x = (param(params, n) for n in ("lookback", "theta", "x"))
    return f"L={lookback:g}, θ={theta * 100:g}%, x={x:g}"


def grid_variants() -> list[Params]:
    variants: list[Params] = [()]
    for name, values in GRID.items():
        variants = [(*v, (name, value)) for v in variants for value in values]
    if len(variants) > VARIANT_CAP:
        raise AssertionError(f"H6 grid exceeds the registered cap of {VARIANT_CAP}")
    return variants


def neighbours(params: Params) -> list[Params]:
    """Immediate grid neighbours: adjacent L or θ at the same x, and the other x."""
    found = []
    for position, (name, value) in enumerate(params):
        values = GRID[name]
        i = values.index(value)
        for j in (i - 1, i + 1):
            if 0 <= j < len(values):
                swapped = list(params)
                swapped[position] = (name, values[j])
                found.append(tuple(swapped))
    return found


def half_up(value: float) -> int:
    """Round to whole days, halves up (H5's G4 rounded 112.5 to 113)."""
    return math.floor(value + 0.5)


def robustness_variants(params: Params) -> list[Params]:
    """R1: L × 0.75 and × 1.25 (whole days), then θ × 0.75 and × 1.25; one at a time."""
    lookback, theta, x = (param(params, n) for n in ("lookback", "theta", "x"))
    return [
        (("lookback", half_up(lookback * 0.75)), ("theta", theta), ("x", x)),
        (("lookback", half_up(lookback * 1.25)), ("theta", theta), ("x", x)),
        (("lookback", lookback), ("theta", round(theta * 0.75, 6)), ("x", x)),
        (("lookback", lookback), ("theta", round(theta * 1.25, 6)), ("x", x)),
    ]


# --- data ---------------------------------------------------------------------------------------


def last_day() -> pd.Timestamp:
    return DEVELOPMENT[1]


def load_funding(root: Path | None = None) -> dict[str, pd.Series]:
    """Daily funding sums per asset, from settlements before the day after development ends."""
    cut = last_day() + pd.Timedelta(days=1)
    found = {}
    for asset, symbol in SYMBOLS.items():
        settlements = funding.load(symbol, root)
        found[asset] = daily_funding(settlements[settlements["funding_time"] < cut])
    return found


def load_market(source: str, root: Path | None = None) -> ps.Market:
    return truncate(ps.load_market(source, "1d", root), last_day())


def window_for(market: ps.Market) -> Window:
    return ps.split_window(market, DEVELOPMENT)


# --- running H6 ---------------------------------------------------------------------------------


def crowded(daily: pd.Series, params: Params, market: ps.Market) -> pd.Series:
    """Crowded state decided at each daily close, on the market's calendar."""
    signal = h6_funding_signal(daily, int(param(params, "lookback")))
    state = h6_crowded(signal, param(params, "theta"), HYSTERESIS)
    return state.reindex(market.closes.index).ffill().fillna(0.0)


def targets(
    daily: dict[str, pd.Series], params: Params, market: ps.Market, window: Window
) -> dict[str, pd.Series]:
    found = {}
    for asset in ps.ASSETS:
        signal = h6_funding_signal(daily[asset], int(param(params, "lookback")))
        first_decision = window[0] - market.step
        if math.isnan(signal.get(first_decision, math.nan)):
            raise ValueError(f"{asset}: no funding signal yet at {first_decision:%Y-%m-%d}")
        state = crowded(daily[asset], params, market)
        found[asset] = h6_exposure(state, BASE, param(params, "x"))
    return found


def run_targets(
    target: dict[str, pd.Series], market: ps.Market, cost: float, window: Window
) -> Run:
    """50% sleeves, run independently with the 10-point rebalance band."""
    start, end = window
    sleeves = {
        asset: run_backtest(
            market.opens[[asset]],
            market.closes[[asset]],
            series.to_frame(asset),
            cost,
            start,
            end,
            market.step,
            rebalance_band=REBALANCE_BAND,
            initial=0.5,
        )  # fmt: skip
        for asset, series in target.items()
    }
    return Run(ps.combine_sleeves(sleeves), sleeves)


def evaluate(
    params: Params, daily: dict[str, pd.Series], market: ps.Market, cost: float, window: Window
) -> ps.Evaluation:
    run = run_targets(targets(daily, params, market, window), market, cost, window)
    return ps.Evaluation(params, cost, run.metrics, run.asset_metrics(), run.portfolio)


# --- selection and the pass rule (conventions §7–8) ---------------------------------------------


def selection_scores(evaluations: dict[Params, ps.Evaluation]) -> dict[Params, float]:
    scores = {}
    for params, evaluation in evaluations.items():
        values = [evaluation.selection_base()]
        values += [evaluations[n].selection_base() for n in neighbours(params)]
        scores[params] = statistics.median(values)
    return scores


def select(evaluations: dict[Params, ps.Evaluation]) -> Params:
    scores = selection_scores(evaluations)
    return max(scores, key=lambda p: (scores[p], -evaluations[p].portfolio.trades))


def pass_rule(
    evaluations: dict[Params, ps.Evaluation], selected: Params, benchmarks: dict[str, Metrics]
) -> list[Check]:
    chosen = evaluations[selected]
    checks = ps.series_checks(HYPOTHESIS, chosen, benchmarks)
    base = chosen.selection_base()
    for neighbour in neighbours(selected):
        other = evaluations[neighbour]
        failed = [
            c.criterion
            for c in ps.series_checks(HYPOTHESIS, other, benchmarks, "1–3")
            if not c.passed
        ]
        close_enough = abs(other.selection_base() - base) <= 0.3 * abs(base)
        checks.append(
            Check(
                f"6 Plateau: neighbour {label(neighbour)}",
                not failed and close_enough,
                f"Calmar {other.selection_base():.2f} vs selected {base:.2f}"
                + (f"; fails: {', '.join(failed)}" if failed else ""),
            )
        )
    without_best = chosen.portfolio.cagr_without_best_year
    checks.append(
        Check("7 CAGR > 0 without the best calendar year", without_best > 0, f"{without_best:.1%}")
    )
    return checks


# --- in-sample checks R1–R6 ---------------------------------------------------------------------


def decision_days(market: ps.Market, window: Window) -> pd.DatetimeIndex:
    """Closes whose decisions execute inside the window: the day before it, to its second-last."""
    start, end = window
    return pd.date_range(start - market.step, end - market.step, freq=market.step)


def episodes(state: pd.Series, days: pd.DatetimeIndex) -> list[tuple[int, int]]:
    """(offset, length) of each crowded run among the decisions that execute in the window."""
    return positions(state.reindex(days).ffill().fillna(0.0))


def window_returns(
    result_equity: pd.Series, initial: float, step: pd.Timedelta
) -> dict[str, float]:
    """R2: net return of each registered half-year inside one continuous run."""
    curve = with_start(result_equity, initial, step)
    found = {}
    for name, first, last in WINDOWS:
        start = pd.Timestamp(first, tz="UTC")
        stop = pd.Timestamp(last, tz="UTC") + pd.Timedelta(days=1)  # mark after the last close
        if start in curve.index and stop in curve.index:
            found[name] = float(curve[stop] / curve[start] - 1)
    return found


def random_crowded_targets(
    plans: dict[str, tuple[list[int], float]],
    days: pd.DatetimeIndex,
    rng: np.random.Generator,
) -> dict[str, pd.Series]:
    """R5: per asset, H6's crowded-episode lengths, shuffled and placed at random, non-overlapping.

    Exposure is ``BASE`` outside them and ``x × BASE`` inside, as for H6 itself.
    """
    found = {}
    for asset, (lengths, x) in plans.items():
        order = [int(d) for d in rng.permutation(lengths)] if lengths else []
        state = pd.Series(0.0, index=days)
        for offset, length in zip(random_layout(order, len(days), rng), order, strict=True):
            state.iloc[offset : offset + length] = 1.0
        found[asset] = h6_exposure(state, BASE, x)
    return found


def random_calmars(
    plans: dict[str, tuple[list[int], float]],
    market: ps.Market,
    window: Window,
    runs: int,
    seed: int = SEED,
) -> npt.NDArray[np.float64]:
    rng = np.random.default_rng(seed)
    days = decision_days(market, window)
    calmars = np.empty(runs)
    for run in range(runs):
        target = random_crowded_targets(plans, days, rng)
        calmars[run] = run_targets(target, market, COST_R5, window).metrics.calmar
    return calmars


# --- orchestration ------------------------------------------------------------------------------


@dataclass
class Gate1:
    window: Window
    evaluations: dict[Params, ps.Evaluation]
    scores: dict[Params, float]
    selected: Params
    benchmarks: dict[str, Metrics]
    checks: list[Check]
    robustness: dict[Params, ps.Evaluation]
    selected_base_cost: ps.Evaluation
    windows: dict[str, float]
    mc_p95: float
    random: npt.NDArray[np.float64]
    episode_counts: dict[str, int]
    informational: list[tuple[str, ps.Evaluation, dict[str, Metrics]]]
    notes: list[str]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def gate1(
    root: Path | None = None,
    random_runs: int = RANDOM_RUNS,
    mc_paths: int = MC_PATHS,
) -> Gate1:
    daily = load_funding(root)
    market = load_market(ps.PRIMARY, root)
    window = window_for(market)
    evaluations = {p: evaluate(p, daily, market, ps.COST_STRESS, window) for p in grid_variants()}
    scores = selection_scores(evaluations)
    selected = select(evaluations)
    benchmarks = ps.run_benchmarks(market, ps.COST_STRESS, window)
    checks = pass_rule(evaluations, selected, benchmarks)
    notes: list[str] = []
    runs = {ps.COST_STRESS: evaluations[selected]}

    def at(cost: float) -> ps.Evaluation:
        """The selected variant on Kraken at ``cost``, each run once."""
        if cost not in runs:
            runs[cost] = evaluate(selected, daily, market, cost, window)
        return runs[cost]

    # R1: ±25% robustness at 1× costs.
    base_cost = at(ps.COST_BASE)
    robustness = {
        p: evaluate(p, daily, market, ps.COST_BASE, window) for p in robustness_variants(selected)
    }
    floor = R1_SHARPE_SHARE * base_cost.portfolio.sharpe
    for params, evaluation in robustness.items():
        checks.append(
            Check(
                f"R1 Robustness: {label(params)}",
                evaluation.portfolio.sharpe >= floor,
                f"Sharpe {evaluation.portfolio.sharpe:.2f} vs floor "
                f"{R1_SHARPE_SHARE:g} × {base_cost.portfolio.sharpe:.2f} = {floor:.2f} (1× costs)",
            )
        )

    # R2: half-year windows of the continuous selected run.
    r2 = at(COST_R2).result
    assert r2 is not None
    windows = window_returns(r2.equity, r2.initial, r2.step)
    positive = sum(value > 0 for value in windows.values())
    checks.append(
        Check(
            f"R2 Walk-forward: net return > 0 in ≥ {MIN_POSITIVE_WINDOWS} of {len(WINDOWS)} "
            "half-years",
            len(windows) == len(WINDOWS) and positive >= MIN_POSITIVE_WINDOWS,
            f"{positive} of {len(windows)} ({COST_R2:.2%}/side)",
        )
    )

    # R4: Monte Carlo drawdown, reported and carried into the holdout registration.
    r4 = at(COST_R4).result
    assert r4 is not None
    returns = period_returns(r4.equity, r4.initial, r4.step)
    drawdowns = bootstrap_drawdowns(
        returns.to_numpy(dtype=float), MC_DAYS, mc_paths, MC_BLOCK, SEED
    )
    mc_p95 = float(np.percentile(drawdowns, 95))

    # R5: random crowded periods, same lengths, base and x.
    days = decision_days(market, window)
    x = param(selected, "x")
    plans: dict[str, tuple[list[int], float]] = {}
    episode_counts = {}
    for asset in ps.ASSETS:
        found = episodes(crowded(daily[asset], selected, market), days)
        plans[asset] = ([length for _, length in found], x)
        episode_counts[asset] = len(found)
    random = random_calmars(plans, market, window, random_runs)
    r5_calmar = at(COST_R5).portfolio.calmar
    threshold = float(np.percentile(random, RANDOM_PERCENTILE))
    share = float((random < r5_calmar).mean())
    checks.append(
        Check(
            f"R5 Null: Calmar above the {RANDOM_PERCENTILE}th percentile of {random_runs:,} "
            "random-crowded runs",
            r5_calmar > threshold,
            f"{r5_calmar:.2f} vs {threshold:.2f} (beats {share:.0%} of runs)",
        )
    )

    # R6 and the informational runs.
    informational: list[tuple[str, ps.Evaluation, dict[str, Metrics]]] = []
    for cost in (ps.COST_BASE, ps.COST_INFO):
        name = f"Kraken at {cost:.2%}/side"
        informational.append((name, at(cost), ps.run_benchmarks(market, cost, window)))
    binance: ps.Evaluation | None = None
    for source, name in (("binance", "Binance USDT (R6)"), ("bitvavo", "Bitvavo EUR (reported)")):
        try:
            other = load_market(source, root)
        except FileNotFoundError:
            notes.append(f"{name}: data not available, skipped")
            continue
        other_window = window_for(other)
        evaluation = evaluate(selected, daily, other, ps.COST_STRESS, other_window)
        informational.append(
            (name, evaluation, ps.run_benchmarks(other, ps.COST_STRESS, other_window))
        )
        if source == "binance":
            binance = evaluation
    binance_cagr = binance.portfolio.cagr if binance else math.nan
    checks.append(
        Check(
            "R6 Binance USDT: CAGR > 0 at 2× costs (no sign reversal)",
            binance is not None and binance_cagr > 0,
            f"{binance_cagr:.1%}" if binance else "Binance data missing",
        )
    )

    # Kill rules.
    checks.append(
        Check(
            f"H6 kill: ≥ {MIN_EPISODES} crowded episodes per asset",
            all(count >= MIN_EPISODES for count in episode_counts.values()),
            ", ".join(f"{a} {n}" for a, n in episode_counts.items()),
        )
    )
    checks.append(
        Check(f"H6 kill: not the corner ({label(CORNER)})", selected != CORNER, label(selected))
    )
    notes.append(
        f"Variants: {len(evaluations)} grid + {len(robustness)} robustness = "
        f"{len(evaluations) + len(robustness)}; running trial count "
        f"{TRIALS_BEFORE + len(evaluations) + len(robustness)} (deflated Sharpe at the holdout)."
    )
    return Gate1(
        window, evaluations, scores, selected, benchmarks, checks, robustness, base_cost,
        windows, mc_p95, random, episode_counts, informational, notes,
    )  # fmt: skip


# --- report -------------------------------------------------------------------------------------


def render(gate: Gate1) -> str:
    start, end = gate.window
    row = ps.row
    lines = [
        f"# Gate 1′ {HYPOTHESIS}: {TITLE}",
        "",
        f"Generated {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC "
        f"from code `{ps.git_revision()}`. "
        "Rules: [research/hypotheses/H6.md](../hypotheses/H6.md), "
        "[_CONVENTIONS.md](../hypotheses/_CONVENTIONS.md) (amendment 1) and PROJECT_PLAN.md "
        "amendment A3.",
        "",
        f"Primary data: Kraken 1d, development {start:%Y-%m-%d} → {end:%Y-%m-%d}; signal: Binance "
        f"USD-M funding. Judged at **{ps.COST_STRESS:.2%} per side** (2× costs). Base exposure "
        f"{BASE:.0%} of each sleeve, hysteresis {HYSTERESIS * 100:g} points, rebalance band "
        f"{REBALANCE_BAND * 100:g} points.",
        "",
        f"## Decision: {'✅ PASS (Gate 1′)' if gate.passed else '❌ KILL'}",
        "",
        "## Benchmarks (buy & hold, 2× costs)",
        "",
        row(["Series", *ps.METRIC_HEADER]),
        row(["---"] + ["---:"] * len(ps.METRIC_HEADER)),
    ]
    lines += [row([name, *ps.metric_cells(m)]) for name, m in gate.benchmarks.items()]
    lines += [
        "",
        "## Grid (2× costs)",
        "",
        "Selection score = median of the BTC/ETH-averaged Calmar of the variant and its grid "
        "neighbours (conventions §8).",
        "",
    ]
    header = ["Variant", "Score", "BTC Calmar", "ETH Calmar", *ps.METRIC_HEADER]
    lines += [row(header), row(["---"] + ["---:"] * (len(header) - 1))]
    for params, evaluation in gate.evaluations.items():
        marker = " ⬅ selected" if params == gate.selected else ""
        lines.append(
            row(
                [
                    label(params) + marker,
                    f"{gate.scores[params]:.2f}",
                    *[f"{evaluation.per_asset[a].calmar:.2f}" for a in ps.ASSETS],
                    *ps.metric_cells(evaluation.portfolio),
                ]
            )
        )
    lines += ["", f"## Pass rule and in-sample checks for {label(gate.selected)}", ""]
    lines += [row(["Criterion", "Result", "Detail"]), row(["---", "---", "---"])]
    lines += [row([c.criterion, "✅" if c.passed else "❌", c.detail]) for c in gate.checks]
    lines += [
        "",
        "## R1 robustness (1× costs)",
        "",
        row(["Variant", *ps.METRIC_HEADER]),
        row(["---"] + ["---:"] * len(ps.METRIC_HEADER)),
        row(
            [
                f"{label(gate.selected)} (selected)",
                *ps.metric_cells(gate.selected_base_cost.portfolio),
            ]
        ),
    ]
    lines += [row([label(p), *ps.metric_cells(e.portfolio)]) for p, e in gate.robustness.items()]
    lines += [
        "",
        f"## R2 half-years ({COST_R2:.2%}/side)",
        "",
        row(list(gate.windows)),
        row(["---:"] * len(gate.windows)),
        row([f"{value:+.1%}" for value in gate.windows.values()]),
        "",
        "## R4 Monte Carlo and R5 null",
        "",
        f"- R4: 95th-percentile drawdown over {MC_DAYS}-day paths ({COST_R4:.2%}/side, "
        f"{MC_BLOCK}-day blocks, seed {SEED}): **{gate.mc_p95:.1%}**. Carried into the holdout "
        "registration.",
        f"- R5: random-crowded Calmars ({COST_R5:.2%}/side): median "
        f"{float(np.median(gate.random)):.2f}, 5th percentile "
        f"{float(np.percentile(gate.random, 5)):.2f}, 95th percentile "
        f"{float(np.percentile(gate.random, 95)):.2f}.",
        "- Crowded episodes in the window: "
        + ", ".join(f"{a} {n}" for a, n in gate.episode_counts.items())
        + ".",
        "",
        "## Informational (R3 and other runs; only R6 is a criterion)",
        "",
        row(["Run", "Series", *ps.METRIC_HEADER]),
        row(["---", "---"] + ["---:"] * len(ps.METRIC_HEADER)),
    ]
    for name, evaluation, bench in gate.informational:
        lines.append(row([name, "H6", *ps.metric_cells(evaluation.portfolio)]))
        lines.append(row([name, "50/50 buy & hold", *ps.metric_cells(bench["50/50"])]))
    if gate.notes:
        lines += ["", *[f"- {note}" for note in gate.notes]]
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aitradingbot.analysis.h6")
    parser.add_argument("--root", type=Path, default=None, help="data directory (default: ./data)")
    parser.add_argument("--out", type=Path, default=None, help="also write the report here")
    args = parser.parse_args(argv)
    gate = gate1(args.root)
    text = render(gate)
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8", newline="\n")
    return 0 if gate.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

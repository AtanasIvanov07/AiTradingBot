"""Gate 1 pre-screen for the registered hypotheses, as code (research/hypotheses/_CONVENTIONS.md).

Usage:
    python -m aitradingbot.analysis.prescreen H1 --out research/reports/prescreen-H1.md

Everything here mirrors a registered rule: the grids (cards H1–H3), costs (§4), benchmarks (§5),
metrics (§6), the pass rule (§7), the plateau-median selection (§8) and each card's kill criteria.
Changing any of it requires a dated amendment in the conventions file first.
Only the development split (2018–2022) is used. Validation and holdout data are never loaded here.
"""

from __future__ import annotations

import argparse
import math
import statistics
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from aitradingbot.analysis.engine import BacktestResult, run_backtest
from aitradingbot.analysis.metrics import Metrics, summarize
from aitradingbot.analysis.strategies import (
    h1_trend_filter,
    h2_dual_momentum,
    h3_vol_target,
)
from aitradingbot.ingest.common import TIMEFRAMES, Dataset
from aitradingbot.splits import DEVELOPMENT

COST_BASE = 0.003
COST_STRESS = 0.006  # the pre-screen is judged at 2× costs
COST_INFO = 0.009
ASSETS = ("BTC", "ETH")
QUOTES = {"kraken": "EUR", "bitvavo": "EUR", "binance": "USDT"}
PRIMARY = "kraken"
VARIANT_CAP = 20

TITLES = {
    "H1": "Daily trend following (SMA filter with band)",
    "H2": "Weekly dual-momentum rotation BTC / ETH / EUR",
    "H3": "Volatility-targeted holding",
}
GRIDS: dict[str, dict[str, list[float]]] = {
    "H1": {"n": [50, 75, 100, 125, 150, 200], "band": [0.0, 0.02, 0.04]},
    "H2": {"lookback": [30, 60, 90, 120, 180], "buffer": [0.0, 0.05, 0.10]},
    "H3": {"target_vol": [0.30, 0.40, 0.50, 0.60], "lookback": [20, 30, 60]},
}
SLEEVE_HYPOTHESES = {"H1", "H3"}  # 50% of capital per asset, run independently
H3_REBALANCE_BAND = 0.10
WEDNESDAY = 2

Params = tuple[tuple[str, float], ...]


def param(params: Params, name: str) -> float:
    return dict(params)[name]


def label(params: Params) -> str:
    parts = []
    for name, value in params:
        is_fraction = name in {"band", "buffer", "target_vol"}
        parts.append(f"{name}={value:.0%}" if is_fraction else f"{name}={value:g}")
    return ", ".join(parts)


def grid_variants(hypothesis: str) -> list[Params]:
    grid = GRIDS[hypothesis]
    names = list(grid)
    variants: list[Params] = [()]
    for name in names:
        variants = [(*v, (name, value)) for v in variants for value in grid[name]]
    if len(variants) > VARIANT_CAP:
        raise AssertionError(f"{hypothesis} grid exceeds the registered cap of {VARIANT_CAP}")
    return variants


def neighbours(hypothesis: str, params: Params) -> list[Params]:
    """Immediate grid neighbours: one step up or down in exactly one parameter."""
    grid = GRIDS[hypothesis]
    found = []
    for position, (name, value) in enumerate(params):
        values = grid[name]
        i = values.index(value)
        for j in (i - 1, i + 1):
            if 0 <= j < len(values):
                swapped = list(params)
                swapped[position] = (name, values[j])
                found.append(tuple(swapped))
    return found


# --- data ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Market:
    source: str
    timeframe: str
    opens: pd.DataFrame  # regular calendar, NaN where a candle is missing
    closes: pd.DataFrame
    raw_closes: dict[str, pd.Series]  # candles that actually exist
    step: pd.Timedelta

    @property
    def candles_per_day(self) -> int:
        return int(pd.Timedelta(days=1) / self.step)

    @property
    def periods_per_year(self) -> float:
        return float(pd.Timedelta(days=365) / self.step)

    def first_common(self) -> pd.Timestamp:
        return pd.Timestamp(max(series.index.min() for series in self.raw_closes.values()))


def load_market(source: str, timeframe: str, root: Path | None = None) -> Market:
    step = TIMEFRAMES[timeframe]
    frames = {
        asset: Dataset(source, f"{asset}/{QUOTES[source]}", timeframe)
        .load(root)
        .set_index("open_time")
        for asset in ASSETS
    }
    first = min(frame.index.min() for frame in frames.values())
    last = max(frame.index.max() for frame in frames.values())
    calendar = pd.date_range(first, last, freq=step)
    opens = pd.DataFrame({a: f["open"].reindex(calendar) for a, f in frames.items()})
    closes = pd.DataFrame({a: f["close"].reindex(calendar) for a, f in frames.items()})
    raw = {a: f["close"] for a, f in frames.items()}
    return Market(source, timeframe, opens, closes, raw, step)


def development_window(
    market: Market, warmup_candles: int = 0
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """First and last candle open times evaluated: the development split, shortened at the
    start if the series (plus indicator warm-up) begins later, as Bitvavo's does."""
    start = DEVELOPMENT[0]
    warmed = market.first_common() + (warmup_candles + 1) * market.step
    if warmed > start:
        start = warmed.ceil("D")
    end = DEVELOPMENT[1] + pd.Timedelta(days=1) - market.step
    return start, end


# --- running variants ---------------------------------------------------------------------------


@dataclass
class Evaluation:
    params: Params
    cost: float
    portfolio: Metrics
    per_asset: dict[str, Metrics] = field(default_factory=dict)
    result: BacktestResult | None = None

    def selection_base(self) -> float:
        """Calmar used for selection: BTC and ETH averaged for sleeve strategies (§8)."""
        if self.per_asset:
            return statistics.fmean(m.calmar for m in self.per_asset.values())
        return self.portfolio.calmar


def warmup(hypothesis: str, params: Params, market: Market) -> int:
    key = "n" if hypothesis == "H1" else "lookback"
    scale = market.candles_per_day if hypothesis in SLEEVE_HYPOTHESES else 1
    return int(param(params, key)) * scale


def sleeve_targets(hypothesis: str, params: Params, market: Market, asset: str) -> pd.Series:
    raw = market.raw_closes[asset]
    scale = market.candles_per_day  # lookbacks are registered in days; 4h runs scale them ×6
    if hypothesis == "H1":
        signal = h1_trend_filter(raw, int(param(params, "n")) * scale, param(params, "band"))
    else:
        signal = h3_vol_target(
            raw,
            param(params, "target_vol"),
            int(param(params, "lookback")) * scale,
            market.periods_per_year,
        )
    return signal.reindex(market.closes.index).ffill().fillna(0.0)


def combine_sleeves(sleeves: dict[str, BacktestResult]) -> BacktestResult:
    results = list(sleeves.values())
    equity = sum((r.equity for r in results[1:]), results[0].equity)
    exposure = pd.DataFrame(
        {a: r.exposure[a] * r.equity / equity for a, r in sleeves.items()}, index=equity.index
    )
    trades = pd.concat([r.trades for r in results], ignore_index=True)
    return BacktestResult(
        equity, exposure, trades, sum(r.initial for r in results), results[0].step
    )


def run_variant(
    hypothesis: str,
    params: Params,
    market: Market,
    cost: float,
    window: tuple[pd.Timestamp, pd.Timestamp],
    weekday: int = 6,
) -> Evaluation:
    start, end = window
    if hypothesis in SLEEVE_HYPOTHESES:
        band = H3_REBALANCE_BAND if hypothesis == "H3" else 0.0
        sleeves = {}
        for asset in ASSETS:
            targets = sleeve_targets(hypothesis, params, market, asset).to_frame(asset)
            sleeves[asset] = run_backtest(
                market.opens[[asset]], market.closes[[asset]], targets, cost,
                start, end, market.step, rebalance_band=band, initial=0.5,
            )  # fmt: skip
        portfolio = combine_sleeves(sleeves)
        per_asset = {a: summarize(r) for a, r in sleeves.items()}
        return Evaluation(params, cost, summarize(portfolio), per_asset, portfolio)
    weights = h2_dual_momentum(
        market.closes, int(param(params, "lookback")), param(params, "buffer"), weekday
    )
    result = run_backtest(market.opens, market.closes, weights, cost, start, end, market.step)
    return Evaluation(params, cost, summarize(result), {}, result)


def run_benchmarks(
    market: Market, cost: float, window: tuple[pd.Timestamp, pd.Timestamp]
) -> dict[str, Metrics]:
    """Buy & hold per asset and the un-rebalanced 50/50 portfolio (§5)."""
    start, end = window
    sleeves = {}
    for asset in ASSETS:
        hold = pd.DataFrame({asset: 1.0}, index=market.closes.index)
        sleeves[asset] = run_backtest(
            market.opens[[asset]], market.closes[[asset]], hold, cost,
            start, end, market.step, initial=0.5,
        )  # fmt: skip
    benchmarks = {a: summarize(r) for a, r in sleeves.items()}
    benchmarks["50/50"] = summarize(combine_sleeves(sleeves))
    return benchmarks


# --- selection and pass rule --------------------------------------------------------------------


def selection_scores(hypothesis: str, evaluations: dict[Params, Evaluation]) -> dict[Params, float]:
    """§8: median of a variant's own selection Calmar and its immediate neighbours'."""
    scores = {}
    for params, evaluation in evaluations.items():
        values = [evaluation.selection_base()]
        values += [evaluations[n].selection_base() for n in neighbours(hypothesis, params)]
        scores[params] = statistics.median(values)
    return scores


def select(hypothesis: str, evaluations: dict[Params, Evaluation]) -> Params:
    scores = selection_scores(hypothesis, evaluations)
    return max(scores, key=lambda p: (scores[p], -evaluations[p].portfolio.trades))


@dataclass(frozen=True)
class Check:
    criterion: str
    passed: bool
    detail: str


def core_checks(
    hypothesis: str, metrics: Metrics, benchmark: Metrics, scope: str, numbers: str = "1–4"
) -> list[Check]:
    """Criteria 1–4 of §7 for one series vs its benchmark (H3 uses its card's drawdown rule)."""
    checks = [
        Check(
            f"1 Calmar ≥ 1.2× benchmark ({scope})",
            metrics.calmar >= 1.2 * benchmark.calmar,
            f"{metrics.calmar:.2f} vs 1.2 × {benchmark.calmar:.2f} = {1.2 * benchmark.calmar:.2f}",
        )
    ]
    drawdown, bench_drawdown = abs(metrics.max_drawdown), abs(benchmark.max_drawdown)
    if hypothesis == "H3":
        checks.append(
            Check(
                f"2 Max drawdown ≥ 25% smaller than benchmark's ({scope})",
                drawdown <= 0.75 * bench_drawdown,
                f"{drawdown:.1%} vs limit {0.75 * bench_drawdown:.1%}",
            )
        )
    else:
        checks.append(Check(f"2 Max drawdown ≤ 40% ({scope})", drawdown <= 0.40, f"{drawdown:.1%}"))
    checks.append(Check(f"3 CAGR > 0 ({scope})", metrics.cagr > 0, f"{metrics.cagr:.1%}"))
    checks.append(
        Check(
            f"4 Sharpe ≥ benchmark ({scope})",
            metrics.sharpe >= benchmark.sharpe,
            f"{metrics.sharpe:.2f} vs {benchmark.sharpe:.2f}",
        )
    )
    return checks if numbers == "1–4" else checks[:3]


def series_checks(
    hypothesis: str, evaluation: Evaluation, benchmarks: dict[str, Metrics], numbers: str = "1–4"
) -> list[Check]:
    checks = core_checks(
        hypothesis, evaluation.portfolio, benchmarks["50/50"], "portfolio", numbers
    )
    for asset, metrics in evaluation.per_asset.items():  # criterion 5: each asset on its own
        checks += core_checks(hypothesis, metrics, benchmarks[asset], asset, numbers)
    return checks


def holding_concentration(result: BacktestResult) -> float:
    """H2 kill rule: share of total profit earned in the single best continuous holding period."""
    held = result.exposure.idxmax(axis=1).where(result.exposure.max(axis=1) > 0, "cash")
    segment = (held != held.shift()).cumsum()
    equity = result.equity
    starts = equity.shift(1).fillna(result.initial)
    profits = (equity - starts).groupby(segment).sum()
    profits = profits[held.groupby(segment).first() != "cash"]
    total = float(equity.iloc[-1] - result.initial)
    if total <= 0 or profits.empty:
        return math.nan
    return float(profits.max() / total)


def pass_rule(
    hypothesis: str,
    evaluations: dict[Params, Evaluation],
    selected: Params,
    benchmarks: dict[str, Metrics],
    extra: list[Check],
) -> list[Check]:
    chosen = evaluations[selected]
    checks = series_checks(hypothesis, chosen, benchmarks)
    base = chosen.selection_base()
    for neighbour in neighbours(hypothesis, selected):
        other = evaluations[neighbour]
        failed = [
            c.criterion for c in series_checks(hypothesis, other, benchmarks, "1–3") if not c.passed
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
    return checks + extra


# --- orchestration ------------------------------------------------------------------------------


@dataclass
class Prescreen:
    hypothesis: str
    market: Market
    window: tuple[pd.Timestamp, pd.Timestamp]
    evaluations: dict[Params, Evaluation]
    scores: dict[Params, float]
    selected: Params
    benchmarks: dict[str, Metrics]
    checks: list[Check]
    informational: list[tuple[str, Evaluation, dict[str, Metrics]]]
    notes: list[str]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def run_grid(
    hypothesis: str, market: Market, cost: float, window: tuple[pd.Timestamp, pd.Timestamp]
) -> dict[Params, Evaluation]:
    return {p: run_variant(hypothesis, p, market, cost, window) for p in grid_variants(hypothesis)}


def try_market(source: str, timeframe: str, root: Path | None) -> Market | None:
    try:
        return load_market(source, timeframe, root)
    except FileNotFoundError:
        return None


def prescreen(hypothesis: str, root: Path | None = None) -> Prescreen:
    market = load_market(PRIMARY, "1d", root)
    window = development_window(market)
    evaluations = run_grid(hypothesis, market, COST_STRESS, window)
    scores = selection_scores(hypothesis, evaluations)
    selected = select(hypothesis, evaluations)
    benchmarks = run_benchmarks(market, COST_STRESS, window)
    chosen = evaluations[selected]
    extra: list[Check] = []
    informational: list[tuple[str, Evaluation, dict[str, Metrics]]] = []
    notes: list[str] = []

    def confirm(
        name: str, other: Market | None, run: Callable[[Market], Evaluation]
    ) -> Evaluation | None:
        if other is None:
            notes.append(f"{name}: data not available, skipped")
            return None
        other_window = development_window(other, warmup(hypothesis, selected, other))
        evaluation = run(other)
        informational.append((name, evaluation, run_benchmarks(other, COST_STRESS, other_window)))
        if other_window[0] > window[0]:
            notes.append(f"{name}: evaluated from {other_window[0]:%Y-%m-%d} (data starts later)")
        return evaluation

    for cost in (COST_BASE, COST_INFO):
        informational.append(
            (
                f"Primary at {cost:.2%}/side",
                run_variant(hypothesis, selected, market, cost, window),
                run_benchmarks(market, cost, window),
            )
        )

    def selected_on(other: Market, weekday: int = 6) -> Evaluation:
        other_window = development_window(other, warmup(hypothesis, selected, other))
        return run_variant(hypothesis, selected, other, COST_STRESS, other_window, weekday)

    binance = confirm(
        "Binance USDT (confirmation 1)", try_market("binance", "1d", root), selected_on
    )
    confirm("Bitvavo EUR (confirmation 2)", try_market("bitvavo", "1d", root), selected_on)
    if hypothesis in SLEEVE_HYPOTHESES:
        confirm("Kraken 4h (robustness)", try_market(PRIMARY, "4h", root), selected_on)
    else:
        informational.append(
            (
                "Wednesday rebalance (robustness)",
                run_variant(hypothesis, selected, market, COST_STRESS, window, WEDNESDAY),
                benchmarks,
            )
        )

    if hypothesis == "H1":
        corner = selected == (("n", 50), ("band", 0.0))
        extra.append(
            Check("H1 kill: not the fastest corner (n=50, band=0%)", not corner, label(selected))
        )
        binance_cagr = binance.portfolio.cagr if binance else math.nan
        extra.append(
            Check(
                "H1 kill: CAGR > 0 at 2× costs on Binance USDT too",
                binance is not None and binance_cagr > 0,
                f"{binance_cagr:.1%}" if binance else "Binance data missing",
            )
        )
    elif hypothesis == "H2":
        h1 = run_grid("H1", market, COST_STRESS, window)
        h1_selected = h1[select("H1", h1)]
        extra.append(
            Check(
                "5′ Calmar beats H1's selected variant",
                chosen.portfolio.calmar > h1_selected.portfolio.calmar,
                f"{chosen.portfolio.calmar:.2f} vs H1 ({label(h1_selected.params)}) "
                f"{h1_selected.portfolio.calmar:.2f}",
            )
        )
        share = holding_concentration(chosen.result) if chosen.result else math.nan
        extra.append(
            Check(
                "H2 kill: ≤ 60% of profit from one holding period",
                not math.isnan(share) and share <= 0.60,
                "no profit" if math.isnan(share) else f"{share:.0%}",
            )
        )
    else:
        turnover = chosen.portfolio.turnover_per_year
        extra.append(Check("H3 kill: turnover ≤ 400% per year", turnover <= 4.0, f"{turnover:.0%}"))

    checks = pass_rule(hypothesis, evaluations, selected, benchmarks, extra)
    return Prescreen(
        hypothesis, market, window, evaluations, scores, selected, benchmarks,
        checks, informational, notes,
    )  # fmt: skip


# --- report -------------------------------------------------------------------------------------


def row(cells: Sequence[object]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def metric_cells(m: Metrics) -> list[str]:
    return [
        f"{m.cagr:.1%}", f"{m.max_drawdown:.1%}", f"{m.sharpe:.2f}", f"{m.calmar:.2f}",
        f"{m.worst_year:.1%}", str(m.round_trips), f"{m.time_in_market:.0%}",
        f"{m.turnover_per_year:.1f}×",
    ]  # fmt: skip


METRIC_HEADER = [
    "CAGR",
    "Max DD",
    "Sharpe",
    "Calmar",
    "Worst year",
    "Round trips",
    "In market",
    "Turnover/yr",
]


def git_revision() -> str:
    try:
        output = subprocess.run(
            ["git", "describe", "--always", "--dirty"], capture_output=True, text=True, check=True
        )
        return output.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def render(screen: Prescreen) -> str:
    h = screen.hypothesis
    start, end = screen.window
    lines = [
        f"# Pre-screen {h}: {TITLES[h]}",
        "",
        f"Generated {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC from code `{git_revision()}`. "
        f"Rules: [research/hypotheses/{h}.md](../hypotheses/{h}.md) and "
        "[_CONVENTIONS.md](../hypotheses/_CONVENTIONS.md).",
        "",
        f"Primary data: {screen.market.source} {screen.market.timeframe}, development split "
        f"{start:%Y-%m-%d} → {end:%Y-%m-%d}. Judged at **{COST_STRESS:.2%} per side** (2× costs). "
        f"Variants tested: **{len(screen.evaluations)}** (cap {VARIANT_CAP}).",
        "",
        f"## Decision: {'✅ PASS (Gate 1)' if screen.passed else '❌ KILL'}",
        "",
        "## Benchmarks (buy & hold, 2× costs)",
        "",
        row(["Series", *METRIC_HEADER]),
        row(["---"] + ["---:"] * len(METRIC_HEADER)),
    ]
    lines += [row([name, *metric_cells(m)]) for name, m in screen.benchmarks.items()]
    lines += [
        "",
        "## Grid (2× costs)",
        "",
        "Selection score = median Calmar of the variant and its grid neighbours "
        "(BTC/ETH-averaged for sleeve strategies).",
        "",
    ]
    asset_cols = [f"{a} Calmar" for a in ASSETS] if h in SLEEVE_HYPOTHESES else []
    header = ["Variant", "Score", *asset_cols, *METRIC_HEADER]
    lines += [row(header), row(["---"] + ["---:"] * (len(header) - 1))]
    for params, evaluation in screen.evaluations.items():
        marker = " ⬅ selected" if params == screen.selected else ""
        assets = [f"{evaluation.per_asset[a].calmar:.2f}" for a in ASSETS] if asset_cols else []
        lines.append(
            row(
                [
                    label(params) + marker,
                    f"{screen.scores[params]:.2f}",
                    *assets,
                    *metric_cells(evaluation.portfolio),
                ]
            )
        )
    lines += ["", f"## Pass rule for {label(screen.selected)}", ""]
    lines += [row(["Criterion", "Result", "Detail"]), row(["---", "---", "---"])]
    lines += [row([c.criterion, "✅" if c.passed else "❌", c.detail]) for c in screen.checks]
    lines += [
        "",
        "## Informational (not part of the decision unless a kill rule above uses it)",
        "",
        row(["Run", "Series", *METRIC_HEADER]),
        row(["---", "---"] + ["---:"] * len(METRIC_HEADER)),
    ]
    for name, evaluation, bench in screen.informational:
        lines.append(row([name, "strategy", *metric_cells(evaluation.portfolio)]))
        lines.append(row([name, "50/50 buy & hold", *metric_cells(bench["50/50"])]))
    if screen.notes:
        lines += ["", *[f"- {note}" for note in screen.notes]]
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aitradingbot.analysis.prescreen")
    parser.add_argument("hypothesis", choices=sorted(GRIDS))
    parser.add_argument("--root", type=Path, default=None, help="data directory (default: ./data)")
    parser.add_argument("--out", type=Path, default=None, help="also write the report here")
    args = parser.parse_args(argv)
    screen = prescreen(args.hypothesis, args.root)
    text = render(screen)
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8", newline="\n")
    return 0 if screen.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

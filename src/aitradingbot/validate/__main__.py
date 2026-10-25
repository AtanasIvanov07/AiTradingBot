"""Command line: python -m aitradingbot.validate [--out research/reports/data-validation.md]

Validates every clean series under data/clean/, cross-checks pairs available from more than one
source, checks the funding-rate series (H6 signal), prints a Markdown report and exits with
status 1 if any series has errors.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

from aitradingbot.ingest import funding
from aitradingbot.ingest.common import Dataset, list_clean_datasets
from aitradingbot.splits import RESEARCH_END, RESEARCH_START, WARMUP_START
from aitradingbot.validate.checks import (
    DEFAULT_MAX_MISSING_FRACTION,
    FundingReport,
    Report,
    assess_from,
    cross_source,
    validate,
    validate_funding,
)

MAX_LISTED = 5
SUMMARY_HEADER = [
    "Source", "Pair", "TF", "Rows", "First", "Last", "Research coverage",
    "Missing", "Gaps", "Outliers", "Zero vol", "Status",
]  # fmt: skip
CROSS_HEADER = [
    "Pair", "TF", "Sources", "Common candles", "Median diff", "p99 diff", "Max diff",
    "Share > tolerance",
]  # fmt: skip
FUNDING_HEADER = [
    "Symbol", "Settlements", "First", "Last", "Coverage", "Missing", "Extreme", "Max |rate|",
    "Status",
]  # fmt: skip
FUNDING_START = pd.Timestamp(f"{funding.ARCHIVE_START}-01", tz="UTC")


def table_row(cells: list[object]) -> str:
    return "| " + " | ".join(str(cell) for cell in cells) + " |"


def table_head(header: list[str], numeric_from: int) -> list[str]:
    """Header plus separator; columns from index ``numeric_from`` on are right-aligned."""
    align = ["---" if i < numeric_from else "---:" for i in range(len(header))]
    return [table_row(list(header)), table_row(list(align))]


def fmt_time(value: pd.Timestamp | None, timeframe: str) -> str:
    if value is None:
        return "—"
    return f"{value:%Y-%m-%d}" if timeframe == "1d" else f"{value:%Y-%m-%d %H:%M}"


def status_label(report: Report | FundingReport) -> str:
    if not report.ok:
        return "❌ error"
    return "⚠️ warn" if report.warnings else "✅ ok"


def coverage_label(report: Report) -> str:
    if report.covers(RESEARCH_START, RESEARCH_END):
        return "full"
    return f"from {fmt_time(report.first, '1d')} to {fmt_time(report.last, '1d')}"


def build_report(
    root: Path | None, max_missing_fraction: float, tolerance: float
) -> tuple[str, bool]:
    datasets = list_clean_datasets(root)
    lines = [
        "# Data validation report",
        "",
        f"Generated {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC. "
        f"Research period: {RESEARCH_START:%Y-%m-%d} → {RESEARCH_END:%Y-%m-%d}. "
        f"Gaps, outliers and zero-volume candles are assessed from {WARMUP_START:%Y-%m-%d} "
        f"(warm-up start), Bitvavo's from {assess_from('bitvavo'):%Y-%m-%d}; a series errors if "
        f"more than {max_missing_fraction:.1%} of candles are missing. Timestamps are candle open "
        "times, UTC.",
        "",
    ]
    if not datasets:
        lines.append("No clean datasets found. Run `python -m aitradingbot.ingest all` first.")
        return "\n".join(lines) + "\n", False

    frames: dict[Dataset, pd.DataFrame] = {}
    reports: dict[Dataset, Report] = {}
    for dataset in datasets:
        frames[dataset] = dataset.load(root)
        reports[dataset] = validate(
            frames[dataset],
            dataset.timeframe,
            max_missing_fraction,
            assess_from=assess_from(dataset.source),
        )

    lines += ["## Summary", "", *table_head(SUMMARY_HEADER, numeric_from=3)]
    for dataset, report in reports.items():
        tf = dataset.timeframe
        lines.append(
            table_row(
                [
                    dataset.source,
                    dataset.pair,
                    tf,
                    f"{report.rows:,}",
                    fmt_time(report.first, tf),
                    fmt_time(report.last, tf),
                    coverage_label(report),
                    f"{report.missing_candles:,} ({report.missing_fraction:.3%})",
                    len(report.gaps),
                    len(report.outliers),
                    report.zero_volume,
                    status_label(report),
                ]
            )
        )

    lines += ["", "## Findings", ""]
    for dataset, report in reports.items():
        if not report.findings:
            continue
        lines.append(f"**{dataset.source} {dataset.pair} {dataset.timeframe}**")
        lines += [f"- {f.severity}: {f.message}" for f in report.findings]
        largest = sorted(report.gaps, key=lambda gap: gap.missing, reverse=True)[:MAX_LISTED]
        if largest:
            spans = ", ".join(
                f"{fmt_time(g.first_missing, dataset.timeframe)} (+{g.missing})" for g in largest
            )
            lines.append(f"- largest gaps: {spans}")
        if not report.outliers.empty:
            top = report.outliers.nlargest(MAX_LISTED, "close_move").to_dict("records")
            moves = ", ".join(
                f"{fmt_time(row['open_time'], dataset.timeframe)} "
                f"({row['close_move']:+.1%} close, {row['max_wick']:.1%} wick)"
                for row in top
            )
            lines.append(f"- biggest flagged moves: {moves}")
        lines.append("")

    lines += [
        "## Cross-source checks",
        "",
        f"Closes of the same pair and timeframe from different sources "
        f"(tolerance {tolerance:.1%}).",
        "",
        *table_head(CROSS_HEADER, numeric_from=3),
    ]
    groups: dict[tuple[str, str], list[Dataset]] = defaultdict(list)
    for dataset in datasets:
        groups[(dataset.pair, dataset.timeframe)].append(dataset)
    disagreements: list[str] = []
    compared = 0
    for (pair, timeframe), members in sorted(groups.items()):
        for i, first in enumerate(members):
            for second in members[i + 1 :]:
                check = cross_source(frames[first], frames[second], tolerance)
                compared += 1
                worst = ", ".join(
                    f"{fmt_time(row['open_time'], timeframe)} "
                    f"({row['close_a']:g} vs {row['close_b']:g}, {row['rel_diff']:.1%})"
                    for row in check.worst.head(3).to_dict("records")
                )
                disagreements.append(
                    f"- {pair} {timeframe} ({first.source} vs {second.source}): {worst}"
                )
                lines.append(
                    table_row(
                        [
                            pair,
                            timeframe,
                            f"{first.source} vs {second.source}",
                            f"{check.common:,}",
                            f"{check.median_diff:.3%}",
                            f"{check.p99_diff:.3%}",
                            f"{check.max_diff:.2%}",
                            f"{check.share_over_tolerance:.2%}",
                        ]
                    )
                )
    if not compared:
        lines.append(table_row(["—", "—", "no pair available from two sources", *[""] * 5]))
    if disagreements:
        lines += ["", "Largest disagreements (worth a look; often one venue dislocating):", ""]
        lines += disagreements

    funding_reports = {
        symbol: validate_funding(funding.load(symbol, root), max_missing_fraction)
        for symbol in funding.list_symbols(root)
    }
    lines += funding_section(funding_reports)

    all_ok = all(r.ok for r in reports.values()) and all(r.ok for r in funding_reports.values())
    lines += ["", f"**Overall: {'no errors' if all_ok else 'ERRORS FOUND'}**", ""]
    return "\n".join(lines), all_ok


def funding_section(reports: dict[str, FundingReport]) -> list[str]:
    lines = [
        "",
        "## Funding rates (H6 signal)",
        "",
        f"Binance USD-M perpetual settlements. Coverage is checked from {FUNDING_START:%Y-%m-%d} "
        f"(archive start) to {RESEARCH_END:%Y-%m-%d}. Rates are per settlement.",
        "",
    ]
    if not reports:
        lines.append("No funding series found. Run `python -m aitradingbot.ingest funding`.")
        return lines
    lines += table_head(FUNDING_HEADER, numeric_from=1)
    for symbol, report in reports.items():
        covered = report.covers(FUNDING_START, RESEARCH_END)
        lines.append(
            table_row(
                [
                    symbol,
                    f"{report.rows:,}",
                    fmt_time(report.first, "1h"),
                    fmt_time(report.last, "1h"),
                    "full" if covered else "partial",
                    f"{report.missing:,} ({report.missing_fraction:.3%})",
                    report.extreme,
                    f"{report.max_abs_rate:.4%}",
                    status_label(report),
                ]
            )
        )
    for symbol, report in reports.items():
        if report.findings:
            lines += ["", f"**{symbol}**"]
            lines += [f"- {f.severity}: {f.message}" for f in report.findings]
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aitradingbot.validate", description=__doc__)
    parser.add_argument("--root", type=Path, default=None, help="data directory (default: ./data)")
    parser.add_argument("--out", type=Path, default=None, help="also write the report to this file")
    parser.add_argument("--max-missing", type=float, default=DEFAULT_MAX_MISSING_FRACTION)
    parser.add_argument("--tolerance", type=float, default=0.005)
    args = parser.parse_args(argv)
    text, ok = build_report(args.root, args.max_missing, args.tolerance)
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8", newline="\n")  # LF even on Windows
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

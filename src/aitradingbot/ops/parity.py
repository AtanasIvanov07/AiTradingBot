"""Weekly signal-parity check: the dry-run bot's orders vs a backtest replay of the same days.

Usage (from the repo root, with the bot running or stopped):
    python -m aitradingbot.ops.parity                 # since the bot's first order
    python -m aitradingbot.ops.parity --since 2026-10-20

PROJECT_PLAN.md Phase 3: "replay the same period in backtesting and compare trades with dry-run",
Gate 3 asks for 100% parity or every difference explained. This downloads fresh Bitvavo daily
candles, backtests H5TrendVol over the dry-run days at the dry-run fee, and matches orders by day,
pair and side. Freqtrade can't trade on a backtest's first candle, and the dry-run bot trades as
soon as it starts, so orders on the start day are reported but not counted against parity.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd

STRATEGY = "H5TrendVol"
DRY_RUN_FEE = 0.0025  # Bitvavo taker fee used by the dry-run bot
STARTUP_DAYS = 420  # the strategy's 400 startup candles, plus margin
SIZE_TOLERANCE = 0.05  # relative difference in order value still counted as a match
COLUMNS = ["day", "pair", "side", "value"]


def dryrun_orders(db: Path) -> pd.DataFrame:
    """Filled orders from Freqtrade's dry-run SQLite database."""
    query = """
        SELECT ft_pair AS pair, ft_order_side AS side, filled, average, price, order_filled_date
        FROM orders WHERE ft_is_open = 0 AND filled > 0
    """
    with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as connection:
        rows = pd.read_sql_query(query, connection)
    if rows.empty:
        return pd.DataFrame(columns=COLUMNS)
    price = rows["average"].fillna(rows["price"])
    return pd.DataFrame(
        {
            "day": pd.to_datetime(rows["order_filled_date"]).dt.date,
            "pair": rows["pair"],
            "side": rows["side"],
            "value": rows["filled"] * price,
        }
    )


def backtest_orders(result_zip: Path) -> pd.DataFrame:
    """Filled orders from a Freqtrade backtest export (the .zip next to .last_result.json)."""
    with zipfile.ZipFile(result_zip) as archive:
        name = next(
            n for n in archive.namelist()
            if n.endswith(".json") and "_config" not in n and "_market" not in n
        )  # fmt: skip
        data = json.loads(archive.read(name))
    rows = []
    for trade in data["strategy"][STRATEGY]["trades"]:
        orders = trade["orders"]
        if trade.get("exit_reason") == "force_exit":
            orders = orders[:-1]  # the backtest closing everything on its last candle, not a signal
        for order in orders:
            filled = datetime.fromtimestamp(order["order_filled_timestamp"] / 1000, UTC)
            side = "buy" if order["ft_is_entry"] else "sell"
            rows.append((filled.date(), trade["pair"], side, float(order["cost"])))
    return pd.DataFrame(rows, columns=COLUMNS)


@dataclass(frozen=True)
class Parity:
    matched: int
    start_day: int  # dry-run orders on the bot's first day (not counted)
    only_dryrun: list[tuple[date, str, str, float]]
    only_backtest: list[tuple[date, str, str, float]]
    size_mismatch: list[tuple[date, str, str, float, float]]

    @property
    def ok(self) -> bool:
        return not (self.only_dryrun or self.only_backtest or self.size_mismatch)


def compare(dryrun: pd.DataFrame, backtest: pd.DataFrame, start: date, end: date) -> Parity:
    """Match orders by (day, pair, side); flag order values that differ by more than 5%."""
    live = dryrun[(dryrun["day"] > start) & (dryrun["day"] <= end)]
    replay = backtest[(backtest["day"] > start) & (backtest["day"] <= end)]
    key = ["day", "pair", "side"]
    live_sum = live.groupby(key)["value"].sum()
    replay_sum = replay.groupby(key)["value"].sum()
    common = live_sum.index.intersection(replay_sum.index)
    mismatch = [
        (*k, float(live_sum[k]), float(replay_sum[k]))
        for k in common
        if abs(live_sum[k] / replay_sum[k] - 1) > SIZE_TOLERANCE
    ]
    return Parity(
        matched=len(common) - len(mismatch),
        start_day=int((dryrun["day"] == start).sum()),
        only_dryrun=[(*k, float(live_sum[k])) for k in live_sum.index.difference(common)],
        only_backtest=[(*k, float(replay_sum[k])) for k in replay_sum.index.difference(common)],
        size_mismatch=mismatch,
    )


def render(parity: Parity, start: date, end: date) -> str:
    lines = [
        f"# Signal parity {start} → {end}: {'OK' if parity.ok else 'DIFFERENCES'}",
        "",
        f"- Matched orders (day, pair, side, value within {SIZE_TOLERANCE:.0%}): {parity.matched}",
        f"- Start-day orders (not counted; a backtest can't trade its first candle): "
        f"{parity.start_day}",
    ]
    for title, rows in (
        ("Only in the dry-run", parity.only_dryrun),
        ("Only in the backtest replay", parity.only_backtest),
        ("Same order, different size (dry-run vs replay)", parity.size_mismatch),
    ):
        if rows:
            lines += ["", f"## {title}", ""]
            lines += [f"- {' · '.join(str(c) for c in row)}" for row in rows]
    if not parity.ok:
        lines += ["", "Explain or fix every difference (Gate 3). Restart the 8-week clock if a fix "
                  "touches signal or order logic."]  # fmt: skip
    return "\n".join(lines) + "\n"


def freqtrade(*args: str) -> None:
    exe = Path(sys.executable).with_name(
        "freqtrade.exe" if sys.platform == "win32" else "freqtrade"
    )
    subprocess.run(
        [str(exe), *args], check=True, capture_output=True, encoding="utf-8", errors="replace"
    )


def replay(start: date, end: date, workdir: Path) -> Path:
    """Download Bitvavo 1d candles and backtest the strategy over [start, end]."""
    data = workdir / "data"
    results = workdir / "results"
    results.mkdir(parents=True, exist_ok=True)
    first = start - timedelta(days=STARTUP_DAYS)
    common = ["--config", "user_data/config.json", "--userdir", "user_data", "--datadir", str(data)]
    freqtrade(
        "download-data", *common, "--timeframes", "1d",
        "--timerange", f"{first:%Y%m%d}-{end + timedelta(days=1):%Y%m%d}",
    )  # fmt: skip
    freqtrade(
        "backtesting", *common, "--strategy", STRATEGY, "--timeframe", "1d",
        "--timerange", f"{start:%Y%m%d}-{end + timedelta(days=1):%Y%m%d}",
        "--fee", str(DRY_RUN_FEE), "--export", "trades", "--backtest-directory", str(results),
    )  # fmt: skip
    latest = str(json.loads((results / ".last_result.json").read_text())["latest_backtest"])
    return results / latest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aitradingbot.ops.parity")
    parser.add_argument("--db", type=Path, default=Path("user_data/tradesv3.dryrun.sqlite"))
    parser.add_argument("--since", type=date.fromisoformat, default=None)
    parser.add_argument("--out", type=Path, default=None, help="also write the report here")
    args = parser.parse_args(argv)

    live = dryrun_orders(args.db)
    if live.empty:
        print("No dry-run orders yet; nothing to compare.")
        return 0
    start = args.since or min(live["day"])
    end = datetime.now(UTC).date() - timedelta(days=1)  # last closed daily candle
    if end <= start:
        print(f"No closed daily candle after {start} yet; nothing to compare.")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        parity = compare(live, backtest_orders(replay(start, end, Path(tmp))), start, end)
    text = render(parity, start, end)
    print(text)
    out = args.out or Path("user_data/logs") / f"parity-{end}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    return 0 if parity.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

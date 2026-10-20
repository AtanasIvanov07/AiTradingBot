import json
import sqlite3
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from aitradingbot.ops import parity as pa

START, END = date(2026, 10, 20), date(2026, 10, 27)


def ms(day: str) -> int:
    return int(datetime.fromisoformat(day).replace(tzinfo=UTC).timestamp() * 1000)


def write_db(path: Path, rows: list[tuple[str, str, int, float, float, str]]) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE orders (ft_pair TEXT, ft_order_side TEXT, ft_is_open INTEGER, "
            "filled REAL, average REAL, price REAL, order_filled_date TEXT)"
        )
        connection.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(p, s, open_, f, a, a, d) for p, s, open_, f, a, d in rows],
        )


def write_backtest(path: Path, trades: list[dict[str, Any]]) -> Path:
    result = path / "backtest-result.zip"
    with zipfile.ZipFile(result, "w") as archive:
        payload = {"strategy": {pa.STRATEGY: {"trades": trades}}}
        archive.writestr("backtest-result.json", json.dumps(payload))
        archive.writestr("backtest-result_config.json", "{}")
    return result


def frame(rows: list[tuple[date, str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=pa.COLUMNS)


def test_dryrun_orders_reads_filled_orders_only(tmp_path: Path) -> None:
    db = tmp_path / "dry.sqlite"
    write_db(
        db,
        [
            ("BTC/EUR", "buy", 0, 0.001, 70000.0, "2026-10-21 00:00:05"),
            ("ETH/EUR", "buy", 1, 0.02, 2000.0, "2026-10-21 00:00:06"),  # still open
            ("ETH/EUR", "sell", 0, 0.0, 2000.0, "2026-10-21 00:00:07"),  # nothing filled
        ],
    )
    orders = pa.dryrun_orders(db)
    assert orders.to_dict("records") == [
        {"day": date(2026, 10, 21), "pair": "BTC/EUR", "side": "buy", "value": 70.0}
    ]


def test_backtest_orders_drop_the_closing_force_exit(tmp_path: Path) -> None:
    trades: list[dict[str, Any]] = [
        {
            "pair": "BTC/EUR",
            "exit_reason": "force_exit",
            "orders": [
                {"order_filled_timestamp": ms("2026-10-21"), "ft_is_entry": True, "cost": 40.0},
                {"order_filled_timestamp": ms("2026-10-24"), "ft_is_entry": False, "cost": 9.0},
                {"order_filled_timestamp": ms("2026-10-27"), "ft_is_entry": False, "cost": 31.0},
            ],
        }
    ]
    orders = pa.backtest_orders(write_backtest(tmp_path, trades))
    assert list(zip(orders["day"], orders["side"], orders["value"], strict=True)) == [
        (date(2026, 10, 21), "buy", 40.0),
        (date(2026, 10, 24), "sell", 9.0),  # a resize stays; only the final forced close goes
    ]


def test_compare_matches_and_explains_differences() -> None:
    dryrun = frame(
        [
            (START, "BTC/EUR", "buy", 47.0),  # bot start day: reported, not counted
            (date(2026, 10, 22), "BTC/EUR", "sell", 10.0),
            (date(2026, 10, 23), "ETH/EUR", "buy", 6.0),  # size off by 20%
            (date(2026, 10, 25), "ETH/EUR", "sell", 5.0),  # only in the dry-run
            (date(2026, 10, 28), "BTC/EUR", "sell", 3.0),  # after the replay window
        ]
    )
    backtest = frame(
        [
            (date(2026, 10, 22), "BTC/EUR", "sell", 10.2),  # within 5%
            (date(2026, 10, 23), "ETH/EUR", "buy", 5.0),
            (date(2026, 10, 26), "BTC/EUR", "buy", 7.0),  # only in the replay
        ]
    )
    result = pa.compare(dryrun, backtest, START, END)
    assert result.matched == 1 and result.start_day == 1 and not result.ok
    assert result.only_dryrun == [(date(2026, 10, 25), "ETH/EUR", "sell", 5.0)]
    assert result.only_backtest == [(date(2026, 10, 26), "BTC/EUR", "buy", 7.0)]
    assert result.size_mismatch == [(date(2026, 10, 23), "ETH/EUR", "buy", 6.0, 5.0)]
    report = pa.render(result, START, END)
    assert "DIFFERENCES" in report and "Only in the dry-run" in report


def test_identical_orders_are_ok() -> None:
    orders = frame([(date(2026, 10, 22), "BTC/EUR", "sell", 10.0)])
    result = pa.compare(orders, orders, START, END)
    assert result.ok and result.matched == 1
    assert pa.render(result, START, END).startswith("# Signal parity 2026-10-20 → 2026-10-27: OK")

import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

from aitradingbot.ops.backup import backup_sqlite


def test_backup_is_a_readable_copy_and_old_ones_are_pruned(tmp_path: Path) -> None:
    db = tmp_path / "tradesv3.dryrun.sqlite"
    with closing(sqlite3.connect(db)) as connection:
        connection.execute("CREATE TABLE trades (id INTEGER, pair TEXT)")
        connection.execute("INSERT INTO trades VALUES (1, 'BTC/EUR')")
        connection.commit()
    folder = tmp_path / "backups"
    first = date(2026, 10, 1)
    for offset in range(5):
        copy = backup_sqlite(db, folder, first + timedelta(days=offset), keep=3)
    assert copy.name == "tradesv3.dryrun-2026-10-05.sqlite"
    kept = sorted(p.name for p in folder.iterdir())
    assert kept == [f"tradesv3.dryrun-2026-10-0{d}.sqlite" for d in (3, 4, 5)]
    with closing(sqlite3.connect(copy)) as connection:
        assert connection.execute("SELECT pair FROM trades").fetchall() == [("BTC/EUR",)]

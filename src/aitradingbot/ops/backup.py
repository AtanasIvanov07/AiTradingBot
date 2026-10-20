"""Daily backup of the bot's SQLite database (PROJECT_PLAN.md §9.3).

The plan asks for a "daily DB backup copied off the host".

Uses SQLite's online backup API, so it's safe while the bot is writing. Keeps the newest ``keep``
copies. Copying the backup folder off the host is a separate step (see ops/runbook.md).
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path


def backup_sqlite(db: Path, folder: Path, day: date, keep: int = 14) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{db.stem}-{day.isoformat()}.sqlite"
    # closing(), not the connection's own `with`: that only commits, and Windows can't delete a
    # file that is still open (the pruning below failed that way).
    with (
        closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as source,
        closing(sqlite3.connect(target)) as copy,
    ):
        source.backup(copy)
    copies = sorted(folder.glob(f"{db.stem}-*.sqlite"))
    for old in copies[:-keep]:
        old.unlink()
    return target

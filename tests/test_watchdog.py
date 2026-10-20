import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from aitradingbot.ops import watchdog as wd

NOW = datetime(2026, 10, 21, 9, 0, tzinfo=UTC)


class FakeApi:
    """Canned Freqtrade REST responses; records every POST."""

    def __init__(
        self, equity: float = 100.0, dry_run: bool = True, last_candle: str = "2026-10-20"
    ):
        self.posts: list[tuple[str, dict[str, Any] | None]] = []
        self.down = False
        self.responses: dict[str, Any] = {
            "ping": {"status": "pong"},
            "show_config": {"dry_run": dry_run, "state": "running", "timeframe": "1d"},
            "health": {"last_process_ts": (NOW - timedelta(seconds=30)).timestamp()},
            "whitelist": {"whitelist": ["BTC/EUR", "ETH/EUR"]},
            "balance": {"starting_capital": 100.0},
            "profit": {"profit_all_coin": equity - 100.0},
            "status": [
                {
                    "pair": "BTC/EUR",
                    "amount": 0.0006,
                    "open_rate": 73000.0,
                    "current_rate": 73400.0,
                    "open_date": "2026-10-20 18:55:18",
                },
                {
                    "pair": "ETH/EUR",
                    "amount": 0.02,
                    "open_rate": 2160.0,
                    "current_rate": 2170.0,
                    "open_date": "2026-10-20 18:55:19",
                },
            ],  # fmt: skip
            "pair_candles": {"data": [[f"{last_candle}T00:00:00Z", 1, 1, 1, 1, 1]]},
        }

    def get(self, path: str) -> Any:
        if self.down:
            raise ConnectionRefusedError("connection refused")
        return self.responses[path.split("?")[0]]

    def post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        self.posts.append((path, body))
        return {"status": "ok"}

    def set_equity(self, equity: float) -> None:
        self.responses["profit"] = {"profit_all_coin": equity - 100.0}


def sources(
    errors: int = 0, kraken: dict[str, float] | None = None, now: datetime = NOW
) -> wd.Sources:
    prices = kraken or {"BTC/EUR": 73350.0, "ETH/EUR": 2168.0}
    return wd.Sources(
        now=lambda: now,
        second_source=lambda: prices,
        clock_drift=lambda: 0.2,
        error_times=lambda: [now - timedelta(minutes=1)] * errors,
    )


def run(api: FakeApi, state: wd.State, **kwargs: Any) -> tuple[list[wd.Finding], list[str]]:
    src = sources(**kwargs)
    findings = wd.run_once(api, state, src)
    return findings, wd.act(api, findings, state, src.now())


def critical(findings: list[wd.Finding]) -> list[str]:
    return [f.check for f in findings if f.level == "critical"]


def test_healthy_bot_needs_no_action() -> None:
    api, state = FakeApi(), wd.State()
    findings, done = run(api, state)
    assert critical(findings) == [] and done == [] and api.posts == []
    assert {f.check for f in findings} >= {"alive", "mode", "loop", "candles", "errors", "drawdown",
                                          "positions", "price", "clock"}  # fmt: skip
    assert state.peak_equity == 100.0 and state.day == "2026-10-21"


def test_live_mode_stops_the_bot() -> None:
    api, state = FakeApi(dry_run=False), wd.State()
    findings, done = run(api, state)
    assert "mode" in critical(findings)
    assert done == ["stop"] and api.posts == [("stop", None)] and state.halted


def test_drawdown_levels() -> None:
    api, state = FakeApi(), wd.State(peak_equity=100.0, day="2026-10-21", day_start_equity=76.0)
    api.set_equity(75.0)  # 25% below the peak, 1.3% down today
    findings, done = run(api, state)
    assert critical(findings) == ["drawdown"] and done == ["stopentry"] and state.review_needed
    api.set_equity(65.0)  # 35% below the peak
    _, done = run(api, state)
    assert done == ["forceexit all", "stop"] and state.halted
    assert ("forceexit", {"tradeid": "all"}) in api.posts


def test_daily_loss_pauses_then_resumes_after_24_hours() -> None:
    api, state = FakeApi(), wd.State(peak_equity=100.0, day="2026-10-21", day_start_equity=100.0)
    api.set_equity(94.0)  # 6% down today, 6% from the peak
    findings, done = run(api, state)
    assert critical(findings) == ["daily_loss"] and done == ["stopentry"]
    assert not state.review_needed and state.paused_until
    api.set_equity(95.0)
    _, done = run(api, state, now=NOW + timedelta(hours=25))  # a new day, pause expired
    assert done == ["start (daily-loss pause over)"] and state.paused_until == ""


def test_a_pause_needing_review_never_resumes_by_itself() -> None:
    state = wd.State(peak_equity=100.0, day="2026-10-21", day_start_equity=100.0)
    state.paused_until = (NOW - timedelta(hours=1)).isoformat()
    state.review_needed = True
    _, done = run(FakeApi(), state)
    assert done == [] and state.paused_until == ""


@pytest.mark.parametrize(
    ("kwargs", "api_kwargs", "check"),
    [
        ({"errors": 6}, {}, "errors"),
        ({"kraken": {"BTC/EUR": 70000.0, "ETH/EUR": 2168.0}}, {}, "price"),
        ({}, {"last_candle": "2026-10-17"}, "candles"),
    ],
)
def test_operational_triggers_stop_entries(
    kwargs: dict[str, Any], api_kwargs: dict[str, Any], check: str
) -> None:
    api, state = FakeApi(**api_kwargs), wd.State()
    findings, done = run(api, state, **kwargs)
    assert set(critical(findings)) == {check} and done == ["stopentry"] and state.review_needed


def test_a_just_restarted_bot_is_not_a_crash() -> None:
    # Fire drill D4: right after a restart Freqtrade reports no finished loop yet (None).
    started = {"last_process_ts": None, "bot_start_ts": (NOW - timedelta(seconds=20)).timestamp()}
    assert wd.check_loop(started, NOW).level == "warning"
    stuck = {"last_process_ts": None, "bot_start_ts": (NOW - timedelta(minutes=30)).timestamp()}
    assert wd.check_loop(stuck, NOW).level == "critical"


def test_five_errors_only_warn() -> None:
    findings, done = run(FakeApi(), wd.State(), errors=5)
    assert [f.level for f in findings if f.check == "errors"] == ["warning"] and done == []


def test_unreachable_bot_is_critical_without_actions() -> None:
    api = FakeApi()
    api.down = True
    findings, done = run(api, wd.State())
    assert [(f.level, f.check) for f in findings] == [("critical", "alive")]
    assert done == [] and api.posts == []


def test_emergency_runs_the_runbook_sequence() -> None:
    api, state = FakeApi(), wd.State()
    wd.emergency(api, state)
    assert [path for path, _ in api.posts] == ["stopentry", "forceexit", "stop"]
    assert state.halted and state.review_needed


def test_resume_clears_flags() -> None:
    api = FakeApi()
    state = wd.State(review_needed=True, halted=True, paused_until=NOW.isoformat())
    wd.resume(api, state)
    assert not (state.review_needed or state.halted or state.paused_until)
    assert api.posts == [("start", None)]


def test_daily_report_once_a_day_after_8() -> None:
    api, state = FakeApi(), wd.State()
    wd.remember_start(api, state, NOW)
    assert state.start_prices == {"BTC/EUR": 73400.0, "ETH/EUR": 2170.0}
    assert wd.daily_report(api, state, datetime(2026, 10, 21, 7, 59)) is None
    report = wd.daily_report(api, state, datetime(2026, 10, 21, 8, 1))
    assert report is not None and "50/50 buy & hold +0.0%" in report and "not evidence" in report
    assert wd.daily_report(api, state, datetime(2026, 10, 21, 20, 0)) is None


def test_settings_ignore_a_disabled_telegram(tmp_path: Path) -> None:
    path = tmp_path / "config.private.json"
    server = {
        "listen_ip_address": "127.0.0.1",
        "listen_port": 8080,
        "username": "u",
        "password": "p",
    }
    path.write_text(
        json.dumps(
            {"api_server": server, "telegram": {"enabled": False, "token": "t", "chat_id": 1}}
        )
    )
    settings = wd.Settings.from_private_config(path)
    assert settings.api_url == "http://127.0.0.1:8080" and settings.telegram_token == ""
    assert settings.healthchecks_url == ""


def test_state_round_trip(tmp_path: Path) -> None:
    state = wd.State(peak_equity=101.5, start_prices={"BTC/EUR": 1.0})
    state.save(tmp_path / "s.json")
    assert wd.State.load(tmp_path / "s.json") == state
    assert wd.State.load(tmp_path / "missing.json") == wd.State()


def test_watchdog_needs_only_the_standard_library() -> None:
    # The Linux host runs it with the system python3 (ops/linux/aitradingbot-watchdog.service).
    code = "import sys; sys.modules['pandas'] = sys.modules['numpy'] = None; "
    code += "import aitradingbot.ops.watchdog, aitradingbot.ops.private_config"
    subprocess.run([sys.executable, "-c", code], check=True)

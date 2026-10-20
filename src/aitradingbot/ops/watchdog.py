"""External watchdog for the Freqtrade bot (PROJECT_PLAN.md §6.4–§6.6 and §9.1).

Usage:
    python -m aitradingbot.ops.watchdog            # one check, e.g. from cron every 5 minutes
    python -m aitradingbot.ops.watchdog --loop 300 # keep checking every 300 s

It reads the bot through its REST API (credentials from user_data/config.private.json), compares
prices with a second exchange, and acts on the plan's triggers:
- drawdown from the equity peak > 20%, or a daily loss > 5%: stop new entries (`/stopentry`);
- drawdown > 30%: force-exit everything and stop the bot;
- live mode found on the learning path: stop the bot (A1 is dry-run only);
- stale candles, > 5 errors in 10 minutes, or a > 3% price gap to Kraken: stop new entries.
A daily-loss pause resumes after 24 h; everything else needs a manual review.

Alerts go to the log file, and to Telegram when it's configured. When `watchdog.healthchecks_url`
is set in the private config, every run pings it (or `/fail` on a critical finding), as the
heartbeat of §9.1. Telegram is reached directly, so the watchdog still alerts when the bot is down.
"""

from __future__ import annotations

import argparse
import base64
import json
import sqlite3
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Protocol

from aitradingbot.ops.backup import backup_sqlite

Level = Literal["ok", "warning", "critical"]
Action = Literal["stopentry", "forceexit", "stop", "start"]

PAUSE_DRAWDOWN = 0.20
HALT_DRAWDOWN = 0.30
DAILY_LOSS = 0.05
DAILY_PAUSE = timedelta(hours=24)
MAX_ERRORS = 5
ERROR_WINDOW = timedelta(minutes=10)
STALE_AFTER = timedelta(days=3)  # last closed 1d candle opened > 2 intervals before the current one
STUCK_AFTER = timedelta(minutes=10)
MAX_PRICE_GAP = 0.03
MAX_CLOCK_DRIFT = 1.0  # seconds
KRAKEN_PAIRS = {"BTC/EUR": "XXBTZEUR", "ETH/EUR": "XETHZEUR"}  # Kraken's result keys
REPORT_HOUR = 8  # local time, §9.1 daily report


@dataclass(frozen=True)
class Finding:
    level: Level
    check: str
    detail: str
    actions: tuple[Action, ...] = ()


@dataclass
class State:
    """Persisted between runs (user_data/logs/watchdog-state.json)."""

    peak_equity: float = 0.0
    day: str = ""
    day_start_equity: float = 0.0
    paused_until: str = ""  # ISO time, set by a daily-loss pause (resumes by itself)
    review_needed: bool = False  # any other pause: resume only with --resume after a review
    halted: bool = False  # 30% drawdown or live mode: the bot was stopped
    last_report: str = ""
    start_date: str = ""
    start_prices: dict[str, float] = field(default_factory=dict)
    start_equity: float = 0.0

    @classmethod
    def load(cls, path: Path) -> State:
        if not path.exists():
            return cls()
        return cls(**json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8", newline="\n")


class Api(Protocol):
    def get(self, path: str) -> Any: ...
    def post(self, path: str, body: dict[str, Any] | None = None) -> Any: ...


class BotApi:
    """Minimal client for Freqtrade's REST API (HTTP basic auth)."""

    def __init__(self, url: str, username: str, password: str, timeout: float = 10) -> None:
        self.url = url.rstrip("/")
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
        self.timeout = timeout

    def _call(self, method: str, path: str, body: dict[str, Any] | None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            f"{self.url}/api/v1/{path}", data=data, headers=self.headers, method=method
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read())

    def get(self, path: str) -> Any:
        return self._call("GET", path, None)

    def post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        return self._call("POST", path, body or {})


def http_json(url: str, timeout: float = 10) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read())


def kraken_prices() -> dict[str, float]:
    """Last trade prices from Kraken's public ticker, keyed like the bot's pairs."""
    query = ",".join(KRAKEN_PAIRS.values())
    result = http_json(f"https://api.kraken.com/0/public/Ticker?pair={query}")["result"]
    return {pair: float(result[key]["c"][0]) for pair, key in KRAKEN_PAIRS.items()}


def bitvavo_clock_drift() -> float:
    """Seconds between this machine's clock and Bitvavo's server time."""
    server_ms = float(http_json("https://api.bitvavo.com/v2/time")["time"])
    return abs(time.time() - server_ms / 1000)


@dataclass
class Sources:
    """Everything outside the bot, injectable for tests."""

    now: Callable[[], datetime] = lambda: datetime.now(UTC)
    second_source: Callable[[], dict[str, float]] = kraken_prices
    clock_drift: Callable[[], float] = bitvavo_clock_drift
    error_times: Callable[[], list[datetime]] = list


def log_error_times(
    log: Path, keep: timedelta = timedelta(hours=1)
) -> Callable[[], list[datetime]]:
    """Times of ERROR lines in Freqtrade's log (local timestamps), from the last ``keep``."""

    def read() -> list[datetime]:
        if not log.exists():
            return []
        cutoff = datetime.now() - keep
        found = []
        with log.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if " - ERROR - " not in line:
                    continue
                try:
                    stamp = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
                if stamp >= cutoff:
                    found.append(stamp.astimezone(UTC))
        return found

    return read


# --- checks ---------------------------------------------------------------------------------------


def equity_of(api: Api) -> float:
    """Bot equity marked to current prices, net of estimated exit fees.

    Not /balance's total: that values coins with cached tickers and can lag for minutes.
    """
    starting = float(api.get("balance")["starting_capital"])
    return starting + float(api.get("profit")["profit_all_coin"])


def check_mode(config: dict[str, Any]) -> Finding:
    if not config.get("dry_run", False):
        return Finding(
            "critical", "mode", "bot is LIVE; the learning path is dry-run only", ("stop",)
        )
    return Finding("ok", "mode", f"dry-run, state {config.get('state')}")


def check_loop(health: dict[str, Any], now: datetime) -> Finding:
    if health.get("last_process_ts") is None:  # just restarted: no loop finished yet
        started = datetime.fromtimestamp(float(health.get("bot_start_ts") or 0), UTC)
        if now - started > STUCK_AFTER:
            return Finding(
                "critical", "loop", f"no bot loop since the start at {started:%H:%M} UTC"
            )
        return Finding("warning", "loop", "bot starting: no loop finished yet")
    last = datetime.fromtimestamp(float(health["last_process_ts"]), UTC)
    if now - last > STUCK_AFTER:
        return Finding("critical", "loop", f"no bot loop since {last:%Y-%m-%d %H:%M} UTC")
    return Finding("ok", "loop", f"last loop {int((now - last).total_seconds())} s ago")


def check_candles(api: Api, pairs: list[str], timeframe: str, now: datetime) -> list[Finding]:
    findings = []
    for pair in pairs:
        candles = api.get(f"pair_candles?pair={urllib.parse.quote(pair)}&timeframe={timeframe}")
        if not candles["data"]:
            findings.append(Finding("critical", "candles", f"{pair}: no candles", ("stopentry",)))
            continue
        last = datetime.fromisoformat(candles["data"][-1][0].replace("Z", "+00:00"))
        if now - last > STALE_AFTER:
            detail = f"{pair}: last candle {last:%Y-%m-%d}, stale"
            findings.append(Finding("critical", "candles", detail, ("stopentry",)))
        else:
            findings.append(Finding("ok", "candles", f"{pair}: last candle {last:%Y-%m-%d}"))
    return findings


def check_errors(times: list[datetime], now: datetime) -> Finding:
    recent = [t for t in times if now - t <= ERROR_WINDOW]
    if len(recent) > MAX_ERRORS:
        detail = f"{len(recent)} errors in 10 minutes"
        return Finding("critical", "errors", detail, ("stopentry",))
    if recent:
        return Finding("warning", "errors", f"{len(recent)} errors in 10 minutes")
    return Finding("ok", "errors", "no recent errors")


def check_risk(equity: float, state: State, now: datetime) -> list[Finding]:
    """§6.4 circuit breakers on the bot's equity. Updates the peak and the day's start equity."""
    state.peak_equity = max(state.peak_equity, equity)
    today = now.date().isoformat()
    if state.day != today:
        state.day, state.day_start_equity = today, equity
    findings = []
    drawdown = 1 - equity / state.peak_equity if state.peak_equity > 0 else 0.0
    detail = f"equity {equity:.2f}, peak {state.peak_equity:.2f}, drawdown {drawdown:.1%}"
    if drawdown > HALT_DRAWDOWN:
        findings.append(Finding("critical", "drawdown", detail, ("forceexit", "stop")))
    elif drawdown > PAUSE_DRAWDOWN:
        findings.append(Finding("critical", "drawdown", detail, ("stopentry",)))
    else:
        findings.append(Finding("ok", "drawdown", detail))
    day_loss = 1 - equity / state.day_start_equity if state.day_start_equity > 0 else 0.0
    if day_loss > DAILY_LOSS:
        detail = f"down {day_loss:.1%} today; entries paused for 24 h"
        findings.append(Finding("critical", "daily_loss", detail, ("stopentry",)))
        if not state.paused_until:
            state.paused_until = (now + DAILY_PAUSE).isoformat()
    return findings


def check_prices(trades: list[dict[str, Any]], reference: dict[str, float]) -> list[Finding]:
    findings = []
    for trade in trades:
        pair, rate = trade["pair"], trade.get("current_rate")
        if pair not in reference or not rate:
            continue
        gap = abs(float(rate) / reference[pair] - 1)
        detail = f"{pair}: bot {rate} vs Kraken {reference[pair]} ({gap:.2%})"
        if gap > MAX_PRICE_GAP:
            findings.append(Finding("critical", "price", detail, ("stopentry",)))
        else:
            findings.append(Finding("ok", "price", detail))
    return findings


def check_positions(trades: list[dict[str, Any]], pairs: list[str], now: datetime) -> list[Finding]:
    findings = []
    for trade in trades:
        if trade["pair"] not in pairs:
            detail = f"unexpected position in {trade['pair']}"
            findings.append(Finding("critical", "positions", detail, ("stopentry",)))
        opened = datetime.fromisoformat(trade["open_date"]).replace(tzinfo=UTC)
        if trade.get("has_open_orders") and now - opened > timedelta(minutes=10):
            detail = f"{trade['pair']}: order open for more than 10 minutes"
            findings.append(Finding("warning", "positions", detail))
    return findings or [Finding("ok", "positions", f"{len(trades)} open, all expected")]


def check_clock(drift: float) -> Finding:
    if drift > MAX_CLOCK_DRIFT:
        return Finding("warning", "clock", f"clock {drift:.2f} s off Bitvavo's")
    return Finding("ok", "clock", f"drift {drift:.2f} s")


# --- one run ------------------------------------------------------------------------------------


def run_once(api: Api, state: State, sources: Sources) -> list[Finding]:
    """All checks against the bot. Doesn't act; see ``act``."""
    now = sources.now()
    try:
        api.get("ping")
        config = api.get("show_config")
        findings = [Finding("ok", "alive", "API answers"), check_mode(config)]
        findings.append(check_loop(api.get("health"), now))
        pairs = [str(p) for p in api.get("whitelist")["whitelist"]]
        findings += check_candles(api, pairs, str(config["timeframe"]), now)
        findings.append(check_errors(sources.error_times(), now))
        findings += check_risk(equity_of(api), state, now)
        trades = api.get("status")
        findings += check_positions(trades, pairs, now)
    except OSError as error:
        return [Finding("critical", "alive", f"bot API unreachable: {error}")]
    for name, read in (("price", sources.second_source), ("clock", sources.clock_drift)):
        try:
            value = read()
        except (OSError, KeyError, StopIteration, ValueError) as error:
            findings.append(Finding("warning", name, f"second source unavailable: {error}"))
            continue
        if name == "price":
            assert isinstance(value, dict)
            findings += check_prices(trades, value)
        else:
            assert isinstance(value, float)
            findings.append(check_clock(value))
    return findings


def act(api: Api, findings: list[Finding], state: State, now: datetime) -> list[str]:
    """Apply the actions the findings call for; resume a finished daily-loss pause."""
    wanted: list[Action] = []
    for finding in findings:
        wanted += [a for a in finding.actions if a not in wanted]
        if finding.actions and finding.check != "daily_loss":
            state.review_needed = True
    done = []
    if "stop" in wanted or "forceexit" in wanted:
        state.halted = True
    if "forceexit" in wanted:
        api.post("forceexit", {"tradeid": "all"})
        done.append("forceexit all")
    if "stop" in wanted:
        api.post("stop")
        done.append("stop")
    elif "stopentry" in wanted:
        api.post("stopentry")
        done.append("stopentry")
    elif state.paused_until and now >= datetime.fromisoformat(state.paused_until):
        state.paused_until = ""
        if not (state.halted or state.review_needed):
            api.post("start")
            done.append("start (daily-loss pause over)")
    return done


def emergency(api: Api, state: State) -> str:
    """Runbook emergency step 2, by hand: stop entries, exit every position, stop the bot."""
    api.post("stopentry")
    api.post("forceexit", {"tradeid": "all"})
    api.post("stop")
    state.halted = state.review_needed = True
    return "emergency: stopentry, forceexit all, stop sent"


def resume(api: Api, state: State) -> str:
    """Manual reset after a written review (PROJECT_PLAN.md §6.4): clear flags, allow entries."""
    state.review_needed = state.halted = False
    state.paused_until = ""
    api.post("start")
    return "resumed by hand: flags cleared, /start sent"


# --- alerts and reports -------------------------------------------------------------------------


@dataclass(frozen=True)
class Settings:
    api_url: str
    username: str
    password: str
    telegram_token: str = ""
    telegram_chat: str = ""
    healthchecks_url: str = ""

    @classmethod
    def from_private_config(cls, path: Path) -> Settings:
        config = json.loads(path.read_text(encoding="utf-8-sig"))
        server = config["api_server"]
        telegram = config.get("telegram", {})
        enabled = bool(telegram.get("enabled"))
        host = server["listen_ip_address"]
        if host in ("0.0.0.0", "::"):  # in Docker: compose publishes the port on 127.0.0.1
            host = "127.0.0.1"
        return cls(
            api_url=f"http://{host}:{server['listen_port']}",
            username=server["username"],
            password=server["password"],
            telegram_token=telegram.get("token", "") if enabled else "",
            telegram_chat=str(telegram.get("chat_id", "")) if enabled else "",
            healthchecks_url=config.get("watchdog", {}).get("healthchecks_url", ""),
        )


def send_telegram(settings: Settings, text: str) -> None:
    if not (settings.telegram_token and settings.telegram_chat):
        return
    body = urllib.parse.urlencode({"chat_id": settings.telegram_chat, "text": text}).encode()
    url = f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage"
    urllib.request.urlopen(url, data=body, timeout=10).close()


def ping_healthchecks(settings: Settings, failed: bool) -> None:
    if settings.healthchecks_url:
        url = settings.healthchecks_url.rstrip("/") + ("/fail" if failed else "")
        urllib.request.urlopen(url, timeout=10).close()


def daily_report(api: Api, state: State, now_local: datetime) -> str | None:
    """Once a day after 08:00: equity and positions vs a 50/50 buy & hold from the first run."""
    today = now_local.date().isoformat()
    if now_local.hour < REPORT_HOUR or state.last_report == today:
        return None
    state.last_report = today
    equity = equity_of(api)
    trades = api.get("status")
    prices = {t["pair"]: float(t["current_rate"]) for t in trades if t.get("current_rate")}
    lines = [f"Daily report {today} (dry-run, not evidence of an edge)", f"Equity {equity:.2f} EUR"]
    if state.start_equity and state.start_prices and set(prices) >= set(state.start_prices):
        hold = sum(0.5 * prices[p] / state.start_prices[p] for p in state.start_prices)
        lines.append(
            f"Since {state.start_date}: bot {equity / state.start_equity - 1:+.1%}, "
            f"50/50 buy & hold {hold - 1:+.1%}"
        )
    for trade in trades:
        lines.append(
            f"{trade['pair']}: {trade['amount']} @ {trade['open_rate']} "
            f"(now {trade.get('current_rate')})"
        )
    if not trades:
        lines.append("No open positions")
    return "\n".join(lines)


def remember_start(api: Api, state: State, now: datetime) -> None:
    """Benchmark baseline: prices and equity at the watchdog's first run with both pairs priced."""
    if state.start_prices:
        return
    trades = api.get("status")
    prices = {t["pair"]: float(t["current_rate"]) for t in trades if t.get("current_rate")}
    if len(prices) < len(KRAKEN_PAIRS):
        return  # wait until both pairs have a live price
    state.start_prices = prices
    state.start_equity = equity_of(api)
    state.start_date = now.date().isoformat()


def format_findings(findings: list[Finding], done: list[str], now: datetime) -> str:
    worst = max(findings, key=lambda f: ["ok", "warning", "critical"].index(f.level)).level
    lines = [f"{now:%Y-%m-%d %H:%M:%S} UTC watchdog: {worst.upper()}"]
    lines += [f"  [{f.level}] {f.check}: {f.detail}" for f in findings if f.level != "ok"]
    if done:
        lines.append(f"  actions: {', '.join(done)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aitradingbot.ops.watchdog")
    parser.add_argument(
        "--private-config", type=Path, default=Path("user_data/config.private.json")
    )
    parser.add_argument("--state", type=Path, default=Path("user_data/logs/watchdog-state.json"))
    parser.add_argument("--log", type=Path, default=Path("user_data/logs/watchdog.log"))
    parser.add_argument("--bot-log", type=Path, default=Path("user_data/logs/freqtrade.log"))
    parser.add_argument("--db", type=Path, default=Path("user_data/tradesv3.dryrun.sqlite"))
    parser.add_argument("--backup-dir", type=Path, default=Path("user_data/backups"))
    parser.add_argument("--loop", type=int, default=0, help="repeat every N seconds (0 = once)")
    parser.add_argument("--resume", action="store_true", help="clear pauses after a review")
    parser.add_argument("--emergency", action="store_true", help="exit everything and stop")
    args = parser.parse_args(argv)

    settings = Settings.from_private_config(args.private_config)
    api = BotApi(settings.api_url, settings.username, settings.password)
    if args.resume or args.emergency:
        state = State.load(args.state)
        print(emergency(api, state) if args.emergency else resume(api, state))
        state.save(args.state)
        return 0
    sources = Sources(error_times=log_error_times(args.bot_log))
    while True:
        try:
            critical = cycle(
                api, settings, sources, args.state, args.log, (args.db, args.backup_dir)
            )
        except Exception as error:  # the watchdog itself must never die silently
            critical = True
            message = f"{sources.now():%Y-%m-%d %H:%M:%S} UTC watchdog ERROR: {error!r}"
            write_log(args.log, message)
            try:
                send_telegram(settings, message)
                ping_healthchecks(settings, failed=True)
            except OSError:
                pass
        if not args.loop:
            return 2 if critical else 0
        time.sleep(args.loop)


def write_log(log: Path, text: str) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text + "\n")


def cycle(
    api: Api,
    settings: Settings,
    sources: Sources,
    state_path: Path,
    log: Path,
    backup: tuple[Path, Path] | None = None,
) -> bool:
    """One watchdog run: check, act, report, alert. Returns True on a critical finding.

    With the daily report it also backs up the bot database (``backup`` = (db, folder)).
    """
    state = State.load(state_path)
    now = sources.now()
    findings = run_once(api, state, sources)
    reachable = findings[0].check != "alive" or findings[0].level == "ok"
    done = act(api, findings, state, now) if reachable else []
    report = None
    if reachable:
        try:
            remember_start(api, state, now)
            report = daily_report(api, state, datetime.now())
        except OSError as error:
            findings.append(Finding("warning", "report", f"report failed: {error}"))
    if report and backup and backup[0].exists():
        try:
            copy = backup_sqlite(backup[0], backup[1], now.date())
            report += f"\nDatabase backed up to {copy}"
        except (OSError, sqlite3.Error) as error:
            findings.append(Finding("warning", "backup", f"backup failed: {error}"))
    state.save(state_path)
    message = format_findings(findings, done, now)
    write_log(log, message + ("\n" + report if report else ""))
    print(message)
    critical = any(f.level == "critical" for f in findings)
    try:
        if critical or done:
            send_telegram(settings, message)
        if report:
            send_telegram(settings, report)
        ping_healthchecks(settings, critical)
    except OSError as error:
        write_log(log, f"  alert delivery failed: {error}")
    return critical


if __name__ == "__main__":
    raise SystemExit(main())

# Runbook

For the learning-only path (PROJECT_PLAN.md amendment A1): the **H5TrendVol** strategy in **dry-run** (paper trading,
€100 paper wallet, Bitvavo market data), plus the external watchdog. No exchange API keys, no real money.

All commands run from the repo root (`C:\dev\AiTradingBot` on the PC).

## What runs where

| Part | Windows PC (now) | Linux host (Azure / Oracle, later) |
|---|---|---|
| Bot | `freqtrade trade … --strategy H5TrendVol`, started by `ops\windows\start-dryrun.ps1` | `docker compose -f ops/docker-compose.yml up -d` |
| Watchdog | `python -m aitradingbot.ops.watchdog --loop 120`, started by the same script | the same command under systemd (see `ops/linux/`) |
| Bot log | `user_data\logs\freqtrade.log` | `user_data/logs/freqtrade.log` |
| Watchdog log, state, daily report | `user_data\logs\watchdog.log`, `watchdog-state.json` | same |
| Paper trades (SQLite) | `user_data\tradesv3.dryrun.sqlite` | same |
| Daily DB backups (14 kept) | `user_data\backups\` | same; copy off the host (below) |
| REST API / FreqUI | `http://127.0.0.1:8080` (localhost only) | via an SSH tunnel: `ssh -L 8080:127.0.0.1:8080 <host>` |

Secrets (API login, Telegram token, Healthchecks URL) live only in `user_data/config.private.json` (gitignored).
Never paste them into chats, screenshots or issues.

## Start / stop / restart

**Windows PC**
- Start (or restart whatever isn't running): `powershell -ExecutionPolicy Bypass -File ops\windows\start-dryrun.ps1`
- Stop the bot and the watchdog: `powershell -ExecutionPolicy Bypass -File ops\windows\stop-dryrun.ps1`
- Nothing restarts a crashed bot on Windows. After a "bot API unreachable" alert, run the start script.
- Sleep, Windows Update reboots and shutdowns stop the bot. Keep the PC awake while it's the host, or move to the
  Linux host. Changing power settings is yours to do.

**Linux host**
- Start: `docker compose -f ops/docker-compose.yml up -d`, then `sudo systemctl start aitradingbot-watchdog`.
- Stop: `sudo systemctl stop aitradingbot-watchdog`, then `docker compose -f ops/docker-compose.yml down`.
- Logs: `docker compose -f ops/docker-compose.yml logs -f --tail 100`
- Docker restarts a crashed bot (`restart: unless-stopped`).

## Is it healthy?

- One watchdog check now: `.venv\Scripts\python.exe -m aitradingbot.ops.watchdog`. It prints OK, WARNING or
  CRITICAL with the reasons.
- `user_data\logs\watchdog.log`: one line every 2 minutes, plus the daily report after 08:00.
- What the watchdog checks:
  - the API is up and the bot loop is running;
  - the bot is in dry-run;
  - candles are fresh;
  - errors in the bot log;
  - drawdown and daily loss;
  - unexpected positions;
  - price vs Kraken;
  - clock drift.
  It acts on its own (below), and alerts on Telegram once that's configured.

## Routines (PROJECT_PLAN.md §9.2)

- **Daily (2 min):** read the daily report (Telegram, or the end of `watchdog.log`), and check the last lines say OK.
- **Weekly (30 min):**
  1. Signal parity: `.venv\Scripts\python.exe -m aitradingbot.ops.parity`. It writes
     `user_data\logs\parity-<date>.md`.
     - Every difference must be explained or fixed (Gate 3).
     - Orders on the bot's first day are reported but not counted.
  2. Errors: `Select-String -Path user_data\logs\freqtrade.log -Pattern " - ERROR - "`.
  3. Write a short note in `research/journal.md`: uptime, parity result, anything odd.
- **Monthly:** copy `user_data\backups\` off the host. Check the Azure credit, once Azure is in use.

## What the watchdog does by itself (PROJECT_PLAN.md §6.4 / §6.6)

| Trigger | Action | Undo |
|---|---|---|
| Daily loss > 5% | `/stopentry` (pause new entries) | Resumes by itself after 24 h |
| Drawdown from peak > 20% | `/stopentry` | By hand, after a written review (below) |
| Drawdown from peak > 30% | `/forceexit all` + `/stop` | By hand, after a post-mortem |
| Bot is in live mode | `/stop` | Fix the config. The learning path is dry-run only |
| Candles stale > 2 days, > 5 errors in 10 min, price > 3% off Kraken, unexpected position | `/stopentry` | By hand, after a review |

**Resume after a review:** write what happened and why it's safe in `research/journal.md`, then run
`.venv\Scripts\python.exe -m aitradingbot.ops.watchdog --resume`. That clears the watchdog's flags and sends `/start`.

## Emergency (in order)

1. Telegram, once it's set up: `/stopentry`, then `/forceexit all`, then `/stop`.
2. Watchdog manual trigger, which does the same three steps:
   `.venv\Scripts\python.exe -m aitradingbot.ops.watchdog --emergency`
3. Stop the processes: `ops\windows\stop-dryrun.ps1`, or `docker compose … down`.
4. Live trading only (not on this path): on the exchange website, **delete the API key**, then close positions by hand.
5. Write a post-mortem in `research/reports/` before restarting.

## Restore the database from a backup

1. Stop the bot and the watchdog (above).
2. Keep the current file: rename `user_data\tradesv3.dryrun.sqlite` to `tradesv3.dryrun.broken.sqlite`.
3. Copy the chosen `user_data\backups\tradesv3.dryrun-<date>.sqlite` to `user_data\tradesv3.dryrun.sqlite`.
4. Start again, then check `/status` (FreqUI, or one watchdog check) shows the expected open paper trades.
5. Paper trades after the backup's date are lost. Note it in the journal; parity for those days won't match.

**Copy backups off the host:**
- From the PC to the Linux host's backups: `scp -r <host>:AiTradingBot/user_data/backups ./host-backups`
- On the PC itself, copy `user_data\backups` to another disk or cloud folder you control.

## Upgrade Freqtrade

1. Bump the version in `requirements.txt` **and** `ops/docker-compose.yml` (a test enforces the match).
2. Run `pytest`, a backtest (`journal #10` command) and the parity check.
3. Run it in dry-run for one week. Rollback: revert both files, reinstall, and restart.

## Switch dry-run ↔ live

**Not on the learning path.** Phase 4 stays locked (amendment A1), and `tests/test_repo.py` fails if `config.json`
leaves dry-run. Any change here needs a new plan decision first.

## Fire drills

Procedure and results: [ops/fire-drills.md](fire-drills.md). Run them on the **drill bot** (port 8081, its own
database), never on the main paper bot.

## Links

- ESMA MiCA register: https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/markets-crypto-assets-regulation-mica
- Freqtrade REST API and Telegram docs: https://www.freqtrade.io/en/stable/rest-api/ and
  https://www.freqtrade.io/en/stable/telegram-usage/
- Bitvavo status and support: TODO. Add the official status page link from Bitvavo's help centre (verify it
  yourself).
- Tax notes: TODO (PROJECT_PLAN.md §8.2). Paper trades aren't taxable events.

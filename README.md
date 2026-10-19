# AiTradingBot

A rule-based spot crypto trading experiment (BTC/EUR, ETH/EUR) built on [Freqtrade](https://www.freqtrade.io/).
**[PROJECT_PLAN.md](PROJECT_PLAN.md)** covers the goals, risk rules, phase gates and timeline.

> Dry-run only until Phase 4's gate is passed. `tests/test_repo.py` fails if `user_data/config.json` leaves dry-run.

## Quick start (Windows, PowerShell)

```powershell
# one-time setup
py -3.12 -m venv .venv            # or: & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
pip install -e . --no-deps        # makes `python -m aitradingbot...` work
pre-commit install

# checks
pre-commit run --all-files
pytest

# smoke-test backtest (Phase 0)
freqtrade download-data --config user_data/config.json --timeframes 5m --timerange 20261001-
freqtrade backtesting --config user_data/config.json --strategy SampleStrategy --timerange 20261002- --fee 0.0025
```

## Research data (Phase 1)

```powershell
python -m aitradingbot.ingest all        # Binance (USDT), Kraken (EUR), Bitvavo (EUR): 1d, 4h, 1h
python -m aitradingbot.validate --out research/reports/data-validation.md
pytest                                   # includes tests/test_data_quality.py on the real data
```

| Source | What | How |
|---|---|---|
| Binance public data | BTC/USDT, ETH/USDT since Aug 2017 | Monthly zips from data.binance.vision, SHA-256 verified, cached in `data/raw/` |
| Kraken OHLCVT | BTC/EUR, ETH/EUR long EUR history | Reads only the needed CSVs out of Kraken's ~10 GB archive via HTTP range requests (CRC-checked). `--zip` accepts local copies. |
| Bitvavo API | BTC/EUR, ETH/EUR, the market the bot trades | Public candles endpoint, paged backwards; unclosed candles dropped |

Everything lands in `data/clean/<source>/<BASE>_<QUOTE>_<tf>.parquet` with a `.manifest.json` (inputs, checksums, row
counts). Candles are labelled by **open time in UTC**. Splits are in `src/aitradingbot/splits.py`; the holdout
(2025-01 → 2026-09) is downloaded and quality-checked, but strategy results on it are looked at once, at the end of Phase 2.

## Pre-screen (Phase 1, Gate 1)

```powershell
python -m aitradingbot.analysis.prescreen H1 --out research/reports/prescreen-H1.md
```

Applies the **registered** rules in `research/hypotheses/` mechanically: the grid, plateau-median variant selection,
the §7 pass rule at 2× costs, and each card's kill rules. It uses development data (2018–2022) only, and the exit code is 0
only on PASS. Log every run in `research/journal.md`. The engine (`src/aitradingbot/analysis/engine.py`) fills each
decision at the next candle's open; `tests/test_engine.py` checks it against a hand-calculated example.

## Layout

| Path | What |
|---|---|
| `research/` | Journal of every test, hypothesis cards, notebooks, gate reports |
| `src/aitradingbot/` | Data ingest, validation, analysis harness (Phases 1–2) |
| `user_data/` | Freqtrade: strategies and `config.json` (no secrets). Secrets go in `config.private.json` (gitignored). |
| `ops/` | Server `docker-compose.yml`, runbook, watchdog (Phase 3) |
| `tests/` | pytest |
| `data/` | Research data (gitignored) |

## Safety rules
- Never commit secrets. `gitleaks` runs on every commit; `config.private.json` and `.env` are gitignored.
- API keys: trade + read only, **never withdrawal**, IP-whitelisted.
- Pin Freqtrade: `requirements.txt` and the Docker image tag must match (enforced by a test).

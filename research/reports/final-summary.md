# Closing summary

Closed **2026-10-25** under PROJECT_PLAN.md amendment A3's final stop, by the project owner's decision not to
register a seventh hypothesis. Details of every run are in [research/journal.md](../journal.md) (#0–#16) and the
reports next to this file. Phase 1's own closing summary is [phase1-summary.md](phase1-summary.md).

## Decision

**Stop for good.** Six registered hypotheses were tested; none passed. No strategy goes forward, nothing ever traded
with real money, and no exchange API key was ever created. The plan's outcome for this case applies: the project
counts as a learning success. The plan's suggested alternative was plain monthly DCA. That's a personal decision,
not something this project recommends.

## What was tested

All results at 2× costs (0.60% per side) on Kraken EUR daily data, for the variant each card's rules selected.

| Card | Idea | Test and period | CAGR | Max DD | Sharpe | Calmar | Benchmark (50/50 buy & hold) | Why killed |
|---|---|---|---:|---:|---:|---:|---|---|
| H1 | Trend filter (SMA with band) | Gate 1, 2018–2022 | 47.3% | −57.2% | 0.99 | 0.83 | 8.5%, −87.0%, Calmar 0.10 | Drawdown > 40%; no plateau |
| H2 | Weekly BTC/ETH/cash rotation | Gate 1, 2018–2022 | 37.0% | −79.8% | 0.80 | 0.46 | same | Drawdown; no plateau; worse than H1 |
| H3 | Volatility-targeted holding | Gate 1, 2018–2022 | 12.5% | −47.7% | 0.54 | 0.26 | same | BTC Sharpe below buy & hold; nothing left without its best year |
| H4 | H1 trend × H3 sizing (post-hoc) | Gate 1, 2018–2022 | 42.0% | −46.7% | 1.08 | 0.90 | same | Drawdown; no plateau; turnover |
| H5 | H4 at one slow setting (post-hoc ×2) | Gate 2, 2023–2024 (by exception)* | 35.5% | −20.4% | 1.30 | 1.74 | 108.4%, −34.8%, Calmar 3.11 | Calmar far below 1.2×; timing beat only 37% of random runs |
| H6 | Funding-rate crowding filter | Gate 1′, 2020-02 → 2024-12 | 38.3% | −44.5% | 1.20 | 0.86 | 73.8%, −75.4%, Calmar 0.98 | Calmar; drawdown; timing beat only 35% of random runs |

\* H5's Gate 2 row is at modelled costs (0.30% per side), as registered. At Gate 1 (2018–2022, 2× costs) it had
21.9% CAGR, −27.3% drawdown and Calmar 0.80, and missed only the plateau rule, by 0.1 point.

**Variants tested in total: 89.** The 2025-01 → 2026-09 **holdout was never opened.**

## What it showed

- **Every rule cut risk, and none added return through timing.** Each had a smaller drawdown than buy & hold over
  the same period. But the two strictest tests, H5's and H6's random-entry checks, showed the timing did no better
  than chance at the same exposure. The gain came from holding less, which anyone can do without a bot.
- **In rising markets the caution was expensive.** H5 gave up about two-thirds of buy & hold's return in 2023–2024;
  H6 about half over 2020–2024.
- **The pre-registration worked.** It stopped near-misses (H4's other variants, H5's 0.1-point plateau miss) from
  being rescued after the fact, and kept the holdout clean throughout.
- **Data bugs are the biggest silent risk.** A bad Kraken print (2018), and two Bitvavo paging bugs that invented a
  "missing" FTX-day candle (journal #14), were all found by cross-checks, not by results looking wrong.

## What was built

- Data pipeline for Binance, Kraken, Bitvavo and Binance funding rates, with checksums, manifests and a validator.
- A research backtest engine, checked against a hand-worked example, an independent re-implementation and Freqtrade.
- Gate runners that apply registered rules as code (`prescreen`, `gate2`, `h6`).
- Operations tooling for paper trading: a Freqtrade strategy, watchdog, parity check, runbook and fire drills.
- 194 tests, with ruff, mypy and gitleaks in pre-commit.

## Loose ends (yours)

- **Probably nothing to revoke:** the journal records no exchange API key, Telegram token or Healthchecks URL being
  created (#11, #13), and Azure for Students was never activated. If you made any of them yourself since, revoke it.
- **The original working copy**, where the paper bot ran, still holds
  the paper-trading database with its 2 paper positions, the logs, backups and any `config.private.json`. Check it
  for anything private, then delete it. Everything worth keeping is on GitHub.
- **Optional cleanup in this copy** (gitignored): `data/` (51 MB of downloaded market data) and `.venv`.

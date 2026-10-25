# Pre-registration conventions (apply to every hypothesis card)

Status: **REGISTERED 2026-10-19**: approved as written by the project owner, before any strategy was tested. From now
on, changes are allowed only as dated amendments at the bottom of this file, written *before* the next test run.
Git history is the audit trail.

These rules exist so that a strategy's results can't quietly shape how the strategy is judged
(PROJECT_PLAN.md §2.3, §5). Nothing in these cards was informed by looking at strategy returns on our data.

## 1. Data

| Role | Series | Why |
|---|---|---|
| **Primary (pre-screen)** | Kraken **BTC/EUR, ETH/EUR**, 1d | EUR is the currency we trade. Longest clean history: warm-up available long before 2018, so every lookback in the grid starts warmed up on 2018-01-01. |
| Confirmation 1 | Binance **BTC/USDT, ETH/USDT**, 1d | A different venue and quote currency. A real effect shouldn't depend on one exchange. |
| Confirmation 2 | Bitvavo **BTC/EUR, ETH/EUR**, 1d (from 2019-03-08) | The venue the bot will trade. Note the missing candle on 2022-11-09. |
| Robustness | Kraken 4h | Same rule with lookbacks scaled ×6. Informational only, not a gate. |

> **Deviation from PROJECT_PLAN.md §4.2**, approved at registration. The plan said to do discovery on Binance USDT and confirm
> on EUR. Phase 1 showed Kraken EUR has a *longer* clean history than Binance (2013/2015 vs Aug 2017). Using it as
> primary means warm-up never eats into the development period, and we test in the currency we trade.

Clean data comes from `data/clean/` exactly as validated (journal #1). Gaps are not filled: a missing day
simply has no signal update. Positions carry over and are marked at the next available close.

## 2. Periods (from `src/aitradingbot/splits.py`)

- **Pre-screen: development only, 2018-01-01 → 2022-12-31.** Indicators may use earlier data for warm-up; returns
  are counted from 2018-01-01.
- Validation (2023–2024) and the holdout (2025-01 → 2026-09) are **not touched** in Phase 1.

## 3. Execution model

- Signals are computed on the **daily close** (candle open time *t*, closes at *t* + 1 day, 00:00 UTC).
- Orders fill at the **next candle's open**. No same-candle fills, no peeking at the candle being traded.
- Long-only spot, no leverage. Cash earns 0%.
- Each card says how capital is split. Fractional positions are allowed in the pre-screen. The €5 minimum order is
  checked as a feasibility note, not simulated.

## 4. Costs

- **Base: 0.30% per side** = 0.25% Bitvavo taker fee + 0.05% slippage.
- **Pre-screen stress: 0.60% per side (2×).** The pre-screen pass/fail is judged here.
- Also report 0.90% per side (3×), informational. Phase 1 showed Bitvavo dislocating 5–12% from Kraken in violent
  hours, so cost sensitivity matters.
- Costs apply to the traded notional, including partial rebalances.

## 5. Benchmarks

- Each asset vs **its own buy & hold** (bought at the 2018-01-01 open, same costs on the single entry).
- Portfolios vs **50/50 BTC-ETH buy & hold**, not rebalanced (two independent sleeves).

## 6. Metrics (daily equity, marked at each close)

- **CAGR** = (final ÷ initial)^(365 ÷ days) − 1
- **Max drawdown** = largest peak-to-trough fall of daily equity
- **Sharpe** = mean daily return ÷ std of daily return × √365 (risk-free rate 0)
- **Calmar** = CAGR ÷ |max drawdown|
- Also reported: number of round trips, time in market, turnover, and worst calendar year.

## 7. Pre-screen pass rule (Gate 1, PROJECT_PLAN.md §7 Phase 1)

A hypothesis passes only if the **selected variant** (§8) meets **all** of these on development data at **2× costs**:

1. Calmar ≥ **1.2 ×** the benchmark's Calmar *(from the plan)*
2. Max drawdown ≤ **40%** *(added)*
3. CAGR > **0** *(added)*
4. Sharpe ≥ the benchmark's Sharpe *(added)*
5. Criteria 1–4 hold for **BTC and ETH separately**, with the same parameters *(from the plan)*
6. **Plateau:** every immediate grid neighbour of the selected variant also passes 1–3, and has Calmar within 30% of
   the selected variant's *(makes the plan's "stable plateau" testable)*
7. **Not one lucky stretch:** removing the best calendar year keeps CAGR > 0 *(added)*

> **Why criteria 2–4 and 7 were added** (approved at registration). 2018–2022 starts near the 2017 peak and ends in the 2022 bear
> market. Buy & hold had a low CAGR and drawdowns around 75–80%, so its Calmar is tiny. "1.2× buy & hold's Calmar"
> alone could be passed by almost anything that sits in cash for long stretches. The absolute floors stop a weak
> strategy passing just because the benchmark was poor. This reasoning uses public market history only, not
> results computed on our data.

## 8. Variant selection: decided now, so the best-looking number can't be cherry-picked

- Test the **full grid** given in each card; every run counts toward the card's variant cap and goes in the journal.
- Score each variant by the **median Calmar (2× costs, BTC and ETH averaged) of itself and its immediate grid
  neighbours**. Select the variant with the best score. This favours the middle of a plateau over an isolated spike.
- If two variants tie, pick the one with fewer trades (lower cost risk).

## 9. Kill rules (all cards)

- Fails the pass rule → **killed** for this round; record the numbers anyway.
- No retrying with a new grid, unless it's registered as a new hypothesis card, which counts toward the
  3-hypothesis cap in PROJECT_PLAN.md §7.
- A bug found after a run → fix it, re-run the **whole** grid, and note it in the journal. That's not a new variant.

## Amendments

### Amendment 1 — Periods under PROJECT_PLAN.md amendment A3 (registered 2026-10-25)

Applies to cards registered under A3 (H6, H7). H1–H5 and their results are unchanged.

- **Development: 2018-01-01 → 2024-12-31.** The validation split (2023–2024) was spent by H5's Gate 2 (journal
  #12), so it's in-sample from now on. A card whose data starts later says so and uses its own start date.
- **Holdout: 2025-01-01 → 2026-09-30, unchanged.** Opened once, for at most one card, under a holdout file
  registered first (A3 step 5).
- **§2 is replaced** by the two points above. Gate 1′ ("pre-screen") runs on the development period.
- **§7 is unchanged** and is judged on the development period at 2× costs. A3 step 3 adds the in-sample checks
  from PROJECT_PLAN.md §5.4 steps 3–8; each card fixes their exact tests before it is run.
- **§9's cap:** at most 2 new cards under A3, and at most one of them goes to the holdout.
- Multiple testing: the trial count carries on from 67 (journal #12).
- Everything else (data roles, execution model, costs, benchmarks, metrics, variant selection) is unchanged.

### Amendment 2 — Erratum: Bitvavo's 2022-11-09 candle (2026-10-25)

§1's note about "the missing candle on 2022-11-09" is wrong. That candle was dropped by a paging bug in our Bitvavo
ingest, not missing at the exchange (journal #14). Bitvavo 1d data has no gaps. No rule changes.

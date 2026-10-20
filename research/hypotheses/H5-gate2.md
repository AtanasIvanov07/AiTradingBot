# H5 — Gate 2 pre-registration (Phase 2: out-of-sample test)

Status: **REGISTERED.** Date drafted: 2026-10-20. Date registered: 2026-10-20 (approved as written).
Strategy: [H5.md](H5.md), unchanged: H4's rule fixed at N=150, target vol 30%, band 2%, vol lookback 30 days,
10-point rebalance band, 50% sleeves, next-open fills. Shared rules: [_CONVENTIONS.md](_CONVENTIONS.md).
Pass rules: PROJECT_PLAN.md §1.2 (research metrics) and Phase 2 (Gate 2), made exact below **before any 2023+
strategy result is computed**.

> ## ⚠️ Exception: H5 failed Gate 1
>
> H5 missed Gate 1 on one criterion only: the plateau. Its neighbour n=200/30% was 30.10% below, against a 30%
> limit (journal #9). The owner chose to take it into Phase 2 anyway (PROJECT_PLAN.md amendment A2).
> **Consequences:**
> - The Gate 1 record stays "failed". This test happens by exception, and any pass is reported with that label.
> - H5 is the only candidate. If it fails here, PROJECT_PLAN.md Phase 2 says **stop**: no other hypothesis passed
>   Gate 1.
> - Multiple testing: 63 variants so far, plus 4 robustness runs here, for **67**. Reported as a deflated Sharpe
>   ratio.

## What has and hasn't been seen

- **Validation (2023-01 → 2024-12) and holdout (2025-01 → 2026-09):** no strategy return, drawdown or trade has
  been computed on either.
  - Phase 1 ran data-quality checks only (gaps, outliers, bad prints) across all years.
  - The dry-run (from 2026-10-20) and a parity smoke run (from 2026-10-05) used candles from 2025-08 onward only as
    indicator warm-up. One bit leaks from that: H5's trend was "on" for both coins in mid-October 2026, just after
    the holdout ends.
- **General market history** (public knowledge, not our data): BTC and ETH mostly rose in 2023–2024. A cautious,
  often half-invested rule usually lags buy & hold in such a period. This was stated in H5's card before
  registration. **G1 is the criterion most likely to fail.**

## Data, engines and costs

- **Primary:** Kraken EUR daily, validation 2023-01-01 → 2024-12-31. Indicators warm up on the candles before
  2023, as in research.
- **Judge:** the research engine (`aitradingbot.analysis.engine`, the same code as Gate 1).
- **Implementation check:** a Freqtrade backtest of `H5TrendVol` on the same period.
  - It must agree on positions, except differences explained by data gaps (journal #10).
  - Disagreement means **stop and investigate** under the bug-fix rule (conventions §9). It isn't a kill, and
    nothing is re-tuned.
- **Costs:** modelled = **0.30% per side** (conventions §4). Every criterion uses modelled costs, except G3
  (2×, 0.60%). 0.90% is informational.
- **Benchmark:** 50/50 BTC/ETH buy & hold, un-rebalanced, same period and costs (conventions §5).

## Criteria (all must pass on validation)

| # | Criterion (PROJECT_PLAN.md §1.2) | Exact test |
|---|---|---|
| G1 | OOS Calmar ≥ 1.2× benchmark | Portfolio Calmar ≥ 1.2 × 50/50 buy & hold Calmar, 2023–2024 |
| G2 | OOS max drawdown ≤ 35% | Portfolio max drawdown ≤ 35% |
| G3 | OOS net return at 2× costs > 0 | Portfolio CAGR > 0 at 0.60% per side |
| G4 | ±25% parameters keep ≥ 70% of Sharpe | Four one-at-a-time variants: N = 113 and 188; target vol = 22.5% and 37.5%. Each needs Sharpe ≥ 0.7 × H5's validation Sharpe |
| G5 | Beats ≥ 95% of 1,000 random-entry runs | H5's portfolio Calmar > the 95th percentile of 1,000 random strategies (procedure below) |
| G6 | Profitable in ≥ 60% of walk-forward windows | Fixed parameters (no re-optimisation; registered in H5.md). Windows 2023H1, 2023H2, 2024H1, 2024H2; net return > 0 in **≥ 3 of 4** |
| G7 | Bitvavo EUR confirmation (§5.4 step 9) | On Bitvavo EUR, 2023–2024: portfolio CAGR > 0 at 2× costs |

**Sample size (§1.2):**
- Orders (entries, exits, resizes, BTC and ETH together) are counted.
- Below 50, the result is labelled **low confidence**. That was accepted at H5's registration, so it isn't a kill.

## Holdout (opened once, only if G1–G7 all pass)

- 2025-01-01 → 2026-09-30, same engine and costs.
- **Pass:** holdout portfolio return ≥ 0, **and** holdout max drawdown no worse than the **95th-percentile Monte
  Carlo drawdown** from validation (§1.2).
- **Monte Carlo:**
  - circular block bootstrap of H5's validation daily portfolio returns, block length 20 days;
  - 10,000 paths, each as long as the holdout (638 days);
  - fixed seed 20261020;
  - the threshold is the drawdown that 95% of paths stay within.
- If any of G1–G7 fails, the holdout **stays closed** for H5, so it's still clean for any future, genuinely new
  plan.

## Random-entry procedure (G5)

The random strategies have the same trade count, durations and time in market (§1.2: "same trade count and time in
market"). For each asset:
1. Take H5's validation positions. A position is a run of days with exposure > 0; one already open on 2023-01-01
   counts, and so does one still open at the end.
2. Keep the list of holding durations, and H5's average exposure while in a position.
3. A random strategy:
   - takes the same durations in a random order;
   - places them at uniformly random, non-overlapping start days inside 2023–2024;
   - holds a constant exposure equal to that average;
   - runs on the same engine, with the same costs and sleeves.
4. 1,000 runs, fixed seed 20261020. Each run's portfolio Calmar is compared with H5's.

## Decision

- **Gate 2 PASS** = G1–G7 pass **and** the holdout check passes. Then H5 goes to Phase 3 proper (paper trading,
  already running), and then Phase 4 (live €100). That step needs your own API keys and switch-over.
- **Any fail = H5 killed** for good. There's no re-tuning, no new grid, and no second look at the holdout.
- **Bug found after a run:** fix it, re-run everything, and journal it (conventions §9).

## Reported, not criteria

- Per-asset results.
- Binance USDT over 2023–2024.
- 3× costs.
- Deflated Sharpe ratio for 67 trials.
- Monte Carlo 95th-percentile drawdown, used to cross-check the §6.4 risk limits.
- The trade list.
- Freqtrade agreement.
- SOL/EUR, if its data can be added before the run. Otherwise skipped, and it's not added after seeing results.

## Variants

- 1 (H5) plus 4 robustness variants on validation.
- The random-entry and Monte Carlo runs are benchmarks, not variants.

## Decisions at registration (2026-10-20, approved as written)

1. Take H5 into Gate 2 despite the Gate 1 miss (amendment A2).
2. Use the exact tests above, especially G4's four variants, G5's random-entry design, G6's 3 of 4 windows, G7's
   Bitvavo rule, and the holdout's Monte Carlo design.
3. Accept a low-confidence label if there are fewer than 50 orders.

## Result / decision

**❌ KILLED at Gate 2, validation (2026-10-20)**: report [gate2-H5.md](../reports/gate2-H5.md), journal #12.
**The holdout was not opened.**

- At modelled costs, 2023–2024:
  - H5: 35.5% CAGR, −20.4% max drawdown, Sharpe 1.30, Calmar 1.74.
  - 50/50 buy & hold: 108.4%, −34.8%, 1.76, 3.11.
- **Failed G1:** Calmar 1.74 against the required 3.74.
- **Failed G5:** below the random-entry 95th percentile (3.69). H5 beat only 37% of the 1,000 random strategies
  with the same positions and time in market.
- Passed:
  - G2 (20.4% drawdown);
  - G3 (33.2% at 2× costs);
  - G4 (all four ±25% variants);
  - G6 (4 of 4 half-years profitable);
  - G7 (Bitvavo 34.4% at 2× costs).
  - 75 orders, so not low confidence.
- The result was confirmed by an independent re-implementation and by Freqtrade (11 of 11 positions identical).
- Interpretation:
  - H5 halved the drawdown, but in a strongly rising market it gave up about two-thirds of the return.
  - Its in/out timing did no better than chance at the same exposure.
  - Per the decision rule, H5 is killed for good. No other candidate passed Gate 1, so PROJECT_PLAN.md's Phase 2
    kill rule says stop.

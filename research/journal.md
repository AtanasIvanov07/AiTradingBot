# Research journal

Log **every** backtest or analysis run here, including failures and abandoned ideas. The total number of
tests matters: the more variants you try, the more likely the best one is luck (PROJECT_PLAN.md §2.3).

| # | Date | Hypothesis | Strategy / params | Data & period | Costs | Result (key metrics) | Decision / notes |
|---|---|---|---|---|---|---|---|
| 0 | 2026-10-19 | — (pipeline smoke test) | Freqtrade `SampleStrategy` (unmodified template), 5m | Bitvavo BTC/EUR, ETH/EUR, Oct 2026 only | fee 0.25% | 9 trades, −9.15% (market −7.14%), max DD 10.0%, profit factor 0.17 | Proves the toolchain works. Not a strategy test. The data window is deliberately outside every research split (dev/validation/holdout end 2026-09-30). |
| 1 | 2026-10-19 | — (data pipeline) | — | Binance BTC/ETH-USDT, Kraken + Bitvavo BTC/ETH-EUR; 1d/4h/1h | — | 18 series, all pass validation (0 errors); report in `research/reports/data-validation.md` | Phase 1 data foundation. Data-quality stats only; no returns or strategy results computed. |
| 2 | 2026-10-19 | H1 | SMA band filter, 18-variant grid; selected n=50, band=4% | Kraken BTC/ETH-EUR 1d, dev 2018–2022 (+ Binance, Bitvavo, 4h informational) | 0.60%/side | Portfolio 47.3% CAGR, −58.3% DD, Sharpe 0.99 vs 50/50 B&H 8.5%, −87.3%, 0.51 | **KILL**: DD > 40% in all 18 variants; plateau fails. Cumulative variants tested: 18. *Superseded by #5 (data correction #4); decision unchanged.* |
| 3 | 2026-10-19 | H2 | Weekly dual momentum, 15-variant grid; selected lookback=30, buffer=0% | Kraken BTC/ETH-EUR 1d, dev 2018–2022 (+ Binance, Bitvavo, Wednesday informational) | 0.60%/side | 37.0% CAGR, −80.2% DD, Sharpe 0.80 vs 50/50 B&H 8.5%, −87.3%, 0.51 | **KILL**: DD −77% to −88% in all 15 variants; plateau fails; loses to H1 (Calmar 0.46 vs 0.81). Cumulative variants tested: 34 (incl. 1 informational re-run). *Superseded by #6 (data correction #4); decision unchanged.* |
| 4 | 2026-10-19 | — (data correction) | Bad-open cleaning rule | All sources | — | Kraken BTC/EUR + ETH/EUR 2018-01-13 reopening prints (open €20,000 / €700) dropped in 1d/4h/1h, plus a few old hourly prints | Found while cross-checking H3. Bug-fix re-runs of the same grids (#5–#7), not new variants (conventions §9). The first H3 run on bad data is void. |
| 5 | 2026-10-19 | H1 (re-run) | Same 18-variant grid; selected n=50, band=4% | Corrected Kraken data, dev 2018–2022 | 0.60%/side | 47.3% CAGR, −57.2% DD, Sharpe 0.99, Calmar 0.83 vs B&H 8.5%, −87.0%, 0.51 | **KILL** (unchanged): DD > 40% in all variants; plateau fails. |
| 6 | 2026-10-19 | H2 (re-run) | Same 15-variant grid; selected lookback=30, buffer=0% | Corrected Kraken data, dev 2018–2022 | 0.60%/side | 37.0% CAGR, −79.8% DD, Sharpe 0.80 | **KILL** (unchanged): DD, plateau, loses to H1 (0.46 vs 0.83). |
| 7 | 2026-10-19 | H3 | Vol targeting, 12-variant grid; selected target_vol=30%, lookback=60 | Corrected Kraken data, dev 2018–2022 (+ Binance, Bitvavo, 4h informational) | 0.60%/side | 12.5% CAGR, −47.7% DD, Sharpe 0.54, Calmar 0.26 vs B&H 8.5%, −87.0%, 0.51 | **KILL**: BTC Sharpe 0.33 < 0.44; −3.3% CAGR without the best year. Cumulative variants tested: 46. |
| 8 | 2026-10-20 | H4 (post-hoc) | Trend filter × vol sizing, 16-variant grid; selected n=50, target_vol=60% | Kraken BTC/ETH-EUR 1d, dev 2018–2022 (+ Binance, Bitvavo, 4h informational) | 0.60%/side | 42.0% CAGR, −46.7% DD, Sharpe 1.08, Calmar 0.90 vs B&H 8.5%, −87.0%, 0.51 | **KILL**: DD 46.7% > 40% (BTC 54.4%, ETH 45.9%); plateau fails; turnover 940%/yr > 400%. Cumulative variants tested: 62. |
| 9 | 2026-10-20 | H5 (post-hoc ×2) | H4's rule fixed at n=150, target_vol=30%, plus 4 plateau neighbours (1 new: target_vol=20%) | Kraken BTC/ETH-EUR 1d, dev 2018–2022 (+ Binance, Bitvavo, 4h informational) | 0.60%/side | 21.9% CAGR, −27.3% DD, Sharpe 0.99, Calmar 0.80 vs B&H 8.5%, −87.0%, 0.51 | **KILL**: plateau neighbour n=200/30% is 30.1% below (limit 30%). Everything else passed. Both Phase 1 iterations used, so the plan's stop rule is triggered. Cumulative variants tested: 63. |
| 10 | 2026-10-20 | H5 (learning path, amendment A1) | Freqtrade strategy `H5TrendVol` (same rule; no new parameters) | Kraken BTC/ETH-EUR 1d, dev 2018–2022 (+ Bitvavo 2020-04 → 2022) | 0.60%/side | Freqtrade 2.715× vs research engine 2.693× final equity; DD −26.9% vs −27.3%; 23/24 positions identical | **Parity OK** after fixing 2 bugs in the strategy. Not evidence: H5 stays killed. Variants: still 63. |
| 11 | 2026-10-20 | H5 (learning path, A1) | Dry-run `H5TrendVol` + watchdog, parity tool, fire drills | Live Bitvavo data from 2026-10-20 (paper, €100) | Bitvavo fee 0.25% (dry-run) | Bot running on the PC; 2 paper positions; drills D1–D5 passed (1.3–7 s) | **8-week Gate 3 operations clock started.** Operations only; no strategy result. |

## Notes

### #0 — Phase 0 smoke test
- Purpose: check that data download and backtesting work end to end. The result says **nothing** about any edge.
- Why this strategy and period: `SampleStrategy` is unrelated to H1–H4, and October 2026 is outside all research splits. That way, nothing here peeks at the data the real hypotheses will be judged on.
- Commands: `freqtrade download-data --config user_data/config.json --timeframes 5m --timerange 20261001-`, then `freqtrade backtesting --config user_data/config.json --strategy SampleStrategy --timerange 20261002- --fee 0.0025`.
- Bitvavo data download worked (≈5,380 candles per pair, as expected for 18.7 days of 5m candles), despite Freqtrade's "not officially supported" warning.
- One useful observation: total trade volume was €847, so fees at 0.25% were about €2.12, nearly a quarter of the €9.15 loss in 17 days. Fee drag at small size is real (§0.1).

### #1 — Phase 1 data pipeline
- Commands: `python -m aitradingbot.ingest all`, then `python -m aitradingbot.validate --out research/reports/data-validation.md`, then `pytest`.
- Coverage:
  - Binance: 17 Aug 2017 → 30 Sep 2026.
  - Kraken: BTC/EUR from Sep 2013 and ETH/EUR from Aug 2015, both → 30 Sep 2026.
  - Bitvavo: both pairs from **8 Mar 2019** (ETH/EUR 1h only from 16 Nov 2019) to now. Bitvavo can therefore confirm results from 2019 onward, but not the 2018 bear market.
- Data quirks found and handled:
  - **Binance, 9–11 Feb 2018:** after its outage, 43 hourly candles open at :28:14.789 instead of on the hour. They're **dropped** (recorded in the manifest), leaving a visible gap. Snapping them onto the hour would mislabel the period they cover.
  - **Kraken, 11–12 Jan 2018:** a 37-hour gap in 1h data (exchange outage). Kraken's 2013–2015 EUR markets have many no-trade gaps, so gaps are judged only from the Aug 2017 warm-up start (0.1% missing since then).
  - **Bitvavo:** a missing daily candle on 9 Nov 2022 for both pairs, during the FTX crash. Remember this when confirming results on Bitvavo data.
  - **Kraken archives:** the full archive and the 2026Q3 zip agree on every overlapping candle (0 conflicts). Kraken's support page saying the archive ends "30 June 2026" is out of date.
- Cross-source (Bitvavo vs Kraken, EUR):
  - Median close difference is about 0.04%, so the sources agree well.
  - Bitvavo had **large dislocations during extreme moves**: BTC 1h +9.3% vs Kraken (7 Jan 2021), ETH 1h €200.00 vs €228 (16 Feb 2020), several 5–8% on 4 Dec 2021.
  - Implication for Phase 2/3: on Bitvavo, stops and market orders during violent moves can fill far from "fair" prices. Stress-test slippage beyond 0.05% for exits triggered in high-volatility candles.
- Size on disk: ~44 MB in total. Kraken's 9.6 GB archive was read remotely; only the needed CSVs were fetched.

### #2 — H1 pre-screen (Gate 1)
- Command: `python -m aitradingbot.analysis.prescreen H1 --out research/reports/prescreen-H1.md`, run on committed code `accfddf` (7.6 s).
- Decision: **KILL** under the registered rules. Details are in the H1 card and the report.
- Why:
  - **Every** variant's portfolio drawdown was 53.7–73.8%, above the 40% limit.
  - The selected variant's neighbour (n=75, band=4%) has a third of its Calmar, so there's no stable plateau.
- What it still tells us: a plain trend filter roughly doubled Sharpe vs buy & hold and cut the worst drawdown from
  about −87% to about −58%. That fits the "drawdown reduction, not alpha" rationale, but it isn't enough to meet the
  risk bar when the strategy is fully invested while long.
- Bug checks before accepting the result:
  - Buy & hold matches market history (BTC/EUR €11,994 → €15,421, CAGR 5.2% before costs; 2018 drawdowns −80% BTC,
    −94% ETH).
  - An independent vectorised recomputation of BTC n=100, band=0% matched the engine (CAGR 20.28% vs 20.20%, max
    DD −61.98% vs −61.97%).
  - Every trade happens at the open after the signal changed. The one exception is the opening purchase on
    2018-01-01, when the trend was already up.
  - Kraken's daily open equals the previous close to within 0.005% (median), so next-open fills are realistic.
- Multiple-testing count so far: 18 variants (H1).
- Caution for what comes next: any new idea shaped by this result (e.g. "H1 plus volatility sizing" or "shorter
  lookbacks") was suggested by the development data. If registered, it must say so and count toward the
  3-hypothesis cap. Its pre-screen evidence is weaker than for a hypothesis written blind.

### #3 — H2 pre-screen (Gate 1)
- Command: `python -m aitradingbot.analysis.prescreen H2 --out research/reports/prescreen-H2.md`, run on committed code `cde4a78` (10.6 s, including the internal H1 re-run for criterion 5′).
- Decision: **KILL**. Details are in the H2 card and the report.
- Why:
  - Drawdowns of −77% to −88% across the whole grid. The selected variant's −80% is barely better than buy & hold's −87%.
  - No plateau.
  - It loses to H1 on Calmar, so choosing between BTC and ETH added nothing over a simple in-or-out filter.
- Where the drawdown came from:
  - The peak came on 2018-01-14, after riding ETH +77% in two weeks.
  - Through 2018 the 30-day momentum check kept re-entering bear-market rallies and got hit each time. Weekly lag
    plus holding a single asset magnified every loss.
  - Equity bottomed at 0.35 on 2019-03-05.
- Fragility:
  - Moving the rebalance from Sunday to Wednesday changed CAGR from 37.0% to 23.9%.
  - Bitvavo, which starts in 2019-04 and so skips the 2018 bear market, looks far better (84% CAGR, −53% DD). That's
    regime dependence, not confirmation.
- Bug check: an independent re-implementation (my own weekly decisions, close-to-close returns, one cost side for
  cash moves and two for BTC↔ETH switches) matched the engine (CAGR 36.98% vs 37.01%, max DD −80.22% vs −80.15%).
- Multiple-testing count so far: 34 runs (H1 18; H2 15 plus 1 informational Wednesday run).
- Pattern across H1 and H2: strategies that are fully invested whenever they're long don't get under the 40%
  drawdown limit in 2018–2022, whatever the timing signal. H3, which scales exposure down by volatility, is the
  registered test of whether reducing *size* helps where timing didn't. That card was written before either result.

### #4 — Data correction: bad reopening prints (found during the H3 check)
- How it was found:
  - The H3 cross-check didn't match: the engine gave BTC CAGR 7.24%, an independent close-to-close version 5.48%.
  - Diffing the two equity curves pointed at **2018-01-13**: Kraken's first candle after its outage.
  - Its **open was €20,000** (high €20,000). Binance had BTC at about $13,750 (~€11,400) that day.
  - ETH/EUR opened at **€700** (high €1,497) against ~€1,000.
  - The engine fills at opens, so strategies that rebalanced there traded at fantasy prices. The validator *had*
    flagged the candle as an outlier warning, but it was never cross-checked as the plan requires.
- Fix:
  - `drop_bad_opens`: a candle is dropped when its open is more than 25% / 15% / 10% (1d / 4h / 1h) from the
    previous close **and** from its own close. A real move during a no-trade gap opens near its own close and is kept.
  - The validator now treats any such candle as an error. It also errors when a series has no candles in the
    assessed window.
- A mistake on the way, caught before any re-run used it:
  - The first version repeated until stable. Comparing against ever-older closes cascaded through Kraken's gappy
    2013–2015 history and deleted 99.9% of BTC/EUR 1h.
  - The validator didn't notice, because the few remaining rows predated the assessed window. That's now an error.
  - The rule runs in a single pass, and a test covers the cascade case.
- Dropped since 2017-08:
  - Kraken BTC/EUR: 1d 2018-01-13; 4h 2018-01-13 08:00; 1h 2017-08-26 20:00, 2018-01-13 11:00, 2018-04-03 19:00.
  - Kraken ETH/EUR: 1d/4h/1h at the same 2018-01-13 reopening.
  - Binance ETH/USDT: 1h/4h 2017-08-22 04:00.
  - Validation: 0 errors. 30/30 data tests pass.
- Per conventions §9, H1–H3 were re-run on the full grids (#5–#7). These are bug-fix re-runs, not new variants.

### #5–#7 — Gate 1 on corrected data
- Code: fix committed as `087d1d5`. All three reports were generated from that clean revision; an earlier run on the
  uncommitted fix gave identical numbers.
- **H1:** same selected variant, near-identical numbers (DD −58.3% → −57.2%). **KILL** stands.
- **H2:** near-identical numbers (DD −80.2% → −79.8%). **KILL** stands.
- **H3** (first valid run):
  - Selected target_vol=30%, lookback=60. Portfolio 12.5% CAGR, −47.7% DD, Sharpe 0.54, vs 50/50 buy & hold
    8.5%, −87.0%, 0.51.
  - Passes its drawdown rule (−47.7% vs a −65.2% limit), the plateau, and criteria 1, 3 and 4 for the portfolio.
  - Fails **criterion 4 for BTC** (Sharpe 0.33 vs buy & hold 0.44).
  - Fails **criterion 7** (−3.3% CAGR without its best year).
  - Read plainly: volatility targeting *halves the worst loss*, but holding about 40% exposure gives up so much
    upside that BTC's risk-adjusted return falls *below* buy & hold, and almost all the return comes from 2020.
  - The engine now matches the independent calculation (BTC CAGR 5.39% vs 5.48%, DD −49.13% for both).
- **Phase 1 outcome: all three registered hypotheses failed Gate 1.** Cumulative variants tested: 46 (18 + 15 + 1
  informational + 12).
- Next decision (PROJECT_PLAN.md §7, Phase 1 kill/iterate): either register up to 2 new hypotheses and repeat once,
  or stop and DCA. Any new hypothesis is now informed by these results and must say so.

### #8 — H4 pre-screen (Gate 1, post-hoc hypothesis)
- Command: `python -m aitradingbot.analysis.prescreen H4 --out research/reports/prescreen-H4.md`, run on committed code
  `0412937` with a clean tree.
- Decision: **KILL** under the registered rules. Details are in the H4 card and the report.
- Why:
  - **Criterion 2:** the selected variant's drawdown is 46.7% for the portfolio (BTC 54.4%, ETH 45.9%), above the 40%
    limit.
  - **Plateau:** both neighbours (n=100/60%, n=50/50%) also fail the drawdown limit.
  - **Turnover kill:** 940% per year, against a 400% cap.
  - Passed: criteria 1, 3, 4 and 7 (13.9% CAGR without the best year) and the Binance kill check (39.3% CAGR).
- What it still tells us:
  - Combining the two ideas helped on both axes. Sharpe was the best so far (1.08, vs H1's 0.99), and the drawdown was
    smaller than H1's (−46.7% vs −57.2%).
  - It still wasn't enough at the variant the rules selected.
  - Bitvavo (from 2019-04, so no 2018 bear market) made 58.5% CAGR, against 59.6% for buy & hold, with a −53% vs −75%
    drawdown. Kraken 4h is close to 1d (44.6%, −43.9%).
- Bug check: an independent re-implementation matched the engine for the selected variant. It uses its own loops for
  the SMA hysteresis, the rolling std and the sleeve simulation, with no project imports.

  |  | CAGR | Max DD | Turnover |
  |---|---:|---:|---:|
  | Independent re-implementation | 42.0% | −46.7% | 941% |
  | Engine | 42.0% | −46.7% | 940% |

  The per-asset numbers match to 0.1 point, and n=150/30% and n=200/60% match too.
- Where the turnover comes from (selected variant, per year, as a share of average equity):
  - Trend entries 4.0× and exits 4.4×. Volatility resizes add only 1.0×.
  - Over five years that's 50 round trips plus 77 resizes.
  - Cost drag at 0.60% per side is 5.6% of average equity per year.
- **A drafting mistake in the card (mine):**
  - The 400% cap was copied from H3, which is always invested and barely trades (92%/yr).
  - The card's own estimate for H4, 4–10 round trips per asset per year, implies more than 400% from entries and
    exits alone at full sleeve size. So the cap was close to unpassable for the fast-trend variants.
  - Not changed after the fact. It doesn't change the decision, because the drawdown and plateau checks fail on their
    own.
  - Lesson for any later card: check that kill thresholds are consistent with the card's own trade estimate.
- Informational, **not** a decision:
  - 4 of the 16 variants pass criteria 1–5, criterion 7 and the turnover cap on their own: n=100/30%, n=150/30%,
    n=150/40% and n=200/30%. Their plateau and Binance checks weren't evaluated.
  - All four combine the lowest target volatility with a slower trend.
  - The §8 selection rule picks the highest smoothed Calmar, which here sits at the fast, aggressive corner that breaks
    the drawdown limit.
  - Choosing one of the four now would mean picking after seeing the results, which this card doesn't allow.
  - This scan re-evaluated the same 16 variants; it doesn't add variants.
- Phase 1 allowance: H4 used the first of the two new hypotheses, so one is left (PROJECT_PLAN.md §7).
  - Any H5 built on the observation above would be fitted to the development data twice over, so its Gate 1 would carry
    almost no evidence.
  - Only the untouched validation split (2023–2024) could test it.
- Multiple-testing count so far: 62 variants (46 + 16).

### #9 — H5 pre-screen (Gate 1, post-hoc twice over)
- Command: `python -m aitradingbot.analysis.prescreen H5 --out research/reports/prescreen-H5.md`, run on committed code
  `aa077ca` with a clean tree.
- Runs: the fixed variant and its 4 plateau neighbours.
  - The fixed variant and 3 of the neighbours repeat H4 grid runs, with identical numbers.
  - Only n=150/20% is new.
- Decision: **KILL** under the registered rules, on **one criterion only**.
  - **Plateau (criterion 6):** neighbour n=200/30% has an averaged Calmar of 0.4956 (BTC 0.436, ETH 0.555). H5's own
    is 0.7090, so the floor is 0.4963.
  - The neighbour is 30.10% below; the limit is 30%.
  - The card flagged this neighbour as borderline before the run, and committed to not adjusting the rule to fit.
- Everything else passed:
  - criteria 1–5 (portfolio −27.3% DD; BTC −31.5%, ETH −30.3%);
  - criterion 7 (10.1% CAGR without the best year);
  - the Binance kill check (23.7% CAGR, −26.9% DD);
  - turnover (276%/yr).
  - The other three neighbours are within 12% of H5's Calmar. The new one, n=150/20%, made 15.1% CAGR with −20.8% DD
    and an averaged Calmar of 0.69.
- Bug check: the independent re-implementation from #8 matched the fixed variant (CAGR 21.9%, DD −27.3%, Sharpe 0.99,
  turnover 276%; per-asset Calmar 0.649 / 0.770 vs the engine's 0.649 / 0.769).
  - For the failing neighbour it gives an averaged Calmar of 0.4960, i.e. 30.11% below.
  - So both implementations put it on the failing side, by about 0.1 point.
- Informational:
  - Costs barely matter at this turnover: 22.7% CAGR at 1×, 21.6% at 3×.
  - Kraken 4h: 23.8% CAGR, −26.9% DD.
  - Bitvavo, from 2019-08 (mostly a rising market): 21.1% CAGR vs buy & hold's 43.4%, with −34.2% vs −75.4% DD, so
    Calmar 0.62 vs 0.58.
  - That's an early sign of the Gate 2 concern in the card: in a strong rise, this rule keeps the drawdown small but
    makes about half of buy & hold's return.
- What it means:
  - The slow-trend, low-volatility end of the H4 family is the closest any hypothesis came to passing.
  - But the slow side of its plateau is clearly weaker (n=200: BTC Calmar 0.44 vs 0.65), and the result missed by a
    hair.
  - Under pre-registration, a miss by 0.1 point is still a miss. Moving the line now would make every earlier decision
    meaningless.
- **Phase 1 outcome: H1–H5 all killed at Gate 1.** Both allowed iterations (H4, H5) are used.
  - PROJECT_PLAN.md §7 Phase 1: "If those fail too, **stop**. Consider monthly DCA instead, and count the project as
    a learning success."
  - **That rule is now triggered.**
  - The validation split (2023–2024) and the holdout (2025-01 → 2026-09) remain **unopened**.
- Multiple-testing count: 63 variants (62 + 1 new neighbour).

### #10 — Learning path: H5 as a Freqtrade strategy, checked against the research engine
- Context: PROJECT_PLAN.md amendment A1 (learning-only, dry-run only). This checks the *implementation*. It's not a
  test of the strategy, and no validation or holdout data was used: exports were cut at 2022-12-31.
- Strategy: `user_data/strategies/h5_trend_vol.py`. It's self-contained, because the Docker image has no
  `aitradingbot` package.
  - Unit tests in `tests/test_freqtrade_strategy.py` check that its indicators equal
    `h4_trend_vol` / `h1_trend_filter` / `h3_vol_target` exactly, and that they never look ahead.
  - They also check the resize maths.
- Command, with Kraken 1d exported to Freqtrade's format:
  `freqtrade backtesting --strategy H5TrendVol --timeframe 1d --timerange 20171231-20230101 --fee 0.006`, run on a
  €10,000 wallet so that minimum orders don't interfere.
- **Two bugs found in the strategy, both fixed:**
  1. **Sleeve equity double-counted partial-sell gains.** `wallets.get_starting_balance()` already includes open
     trades' realised profit, and the strategy added it again. That overstated equity, so exposure was understated
     and resizes went up. Fix: use the fixed starting capital from the config. The formula now matches an
     independent cash ledger on all 1,692 checks.
  2. **Partial sells were too big.** Freqtrade sells `|stake| × amount / trade.stake_amount`, a share of the *cost
     basis*, not of market value.
     - On 2019-04-03 a cut from 100% to 48% left 38%, and the next day it bought back (double fees).
     - Fix: convert euros of market value into Freqtrade's unit. There's a regression test for it.
  - Before the fixes the backtest showed 25.5% CAGR, then 19.6%; after both it shows 22.1%. **A dry-run with these
    bugs would have traded wrongly without anyone noticing.**
- **Parity after the fixes** (Kraken, 2018–2022):

  |  | Freqtrade | Research engine |
  |---|---:|---:|
  | Final equity | 2.715× | 2.693× |
  | CAGR | 22.1% | 21.9% |
  | Max DD | −26.9% | −27.3% |
  | Sharpe | 1.01 | 0.99 |

  - 23 of 24 positions open and close on the same days. Orders: BTC 56/58 identical, ETH 52/53.
  - The remaining differences:
    - The Kraken 2018-01-12/13 gap: Freqtrade fills missing candles with the previous close. That shifts SMA/vol
      until mid-February 2018 and moves one BTC entry by a day.
    - 3 resizes that sit right at the 10-point threshold.
- **Bitvavo check (2020-04-11 → 2022):** Freqtrade needs 400 startup candles, so it can only start there.
  - Orders are again almost identical (BTC 34/36, ETH 32/33).
  - But final equity differs (2.53× vs 2.26×). The whole gap is **one missing candle on 2022-11-09**, the FTX crash
    day.
    - Freqtrade fills it at the previous close and "sells" both sleeves at the pre-crash price, a fill that couldn't
      have happened.
    - The research engine blocks trading on missing candles and sells the next day.
  - **Lesson: a Freqtrade backtest across missing candles can invent fills.** Check gaps before trusting one.
- Freqtrade's own checks:
  - `lookahead-analysis`: no bias (20 signals).
  - `recursive-analysis`: no indicator variance across startups of 150, 200, 300, 400 and 600 candles.
- €100 wallet on Bitvavo: identical to the €10,000 run. A 10-point resize of a €50 sleeve is ≥ €5, so Bitvavo's
  minimum order is never binding, but it's exactly at the limit.
- Variants: still 63. Same rule, same parameters, and no decision depends on these numbers.

### #11 — Learning path: dry-run started, operations tooling, fire drills
- **Dry-run (paper trading) on the Windows PC since 2026-10-20 18:55 UTC**: `ops\windows\start-dryrun.ps1`.
  - Freqtrade 2026.9, H5TrendVol, Bitvavo market data, €100 paper wallet, market orders. Bitvavo's 0.25% taker fee
    is used by the dry-run.
  - On start the last closed candle (2026-10-19) had BTC target 0.947 and ETH 0.857, so the bot bought both at
    once (€47.37 BTC, €42.85 ETH). In research those entries would have filled at the 2026-10-20 00:00 open. Only
    the first day differs, which is why the parity tool doesn't count bot-start-day orders.
  - Config change for parity with the research engine: market orders (taker, `price_side: other`) instead of
    limit orders at the same side.
- **Watchdog** (`src/aitradingbot/ops/watchdog.py`, every 2 minutes):
  - Triggers:
    - API alive, bot loop running, dry-run mode;
    - stale candles;
    - > 5 errors in 10 min;
    - drawdown 20% / 30%, and daily loss 5%;
    - unexpected positions;
    - price > 3% off Kraken;
    - clock drift.
  - Actions: `/stopentry`, `/forceexit all`, `/stop`. Only the daily-loss pause resumes by itself; everything else
    waits for `--resume` after a written review. There's also an `--emergency` command.
  - Daily report after 08:00, and a daily SQLite backup (14 kept).
  - Equity is `starting capital + profit`, because `/balance` values coins with cached tickers that lag.
- **Weekly parity check** (`src/aitradingbot/ops/parity.py`): downloads fresh Bitvavo candles, backtests the dry-run
  days at the dry-run fee, and matches orders by day, pair and side (value within 5%).
  - It drops the backtest's automatic close on its last candle, and doesn't count bot-start-day orders.
  - A smoke run over 2026-10-05 → 10-19 worked end to end. There were no dry-run orders yet, so it isn't a parity
    result.
- **Fire drills** on a separate drill bot (`ops/fire-drills.md`): D1 manual emergency 2.3 s, D2 drawdown > 30%
  3.1 s, D3 stale data 1.3 s, D4 crash and recovery (API back in 7 s, same trades restored from SQLite), D5
  exchange unreachable (Freqtrade exits; watchdog flags it).
- **Bugs found and fixed while building:**
  - the watchdog crashed when a just-restarted bot had no finished loop yet (found by D4);
  - the Windows start script skipped the watchdog when the bot was already running;
  - the backup left SQLite connections open, so Windows couldn't delete old copies (found by a test);
  - the parity tool counted dry-run orders after its window and the backtest's final forced close.
- **Learned:**
  - Freqtrade locks a pair until the next candle after any exit.
  - ccxt ignores `HTTPS_PROXY`.
  - On Windows nothing restarts a crashed bot.
- **Linux host prepared, not used yet**: `ops/linux/setup-host.sh` (swap, Docker, chrony, unattended upgrades,
  ufw, private config) and a systemd unit for the watchdog.
- Waiting on you: Telegram bot and token, Healthchecks URL, Azure or Oracle VM, and the API-key revocation drill on
  a test key.

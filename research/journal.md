# Research journal

Log **every** backtest or analysis run here, including failures and abandoned ideas. The total number of
tests matters: the more variants you try, the more likely the best one is luck (PROJECT_PLAN.md §2.3).

| # | Date | Hypothesis | Strategy / params | Data & period | Costs | Result (key metrics) | Decision / notes |
|---|---|---|---|---|---|---|---|
| 0 | 2026-10-19 | — (pipeline smoke test) | Freqtrade `SampleStrategy` (unmodified template), 5m | Bitvavo BTC/EUR, ETH/EUR, Oct 2026 only | fee 0.25% | 9 trades, −9.15% (market −7.14%), max DD 10.0%, profit factor 0.17 | Proves the toolchain works. Not a strategy test. The data window is deliberately outside every research split (dev/validation/holdout end 2026-09-30). |
| 1 | 2026-10-19 | — (data pipeline) | — | Binance BTC/ETH-USDT, Kraken + Bitvavo BTC/ETH-EUR; 1d/4h/1h | — | 18 series, all pass validation (0 errors); report in `research/reports/data-validation.md` | Phase 1 data foundation. Data-quality stats only; no returns or strategy results computed. |
| 2 | 2026-10-19 | H1 | SMA band filter, 18-variant grid; selected n=50, band=4% | Kraken BTC/ETH-EUR 1d, dev 2018–2022 (+ Binance, Bitvavo, 4h informational) | 0.60%/side | Portfolio 47.3% CAGR, −58.3% DD, Sharpe 0.99 vs 50/50 B&H 8.5%, −87.3%, 0.51 | **KILL**: DD > 40% in all 18 variants; plateau fails. Cumulative variants tested: 18. |
| 3 | 2026-10-19 | H2 | Weekly dual momentum, 15-variant grid; selected lookback=30, buffer=0% | Kraken BTC/ETH-EUR 1d, dev 2018–2022 (+ Binance, Bitvavo, Wednesday informational) | 0.60%/side | 37.0% CAGR, −80.2% DD, Sharpe 0.80 vs 50/50 B&H 8.5%, −87.3%, 0.51 | **KILL**: DD −77% to −88% in all 15 variants; plateau fails; loses to H1 (Calmar 0.46 vs 0.81). Cumulative variants tested: 34 (incl. 1 informational re-run). |

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

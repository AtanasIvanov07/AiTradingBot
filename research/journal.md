# Research journal

Log **every** backtest or analysis run here, including failures and abandoned ideas. The total number of
tests matters: the more variants you try, the more likely the best one is luck (PROJECT_PLAN.md §2.3).

| # | Date | Hypothesis | Strategy / params | Data & period | Costs | Result (key metrics) | Decision / notes |
|---|---|---|---|---|---|---|---|
| 0 | 2026-10-19 | — (pipeline smoke test) | Freqtrade `SampleStrategy` (unmodified template), 5m | Bitvavo BTC/EUR, ETH/EUR, Oct 2026 only | fee 0.25% | 9 trades, −9.15% (market −7.14%), max DD 10.0%, profit factor 0.17 | Proves the toolchain works. Not a strategy test. The data window is deliberately outside every research split (dev/validation/holdout end 2026-09-30). |

| 1 | 2026-10-19 | — (data pipeline) | — | Binance BTC/ETH-USDT, Kraken + Bitvavo BTC/ETH-EUR; 1d/4h/1h | — | 18 series, all pass validation (0 errors); report in `research/reports/data-validation.md` | Phase 1 data foundation. Data-quality stats only; no returns or strategy results computed. |

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

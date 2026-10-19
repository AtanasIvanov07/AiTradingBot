# Research journal

Log **every** backtest or analysis run here, including failures and abandoned ideas. The total number of
tests matters: the more variants you try, the more likely the best one is luck (PROJECT_PLAN.md §2.3).

| # | Date | Hypothesis | Strategy / params | Data & period | Costs | Result (key metrics) | Decision / notes |
|---|---|---|---|---|---|---|---|
| 0 | 2026-10-19 | — (pipeline smoke test) | Freqtrade `SampleStrategy` (unmodified template), 5m | Bitvavo BTC/EUR, ETH/EUR, Oct 2026 only | fee 0.25% | 9 trades, −9.15% (market −7.14%), max DD 10.0%, profit factor 0.17 | Proves the toolchain works. Not a strategy test. The data window is deliberately outside every research split (dev/validation/holdout end 2026-09-30). |

## Notes

### #0 — Phase 0 smoke test
- Purpose: check that data download and backtesting work end to end. The result says **nothing** about any edge.
- Why this strategy and period: `SampleStrategy` is unrelated to H1–H4, and October 2026 is outside all research splits. That way, nothing here peeks at the data the real hypotheses will be judged on.
- Commands: `freqtrade download-data --config user_data/config.json --timeframes 5m --timerange 20261001-`, then `freqtrade backtesting --config user_data/config.json --strategy SampleStrategy --timerange 20261002- --fee 0.0025`.
- Bitvavo data download worked (≈5,380 candles per pair, as expected for 18.7 days of 5m candles), despite Freqtrade's "not officially supported" warning.
- One useful observation: total trade volume was €847, so fees at 0.25% were about €2.12, nearly a quarter of the €9.15 loss in 17 days. Fee drag at small size is real (§0.1).

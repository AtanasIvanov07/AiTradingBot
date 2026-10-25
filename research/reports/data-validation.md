# Data validation report

Generated 2026-10-25 16:07 UTC. Research period: 2018-01-01 → 2026-09-30. Gaps, outliers and zero-volume candles are assessed from 2017-08-01 (warm-up start), Bitvavo's from 2020-01-01; a series errors if more than 1.0% of candles are missing. Timestamps are candle open times, UTC.

## Summary

| Source | Pair | TF | Rows | First | Last | Research coverage | Missing | Gaps | Outliers | Zero vol | Status |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| binance | BTC/USDT | 1d | 3,332 | 2017-08-17 | 2026-09-30 | full | 0 (0.000%) | 0 | 1 | 0 | ⚠️ warn |
| binance | BTC/USDT | 1h | 79,794 | 2017-08-17 04:00 | 2026-09-30 23:00 | full | 170 (0.213%) | 28 | 19 | 4 | ⚠️ warn |
| binance | BTC/USDT | 4h | 19,974 | 2017-08-17 04:00 | 2026-09-30 20:00 | full | 17 (0.085%) | 9 | 6 | 0 | ⚠️ warn |
| binance | ETH/USDT | 1d | 3,332 | 2017-08-17 | 2026-09-30 | full | 0 (0.000%) | 0 | 6 | 0 | ⚠️ warn |
| binance | ETH/USDT | 1h | 79,793 | 2017-08-17 04:00 | 2026-09-30 23:00 | full | 171 (0.214%) | 29 | 39 | 6 | ⚠️ warn |
| binance | ETH/USDT | 4h | 19,973 | 2017-08-17 04:00 | 2026-09-30 20:00 | full | 18 (0.090%) | 10 | 14 | 0 | ⚠️ warn |
| bitvavo | BTC/EUR | 1d | 2,764 | 2019-03-08 | 2026-09-30 | from 2019-03-08 to 2026-09-30 | 0 (0.000%) | 0 | 1 | 0 | ⚠️ warn |
| bitvavo | BTC/EUR | 1h | 66,143 | 2019-03-08 08:00 | 2026-09-30 23:00 | from 2019-03-08 to 2026-09-30 | 80 (0.135%) | 29 | 22 | 0 | ⚠️ warn |
| bitvavo | BTC/EUR | 4h | 16,581 | 2019-03-08 08:00 | 2026-09-30 20:00 | from 2019-03-08 to 2026-09-30 | 1 (0.007%) | 1 | 7 | 0 | ⚠️ warn |
| bitvavo | ETH/EUR | 1d | 2,764 | 2019-03-08 | 2026-09-30 | from 2019-03-08 to 2026-09-30 | 0 (0.000%) | 0 | 6 | 0 | ⚠️ warn |
| bitvavo | ETH/EUR | 1h | 65,583 | 2019-03-08 10:00 | 2026-09-30 23:00 | from 2019-03-08 to 2026-09-30 | 133 (0.225%) | 70 | 29 | 0 | ⚠️ warn |
| bitvavo | ETH/EUR | 4h | 16,568 | 2019-03-08 08:00 | 2026-09-30 20:00 | from 2019-03-08 to 2026-09-30 | 1 (0.007%) | 1 | 10 | 0 | ⚠️ warn |
| kraken | BTC/EUR | 1d | 4,763 | 2013-09-10 | 2026-09-30 | full | 2 (0.060%) | 1 | 1 | 0 | ⚠️ warn |
| kraken | BTC/EUR | 1h | 113,174 | 2013-09-10 23:00 | 2026-09-30 23:00 | full | 87 (0.108%) | 19 | 21 | 0 | ⚠️ warn |
| kraken | BTC/EUR | 4h | 28,428 | 2013-09-10 20:00 | 2026-09-30 20:00 | full | 12 (0.060%) | 4 | 10 | 0 | ⚠️ warn |
| kraken | ETH/EUR | 1d | 4,072 | 2015-08-07 | 2026-09-30 | full | 1 (0.030%) | 1 | 9 | 0 | ⚠️ warn |
| kraken | ETH/EUR | 1h | 96,677 | 2015-08-07 11:00 | 2026-09-30 23:00 | full | 81 (0.101%) | 20 | 43 | 0 | ⚠️ warn |
| kraken | ETH/EUR | 4h | 24,387 | 2015-08-07 08:00 | 2026-09-30 20:00 | full | 11 (0.055%) | 6 | 18 | 0 | ⚠️ warn |

## Findings

**binance BTC/USDT 1d**
- warning: 1 candles with moves > 25%
- biggest flagged moves: 2020-03-12 (+39.5% close, 8.1% wick)

**binance BTC/USDT 1h**
- warning: 170 missing candles (0.213%) in 28 gaps; largest 75 from 2018-02-08 01:00
- warning: 19 candles with moves > 10%
- warning: 4 candles with zero volume
- largest gaps: 2018-02-08 01:00 (+75), 2018-06-26 02:00 (+10), 2019-05-15 03:00 (+10), 2019-08-15 02:00 (+8), 2017-09-06 16:00 (+7)
- biggest flagged moves: 2020-03-12 10:00 (+18.2% close, 7.7% wick), 2020-03-13 02:00 (+17.4% close, 8.8% wick), 2020-03-12 23:00 (+17.3% close, 8.1% wick), 2017-09-15 12:00 (+14.1% close, 1.2% wick), 2020-03-15 21:00 (+13.8% close, 0.6% wick)

**binance BTC/USDT 4h**
- warning: 17 missing candles (0.085%) in 9 gaps; largest 7 from 2018-02-08 04:00
- warning: 6 candles with moves > 15%
- largest gaps: 2018-02-08 04:00 (+7), 2018-06-26 04:00 (+2), 2019-05-15 04:00 (+2), 2017-09-06 16:00 (+1), 2018-07-04 04:00 (+1)
- biggest flagged moves: 2017-09-15 12:00 (+31.2% close, 0.7% wick), 2020-03-12 20:00 (+20.5% close, 8.1% wick), 2020-03-12 08:00 (+17.9% close, 8.5% wick), 2020-03-13 00:00 (+7.7% close, 21.2% wick), 2021-05-19 12:00 (+3.6% close, 19.6% wick)

**binance ETH/USDT 1d**
- warning: 6 candles with moves > 25%
- biggest flagged moves: 2020-03-12 (+44.6% close, 6.1% wick), 2021-05-19 (+27.7% close, 22.6% wick), 2021-05-24 (+26.3% close, 1.0% wick), 2021-01-03 (+26.3% close, 3.4% wick), 2017-08-22 (+4.2% close, 53.5% wick)

**binance ETH/USDT 1h**
- warning: 171 missing candles (0.214%) in 29 gaps; largest 75 from 2018-02-08 01:00
- warning: 39 candles with moves > 10%
- warning: 6 candles with zero volume
- largest gaps: 2018-02-08 01:00 (+75), 2018-06-26 02:00 (+10), 2019-05-15 03:00 (+10), 2019-08-15 02:00 (+8), 2017-09-06 16:00 (+7)
- biggest flagged moves: 2020-03-12 10:00 (+20.9% close, 6.0% wick), 2017-09-15 14:00 (+18.1% close, 1.8% wick), 2017-09-04 07:00 (+17.5% close, 1.7% wick), 2018-01-17 16:00 (+15.3% close, 0.2% wick), 2020-03-12 23:00 (+15.3% close, 6.1% wick)

**binance ETH/USDT 4h**
- warning: 18 missing candles (0.090%) in 10 gaps; largest 7 from 2018-02-08 04:00
- warning: 14 candles with moves > 15%
- largest gaps: 2018-02-08 04:00 (+7), 2018-06-26 04:00 (+2), 2019-05-15 04:00 (+2), 2017-08-22 04:00 (+1), 2017-09-06 16:00 (+1)
- biggest flagged moves: 2017-09-15 12:00 (+31.6% close, 3.3% wick), 2020-03-12 20:00 (+22.1% close, 6.1% wick), 2020-03-12 08:00 (+20.4% close, 9.9% wick), 2018-02-06 12:00 (+17.1% close, 2.4% wick), 2017-09-04 04:00 (+16.6% close, 2.9% wick)

**bitvavo BTC/EUR 1d**
- warning: 1 candles since 2020-01-01 with moves > 25%
- biggest flagged moves: 2020-03-12 (+38.0% close, 3.8% wick)

**bitvavo BTC/EUR 1h**
- warning: 105 missing candles before 2020-01-01 (not used for research)
- warning: 80 missing candles since 2020-01-01 (0.135%) in 29 gaps; largest 6 from 2023-07-23 01:00
- warning: 22 candles since 2020-01-01 with moves > 10%
- largest gaps: 2023-07-23 01:00 (+6), 2025-01-19 01:00 (+5), 2025-04-23 00:00 (+5), 2023-11-14 13:00 (+4), 2024-12-15 02:00 (+4)
- biggest flagged moves: 2020-03-13 02:00 (+18.8% close, 9.0% wick), 2020-03-12 23:00 (+16.0% close, 3.8% wick), 2020-03-15 21:00 (+13.8% close, 2.9% wick), 2020-03-12 10:00 (+13.7% close, 8.6% wick), 2021-05-19 12:00 (+12.4% close, 9.7% wick)

**bitvavo BTC/EUR 4h**
- warning: 1 missing candles since 2020-01-01 (0.007%) in 1 gaps; largest 1 from 2025-04-23 00:00
- warning: 7 candles since 2020-01-01 with moves > 15%
- largest gaps: 2025-04-23 00:00 (+1)
- biggest flagged moves: 2020-03-12 20:00 (+19.2% close, 3.8% wick), 2020-03-12 08:00 (+17.8% close, 4.5% wick), 2020-03-13 00:00 (+8.9% close, 19.0% wick), 2021-01-10 20:00 (+4.0% close, 15.4% wick), 2021-05-19 12:00 (+2.6% close, 21.4% wick)

**bitvavo ETH/EUR 1d**
- warning: 6 candles since 2020-01-01 with moves > 25%
- biggest flagged moves: 2020-03-12 (+43.6% close, 5.3% wick), 2021-05-19 (+27.4% close, 30.3% wick), 2020-03-13 (+25.8% close, 17.4% wick), 2021-05-24 (+25.7% close, 1.2% wick), 2021-01-03 (+25.1% close, 4.1% wick)

**bitvavo ETH/EUR 1h**
- warning: 610 missing candles before 2020-01-01 (not used for research)
- warning: 133 missing candles since 2020-01-01 (0.225%) in 70 gaps; largest 6 from 2023-07-23 01:00
- warning: 29 candles since 2020-01-01 with moves > 10%
- largest gaps: 2023-07-23 01:00 (+6), 2025-01-19 01:00 (+5), 2025-04-23 00:00 (+5), 2023-11-14 13:00 (+4), 2024-03-03 01:00 (+4)
- biggest flagged moves: 2020-03-12 10:00 (+19.5% close, 5.0% wick), 2020-03-13 03:00 (+17.0% close, 8.6% wick), 2020-02-16 16:00 (+16.5% close, 0.9% wick), 2020-02-16 17:00 (+15.9% close, 0.9% wick), 2021-05-19 12:00 (+15.0% close, 25.7% wick)

**bitvavo ETH/EUR 4h**
- warning: 13 missing candles before 2020-01-01 (not used for research)
- warning: 1 missing candles since 2020-01-01 (0.007%) in 1 gaps; largest 1 from 2025-04-23 00:00
- warning: 10 candles since 2020-01-01 with moves > 15%
- largest gaps: 2025-04-23 00:00 (+1)
- biggest flagged moves: 2020-03-12 20:00 (+21.1% close, 5.3% wick), 2020-03-13 00:00 (+20.9% close, 17.4% wick), 2020-03-12 08:00 (+20.6% close, 7.0% wick), 2021-05-19 08:00 (+9.2% close, 21.1% wick), 2021-09-07 12:00 (+7.0% close, 23.5% wick)

**kraken BTC/EUR 1d**
- warning: 4 missing candles before 2017-08-01 (not used for research)
- warning: 2 missing candles since 2017-08-01 (0.060%) in 1 gaps; largest 2 from 2018-01-12 00:00
- warning: 1 candles since 2017-08-01 with moves > 25%
- largest gaps: 2018-01-12 (+2)
- biggest flagged moves: 2020-03-12 (+37.7% close, 4.4% wick)

**kraken BTC/EUR 1h**
- warning: 1172 missing candles before 2017-08-01 (not used for research)
- warning: 87 missing candles since 2017-08-01 (0.108%) in 19 gaps; largest 40 from 2018-01-11 22:00
- warning: 21 candles since 2017-08-01 with moves > 10%
- largest gaps: 2018-01-11 22:00 (+40), 2018-01-11 07:00 (+5), 2018-01-11 13:00 (+5), 2024-04-14 04:00 (+5), 2025-11-01 16:00 (+5)
- biggest flagged moves: 2020-03-13 02:00 (+17.8% close, 9.0% wick), 2020-03-12 10:00 (+15.9% close, 8.1% wick), 2020-03-12 23:00 (+15.4% close, 4.4% wick), 2021-01-02 20:00 (+15.0% close, 3.6% wick), 2017-09-15 12:00 (+13.8% close, 2.1% wick)

**kraken BTC/EUR 4h**
- warning: 169 missing candles before 2017-08-01 (not used for research)
- warning: 12 missing candles since 2017-08-01 (0.060%) in 4 gaps; largest 9 from 2018-01-12 00:00
- warning: 10 candles since 2017-08-01 with moves > 15%
- largest gaps: 2018-01-12 00:00 (+9), 2018-01-11 08:00 (+1), 2024-04-14 04:00 (+1), 2025-11-01 16:00 (+1)
- biggest flagged moves: 2017-09-15 12:00 (+26.2% close, 2.4% wick), 2020-03-12 20:00 (+18.7% close, 4.4% wick), 2020-03-12 08:00 (+17.6% close, 6.3% wick), 2018-02-06 12:00 (+16.5% close, 2.9% wick), 2017-12-22 04:00 (+10.6% close, 15.1% wick)

**kraken ETH/EUR 1d**
- warning: 1 missing candles since 2017-08-01 (0.030%) in 1 gaps; largest 1 from 2018-01-13 00:00
- warning: 9 candles since 2017-08-01 with moves > 25%
- largest gaps: 2018-01-13 (+1)
- biggest flagged moves: 2020-03-12 (+43.4% close, 6.5% wick), 2021-05-19 (+27.4% close, 22.0% wick), 2021-05-24 (+25.7% close, 1.3% wick), 2020-03-13 (+25.2% close, 17.6% wick), 2017-12-22 (+11.7% close, 28.3% wick)

**kraken ETH/EUR 1h**
- warning: 983 missing candles before 2017-08-01 (not used for research)
- warning: 81 missing candles since 2017-08-01 (0.101%) in 20 gaps; largest 19 from 2018-01-12 19:00
- warning: 43 candles since 2017-08-01 with moves > 10%
- largest gaps: 2018-01-12 19:00 (+19), 2018-01-12 04:00 (+14), 2018-01-11 07:00 (+5), 2024-01-20 16:00 (+5), 2024-04-14 04:00 (+5)
- biggest flagged moves: 2020-03-12 10:00 (+18.4% close, 5.1% wick), 2018-01-17 16:00 (+18.1% close, 2.3% wick), 2020-03-13 02:00 (+17.0% close, 8.2% wick), 2017-09-15 12:00 (+16.6% close, 0.9% wick), 2018-02-02 13:00 (+15.3% close, 1.5% wick)

**kraken ETH/EUR 4h**
- warning: 38 missing candles before 2017-08-01 (not used for research)
- warning: 11 missing candles since 2017-08-01 (0.055%) in 6 gaps; largest 4 from 2018-01-12 20:00
- warning: 18 candles since 2017-08-01 with moves > 15%
- largest gaps: 2018-01-12 20:00 (+4), 2018-01-12 04:00 (+3), 2018-01-11 08:00 (+1), 2024-01-20 16:00 (+1), 2024-04-14 04:00 (+1)
- biggest flagged moves: 2017-09-15 12:00 (+29.4% close, 4.3% wick), 2018-02-06 12:00 (+24.5% close, 5.2% wick), 2020-03-13 00:00 (+21.2% close, 17.6% wick), 2020-03-12 20:00 (+21.0% close, 6.5% wick), 2018-02-02 12:00 (+20.8% close, 9.1% wick)

## Cross-source checks

Closes of the same pair and timeframe from different sources (tolerance 0.5%).

| Pair | TF | Sources | Common candles | Median diff | p99 diff | Max diff | Share > tolerance |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| BTC/EUR | 1d | bitvavo vs kraken | 2,764 | 0.038% | 0.417% | 3.98% | 0.83% |
| BTC/EUR | 1h | bitvavo vs kraken | 66,111 | 0.034% | 0.378% | 9.35% | 0.66% |
| BTC/EUR | 4h | bitvavo vs kraken | 16,579 | 0.035% | 0.378% | 5.42% | 0.70% |
| ETH/EUR | 1d | bitvavo vs kraken | 2,764 | 0.047% | 0.824% | 2.08% | 2.28% |
| ETH/EUR | 1h | bitvavo vs kraken | 65,550 | 0.042% | 0.613% | 12.30% | 1.40% |
| ETH/EUR | 4h | bitvavo vs kraken | 16,565 | 0.043% | 0.660% | 5.16% | 1.68% |

Largest disagreements (worth a look; often one venue dislocating):

- BTC/EUR 1d (bitvavo vs kraken): 2019-07-14 (9079.6 vs 9456.1, 4.0%), 2021-01-03 (26907 vs 25938.5, 3.7%), 2024-05-20 (64186 vs 65485.6, 2.0%)
- BTC/EUR 1h (bitvavo vs kraken): 2021-01-07 18:00 (32382 vs 29614.3, 9.3%), 2021-12-04 16:00 (45950 vs 42474.2, 8.2%), 2021-01-02 20:00 (24500 vs 22705.5, 7.9%)
- BTC/EUR 4h (bitvavo vs kraken): 2021-01-04 04:00 (26143 vs 24800, 5.4%), 2021-12-04 12:00 (44965 vs 42820.4, 5.0%), 2021-12-04 16:00 (45732 vs 43749.3, 4.5%)
- ETH/EUR 1d (bitvavo vs kraken): 2019-07-15 (207.18 vs 202.96, 2.1%), 2019-07-23 (194.05 vs 190.28, 2.0%), 2019-05-31 (235.77 vs 239.83, 1.7%)
- ETH/EUR 1h (bitvavo vs kraken): 2020-02-16 16:00 (200 vs 228.06, 12.3%), 2020-02-17 21:00 (218 vs 240.3, 9.3%), 2021-12-04 16:00 (3748.7 vs 3538.99, 5.9%)
- ETH/EUR 4h (bitvavo vs kraken): 2021-01-04 04:00 (851.03 vs 809.29, 5.2%), 2021-12-04 12:00 (3744 vs 3587.39, 4.4%), 2021-01-04 00:00 (831.59 vs 799.9, 4.0%)

## Funding rates (H6 signal)

Binance USD-M perpetual settlements. Coverage is checked from 2020-01-01 (archive start) to 2026-09-30. Rates are per settlement.

| Symbol | Settlements | First | Last | Coverage | Missing | Extreme | Max |rate| | Status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | 7,395 | 2020-01-01 00:00 | 2026-09-30 16:00 | full | 0 (0.000%) | 0 | 0.3000% | ✅ ok |
| ETHUSDT | 7,395 | 2020-01-01 00:00 | 2026-09-30 16:00 | full | 0 (0.000%) | 5 | 0.3750% | ⚠️ warn |

**ETHUSDT**
- warning: 5 settlements beyond ±0.3%

**Overall: no errors**

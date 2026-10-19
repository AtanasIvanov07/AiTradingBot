# Pre-screen H2: Weekly dual-momentum rotation BTC / ETH / EUR

Generated 2026-10-19 20:58 UTC from code `087d1d5`. Rules: [research/hypotheses/H2.md](../hypotheses/H2.md) and [_CONVENTIONS.md](../hypotheses/_CONVENTIONS.md).

Primary data: kraken 1d, development split 2018-01-01 → 2022-12-31. Judged at **0.60% per side** (2× costs). Variants tested: **15** (cap 20).

## Decision: ❌ KILL

## Benchmarks (buy & hold, 2× costs)

| Series | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BTC | 5.0% | -80.3% | 0.44 | 0.06 | -73.2% | 0 | 100% | 0.1× |
| ETH | 11.6% | -93.4% | 0.61 | 0.12 | -82.1% | 0 | 100% | 0.1× |
| 50/50 | 8.5% | -87.0% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |

## Grid (2× costs)

Selection score = median Calmar of the variant and its grid neighbours (BTC/ETH-averaged for sleeve strategies).

| Variant | Score | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| lookback=30, buffer=0% ⬅ selected | 0.41 | 37.0% | -79.8% | 0.80 | 0.46 | -54.7% | 44 | 60% | 15.9× |
| lookback=30, buffer=5% | 0.39 | 32.9% | -79.8% | 0.76 | 0.41 | -54.7% | 43 | 60% | 15.2× |
| lookback=30, buffer=10% | 0.37 | 29.2% | -79.8% | 0.72 | 0.37 | -54.7% | 43 | 60% | 15.2× |
| lookback=60, buffer=0% | 0.19 | 12.4% | -78.4% | 0.54 | 0.16 | -61.5% | 36 | 60% | 14.4× |
| lookback=60, buffer=5% | 0.16 | 10.8% | -78.4% | 0.52 | 0.14 | -61.5% | 34 | 60% | 12.4× |
| lookback=60, buffer=10% | 0.18 | 8.7% | -78.4% | 0.49 | 0.11 | -61.5% | 31 | 60% | 11.4× |
| lookback=90, buffer=0% | 0.19 | 16.9% | -77.4% | 0.59 | 0.22 | -63.3% | 23 | 58% | 7.7× |
| lookback=90, buffer=5% | 0.22 | 17.4% | -76.9% | 0.59 | 0.23 | -63.3% | 22 | 58% | 7.0× |
| lookback=90, buffer=10% | 0.17 | 17.4% | -76.9% | 0.59 | 0.23 | -63.3% | 22 | 58% | 7.0× |
| lookback=120, buffer=0% | 0.13 | 5.9% | -88.2% | 0.46 | 0.07 | -85.6% | 23 | 57% | 8.7× |
| lookback=120, buffer=5% | 0.10 | 8.6% | -87.6% | 0.49 | 0.10 | -83.2% | 20 | 57% | 7.7× |
| lookback=120, buffer=10% | 0.13 | 5.8% | -87.6% | 0.45 | 0.07 | -83.2% | 18 | 57% | 5.8× |
| lookback=180, buffer=0% | 0.16 | 13.8% | -88.4% | 0.56 | 0.16 | -65.8% | 19 | 60% | 7.9× |
| lookback=180, buffer=5% | 0.16 | 15.5% | -87.3% | 0.58 | 0.18 | -62.7% | 17 | 60% | 7.5× |
| lookback=180, buffer=10% | 0.16 | 14.3% | -87.3% | 0.56 | 0.16 | -62.7% | 15 | 60% | 6.5× |

## Pass rule for lookback=30, buffer=0%

| Criterion | Result | Detail |
| --- | --- | --- |
| 1 Calmar ≥ 1.2× benchmark (portfolio) | ✅ | 0.46 vs 1.2 × 0.10 = 0.12 |
| 2 Max drawdown ≤ 40% (portfolio) | ❌ | 79.8% |
| 3 CAGR > 0 (portfolio) | ✅ | 37.0% |
| 4 Sharpe ≥ benchmark (portfolio) | ✅ | 0.80 vs 0.51 |
| 6 Plateau: neighbour lookback=60, buffer=0% | ❌ | Calmar 0.16 vs selected 0.46; fails: 2 Max drawdown ≤ 40% (portfolio) |
| 6 Plateau: neighbour lookback=30, buffer=5% | ❌ | Calmar 0.41 vs selected 0.46; fails: 2 Max drawdown ≤ 40% (portfolio) |
| 7 CAGR > 0 without the best calendar year | ✅ | 6.1% |
| 5′ Calmar beats H1's selected variant | ❌ | 0.46 vs H1 (n=50, band=4%) 0.83 |
| H2 kill: ≤ 60% of profit from one holding period | ✅ | 43% |

## Informational (not part of the decision unless a kill rule above uses it)

| Run | Series | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Primary at 0.30%/side | strategy | 44.4% | -78.5% | 0.88 | 0.57 | -52.3% | 44 | 60% | 15.9× |
| Primary at 0.30%/side | 50/50 buy & hold | 8.6% | -87.0% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |
| Primary at 0.90%/side | strategy | 30.0% | -80.9% | 0.73 | 0.37 | -56.9% | 44 | 60% | 16.0× |
| Primary at 0.90%/side | 50/50 buy & hold | 8.5% | -87.0% | 0.51 | 0.10 | -77.7% | 0 | 100% | 0.1× |
| Binance USDT (confirmation 1) | strategy | 37.2% | -80.9% | 0.80 | 0.46 | -53.8% | 43 | 61% | 15.4× |
| Binance USDT (confirmation 1) | 50/50 buy & hold | 7.1% | -88.1% | 0.50 | 0.08 | -77.7% | 0 | 100% | 0.1× |
| Bitvavo EUR (confirmation 2) | strategy | 83.9% | -53.4% | 1.24 | 1.57 | -17.1% | 33 | 64% | 15.9× |
| Bitvavo EUR (confirmation 2) | 50/50 buy & hold | 55.2% | -74.5% | 0.96 | 0.74 | -64.5% | 0 | 100% | 0.0× |
| Wednesday rebalance (robustness) | strategy | 23.9% | -76.7% | 0.66 | 0.31 | -53.6% | 49 | 59% | 19.2× |
| Wednesday rebalance (robustness) | 50/50 buy & hold | 8.5% | -87.0% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |

- Bitvavo EUR (confirmation 2): evaluated from 2019-04-08 (data starts later)

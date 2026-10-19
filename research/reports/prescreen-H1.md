# Pre-screen H1: Daily trend following (SMA filter with band)

Generated 2026-10-19 19:40 UTC from code `accfddf`. Rules: [research/hypotheses/H1.md](../hypotheses/H1.md) and [_CONVENTIONS.md](../hypotheses/_CONVENTIONS.md).

Primary data: kraken 1d, development split 2018-01-01 → 2022-12-31. Judged at **0.60% per side** (2× costs). Variants tested: **18** (cap 20).

## Decision: ❌ KILL

## Benchmarks (buy & hold, 2× costs)

| Series | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BTC | 5.0% | -80.3% | 0.44 | 0.06 | -73.2% | 0 | 100% | 0.1× |
| ETH | 11.6% | -93.6% | 0.61 | 0.12 | -82.1% | 0 | 100% | 0.1× |
| 50/50 | 8.5% | -87.3% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |

## Grid (2× costs)

Selection score = median Calmar of the variant and its grid neighbours (BTC/ETH-averaged for sleeve strategies).

| Variant | Score | BTC Calmar | ETH Calmar | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| n=50, band=0% | 0.67 | 0.74 | 0.61 | 42.3% | -58.5% | 0.94 | 0.72 | -45.1% | 97 | 56% | 19.0× |
| n=50, band=2% | 0.70 | 0.96 | 0.92 | 56.3% | -53.7% | 1.11 | 1.05 | -33.7% | 50 | 55% | 10.7× |
| n=50, band=4% ⬅ selected | 0.73 | 0.50 | 0.97 | 47.3% | -58.3% | 0.99 | 0.81 | -31.1% | 40 | 55% | 8.0× |
| n=75, band=0% | 0.36 | 0.18 | 0.40 | 22.4% | -64.9% | 0.65 | 0.35 | -45.9% | 91 | 57% | 17.9× |
| n=75, band=2% | 0.37 | 0.45 | 0.36 | 27.3% | -66.0% | 0.73 | 0.41 | -48.2% | 44 | 57% | 9.8× |
| n=75, band=4% | 0.47 | 0.28 | 0.19 | 16.6% | -69.6% | 0.56 | 0.24 | -52.0% | 37 | 57% | 8.1× |
| n=100, band=0% | 0.34 | 0.33 | 0.30 | 21.1% | -63.8% | 0.63 | 0.33 | -47.8% | 66 | 58% | 13.1× |
| n=100, band=2% | 0.41 | 0.46 | 0.28 | 24.5% | -64.4% | 0.68 | 0.38 | -47.7% | 34 | 58% | 7.3× |
| n=100, band=4% | 0.45 | 0.58 | 0.46 | 34.2% | -62.0% | 0.82 | 0.55 | -44.1% | 21 | 57% | 3.9× |
| n=125, band=0% | 0.36 | 0.42 | 0.29 | 24.2% | -59.9% | 0.68 | 0.40 | -48.1% | 54 | 55% | 10.7× |
| n=125, band=2% | 0.40 | 0.63 | 0.33 | 30.6% | -57.9% | 0.77 | 0.53 | -41.6% | 29 | 54% | 5.5× |
| n=125, band=4% | 0.50 | 0.67 | 0.43 | 34.1% | -58.5% | 0.82 | 0.58 | -36.1% | 19 | 55% | 3.8× |
| n=150, band=0% | 0.36 | 0.35 | 0.37 | 25.7% | -64.4% | 0.70 | 0.40 | -41.8% | 44 | 52% | 8.3× |
| n=150, band=2% | 0.40 | 0.38 | 0.42 | 28.5% | -63.1% | 0.74 | 0.45 | -42.5% | 24 | 52% | 4.2× |
| n=150, band=4% | 0.43 | 0.38 | 0.52 | 32.8% | -66.4% | 0.79 | 0.49 | -47.6% | 17 | 51% | 2.8× |
| n=200, band=0% | 0.27 | 0.09 | 0.44 | 23.8% | -66.8% | 0.67 | 0.36 | -40.7% | 38 | 53% | 6.3× |
| n=200, band=2% | 0.27 | 0.11 | 0.30 | 18.0% | -73.8% | 0.58 | 0.24 | -51.5% | 22 | 53% | 3.8× |
| n=200, band=4% | 0.26 | 0.15 | 0.38 | 22.6% | -70.9% | 0.65 | 0.32 | -47.0% | 16 | 53% | 2.6× |

## Pass rule for n=50, band=4%

| Criterion | Result | Detail |
| --- | --- | --- |
| 1 Calmar ≥ 1.2× benchmark (portfolio) | ✅ | 0.81 vs 1.2 × 0.10 = 0.12 |
| 2 Max drawdown ≤ 40% (portfolio) | ❌ | 58.3% |
| 3 CAGR > 0 (portfolio) | ✅ | 47.3% |
| 4 Sharpe ≥ benchmark (portfolio) | ✅ | 0.99 vs 0.51 |
| 1 Calmar ≥ 1.2× benchmark (BTC) | ✅ | 0.50 vs 1.2 × 0.06 = 0.08 |
| 2 Max drawdown ≤ 40% (BTC) | ❌ | 63.1% |
| 3 CAGR > 0 (BTC) | ✅ | 31.5% |
| 4 Sharpe ≥ benchmark (BTC) | ✅ | 0.82 vs 0.44 |
| 1 Calmar ≥ 1.2× benchmark (ETH) | ✅ | 0.97 vs 1.2 × 0.12 = 0.15 |
| 2 Max drawdown ≤ 40% (ETH) | ❌ | 60.0% |
| 3 CAGR > 0 (ETH) | ✅ | 58.3% |
| 4 Sharpe ≥ benchmark (ETH) | ✅ | 1.03 vs 0.61 |
| 6 Plateau: neighbour n=75, band=4% | ❌ | Calmar 0.23 vs selected 0.73; fails: 2 Max drawdown ≤ 40% (portfolio), 2 Max drawdown ≤ 40% (BTC), 2 Max drawdown ≤ 40% (ETH) |
| 6 Plateau: neighbour n=50, band=2% | ❌ | Calmar 0.94 vs selected 0.73; fails: 2 Max drawdown ≤ 40% (portfolio), 2 Max drawdown ≤ 40% (BTC), 2 Max drawdown ≤ 40% (ETH) |
| 7 CAGR > 0 without the best calendar year | ✅ | 17.6% |
| H1 kill: not the fastest corner (n=50, band=0%) | ✅ | n=50, band=4% |
| H1 kill: CAGR > 0 at 2× costs on Binance USDT too | ✅ | 41.8% |

## Informational (not part of the decision unless a kill rule above uses it)

| Run | Series | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Primary at 0.30%/side | strategy | 50.9% | -57.1% | 1.03 | 0.89 | -29.1% | 40 | 55% | 8.0× |
| Primary at 0.30%/side | 50/50 buy & hold | 8.6% | -87.3% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |
| Primary at 0.90%/side | strategy | 43.8% | -59.5% | 0.94 | 0.74 | -33.0% | 40 | 55% | 8.0× |
| Primary at 0.90%/side | 50/50 buy & hold | 8.5% | -87.3% | 0.51 | 0.10 | -77.7% | 0 | 100% | 0.1× |
| Binance USDT (confirmation 1) | strategy | 41.8% | -57.8% | 0.91 | 0.72 | -44.6% | 40 | 54% | 7.7× |
| Binance USDT (confirmation 1) | 50/50 buy & hold | 7.1% | -88.1% | 0.50 | 0.08 | -77.7% | 0 | 100% | 0.1× |
| Bitvavo EUR (confirmation 2) | strategy | 70.7% | -52.7% | 1.25 | 1.34 | -42.5% | 30 | 60% | 7.9× |
| Bitvavo EUR (confirmation 2) | 50/50 buy & hold | 59.6% | -74.7% | 0.99 | 0.80 | -64.6% | 0 | 100% | 0.0× |
| Kraken 4h (robustness) | strategy | 52.0% | -60.2% | 1.06 | 0.86 | -34.6% | 42 | 56% | 8.1× |
| Kraken 4h (robustness) | 50/50 buy & hold | 8.5% | -87.6% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |

- Bitvavo EUR (confirmation 2): evaluated from 2019-04-28 (data starts later)

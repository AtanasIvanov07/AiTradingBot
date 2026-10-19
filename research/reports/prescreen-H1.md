# Pre-screen H1: Daily trend following (SMA filter with band)

Generated 2026-10-19 20:58 UTC from code `087d1d5`. Rules: [research/hypotheses/H1.md](../hypotheses/H1.md) and [_CONVENTIONS.md](../hypotheses/_CONVENTIONS.md).

Primary data: kraken 1d, development split 2018-01-01 → 2022-12-31. Judged at **0.60% per side** (2× costs). Variants tested: **18** (cap 20).

## Decision: ❌ KILL

## Benchmarks (buy & hold, 2× costs)

| Series | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BTC | 5.0% | -80.3% | 0.44 | 0.06 | -73.2% | 0 | 100% | 0.1× |
| ETH | 11.6% | -93.4% | 0.61 | 0.12 | -82.1% | 0 | 100% | 0.1× |
| 50/50 | 8.5% | -87.0% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |

## Grid (2× costs)

Selection score = median Calmar of the variant and its grid neighbours (BTC/ETH-averaged for sleeve strategies).

| Variant | Score | BTC Calmar | ETH Calmar | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| n=50, band=0% | 0.55 | 0.49 | 0.62 | 35.6% | -60.4% | 0.85 | 0.59 | -43.5% | 97 | 56% | 18.9× |
| n=50, band=2% | 0.65 | 0.68 | 0.93 | 50.2% | -56.2% | 1.03 | 0.89 | -31.0% | 50 | 55% | 11.0× |
| n=50, band=4% ⬅ selected | 0.74 | 0.50 | 0.98 | 47.3% | -57.2% | 0.99 | 0.83 | -31.1% | 40 | 55% | 8.0× |
| n=75, band=0% | 0.33 | 0.18 | 0.40 | 22.4% | -64.0% | 0.65 | 0.35 | -45.9% | 91 | 57% | 17.9× |
| n=75, band=2% | 0.37 | 0.40 | 0.34 | 25.4% | -67.9% | 0.70 | 0.37 | -52.3% | 45 | 58% | 9.9× |
| n=75, band=4% | 0.47 | 0.28 | 0.20 | 17.0% | -68.2% | 0.56 | 0.25 | -51.1% | 37 | 57% | 8.1× |
| n=100, band=0% | 0.32 | 0.28 | 0.28 | 19.5% | -64.1% | 0.60 | 0.30 | -48.1% | 68 | 58% | 13.2× |
| n=100, band=2% | 0.37 | 0.46 | 0.28 | 24.5% | -63.4% | 0.68 | 0.39 | -47.7% | 34 | 58% | 7.3× |
| n=100, band=4% | 0.43 | 0.60 | 0.53 | 36.5% | -56.7% | 0.84 | 0.64 | -38.0% | 20 | 57% | 3.9× |
| n=125, band=0% | 0.35 | 0.41 | 0.27 | 23.5% | -60.2% | 0.67 | 0.39 | -47.9% | 54 | 55% | 10.6× |
| n=125, band=2% | 0.40 | 0.56 | 0.33 | 29.4% | -58.3% | 0.75 | 0.50 | -42.2% | 30 | 54% | 5.7× |
| n=125, band=4% | 0.47 | 0.56 | 0.43 | 32.4% | -59.6% | 0.79 | 0.54 | -39.2% | 19 | 55% | 3.8× |
| n=150, band=0% | 0.35 | 0.35 | 0.36 | 25.5% | -63.8% | 0.69 | 0.40 | -42.3% | 44 | 52% | 8.3× |
| n=150, band=2% | 0.40 | 0.38 | 0.43 | 28.5% | -62.0% | 0.74 | 0.46 | -42.5% | 24 | 52% | 4.2× |
| n=150, band=4% | 0.43 | 0.38 | 0.52 | 32.8% | -65.5% | 0.79 | 0.50 | -47.6% | 17 | 51% | 2.8× |
| n=200, band=0% | 0.24 | 0.03 | 0.44 | 22.9% | -69.3% | 0.65 | 0.33 | -44.7% | 38 | 53% | 6.1× |
| n=200, band=2% | 0.24 | 0.13 | 0.33 | 19.7% | -71.4% | 0.61 | 0.28 | -47.9% | 22 | 53% | 3.8× |
| n=200, band=4% | 0.25 | 0.15 | 0.34 | 20.9% | -71.1% | 0.62 | 0.29 | -50.1% | 16 | 53% | 2.6× |

## Pass rule for n=50, band=4%

| Criterion | Result | Detail |
| --- | --- | --- |
| 1 Calmar ≥ 1.2× benchmark (portfolio) | ✅ | 0.83 vs 1.2 × 0.10 = 0.12 |
| 2 Max drawdown ≤ 40% (portfolio) | ❌ | 57.2% |
| 3 CAGR > 0 (portfolio) | ✅ | 47.3% |
| 4 Sharpe ≥ benchmark (portfolio) | ✅ | 0.99 vs 0.51 |
| 1 Calmar ≥ 1.2× benchmark (BTC) | ✅ | 0.50 vs 1.2 × 0.06 = 0.08 |
| 2 Max drawdown ≤ 40% (BTC) | ❌ | 63.1% |
| 3 CAGR > 0 (BTC) | ✅ | 31.5% |
| 4 Sharpe ≥ benchmark (BTC) | ✅ | 0.82 vs 0.44 |
| 1 Calmar ≥ 1.2× benchmark (ETH) | ✅ | 0.98 vs 1.2 × 0.12 = 0.15 |
| 2 Max drawdown ≤ 40% (ETH) | ❌ | 59.2% |
| 3 CAGR > 0 (ETH) | ✅ | 58.3% |
| 4 Sharpe ≥ benchmark (ETH) | ✅ | 1.03 vs 0.61 |
| 6 Plateau: neighbour n=75, band=4% | ❌ | Calmar 0.24 vs selected 0.74; fails: 2 Max drawdown ≤ 40% (portfolio), 2 Max drawdown ≤ 40% (BTC), 2 Max drawdown ≤ 40% (ETH) |
| 6 Plateau: neighbour n=50, band=2% | ❌ | Calmar 0.80 vs selected 0.74; fails: 2 Max drawdown ≤ 40% (portfolio), 2 Max drawdown ≤ 40% (BTC), 2 Max drawdown ≤ 40% (ETH) |
| 7 CAGR > 0 without the best calendar year | ✅ | 17.6% |
| H1 kill: not the fastest corner (n=50, band=0%) | ✅ | n=50, band=4% |
| H1 kill: CAGR > 0 at 2× costs on Binance USDT too | ✅ | 41.8% |

## Informational (not part of the decision unless a kill rule above uses it)

| Run | Series | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Primary at 0.30%/side | strategy | 50.9% | -55.9% | 1.03 | 0.91 | -29.1% | 40 | 55% | 8.0× |
| Primary at 0.30%/side | 50/50 buy & hold | 8.6% | -87.0% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |
| Primary at 0.90%/side | strategy | 43.8% | -58.4% | 0.94 | 0.75 | -33.0% | 40 | 55% | 8.0× |
| Primary at 0.90%/side | 50/50 buy & hold | 8.5% | -87.0% | 0.51 | 0.10 | -77.7% | 0 | 100% | 0.1× |
| Binance USDT (confirmation 1) | strategy | 41.8% | -57.8% | 0.91 | 0.72 | -44.6% | 40 | 54% | 7.7× |
| Binance USDT (confirmation 1) | 50/50 buy & hold | 7.1% | -88.1% | 0.50 | 0.08 | -77.7% | 0 | 100% | 0.1× |
| Bitvavo EUR (confirmation 2) | strategy | 70.7% | -52.7% | 1.25 | 1.34 | -42.5% | 30 | 60% | 7.9× |
| Bitvavo EUR (confirmation 2) | 50/50 buy & hold | 59.6% | -74.7% | 0.99 | 0.80 | -64.6% | 0 | 100% | 0.0× |
| Kraken 4h (robustness) | strategy | 52.0% | -60.2% | 1.06 | 0.86 | -34.6% | 42 | 56% | 8.1× |
| Kraken 4h (robustness) | 50/50 buy & hold | 8.5% | -87.6% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |

- Bitvavo EUR (confirmation 2): evaluated from 2019-04-28 (data starts later)

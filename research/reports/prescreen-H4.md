# Pre-screen H4: Trend filter with volatility-targeted sizing (post-hoc)

Generated 2026-10-20 17:45 UTC from code `0412937`. Rules: [research/hypotheses/H4.md](../hypotheses/H4.md) and [_CONVENTIONS.md](../hypotheses/_CONVENTIONS.md).

Primary data: kraken 1d, development split 2018-01-01 → 2022-12-31. Judged at **0.60% per side** (2× costs). Variants tested: **16** (cap 20).

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
| n=50, target_vol=30% | 0.75 | 0.63 | 0.93 | 25.9% | -31.2% | 1.14 | 0.83 | -22.2% | 50 | 55% | 5.3× |
| n=50, target_vol=40% | 0.77 | 0.56 | 0.95 | 30.8% | -37.6% | 1.08 | 0.82 | -26.4% | 50 | 55% | 6.8× |
| n=50, target_vol=50% | 0.79 | 0.60 | 1.06 | 38.4% | -43.4% | 1.11 | 0.88 | -31.0% | 50 | 55% | 8.3× |
| n=50, target_vol=60% ⬅ selected | 0.83 | 0.63 | 1.05 | 42.0% | -46.7% | 1.08 | 0.90 | -32.1% | 50 | 55% | 9.4× |
| n=100, target_vol=30% | 0.67 | 0.52 | 0.74 | 21.3% | -34.6% | 0.97 | 0.62 | -26.7% | 34 | 58% | 3.9× |
| n=100, target_vol=40% | 0.63 | 0.45 | 0.75 | 25.7% | -42.6% | 0.93 | 0.60 | -32.5% | 34 | 58% | 5.0× |
| n=100, target_vol=50% | 0.60 | 0.41 | 0.74 | 29.2% | -49.2% | 0.90 | 0.59 | -38.1% | 34 | 58% | 5.9× |
| n=100, target_vol=60% | 0.65 | 0.46 | 0.68 | 30.9% | -53.3% | 0.86 | 0.58 | -40.3% | 34 | 58% | 6.7× |
| n=150, target_vol=30% | 0.67 | 0.65 | 0.77 | 21.9% | -27.3% | 0.99 | 0.80 | -16.9% | 24 | 52% | 2.8× |
| n=150, target_vol=40% | 0.71 | 0.58 | 0.97 | 27.1% | -32.9% | 0.98 | 0.83 | -19.8% | 24 | 52% | 3.6× |
| n=150, target_vol=50% | 0.72 | 0.53 | 0.92 | 31.7% | -38.7% | 0.96 | 0.82 | -23.6% | 24 | 52% | 4.3× |
| n=150, target_vol=60% | 0.65 | 0.59 | 0.86 | 34.5% | -42.0% | 0.94 | 0.82 | -25.3% | 24 | 52% | 4.6× |
| n=200, target_vol=30% | 0.50 | 0.44 | 0.56 | 17.6% | -34.3% | 0.86 | 0.51 | -14.2% | 22 | 53% | 2.4× |
| n=200, target_vol=40% | 0.46 | 0.33 | 0.54 | 20.0% | -43.5% | 0.79 | 0.46 | -16.6% | 22 | 53% | 3.2× |
| n=200, target_vol=50% | 0.42 | 0.30 | 0.53 | 22.9% | -50.8% | 0.77 | 0.45 | -21.9% | 22 | 53% | 3.9× |
| n=200, target_vol=60% | 0.41 | 0.29 | 0.50 | 24.3% | -55.7% | 0.75 | 0.44 | -27.9% | 22 | 53% | 4.3× |

## Pass rule for n=50, target_vol=60%

| Criterion | Result | Detail |
| --- | --- | --- |
| 1 Calmar ≥ 1.2× benchmark (portfolio) | ✅ | 0.90 vs 1.2 × 0.10 = 0.12 |
| 2 Max drawdown ≤ 40% (portfolio) | ❌ | 46.7% |
| 3 CAGR > 0 (portfolio) | ✅ | 42.0% |
| 4 Sharpe ≥ benchmark (portfolio) | ✅ | 1.08 vs 0.51 |
| 1 Calmar ≥ 1.2× benchmark (BTC) | ✅ | 0.63 vs 1.2 × 0.06 = 0.08 |
| 2 Max drawdown ≤ 40% (BTC) | ❌ | 54.4% |
| 3 CAGR > 0 (BTC) | ✅ | 34.2% |
| 4 Sharpe ≥ benchmark (BTC) | ✅ | 0.94 vs 0.44 |
| 1 Calmar ≥ 1.2× benchmark (ETH) | ✅ | 1.05 vs 1.2 × 0.12 = 0.15 |
| 2 Max drawdown ≤ 40% (ETH) | ❌ | 45.9% |
| 3 CAGR > 0 (ETH) | ✅ | 48.3% |
| 4 Sharpe ≥ benchmark (ETH) | ✅ | 1.07 vs 0.61 |
| 6 Plateau: neighbour n=100, target_vol=60% | ❌ | Calmar 0.57 vs selected 0.84; fails: 2 Max drawdown ≤ 40% (portfolio), 2 Max drawdown ≤ 40% (BTC), 2 Max drawdown ≤ 40% (ETH) |
| 6 Plateau: neighbour n=50, target_vol=50% | ❌ | Calmar 0.83 vs selected 0.84; fails: 2 Max drawdown ≤ 40% (portfolio), 2 Max drawdown ≤ 40% (BTC), 2 Max drawdown ≤ 40% (ETH) |
| 7 CAGR > 0 without the best calendar year | ✅ | 13.9% |
| H4 kill: CAGR > 0 at 2× costs on Binance USDT too | ✅ | 39.3% |
| H4 kill: turnover ≤ 400% per year | ❌ | 940% |

## Informational (not part of the decision unless a kill rule above uses it)

| Run | Series | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Primary at 0.30%/side | strategy | 45.6% | -44.4% | 1.14 | 1.03 | -30.1% | 50 | 55% | 9.4× |
| Primary at 0.30%/side | 50/50 buy & hold | 8.6% | -87.0% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |
| Primary at 0.90%/side | strategy | 38.4% | -48.8% | 1.01 | 0.79 | -34.1% | 50 | 55% | 9.4× |
| Primary at 0.90%/side | 50/50 buy & hold | 8.5% | -87.0% | 0.51 | 0.10 | -77.7% | 0 | 100% | 0.1× |
| Binance USDT (confirmation 1) | strategy | 39.3% | -50.2% | 1.02 | 0.78 | -39.7% | 53 | 56% | 9.0× |
| Binance USDT (confirmation 1) | 50/50 buy & hold | 7.1% | -88.1% | 0.50 | 0.08 | -77.7% | 0 | 100% | 0.1× |
| Bitvavo EUR (confirmation 2) | strategy | 58.5% | -53.3% | 1.28 | 1.10 | -42.6% | 38 | 60% | 9.2× |
| Bitvavo EUR (confirmation 2) | 50/50 buy & hold | 59.6% | -74.7% | 0.99 | 0.80 | -64.6% | 0 | 100% | 0.0× |
| Kraken 4h (robustness) | strategy | 44.6% | -43.9% | 1.17 | 1.02 | -28.7% | 65 | 55% | 11.7× |
| Kraken 4h (robustness) | 50/50 buy & hold | 8.5% | -87.6% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |

- Bitvavo EUR (confirmation 2): evaluated from 2019-04-28 (data starts later)

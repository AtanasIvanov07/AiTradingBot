# Pre-screen H5: H4's rule at one fixed setting (post-hoc)

Generated 2026-10-20 18:03 UTC from code `aa077ca`. Rules: [research/hypotheses/H5.md](../hypotheses/H5.md) and [_CONVENTIONS.md](../hypotheses/_CONVENTIONS.md).

Primary data: kraken 1d, development split 2018-01-01 → 2022-12-31. Judged at **0.60% per side** (2× costs). Variants tested: **5** (cap 20).

## Decision: ❌ KILL

## Benchmarks (buy & hold, 2× costs)

| Series | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BTC | 5.0% | -80.3% | 0.44 | 0.06 | -73.2% | 0 | 100% | 0.1× |
| ETH | 11.6% | -93.4% | 0.61 | 0.12 | -82.1% | 0 | 100% | 0.1× |
| 50/50 | 8.5% | -87.0% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |

## Fixed variant and plateau neighbours (2× costs)

No selection score: the card fixes the variant. The other rows are its plateau neighbours.

| Variant | Score | BTC Calmar | ETH Calmar | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| n=150, target_vol=30% ⬅ fixed | — | 0.65 | 0.77 | 21.9% | -27.3% | 0.99 | 0.80 | -16.9% | 24 | 52% | 2.8× |
| n=100, target_vol=30% | — | 0.52 | 0.74 | 21.3% | -34.6% | 0.97 | 0.62 | -26.7% | 34 | 58% | 3.9× |
| n=200, target_vol=30% | — | 0.44 | 0.56 | 17.6% | -34.3% | 0.86 | 0.51 | -14.2% | 22 | 53% | 2.4× |
| n=150, target_vol=20% | — | 0.58 | 0.80 | 15.1% | -20.8% | 0.98 | 0.73 | -13.2% | 22 | 52% | 1.9× |
| n=150, target_vol=40% | — | 0.58 | 0.97 | 27.1% | -32.9% | 0.98 | 0.83 | -19.8% | 24 | 52% | 3.6× |

## Pass rule for n=150, target_vol=30%

| Criterion | Result | Detail |
| --- | --- | --- |
| 1 Calmar ≥ 1.2× benchmark (portfolio) | ✅ | 0.80 vs 1.2 × 0.10 = 0.12 |
| 2 Max drawdown ≤ 40% (portfolio) | ✅ | 27.3% |
| 3 CAGR > 0 (portfolio) | ✅ | 21.9% |
| 4 Sharpe ≥ benchmark (portfolio) | ✅ | 0.99 vs 0.51 |
| 1 Calmar ≥ 1.2× benchmark (BTC) | ✅ | 0.65 vs 1.2 × 0.06 = 0.08 |
| 2 Max drawdown ≤ 40% (BTC) | ✅ | 31.5% |
| 3 CAGR > 0 (BTC) | ✅ | 20.4% |
| 4 Sharpe ≥ benchmark (BTC) | ✅ | 0.89 vs 0.44 |
| 1 Calmar ≥ 1.2× benchmark (ETH) | ✅ | 0.77 vs 1.2 × 0.12 = 0.15 |
| 2 Max drawdown ≤ 40% (ETH) | ✅ | 30.3% |
| 3 CAGR > 0 (ETH) | ✅ | 23.3% |
| 4 Sharpe ≥ benchmark (ETH) | ✅ | 0.94 vs 0.61 |
| 6 Plateau: neighbour n=100, target_vol=30% | ✅ | Calmar 0.63 vs selected 0.71 |
| 6 Plateau: neighbour n=200, target_vol=30% | ❌ | Calmar 0.50 vs selected 0.71 |
| 6 Plateau: neighbour n=150, target_vol=20% | ✅ | Calmar 0.69 vs selected 0.71 |
| 6 Plateau: neighbour n=150, target_vol=40% | ✅ | Calmar 0.77 vs selected 0.71 |
| 7 CAGR > 0 without the best calendar year | ✅ | 10.1% |
| H5 kill: CAGR > 0 at 2× costs on Binance USDT too | ✅ | 23.7% |
| H5 kill: turnover ≤ 400% per year | ✅ | 276% |

## Informational (not part of the decision unless a kill rule above uses it)

| Run | Series | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Primary at 0.30%/side | strategy | 22.7% | -27.3% | 1.02 | 0.83 | -16.9% | 24 | 52% | 2.8× |
| Primary at 0.30%/side | 50/50 buy & hold | 8.6% | -87.0% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |
| Primary at 0.90%/side | strategy | 21.6% | -27.9% | 0.98 | 0.77 | -17.6% | 24 | 52% | 2.8× |
| Primary at 0.90%/side | 50/50 buy & hold | 8.5% | -87.0% | 0.51 | 0.10 | -77.7% | 0 | 100% | 0.1× |
| Binance USDT (confirmation 1) | strategy | 23.7% | -26.9% | 1.08 | 0.88 | -16.2% | 21 | 50% | 2.3× |
| Binance USDT (confirmation 1) | 50/50 buy & hold | 1.0% | -85.1% | 0.42 | 0.01 | -81.5% | 0 | 100% | 0.2× |
| Bitvavo EUR (confirmation 2) | strategy | 21.1% | -34.2% | 0.92 | 0.62 | -25.5% | 17 | 59% | 2.9× |
| Bitvavo EUR (confirmation 2) | 50/50 buy & hold | 43.4% | -75.4% | 0.86 | 0.58 | -64.8% | 0 | 100% | 0.1× |
| Kraken 4h (robustness) | strategy | 23.8% | -26.9% | 1.13 | 0.88 | -14.0% | 33 | 53% | 3.3× |
| Kraken 4h (robustness) | 50/50 buy & hold | 8.5% | -87.6% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |

- H5: one fixed variant registered in the card, so nothing is selected; the other 4 runs are its plateau neighbours (criterion 6)
- Binance USDT (confirmation 1): evaluated from 2018-01-15 (data starts later)
- Bitvavo EUR (confirmation 2): evaluated from 2019-08-06 (data starts later)

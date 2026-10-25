# Gate 1′ H6: Funding-rate crowding filter

Generated 2026-10-25 16:26 UTC from code `5802972`. Rules: [research/hypotheses/H6.md](../hypotheses/H6.md), [_CONVENTIONS.md](../hypotheses/_CONVENTIONS.md) (amendment 1) and PROJECT_PLAN.md amendment A3.

Primary data: Kraken 1d, development 2020-02-01 → 2024-12-31; signal: Binance USD-M funding. Judged at **0.60% per side** (2× costs). Base exposure 50% of each sleeve, hysteresis 10 points, rebalance band 10 points.

## Decision: ❌ KILL

## Benchmarks (buy & hold, 2× costs)

| Series | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BTC | 61.7% | -73.6% | 1.08 | 0.84 | -62.1% | 0 | 100% | 0.1× |
| ETH | 83.3% | -77.2% | 1.15 | 1.08 | -65.6% | 0 | 100% | 0.0× |
| 50/50 | 73.8% | -75.4% | 1.12 | 0.98 | -64.9% | 0 | 100% | 0.0× |

## Grid (2× costs)

Selection score = median of the BTC/ETH-averaged Calmar of the variant and its grid neighbours (conventions §8).

| Variant | Score | BTC Calmar | ETH Calmar | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L=3, θ=20%, x=0 | 0.59 | 0.61 | 0.31 | 19.3% | -39.1% | 0.82 | 0.49 | -34.9% | 19 | 70% | 2.3× |
| L=3, θ=20%, x=0.5 | 0.73 | 0.72 | 0.70 | 31.8% | -43.3% | 1.10 | 0.74 | -34.8% | 0 | 100% | 1.3× |
| L=3, θ=35%, x=0 | 0.61 | 0.59 | 0.56 | 27.5% | -45.7% | 0.93 | 0.60 | -34.7% | 39 | 88% | 4.2× |
| L=3, θ=35%, x=0.5 | 0.74 | 0.70 | 0.79 | 35.1% | -45.3% | 1.08 | 0.77 | -34.7% | 0 | 100% | 2.2× |
| L=3, θ=50%, x=0 | 0.66 | 0.63 | 0.59 | 29.0% | -46.5% | 0.94 | 0.62 | -35.2% | 26 | 93% | 2.7× |
| L=3, θ=50%, x=0.5 | 0.75 | 0.73 | 0.78 | 36.1% | -46.8% | 1.08 | 0.77 | -35.3% | 0 | 100% | 1.5× |
| L=7, θ=20%, x=0 | 0.64 | 0.86 | 0.34 | 25.3% | -39.4% | 1.02 | 0.64 | -35.6% | 16 | 75% | 2.0× |
| L=7, θ=20%, x=0.5 | 0.79 | 0.86 | 0.75 | 34.6% | -41.4% | 1.17 | 0.84 | -35.6% | 0 | 100% | 1.2× |
| L=7, θ=35%, x=0 | 0.67 | 0.68 | 0.61 | 30.1% | -45.2% | 1.00 | 0.67 | -34.7% | 24 | 87% | 2.7× |
| L=7, θ=35%, x=0.5 | 0.80 | 0.75 | 0.84 | 37.2% | -45.1% | 1.13 | 0.82 | -34.7% | 0 | 100% | 1.5× |
| L=7, θ=50%, x=0 | 0.71 | 0.79 | 0.63 | 34.0% | -45.8% | 1.07 | 0.74 | -34.9% | 20 | 93% | 2.1× |
| L=7, θ=50%, x=0.5 | 0.79 | 0.79 | 0.84 | 38.9% | -46.3% | 1.14 | 0.84 | -34.8% | 0 | 100% | 1.2× |
| L=14, θ=20%, x=0 | 0.67 | 0.88 | 0.43 | 27.8% | -39.1% | 1.11 | 0.71 | -35.2% | 16 | 73% | 2.0× |
| L=14, θ=20%, x=0.5 | 0.82 | 0.88 | 0.77 | 36.2% | -42.5% | 1.23 | 0.85 | -35.0% | 0 | 100% | 1.2× |
| L=14, θ=35%, x=0 | 0.69 | 0.91 | 0.47 | 31.9% | -42.5% | 1.11 | 0.75 | -34.9% | 15 | 87% | 1.8× |
| L=14, θ=35%, x=0.5 ⬅ selected | 0.83 | 0.87 | 0.79 | 38.3% | -44.5% | 1.20 | 0.86 | -34.9% | 0 | 100% | 1.0× |
| L=14, θ=50%, x=0 | 0.73 | 0.73 | 0.78 | 35.5% | -45.5% | 1.08 | 0.78 | -35.6% | 14 | 93% | 1.6× |
| L=14, θ=50%, x=0.5 | 0.82 | 0.75 | 0.91 | 39.3% | -45.7% | 1.13 | 0.86 | -35.7% | 0 | 100% | 1.0× |

## Pass rule and in-sample checks for L=14, θ=35%, x=0.5

| Criterion | Result | Detail |
| --- | --- | --- |
| 1 Calmar ≥ 1.2× benchmark (portfolio) | ❌ | 0.86 vs 1.2 × 0.98 = 1.17 |
| 2 Max drawdown ≤ 40% (portfolio) | ❌ | 44.5% |
| 3 CAGR > 0 (portfolio) | ✅ | 38.3% |
| 4 Sharpe ≥ benchmark (portfolio) | ✅ | 1.20 vs 1.12 |
| 1 Calmar ≥ 1.2× benchmark (BTC) | ❌ | 0.87 vs 1.2 × 0.84 = 1.01 |
| 2 Max drawdown ≤ 40% (BTC) | ❌ | 43.9% |
| 3 CAGR > 0 (BTC) | ✅ | 38.3% |
| 4 Sharpe ≥ benchmark (BTC) | ✅ | 1.27 vs 1.08 |
| 1 Calmar ≥ 1.2× benchmark (ETH) | ❌ | 0.79 vs 1.2 × 1.08 = 1.30 |
| 2 Max drawdown ≤ 40% (ETH) | ❌ | 48.2% |
| 3 CAGR > 0 (ETH) | ✅ | 38.3% |
| 4 Sharpe ≥ benchmark (ETH) | ❌ | 1.08 vs 1.15 |
| 6 Plateau: neighbour L=7, θ=35%, x=0.5 | ❌ | Calmar 0.79 vs selected 0.83; fails: 1 Calmar ≥ 1.2× benchmark (portfolio), 2 Max drawdown ≤ 40% (portfolio), 1 Calmar ≥ 1.2× benchmark (BTC), 2 Max drawdown ≤ 40% (BTC), 1 Calmar ≥ 1.2× benchmark (ETH), 2 Max drawdown ≤ 40% (ETH) |
| 6 Plateau: neighbour L=14, θ=20%, x=0.5 | ❌ | Calmar 0.83 vs selected 0.83; fails: 1 Calmar ≥ 1.2× benchmark (portfolio), 2 Max drawdown ≤ 40% (portfolio), 1 Calmar ≥ 1.2× benchmark (BTC), 2 Max drawdown ≤ 40% (BTC), 1 Calmar ≥ 1.2× benchmark (ETH), 2 Max drawdown ≤ 40% (ETH) |
| 6 Plateau: neighbour L=14, θ=50%, x=0.5 | ❌ | Calmar 0.83 vs selected 0.83; fails: 1 Calmar ≥ 1.2× benchmark (portfolio), 2 Max drawdown ≤ 40% (portfolio), 1 Calmar ≥ 1.2× benchmark (BTC), 2 Max drawdown ≤ 40% (BTC), 1 Calmar ≥ 1.2× benchmark (ETH), 2 Max drawdown ≤ 40% (ETH) |
| 6 Plateau: neighbour L=14, θ=35%, x=0 | ❌ | Calmar 0.69 vs selected 0.83; fails: 1 Calmar ≥ 1.2× benchmark (portfolio), 2 Max drawdown ≤ 40% (portfolio), 1 Calmar ≥ 1.2× benchmark (BTC), 2 Max drawdown ≤ 40% (BTC), 1 Calmar ≥ 1.2× benchmark (ETH), 2 Max drawdown ≤ 40% (ETH) |
| 7 CAGR > 0 without the best calendar year | ✅ | 23.4% |
| R1 Robustness: L=11, θ=35%, x=0.5 | ✅ | Sharpe 1.10 vs floor 0.7 × 1.21 = 0.85 (1× costs) |
| R1 Robustness: L=18, θ=35%, x=0.5 | ✅ | Sharpe 1.22 vs floor 0.7 × 1.21 = 0.85 (1× costs) |
| R1 Robustness: L=14, θ=26.25%, x=0.5 | ✅ | Sharpe 1.20 vs floor 0.7 × 1.21 = 0.85 (1× costs) |
| R1 Robustness: L=14, θ=43.75%, x=0.5 | ✅ | Sharpe 1.14 vs floor 0.7 × 1.21 = 0.85 (1× costs) |
| R2 Walk-forward: net return > 0 in ≥ 6 of 10 half-years | ✅ | 9 of 10 (0.60%/side) |
| R5 Null: Calmar above the 95th percentile of 1,000 random-crowded runs | ❌ | 0.86 vs 1.18 (beats 35% of runs) |
| R6 Binance USDT: CAGR > 0 at 2× costs (no sign reversal) | ✅ | 37.3% |
| H6 kill: ≥ 3 crowded episodes per asset | ✅ | BTC 8, ETH 8 |
| H6 kill: not the corner (L=3, θ=20%, x=0) | ✅ | L=14, θ=35%, x=0.5 |

## R1 robustness (1× costs)

| Variant | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L=14, θ=35%, x=0.5 (selected) | 38.8% | -44.4% | 1.21 | 0.87 | -34.8% | 0 | 100% | 1.0× |
| L=11, θ=35%, x=0.5 | 35.1% | -44.5% | 1.10 | 0.79 | -34.7% | 0 | 100% | 1.2× |
| L=18, θ=35%, x=0.5 | 38.8% | -44.5% | 1.22 | 0.87 | -34.8% | 0 | 100% | 0.9× |
| L=14, θ=26.25%, x=0.5 | 37.1% | -44.4% | 1.20 | 0.83 | -34.1% | 0 | 100% | 1.0× |
| L=14, θ=43.75%, x=0.5 | 38.6% | -46.1% | 1.14 | 0.84 | -34.5% | 0 | 100% | 1.0× |

## R2 half-years (0.60%/side)

| 2020H1 | 2020H2 | 2021H1 | 2021H2 | 2022H1 | 2022H2 | 2023H1 | 2023H2 | 2024H1 | 2024H2 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| +29.3% | +64.4% | +36.2% | +27.5% | -35.2% | +0.5% | +28.5% | +13.4% | +22.8% | +14.6% |

## R4 Monte Carlo and R5 null

- R4: 95th-percentile drawdown over 638-day paths (0.30%/side, 20-day blocks, seed 20261025): **42.9%**. Carried into the holdout registration.
- R5: random-crowded Calmars (0.60%/side): median 0.90, 5th percentile 0.75, 95th percentile 1.18.
- Crowded episodes in the window: BTC 8, ETH 8.

## Informational (R3 and other runs; only R6 is a criterion)

| Run | Series | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Kraken at 0.30%/side | H6 | 38.8% | -44.4% | 1.21 | 0.87 | -34.8% | 0 | 100% | 1.0× |
| Kraken at 0.30%/side | 50/50 buy & hold | 73.9% | -75.4% | 1.13 | 0.98 | -64.9% | 0 | 100% | 0.0× |
| Kraken at 0.90%/side | H6 | 37.8% | -44.6% | 1.18 | 0.85 | -34.9% | 0 | 100% | 1.1× |
| Kraken at 0.90%/side | 50/50 buy & hold | 73.7% | -75.4% | 1.12 | 0.98 | -64.9% | 0 | 100% | 0.0× |
| Binance USDT (R6) | H6 | 37.3% | -46.5% | 1.16 | 0.80 | -36.1% | 0 | 100% | 1.1× |
| Binance USDT (R6) | 50/50 buy & hold | 71.4% | -77.7% | 1.10 | 0.92 | -66.8% | 0 | 100% | 0.0× |
| Bitvavo EUR (reported) | H6 | 38.4% | -44.5% | 1.20 | 0.86 | -34.9% | 0 | 100% | 1.0× |
| Bitvavo EUR (reported) | 50/50 buy & hold | 73.9% | -75.4% | 1.13 | 0.98 | -64.9% | 0 | 100% | 0.0× |

- Variants: 18 grid + 4 robustness = 22; running trial count 89 (deflated Sharpe at the holdout).

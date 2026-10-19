# Pre-screen H3: Volatility-targeted holding

Generated 2026-10-19 20:58 UTC from code `087d1d5`. Rules: [research/hypotheses/H3.md](../hypotheses/H3.md) and [_CONVENTIONS.md](../hypotheses/_CONVENTIONS.md).

Primary data: kraken 1d, development split 2018-01-01 → 2022-12-31. Judged at **0.60% per side** (2× costs). Variants tested: **12** (cap 20).

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
| target_vol=30%, lookback=20 | 0.16 | 0.09 | 0.17 | 7.7% | -52.4% | 0.39 | 0.15 | -44.1% | 0 | 100% | 3.5× |
| target_vol=30%, lookback=30 | 0.16 | 0.15 | 0.22 | 10.8% | -53.2% | 0.48 | 0.20 | -45.6% | 0 | 100% | 2.1× |
| target_vol=30%, lookback=60 ⬅ selected | 0.21 | 0.11 | 0.37 | 12.5% | -47.7% | 0.54 | 0.26 | -37.2% | 0 | 100% | 0.9× |
| target_vol=40%, lookback=20 | 0.13 | 0.10 | 0.22 | 11.2% | -62.5% | 0.46 | 0.18 | -54.0% | 0 | 100% | 4.1× |
| target_vol=40%, lookback=30 | 0.16 | 0.07 | 0.22 | 10.3% | -61.9% | 0.45 | 0.17 | -53.7% | 0 | 100% | 2.6× |
| target_vol=40%, lookback=60 | 0.19 | 0.12 | 0.30 | 13.3% | -56.5% | 0.51 | 0.24 | -45.2% | 0 | 100% | 1.1× |
| target_vol=50%, lookback=20 | 0.13 | 0.08 | 0.11 | 7.1% | -68.9% | 0.39 | 0.10 | -60.3% | 0 | 100% | 4.4× |
| target_vol=50%, lookback=30 | 0.13 | 0.07 | 0.20 | 10.7% | -68.6% | 0.46 | 0.16 | -60.4% | 0 | 100% | 2.6× |
| target_vol=50%, lookback=60 | 0.17 | 0.07 | 0.25 | 12.1% | -65.9% | 0.48 | 0.18 | -55.6% | 0 | 100% | 1.3× |
| target_vol=60%, lookback=20 | 0.09 | 0.11 | 0.15 | 10.1% | -75.0% | 0.46 | 0.13 | -65.6% | 0 | 100% | 3.8× |
| target_vol=60%, lookback=30 | 0.13 | 0.05 | 0.13 | 7.4% | -75.5% | 0.42 | 0.10 | -67.8% | 0 | 100% | 2.5× |
| target_vol=60%, lookback=60 | 0.16 | 0.10 | 0.24 | 13.5% | -70.3% | 0.52 | 0.19 | -60.2% | 0 | 100% | 1.3× |

## Pass rule for target_vol=30%, lookback=60

| Criterion | Result | Detail |
| --- | --- | --- |
| 1 Calmar ≥ 1.2× benchmark (portfolio) | ✅ | 0.26 vs 1.2 × 0.10 = 0.12 |
| 2 Max drawdown ≥ 25% smaller than benchmark's (portfolio) | ✅ | 47.7% vs limit 65.2% |
| 3 CAGR > 0 (portfolio) | ✅ | 12.5% |
| 4 Sharpe ≥ benchmark (portfolio) | ✅ | 0.54 vs 0.51 |
| 1 Calmar ≥ 1.2× benchmark (BTC) | ✅ | 0.11 vs 1.2 × 0.06 = 0.08 |
| 2 Max drawdown ≥ 25% smaller than benchmark's (BTC) | ✅ | 49.1% vs limit 60.2% |
| 3 CAGR > 0 (BTC) | ✅ | 5.4% |
| 4 Sharpe ≥ benchmark (BTC) | ❌ | 0.33 vs 0.44 |
| 1 Calmar ≥ 1.2× benchmark (ETH) | ✅ | 0.37 vs 1.2 × 0.12 = 0.15 |
| 2 Max drawdown ≥ 25% smaller than benchmark's (ETH) | ✅ | 49.7% vs limit 70.1% |
| 3 CAGR > 0 (ETH) | ✅ | 18.2% |
| 4 Sharpe ≥ benchmark (ETH) | ✅ | 0.68 vs 0.61 |
| 6 Plateau: neighbour target_vol=40%, lookback=60 | ✅ | Calmar 0.21 vs selected 0.24 |
| 6 Plateau: neighbour target_vol=30%, lookback=30 | ✅ | Calmar 0.18 vs selected 0.24 |
| 7 CAGR > 0 without the best calendar year | ❌ | -3.3% |
| H3 kill: turnover ≤ 400% per year | ✅ | 92% |

## Informational (not part of the decision unless a kill rule above uses it)

| Run | Series | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Primary at 0.30%/side | strategy | 12.9% | -47.5% | 0.55 | 0.27 | -36.6% | 0 | 100% | 0.9× |
| Primary at 0.30%/side | 50/50 buy & hold | 8.6% | -87.0% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |
| Primary at 0.90%/side | strategy | 12.3% | -47.9% | 0.53 | 0.26 | -37.5% | 0 | 100% | 0.9× |
| Primary at 0.90%/side | 50/50 buy & hold | 8.5% | -87.0% | 0.51 | 0.10 | -77.7% | 0 | 100% | 0.1× |
| Binance USDT (confirmation 1) | strategy | 12.5% | -48.4% | 0.54 | 0.26 | -35.9% | 0 | 100% | 0.8× |
| Binance USDT (confirmation 1) | 50/50 buy & hold | 7.1% | -88.1% | 0.50 | 0.08 | -77.7% | 0 | 100% | 0.1× |
| Bitvavo EUR (confirmation 2) | strategy | 26.4% | -43.2% | 0.91 | 0.61 | -35.9% | 0 | 100% | 0.9× |
| Bitvavo EUR (confirmation 2) | 50/50 buy & hold | 57.5% | -74.8% | 0.98 | 0.77 | -64.6% | 0 | 100% | 0.0× |
| Kraken 4h (robustness) | strategy | 12.4% | -48.2% | 0.54 | 0.26 | -36.9% | 0 | 100% | 0.7× |
| Kraken 4h (robustness) | 50/50 buy & hold | 8.5% | -87.6% | 0.51 | 0.10 | -77.6% | 0 | 100% | 0.1× |

- Bitvavo EUR (confirmation 2): evaluated from 2019-05-08 (data starts later)

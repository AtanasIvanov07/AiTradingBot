# Gate 2 H5: out-of-sample test

Generated 2026-10-20 20:02 UTC from code `1474bac`. Rules: [research/hypotheses/H5-gate2.md](../hypotheses/H5-gate2.md).

Validation: Kraken EUR 1d, 2023-01-01 → 2024-12-31, modelled costs 0.30% per side. Orders: **75**.

## Decision: ❌ KILL (validation)

## H5 vs buy & hold (validation, modelled costs)

| Series | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H5 portfolio | 35.5% | -20.4% | 1.30 | 1.74 | 28.2% | 9 | 80% | 5.6× |
| H5 BTC | 45.3% | -22.8% | 1.42 | 1.99 | 40.8% | 5 | 78% | 6.2× |
| H5 ETH | 25.0% | -18.7% | 0.94 | 1.34 | 15.6% | 4 | 71% | 4.9× |
| Buy & hold BTC | 141.1% | -27.0% | 2.07 | 5.23 | 134.6% | 0 | 100% | 0.2× |
| Buy & hold ETH | 69.5% | -45.9% | 1.22 | 1.51 | 55.4% | 0 | 100% | 0.2× |
| Buy & hold 50/50 | 108.4% | -34.8% | 1.76 | 3.11 | 100.8% | 0 | 100% | 0.2× |

## Criteria (validation)

| Criterion | Result | Detail |
| --- | --- | --- |
| G1 Calmar ≥ 1.2× 50/50 buy & hold | ❌ | 1.74 vs 1.2 × 3.11 = 3.74 |
| G2 Max drawdown ≤ 35% | ✅ | 20.4% |
| G3 CAGR > 0 at 2× costs | ✅ | 33.2% |
| G4 ±25%: n=113, target_vol=30% keeps ≥ 70% of Sharpe | ✅ | 1.43 vs 0.7 × 1.30 = 0.91 |
| G4 ±25%: n=188, target_vol=30% keeps ≥ 70% of Sharpe | ✅ | 1.30 vs 0.7 × 1.30 = 0.91 |
| G4 ±25%: n=150, target_vol=22% keeps ≥ 70% of Sharpe | ✅ | 1.30 vs 0.7 × 1.30 = 0.91 |
| G4 ±25%: n=150, target_vol=38% keeps ≥ 70% of Sharpe | ✅ | 1.37 vs 0.7 × 1.30 = 0.91 |
| G5 Calmar beats ≥ 95% of 1,000 random-entry runs | ❌ | 1.74 vs 95th percentile 3.69 |
| G6 Profitable in ≥ 3 of 4 half-years | ✅ | 2023H1 +10.0%, 2023H2 +16.5%, 2024H1 +35.2%, 2024H2 +6.1% |
| G7 Bitvavo EUR: CAGR > 0 at 2× costs | ✅ | 34.4% |

## Holdout (2025-01 → 2026-09)

Not opened: a validation criterion failed, so the holdout stays closed.

## Reported, not criteria

- Monte Carlo 95th-percentile drawdown over a holdout-length path (from validation): 34.2%. Cross-check against the §6.4 risk limits (20% / 30%).
- Deflated Sharpe ratio (development data, 67 trials): 0.87
- Random-entry 95th-percentile Calmar: 3.69
- Freqtrade implementation check: 11 identical positions; agree

| Run | Series | CAGR | Max DD | Sharpe | Calmar | Worst year | Round trips | In market | Turnover/yr |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Primary at 0.60%/side | H5 | 33.2% | -21.3% | 1.24 | 1.56 | 25.8% | 9 | 80% | 5.6× |
| Primary at 0.90%/side | H5 | 30.9% | -22.2% | 1.17 | 1.39 | 23.5% | 9 | 80% | 5.6× |
| Robustness n=113, target_vol=30% | H5 | 38.5% | -23.2% | 1.43 | 1.66 | 30.5% | 13 | 81% | 6.6× |
| Robustness n=188, target_vol=30% | H5 | 37.0% | -20.9% | 1.30 | 1.77 | 32.2% | 6 | 80% | 4.7× |
| Robustness n=150, target_vol=22% | H5 | 27.0% | -16.1% | 1.30 | 1.68 | 22.4% | 9 | 80% | 4.6× |
| Robustness n=150, target_vol=38% | H5 | 46.4% | -23.3% | 1.37 | 1.99 | 35.5% | 9 | 80% | 6.3× |
| Binance USDT at 0.60%/side | H5 | 35.8% | -20.1% | 1.30 | 1.78 | 33.1% | 9 | 79% | 5.6× |
| Binance USDT at 0.60%/side | 50/50 buy & hold | 104.7% | -34.0% | 1.70 | 3.08 | 89.2% | 0 | 100% | 0.2× |

- Gate 1 exception (amendment A2): H5 failed Gate 1's plateau by 0.1 point.
- SOL/EUR: skipped (its data wasn't added before the run).
- Holdout: not opened (a validation criterion failed); it stays closed.

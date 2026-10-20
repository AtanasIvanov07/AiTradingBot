# Phase 1 closing summary

Closed **2026-10-20** under the Phase 1 stop rule (PROJECT_PLAN.md §7), confirmed by the project owner. Details for
each run are in [research/journal.md](../journal.md) (#0–#9) and the `prescreen-H*.md` reports next to this file.

## Decision

**Stop.** All five hypotheses failed Gate 1, and both allowed iterations (H4, H5) are used. The plan's outcome for
this case applies: no strategy goes forward, and the project counts as a learning success. The plan suggests
monthly DCA instead. That's a personal decision, not something this project recommends.

## What was tested

Development data 2018–2022 (Kraken EUR, daily), judged at 2× costs (0.60% per side). These are the variants that
the registered rules selected.

| Card | Idea | Selected variant | CAGR | Max DD | Sharpe | Calmar | Why killed |
|---|---|---|---:|---:|---:|---:|---|
| H1 | Trend filter (SMA with band) | n=50, band=4% | 47.3% | −57.2% | 0.99 | 0.83 | Drawdown > 40% in every variant; no plateau |
| H2 | Weekly BTC/ETH/cash rotation | lookback=30, buffer=0% | 37.0% | −79.8% | 0.80 | 0.46 | Drawdown; no plateau; worse than H1 |
| H3 | Volatility-targeted holding | target 30%, lookback 60 | 12.5% | −47.7% | 0.54 | 0.26 | BTC Sharpe below buy & hold; nothing left without its best year |
| H4 *(post-hoc)* | H1 trend × H3 sizing | n=50, target 60% | 42.0% | −46.7% | 1.08 | 0.90 | Drawdown > 40%; no plateau; turnover 940%/yr |
| H5 *(post-hoc ×2)* | H4 fixed at a slow, low-vol setting | n=150, target 30% | 21.9% | −27.3% | 0.99 | 0.80 | Plateau: one neighbour 30.1% below (limit 30%) |
| — | 50/50 buy & hold | — | 8.5% | −87.0% | 0.51 | 0.10 | (benchmark) |

**Variants tested: 63.** For every hypothesis, the engine was checked against an independent re-implementation.

## What was learned

- **Risk could be cut, but not cleanly enough.**
  - Every rule beat buy & hold on Sharpe except H3 for BTC. Drawdowns fell from −87% to between −27% and −80%.
  - The binding limits were the 40% drawdown cap and the requirement for stable neighbouring settings, not
    profitability.
- **Fully invested while long is too much risk:** H1 and H2 always had drawdowns above 50%.
- **Volatility sizing alone gives up too much:** H3 kept the drawdown smaller but lost the upside.
- **The setting that met the limits was the cautious one, and it paid for that.** On Bitvavo (2019–2022, mostly
  rising) H5 made 21.1% a year against buy & hold's 43.4%.
- **Costs matter for fast rules, not slow ones.**
  - H4's turnover cost about 5.6% of equity a year at 2× costs.
  - H5 barely changed between 1× and 3× costs (22.7% vs 21.6%).
- **Data bugs are the biggest silent risk.** One bad Kraken print (2018-01-13) inflated fills until an independent
  cross-check caught it. The fix, re-runs and the "empty window" validator error came from that.
- **Pre-registration worked as intended.** It stopped two near-misses (H4's other variants, H5's 0.1-point plateau
  miss) from being rescued after the fact.

## What this does and doesn't show

- It **doesn't** show that these rules lose money. On 2018–2022 they had better risk-adjusted returns than holding.
- It **does** show that none met the risk and stability bar set in advance. So there is no evidence-backed reason to
  trade them with real money.
- The **validation (2023–2024) and holdout (2025-01 → 2026-09) splits were never opened.**
  - Any genuinely new idea in a future project could still be tested on them cleanly.
  - It would need a new plan, and the 63 trials so far should count toward its multiple-testing correction.

## What's left

- **Kept:** the repository on GitHub, including:
  - the data pipeline and validator;
  - the backtester and its tests;
  - the Gate 1 runner;
  - the five cards, the journal and the reports.
- Nothing ever traded live. Infrastructure cost was €0, and the €100 of trading capital was never used.
- **Loose ends (yours):**
  - If you created any exchange API keys or a Telegram bot token for this project, revoke them, since nothing uses
    them now.
  - Azure for Students was never activated, so there's nothing to shut down.
  - Delete the empty old OneDrive project folder.

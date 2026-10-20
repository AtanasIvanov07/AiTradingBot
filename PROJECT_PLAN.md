# AiTradingBot — Project Plan

*Version 1.1 (free-hosting update) · 19 October 2026 · Spot crypto (BTC, ETH) · Bulgaria / EU · €100 trading capital · 10–20 h/week*

> **Status (20 Oct 2026): closed at Phase 1 under its stop rule.** All five hypotheses (H1–H5) failed Gate 1, so Phases 2–5 were not started and nothing traded. See [research/reports/phase1-summary.md](research/reports/phase1-summary.md).

> **Disclaimer.** This is not financial, tax or legal advice, and I am not a licensed adviser. It is a plan for a careful engineering and research experiment. It does not recommend any investment. Facts about exchanges, fees and tax change often. Section 12 lists what I could not fully verify.

---

## Table of contents

0. [Summary and reality check](#0-summary-and-reality-check)
1. [Goals and success metrics](#1-goals-and-success-metrics)
2. [Strategy research and validating an edge before building](#2-strategy-research-and-validating-an-edge-before-building)
3. [Architecture and tech stack](#3-architecture-and-tech-stack)
4. [Data sourcing and cleaning](#4-data-sourcing-and-cleaning)
5. [Backtesting methodology and pitfalls](#5-backtesting-methodology-and-pitfalls)
6. [Risk management](#6-risk-management)
7. [Phased rollout with checklists and exit criteria](#7-phased-rollout-with-checklists-and-exit-criteria)
8. [Legal, tax and security](#8-legal-tax-and-security)
9. [Monitoring, maintenance and failure modes](#9-monitoring-maintenance-and-failure-modes)
10. [Timeline and milestones](#10-timeline-and-milestones)
11. [Budget and cost levers](#11-budget-and-cost-levers)
12. [What I'm unsure about: verify these yourself](#12-what-im-unsure-about-verify-these-yourself)
13. [Glossary](#13-glossary)
14. [Sources and further reading](#14-sources-and-further-reading)

---

## 0. Summary and reality check

### 0.1 Read this first

- **Most retail active traders lose money, and most trading bots don't beat simply holding.** I don't know of a rigorous study of retail crypto bots specifically. The closest evidence is from day traders:
  - In Brazil, 97% of people who day-traded futures on more than 300 days lost money (Chague, De-Losso & Giovannetti, 2019).
  - In Taiwan, fewer than 1% of day traders earned predictable profits after fees (Barber, Lee, Liu & Odean).

  A bot removes emotional mistakes. It does not remove fees, overfitting, or competition from professional firms with better data and infrastructure.
- **With €100, every euro of cost matters.** An excellent year (+30%) earns €30, and a €5/month server would cost €60 a year. That's why this plan keeps **infrastructure at €0**, using free cloud tiers and your GitHub Student Developer Pack (§3.7–3.8). It also treats trading fees as the main cost to minimise (§11.2). With €0 overhead a net profit is possible, but expect a few euros a year at best. The bigger payoff is a working, validated pipeline, real skills, and an honest answer to "does this strategy have an edge?" Money only becomes meaningful if you later scale up, and that should require evidence (see Gate 4).
- **Your benchmark is holding BTC/ETH, not zero.** Making +10% while BTC rose +60% is a failure, unless you took far less risk. A realistic good outcome for the strategies below is lower returns than buy-and-hold in strong bull markets and much smaller losses in crashes.
- **Fees are your main enemy at this size.** Approximate annual fee drag = round trips per year × round-trip cost × fraction of capital per trade. At 0.6% per round trip, 20 full-size round trips a year cost about 12% per year before the strategy earns anything. This is why the plan uses slow strategies (daily candles).
- **Binance is not usable for trading from the EU.** See 0.3.
- **The most likely outcome**, in my honest judgment (not a statistic): you learn a great deal, and you find either no edge or a modest "smaller-drawdown" edge. A strategy that clearly beats buy-and-hold on a risk-adjusted basis out of sample is possible but less likely. Losing part of the €100 is a realistic outcome, so plan for it.

### 0.2 Key decisions

| Decision | Choice | Why |
|---|---|---|
| Instruments | Spot **BTC/EUR** and **ETH/EUR**, long-only, **no leverage** | Most liquid, lowest spreads, no liquidation risk, simplest taxes. EUR pairs avoid a USD conversion layer. |
| Timeframe | **Daily** candles (primary), 4h (secondary) | Fewer trades means less fee drag. Insensitive to latency, so it runs fine on a small free cloud VM. |
| Exchange | **Bitvavo** by default, **OKX EEA** as the alternative. Not Binance. Not Kraken at this size. | MiCA-authorised, low entry fees, EUR-native, €5 minimum order (see §3.6). |
| Tech stack | **Python + Freqtrade** + pandas/Jupyter + Docker | Mature open-source crypto bot with backtesting, paper trading, live trading, built-in bias checks and an ML module. Details in §3. |
| Hosting | **€0:** your own PC for research. An **Azure for Students VM** (Student Pack, no card) in an EU region for paper and live trading. A free **Oracle Cloud** VM as the second host. An old laptop or Pi as the fallback. | Paid servers would eat most of any profit at €100 (§3.7). |
| First strategy family | **Trend following / time-series momentum** | Best-documented edge for slow crypto trading. Low trade count, so fees stay manageable. |
| Paper trading | Freqtrade **dry-run** on live market data | The same code path as live trading, so very little can differ between paper and live. |
| ML / LLM | **Only after** a validated rule-based baseline: regime filter, then a gradient-boosted signal filter. LLM sentiment only as a forward-only shadow test. | §7, Phase 5. |

### 0.3 About your Binance account

According to multiple news reports, Binance has had no MiCA authorisation since **1 July 2026**. Since then it has stopped accepting new spot orders, deposits and sign-ups from EEA residents. Withdrawals and closing existing positions still work. **Setting up API access there will not let you trade.**

- If you have funds there, check Binance's in-app notices and consider moving them to an authorised exchange.
- You can still use **Binance's free public historical data** for research. That needs no account (§4).

---

## 1. Goals and success metrics

### 1.1 Goals, in priority order

| # | Goal | Why it's ranked here |
|---|---|---|
| G1 | **Learn** systematic trading: research, backtesting, risk and operations | You get this even if the strategy fails. |
| G2 | **Engineer** a bot that runs unattended, safely and observably | Reusable for any future strategy. |
| G3 | **Find evidence**: a statistically honest answer to "does strategy X have an edge after costs?" | "No" is a valid, useful result. |
| G4 | **Money**: a **net profit after all costs** (trading fees, hosting, electricity, tax), while never losing more than **€30** of the €100 (the loss budget) | Capital preservation comes before profit. €0 infrastructure is what makes a net profit possible. |

### 1.2 Measurable success metrics

Formulas for each term are in the glossary (§13).

**Research / edge (measured in Phase 2)**

| Metric | Target |
|---|---|
| Out-of-sample (OOS) Calmar ratio (CAGR ÷ max drawdown) vs a 50/50 BTC-ETH buy-and-hold benchmark over the same period | ≥ 1.2 × benchmark |
| OOS max drawdown | ≤ 35% (BTC buy-and-hold has historically had drawdowns of roughly 75%+) |
| OOS net return at **2×** modelled costs | > 0 |
| Parameter robustness: ±25% change to each parameter | Keeps ≥ 70% of the baseline Sharpe ratio |
| Random-entry test: beats random strategies with the same trade count and time in market | Beats ≥ 95% of 1,000 random runs |
| Sample size | ≥ 50 OOS trades across BTC and ETH. With fewer, label results "low confidence". |
| Walk-forward consistency | Profitable in ≥ 60% of walk-forward test windows |
| Final holdout (opened once) | Max drawdown no worse than the 95th-percentile Monte Carlo drawdown from validation, and return ≥ 0 |

**Engineering (measured in Phases 3–4)**

| Metric | Target |
|---|---|
| Uptime (heartbeat-measured) | ≥ 99% |
| Signal parity: paper/live trades vs a backtest replay of the same period | 100% match, or every difference explained |
| Time to detect a failure | ≤ 15 minutes (heartbeat alert) |
| Kill-switch fire drill: from trigger to "no positions, no new entries" | ≤ 5 minutes |
| Secrets committed to git | 0 (checked with `gitleaks`) |
| Unhandled exceptions in the last 2 weeks before a phase gate | 0 |

**Live (measured in Phase 4)**

| Metric | Target |
|---|---|
| Realised cost per side (fees + slippage) | ≤ 1.5 × modelled |
| Drawdown from equity peak | Soft limit 20%, hard stop 30% |
| Cumulative net loss | ≤ €30 (loss budget) |
| Net € result after all costs (fees, hosting, electricity, tax) | > €0 (the profitability goal) |
| Infrastructure cost | €0/month |
| Risk-rule breaches | 0 |

---

## 2. Strategy research and validating an edge before building

### 2.1 Where could an edge come from?

An edge is a repeatable reason you should earn money that someone else is willing to give up. In liquid markets, real edges usually come from:

1. **Risk premia:** being paid to hold risk others avoid.
2. **Behavioural patterns:** herding and slow reaction cause trends; overreaction causes short-term reversals.
3. **Structural flows:** forced selling, liquidations, rebalancing, funding payments.
4. **Speed and infrastructure:** arbitrage, market making, high-frequency trading. **Not available to you.** Professionals win here, so ignore it.

For every idea, write one sentence answering: *"Who is on the other side of my trade, and why are they willing to lose?"* If you can't answer, be suspicious.

### 2.2 Candidate hypotheses, ranked

| ID | Hypothesis | Sketch of rules | Expected trades | Priority |
|---|---|---|---|---|
| **H1** | **Trend following (time-series momentum)** on BTC and ETH, daily | Long when close > SMA(N) and/or on a 20-day Donchian breakout. Exit on close < SMA or a trailing 10-day low. Size positions by volatility. | ~5–15 round trips per asset per year | **Primary** |
| H2 | **Dual-momentum rotation:** BTC vs ETH vs EUR cash, weekly | Each week, hold whichever of BTC/ETH has the higher 30–90-day return if it is above 0. Otherwise hold EUR. | ~10–25 switches per year | Secondary |
| H3 | **Volatility-targeted holding** (a risk overlay, not an edge) | Always hold BTC/ETH, scaling exposure down when realised volatility is high | Monthly rebalance | Benchmark ("do I even need signals?") |
| H4 | **Short-term mean reversion** (e.g. RSI(2) on 4h) | Buy sharp dips in an uptrend, sell on recovery | 50–150 per year | Low. Fees probably kill it. Educational contrast only. |

**Why H1 first.** Time-series momentum is documented across many asset classes (Moskowitz, Ooi & Pedersen, 2012) and in crypto specifically (Liu & Tsyvinski, 2021; Liu, Tsyvinski & Wu, 2022). Its realistic benefit is avoiding the worst of bear markets rather than beating buy-and-hold in bull markets. Its known weakness is repeated small losses ("whipsaws") in sideways markets.

**Out of scope:** leverage and perpetuals, memecoins and small caps, arbitrage, market making, copying paid "signals", and strategies downloaded from the internet that you haven't fully read and understood.

### 2.3 Edge-validation funnel: do this *before* building anything in the bot

```
 Idea ──▶ ① Hypothesis card ──▶ ② Quick pre-screen ──▶ ③ Robustness pre-screen ──▶ ④ Port to Freqtrade (Phase 2)
            (30 min)             (notebook, 1–2 evenings)  (heatmaps, cross-asset)        (full methodology)
            ↳ kill if no         ↳ kill if it fails         ↳ kill if fragile
              rationale            at 2× costs
```

1. **Hypothesis card.** Pre-register everything *before* looking at results (template below). Limit yourself to about 20 variants per hypothesis. Searching more variants makes a lucky result more likely.
2. **Quick pre-screen.** Use a small vectorised pandas backtest (~100 lines that you write yourself, which also teaches you the mechanics). Use **development data only** (2018–2022, §5.1) and costs at **2×** the realistic level (0.6% per side). Compare with buy-and-hold. If it doesn't clearly beat the benchmark here, kill it. Results only get worse from here.
3. **Robustness pre-screen.** Plot a parameter heatmap: is there a broad stable plateau, or one lucky spike? The same parameters should work on BTC *and* ETH, and roughly on both daily and 4h candles.
4. **Only then** implement it as a Freqtrade strategy and run the full methodology in §5.

**Research journal.** Log *every* test you run (date, hypothesis, parameters, period, result) in `research/journal.md`. The number of tests matters: if you try 100 variants, the best one looks great by pure chance. This is the multiple-testing problem. The "deflated Sharpe ratio" (Bailey & López de Prado) is a formal correction for it.

**Hypothesis card template** (`research/hypotheses/H1.md`):

```markdown
# H1 — Daily trend following, BTC/EUR + ETH/EUR
Date registered: YYYY-MM-DD
Rule (plain words):
Rationale (who loses to me and why):
Parameters (max 3) and ranges to test:
Data / period: development 2018-01-01 → 2022-12-31 only
Costs assumed: 0.30% per side (base), 0.60% per side (stress)
Expected trades/year:
Success criteria (pre-screen): Calmar ≥ 1.2× buy & hold at 2× costs; plateau in heatmap
Kill criteria:
Max variants I will test: 20
Result / decision:
```

---

## 3. Architecture and tech stack

### 3.1 Recommendation: Python + Freqtrade

**Why Python rather than C#, even though C# is your strength:**

- The whole crypto-bot and data-science ecosystem is Python-first: Freqtrade, CCXT (exchange connectivity), pandas, scikit-learn, LightGBM, Jupyter. Phase 5 (ML) would push you to Python anyway, so learning it once now avoids maintaining two stacks.
- For a C# developer, the Python needed here is about a 1–2-week ramp. Type hints with `mypy`, plus `ruff` and `pytest`, give you much of the safety you're used to.
- Most tutorials, Q&A and community strategies for retail crypto bots are in Python.

**Why Freqtrade rather than writing your own engine:**

- **Order handling is the most bug-prone part** of any trading system: partial fills, restarts, rejected orders, rounding to exchange precision, rate limits. Freqtrade has solved these for years. For €100 of capital, writing this yourself is the highest-risk, lowest-value work.
- It includes **backtesting, dry-run (paper trading on live data) and live trading on the same code path**. What you paper-trade is exactly what goes live.
- It includes **`lookahead-analysis`** (detects strategies that peek at future candles) and **`recursive-analysis`** (checks that indicator warm-up is long enough). These directly guard against the two most common backtest bugs.
- It includes a Telegram bot, a web UI (FreqUI), SQLite trade persistence, built-in risk "protections", and **FreqAI**, an ML module for Phase 5.
- It is open source, free, and released monthly.

**What you'll still write yourself** (where your engineering skills pay off):

- The data validation pipeline (§4).
- The research notebooks and pre-screen backtester (§2.3).
- The validation harness: walk-forward analysis, Monte Carlo, random-entry benchmark, cost stress (§5).
- The strategy classes, the position-sizing logic and the external watchdog / kill switch (§6).
- Reporting and reconciliation scripts (§9).

**What you give up:**

- Freqtrade's built-in parameter optimiser (`hyperopt`) makes overfitting very easy. Use it sparingly and only within the protocol in §5.
- You work inside a framework's model (per-pair dataframes, signal columns). That's fine for H1–H4, but limiting for exotic portfolio logic.
- Python is dynamically typed. Mitigate with type hints, `mypy` and tests.

### 3.2 Stack options compared

| | **A. Python + Freqtrade** ✅ | B. C# + QuantConnect LEAN | C. Python custom (CCXT + own engine) | D. C# custom (exchange SDKs) |
|---|---|---|---|---|
| Fits your skills | Good (Python ramp ~1–2 weeks) | **Best** (C#) | Good | **Best** |
| Time to first honest backtest | **Days** | 1–2 weeks (data setup) | Weeks | Weeks |
| Paper trading built in | **Yes (dry-run)** | Yes | You build it | You build it |
| Look-ahead / warm-up checks | **Built in** | Partly by design | You build it | You build it |
| ML path | **FreqAI + whole Python ML ecosystem** | Possible, Python-centric | Python ecosystem | Weaker (ML.NET) |
| Risk of execution bugs with real money | **Low (mature)** | Low (mature) | High | High |
| EU-licensed exchange support | Bitvavo (community-tested), OKX EEA, Bybit EU, Kraken | Several (e.g. Kraken, Coinbase, Bybit). I couldn't confirm Bitvavo or OKX EEA. | Anything CCXT supports | Depends on library |
| Cost | Free | Engine free; some cloud/data features paid | Free | Free |

**Verdict:** A. Consider B only if you strongly prefer to stay in C#, and accept a slower start and a narrower exchange choice.

### 3.3 Architecture

```
┌──────────────────────────── RESEARCH (offline, your PC) ────────────────────────────┐
│  Data sources ──▶ ingest ──▶ validate/clean ──▶ Parquet store ──▶ Jupyter notebooks   │
│  (Binance public                (pytest checks)    (raw = immutable,   (hypotheses,      │
│   dumps, Kraken CSV,                                clean = derived)    pre-screens,     │
│   exchange API)                                                         walk-forward,    │
│                                                                         Monte Carlo)     │
└───────────────────────────────────────────────┬───────────────────────────────────────┘
                                                │ validated strategy code (git)
                                                ▼
┌────────────────────── FREQTRADE BOT (Docker; free Azure for Students VM, EU region) ─┐
│  Exchange API (CCXT) ──▶ closed candles ──▶ Strategy (signals) ──▶ Risk layer         │
│                                                                  (position size,      │
│                                                                   stops, protections) │
│                                                                        │              │
│              SQLite trade DB ◀── fills / positions ◀── Order manager ◀─┘              │
│                    │                                       │                          │
│                    │                                       └──▶ Exchange (Bitvavo)    │
└────────────────────┼──────────────────────────────────────────────────────────────────┘
                     ▼
┌──────────────────────────────── MONITORING & SAFETY ─────────────────────────────────┐
│ Telegram alerts & commands · FreqUI (localhost only, via SSH tunnel) · heartbeat      │
│ (Healthchecks.io) · watchdog / kill-switch script (REST API) · daily report ·         │
│ weekly reconciliation (bot DB vs exchange balances)                                   │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Components

| Layer | Tool | Notes |
|---|---|---|
| Language | Python 3.12 (check Freqtrade's current minimum) | Use type hints everywhere |
| Bot framework | Freqtrade, Docker image **pinned to a specific monthly release** | Never use `latest` in live |
| Exchange connectivity | CCXT (inside Freqtrade) | |
| Research | JupyterLab, pandas, numpy, matplotlib/plotly | Add `vectorbt` later only if needed |
| Storage | Parquet (+ DuckDB for ad-hoc queries); Freqtrade's own feather/SQLite | |
| Quality | `pytest`, `ruff`, `mypy`, `pre-commit`, `gitleaks` | |
| Version control | git + private GitHub repository | Secrets never committed |
| IDE | VS Code, or PyCharm Professional (free via your Student Pack) | PyCharm will feel close to Rider/Visual Studio |
| Runtime | Native Python venv on your Windows PC for development and backtests (same pinned Freqtrade version). Docker on a free Azure for Students VM in an EU region for paper and live trading (§3.7). | `tests/test_repo.py` enforces the version match between `requirements.txt` and the Docker image |
| Secrets | 1Password (Student Pack) as the vault; `config.private.json` on the host only | Never in git |
| Monitoring | Freqtrade Telegram bot, FreqUI, Healthchecks.io (free tier), your watchdog script | |
| ML (Phase 5) | FreqAI with LightGBM; scikit-learn for research | |
| LLM (Phase 5, optional) | Any provider API with a small, cheap model | Set a hard monthly spending cap |

### 3.5 Repository layout

```
AiTradingBot/
├── PROJECT_PLAN.md            ← this file
├── README.md
├── .gitignore                 ← data/, user_data/config.private.json, .env, *.sqlite
├── research/
│   ├── journal.md             ← every test you ever run
│   ├── hypotheses/            ← H1.md, H2.md …
│   └── notebooks/
├── src/
│   ├── ingest/                ← download Binance/Kraken/exchange data
│   ├── validate/              ← data quality checks
│   └── analysis/              ← walk-forward, Monte Carlo, random-entry, reports
├── user_data/                 ← Freqtrade's folder
│   ├── strategies/            ← TrendV1.py …
│   ├── config.json            ← no secrets
│   └── config.private.json    ← API keys, Telegram token (gitignored)
├── ops/
│   ├── docker-compose.yml
│   ├── watchdog.py            ← external kill switch
│   └── runbook.md
├── data/                      ← gitignored: raw/, clean/
└── tests/
```

### 3.6 Exchange choice

| Exchange | MiCA status | Entry-tier spot fees (maker / taker) | Freqtrade support | Stop-loss on exchange (Freqtrade, spot) | Notes |
|---|---|---|---|---|---|
| **Bitvavo** ✅ | Authorised (Dutch AFM, per reviews) | **0.15% / 0.25%** (official fee page, via search) | Community-tested | ❌ | EUR-native. BTC-EUR minimum order **€5.00** (live API). Serves Bulgaria. |
| **OKX EEA** (my.okx.com) | Authorised (per public reports) | **Unverified** for EEA. Global base is 0.08% / 0.10%. | **Official** (`myokx`) | ✅ | API returns only 100 candles per call (slow backtest data downloads). |
| Bybit EU | Authorised (Austria FMA) | **Conflicting:** 0.10–0.25% | Official ("Bybit EU") | ❌ | One source reports a flat 0.25% from 5 Oct 2026 |
| Kraken | Authorised (Central Bank of Ireland entity) | **0.40% / 0.80%** (July 2026 schedule) | Official | ✅ | Too expensive at your size. Excellent free historical data. |
| Binance | **Not authorised** | — | — | — | No new EEA spot orders since 1 July 2026 (news reports) |

**Default: Bitvavo.** Round-trip cost ≈ 2 × (0.25% taker + 0.05% slippage) = **0.6%**.

Decision rule for Phase 0:
1. Before depositing, check the exact fee shown in your account at Bitvavo (and at OKX EEA if you're curious).
2. Pick the lowest verified round-trip cost. If it's a tie, prefer official Freqtrade support and stop-loss on exchange (OKX EEA).
3. Confirm the exchange is listed in **ESMA's MiCA register** yourself.

Bitvavo's lack of stop-loss on exchange (in Freqtrade) means **your stops only work while the bot is running**. This is acceptable for a daily strategy with €100, but it is one reason to measure uptime in Phase 3 (§9).

### 3.7 Free hosting (target: €0/month)

Development and research run on your own PC, which you use anyway. From Phase 3 the bot needs a machine that runs 24/7. Your **GitHub Student Developer Pack** provides the best free option.

| Option | Cost to you | Role | Catches |
|---|---|---|---|
| **Azure for Students VM** in an EU region (e.g. West Europe or Germany West Central) ✅ | €0. **No credit card.** $100 credit for 12 months. 750 h/month each of B1s, B2pts v2 (ARM) and B2ats v2 (AMD) VMs free for 12 months. Renewable yearly while you're a student. | **Primary host** for paper and live trading | These sizes have **1 GB RAM** (per Azure's size docs; verify), below Freqtrade's advised 2 GB. Add a 2 GB swap file and measure memory in Phase 3. Disk and public IP may draw a few $/month from the credit. When the credit runs out, the subscription is **disabled**: no surprise bills, but the bot stops. |
| **Oracle Cloud Always Free**, Ampere A1 VM in an EU home region | €0 | **Second host:** runs the dry-run shadow bot, serves as hot standby, and becomes the long-term home once student benefits end | Idle reclamation (below). The home region is permanent. A1 capacity is sometimes unavailable. Up to 2 OCPUs / 12 GB (already cut once from 4 / 24). Card likely needed at sign-up (verify). |
| Old laptop or Raspberry Pi you already own (Linux) | Electricity only (≈ €7–18/year) | Emergency fallback | Home power and internet cuts (a laptop battery works as a built-in UPS). A changing home IP complicates API-key whitelisting. |
| Your desktop PC running 24/7 | Electricity ≈ €100+/year | Development and short tests only | Not actually free. Windows Update reboots and sleep. |
| Heroku (Student Pack: $13/month for 24 months) | €0 within the credit | ❌ Not for the bot | Card required (per a third-party guide). Dynos restart daily and lose local files, so the trade database would need a separate Postgres add-on. Outbound IPs change, which rules out API-key whitelisting. |
| DigitalOcean (Student Pack) | — | ❌ | The $200 student credit ended on 31 July 2026 |
| Google Cloud Always Free e2-micro | €0 | ❌ | US regions only. Bitvavo serves EEA residents, and I couldn't confirm whether its API accepts traffic from US data centres. Don't risk your account. |
| AWS free plan | €0 for up to 6 months | ❌ | Not permanent |
| Paid EU VPS | ~€4–7/month | Only if a successful live phase justifies it | €50–85/year cancels out any profit at €100 capital |

**Timing tip:** Azure's 12-month clock starts when you activate the subscription. **Activate it at the start of Phase 3 (around Week 10), not now.** It then covers paper trading, live trading and the ML forward test (until about Week 62).

**Electricity math.** Use the price per kWh on your bill. One source listed about €0.29/kWh for Bulgaria in mid-2025; your tariff may differ.

```
yearly cost (€) = watts × 8,760 h ÷ 1,000 × price per kWh
desktop  ~60 W → ~525 kWh/yr → ~€105 at €0.20/kWh
laptop   ~10 W →  ~88 kWh/yr →  ~€18
Pi        ~4 W →  ~35 kWh/yr →   ~€7
```

**Oracle's idle-reclamation rule.** Oracle may reclaim (stop) an Always Free instance if, over 7 days, its 95th-percentile CPU use, network use and (on A1) memory use are all below 20%. A bot trading daily candles will almost certainly look "idle" by that definition. That's why Oracle is the *second* host here: a stopped shadow bot costs nothing.
- If Oracle ever becomes the **live** host, upgrade to Pay As You Go first. Oracle's docs say Always Free resources stay free after upgrading. Community reports say upgraded accounts escape idle reclamation, but the official page doesn't say either way. Set a **€1 budget alert**, and only create resources marked "Always Free eligible".
- **Don't run "keep-busy" scripts** that burn CPU to dodge the idle check. They work against the provider's policy, and if the account is closed your bot goes with it.

**Azure host checklist (start of Phase 3)**
- [ ] Activate Azure for Students yourself, via the Student Pack or azure.microsoft.com/free/students. No card needed.
- [ ] Enable MFA on the Microsoft account.
- [ ] Create a **B2ats v2** VM (2 vCPU, x86, so every Freqtrade image works) with Ubuntu LTS in an EU region. Double-check it's a free-eligible size.
- [ ] Add a 2 GB swap file. Use the VM's static public IP for the API-key IP whitelist.
- [ ] Set a cost alert, and check the remaining credit monthly (§9.2).
- [ ] Harden it (§8.4), install Docker, and deploy the pinned Freqtrade image.

**Oracle host checklist (optional, Phases 3–4)**
- [ ] Create the account yourself with an **EU home region** (it can't be changed later). Enable MFA.
- [ ] Create an Ampere A1 VM (1 OCPU / 6 GB) with Ubuntu LTS. If you get "out of host capacity", retry later or in another availability domain.
- [ ] Run the dry-run shadow bot here with the same `docker-compose.yml`. Check that the pinned image supports arm64.

**Portability rule:** every host runs the *same* `docker-compose.yml` and config. The DB and config backups live off the host, so switching hosts takes under an hour.

### 3.8 Other Student Pack tools worth using

Terms are from the official pack page as of October 2026. Offers change (DigitalOcean left in 2026), so re-check before relying on one.

| Tool | Use in this project | Terms |
|---|---|---|
| GitHub Pro | Private repo, CI with GitHub Actions, Codespaces | Free while you're a student |
| GitHub Copilot (Student) | Coding help while you learn Python | Free for verified students; usage limits apply |
| JetBrains (PyCharm Professional) | Python IDE with a strong debugger and notebook support | Free, renewed yearly |
| 1Password (incl. developer tools) | Exchange, email and cloud passwords; 2FA recovery codes; API keys (its CLI can inject secrets at runtime) | Free for 2 years |
| Termius | SSH from your phone, for emergency stops (§6.5) | Free while you're a student |
| Educative / Boot.dev | Python and data-analysis courses (Phases 0–1) | 6 months / 3 months free |
| DataCamp | pandas and machine-learning courses (Phase 5) | 3 months free (check the sign-up conditions) |
| Datadog or New Relic (optional) | Host dashboards, e.g. memory on the 1 GB Azure VM | Datadog Pro free for 2 years (10 servers); New Relic free while you're a student |
| Sentry / Honeybadger (optional) | Error tracking / uptime and cron monitoring | Sentry 1 year (renewable); Honeybadger 1 year |

**Stagger the time-limited offers.** Each clock starts when you redeem the offer, so activate each one when its phase begins:
- Now: GitHub Pro, Copilot, JetBrains, 1Password, Termius, and *one* Python course.
- Phase 3: Azure.
- Phase 5: DataCamp.

---

## 4. Data sourcing and cleaning

### 4.1 What data you need

- **OHLCV candles** at 1d and 4h (1h for more realistic stop simulation) for BTC and ETH. You need two versions:
  - the exact market you'll trade (BTC/EUR, ETH/EUR on Bitvavo);
  - a long-history version (BTC/USDT, ETH/USDT).
- **Exchange metadata:** fees, minimum order sizes, price and quantity precision.
- **Phase 5 only:** extra features (volume, volatility, market-wide data) and news headlines.

### 4.2 Sources (all free)

| Source | What | Use |
|---|---|---|
| **Binance public data** (data.binance.vision) | BTCUSDT/ETHUSDT klines since 2017, 1m–1d, zipped CSVs with checksums. No account needed. | Long-horizon research |
| **Kraken downloadable OHLCVT history** (assets.kraken.com: a ~9.6 GB full archive in 5 parts, plus quarterly zips) | Long **EUR** history (BTC/EUR from 2013; the archive manifest says coverage runs to 2026-09-30) | EUR-denominated validation. `aitradingbot.ingest kraken` reads only the needed CSVs via HTTP range requests (~tens of MB). |
| **Bitvavo API** via `freqtrade download-data` | The exact market you'll trade | Final validation and live parity. **Verify how far back history goes.** |
| CryptoDataDownload (CSV) | Independent copy | Cross-check only |

**USDT vs EUR:** BTC/USDT and BTC/EUR differ by the EUR/USD exchange rate, which adds noise. Do discovery on long USDT history, then **confirm on the EUR pair you'll actually trade** before Gate 2.

### 4.3 Cleaning checklist

Implemented in `src/aitradingbot/ingest/` (cleaning) and `src/aitradingbot/validate/` (checks); see journal #1 for what it found.

- [x] Convert all timestamps to **UTC**; every source is stored with `open_time` = candle **open** time.
- [x] Remove exact **duplicate** candles. Conflicting duplicates are kept so validation reports them, and timestamps must strictly increase.
- [x] Drop candles **off the timeframe grid** (e.g. Binance's post-outage :28 candles in Feb 2018) and record them in the manifest.
- [x] Drop candles whose **open jumps** more than 25% / 15% / 10% (1d / 4h / 1h) from the previous close. In 24/7 markets the open is the first trade after that close, so a bigger jump is a bad print. Example: Kraken reopened after its Jan 2018 outage with BTC/EUR at €20,000 and ETH/EUR at €700. Added 19 Oct 2026, after the H3 cross-check exposed it (journal #4). The validator treats any remaining jump as an error.
- [x] Detect **gaps** (missing candles) and report them. The clean store never contains synthetic candles. Any forward-filling is decided at analysis time and must be flagged. More than 1% missing since the warm-up start is an error.
- [x] Check **OHLC consistency**: low ≤ open, close ≤ high, and volume ≥ 0.
- [x] Flag **outliers**: daily close-to-close moves or wicks > 25% (4h: 15%, 1h: 10%). Cross-check against a second source before keeping or removing them.
- [x] Mark **zero-volume** candles.
- [x] **Cross-source check:** Bitvavo vs Kraken EUR closes (median difference ~0.04%; largest disagreements listed in the report).
- [ ] Watch for **survivorship bias** if you ever expand beyond BTC/ETH: include coins that were later delisted.
- [x] Write a **data manifest** per file: source, download date, input checksums, row count, date range, cleaning notes.

### 4.4 Automated data tests (`tests/test_data_quality.py`)

Automated checks that run on every refresh:

- Timestamps are unique and strictly increasing.
- The number of gaps is below a threshold, and the gaps are listed.
- OHLC invariants hold.
- No NaNs in the clean data.
- The date range covers the required splits.
- Cross-source divergence stays within tolerance.

### 4.5 Storage

`data/raw/` is **immutable**: never edit it, only re-download. `data/clean/` is derived by scripts, so it can be regenerated anytime. Partition files by `exchange/pair/timeframe`. Use the Parquet format.

---

## 5. Backtesting methodology and pitfalls

### 5.1 Data splits

```
2018-01 ─────────────── 2022-12 │ 2023-01 ──── 2024-12 │ 2025-01 ──── 2026-09 │ live data →
 DEVELOPMENT (in-sample)        │ VALIDATION (OOS,      │ FINAL HOLDOUT         │ PAPER TRADING
 bear 2018 · bull 2020-21 ·     │ walk-forward)         │ "lockbox": open ONCE  │ (Phase 3)
 bear 2022                      │                       │ at the end of Phase 2 │
```

- **Walk-forward:** optimise on a rolling 2-year window, test on the next 6 months, roll forward 6 months, and repeat. Only the stitched-together test windows count as OOS performance.
- The development period includes both bull and bear markets on purpose. A strategy tested only in a bull market tells you nothing.
- **The holdout is burnt after one look.** If the strategy fails it, the strategy is rejected. Tweaking and re-running on the holdout turns it into in-sample data.

### 5.2 Execution realism

| Item | Setting |
|---|---|
| Signals | Computed on **closed candles only** |
| Fill price | **Next candle's open** (Freqtrade's backtest behaviour) |
| Fees | Exchange taker fee (0.25%) per side via `--fee 0.0025`, unless maker-only logic is implemented *and* fill rates are verified |
| Slippage | 0.05% per side as a base case for BTC/ETH at your size; **stress at 0.2%** |
| Minimum order | €5, with exchange precision rounding |
| Starting balance | €100 with realistic stake sizes. Rounding and minimums matter at this size. |
| Cost stress | Re-run at 1×, 2× and 3× total costs |

### 5.3 Common pitfalls and countermeasures

| Pitfall | What it looks like | Prevention and detection |
|---|---|---|
| **Overfitting** (curve fitting) | Great backtest, poor live results. Many parameters, sharp optimum. | ≤ 3 parameters. Choose the centre of a stable plateau. Walk-forward. Holdout. Parameter ±25% test. |
| **Data snooping / multiple testing** | "I tried 200 ideas, and this one works" | Pre-registered hypothesis cards, a cap on variants, a research journal, deflated Sharpe awareness |
| **Look-ahead bias** | Uses information not available at decision time, e.g. a candle's close to trade at that same candle's open, `shift(-1)`, normalising with full-dataset statistics | Closed candles only. Next-open fills. Freqtrade `lookahead-analysis`. Code review of every `shift`. |
| **Indicator warm-up** | Indicators like EMA differ between backtest and live because of different history length | Freqtrade `recursive-analysis`; set `startup_candle_count` accordingly |
| **Fee and slippage underestimation** | High-turnover strategies look profitable | Real fee schedule, slippage, 2×/3× stress, turnover report |
| **Unrealistic limit fills** | Assuming every limit order fills at its price | Model taker fills by default. If you use maker orders, measure real fill rates in dry-run. |
| **Survivorship bias** | Testing only coins that still exist | Not an issue for BTC/ETH. Matters if you expand the universe. |
| **Regime dependency** | Works only in 2020–21 | Require performance in each regime and in each walk-forward window |
| **Small sample** | Strong conclusions from 15 trades | ≥ 50 OOS trades, confidence intervals, Monte Carlo |
| **Benchmark neglect** | "+40%!", while buy-and-hold made +150% | Always report the benchmark side by side, with risk-adjusted metrics |
| **Backtest/live code divergence** | Research code ≠ trading code | Final validation uses the *same Freqtrade strategy file* that will trade |
| **Timezone / candle-boundary errors** | Daily candles misaligned between sources | Everything in UTC; tests from §4.4 |
| **ML leakage** (Phase 5) | Features computed with future data, random train/test splits on time series | Purged/embargoed time-series cross-validation |

### 5.4 Validation procedure (Phase 2, in order)

1. Implement the strategy in Freqtrade, then run `lookahead-analysis` and `recursive-analysis`. Fix every finding.
2. Run the **in-sample** backtest at base costs and record it in the journal.
3. Build a **parameter robustness grid** (coarse: ≤ 3 parameters × ~5 values). Select the plateau centre.
4. Run **walk-forward OOS** over 2023–2024 (and rolling windows from 2018 onward).
5. Run the **cost stress** at 1×, 2× and 3×.
6. Run **Monte Carlo**: bootstrap the OOS trade sequence 10,000 times to get distributions of max drawdown and CAGR. Set risk limits from the **95th-percentile drawdown**.
7. Run the **random-entry benchmark**: 1,000 strategies with random entries but the same trade count and average holding time. Your strategy must beat ≥ 95% of them.
8. Run a **cross-asset check**: the same parameters on BTC and ETH, plus one unseen asset (e.g. SOL) as a test only, not for trading.
9. **Confirm on Bitvavo EUR data.**
10. **Open the holdout once.** Record the result. Accept or reject.
11. Write the **backtest report** (`research/reports/H1-gate2.md`). It should include all metrics from §1.2, the equity curve vs the benchmark, a drawdown chart, the trade list, the cost-stress table and the Monte Carlo histogram.

Useful commands (exact flags can change between versions, so check `--help`):

```bash
freqtrade download-data --exchange bitvavo --pairs BTC/EUR ETH/EUR --timeframes 1d 4h 1h --timerange 20180101-
freqtrade backtesting --strategy TrendV1 --timerange 20230101-20241231 --fee 0.0025
freqtrade lookahead-analysis --strategy TrendV1 --timerange 20220101-20241231
freqtrade recursive-analysis --strategy TrendV1 --timerange 20220101-20241231
```

---

## 6. Risk management

### 6.1 Capital rules (non-negotiable)

- [ ] The trading account holds **€100 maximum** during Phase 4. Consider the whole amount losable.
- [ ] **Never top up after losses** to "win it back".
- [ ] Spot only, **no leverage, no margin, no borrowing**.
- [ ] Only BTC and ETH, only against EUR.
- [ ] Add capital only by passing Gate 4, in steps (€100 → €250 → €500). Each step needs another 3 months of clean live results and a 24-hour cooling-off before deciding.
- [ ] Only ever trade money whose total loss would not affect your life.

### 6.2 Position sizing

**Fixed-fractional risk per trade:**

```
position size (€) = (equity × risk per trade) / stop distance (%)
```

- Risk per trade: **2% of equity** (€2 on €100).
- Stop distance: 2 × ATR(14) on daily BTC, typically about 6–8%.
- Example: €2 / 0.07 ≈ **€28 position**.
- Caps: **≤ 50% of equity per asset**, **≤ 100% total exposure** (spot can't exceed it anyway), and each order must be **≥ €5** (exchange minimum). If the computed size is below the minimum, skip the trade. Don't round up the risk.

**Alternative: volatility targeting** (for H1/H3):

```
weight = target volatility / realised volatility
```

For example, with a 25% annual target and BTC realised volatility of 50%, the weight is 0.5 (50% of equity), capped at 50% per asset. This keeps risk roughly constant as markets calm down or get wild. Implement it with Freqtrade's `custom_stake_amount`.

### 6.3 Stops and exits

- Each trade has a **protective stop** (e.g. 2–3 × ATR), set at entry and never widened.
- A **strategy exit** comes from the signal (e.g. close < SMA, or a trailing channel low).
- Optional time stop: exit if a trade hasn't moved in N days. Test it; don't assume it helps.
- With Bitvavo, stops are enforced **by the bot**, not by the exchange, so bot uptime is part of risk management.

### 6.4 Portfolio circuit breakers

| Trigger | Action | Reset |
|---|---|---|
| Daily loss > 5% of equity | Pause new entries for 24h, alert | Automatic after 24h |
| 3 stop-losses within 7 days | Pause new entries for 72h (Freqtrade `StoplossGuard`) | Automatic |
| Drawdown from equity peak > **20%** | **Stop new entries**, alert, manual review | Manual, after a written review |
| Drawdown from equity peak > **30%** | **Flatten all positions, halt the bot** | Restart only after a post-mortem and a return to Phase 2 |
| Cumulative loss > €30 (loss budget) | Halt the project's live phase | Project decision (§7, Gate 4) |

Freqtrade "protections" (`MaxDrawdown`, `StoplossGuard`, `CooldownPeriod`) cover several of these. The rest go in your watchdog.

### 6.5 Kill switch: four independent layers

1. **In-bot:** Freqtrade protections and stops (above).
2. **External watchdog** (`ops/watchdog.py`, cron every 5 minutes). It reads equity and positions from Freqtrade's REST API and from the exchange directly. On any trigger in §6.4 or §6.6, it calls the API to stop entries, force-exit all trades and stop the bot (endpoints along the lines of `stopentry`, `forceexit all`, `stop`; check the docs). Then it alerts you on Telegram.
3. **Manual from your phone:** Telegram commands `/stopentry`, `/forceexit all`, `/stop`.
4. **Last resort:** log in to the exchange website, **delete the API key**, and close positions by hand. Practise this once in Phase 3.

### 6.6 Operational risk triggers (the watchdog halts entries and alerts)

- More than 5 API errors in 10 minutes.
- Stale data: no new candle for more than 2 candle intervals.
- **Balance mismatch** between the bot's database and exchange balances of more than 2%.
- Unexpected open orders, or positions the bot didn't create.
- Exchange price deviates by more than 3% from a second source (e.g. a public ticker from another exchange).
- Clock drift of more than 1 second (exchanges reject requests with bad timestamps).

---

## 7. Phased rollout with checklists and exit criteria

Every phase ends with a **gate**. Write down the result honestly in `research/reports/`. **Failing a gate is a successful outcome of the process:** it saved you money.

### Phase 0 — Foundations (Weeks 1–2, ~25–35 h)

**Goal:** working tools, basic finance vocabulary, an exchange account ready (but not funded beyond a test amount).

- [x] Install git and Python 3.12. Add VS Code (Python + Jupyter extensions) or PyCharm Professional. Docker isn't needed locally; the server runs it.
- [ ] Activate the Student Pack offers you need now (§3.8): GitHub Pro, Copilot, JetBrains, 1Password, Termius, and one Python course. **Leave Azure and DataCamp for later**, because their clocks start at activation.
- [x] Local git repository using the layout in §3.5, with `.gitignore` *first*, `pre-commit` with `ruff`, `mypy`, `gitleaks`, and a `pytest` skeleton (done 19 Oct 2026).
- [ ] Push it to a **private** GitHub repository; CI (`.github/workflows/ci.yml`) then runs on every push.
- [ ] Python ramp for a C# developer: the language basics, then pandas (*Python for Data Analysis* by Wes McKinney is free online).
- [ ] Finance basics: read the glossary (§13) and the first chapters of *Quantitative Trading* (Ernest Chan) or *Systematic Trading* (Robert Carver).
- [x] Install Freqtrade, download sample data and **backtest the sample strategy** (done: `research/journal.md` #0).
- [ ] Read the Freqtrade strategy docs end to end.
- [ ] **Exchange** (you do this yourself): open or verify a Bitvavo account.
  - [ ] Enable 2FA with an authenticator app.
  - [ ] Check the fee shown in your account.
  - [ ] Check the exchange in the ESMA MiCA register.
  - [ ] Don't create API keys yet.
- [ ] Binance: read its EEA notices in your account. If you have funds there, decide whether to withdraw them.
- [ ] Set up a Telegram bot for notifications (token stored in `config.private.json` only).

**Exit criteria (all must hold)**
- [x] Freqtrade backtest of the sample strategy runs from your repository (native venv locally; `ops/docker-compose.yml` is for the server).
- [ ] CI/pre-commit runs, and `gitleaks` reports no secrets.
- [ ] You can explain in your own words: CAGR, max drawdown, Sharpe, Calmar, maker/taker fee, slippage, look-ahead bias.

### Phase 1 — Data and strategy research (Weeks 3–5, ~35–50 h)

**Goal:** a trustworthy dataset and at least one hypothesis that survives the pre-screen.

- [x] Ingest scripts for the Binance public data, Kraken EUR history and Bitvavo (`python -m aitradingbot.ingest`, done 19 Oct 2026).
- [x] Data validation tests (§4.4) all green, with a data manifest per series (`research/reports/data-validation.md`, journal #1).
- [x] Hypothesis cards for H1, H2 and H3, registered **before** testing (19 Oct 2026; shared rules in `research/hypotheses/_CONVENTIONS.md`). H4 not registered.
- [x] Your own small backtester, unit-tested on a hand-calculated toy example (19 Oct 2026). It's a ~130-line candle loop rather than vectorised, for transparent band and cash handling. Next-open fills are tested against a hand-worked 4-candle example and look-ahead guards. Plus `aitradingbot.analysis.prescreen`, which applies the registered Gate 1 rules as code.
- [x] Pre-screen each hypothesis on development data at 2× costs vs buy-and-hold (19 Oct 2026): **H1, H2 and H3 all killed at Gate 1** (journal #5–#7, `research/reports/prescreen-H*.md`).
- [x] Iterate (kill/iterate rule below): **H4** registered 20 Oct 2026, the trend filter with volatility sizing. It is *post-hoc*, informed by the H1–H3 results, and uses the first of the two allowed new hypotheses. **Killed at Gate 1** (20 Oct 2026, journal #8): 46.7% drawdown, no plateau, 940%/yr turnover. **H5** registered 20 Oct 2026, H4's rule fixed at N=150 and 30% target vol. It is post-hoc twice over, its parameters chosen from H4's grid, so its real test is Gate 2 on the validation split. It is the last allowed new hypothesis. **Killed at Gate 1** (20 Oct 2026, journal #9): everything passed except the plateau, missed by 0.1 point (a neighbour 30.1% below vs the 30% limit).
- [ ] Robustness heatmaps and a cross-asset check for the survivors. *(Not applicable: no survivors.)*
- [x] Every run logged in `research/journal.md` (#0–#9; 63 variants tested in total).

**Exit criteria**
- [ ] At least one hypothesis passes the pre-screen: Calmar ≥ 1.2× buy-and-hold at 2× costs on development data, on a stable plateau, working on both BTC and ETH.

**Kill / iterate criteria**
- [x] If none pass, register up to 2 new hypotheses and repeat once. *(Done: H4 and H5, journal #8–#9.)*
- [x] If those fail too, **stop**. Consider monthly DCA instead, and count the project as a learning success. (This is a perfectly respectable outcome.) **Triggered 20 Oct 2026** (journal #9) and **confirmed by the owner the same day**: Phase 1 closed, summary in `research/reports/phase1-summary.md`. The validation and holdout splits are still unopened.

### Phase 2 — Rigorous backtest (Weeks 6–9, ~40–60 h)

**Goal:** an honest verdict on the best candidate using the full methodology (§5).

- [ ] Implement it as a Freqtrade strategy (`user_data/strategies/TrendV1.py`) with position sizing from §6.2.
- [ ] `lookahead-analysis` clean; `startup_candle_count` set via `recursive-analysis`.
- [ ] In-sample, robustness grid, walk-forward, cost stress, Monte Carlo, random-entry benchmark, cross-asset check, EUR confirmation (§5.4, steps 1–9).
- [ ] Holdout opened **once** (step 10).
- [ ] Risk limits from §6.4 cross-checked against the Monte Carlo 95th-percentile drawdown. Tighten them if needed.
- [ ] Backtest report written.

**Exit criteria (Gate 2: all the research metrics in §1.2)**
- [ ] OOS Calmar ≥ 1.2× benchmark, and OOS max drawdown ≤ 35%.
- [ ] Positive at 2× costs.
- [ ] Parameter ±25% keeps ≥ 70% of the Sharpe ratio.
- [ ] Beats ≥ 95% of random-entry runs.
- [ ] Profitable in ≥ 60% of walk-forward windows.
- [ ] ≥ 50 OOS trades, or the result is explicitly labelled low-confidence and you consciously accept that.
- [ ] Holdout within the Monte Carlo expectations.

**Kill criteria**
- [ ] If the strategy fails Gate 2 → take the next hypothesis that passed the pre-screen into Phase 2. If 3 hypotheses have failed Gate 2 (or none are left), **stop**, using the same "DCA instead, learning success" outcome as Phase 1.
- [ ] Never "fix" a strategy by re-tuning it until it passes the holdout.

### Phase 3 — Paper trading (Weeks 10–17, minimum 8 weeks; ~30–40 h to build, then ~1–2 h/week)

**Goal:** prove the *implementation and operations*, not the edge. A daily strategy makes only a handful of trades in 8 weeks, which is far too few to judge profitability, but enough to catch bugs.

- [ ] Set up the free host: the Azure checklist in §3.7, plus Oracle if you want the shadow/standby host now.
- [ ] Freqtrade dry-run with `dry_run: true`, `dry_run_wallet: 100`, `stake_currency: EUR` and a **pinned** Docker image, running 24/7 **on the Azure VM**. Paper trading on the machine that will trade live gives the best parity.
  - [ ] While the VM is being set up, you can start on your Windows PC: disable sleep, set Windows Update active hours, and make Docker start automatically. Move to the VM as soon as it's ready.
- [ ] Measure memory use on the 1 GB VM (peak, swap use). If it's too tight, move to the Oracle A1 VM and make that the live host (Pay As You Go upgrade first, §3.7).
- [ ] **Engineering canary** (optional but recommended): a second dry-run bot running a faster 1h/4h strategy, *only* to exercise order paths more often. Not for trading decisions.
- [ ] Monitoring live: Telegram trade/error alerts, Healthchecks.io heartbeat, daily report (§9.1).
- [ ] Watchdog/kill switch implemented. **Fire drills** done and logged:
  - [ ] simulate a drawdown trigger;
  - [ ] kill the network;
  - [ ] corrupt/stale data (stop the data feed);
  - [ ] manual `/forceexit all`;
  - [ ] the API-key revocation procedure (on a test key).
- [ ] Weekly **signal parity check**: replay the same period in backtesting and compare trades with dry-run.
- [ ] Runbook (`ops/runbook.md`) written: start, stop, upgrade, restore, kill, contacts and links.
- [ ] Confirm the live host's measured uptime is ≥ 99%. If it isn't, switch to the next host in §3.7 and re-measure.
- [ ] Create **trade-only API keys** (no withdrawal permission, IP-whitelisted) only near the end of this phase (§8.4).

**Exit criteria (Gate 3)**
- [ ] ≥ 8 weeks continuous, including at least the last 4 on the host that will run live; uptime ≥ 99%.
- [ ] Memory on the live host stays below 80% of RAM, with only light swap use.
- [ ] 100% signal parity (or every difference explained and fixed).
- [ ] Simulated fills vs market prices within the assumed slippage.
- [ ] 0 unhandled exceptions in the final 2 weeks.
- [ ] All fire drills passed within ≤ 5 minutes.
- [ ] Paper P&L not worse than the 5th percentile of the Monte Carlo expectation for that period. This is a sanity check, not proof.

**Kill / rollback criteria**
- [ ] A parity bug or unexplained behaviour → fix it and restart the 8-week clock if the fix touched signal or order logic.

### Phase 4 — Small live (Weeks 18–30, minimum 12 weeks; ~1–2 h/week plus reviews)

**Goal:** confirm that real fills, fees and operations match expectations with real money at stake.

- [ ] Deposit **€100** via SEPA. Check the deposit fee first.
- [ ] Live config: `dry_run: false`, the same pinned image and strategy file as in paper.
- [ ] **Keep the dry-run bot running in parallel as a shadow**, on the Oracle VM (or on the same VM if memory allows). Live and shadow should make the same decisions.
- [ ] Daily 2-minute check; weekly review (§9.2); monthly report vs backtest and benchmark.
- [ ] Track realised fees and slippage per trade vs the model.
- [ ] Export trades monthly for tax records (§8.2).

**Exit criteria (Gate 4: continue, and optionally scale)**
- [ ] ≥ 12 weeks live with 0 risk-rule breaches and no unplanned manual interventions.
- [ ] Realised costs ≤ 1.5× modelled.
- [ ] Live trades = shadow trades = backtest replay, with P&L differences explained by costs.
- [ ] Drawdown within limits; cumulative loss ≤ €30.
- [ ] Scale-up (optional) follows the capital rules in §6.1, in steps, with a cooling-off day before deciding.

**Kill criteria**
- [ ] Drawdown > 30%, loss budget hit, or unexplained divergence → halt, post-mortem, back to Phase 2 (or end the project).

### Phase 5 — Evaluating ML / LLM components (offline research from ~Week 14; forward test ~Weeks 22–34)

**Precondition:** Gate 2 passed. Phase 3/4 waiting time is when you do this research.

**Key honest point: crypto price data at slow timeframes is sample-starved.** A daily trend system produces perhaps 100–200 trades across 2018–2026, and BTC has only about 3,000 daily candles. ML models need far more samples than that to learn reliably. **Overfitting is the default outcome**, not an edge case.

#### Options compared for your skill level

| Option | What it is | Learning curve for you | Data needs | Can it be backtested honestly? | Extra cost | Verdict |
|---|---|---|---|---|---|---|
| M0. Better rules | Improve the rule-based system (e.g. volatility filter) | None | Existing | Yes | €0 | Baseline to beat |
| **M1. Regime filter** | Simple statistical classifier of market regime (trend strength, volatility level; optionally a 2-state hidden Markov model). Strategy on/off or size up/down. | Low–medium | Low (few features) | Yes, with walk-forward | €0 | ✅ **Start here** |
| **M2. Meta-labelling filter** | Gradient-boosted trees (LightGBM via FreqAI or scikit-learn) predict whether *a rule signal* will be profitable. Take or size trades by that probability. (López de Prado's "meta-labelling".) | Medium (2–4 weeks of ML basics) | Needs **hundreds to thousands** of labelled signals, so pool assets/timeframes | Yes, but only with **purged + embargoed time-series cross-validation** | €0 | ✅ Second, **if** sample size allows |
| M3. LLM sentiment / news filter | An LLM scores headlines/social posts. Skip entries in strongly negative regimes, etc. | Low to code, high to evaluate | A news feed (free ones are limited; historical archives often cost money) | **No.** See below. Forward test only. | API fees (set a hard monthly cap) | ⚠️ Optional shadow experiment only |
| M4. Deep-learning price prediction (LSTM/Transformers) | Predict prices or returns directly | High | Very high | Extremely easy to fool yourself | €0–€€ | ❌ Not recommended |
| M5. Reinforcement learning (FreqAI supports it) | An agent learns to trade by trial and error | High | Very high | Notoriously unstable | €0 | ❌ Not recommended |

**Why LLM sentiment can't be backtested honestly.** An LLM used today has seen the internet *after* the events in your backtest. It "knows" which 2022 headline preceded a crash. Backtest results are therefore biased upward, even if you only ask it to "score sentiment". Historical news archives are also often incomplete or paid. The only honest test is **forward**: log the LLM's scores daily in dry-run for several months, then compare the filtered strategy against the baseline. With a daily strategy, that yields very few decisions, so expect **inconclusive results** after 3 months. Know that going in.

#### Recommended path

1. **M1 regime filter** (Weeks ~14–18): 2–3 simple features with a walk-forward test. Cheap, interpretable, and it teaches the ML evaluation workflow.
2. **M2 meta-labelling** (Weeks ~18–24): only if you can build ≥ ~500 labelled signals (e.g. pooling BTC + ETH and 4h + daily signals). Learn scikit-learn basics first (activate DataCamp's free 3 months from your Student Pack here), then purged cross-validation.
3. **M3 LLM** (Weeks ~22–34, optional): a forward-only shadow log in dry-run. Never in the live decision path until it passes the same acceptance test.

#### Acceptance test (applies to M1–M3)

The ML/LLM variant goes live **only if all of these hold:**
- [ ] It beats the rule-based baseline in **walk-forward OOS** by a margin set in advance (e.g. Sharpe +0.2, *or* max drawdown at least 20% smaller with no more than 10% lower CAGR).
- [ ] It beats a **random filter** that drops the same fraction of trades, in ≥ 95% of 1,000 runs. Otherwise the "improvement" is just luck from trading less.
- [ ] Its features have been checked for leakage, and its training/test splits are purged and embargoed.
- [ ] The improvement holds at 2× costs and across both assets.
- [ ] The added complexity is worth it: you can explain *why* it works, and it doesn't add a fragile dependency (e.g. a paid API) to the live path.

If any of these fail, **keep the rules**. "ML didn't help" is a common and legitimate finding.

---

## 8. Legal, tax and security

### 8.1 Regulatory (EU / MiCA)

- **Trading your own money with your own bot is legal** and needs no licence.
- **Don't** manage other people's money, sell signals, or run the bot "for friends". Those can be regulated services under MiCA.
- Use only exchanges authorised under MiCA (a crypto-asset service provider, CASP). **Check ESMA's register yourself.** Transitional periods ended by 1 July 2026, which is why Binance stopped serving EEA users.
- **Market-abuse rules apply to crypto** under MiCA. Don't run anything that resembles manipulation: placing and quickly cancelling orders to move prices (spoofing/layering), wash trading against yourself, or pump coordination. With BTC/ETH at €100 you're nowhere near this, but don't build such logic.
- **Exchange terms of service:** respect API rate limits; follow rules on one account per person and sub-accounts. Bitvavo may require an `operatorId` for API orders (Freqtrade documents where to set it).

### 8.2 Tax (Bulgaria)

What multiple sources agree on (verify everything with the NRA or a Bulgarian accountant):

- Crypto gains of Bulgarian tax residents are taxed at a **flat 10%** on the **annual net result** (gains minus losses within the year).
- **Every disposal is a taxable event:** selling crypto for EUR, and (per at least one guide) crypto-to-crypto swaps. A bot can generate many events, so you need a complete trade log.
- Report on the **annual tax return**. Tax-software guides cite **Appendix 5, code 508**, with a crypto sub-code. File and pay by **30 April** of the following year (the 2026 return is due 30 April 2027).
- **DAC8:** since **1 January 2026**, exchanges collect your transaction data and report it to tax authorities. Assume the NRA will see your trades.
- **Bulgaria adopted the euro on 1 January 2026.** EUR-denominated trading means no BGN conversion for 2026 onwards. For pre-2026 holdings, the conversion rate is fixed at 1.95583 BGN per EUR.

**Uncertain or conflicting, so ask a professional:**
- Whether a 10% statutory expense deduction applies.
- Whether losses carry forward (one source says no).
- Which cost-basis method applies (FIFO vs weighted average).
- How staking is treated.
- Whether frequent automated trading could ever be reclassified as business income.

**Practical steps:**
- [ ] Export the full trade history from the exchange **and** Freqtrade's database monthly. Back it up.
- [ ] Keep a simple ledger: date, pair, side, quantity, price, fee, EUR value. Freqtrade's DB plus a small export script covers this.
- [ ] Before your first filing, get a one-off consultation or use NRA guidance. A consult may cost more than your capital, but the filing obligation exists regardless of profit size.
- [ ] Keep records for **several years** (ask how long; 5–10 years is a common rule of thumb).

### 8.3 Exchange and broker rules checklist

- [ ] The account is verified (KYC) in your own name; the bot trades only your account.
- [ ] Read the API terms and rate limits; Freqtrade's `rateLimit` setting is left at a safe value (increase it if you see rate-limit errors; never decrease it).
- [ ] Use a **sub-account** for the bot if the exchange offers one, so the bot can't touch your other holdings.
- [ ] Know the exchange's maintenance and incident status page, and subscribe to it.

### 8.4 Security checklist

**API keys**
- [ ] Permissions: **read + trade only. Never withdrawal.**
- [ ] **IP whitelist** the live host's static public IP. On a home connection with a changing IP, the key stops working when the IP changes. That fails safe, but it's annoying, which is one reason the plan prefers a cloud VM.
- [ ] Separate keys per environment. Dry-run needs **no keys at all**.
- [ ] Store keys only in `config.private.json` or environment variables. Gitignored. File permissions `600` on the server.
- [ ] Rotate every 90 days and immediately if leaked or in any doubt. Delete unused keys.
- [ ] **Never paste API keys, seed phrases or passwords into chats, AI assistants (including this one), screenshots or issue trackers.**

**Accounts**
- [ ] 2FA with an authenticator app (not SMS) on the exchange **and** your email account.
- [ ] Withdrawal address whitelist with a time lock on the exchange; anti-phishing code enabled.
- [ ] Unique, generated passwords for the exchange, email and cloud accounts, stored in 1Password (Student Pack) together with the 2FA recovery codes.
- [ ] Cloud accounts (Azure, Oracle): MFA on, cost/budget alerts set, and only free-eligible resources created.

**Server (cloud VM or home device)**
- [ ] SSH key login only, no password login, no root login.
- [ ] Firewall: only SSH open.
- [ ] Automatic security updates; `fail2ban`.
- [ ] **FreqUI and the REST API bound to localhost.** Access them through an SSH tunnel. **Never expose them to the internet.**
- [ ] The Telegram bot is restricted to your chat ID.

**Code and supply chain**
- [ ] Install Freqtrade only from the official repository or Docker image, pinned by version.
- [ ] **Never run "profitable strategies" from GitHub, Discord or Telegram without reading every line.** Malicious strategies can steal API keys.
- [ ] Be aware of scams: "AI trading bots" sold online, guaranteed returns, "account managers" who contact you. None are legitimate.

---

## 9. Monitoring, maintenance and failure modes

### 9.1 Monitoring and alerts

| Signal | Source | Threshold | Channel |
|---|---|---|---|
| Bot alive | Heartbeat ping (cron → Freqtrade API `/ping` → Healthchecks.io) | Missed for 15 min | Email + Telegram |
| Trade opened or closed | Freqtrade | Every event | Telegram |
| Errors and warnings | Freqtrade logs | Any error | Telegram |
| Drawdown / daily loss | Watchdog | §6.4 levels | Telegram (+ automatic action) |
| Balance mismatch | Watchdog (bot DB vs exchange) | > 2% | Telegram + halt entries |
| Stale data | Watchdog | > 2 candle intervals | Telegram + halt entries |
| Daily report | Script | Daily 08:00 | Telegram: equity, positions, P&L vs benchmark, parity status |
| Disk space / memory | Server | > 80% (watch memory closely on a 1 GB VM) | Email |
| Free-credit balance | Azure cost alert | < $20 remaining | Email |

### 9.2 Routines

- **Daily (2 min):** read the daily report; confirm the heartbeat is green.
- **Weekly (30 min):**
  - parity check (dry-run/live vs backtest replay);
  - review errors;
  - reconcile balances;
  - log notes in the journal.
- **Monthly (1–2 h):**
  - performance vs backtest expectations and vs the benchmark;
  - realised cost review;
  - trade export for taxes;
  - Azure credit balance and the expiry dates of your free offers (Azure 12 months, student status).
  - Update Freqtrade by testing the new pinned version **in dry-run for a week before live**.
- **Quarterly:**
  - re-validation: run the strategy on the newest data as fresh OOS;
  - check that results remain within Monte Carlo expectations;
  - rotate API keys.
  - **Don't re-optimise parameters** on recent data outside the walk-forward protocol.

### 9.3 Failure modes

| Failure | Symptom | Detection | Mitigation |
|---|---|---|---|
| Home device sleeps, reboots for updates, or loses power | Bot silent; stops not enforced | Heartbeat alert | Power settings, auto-start Docker, laptop battery as a UPS; cloud VM for live |
| Free cloud VM stops: Azure credit used up (subscription disabled), Oracle idle reclamation, capacity or policy change | Bot silent; stops not enforced | Heartbeat alert, provider email, credit alert | Monitor credit; switch hosts with the same compose file (§3.7) |
| Free offer ends: Azure's 12 months, student status ends, offer changes | Host or tool goes away | Calendar reminder 1 month ahead | Renew Azure for Students yearly while eligible; move to Oracle Always Free; keep backups off the host |
| Out of memory on a 1 GB VM | Bot killed or restarting | Memory alert, Docker restart count | 2 GB swap; fewer pairs/indicators; move to Oracle A1 (12 GB) |
| Exchange API outage or maintenance | Order errors, timeouts | Error alerts, exchange status page | Freqtrade retries; watchdog halts entries after repeated errors |
| Rate limiting | "Rate limit exceeded" | Logs | Raise `rateLimit`; fewer API calls |
| Clock drift | Timestamp/nonce errors | Logs, clock check | Time sync enabled (WSL2 clocks can drift after sleep) |
| Partial fills or rejected orders | Positions differ from intent | Reconciliation | Freqtrade handles most; watchdog mismatch check |
| Duplicate orders after a restart | Unexpected positions | Reconciliation | Freqtrade persists state in SQLite; never run two bots on one account/sub-account |
| Stale or bad data (bad tick) | Strange signals | Stale-data / price-deviation checks | Halt entries; cross-source price check |
| Exchange changes its API / CCXT update | Errors after an upgrade | Errors in dry-run first | Pinned versions; upgrade dry-run first |
| Wrong config deployed (e.g. live instead of dry-run) | Real orders unexpectedly | Startup Telegram message shows the mode | Separate config files per mode; checklist before deploying |
| API key leaked | Unknown activity | Exchange login/API alerts | No withdrawal rights, IP whitelist, rotate immediately |
| SQLite DB corruption or disk full | Bot crash | Heartbeat, disk alert | Daily DB backup copied off the host; disk monitoring |
| Flash crash / gap through a stop | Loss larger than planned | Trade alerts | Small position sizes; accept as a known risk; no leverage |
| Pair delisted or trading halted | Can't exit | Exchange announcements | Majors only; follow exchange announcements |
| **Strategy decay** (edge disappears) | Slow underperformance | Monthly report vs Monte Carlo band | Retire the strategy if it's below the 5th-percentile band for 2 consecutive quarters, or on a Gate-4 breach |
| **Silent failure** (bot "running" but not trading) | No trades for longer than expected | Expected-trade-frequency alert; parity check | Weekly parity check |

### 9.4 Runbook skeleton (`ops/runbook.md`)

- How to start, stop and restart (commands).
- How to switch between dry-run and live (checklist).
- How to upgrade (dry-run first; how to roll back).
- **Emergency:** Telegram commands → watchdog manual trigger → exchange website key deletion → manual close.
- How to restore the database from backup.
- Contacts and links: exchange support, status page, ESMA register, your tax notes.

---

## 10. Timeline and milestones

At 10–20 h/week. **The calendar is limited by the required paper and live durations, not by coding.** Use the waiting time for Phase 5 research and hardening. Add ~25% slack: first projects run late.

| Weeks | Phase | Effort | Milestone |
|---|---|---|---|
| 1–2 | P0 Foundations | 25–35 h | **M0:** Freqtrade sample backtest runs from your repo in Docker; pre-commit/CI green; exchange account verified |
| 3–5 | P1 Data and research | 35–50 h | **M1:** validated dataset with tests; ≥ 2 hypothesis cards pre-screened; a candidate passes Gate 1 (or the project stops) |
| 6–9 | P2 Rigorous backtest | 40–60 h | **M2:** Gate 2 report; holdout opened once; accept/reject |
| 10–17 | P3 Paper trading | 30–40 h + 1–2 h/week | **M3:** free Azure host running (Oracle optional); 8 weeks of dry-run; fire drills passed; runbook; Gate 3 |
| 14–24 | P5a ML research (offline, parallel) | 40–70 h | **M5a:** regime filter and (if feasible) meta-labelling evaluated by walk-forward; go/no-go for a forward test |
| 18–30 | P4 Small live (€100) | 1–2 h/week + reviews | **M4:** 12+ weeks live; Gate 4: stop, continue, or scale in steps |
| 22–34 | P5b ML/LLM forward shadow test | ~1 h/week + analysis | **M5b:** acceptance test for any ML/LLM component |
| ~34 | Project review | 4–6 h | **M6:** written retrospective: what worked, what didn't, continue or stop |

**Total: about 7 months (≈ May 2027) to a live verdict on the rule-based system; about 8 months (≈ June 2027) to an ML/LLM verdict.** Early stops at Gate 1 or Gate 2 are possible, and they're not failures of the project.

---

## 11. Budget and cost levers

### 11.1 Budget (target: €0/month overhead)

| Item | Cost | When |
|---|---|---|
| Trading capital | **€100** (fully at risk) | Phase 4 |
| Software (Freqtrade, Python, Docker, VS Code / PyCharm via Student Pack) | €0 | All |
| Code hosting and CI (GitHub Pro via Student Pack) | €0 | All |
| Data | €0 (public sources) | All |
| Monitoring (Telegram, Healthchecks.io free tier; optional Student Pack tools) | €0 | P3+ |
| Hosting | €0: Azure for Students VM (no card; $100 credit covers any disk/IP charges), Oracle Always Free as second host (§3.7) | P3+ |
| Fallback host | Electricity only (≈ €7–18/year), and only if a device you already own is ever used | If needed |
| Password manager (1Password via Student Pack) | €0 for 2 years | P0+ |
| SEPA deposit / withdrawal fees | Depends on bank and exchange; check before depositing and prefer free options | P4 |
| LLM API (optional) | Use a free tier if one exists; otherwise a few €/month with a hard cap. Only for the shadow experiment. | P5b |
| Tax consultation (optional) | Use free NRA guidance first; pay only if questions remain | Before the first filing |

### 11.2 Cost levers: what decides whether you can be profitable

With hosting at €0, **trading fees are by far the biggest cost**, followed by tax on any gains. In order of impact:

1. **Trade less.** Fee drag scales with round trips (§0.1). A daily strategy with ~10 full-size round trips a year at 0.6% costs ~6% a year. Fifty round trips would cost ~30%.
2. **Use maker (limit) orders where possible.** On Bitvavo's entry tier, maker is 0.15% vs 0.25% taker, which saves ~0.2% per round trip. Freqtrade can place limit entries at the best bid and fall back to a market order after a timeout (`order_types`, `entry_pricing`, `unfilledtimeout`). **Backtest with taker fees anyway.** Count maker savings as a bonus only once dry-run shows real fill rates: missed fills can cost more than the fee saved.
3. **Avoid hidden small costs:** small-balance conversion fees, card deposits (SEPA is usually cheapest), and needless withdrawals.
4. **Don't pay for anything the plan can do for free:** signals, "premium" strategies, paid data, paid bots, paid servers.
5. **Tax:** 10% of net annual gains (§8.2), so a €20 gross profit becomes ~€18. Track it so it doesn't surprise you.

**Honest bottom line:** with €0 overhead, a small net profit is possible *if* the strategy has a real edge. Even then, at €100 it will be a few euros to a few tens of euros a year. The plan treats profit as a target, not an expectation.

---

## 12. What I'm unsure about: verify these yourself

| Item | Status | How to verify |
|---|---|---|
| Bitvavo entry fees (0.15% / 0.25%) | From the official fee page via a search summary; my direct page fetch was blocked | Fee shown in your account |
| OKX EEA and Bybit EU fees | Unverified / conflicting | Their official fee pages and your account |
| Exchange MiCA statuses | From reviews and news, not from the register itself | ESMA MiCA register |
| Binance EEA restrictions | From multiple news reports (June–July 2026) | Binance's notices in your account |
| Bulgarian tax details (appendix/code, deductions, loss carry-forward, cost basis, staking, business-income risk) | Partly conflicting sources | NRA (nra.bg) or a Bulgarian accountant |
| DAC8 transposition into Bulgarian law and NRA reporting deadlines | Unverified | NRA |
| Bitvavo historical candle depth via the API | **Answered:** BTC/EUR and ETH/EUR from 8 Mar 2019 (ETH/EUR 1h from 16 Nov 2019). It doesn't cover the 2018 bear market. | — |
| Freqtrade + Bitvavo reliability | Community-tested only; no stop-loss on exchange | Dry-run in Phase 3 |
| LEAN (C#) support for Bitvavo/OKX EEA | Not confirmed | LEAN docs, if you consider option B |
| Future strategy performance | **Unknowable.** Historical results can and often do fail to repeat. | Phases 3–4 |
| Azure for Students VM details: RAM of B1s / B2ats v2 (I believe 1 GB), whether disk and public IP are covered, EU-region eligibility | Partly from memory; the official page doesn't list them | Azure portal when creating the VM |
| Freqtrade on a 1 GB VM | Below Freqtrade's advised 2 GB, so not tested | Measure in Phase 3 |
| Oracle: does idle reclamation apply after a Pay As You Go upgrade? Card at sign-up? | Official docs don't say; community reports say upgraded accounts are exempt | Oracle support, and your heartbeat data |
| Bitvavo API access from non-EU data centres | Unknown, so the plan avoids it | Bitvavo support |
| Student Pack offer terms | Change often (DigitalOcean left in 2026). Heroku's card requirement comes from a third-party guide. | education.github.com/pack before redeeming |
| Your electricity price | One source: ~€0.29/kWh (mid-2025) | Your electricity bill |
| Paid VPS prices (only if ever needed) | Change over time | Provider websites |

---

## 13. Glossary

- **OHLCV:** a candle's Open, High, Low, Close and Volume.
- **Spot:** buying and holding the actual coin. No borrowing, so the most you can lose is what you put in.
- **Maker / taker fee:** a *maker* order rests on the order book (limit order) and usually pays less. A *taker* order fills immediately (market order) and pays more.
- **Slippage:** the difference between the price you expected and the price you got.
- **Round trip:** a buy plus the later sell. Cost ≈ 2 × (fee + slippage).
- **Return / CAGR:** compound annual growth rate = (final ÷ initial)^(1/years) − 1.
- **Drawdown:** the drop from the highest equity so far. **Max drawdown** is the worst such drop.
- **Volatility:** how much returns swing. Annualised volatility ≈ standard deviation of daily returns × √365 (crypto trades every day).
- **Sharpe ratio:** annualised return ÷ annualised volatility (ignoring the risk-free rate for simplicity). Higher means more return per unit of risk.
- **Calmar ratio:** CAGR ÷ max drawdown. Very intuitive for crypto.
- **Profit factor:** gross profits ÷ gross losses. Above 1 is profitable; above ~1.3 is a reasonable minimum after costs.
- **Win rate / expectancy:** the percentage of winning trades / the average profit per trade. Trend systems often win only 30–40% of trades but have larger wins than losses.
- **Exposure / time in market:** the fraction of time you hold a position.
- **In-sample / out-of-sample (OOS):** data used to design the strategy / data it has never seen.
- **Walk-forward analysis:** repeatedly fit on a past window, then test on the next unseen window.
- **Look-ahead bias:** accidentally using information that wasn't available at decision time.
- **Overfitting:** tuning a strategy to past noise, so it fails on new data.
- **ATR (Average True Range):** a volatility measure in price units, often used to set stops.
- **SMA / EMA:** simple and exponential moving averages.
- **Donchian channel:** the highest high and lowest low over N periods.
- **DCA (dollar-cost averaging):** buying a fixed amount on a schedule regardless of price. The "do-nothing-clever" benchmark.
- **MiCA:** the EU's Markets in Crypto-Assets Regulation, which licenses crypto exchanges (CASPs).
- **DAC8:** the EU directive requiring crypto platforms to report users' transactions to tax authorities.

---

## 14. Sources and further reading

**Regulation, exchanges and fees (checked 19 Oct 2026)**
- [Is Binance MiCA authorised? (Tangem)](https://tangem.com/en/learning-hub/post/is-binance-mica-authorised/)
- [Binance MiCA licence: EU lockout, July 2026 (Zyphe)](https://www.zyphe.com/resources/news/binance-mica-licence-eu-lockout-july-2026)
- [Binance prepares to suspend services across the EU (AML Intelligence)](https://www.amlintelligence.com/2026/06/news-binance-prepares-to-suspend-services-across-the-eu/)
- [MiCA takes effect: Binance locked out of EU (The Crypto Times)](https://www.cryptotimes.io/2026/07/01/mica-takes-effect-binance-locked-out-of-eu-but-reassures-users/)
- [Does Binance have a MiCA licence? (CASP Tracker)](https://casptracker.eu/exchange/binance/)
- [ESMA — MiCA (interim register of CASPs)](https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/markets-crypto-assets-regulation-mica)
- [Kraken — Cross-platform fee tier changes (July 2026)](https://support.kraken.com/articles/cross-platform-fee-tier-changes)
- [Kraken — Fee schedule](https://www.kraken.com/features/fee-schedule)
- [Bitvavo — Fees](https://bitvavo.com/en/fees)
- [Bitvavo — Countries](https://bitvavo.com/en/countries) · [Bitvavo — In which countries can I use Bitvavo?](https://support.bitvavo.com/hc/en-us/articles/4405238046993)
- [Bitvavo API — BTC-EUR market info](https://api.bitvavo.com/v2/markets?market=BTC-EUR)
- [Bybit EU comparisons (CryptoTicker)](https://cryptoticker.io/en/comparison/bitvavo-vs-bybit/)
- [OKX fees overview (BitDegree)](https://www.bitdegree.org/crypto/tutorials/okx-fees)

**Tax (Bulgaria) and reporting**
- [Bulgaria crypto tax guide 2026 (Waltio)](https://help.waltio.com/en/articles/14739037-bulgaria-crypto-tax-guide-2026-the-complete-guide)
- [Crypto taxes in Bulgaria 2026 (Anagami)](https://www.anagami.bg/en/blog/crypto-taxes-in-bulgaria-2026crypto-to-crypto-staking-lending-airdrops-defi-yield-farming/)
- [Bulgaria crypto tax rates (TaxAtlas)](https://taxatlas.io/country/bulgaria/crypto-tax)
- [DAC8 + CARF Bulgaria 2026 (Innovires)](https://innovires.com/tax-residency/blog/dac8-carf-bulgaria-crypto-reporting-2026.html)
- [DAC8 reporting requirements (Grant Thornton)](https://www.grantthornton.nl/en/insights-en/tax/dac8-reporting-requirements-for-crypto-and-digital-asset-service-providers-in-the-eu/)
- [Bulgaria adopts euro as of 1 January 2026 (European Commission)](https://trade.ec.europa.eu/access-to-markets/en/news/bulgaria-adopts-euro-1-january-2026)

**Hosting and Student Pack (checked 19 Oct 2026)**
- [GitHub Student Developer Pack](https://education.github.com/pack)
- [Azure for Students](https://azure.microsoft.com/en-us/free/students)
- [Student Pack benefits, verified Sept 2026 (StudentDevGuide)](https://studentdevguide.dev/github-student-developer-pack-benefits/)
- [DigitalOcean student credit ended (AIStudentDiscount)](https://aistudentdiscount.com/digitalocean-github-student-developer-pack-credits/)
- [Oracle Cloud — Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Oracle Cloud — Free tier FAQ](https://www.oracle.com/cloud/free/faq/)
- [Oracle Cloud Always Free, 2026 limits (Site2US)](https://site2us.com/en/servers/oracle-cloud-free-tier)
- [GCP free tier guide 2026 (AgentDeals)](https://agentdeals.dev/gcp-free-tier-2026)
- [AWS free tier in 2026 (InfraTally)](https://infratally.com/articles/aws-free-tier-2026/)
- [Bulgaria electricity prices (GlobalPetrolPrices)](https://www.globalpetrolprices.com/Bulgaria/electricity_prices/)

**Freqtrade**
- [Freqtrade documentation](https://www.freqtrade.io/en/stable/) · [Exchange-specific notes](https://www.freqtrade.io/en/stable/exchanges/)
- [Lookahead analysis](https://www.freqtrade.io/en/stable/lookahead-analysis/) · [Recursive analysis](https://www.freqtrade.io/en/stable/recursive-analysis/)

**Research and books**
- Chague, De-Losso & Giovannetti (2019), *Day Trading for a Living?*
- Barber, Lee, Liu & Odean, *The Cross-Section of Speculator Skill: Evidence from Day Trading*
- Moskowitz, Ooi & Pedersen (2012), *Time Series Momentum*, Journal of Financial Economics
- Liu & Tsyvinski (2021), *Risks and Returns of Cryptocurrency*, Review of Financial Studies
- Liu, Tsyvinski & Wu (2022), *Common Risk Factors in Cryptocurrency*, Journal of Finance
- Bailey & López de Prado (2014), *The Deflated Sharpe Ratio*
- Ernest Chan, *Quantitative Trading* (2nd ed.): practical starting point
- Robert Carver, *Systematic Trading*: position sizing and risk, very relevant
- David Aronson, *Evidence-Based Technical Analysis*: data snooping and statistical testing
- Marcos López de Prado, *Advances in Financial Machine Learning*: for Phase 5 (meta-labelling, purged cross-validation)
- Wes McKinney, *Python for Data Analysis* (free online): pandas

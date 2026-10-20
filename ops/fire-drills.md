# Fire drills

Phase 3 / Gate 3 (PROJECT_PLAN.md): every drill must reach a safe state within **5 minutes** of the trigger.
Drills run against a separate **drill bot** (port 8081, `user_data/tradesv3.drill.sqlite`, log
`user_data/logs/drill.log`), never against the main paper bot, so the 8-week dry-run and its parity checks
stay clean. The drill bot is a dry-run copy: paper positions only.

The time to a safe state = detection + action. The watchdog checks every 2 minutes, so the worst-case
detection is 2 minutes; the times below are from trigger to safe state once the trigger is seen.

## 2026-10-20 (Windows PC, Freqtrade 2026.9, H5TrendVol dry-run)

| # | Drill | How | Result | Time |
|---|---|---|---|---|
| D1 | Manual emergency: `/stopentry` → `/forceexit all` → `/stop` | REST API (Telegram not set up yet) | ✅ 2 positions closed, bot stopped | 2.3 s |
| D2 | Drawdown > 30% | Watchdog run with an equity peak far above equity | ✅ Watchdog: drawdown critical → `forceexit all` + `stop`; 2 positions closed | 3.1 s |
| D3 | Stale data | Watchdog run with the clock moved 4 days ahead (candles look 4 days old) | ✅ `stopentry`; positions kept, state paused | 1.3 s |
| D4 | Bot crash and recovery | Hard-kill the drill bot's processes, then restart | ✅ Watchdog: "bot API unreachable" (critical). Restart: API up in 7 s, the same open trades (ids 5, 6) restored from SQLite | 7 s to recover |
| D5 | Exchange unreachable (network loss) | Restart with ccxt's `httpsProxy` pointed at a dead port | ✅ Freqtrade retried 4×, logged "Could not load markets" and exited; watchdog: "bot API unreachable" (critical) | detected at the next check |

**Bugs found by the drills, fixed the same day:**
- D4: right after a restart Freqtrade's `/health` has no finished loop yet (`last_process_ts` = null), and
  the watchdog crashed on it. Now it's a warning while the bot starts, and critical if no loop follows
  within 10 minutes. The watchdog loop also catches any unexpected error, logs it and alerts, instead of
  dying. Regression test: `test_a_just_restarted_bot_is_not_a_crash`.
- The Windows start script stopped at "bot already running" and never started the watchdog. It now starts
  each part independently.

**Learned:**
- After any exit, Freqtrade locks the pair until the next candle (auto lock), so H5 re-enters at the next
  daily open at the earliest. That's correct for the rule. In a drill, unlock with `DELETE /api/v1/locks/{id}`.
- Environment proxy variables (`HTTPS_PROXY`) don't affect ccxt. Use `exchange.ccxt_config.httpsProxy` in a
  drill-only config to simulate an unreachable exchange.
- On Windows nothing restarts a crashed bot. After a "bot API unreachable" alert, run
  `ops\windows\start-dryrun.ps1`. On the Linux host, Docker's `restart: unless-stopped` does it.

**Still to do (they need your accounts):**
- [ ] Telegram: `/stopentry`, `/forceexit all`, `/stop` from your phone. Needs your bot token in
  `config.private.json`.
- [ ] Heartbeat alert: miss a Healthchecks.io ping and confirm the email arrives. Needs your Healthchecks
  URL in `config.private.json` → `watchdog.healthchecks_url`.
- [ ] API-key revocation procedure on a **test** key on the exchange website (PROJECT_PLAN.md §6.5 layer 4).
  The learning path uses no keys, so this is practice only.
- [ ] Repeat D1–D5 on the 24/7 host (Azure or Oracle) once it's set up.

# Runbook

Skeleton: fill in during Phase 3 (PROJECT_PLAN.md §9.4). Every section must be tested before going live.

## Start / stop / restart
- Start: `docker compose -f ops/docker-compose.yml up -d`
- Stop: `docker compose -f ops/docker-compose.yml down`
- Logs: `docker compose -f ops/docker-compose.yml logs -f --tail 100`

## Switch dry-run ↔ live (checklist)
- [ ] TODO (Phase 4)

## Upgrade Freqtrade
1. Bump the version in `requirements.txt` **and** `ops/docker-compose.yml` (the test enforces the match).
2. Run it in dry-run for one week.
3. Only then upgrade live. Rollback: revert both files and `up -d` again.

## Emergency (in order)
1. Telegram: `/stopentry`, then `/forceexit all`, then `/stop`
2. Watchdog manual trigger: TODO (Phase 3)
3. Exchange website: **delete the API key**, then close positions by hand
4. Write a post-mortem in `research/reports/` before restarting

## Restore the database from backup
- TODO (Phase 3)

## Links
- Exchange status page: TODO
- ESMA MiCA register: https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/markets-crypto-assets-regulation-mica
- Tax notes: TODO

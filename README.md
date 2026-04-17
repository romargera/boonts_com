# Boonts.com - Personal Business Card

A modern, blazing-fast personal website that serves as a digital business card and link hub. Designed with a mobile-first, intentional minimalism aesthetic.

## Tech Stack
- Vanilla HTML/CSS/JS
- Vite (Build Tool)

## Local Development
```bash
npm install
npm run dev
```

## Deployment
Deployed automatically to Coolify.

## CI/CD
This repository uses a 2-step GitHub Actions pipeline:

1. `Sync Dist`
- Trigger: push to `main` when source files change (`src`, `public`, `package*.json`, `vite.config.js`)
- Action: runs `npm ci && npm run build`, then commits updated `dist/` back to `main`

2. `Deploy To Coolify`
- Trigger: push to `main` when `dist/**` changes
- Action: calls Coolify deployment API and waits for final deployment status

## Daily Analytics Backup (Reserve)
There is an additional workflow:

3. `Analytics Backup Daily`
- Trigger: scheduled daily (`01:17 UTC`) and manual `workflow_dispatch`
- Action: reads one day of aggregated data from Umami and stores it in branch `analytics-data`

Backup files:
- `analytics/daily/boonts-main/YYYY-MM-DD.json`
- `analytics/daily/boonts-main/latest.json`

This gives a cheap daily reserve in git in case Umami is unavailable.

## Query Daily Backups
Use the helper script to read day-level metrics:

```bash
python3 scripts/analytics_daily_query.py --site-key boonts-main
```

Examples:

```bash
# Last 30 days
python3 scripts/analytics_daily_query.py --site-key boonts-main --limit 30

# Date range
python3 scripts/analytics_daily_query.py --site-key boonts-main --from-date 2026-04-01 --to-date 2026-04-30

# JSON output
python3 scripts/analytics_daily_query.py --site-key boonts-main --json
```

By default it reads from `origin/analytics-data`.

## Security And Secrets
Set these in `Settings -> Secrets and variables -> Actions`.

### CI/CD secrets
- `COOLIFY_API_URL` (example: `http://46.62.132.251:8000`)
- `MAC_ROMAN_DEPLOY` (Coolify API token)
- `COOLIFY_APP_UUID` (application UUID in Coolify)

### Analytics backup secrets
- `UMAMI_BASE_URL` (example: `https://analytics.boonts.com`)
- `UMAMI_USERNAME`
- `UMAMI_PASSWORD`

Security notes:
- Credentials are used only at runtime in Actions and are never committed to git.
- `.env*` files are ignored by default in `.gitignore`.
- Backup snapshots contain aggregated counters only.

Also enable `Settings -> Actions -> General -> Workflow permissions -> Read and write permissions` so workflows can push generated updates.

## Reuse In New Repositories
Workflows are split into reusable units, so other repos can use the same setup:

- `.github/workflows/reusable-sync-dist.yml`
- `.github/workflows/reusable-deploy-coolify.yml`
- `.github/workflows/reusable-analytics-backup.yml`

Example from another repo:

```yaml
name: Site Analytics Backup
on:
  schedule:
    - cron: "20 1 * * *"

jobs:
  backup:
    uses: romargera/boonts_com/.github/workflows/reusable-analytics-backup.yml@main
    with:
      website_id: "YOUR_UMAMI_WEBSITE_ID"
      site_key: "my-site"
      timezone: "Europe/Belgrade"
      backup_branch: "analytics-data"
      fail_on_missing_secrets: true
    secrets:
      UMAMI_BASE_URL: ${{ secrets.UMAMI_BASE_URL }}
      UMAMI_USERNAME: ${{ secrets.UMAMI_USERNAME }}
      UMAMI_PASSWORD: ${{ secrets.UMAMI_PASSWORD }}
```

For CI/CD reuse, call:
- `reusable-sync-dist.yml` for build + dist sync
- `reusable-deploy-coolify.yml` for Coolify deploy + status polling

## Daily Flow
1. Push code changes to `main`
2. GitHub Actions rebuilds and syncs `dist`
3. GitHub Actions triggers Coolify deployment automatically
4. Daily analytics snapshot is saved to `analytics-data` branch

## License
MIT

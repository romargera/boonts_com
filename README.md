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

## CI/CD (GitHub Actions + Coolify API)
This repository uses a simple 2-step pipeline:

1. `Sync Dist` workflow
- Trigger: push to `main` when source files change (`src`, `public`, `package*.json`, `vite.config.js`)
- Action: runs `npm ci && npm run build`, then commits updated `dist/` back to `main`

2. `Deploy To Coolify` workflow
- Trigger: push to `main` when `dist/**` changes
- Action: calls Coolify deployment API and waits for final deployment status

### Required GitHub Repository Secrets
Set these in `Settings -> Secrets and variables -> Actions`:

- `COOLIFY_API_URL` (example: `http://46.62.132.251:8000`)
- `MAC_ROMAN_DEPLOY` (Coolify API token)
- `COOLIFY_APP_UUID` (application UUID in Coolify)

Also enable `Settings -> Actions -> General -> Workflow permissions -> Read and write permissions` so `Sync Dist` can push `dist/` updates.

### Daily flow
1. Push code changes to `main`
2. GitHub Actions rebuilds and syncs `dist`
3. GitHub Actions triggers Coolify deployment automatically

## License
MIT

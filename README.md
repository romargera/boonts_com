# Boonts.com

[Live Website](https://boonts.com)

A high-performance personal business card and link hub built with intentional minimalism and a mobile-first philosophy.

## Technical Architecture

*   **Core**: Vanilla HTML5, CSS3, and ES6+ JavaScript.
*   **Build System**: [Vite](https://vitejs.dev/) for optimized asset bundling and fast HMR.
*   **Hosting**: [GitHub Pages](https://pages.github.com/) with a custom domain (`boonts.com`).
*   **Analytics**: Cloudflare Worker endpoint compatible with the existing Umami-style event names.

## Getting Started

### Prerequisites

*   Node.js (v18+)
*   npm
*   Python 3.9+ (standard library only, for SEO generation and validation)

### Local Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Infrastructure & DevOps

### CI/CD Pipeline
The project is deployed by GitHub Actions:
1.  **Build**: Runs `npm run build` to generate SEO files, build with Vite, and validate the output; then runs `npm run test:seo` before uploading the artifact.
2.  **Deploy**: Publishes `dist/` to GitHub Pages using `actions/deploy-pages`.

### Custom Domain (`boonts.com`)
GitHub Pages reads the domain from `public/CNAME` during build.  
Required DNS records for apex domain setup:

```text
A     @    185.199.108.153
A     @    185.199.109.153
A     @    185.199.110.153
A     @    185.199.111.153
AAAA  @    2606:50c0:8000::153
AAAA  @    2606:50c0:8001::153
AAAA  @    2606:50c0:8002::153
AAAA  @    2606:50c0:8003::153
CNAME www  romargera.github.io
```

Cloudflare is the authoritative DNS provider. Production responses on September 5, 2026 also show Cloudflare edge processing, including email obfuscation. GitHub Pages remains the deployment origin; do not assume DNS-only serving from the records above.

Security disclosure metadata is published at:

```text
https://boonts.com/.well-known/security.txt
```

### Analytics
All source pages use `https://analytics.boonts.com/script.js`, served by
`cloudflare/analytics-worker`. The older `umami.boonts.com` service is separate;
historical data there is not automatically migrated.

The collector exposes `window.umami.track(...)` and handles every declared
`data-umami-event`. `click-gcal-hiring` and `click-gcal-consulting` measure distinct
contact intents with equal business priority. Neither is a booked or held meeting.

New events use one unique KV receipt per request (`event2:`), expiring after 180 days.
This avoids the lost updates possible with the former read/modify/write counters.
Receipts contain date, approved event/path, a coarse source channel and landing path.
No IP, user ID, URL query or raw referrer is persisted. Session storage carries only
channel, landing path and a 30-minute inactivity timestamp; it is not a user identifier.
Search attribution is referrer-based and can miss stripped referrers, cross-device
journeys and AI Overview traffic inside Google. It is not GA4 session attribution.

```bash
npm run deploy:analytics                 # loads .env without shell evaluation
npm run analytics:events -- --days 30    # reads old counters and new receipts
```

Old `event:` counts are approximate under concurrency and have no source dimension.
New receipts count accepted requests, including test/bot traffic and possible retries;
they are not unique people. KV listing is eventually consistent: allow time before
checking delivery. Keep reports private; qualification of real conversations is manual.

## SheSafe Landing Page

The SheSafe landing page is hosted at `https://boonts.com/shesafe/`.

### Language Localization

Each supported language is a fully static, independently built and crawlable page at its own URL, rather than a client-side translation applied on top of a single URL. Every page carries a self-referencing canonical and a full `hreflang` block (including `x-default`) pointing at the others, and all four are listed with reciprocal alternates in `sitemap.xml`.

#### Locale URLs:
*   **English** (canonical/default): [https://boonts.com/shesafe/](https://boonts.com/shesafe/)
*   **Russian**: [https://boonts.com/shesafe/ru/](https://boonts.com/shesafe/ru/)
*   **Spanish**: [https://boonts.com/shesafe/es/](https://boonts.com/shesafe/es/)
*   **Portuguese**: [https://boonts.com/shesafe/pt/](https://boonts.com/shesafe/pt/)

A language switcher on each page links to the other three locales.

## SEO content workflow

The current strategy and remaining tasks are in [SEO_STRATEGY_PLAN.md](SEO_STRATEGY_PLAN.md).
Register canonical pages in `seo/pages.json`; Vite derives its HTML inputs from this registry.
Edit content and metadata in source HTML, including both the visible FAQ and its JSON-LD.
Run `npm run seo:generate` to regenerate `public/sitemap.xml`, `public/llms.txt`, and
`public/llms-full.txt`. Do not edit these generated files manually. Article `lastmod`
comes from its editorial `dateModified`; deployment time is never used as freshness.

`npm run build` validates all 12 current canonical pages and the generated production
files. `npm run test:seo` runs mutation-based regression tests. `npm run seo:live`
records a limited production HTTP/HTML snapshot in `seo/live-baseline.json`; it does
not measure indexing, rankings, authentic crawler access or Core Web Vitals.

## Private search measurements

Credentials belong in `.env` and `.secrets/`, both ignored by Git and Docker builds.
`GOOGLE_APPLICATION_CREDENTIALS` points to a local service-account JSON file;
GSC uses `sc-domain:boonts.com`. Yandex needs an OAuth access token, not just a
client ID/secret. The refresh token is stored locally; the current reader does not
refresh automatically. Never copy secrets into `VITE_` variables or public files.

```bash
python3 -m venv .venv-seo
.venv-seo/bin/pip install -r requirements-seo-lock.txt
npm run seo:baseline                    # 90 final days ending 3 days ago
npm run seo:geo                         # bounded Gemini API pilot; resumes successful rows
.venv-seo/bin/python scripts/search_baseline.py --submit-sitemap
```

Baseline exports and API errors go to ignored `seo/private/` with restricted file
permissions. GSC totals are queried independently of query rows; anonymization
means query rows need not sum to totals. Yandex popular queries are a limited list.
The GEO command uses the existing Gemini key and Google Search grounding: it is
an API pilot, not a consumer ChatGPT/Perplexity benchmark. Failed, truncated and
searchless answers require separate treatment. See `seo/OPERATIONS.md`.

## License

MIT © [Roman](https://github.com/romargera)

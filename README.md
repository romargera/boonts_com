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
1.  **Build**: Installs dependencies and builds the site with `vite build`.
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

Cloudflare is the authoritative DNS provider for `boonts.com`, but the public site is intentionally served directly by GitHub Pages DNS records. Keep these records DNS-only if the goal is simple static hosting. Enable Cloudflare proxying only when edge features such as WAF/Bot Fight Mode, Cloudflare-managed HSTS, or AI crawler blocking are required, and verify GitHub Pages HTTPS after the change.

Security disclosure metadata is published at:

```text
https://boonts.com/.well-known/security.txt
```

### Analytics
The public site keeps the same event names that were previously used by Umami:

```text
pageview
click-linkedin
click-telegram
click-whatsapp
click-email
scroll-25
scroll-50
scroll-75
scroll-100
```

`analytics.boonts.com/script.js` is served by the Cloudflare Worker in `cloudflare/analytics-worker`. The Worker exposes a small Umami-compatible `window.umami.track(...)` API and writes only daily aggregate counters to Workers KV. It does not persist IP addresses or user agents.

```bash
# Deploy the analytics Worker
npm run deploy:analytics

# Query Cloudflare event counts
npm run analytics:events -- --days 30
```

The old Umami backup reader is still available for historical snapshots in the `analytics-data` branch:

```bash
python3 scripts/analytics_daily_query.py --site-key boonts-main --limit 30
```

## License

MIT © [Roman](https://github.com/romargera)

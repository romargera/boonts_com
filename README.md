# Boonts.com

[Live Website](https://boonts.com)

A high-performance personal business card and link hub built with intentional minimalism and a mobile-first philosophy.

## Technical Architecture

*   **Core**: Vanilla HTML5, CSS3, and ES6+ JavaScript.
*   **Build System**: [Vite](https://vitejs.dev/) for optimized asset bundling and fast HMR.
*   **Hosting**: [GitHub Pages](https://pages.github.com/) with a custom domain (`boonts.com`).
*   **Analytics**: Integrated with [Umami](https://umami.is/) for privacy-focused usage metrics.

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

### Analytics Data Integrity
A scheduled daily task (`scripts/analytics_daily_query.py`) fetches aggregated metrics from Umami and persists them to the `analytics-data` branch. This ensures a redundant, version-controlled backup of site performance data.

```bash
# Query local analytics data
python3 scripts/analytics_daily_query.py --site-key boonts-main --limit 30
```

## License

MIT © [Roman](https://github.com/romargera)

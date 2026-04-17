# Boonts.com

[Live Website](https://boonts.com)

A high-performance personal business card and link hub built with intentional minimalism and a mobile-first philosophy.

## Technical Architecture

*   **Core**: Vanilla HTML5, CSS3, and ES6+ JavaScript.
*   **Build System**: [Vite](https://vitejs.dev/) for optimized asset bundling and fast HMR.
*   **Hosting**: Self-hosted via [Coolify](https://coolify.io/).
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
The project utilizes a dual-stage GitHub Actions workflow:
1.  **Sync**: Compiles source code and commits the production-ready `dist/` directory back to the repository on every push to `main`.
2.  **Deploy**: Triggers a webhook deployment to the Coolify instance upon production build updates.

### Analytics Data Integrity
A scheduled daily task (`scripts/analytics_daily_query.py`) fetches aggregated metrics from Umami and persists them to the `analytics-data` branch. This ensures a redundant, version-controlled backup of site performance data.

```bash
# Query local analytics data
python3 scripts/analytics_daily_query.py --site-key boonts-main --limit 30
```

## License

MIT © [Roman](https://github.com/romargera)

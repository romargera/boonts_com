import pageRegistry from "../../../seo/pages.json" with { type: "json" };
const SITE_KEY = "boonts-main";
export const KNOWN_EVENTS = new Set([
  "article-back-home",
  "article-switch-en",
  "article-switch-ru",
  "click-email",
  "click-gcal",
  "click-gcal-consulting",
  "click-gcal-hiring",
  "click-gplay-disabled",
  "click-linkedin",
  "click-telegram",
  "click-whatsapp",
  "discovery-open-en",
  "discovery-open-ru",
  "download-ios",
  "footer-article-practicum-hiring",
  "footer-article-roman-experts-en",
  "footer-article-roman-experts-ru",
  "footer-article-tg-communication",
  "footer-article-vc-interviews",
  "footer-article-vc-roadmap",
  "footer-legal-privacy",
  "footer-legal-terms",
  "footer-nav-home",
  "footer-nav-insights",
  "footer-nav-shesafe",
  "footer-social-email",
  "footer-social-linkedin",
  "footer-social-telegram",
  "footer-social-whatsapp",
  "hub-back-home",
  "hub-click-practicum-hiring",
  "hub-click-tg-communication",
  "hub-click-vc-interviews",
  "hub-click-vc-roadmap",
  "hub-footer-article-en",
  "hub-footer-article-ru",
  "hub-footer-nav-home",
  "hub-footer-nav-insights",
  "hub-footer-nav-shesafe",
  "hub-footer-practicum-hiring",
  "hub-footer-social-email",
  "hub-footer-social-linkedin",
  "hub-footer-social-telegram",
  "hub-footer-social-whatsapp",
  "hub-footer-vc-interviews",
  "hub-footer-vc-roadmap",
  "hub-open-en",
  "hub-open-ru",
  "lang-switch-en",
  "lang-switch-es",
  "lang-switch-pt",
  "lang-switch-ru",
  "pageview",
  "scroll-100",
  "scroll-25",
  "scroll-50",
  "scroll-75"
]);

const KNOWN_PATHS = new Set(pageRegistry.map(page => page.path));
const CHANNELS = new Set(["direct", "google", "yandex", "bing", "ai", "referral"]);

export function classifyReferrer(value) {
  const host = parseUrl(value)?.hostname || "";
  if (!host || host === "boonts.com" || host === "www.boonts.com") return "direct";
  if (/^(www\.)?google\.(com|[a-z]{2}|co\.[a-z]{2}|com\.[a-z]{2})$/.test(host)) return "google";
  if (/^(www\.)?(yandex\.(ru|com|by|kz|uz|com\.tr)|ya\.ru)$/.test(host)) return "yandex";
  if (host === "bing.com" || host.endsWith(".bing.com")) return "bing";
  if (["chatgpt.com", "chat.openai.com", "perplexity.ai", "claude.ai", "gemini.google.com", "copilot.microsoft.com"].some(h => host === h || host.endsWith("." + h))) return "ai";
  return "referral";
}

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "86400",
};

export function buildClientScript() {
  return `(() => {
  if (window.__boontsAnalyticsLoaded) return;
  window.__boontsAnalyticsLoaded = true;

  const script = document.currentScript;
  const endpoint = new URL("/api/send", script && script.src ? script.src : location.href).toString();
  const website = (script && (script.dataset.websiteId || script.dataset.siteKey)) || "${SITE_KEY}";

  const classify = ${classifyReferrer.toString()};
  const parseUrl = ${parseUrl.toString()};
  const now = Date.now();
  let attribution = { channel: classify(document.referrer), landing: location.pathname, touched: now };
  try {
    const previous = JSON.parse(sessionStorage.getItem("boonts-attribution") || "null");
    const ref = parseUrl(document.referrer);
    const internal = ref && ref.hostname === location.hostname;
    if (previous && now - previous.touched < 1800000 && (!ref || internal)) {
      attribution = { ...previous, touched: now };
    }
    sessionStorage.setItem("boonts-attribution", JSON.stringify(attribution));
  } catch {}
  function send(name, data) {
    if (!name || typeof name !== "string") return Promise.resolve();
    const payload = JSON.stringify({
      website,
      name,
      url: location.origin + location.pathname,
      channel: attribution.channel,
      landing: attribution.landing,
      referrer: parseUrl(document.referrer)?.origin || "",
      title: document.title,
      data: data && typeof data === "object" ? data : undefined,
    });

    // Beacon uses credentials=include, incompatible with wildcard CORS.
    // keepalive fetch survives navigation and explicitly omits credentials.
    return fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true,
      credentials: "omit",
    }).catch(() => {});
  }

  window.umami = window.umami || {};
  window.umami.track = send;

  document.addEventListener("click", (event) => {
    const target = event.target && event.target.closest
      ? event.target.closest("[data-umami-event]")
      : null;
    if (!target) return;
    send(target.getAttribute("data-umami-event"));
  }, true);

  const trackPageview = () => send("pageview");
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", trackPageview, { once: true });
  } else {
    trackPageview();
  }
})();`;
}

export function normalizeEvent(payload, request) {
  const pageUrl = parseUrl(payload?.url);
  const referrerUrl = parseUrl(payload?.referrer);
  const country =
    request.headers.get("CF-IPCountry") ||
    request.headers.get("cf-connecting-country") ||
    request.cf?.country ||
    "unknown";

  return {
    name: typeof payload?.name === "string" ? payload.name.slice(0, 80) : "",
    path: pageUrl ? pageUrl.pathname : "/",
    hostname: pageUrl ? pageUrl.hostname : "unknown",
    referrerHost: referrerUrl ? referrerUrl.hostname : "",
    country,
    channel: CHANNELS.has(payload?.channel) ? payload.channel : classifyReferrer(payload?.referrer),
    landing: KNOWN_PATHS.has(payload?.landing) ? payload.landing : (pageUrl?.pathname || "/"),
  };
}

export function buildEventKey({ date, name, path }) {
  return `event:${date}:${name}:${encodeURIComponent(path || "/")}`;
}

function parseUrl(value) {
  if (!value || typeof value !== "string") return null;
  try {
    return new URL(value);
  } catch {
    return null;
  }
}

async function parsePayload(request) {
  const body = await request.text();
  if (!body) return {};
  return JSON.parse(body);
}

// One key per received event avoids read/modify/write losses in eventually-consistent KV.
// UUID identifies a receipt, never a user. No IP, query strings or user identifiers are stored.
async function writeEvent(env, event) {
  if (!env?.BOONTS_EVENTS) throw new Error("Storage unavailable");
  const date = new Date().toISOString().slice(0, 10);
  const key = `event2:${date}:${event.name}:${encodeURIComponent(event.path)}:${event.channel}:${crypto.randomUUID()}`;
  await env.BOONTS_EVENTS.put(key, JSON.stringify({ landing: event.landing }), { expirationTtl: 15552000 });
}

function textResponse(body, init = {}) {
  const status = init.status || 200;

  return new Response(status === 204 ? null : body, {
    ...init,
    status,
    headers: {
      ...CORS_HEADERS,
      ...(init.headers || {}),
    },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return textResponse("", { status: 204 });
    }

    if ((request.method === "GET" || request.method === "HEAD") && url.pathname === "/script.js") {
      return textResponse(request.method === "HEAD" ? null : buildClientScript(), {
        headers: {
          "Content-Type": "application/javascript; charset=utf-8",
          "Cache-Control": "public, max-age=300",
        },
      });
    }

    if ((request.method === "GET" || request.method === "HEAD") && url.pathname === "/health") {
      return textResponse(request.method === "HEAD" ? null : "ok\n", {
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      });
    }

    if (request.method === "POST" && url.pathname === "/api/send") {
      try {
        const payload = await parsePayload(request);
        const event = normalizeEvent(payload, request);
        if (!KNOWN_EVENTS.has(event.name) || event.hostname !== "boonts.com" || !KNOWN_PATHS.has(event.path)) {
          return textResponse("unsupported event\n", { status: 422 });
        }
        try { await writeEvent(env, event); }
        catch { return textResponse("storage unavailable\n", { status: 503 }); }
        return textResponse("", { status: 204 });
      } catch {
        return textResponse("invalid json\n", { status: 400 });
      }
    }

    return textResponse("boonts analytics worker\n", {
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  },
};

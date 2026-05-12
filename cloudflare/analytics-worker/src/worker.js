const SITE_KEY = "boonts-main";
const KNOWN_EVENTS = new Set([
  "pageview",
  "click-linkedin",
  "click-telegram",
  "click-whatsapp",
  "click-email",
  "scroll-25",
  "scroll-50",
  "scroll-75",
  "scroll-100",
]);

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

  function send(name, data) {
    if (!name || typeof name !== "string") return Promise.resolve();
    const payload = JSON.stringify({
      website,
      name,
      url: location.href,
      referrer: document.referrer,
      title: document.title,
      data: data && typeof data === "object" ? data : undefined,
    });

    if (navigator.sendBeacon) {
      const queued = navigator.sendBeacon(endpoint, new Blob([payload], { type: "application/json" }));
      if (queued) return Promise.resolve();
    }

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

async function writeEvent(env, event) {
  if (!env?.BOONTS_EVENTS || !KNOWN_EVENTS.has(event.name)) return;

  const date = new Date().toISOString().slice(0, 10);
  const key = buildEventKey({ date, name: event.name, path: event.path });
  const current = Number.parseInt((await env.BOONTS_EVENTS.get(key)) || "0", 10);
  const next = Number.isFinite(current) ? current + 1 : 1;
  await env.BOONTS_EVENTS.put(key, String(next));
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
        await writeEvent(env, event);
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

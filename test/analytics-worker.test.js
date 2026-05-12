import assert from "node:assert/strict";
import test from "node:test";

import worker, {
  buildClientScript,
  buildEventKey,
  normalizeEvent,
} from "../cloudflare/analytics-worker/src/worker.js";

function request(path, init = {}) {
  return new Request(`https://analytics.boonts.com${path}`, init);
}

test("client script preserves the existing Umami-compatible API surface", () => {
  const script = buildClientScript();

  assert.match(script, /window\.umami/);
  assert.match(script, /data-umami-event/);
  assert.match(script, /sendBeacon/);
  assert.match(script, /api\/send/);
});

test("normalizes Umami-style event payloads without personal identifiers", () => {
  const event = normalizeEvent(
    {
      name: "click-linkedin",
      url: "https://boonts.com/?utm_source=x",
      referrer: "https://example.com/path?q=1",
      title: "Roman Babunts",
    },
    request("/api/send", {
      headers: {
        "CF-Connecting-IP": "203.0.113.10",
        "CF-IPCountry": "RS",
        "User-Agent": "Browser/1.0",
      },
    }),
  );

  assert.equal(event.name, "click-linkedin");
  assert.equal(event.path, "/");
  assert.equal(event.hostname, "boonts.com");
  assert.equal(event.referrerHost, "example.com");
  assert.equal(event.country, "RS");
  assert.equal(event.ip, undefined);
  assert.equal(event.userAgent, undefined);
});

test("builds stable daily KV keys for configured events", () => {
  assert.equal(
    buildEventKey({ date: "2026-05-12", name: "click-linkedin", path: "/" }),
    "event:2026-05-12:click-linkedin:%2F",
  );
});

test("POST /api/send increments one KV event counter", async () => {
  const store = new Map();
  const env = {
    BOONTS_EVENTS: {
      async get(key) {
        return store.get(key) ?? null;
      },
      async put(key, value) {
        store.set(key, value);
      },
    },
  };

  const response = await worker.fetch(
    request("/api/send", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Origin: "https://boonts.com",
        "CF-IPCountry": "RS",
      },
      body: JSON.stringify({
        name: "scroll-50",
        url: "https://boonts.com/",
      }),
    }),
    env,
  );

  assert.equal(response.status, 204);
  assert.equal(store.size, 1);
  assert.equal([...store.values()][0], "1");
  assert.match([...store.keys()][0], /^event:\d{4}-\d{2}-\d{2}:scroll-50:%2F$/);
});

test("GET /script.js returns JavaScript with cache and CORS headers", async () => {
  const response = await worker.fetch(request("/script.js"), {});

  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type"), /application\/javascript/);
  assert.match(response.headers.get("cache-control"), /max-age/);
  assert.equal(response.headers.get("access-control-allow-origin"), "*");
});

test("HEAD /script.js returns JavaScript headers without a body", async () => {
  const response = await worker.fetch(request("/script.js", { method: "HEAD" }), {});

  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type"), /application\/javascript/);
  assert.equal(await response.text(), "");
});

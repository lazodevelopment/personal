/**
 * lazo-healthcheck — cron-driven API monitor with SES alerts + /status JSON for God Mode.
 * Account: Lazo/LeaseReputation Cloudflare (d16dd804...), NOT the wedding-brands account.
 *
 * Alert logic: a check must fail FAILS_BEFORE_ALERT consecutive runs to be declared DOWN
 * (one alert on the transition), recovery sends an UP alert, and while DOWN a reminder
 * goes out every REALERT_HOURS. No emails on healthy runs.
 */


const FAILS_BEFORE_ALERT = 2;
const REALERT_HOURS = 6;
const DEFAULT_TIMEOUT_MS = 10000;

/**
 * CHECKS — fill in the real endpoints.
 *   name            display name (also the KV key — keep stable once live)
 *   url             endpoint to hit
 *   method          default GET
 *   headers/body    optional, for POST checks
 *   expectStatus    array of acceptable HTTP statuses (default [200])
 *   contains        optional substring that must appear in the response body
 *   timeoutMs       per-check timeout (default 10s)
 *   intervalMinutes run cadence; only fires when minute % intervalMinutes === 0.
 *                   Keep expensive checks (June/Haiku) at 30 to limit token spend.
 */
const CHECKS = [
  {
    name: "site",
    label: "meetlazo.com",
    url: "https://meetlazo.com/",
    expectStatus: [200],
    contains: "site-nav",
    intervalMinutes: 5,
  },
  {
    name: "admin",
    label: "God Mode (admin.meetlazo.com)",
    url: "https://admin.meetlazo.com/",
    expectStatus: [200],
    intervalMinutes: 5,
  },
  {
    name: "june-api",
    label: "June API (function + Firestore)",
    url: "https://us-central1-lazo-513ec.cloudfunctions.net/juneGuest",
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ slug: "healthcheck-probe-no-such-site", question: "ping" }),
    expectStatus: [404],
    contains: "not_found",
    timeoutMs: 15000,
    intervalMinutes: 5,
  },
  {
    name: "june-ai",
    label: "June AI (full answer)",
    url: "https://us-central1-lazo-513ec.cloudfunctions.net/juneGuest",
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ slug: "mindy-m-", question: "What time is the ceremony?" }),
    expectStatus: [200],
    contains: "answer",
    timeoutMs: 25000,
    intervalMinutes: 30,
  },
  // --- FILL IN: June API (juneGuest). Use a cheap ping payload if the function
  // supports one; otherwise the smallest real request that proves Haiku answered.
  // {
  //   name: "june",
  //   label: "June API (juneGuest)",
  //   url: "https://<region>-<project>.cloudfunctions.net/juneGuest",
  //   method: "POST",
  //   headers: { "content-type": "application/json" },
  //   body: JSON.stringify({ /* minimal valid payload */ }),
  //   expectStatus: [200],
  //   contains: null,
  //   timeoutMs: 20000,
  //   intervalMinutes: 30,
  // },
  // --- FILL IN: any other HTTP-callable functions (widget APIs, billing endpoints).
  // Firestore-triggered functions (outreachOnInquiry, claimApprovedEmail) have no URL
  // to ping — monitoring those needs a canary write, which can be added later.
];

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(runChecks(env, new Date(event.scheduledTime)));
  },

  // GET /status → JSON of current health (for the God Mode card).
  // Requires header  Authorization: Bearer <STATUS_KEY>  when STATUS_KEY is set.
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/run") {
      const now = new Date();
      const all = url.searchParams.get("all") === "1";
      const due = all ? CHECKS
        : CHECKS.filter((c) => now.getUTCMinutes() % (c.intervalMinutes || 5) === 0);
      await Promise.allSettled(due.map((c) => runOne(env, c, now)));
      return Response.json({ ran: due.length, of: CHECKS.length, at: now.toISOString() });
    }
    if (url.pathname !== "/status") return new Response("Not found", { status: 404 });
    if (env.STATUS_KEY) {
      const auth = request.headers.get("authorization") || "";
      if (auth !== `Bearer ${env.STATUS_KEY}`) {
        return new Response("Unauthorized", { status: 401 });
      }
    }
    const states = await Promise.all(
      CHECKS.map(async (c) => ({
        name: c.name,
        label: c.label || c.name,
        ...(await getState(env, c.name)),
      }))
    );
    const allUp = states.every((s) => s.status !== "down");
    return Response.json(
      { overall: allUp ? "up" : "down", checkedAt: new Date().toISOString(), checks: states },
      { headers: { "access-control-allow-origin": "*", "cache-control": "no-store" } }
    );
  },
};

async function runChecks(env, now) {
  const minute = now.getUTCMinutes();
  const due = CHECKS.filter((c) => minute % (c.intervalMinutes || 5) === 0);
  await Promise.allSettled(due.map((c) => runOne(env, c, now)));
}

async function runOne(env, check, now) {
  const result = await probe(check);
  const state = await getState(env, check.name);

  if (result.ok) {
    if (state.status === "down") {
      await sendAlert(env, upEmail(check, state, now));
    }
    await putState(env, check.name, {
      status: "up",
      fails: 0,
      since: state.status === "up" ? state.since : now.toISOString(),
      lastAlertAt: null,
      lastError: null,
      lastCheckedAt: now.toISOString(),
    });
    return;
  }

  const fails = (state.fails || 0) + 1;
  const wasDown = state.status === "down";
  const nowDown = wasDown || fails >= FAILS_BEFORE_ALERT;
  const next = {
    status: nowDown ? "down" : "up",
    fails,
    since: wasDown ? state.since : nowDown ? now.toISOString() : state.since,
    lastAlertAt: state.lastAlertAt || null,
    lastError: result.error,
    lastCheckedAt: now.toISOString(),
  };

  const shouldAlert =
    (nowDown && !wasDown) || // transition to down
    (wasDown && hoursSince(state.lastAlertAt, now) >= REALERT_HOURS); // still-down reminder

  if (shouldAlert) {
    await sendAlert(env, downEmail(check, next, now, !wasDown));
    next.lastAlertAt = now.toISOString();
  }
  await putState(env, check.name, next);
}

async function probe(check) {
  try {
    const res = await fetch(check.url, {
      method: check.method || "GET",
      headers: check.headers,
      body: check.body,
      signal: AbortSignal.timeout(check.timeoutMs || DEFAULT_TIMEOUT_MS),
      // Never serve a cached "healthy" page from Cloudflare's own edge:
      cf: { cacheTtl: 0, cacheEverything: false },
    });
    const okStatus = (check.expectStatus || [200]).includes(res.status);
    if (!okStatus) return { ok: false, error: `HTTP ${res.status}` };
    if (check.contains) {
      const text = await res.text();
      if (!text.includes(check.contains)) {
        return { ok: false, error: `body missing "${check.contains}"` };
      }
    }
    return { ok: true };
  } catch (e) {
    const msg = e && e.name === "TimeoutError" ? "timeout" : String(e && e.message || e);
    return { ok: false, error: msg };
  }
}

// ---------- state (KV) ----------

async function getState(env, name) {
  const raw = await env.HEALTH.get(`check:${name}`);
  return raw ? JSON.parse(raw) : { status: "up", fails: 0, since: null, lastAlertAt: null };
}

function putState(env, name, state) {
  return env.HEALTH.put(`check:${name}`, JSON.stringify(state));
}

function hoursSince(iso, now) {
  if (!iso) return Infinity;
  return (now.getTime() - new Date(iso).getTime()) / 36e5;
}

// ---------- alerts (SES v2, signed from the worker) ----------

function downEmail(check, state, now, isTransition) {
  const label = check.label || check.name;
  return {
    subject: `[Lazo] DOWN: ${label}`,
    body: [
      `${label} is ${isTransition ? "DOWN" : "still down"}.`,
      ``,
      `Endpoint: ${check.url}`,
      `Error: ${state.lastError}`,
      `Consecutive failures: ${state.fails}`,
      `Down since: ${state.since || now.toISOString()}`,
      ``,
      `Status: https://<worker-route>/status`,
    ].join("\n"),
  };
}

function upEmail(check, state, now) {
  const label = check.label || check.name;
  const downFor = state.since ? Math.round(hoursSince(state.since, now) * 60) : "?";
  return {
    subject: `[Lazo] RECOVERED: ${label}`,
    body: `${label} is back up as of ${now.toISOString()} (was down ~${downFor} min).`,
  };
}

async function sendAlert(env, { subject, body }) {
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      authorization: `Bearer ${env.RESEND_API_KEY}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      from: env.ALERT_FROM,
      to: [env.ALERT_TO],
      subject,
      text: body,
    }),
  });
  if (!res.ok) {
    console.error("Resend send failed", res.status, await res.text());
  }
}

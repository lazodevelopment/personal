// Web Push for the hub: VAPID-signed, aes128gcm-encrypted pushes to Chrome/Firefox subscriptions (RFC 8291/8292).
// Lets the alarm and alerts reach the phone through Chrome on Android (or any browser that subscribed), with no
// third-party app. The VAPID key pair is made once and kept in KV `vapid`; subscriptions live in KV `push_subs`.

const b64u = {
  enc: (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""),
  dec: (s) => { s = String(s || "").replace(/-/g, "+").replace(/_/g, "/"); while (s.length % 4) s += "="; return Uint8Array.from(atob(s), (c) => c.charCodeAt(0)); },
};
const te = new TextEncoder();
const cat = (...parts) => { const n = parts.reduce((a, p) => a + p.length, 0); const out = new Uint8Array(n); let o = 0; for (const p of parts) { out.set(p, o); o += p.length; } return out; };

// the hub's own VAPID keys: made on first use, then reused forever (changing them would orphan every subscription)
export async function vapidKeys(env) {
  const kv = env.HUB;
  let k = await kv.get("vapid", "json");
  if (k?.priv && k?.pub) return k;
  const pair = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
  const priv = await crypto.subtle.exportKey("jwk", pair.privateKey);
  const raw = await crypto.subtle.exportKey("raw", pair.publicKey);
  k = { priv, pub: b64u.enc(raw), at: new Date().toISOString() };
  await kv.put("vapid", JSON.stringify(k));
  return k;
}

async function vapidHeader(env, audience) {
  const k = await vapidKeys(env);
  const key = await crypto.subtle.importKey("jwk", k.priv, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
  const now = Math.floor(Date.now() / 1000);
  const head = b64u.enc(te.encode(JSON.stringify({ typ: "JWT", alg: "ES256" })));
  const body = b64u.enc(te.encode(JSON.stringify({ aud: audience, exp: now + 12 * 3600, sub: "mailto:" + (env.ALERT_EMAIL || "jesse@briskhealth.com") })));
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, te.encode(head + "." + body));   // WebCrypto gives the raw r||s form JWT wants
  return { auth: `vapid t=${head}.${body}.${b64u.enc(sig)}, k=${k.pub}`, pub: k.pub };
}

async function hkdf(salt, ikm, info, len) {
  const key = await crypto.subtle.importKey("raw", ikm, "HKDF", false, ["deriveBits"]);
  return new Uint8Array(await crypto.subtle.deriveBits({ name: "HKDF", hash: "SHA-256", salt, info }, key, len * 8));
}

// RFC 8291 payload encryption (aes128gcm, single record)
async function encrypt(sub, plaintext) {
  const clientPub = b64u.dec(sub.keys.p256dh), auth = b64u.dec(sub.keys.auth);
  const local = await crypto.subtle.generateKey({ name: "ECDH", namedCurve: "P-256" }, true, ["deriveBits"]);
  const localPub = new Uint8Array(await crypto.subtle.exportKey("raw", local.publicKey));
  const peer = await crypto.subtle.importKey("raw", clientPub, { name: "ECDH", namedCurve: "P-256" }, false, []);
  const shared = new Uint8Array(await crypto.subtle.deriveBits({ name: "ECDH", public: peer }, local.privateKey, 256));
  const ikm = await hkdf(auth, shared, cat(te.encode("WebPush: info\0"), clientPub, localPub), 32);
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const cek = await hkdf(salt, ikm, te.encode("Content-Encoding: aes128gcm\0"), 16);
  const nonce = await hkdf(salt, ikm, te.encode("Content-Encoding: nonce\0"), 12);
  const aes = await crypto.subtle.importKey("raw", cek, "AES-GCM", false, ["encrypt"]);
  const padded = cat(te.encode(plaintext), new Uint8Array([2]));   // last-record delimiter
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, aes, padded));
  const rs = new Uint8Array(4); new DataView(rs.buffer).setUint32(0, 4096);
  return cat(salt, rs, new Uint8Array([localPub.length]), localPub, ct);
}

export async function listSubs(env) { return (await env.HUB.get("push_subs", "json")) || []; }
export async function saveSub(env, sub, meta = {}) {
  if (!sub?.endpoint || !sub?.keys?.p256dh || !sub?.keys?.auth) throw new Error("bad subscription");
  const list = (await listSubs(env)).filter((s) => s.endpoint !== sub.endpoint);
  list.unshift({ endpoint: sub.endpoint, keys: sub.keys, ua: String(meta.ua || "").slice(0, 160), label: String(meta.label || "").slice(0, 60), at: new Date().toISOString() });
  await env.HUB.put("push_subs", JSON.stringify(list.slice(0, 10)));
  return list.length;
}
export async function dropSub(env, endpoint) {
  const list = (await listSubs(env)).filter((s) => s.endpoint !== endpoint);
  await env.HUB.put("push_subs", JSON.stringify(list));
  return list.length;
}

// send one payload to every subscription; dead endpoints (404/410) are dropped. Returns [{endpoint, status}]
export async function webPush(env, payload, { ttl = 3600, urgency = "high", topic = "" } = {}) {
  const subs = await listSubs(env);
  if (!subs.length) return [];
  const text = JSON.stringify(payload);
  const out = await Promise.all(subs.map(async (sub) => {
    try {
      const aud = new URL(sub.endpoint).origin;
      const { auth } = await vapidHeader(env, aud);
      const body = await encrypt(sub, text);
      const r = await fetch(sub.endpoint, { method: "POST", headers: { authorization: auth, "content-encoding": "aes128gcm", "content-type": "application/octet-stream", ttl: String(ttl), urgency, ...(topic ? { topic: topic.slice(0, 32) } : {}) }, body });
      const detail = r.ok ? undefined : (await r.text()).slice(0, 160);
      return { endpoint: sub.endpoint.slice(0, 60), ua: sub.ua, status: r.status, detail };
    } catch (e) { return { endpoint: sub.endpoint.slice(0, 60), ua: sub.ua, status: "error", detail: String(e.message || e).slice(0, 160) }; }
  }));
  const dead = out.filter((o) => o.status === 404 || o.status === 410).map((o) => o.endpoint);
  if (dead.length) await env.HUB.put("push_subs", JSON.stringify(subs.filter((s) => !dead.includes(s.endpoint.slice(0, 60)))));
  return out;
}

// the service worker the page registers: shows pushes as notifications, acknowledges the alarm on tap, opens the hub
export const SW_JS = `
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("push", (e) => {
  let d = {}; try { d = e.data ? e.data.json() : {}; } catch { d = { title: "JARVIS", body: e.data ? e.data.text() : "" }; }
  const alarm = d.kind === "alarm";
  const opts = {
    body: d.body || "", icon: "/icon-192.png", badge: "/icon-192.png", tag: d.tag || (alarm ? "alarm" : "jarvis-" + Date.now()), renotify: true,
    requireInteraction: alarm || d.priority === "urgent", silent: false,
    vibrate: alarm ? [800, 300, 800, 300, 800, 300, 800, 300, 800] : d.priority === "urgent" ? [300, 150, 300] : [120],
    timestamp: Date.now(), data: { url: d.url || "/", kind: d.kind || "", at: d.at || "" },
    actions: alarm ? [{ action: "wake", title: "I'm up" }, { action: "snooze", title: "5 more minutes" }] : [],
  };
  e.waitUntil(self.registration.showNotification(d.title || "JARVIS", opts));
});
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const d = e.notification.data || {}; const alarm = d.kind === "alarm";
  const go = async () => {
    if (alarm) { try { await fetch("/api/alarm/ack", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ action: e.action || "wake" }) }); } catch {} }
    if (e.action === "snooze") return;
    const url = new URL(d.url || "/", self.location.origin).href;
    const all = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of all) { if (c.url.startsWith(self.location.origin)) { try { await c.navigate(url); } catch {} return c.focus(); } }
    return self.clients.openWindow(url);
  };
  e.waitUntil(go());
});
self.addEventListener("notificationclose", (e) => { const d = e.notification.data || {}; if (d.kind === "alarm") e.waitUntil(fetch("/api/alarm/ack", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ action: "dismiss" }) }).catch(() => {})); });
self.addEventListener("fetch", () => {});   // nothing cached: the hub is always live
`;

// prints.js - JC-LAZO-PRINTS-0920-001
// The print store: a couple's delivery gallery (/g/{slug}) -> WHCC's hosted
// editor -> a cart on meetlazo.com -> Stripe Checkout -> the order confirmed
// at WHCC -> status and tracking back by webhook. Lazo is seller of record;
// WHCC bills Lazo's card on file when the order ships and drop-ships blind.
//
// Routes (all handled by printsRoute):
//   GET  /api/prints/products                  editor products, simpleEditor only, cached
//   POST /g/{slug}/store/editor                from the gallery page (passcode cookie)
//   POST /api/prints/editor                    from the app ({slug, ids, passcode?})
//   GET  /prints/return?editor=&slug=          the cart page after the editor
//   GET  /api/prints/cart?editor=&slug=        export -> items, pricing, previews
//   POST /api/prints/checkout                  quote at WHCC, then Stripe Checkout
//   GET  /prints/thanks?o=                     after payment
//   GET  /api/prints/order?o=                  one order's status
//   GET  /api/prints/orders?slug=&passcode=    orders for a gallery
//   POST /api/prints/webhook/stripe            checkout.session.completed -> confirm at WHCC
//   POST /api/prints/webhook/whcc              verifier handshake, received / shipped / image events
//   POST /api/prints/admin/register-webhook    one-time, needs PRINTS_ADMIN_KEY
//
// Secrets (wrangler secret put): WHCC_EDITOR_KEY, WHCC_EDITOR_SECRET, WHCC_OS_KEY,
//   WHCC_OS_SECRET, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, PRINTS_ADMIN_KEY, GALLERY_SECRET.
// Vars (wrangler.toml [vars]): WHCC_ENV sandbox|production, PRINT_MARKUP (percent),
//   PRINT_FROM_NAME/ADDR1/ADDR2/CITY/STATE/ZIP (the return address on the label).
//
// State lives in the SITE bucket under _prints/ (the worker never serves _ keys):
//   _prints/editors/{editorId}.json   who opened which editor on which gallery
//   _prints/orders/{oid}.json         the order, from cart to shipped
//   _prints/gallery/{slug}.json       [oid, ...]
//   _prints/byconf/{ConfirmationID}.json  -> oid, for webhooks
//   _prints/events/{key}.json         webhook dedupe (ConfirmationId+SequenceNumber+EventId)

const EDITOR_BASE = { sandbox: "https://prospector-stage.dragdrop.design/api/v1", production: "https://prospector.dragdrop.design/api/v1" };
const OS_BASE = { sandbox: "https://sandbox.apps.whcc.com", production: "https://apps.whcc.com" };
const SITE = "https://meetlazo.com";
const SHIP_METHODS = {
  553: { label: "Standard (2-8 days)", days: "2-8 days" },
  554: { label: "Expedited (3 days or less)", days: "3 days or less" },
  556: { label: "Priority one-day", days: "1 day" },
};
const ASSET_TTL_MS = 7 * 86400000;

const JSONH = { "content-type": "application/json", "cache-control": "no-store", "access-control-allow-origin": "*" };
const jres = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: JSONH });
const esc = (t) => String(t || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const b64url = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
const env1 = (env) => (env.WHCC_ENV === "production" ? "production" : "sandbox");
const money = (n) => "$" + (Math.round(Number(n) * 100) / 100).toFixed(2);

function safeEq(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

async function hmacB64(secret, msg) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return b64url(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(msg)));
}
async function hmacHex(secret, msg) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return hex(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(msg)));
}
async function sha256Hex(s) {
  return hex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)));
}

// ---------------------------------------------------------------- R2 state
async function rget(env, key) {
  const o = await env.SITE.get(key);
  if (!o) return null;
  try { return await o.json(); } catch { return null; }
}
async function rput(env, key, val) {
  await env.SITE.put(key, JSON.stringify(val), { httpMetadata: { contentType: "application/json" } });
}
const newId = (p) => p + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);

// ---------------------------------------------------------------- Firestore (read-only, world-readable docs)
async function fsDoc(collection, id) {
  const r = await fetch(`https://firestore.googleapis.com/v1/projects/lazo-513ec/databases/(default)/documents/${collection}/${encodeURIComponent(id)}`, { headers: { accept: "application/json" } });
  if (!r.ok) return null;
  const d = await r.json();
  return d.fields || null;
}
function fsVal(v) {
  if (v == null) return null;
  if ("stringValue" in v) return v.stringValue;
  if ("integerValue" in v) return Number(v.integerValue);
  if ("doubleValue" in v) return v.doubleValue;
  if ("booleanValue" in v) return v.booleanValue;
  if ("arrayValue" in v) return (v.arrayValue.values || []).map(fsVal);
  if ("mapValue" in v) { const o = {}; for (const [k, x] of Object.entries(v.mapValue.fields || {})) o[k] = fsVal(x); return o; }
  return null;
}

async function loadGallery(slug) {
  if (!/^[a-z0-9-]{1,80}$/.test(slug)) return null;
  const f = await fsDoc("galleries", slug);
  if (!f) return null;
  const g = (k) => fsVal(f[k]);
  if (g("status") !== "live") return null;
  const expiresAt = g("expiresAt") || "";
  if (expiresAt && Date.parse(expiresAt) < Date.now()) return null;
  return { slug, names: g("names") || "", vendorName: g("vendorName") || "", vendorId: g("vendorId") || "",
    storeOn: g("storeOn") !== false, passcodeHash: (g("passcodeHash") || "").toString() };
}
async function manifest(env, slug) {
  try {
    const o = await env.GALLERIES.get(`${slug}/manifest.json`);
    if (!o) return [];
    const m = await o.json();
    return Array.isArray(m) ? m : (m.photos || []);
  } catch { return []; }
}

// The gallery's passcode: the page sends its cookie (Path=/g/{slug}), the app sends the passcode.
async function galleryAuthed(req, gal, body, env) {
  if (!gal.passcodeHash) return true;
  const cookie = req.headers.get("cookie") || "";
  const m = cookie.match(new RegExp(`lazo_g_${gal.slug}=([^;]+)`));
  if (m) {
    const [exp, sig] = decodeURIComponent(m[1]).split(".");
    if (exp && sig && Number(exp) > Date.now() && safeEq(sig, await hmacB64(env.GALLERY_SECRET || "dev-only-not-a-secret", `pass:${gal.slug}:${exp}`))) return true;
  }
  const given = (body && body.passcode ? body.passcode : "").toString().trim().toLowerCase().slice(0, 40);
  if (given && safeEq(await sha256Hex(given), gal.passcodeHash)) return true;
  return false;
}

// A URL WHCC can fetch server-side: no cookie, expires, can't be walked. Same
// scheme as /p/ in index.js (asset:{slug}:{id}:{exp} under GALLERY_SECRET).
async function signedAsset(env, slug, id, exp) {
  const sig = await hmacB64(env.GALLERY_SECRET || "dev-only-not-a-secret", `asset:${slug}:${id}:${exp}`);
  return `${SITE}/p/${exp}/${sig}/${slug}/${id}.jpg`;
}

// ---------------------------------------------------------------- WHCC Editor API
const _tok = new Map(); // accountId -> {token, exp}
async function editorToken(env, accountId) {
  const hit = _tok.get(accountId);
  if (hit && hit.exp > Date.now() + 60000) return hit.token;
  const r = await fetch(`${EDITOR_BASE[env1(env)]}/auth/access-token`, {
    method: "POST", headers: { accept: "application/json", "content-type": "application/json" },
    body: JSON.stringify({ key: (env.WHCC_EDITOR_KEY || "").trim(), secret: (env.WHCC_EDITOR_SECRET || "").trim(), claims: { accountId } }),
  });
  if (!r.ok) throw new Error(`editor token ${r.status}: ${(await r.text()).slice(0, 200)}`);
  const j = await r.json();
  _tok.set(accountId, { token: j.accessToken, exp: (Number(j.expires) || 0) * 1000 });
  return j.accessToken;
}
async function editorCall(env, accountId, method, path, body) {
  const token = await editorToken(env, accountId);
  const r = await fetch(`${EDITOR_BASE[env1(env)]}${path}`, {
    method, headers: { authorization: `Bearer ${token}`, accept: "application/json", "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await r.text();
  let j = null; try { j = JSON.parse(text); } catch {}
  if (!r.ok) throw new Error(`editor ${method} ${path} ${r.status}: ${text.slice(0, 300)}`);
  return j;
}

async function products(env) {
  const key = new Request(`${SITE}/_prints/products/${env1(env)}`);
  const hit = await caches.default.match(key);
  if (hit) return hit.json();
  // The products call wants a bearer token too (the docs example omits it).
  const token = await editorToken(env, "lazo-catalog");
  const r = await fetch(`${EDITOR_BASE[env1(env)]}/products`, { headers: { accept: "application/json", authorization: `Bearer ${token}` } });
  if (!r.ok) throw new Error(`products ${r.status}`);
  const all = await r.json();
  const out = (Array.isArray(all) ? all : []).filter((p) => p.editorCompatibility === "simpleEditor").map((p) => ({
    id: p._id, name: p.name, category: (p.category && p.category.name) || "", compat: p.editorCompatibility,
  }));
  await caches.default.put(key, new Response(JSON.stringify(out), { headers: { "content-type": "application/json", "cache-control": "public, max-age=21600" } }));
  return out;
}

function pickProduct(list, wanted) {
  if (wanted) { const p = list.find((x) => x.id === wanted); if (p) return p; }
  return list.find((x) => /photographic print|photo print/i.test(x.name)) || list.find((x) => /print/i.test(x.name)) || list[0];
}

// ---------------------------------------------------------------- WHCC Order Submit API (webhook registration only)
async function osToken(env) {
  const base = OS_BASE[env1(env)];
  const q = `grant_type=consumer_credentials&consumer_key=${encodeURIComponent(env.WHCC_OS_KEY || "")}&consumer_secret=${encodeURIComponent(env.WHCC_OS_SECRET || "")}`;
  let r = await fetch(`${base}/api/AccessToken?${q}`, { headers: { accept: "application/json" } });
  if (!r.ok) r = await fetch(`${base}/api/AccessToken`, { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded", accept: "application/json" }, body: q });
  if (!r.ok) throw new Error(`os token ${r.status}: ${(await r.text()).slice(0, 200)}`);
  const j = await r.json();
  return j.Token || j.token || "";
}

// ---------------------------------------------------------------- Stripe (raw REST, form-encoded)
function form(obj, prefix, out = []) {
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}[${k}]` : k;
    if (v === undefined || v === null) continue;
    if (typeof v === "object") form(v, key, out);
    else out.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(v))}`);
  }
  return out.join("&");
}
async function stripe(env, path, obj) {
  const r = await fetch(`https://api.stripe.com/v1/${path}`, {
    method: "POST", headers: { authorization: `Bearer ${env.STRIPE_SECRET_KEY}`, "content-type": "application/x-www-form-urlencoded" }, body: form(obj),
  });
  const j = await r.json();
  if (!r.ok) throw new Error(`stripe ${path} ${r.status}: ${(j.error && j.error.message) || ""}`);
  return j;
}
async function stripeVerify(req, raw, secret) {
  const h = req.headers.get("stripe-signature") || "";
  const t = (h.match(/t=(\d+)/) || [])[1];
  const sigs = [...h.matchAll(/v1=([0-9a-f]+)/g)].map((m) => m[1]);
  if (!t || !sigs.length) return false;
  if (Math.abs(Date.now() / 1000 - Number(t)) > 600) return false;
  const want = await hmacHex(secret, `${t}.${raw}`);
  return sigs.some((s) => safeEq(s, want));
}

// ---------------------------------------------------------------- the flow
async function createEditor(req, env, body) {
  const slug = (body.slug || "").toString().toLowerCase();
  const gal = await loadGallery(slug);
  if (!gal) return jres({ ok: false, error: "not_found" }, 404);
  if (!gal.storeOn) return jres({ ok: false, error: "store_off" }, 403);
  if (!(await galleryAuthed(req, gal, body, env))) return jres({ ok: false, error: "locked" }, 401);
  const ids = Array.isArray(body.ids) ? body.ids.map(String).filter((x) => /^[A-Za-z0-9_-]{6,64}$/.test(x)).slice(0, 60) : [];
  const man = await manifest(env, slug);
  const byId = new Map(man.map((p) => [p.id, p]));
  const chosen = ids.length ? ids.map((id) => byId.get(id)).filter(Boolean) : man.slice(0, 40);
  if (!chosen.length) return jres({ ok: false, error: "no_photos" }, 400);
  const list = await products(env);
  const product = pickProduct(list, (body.productId || "").toString());
  if (!product) return jres({ ok: false, error: "no_products" }, 502);
  const exp = Date.now() + ASSET_TTL_MS;
  const photos = [];
  for (const p of chosen) {
    const u = await signedAsset(env, slug, p.id, exp);
    photos.push({ id: p.id, name: p.name || `${p.id}.jpg`, url: u, printUrl: u, filetype: "jpg", size: { original: { width: Number(p.w) || 3000, height: Number(p.h) || 2000 } } });
  }
  const accountId = `lazo-${slug}`;
  const j = await editorCall(env, accountId, "POST", "/editors", {
    userId: accountId,
    productId: product.id,
    redirects: {
      complete: { text: "Checkout", url: `${SITE}/prints/return?editor=%EDITOR_ID%&slug=${slug}` },
      cancel: { text: "Back to your gallery", url: `${SITE}/g/${slug}` },
    },
    settings: {
      quantity: { default: 1 },
      client: { vendor: "default", accentColor: "#52284F", hidePricing: false, disableUploads: true, markupType: "PERCENT", markupAmount: Number(env.PRINT_MARKUP) || 100 },
      controls: { productSwitcher: "enabled", sizeSelector: "enabled" },
    },
    photos,
  });
  await rput(env, `_prints/editors/${j.editorId}.json`, { editorId: j.editorId, slug, accountId, productId: product.id, productName: product.name,
    ids: chosen.map((p) => p.id), coupleUid: (body.coupleUid || "").toString().slice(0, 80), createdAt: new Date().toISOString(), env: env1(env) });
  return jres({ ok: true, url: j.url, editorId: j.editorId, product: product.name });
}

async function exportEditor(env, ed, extra) {
  const payload = Object.assign({ editors: [{ editorId: ed.editorId }] }, extra || {});
  return editorCall(env, ed.accountId, "PUT", "/oas/editors/export", payload);
}

async function cart(env, editorId, slug) {
  const ed = await rget(env, `_prints/editors/${editorId}.json`);
  if (!ed || ed.slug !== slug) return jres({ ok: false, error: "not_found" }, 404);
  const x = await exportEditor(env, ed);
  const items = (x.items || []).map((it) => {
    const pv = it.editor && it.editor.productPreviews ? Object.values(it.editor.productPreviews)[0] : null;
    return {
      editorId: it.id,
      preview: pv ? (pv.scale_512 || pv.scale_256 || "") : "",
      summary: (it.editor && it.editor.selectionsSummary || []).map((s) => s.description).filter(Boolean),
      quantity: (it.pricing && it.pricing.quantity) || 1,
      unit: it.pricing ? Number(it.pricing.markedUpPrice) / Math.max(1, Number(it.pricing.quantity) || 1) : 0,
      price: it.pricing ? Number(it.pricing.markedUpPrice) : 0,
    };
  });
  return jres({ ok: true, product: ed.productName, items, ship: SHIP_METHODS, env: env1(env) });
}

function cleanAddress(a) {
  const s = (k, n) => (a && a[k] ? String(a[k]).trim().slice(0, n) : "");
  const out = { name: s("name", 80), addr1: s("addr1", 100), addr2: s("addr2", 100), city: s("city", 60), state: s("state", 2).toUpperCase(), zip: s("zip", 10), country: "US", email: s("email", 120) };
  if (!out.name || !out.addr1 || !out.city || !/^[A-Z]{2}$/.test(out.state) || !/^\d{5}(-\d{4})?$/.test(out.zip) || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(out.email)) return null;
  if (!out.addr2) delete out.addr2;
  return out;
}
function fromAddress(env) {
  return { name: env.PRINT_FROM_NAME || "Lazo Weddings", addr1: env.PRINT_FROM_ADDR1 || "", addr2: env.PRINT_FROM_ADDR2 || undefined, city: env.PRINT_FROM_CITY || "", state: env.PRINT_FROM_STATE || "", zip: env.PRINT_FROM_ZIP || "", country: "US" };
}

// Quote at WHCC (create without confirm), then a Stripe Checkout session.
async function checkout(env, body) {
  const editorId = (body.editor || "").toString();
  const slug = (body.slug || "").toString().toLowerCase();
  const ed = await rget(env, `_prints/editors/${editorId}.json`);
  if (!ed || ed.slug !== slug) return jres({ ok: false, error: "not_found" }, 404);
  const addr = cleanAddress(body.address);
  if (!addr) return jres({ ok: false, error: "bad_address" }, 400);
  const ship = SHIP_METHODS[Number(body.ship)] ? Number(body.ship) : 553;
  const qty = Math.min(50, Math.max(1, Number(body.quantity) || 1));
  const oid = newId("po_");
  const from = fromAddress(env);
  if (!from.addr1) return jres({ ok: false, error: "no_return_address" }, 500);
  const x = await exportEditor(env, ed, {
    editors: [{ editorId, quantity: qty }],
    orderAttributes: [548, ship],
    entryId: oid,
    reference: `Lazo ${oid} ${slug}`,
    shipToAddress: { name: addr.name, addr1: addr.addr1, addr2: addr.addr2, city: addr.city, state: addr.state, zip: addr.zip, country: "US", email: addr.email },
    shipFromAddress: from,
  });
  const item = (x.items || [])[0] || {};
  const customerProduct = item.pricing ? Number(item.pricing.markedUpPrice) : 0;
  if (!x.order || !customerProduct) return jres({ ok: false, error: "export_failed" }, 502);
  // Create (unconfirmed) at WHCC: this is the quote with shipping and tax at wholesale.
  const created = await editorCall(env, ed.accountId, "POST", "/oas/orders/create", x.order);
  const o0 = (created.Orders || [])[0] || {};
  let shipping = 0;
  for (const p of (o0.Products || [])) if (/drop ship|usps|one-day|expedited|economy/i.test(p.ProductDescription || "")) shipping += Number(p.Price) || 0;
  const wholesale = Number(o0.Total) || 0;
  const subtotal = Math.round(customerProduct * 100) / 100;
  const shipCharge = Math.round(shipping * 100) / 100;
  const total = Math.round((subtotal + shipCharge) * 100) / 100;
  const order = {
    oid, slug, editorId, coupleUid: ed.coupleUid || "", product: ed.productName, summary: item.editor && item.editor.selectionsSummary ? item.editor.selectionsSummary.map((s) => s.description) : [],
    preview: item.editor && item.editor.productPreviews ? (Object.values(item.editor.productPreviews)[0] || {}).scale_512 || "" : "",
    quantity: qty, ship, shipLabel: SHIP_METHODS[ship].label, address: addr,
    customer: { subtotal, shipping: shipCharge, total, currency: "USD" },
    whcc: { confirmationId: created.ConfirmationID || "", wholesaleTotal: wholesale, order: x.order, env: env1(env) },
    status: "pending_payment", createdAt: new Date().toISOString(), events: [],
  };
  await rput(env, `_prints/orders/${oid}.json`, order);
  if (order.whcc.confirmationId) await rput(env, `_prints/byconf/${order.whcc.confirmationId}.json`, { oid });
  const idx = (await rget(env, `_prints/gallery/${slug}.json`)) || [];
  idx.unshift(oid);
  await rput(env, `_prints/gallery/${slug}.json`, idx.slice(0, 200));
  if (!env.STRIPE_SECRET_KEY) return jres({ ok: false, error: "no_stripe", oid }, 500);
  const sess = await stripe(env, "checkout/sessions", {
    mode: "payment",
    customer_email: addr.email,
    success_url: `${SITE}/prints/thanks?o=${oid}`,
    cancel_url: `${SITE}/prints/return?editor=${editorId}&slug=${slug}`,
    metadata: { oid, slug, editorId },
    "line_items[0][quantity]": 1,
    "line_items[0][price_data][currency]": "usd",
    "line_items[0][price_data][unit_amount]": Math.round(subtotal * 100),
    "line_items[0][price_data][product_data][name]": `${ed.productName}${qty > 1 ? ` × ${qty}` : ""}${order.summary.length ? ` · ${order.summary.slice(0, 2).join(", ")}` : ""}`,
    "line_items[1][quantity]": 1,
    "line_items[1][price_data][currency]": "usd",
    "line_items[1][price_data][unit_amount]": Math.round(shipCharge * 100),
    "line_items[1][price_data][product_data][name]": `Shipping · ${SHIP_METHODS[ship].label}`,
  });
  order.stripe = { sessionId: sess.id };
  await rput(env, `_prints/orders/${oid}.json`, order);
  return jres({ ok: true, url: sess.url, oid, total });
}

// After payment: confirm at WHCC. If the earlier quote has gone stale, quote again first.
async function confirmOrder(env, order) {
  const ed = await rget(env, `_prints/editors/${order.editorId}.json`);
  if (!ed) throw new Error("editor record missing");
  const tryConfirm = async (cid) => editorCall(env, ed.accountId, "POST", `/oas/orders/${encodeURIComponent(cid)}/confirm`, undefined);
  let cid = order.whcc.confirmationId;
  try {
    if (!cid) throw new Error("no confirmation id");
    await tryConfirm(cid);
  } catch (e) {
    const created = await editorCall(env, ed.accountId, "POST", "/oas/orders/create", order.whcc.order);
    cid = created.ConfirmationID;
    await tryConfirm(cid);
    order.whcc.confirmationId = cid;
    await rput(env, `_prints/byconf/${cid}.json`, { oid: order.oid });
  }
  order.status = "submitted";
  order.submittedAt = new Date().toISOString();
  order.events.push({ at: order.submittedAt, type: "submitted", confirmationId: cid });
  await rput(env, `_prints/orders/${order.oid}.json`, order);
}

async function stripeWebhook(req, env) {
  const raw = await req.text();
  if (!env.STRIPE_WEBHOOK_SECRET || !(await stripeVerify(req, raw, env.STRIPE_WEBHOOK_SECRET))) return new Response("bad signature", { status: 400 });
  let ev; try { ev = JSON.parse(raw); } catch { return new Response("bad json", { status: 400 }); }
  if (ev.type !== "checkout.session.completed") return new Response("ignored", { status: 200 });
  const s = ev.data && ev.data.object || {};
  const oid = s.metadata && s.metadata.oid;
  if (!oid) return new Response("no oid", { status: 200 });
  const order = await rget(env, `_prints/orders/${oid}.json`);
  if (!order) return new Response("unknown order", { status: 200 });
  if (order.status !== "pending_payment") return new Response("already handled", { status: 200 });
  order.status = "paid";
  order.paidAt = new Date().toISOString();
  order.stripe = Object.assign(order.stripe || {}, { paymentIntent: s.payment_intent || "", amountTotal: s.amount_total || 0 });
  order.events.push({ at: order.paidAt, type: "paid" });
  await rput(env, `_prints/orders/${oid}.json`, order);
  try {
    await confirmOrder(env, order);
  } catch (e) {
    order.status = "paid_unsubmitted";
    order.error = String(e).slice(0, 300);
    await rput(env, `_prints/orders/${oid}.json`, order);
    // 500 makes Stripe retry, and the next attempt finds status paid_unsubmitted below.
    return new Response("confirm failed", { status: 500 });
  }
  return new Response("ok", { status: 200 });
}

// WHCC -> us. The registration handshake posts `verifier`; everything else is signed.
async function whccWebhook(req, env) {
  const raw = await req.text();
  const ct = req.headers.get("content-type") || "";
  let fields = {};
  if (/json/i.test(ct)) { try { fields = JSON.parse(raw); } catch { fields = {}; } }
  else { const p = new URLSearchParams(raw); for (const [k, v] of p) fields[k] = v; }
  if (fields.verifier) {
    try {
      const token = await osToken(env);
      const r = await fetch(`${OS_BASE[env1(env)]}/api/callback/verify`, { method: "POST", headers: { authorization: `Bearer ${token}`, "content-type": "application/x-www-form-urlencoded" }, body: `verifier=${encodeURIComponent(fields.verifier)}` });
      await rput(env, `_prints/webhook-verify.json`, { at: new Date().toISOString(), status: r.status, body: (await r.text()).slice(0, 300) });
    } catch (e) {
      await rput(env, `_prints/webhook-verify.json`, { at: new Date().toISOString(), error: String(e).slice(0, 300) });
    }
    return new Response("ok", { status: 200 });
  }
  // signature: HMAC-SHA256 of the raw body with the Order Submit consumer secret, uppercase hex
  const sigH = req.headers.get("whcc-signature") || "";
  const t = (sigH.match(/t=(\d+)/) || [])[1];
  const v1 = (sigH.match(/v1=([0-9A-Fa-f]+)/) || [])[1];
  if (env.WHCC_OS_SECRET && !env.WHCC_WEBHOOK_LAX) {
    if (!t || !v1) return new Response("no signature", { status: 401 });
    const want = (await hmacHex(env.WHCC_OS_SECRET, raw)).toUpperCase();
    const want2 = (await hmacHex(env.WHCC_OS_SECRET, `${t}.${raw}`)).toUpperCase();
    const got = v1.toUpperCase();
    if (!safeEq(got, want) && !safeEq(got, want2)) return new Response("bad signature", { status: 401 });
  }
  // V1 carries the structured copy in `json`; V2 is the JSON itself.
  let ev = fields;
  if (typeof fields.json === "string") { try { ev = JSON.parse(fields.json); } catch { ev = fields; } }
  const cid = String(ev.ConfirmationId || ev.ConfirmationID || "");
  const seq = String(ev.SequenceNumber || "");
  const type = String(ev.EventId || ev.Event || ev.Type || "").toLowerCase();
  if (!cid) return new Response("no confirmation id", { status: 200 });
  const key = `_prints/events/${cid}_${seq}_${type}.json`;
  const ref = await rget(env, `_prints/byconf/${cid}.json`);
  if (!ref) { await rput(env, key, { at: new Date().toISOString(), orphan: true, ev }); return new Response("unknown order", { status: 200 }); }
  const order = await rget(env, `_prints/orders/${ref.oid}.json`);
  if (!order) return new Response("order missing", { status: 500 });
  const msg = ev.Message && typeof ev.Message === "object" ? ev.Message : {};
  const status = String(msg.Status || ev.Status || "").toLowerCase();
  const at = new Date().toISOString();
  if (/shipped/.test(type) || /shipped/.test(status)) {
    let tracking = msg.Tracking;
    if (typeof tracking === "string") { try { tracking = JSON.parse(tracking); } catch { tracking = [tracking]; } }
    const list = new Set([...(order.tracking || []), ...(Array.isArray(tracking) ? tracking.map(String) : [])]);
    order.tracking = [...list];
    order.carrier = msg.Carrier || order.carrier || "";
    order.shipDate = msg.ShipDate || order.shipDate || "";
    order.trackingUrl = msg.TrackingUrl || msg.TrackingURL || order.trackingUrl || "";
    order.status = "shipped";
    order.events.push({ at, type: "shipped", seq, tracking: [...list] });
  } else if (/reject/.test(type) || /reject|error|missing/.test(status)) {
    order.status = "rejected";
    order.error = String(msg.Status || msg.Error || ev.Message || "").slice(0, 400);
    order.events.push({ at, type: "rejected", seq, error: order.error });
  } else if (/received|accept/.test(type) || /received|accept/.test(status)) {
    if (order.status !== "shipped") order.status = "accepted";
    order.whcc.orderNumber = msg.OrderNumber || order.whcc.orderNumber || "";
    order.events.push({ at, type: "accepted", seq, orderNumber: order.whcc.orderNumber });
  } else if (/image/.test(type)) {
    order.events.push({ at, type: "image", seq, status: String(msg.Status || "") });
  } else {
    order.events.push({ at, type: type || "event", seq, raw: ev });
  }
  await rput(env, `_prints/orders/${order.oid}.json`, order);
  await rput(env, key, { at, seen: true });
  return new Response("ok", { status: 200 });
}

function publicOrder(o) {
  return { oid: o.oid, slug: o.slug, product: o.product, summary: o.summary, preview: o.preview, quantity: o.quantity, shipLabel: o.shipLabel,
    total: o.customer && o.customer.total, status: o.status, createdAt: o.createdAt, paidAt: o.paidAt || "", submittedAt: o.submittedAt || "",
    carrier: o.carrier || "", tracking: o.tracking || [], trackingUrl: o.trackingUrl || "", shipDate: o.shipDate || "", orderNumber: o.whcc && o.whcc.orderNumber || "", error: o.status === "rejected" ? o.error : "" };
}

// ---------------------------------------------------------------- pages
function shell(title, body) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>${esc(title)} · Lazo</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600&family=Jost:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>:root{--plum:#52284F;--deep:#3D1C3B;--gold:#D9B77C;--ivory:#FAF6F0;--ink:#241E2B;--muted:#6B5F72;--line:#E6D6B8}*{box-sizing:border-box}body{margin:0;background:var(--ivory);color:var(--ink);font:300 16px/1.55 Jost,sans-serif}
.top{display:flex;align-items:center;gap:12px;padding:14px 22px;border-bottom:1px solid var(--line);background:rgba(250,246,240,.9);position:sticky;top:0}.top a{color:var(--plum);text-decoration:none;font-weight:600}
.wrap{max-width:900px;margin:0 auto;padding:30px 20px 60px}h1{font:500 38px/1.05 "Cormorant Garamond",serif;color:var(--plum);margin:0 0 8px}h2{font:600 20px "Cormorant Garamond",serif;color:var(--plum);margin:26px 0 8px}
.card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px}.row{display:grid;gap:16px;grid-template-columns:1fr}@media(min-width:760px){.row{grid-template-columns:1.1fr 1fr}}
.item{display:flex;gap:16px;align-items:flex-start}.item img{width:150px;border-radius:10px;border:1px solid var(--line)}.item b{font:600 20px "Cormorant Garamond",serif;color:var(--plum);display:block}.item .m{color:var(--muted);font-size:14px}
label{display:block;font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:12px 0 5px}input,select{width:100%;font:inherit;font-size:16px;padding:11px 13px;border:1px solid var(--line);border-radius:10px;background:#fff;color:var(--ink)}
.g2{display:grid;gap:10px;grid-template-columns:1fr 1fr}.tot{display:flex;justify-content:space-between;padding:8px 0;border-top:1px solid var(--line)}.tot b{font-size:18px}
.btn{display:inline-block;background:var(--plum);color:var(--ivory);border:0;border-radius:999px;padding:14px 26px;font:600 15px Jost,sans-serif;cursor:pointer;width:100%;margin-top:16px}.btn[disabled]{opacity:.5}
.fine{font-size:12.5px;color:var(--muted);margin-top:10px}.err{background:#FBECEC;color:#B04343;border-radius:10px;padding:10px 12px;margin-top:10px;display:none}.pill{display:inline-block;border-radius:999px;padding:3px 10px;font-size:12px;font-weight:600;background:#F3E7CE;color:#8A6A2F}.pill.ok{background:#E7F3EC;color:#2E8B6B}
</style></head><body><div class="top"><a href="/">Lazo</a><span style="color:var(--muted);font-size:13px">Print store</span></div><div class="wrap">${body}</div></body></html>`;
}

function returnPage(editorId, slug) {
  const body = `<h1>Your cart</h1><p style="color:var(--muted);margin:0 0 18px">Printed by a professional lab and shipped to your door. Lazo is the seller; the box carries no lab branding.</p>
<div id="load" class="card">Loading your design…</div>
<div id="cart" class="row" style="display:none">
 <div class="card"><div class="item"><img id="pv" alt=""><div><b id="pname"></b><div class="m" id="psum"></div><label>Quantity</label><input id="qty" type="number" min="1" max="50" value="1" style="width:110px"></div></div>
  <h2>Ship to</h2><input id="name" placeholder="Full name"><input id="addr1" placeholder="Street address" style="margin-top:8px"><input id="addr2" placeholder="Apt, suite (optional)" style="margin-top:8px">
  <div class="g2" style="margin-top:8px"><input id="city" placeholder="City"><input id="state" placeholder="State (2 letters)" maxlength="2"></div>
  <div class="g2" style="margin-top:8px"><input id="zip" placeholder="ZIP"><input id="email" type="email" placeholder="Email for the receipt"></div>
  <label>Shipping</label><select id="ship"></select><div class="fine">US street addresses only. The return address on the label is Lazo's.</div></div>
 <div class="card"><h2 style="margin-top:0">Summary</h2><div class="tot"><span>Product</span><span id="tp"></span></div><div class="tot"><span>Shipping</span><span>at checkout</span></div><div class="tot"><b>Due now</b><b id="tt"></b></div>
  <p class="fine">Shipping and any sales tax are added at checkout from the lab's rate for your address. You pay Lazo through Stripe; the order goes to the lab the moment payment clears.</p>
  <button class="btn" id="go">Continue to payment</button><div class="err" id="err"></div>
  <p class="fine"><a href="/g/${esc(slug)}" style="color:var(--plum)">← Back to the gallery</a> · <a id="edit" href="#" style="color:var(--plum)">Edit the design</a></p></div>
</div>
<script>
(function(){var E=${JSON.stringify(editorId)},S=${JSON.stringify(slug)},$=function(i){return document.getElementById(i)},data=null;
fetch('/api/prints/cart?editor='+encodeURIComponent(E)+'&slug='+encodeURIComponent(S)).then(function(r){return r.json()}).then(function(j){
 if(!j.ok){$('load').textContent='We could not load this design. Go back to the gallery and try again.';return}
 data=j;var it=j.items[0];$('load').style.display='none';$('cart').style.display='';if(it.preview)$('pv').src=it.preview;$('pname').textContent=j.product;$('psum').textContent=it.summary.join(' · ');$('qty').value=it.quantity||1;
 var sel=$('ship');Object.keys(j.ship).forEach(function(k){var o=document.createElement('option');o.value=k;o.textContent=j.ship[k].label;sel.appendChild(o)});
 function tot(){var q=Math.max(1,parseInt($('qty').value||'1',10));var p=it.unit*q;$('tp').textContent='$'+p.toFixed(2);$('tt').textContent='$'+p.toFixed(2)}tot();$('qty').addEventListener('input',tot);
}).catch(function(){$('load').textContent='We could not load this design.'});
$('edit').addEventListener('click',function(e){e.preventDefault();fetch('/api/prints/edit-link',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({editor:E,slug:S})}).then(function(r){return r.json()}).then(function(j){if(j.url)location.href=j.url})});
$('go').addEventListener('click',function(){var b=$('go');b.disabled=true;$('err').style.display='none';
 var body={editor:E,slug:S,quantity:parseInt($('qty').value||'1',10),ship:parseInt($('ship').value,10),address:{name:$('name').value,addr1:$('addr1').value,addr2:$('addr2').value,city:$('city').value,state:$('state').value,zip:$('zip').value,email:$('email').value}};
 fetch('/api/prints/checkout',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json()}).then(function(j){
  if(j.ok&&j.url){location.href=j.url;return}var m={bad_address:'Check the address: name, street, city, two-letter state, ZIP and an email.',no_return_address:'The store is not configured yet.',no_stripe:'Payments are not configured yet.',export_failed:'The lab could not price this design. Try editing it again.'};
  $('err').textContent=m[j.error]||'Something went wrong. Try again.';$('err').style.display='block';b.disabled=false}).catch(function(){$('err').textContent='Something went wrong. Try again.';$('err').style.display='block';b.disabled=false})});
})();
</script>`;
  return new Response(shell("Your cart", body), { headers: { "content-type": "text/html;charset=utf-8", "cache-control": "no-store", "x-robots-tag": "noindex" } });
}

function thanksPage(oid) {
  const body = `<h1>Thank you</h1><div class="card" id="c">Checking your order…</div><p class="fine">Order <b>${esc(oid)}</b>. Your receipt is in your email. We will email you again when it ships, with tracking.</p>
<script>(function(){fetch('/api/prints/order?o='+encodeURIComponent(${JSON.stringify(oid)})).then(function(r){return r.json()}).then(function(j){var c=document.getElementById('c');if(!j.ok){c.textContent='We could not find that order.';return}var o=j.order;
var s={pending_payment:'Waiting for payment',paid:'Paid - sending to the lab',paid_unsubmitted:'Paid - we are sending it to the lab',submitted:'At the lab',accepted:'In production',shipped:'Shipped',rejected:'Needs attention'}[o.status]||o.status;
c.innerHTML='<div class="item">'+(o.preview?'<img src="'+o.preview+'" alt="">':'')+'<div><b>'+o.product+(o.quantity>1?' × '+o.quantity:'')+'</b><div class="m">'+(o.summary||[]).join(' · ')+'</div><div style="margin-top:8px"><span class="pill'+(o.status==='shipped'?' ok':'')+'">'+s+'</span></div>'+(o.tracking&&o.tracking.length?'<div class="m" style="margin-top:8px">'+(o.carrier||'')+' '+o.tracking.join(', ')+(o.trackingUrl?' · <a href="'+o.trackingUrl+'">Track</a>':'')+'</div>':'')+'</div></div>'})})();</script>`;
  return new Response(shell("Thank you", body), { headers: { "content-type": "text/html;charset=utf-8", "cache-control": "no-store", "x-robots-tag": "noindex" } });
}

// ---------------------------------------------------------------- router
export async function printsRoute(req, url, env) {
  const p = url.pathname;
  if (!(p.startsWith("/api/prints/") || p.startsWith("/prints/") || /^\/g\/[a-z0-9-]{1,80}\/store\//.test(p))) return null;
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: { "access-control-allow-origin": "*", "access-control-allow-methods": "GET,POST,OPTIONS", "access-control-allow-headers": "content-type" } });
  try {
    if (p === "/api/prints/products" && req.method === "GET") return jres({ ok: true, products: await products(env) });
    const gm = p.match(/^\/g\/([a-z0-9-]{1,80})\/store\/editor$/);
    if (gm && req.method === "POST") { const b = await req.json().catch(() => ({})); b.slug = gm[1]; return createEditor(req, env, b); }
    if (p === "/api/prints/editor" && req.method === "POST") return createEditor(req, env, await req.json().catch(() => ({})));
    if (p === "/api/prints/cart" && req.method === "GET") return cart(env, (url.searchParams.get("editor") || "").slice(0, 80), (url.searchParams.get("slug") || "").toLowerCase());
    if (p === "/api/prints/edit-link" && req.method === "POST") {
      const b = await req.json().catch(() => ({}));
      const ed = await rget(env, `_prints/editors/${(b.editor || "").toString().slice(0, 80)}.json`);
      if (!ed || ed.slug !== (b.slug || "").toString().toLowerCase()) return jres({ ok: false, error: "not_found" }, 404);
      const j = await editorCall(env, ed.accountId, "POST", `/editors/${encodeURIComponent(ed.editorId)}/edit-link`, {});
      return jres({ ok: true, url: j.url });
    }
    if (p === "/api/prints/checkout" && req.method === "POST") return checkout(env, await req.json().catch(() => ({})));
    if (p === "/prints/return" && req.method === "GET") {
      const e = (url.searchParams.get("editor") || "").slice(0, 80), s = (url.searchParams.get("slug") || "").toLowerCase();
      if (!e || !/^[a-z0-9-]{1,80}$/.test(s)) return new Response("Not found", { status: 404 });
      return returnPage(e, s);
    }
    if (p === "/prints/thanks" && req.method === "GET") return thanksPage((url.searchParams.get("o") || "").slice(0, 40));
    if (p === "/api/prints/order" && req.method === "GET") {
      const o = await rget(env, `_prints/orders/${(url.searchParams.get("o") || "").replace(/[^a-z0-9_]/gi, "").slice(0, 40)}.json`);
      return o ? jres({ ok: true, order: publicOrder(o) }) : jres({ ok: false, error: "not_found" }, 404);
    }
    if (p === "/api/prints/orders" && req.method === "GET") {
      const slug = (url.searchParams.get("slug") || "").toLowerCase();
      const gal = await loadGallery(slug);
      if (!gal) return jres({ ok: false, error: "not_found" }, 404);
      if (!(await galleryAuthed(req, gal, { passcode: url.searchParams.get("passcode") || "" }, env))) return jres({ ok: false, error: "locked" }, 401);
      const idx = (await rget(env, `_prints/gallery/${slug}.json`)) || [];
      const out = [];
      for (const oid of idx.slice(0, 30)) { const o = await rget(env, `_prints/orders/${oid}.json`); if (o && o.status !== "pending_payment") out.push(publicOrder(o)); }
      return jres({ ok: true, orders: out });
    }
    if (p === "/api/prints/webhook/stripe" && req.method === "POST") return stripeWebhook(req, env);
    if (p === "/api/prints/webhook/whcc" && req.method === "POST") return whccWebhook(req, env);
    if (p === "/api/prints/admin/register-webhook" && req.method === "POST") {
      if (!env.PRINTS_ADMIN_KEY || !safeEq(url.searchParams.get("key") || "", env.PRINTS_ADMIN_KEY)) return new Response("forbidden", { status: 403 });
      const token = await osToken(env);
      const r = await fetch(`${OS_BASE[env1(env)]}/api/callback/create`, { method: "POST", headers: { authorization: `Bearer ${token}`, "content-type": "application/x-www-form-urlencoded" }, body: `callbackUri=${encodeURIComponent(`${SITE}/api/prints/webhook/whcc`)}` });
      const text = await r.text();
      const verify = await rget(env, `_prints/webhook-verify.json`);
      return jres({ ok: r.ok, status: r.status, body: text.slice(0, 500), verify });
    }
    // Which environment do the credentials belong to? Tries a token in both, echoes nothing secret.
    if (p === "/api/prints/admin/ping" && req.method === "GET") {
      if (!env.PRINTS_ADMIN_KEY || !safeEq(url.searchParams.get("key") || "", env.PRINTS_ADMIN_KEY)) return new Response("forbidden", { status: 403 });
      const out = { lengths: { editorKey: (env.WHCC_EDITOR_KEY || "").length, editorSecret: (env.WHCC_EDITOR_SECRET || "").length, osKey: (env.WHCC_OS_KEY || "").length, osSecret: (env.WHCC_OS_SECRET || "").length }, configured: { editorKey: !!env.WHCC_EDITOR_KEY, editorSecret: !!env.WHCC_EDITOR_SECRET, osKey: !!env.WHCC_OS_KEY, osSecret: !!env.WHCC_OS_SECRET, stripe: !!env.STRIPE_SECRET_KEY, stripeWebhook: !!env.STRIPE_WEBHOOK_SECRET, returnAddress: !!env.PRINT_FROM_ADDR1 }, env: env1(env), editor: {}, orderSubmit: {} };
      for (const e of ["sandbox", "production"]) {
        try {
          const r = await fetch(`${EDITOR_BASE[e]}/auth/access-token`, { method: "POST", headers: { accept: "application/json", "content-type": "application/json" }, body: JSON.stringify({ key: env.WHCC_EDITOR_KEY, secret: env.WHCC_EDITOR_SECRET, claims: { accountId: "lazo-ping" } }) });
          out.editor[e] = r.ok ? "ok" : `${r.status} ${(await r.text()).replace(/[A-Za-z0-9_-]{30,}/g, "…").slice(0, 200)}`;
        } catch (err) { out.editor[e] = "error"; }
        try {
          const q = `grant_type=consumer_credentials&consumer_key=${encodeURIComponent(env.WHCC_OS_KEY || "")}&consumer_secret=${encodeURIComponent(env.WHCC_OS_SECRET || "")}`;
          let r = await fetch(`${OS_BASE[e]}/api/AccessToken?${q}`, { headers: { accept: "application/json" } });
          if (!r.ok) r = await fetch(`${OS_BASE[e]}/api/AccessToken`, { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded", accept: "application/json" }, body: q });
          out.orderSubmit[e] = r.ok ? "ok" : `${r.status}`;
        } catch (err) { out.orderSubmit[e] = "error"; }
      }
      try { out.productsInEnv = (await products(env)).length; } catch (err) { out.productsInEnv = "error: " + String(err).slice(0, 120); }
      return jres(out);
    }
    if (p === "/api/prints/admin/order" && req.method === "GET") {
      if (!env.PRINTS_ADMIN_KEY || !safeEq(url.searchParams.get("key") || "", env.PRINTS_ADMIN_KEY)) return new Response("forbidden", { status: 403 });
      const o = await rget(env, `_prints/orders/${(url.searchParams.get("o") || "").replace(/[^a-z0-9_]/gi, "").slice(0, 40)}.json`);
      return o ? jres(o) : jres({ ok: false }, 404);
    }
    return new Response("Not found", { status: 404, headers: { "x-robots-tag": "noindex" } });
  } catch (e) {
    return jres({ ok: false, error: "server", detail: String(e).slice(0, 300) }, 502);
  }
}

// worker/src/rt.js
// Build ID: JC-LAZO-CALLS-1016-WORKER-001
//
// LAZO VIDEO CALLS - the media half. A proxy in front of Cloudflare Realtime
// (Serverless SFU app "lazo-video") plus one Durable Object per call.
//
// Why a proxy: the app secret (CF_REALTIME_APP_SECRET) must never reach a
// phone, and every camera or mic track has to pass through us so the call log
// is first-hand evidence of who had video on, not something a client claims.
//
// Every request carries the call token from the callJoin callable
// (functions-dashboard/calls.js): base64url(JSON {c callId, i inquiryId,
// u uid, r role, n name, o otherName, exp}) + '.' + HMAC-SHA256, shared secret
// CALL_TOKEN_SECRET. Only the thread's vendor and couple ever get one.
//
// Safety rules enforced here, not in the app:
//   - one person per side (vendor, couple); nobody else can join or pull media;
//   - the couple's VIDEO track is refused until the vendor allows the camera,
//     and taking that back force-closes it on the SFU;
//   - a session can only touch its own tracks and pull the other side's.
// Events (join, leave, drop, video_on/off, audio_on, camera_allowed/revoked,
// ended) go to callEvent, which appends them to calls/{id}.
//
// Routes (all POST/PUT with Authorization: Bearer <call token>):
//   POST /rt/join                              -> {sessionId, role, camAllowed, other}
//   POST /rt/room                              -> room state (polled every ~2s)
//   POST /rt/allow     {on}                    vendor only
//   POST /rt/leave
//   POST /rt/sessions/{sid}/tracks/new         (SFU passthrough, checked)
//   PUT  /rt/sessions/{sid}/renegotiate        (SFU passthrough, checked)
//   PUT  /rt/sessions/{sid}/tracks/close       (SFU passthrough, checked)

const SFU = "https://rtc.live.cloudflare.com/v1/apps";
const CORS_RT = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "POST, PUT, OPTIONS",
  "access-control-allow-headers": "authorization, content-type",
  "access-control-max-age": "86400",
};
const PRESENT_MS = 15000;        // a side counts as in the room if it polled this recently
const DROP_MS = 45000;           // ...and as gone after this long
const MAX_CALL_MS = 3 * 3600000;

const j = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json", "cache-control": "no-store", ...CORS_RT } });
const b64uDec = (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4)), (c) => c.charCodeAt(0));
const b64uEnc = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");

async function hmacKey(secret) {
  return crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
}
// graceMs: a token only has to be fresh to JOIN; once in, it works for the rest of the call.
export async function verifyCallToken(tok, secret, graceMs = 0) {
  const [body, sig] = String(tok || "").split(".");
  if (!body || !sig || !secret) return null;
  const want = b64uEnc(await crypto.subtle.sign("HMAC", await hmacKey(secret), new TextEncoder().encode(body)));
  if (want.length !== sig.length) return null;
  let diff = 0;
  for (let i = 0; i < want.length; i++) diff |= want.charCodeAt(i) ^ sig.charCodeAt(i);
  if (diff) return null;
  let p;
  try { p = JSON.parse(new TextDecoder().decode(b64uDec(body))); } catch (e) { return null; }
  if (!p || !p.c || !p.u || !["vendor", "couple"].includes(p.r) || !(p.exp + graceMs > Date.now())) return null;
  return p;
}

// mid -> 'audio' | 'video' from an SDP
export function sdpKinds(sdp) {
  const out = {};
  let kind = null;
  for (const line of String(sdp || "").split(/\r?\n/)) {
    if (line.startsWith("m=")) kind = line.slice(2).split(" ")[0];
    else if (line.startsWith("a=mid:") && kind) out[line.slice(6).trim()] = kind;
  }
  return out;
}

// ------------------------------------------------------------------ route ----
export async function rtRoute(req, env) {
  const url = new URL(req.url);
  if (!url.pathname.startsWith("/rt/")) return null;
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS_RT });
  if (!env.CALL_ROOM || !env.CF_REALTIME_APP_ID || !env.CF_REALTIME_APP_SECRET || !env.CALL_TOKEN_SECRET) return j({ error: "calls-not-configured" }, 503);
  const tok = (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
  const p = await verifyCallToken(tok, env.CALL_TOKEN_SECRET, url.pathname === "/rt/join" ? 0 : MAX_CALL_MS);
  if (!p) return j({ error: "bad-token" }, 401);
  const stub = env.CALL_ROOM.get(env.CALL_ROOM.idFromName(p.c));
  const body = req.method === "GET" ? "" : await req.text();
  return stub.fetch("https://room" + url.pathname.slice(3), {
    method: req.method, body: body || undefined,
    headers: { "content-type": "application/json", "x-call": JSON.stringify(p) },
  });
}

// ---------------------------------------------------------- Durable Object ----
export class CallRoom {
  constructor(state, env) {
    this.state = state;
    this.env = env;
    this.room = null;
  }
  async load() {
    if (!this.room) this.room = (await this.state.storage.get("room")) || { members: {}, camAllowed: false, ended: false, createdAt: Date.now() };
    return this.room;
  }
  async save() { await this.state.storage.put("room", this.room); }

  async sfu(method, path, body) {
    const r = await fetch(`${SFU}/${this.env.CF_REALTIME_APP_ID}${path}`, {
      method, headers: { authorization: `Bearer ${this.env.CF_REALTIME_APP_SECRET}`, "content-type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    let data = {};
    try { data = await r.json(); } catch (e) {}
    return { status: r.status, data };
  }

  async log(events) {
    const url = this.env.CALL_EVENT_URL;
    if (!url || !events.length) return;
    const body = JSON.stringify({ callId: this.room.callId, events });
    const sig = hex(await crypto.subtle.sign("HMAC", await hmacKey(this.env.CALL_TOKEN_SECRET), new TextEncoder().encode(body)));
    try {
      const r = await fetch(url, { method: "POST", headers: { "content-type": "application/json", "x-lazo-sig": sig }, body });
      if (!r.ok) console.log("callEvent", r.status);
    } catch (e) { console.log("callEvent failed", e.message); }
  }
  ev(type, m, detail) { return { type, role: m ? m.role : "", uid: m ? m.uid : "", at: Date.now(), detail: detail || "" }; }

  other(role) { return this.room.members[role === "vendor" ? "couple" : "vendor"] || null; }
  view(role) {
    const me = this.room.members[role] || null;
    const o = this.other(role);
    const now = Date.now();
    return {
      ended: !!this.room.ended,
      camAllowed: role === "vendor" ? true : !!this.room.camAllowed,
      coupleCamAllowed: !!this.room.camAllowed,
      me: me ? { sessionId: me.sessionId } : null,
      other: o && !o.left ? {
        name: o.name, role: o.role, sessionId: o.sessionId, present: now - (o.lastSeen || 0) < PRESENT_MS,
        tracks: Object.values(o.tracks || {}).map((t) => ({ trackName: t.name, kind: t.kind })),
      } : null,
    };
  }

  async fetch(request) {
    const p = JSON.parse(request.headers.get("x-call") || "{}");
    const path = new URL(request.url).pathname;
    await this.load();
    if (!this.room.callId) { this.room.callId = p.c; this.room.inquiryId = p.i; }
    if (this.room.callId !== p.c) return j({ error: "wrong-room" }, 403);
    if (this.room.ended) return j({ error: "ended", ended: true }, 410);
    let body = {};
    try { body = request.method === "GET" ? {} : JSON.parse((await request.text()) || "{}"); } catch (e) { return j({ error: "bad-json" }, 400); }
    const role = p.r;

    // ---- join
    if (path === "/join") {
      const prev = this.room.members[role];
      const s = await this.sfu("POST", "/sessions/new");   // no body: the SFU rejects {} ("sessionDescription")
      if (s.status >= 300 || !s.data.sessionId) return j({ error: "sfu", detail: s.data.errorDescription || s.status }, 502);
      const evs = [];
      if (prev && !prev.left && prev.uid !== p.u) evs.push(this.ev("replaced", prev, `by ${p.u}`));
      this.room.members[role] = { uid: p.u, role, name: p.n, sessionId: s.data.sessionId, tracks: {}, joinedAt: Date.now(), lastSeen: Date.now(), left: false };
      evs.push(this.ev(prev ? "rejoin" : "join", this.room.members[role]));
      await this.save();
      await this.state.storage.setAlarm(Date.now() + 30000);
      await this.log(evs);
      return j({ ok: true, sessionId: s.data.sessionId, role, ...this.view(role) });
    }

    const me = this.room.members[role];
    if (!me || me.uid !== p.u || me.left) return j({ error: "not-joined" }, 409);
    me.lastSeen = Date.now();

    // ---- room state
    if (path === "/room") { await this.save(); return j(this.view(role)); }

    // ---- vendor lets the couple turn the camera on (or takes it back)
    if (path === "/allow") {
      if (role !== "vendor") return j({ error: "vendor-only" }, 403);
      const on = body.on !== false;
      this.room.camAllowed = on;
      const evs = [this.ev(on ? "camera_allowed" : "camera_revoked", me)];
      const c = this.room.members.couple;
      if (!on && c && !c.left) {
        const vids = Object.entries(c.tracks).filter(([, t]) => t.kind === "video").map(([mid]) => mid);
        if (vids.length) {
          await this.sfu("PUT", `/sessions/${c.sessionId}/tracks/close`, { tracks: vids.map((mid) => ({ mid })), force: true });
          for (const mid of vids) delete c.tracks[mid];
          evs.push(this.ev("video_off", c, "closed by the vendor"));
        }
      }
      await this.save();
      await this.log(evs);
      return j(this.view(role));
    }

    // ---- leave
    if (path === "/leave") {
      me.left = true;
      const evs = [this.ev("leave", me, body.report ? "left to report" : "")];
      const o = this.other(role);
      if (!o || o.left) { this.room.ended = true; evs.push(this.ev("ended", null)); }
      await this.save();
      await this.log(evs);
      return j({ ok: true, ended: !!this.room.ended });
    }

    // ---- SFU passthrough, own session only
    const m = path.match(/^\/sessions\/([^/]+)\/(tracks\/new|renegotiate|tracks\/close)$/);
    if (!m) return j({ error: "not-found" }, 404);
    if (m[1] !== me.sessionId) return j({ error: "not-your-session" }, 403);
    const op = m[2];

    if (op === "tracks/new") {
      const tracks = Array.isArray(body.tracks) ? body.tracks : [];
      if (!tracks.length) return j({ error: "no-tracks" }, 400);
      const kinds = sdpKinds(body.sessionDescription && body.sessionDescription.sdp);
      const o = this.other(role);
      const out = [];
      const added = [];
      for (const t of tracks) {
        if (t.location === "local") {
          const kind = kinds[String(t.mid)];
          if (kind !== "audio" && kind !== "video") return j({ error: "unknown-track" }, 400);
          if (role === "couple" && kind === "video" && !this.room.camAllowed) return j({ error: "camera-not-allowed" }, 403);
          const name = `${role}-${kind}-${t.mid}-${Date.now().toString(36)}`;
          out.push({ location: "local", mid: String(t.mid), trackName: name });
          added.push({ mid: String(t.mid), name, kind });
        } else if (t.location === "remote") {
          if (!o || o.left || t.sessionId !== o.sessionId) return j({ error: "not-in-room" }, 403);
          if (!Object.values(o.tracks).some((x) => x.name === t.trackName)) return j({ error: "no-such-track" }, 404);
          out.push({ location: "remote", sessionId: o.sessionId, trackName: t.trackName });
        } else return j({ error: "bad-track" }, 400);
      }
      const r = await this.sfu("POST", `/sessions/${me.sessionId}/tracks/new`, { ...(body.sessionDescription ? { sessionDescription: body.sessionDescription } : {}), tracks: out });
      if (r.status < 300 && !r.data.errorCode) {
        const failed = new Set((r.data.tracks || []).filter((x) => x.errorCode).map((x) => String(x.mid)));
        const evs = [];
        for (const a of added) if (!failed.has(a.mid)) { me.tracks[a.mid] = { name: a.name, kind: a.kind }; evs.push(this.ev(a.kind === "video" ? "video_on" : "audio_on", me)); }
        await this.save();
        await this.log(evs);
      }
      return j(r.data, r.status);
    }

    if (op === "renegotiate") {
      const r = await this.sfu("PUT", `/sessions/${me.sessionId}/renegotiate`, { sessionDescription: body.sessionDescription });
      return j(r.data, r.status);
    }

    // tracks/close: own mids only
    const mids = (Array.isArray(body.tracks) ? body.tracks : []).map((t) => String(t.mid));
    if (!mids.length) return j({ error: "no-tracks" }, 400);
    const r = await this.sfu("PUT", `/sessions/${me.sessionId}/tracks/close`, { tracks: mids.map((mid) => ({ mid })), force: body.force === true, ...(body.sessionDescription ? { sessionDescription: body.sessionDescription } : {}) });
    if (r.status < 300) {
      const evs = [];
      for (const mid of mids) {
        const t = me.tracks[mid];
        if (t) { delete me.tracks[mid]; if (t.kind === "video") evs.push(this.ev("video_off", me)); }
      }
      await this.save();
      await this.log(evs);
    }
    return j(r.data, r.status);
  }

  // every 30s while the call is open: drop a side that stopped polling, end an empty or too-long call
  async alarm() {
    await this.load();
    if (this.room.ended) return;
    const now = Date.now();
    const evs = [];
    for (const m of Object.values(this.room.members)) {
      if (!m.left && now - (m.lastSeen || 0) > DROP_MS) { m.left = true; evs.push(this.ev("drop", m)); }
    }
    const anyone = Object.values(this.room.members).some((m) => !m.left);
    if (!anyone || now - this.room.createdAt > MAX_CALL_MS) { this.room.ended = true; evs.push(this.ev("ended", null, anyone ? "time limit" : "")); }
    await this.save();
    await this.log(evs);
    if (!this.room.ended) await this.state.storage.setAlarm(now + 30000);
  }
}

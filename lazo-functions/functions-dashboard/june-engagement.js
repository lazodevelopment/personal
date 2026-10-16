// functions-dashboard/june-engagement.js
// Build ID: JC-LAZO-FNDASH-1016-ENGAGE-001
//
// JUNE FINDS ENGAGEMENT-SHOOT SPOTS. For a photographer's thread, June names
// 5-6 places near where the couple LIVES (the engagement questionnaire's first
// question; before answers come back, the wedding town/metro) and says why each
// one fits them: light and time of day, permits or fees, crowds, pets.
//
//   juneEngagementSpots   callable {inquiryId, more?}  (vendor owner or manager)
//                         -> { setId, spots, home }
//   engagementSpotsAuto   trigger: an engagement questionnaire is completed ->
//                         one set for that thread, once (set id auto_<qId>)
//
// How a set is made:
//   1. Claude (Sonnet 5.5) with web search (<= 4 searches) proposes 8 spots in
//      JSON, permits and fees looked up on the web, never guessed.
//   2. Each spot is checked with ONE Places Text Search (Pro fields only: id,
//      name, address, location, Maps link). Not found, or too far from the
//      couple, and it is dropped. The couple's home city is one more search.
//   3. Verified pins are cached per city in engagementSpots/{cityKey}/spots and
//      homes in engagementSpots/{cityKey}, so the next photographer there
//      reuses them free.
// Written to inquiries/{id}/engagementIdeas/{setId}; the vendor reads it, the
// couple never does (rules JC-LAZO-RULES-1016-ENGAGE). Sharing a spot is a
// normal thread message the Vendor app posts.
//
// Caps: 3 sets per thread per day, 20 per vendor per day.
// Cost: Claude + web search measured ~$0.16 a set on the first live run
// (35k in / 4.5k out / 4 searches), + $0.046 per uncached Places call (quote
// rule: $0.040 + 15%), so ~$0.45-0.55 a set cold and ~$0.20 once a city is
// cached. Each set records usage, placesCalls, cacheHits and estCost (from
// the real token counts).
//
// Wire-up in functions-dashboard/index.js:
//   Object.assign(exports, require('./june-engagement')(ANTHROPIC_API_KEY, PLACES_API_KEY));
// Needs the PLACES_API_KEY secret (the worker's Places key) in Secret Manager.

'use strict';

const { onCall, HttpsError } = require('firebase-functions/v2/https');
const { onDocumentUpdated } = require('firebase-functions/v2/firestore');
const { logger } = require('firebase-functions/v2');
const admin = require('firebase-admin');
const crypto = require('crypto');

const db = () => admin.firestore();
const str = (v) => (v == null ? '' : String(v));
const MODEL = 'claude-sonnet-5-5';
const CAP_THREAD = 3;
const CAP_VENDOR = 20;
const KEEP = 6;
const PLACES_EACH = 0.046;     // $0.040 + 15%
// Sonnet 5.5: $2 / $10 per million tokens; web search $10 per 1,000 searches.
const claudeCost = (u) => (u.input || 0) * 2e-6 + (u.output || 0) * 10e-6 + (u.searches || 0) * 0.01;
const PLACES_MASK = 'places.id,places.displayName,places.formattedAddress,places.location,places.googleMapsUri';

const keyOf = (s) => str(s).toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80);
const hash = (s) => crypto.createHash('sha1').update(str(s).toLowerCase().trim()).digest('hex').slice(0, 20);
const dayOf = (d = new Date()) => d.toISOString().slice(0, 10);

function miles(a, b) {
  const R = 3958.8, rad = (d) => d * Math.PI / 180;
  const dLat = rad(b.lat - a.lat), dLng = rad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
}

// The travel answer -> how far a spot may be (miles). Default: an hour out.
function radiusOf(answer) {
  const a = str(answer).toLowerCase();
  if (/15|stay local/.test(a)) return 15;
  if (/30/.test(a)) return 30;
  if (/road|anywhere|happy to/.test(a)) return 150;
  return 60;
}

// The questionnaire, as question/answer pairs. Lazo's own questions carry a
// spec key ('home', 'travel'...); a photographer's own questions go in as text.
function qaOf(qn) {
  if (!qn) return { pairs: [], byKey: {} };
  const qs = Array.isArray(qn.questions) ? qn.questions : [];
  const spec = Array.isArray(qn.spec) ? qn.spec : [];
  const ans = qn.answers && typeof qn.answers === 'object' ? qn.answers : {};
  const pairs = [], byKey = {};
  qs.forEach((q, i) => {
    const a = str(ans[String(i)]).trim();
    const k = str(spec[i] && spec[i].key);
    if (k && a) byKey[k] = a;
    if (a) pairs.push({ q: str(q).slice(0, 300), a: a.slice(0, 1200) });
  });
  return { pairs, byKey };
}

function parseJson(text) {
  const t = str(text).replace(/```(?:json)?/gi, '').trim();
  const a = t.indexOf('{'), b = t.lastIndexOf('}');
  if (a < 0 || b <= a) throw new Error('no json');
  return JSON.parse(t.slice(a, b + 1));
}

const SYSTEM = `You are June, the assistant inside Lazo, a wedding marketplace. You help a wedding photographer plan a couple's engagement session by suggesting real places to shoot near where the couple lives.
Use web search to confirm each place exists and to look up its photography rules: permit requirements, permit or entry fees, reservation rules, hours, pets policy. Spend at most four searches; search for the rules of the most likely candidates, not for general lists. Never invent a permit, fee or rule: if you could not confirm it, say "Check with <who runs the place>".
Pick places that fit THIS couple: their vibe, time of day, dates and season, places that mean something to them, pets or props, how far they will travel, and what they want to avoid. Mix it up: not eight parks, not eight downtown streets, unless their answers ask for that. Prefer places a photographer can actually work: open access or easy permits, good light at the time they want, somewhere to change outfits if they plan changes.
Write for the photographer: plain, specific, brief. No markdown inside the strings.
Return ONLY one JSON object, no prose before or after it:
{"spots":[{"name":"exact place name as Google Maps lists it","area":"neighborhood or town","why":"one or two sentences tied to their answers","bestTime":"when to shoot and why (light, golden hour timing for their dates)","permit":"what is needed, or 'No permit for small portrait sessions' if confirmed","fee":"cost, or 'Free'","crowds":"how busy and when it is quiet","pets":"allowed, leashed, or not allowed","source":"one URL you used for the rules, or ''"}],"note":"one line on season or weather for their dates, or ''"}
Give 8 spots, best first.`;

module.exports = function juneEngagementModule(ANTHROPIC_API_KEY, PLACES_API_KEY) {
  async function askClaude(user) {
    const messages = [{ role: 'user', content: user }];
    const tools = [{ type: 'web_search_20260209', name: 'web_search', max_uses: 4 }];
    let usage = { input: 0, output: 0, searches: 0 };
    for (let round = 0; round < 4; round++) {
      const r = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'x-api-key': ANTHROPIC_API_KEY.value(),
          'anthropic-version': '2023-06-01',
          'anthropic-beta': 'server-side-fallback-2026-07-01',
        },
        body: JSON.stringify({
          model: MODEL, max_tokens: 16000, fallbacks: 'default',
          output_config: { effort: 'medium' },
          system: SYSTEM, tools, messages,
        }),
      });
      if (!r.ok) {
        const txt = await r.text();
        logger.error('juneEngagementSpots anthropic', r.status, txt.slice(0, 300));
        throw new HttpsError('unavailable', r.status === 400 && /credit/i.test(txt) ? 'June is out of credit - Jesse, top up the Anthropic balance.' : 'June could not look that up right now - try again.');
      }
      const j = await r.json();
      const u = j.usage || {};
      usage.input += u.input_tokens || 0; usage.output += u.output_tokens || 0;
      usage.searches += (u.server_tool_use && u.server_tool_use.web_search_requests) || 0;
      const content = Array.isArray(j.content) ? j.content : [];
      if (j.stop_reason === 'pause_turn') { messages.push({ role: 'assistant', content }); continue; }
      if (j.stop_reason === 'refusal') throw new HttpsError('failed-precondition', 'June could not suggest places for this one.');
      const text = content.filter((c) => c.type === 'text').map((c) => c.text).join('\n');
      return { out: parseJson(text), usage };
    }
    throw new HttpsError('deadline-exceeded', 'June ran long - try again.');
  }

  async function placesSearch(textQuery, near) {
    const body = { textQuery, pageSize: 1 };
    if (near) body.locationBias = { circle: { center: { latitude: near.lat, longitude: near.lng }, radius: 50000 } };
    const r = await fetch('https://places.googleapis.com/v1/places:searchText', {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'X-Goog-Api-Key': PLACES_API_KEY.value(), 'X-Goog-FieldMask': PLACES_MASK },
      body: JSON.stringify(body),
    });
    if (!r.ok) { logger.warn('places', r.status, (await r.text()).slice(0, 200)); return null; }
    const j = await r.json();
    const p = j && Array.isArray(j.places) && j.places[0];
    if (!p || !p.location) return null;
    return {
      placeId: str(p.id), placeName: str(p.displayName && p.displayName.text), address: str(p.formattedAddress),
      lat: p.location.latitude, lng: p.location.longitude,
      mapsUrl: str(p.googleMapsUri) || `https://www.google.com/maps/place/?q=place_id:${str(p.id)}`,
    };
  }

  // Everything June knows about where and who, for one thread.
  async function contextFor(inquiryId) {
    const is = await db().collection('inquiries').doc(inquiryId).get();
    if (!is.exists) throw new HttpsError('not-found', 'Thread not found.');
    const inq = is.data();
    const coupleUid = str(inq.coupleUid);
    let couple = {};
    if (coupleUid && !coupleUid.startsWith('lead_')) {
      const cs = await db().collection('couples').doc(coupleUid).get();
      if (cs.exists) couple = cs.data() || {};
    }
    const qsnap = await db().collection('inquiries').doc(inquiryId).collection('questionnaires').where('type', '==', 'engagement').get();
    let qn = null;
    for (const d of qsnap.docs) {
      const x = d.data();
      const t = (x.completedAt || x.createdAt);
      const ms = t && t.toMillis ? t.toMillis() : 0;
      if (!qn || (x.status === 'completed' && qn.status !== 'completed') || (x.status === qn.status && ms > qn._ms)) qn = { ...x, id: d.id, _ms: ms };
    }
    const { pairs, byKey } = qaOf(qn);
    const metro = str(couple.metroId || (inq.structuredIntent && inq.structuredIntent.metroId));
    const town = str(couple.town);
    const wedding = [town, metro.replace(/-/g, ' ')].filter(Boolean).join(', ');
    const home = str(byKey.home) || wedding;
    return { inq, couple, qn, pairs, byKey, home, wedding, names: str(couple.names || (inq.contact && inq.contact.name) || inq.coupleName) };
  }

  async function homePoint(home) {
    const ref = db().collection('engagementSpots').doc(keyOf(home) || 'unknown');
    const s = await ref.get();
    if (s.exists && typeof s.get('lat') === 'number') return { pt: { lat: s.get('lat'), lng: s.get('lng'), label: str(s.get('label')) || home }, calls: 0 };
    const p = await placesSearch(home, null);
    if (!p) return { pt: null, calls: 1 };
    await ref.set({ label: home, address: p.address, lat: p.lat, lng: p.lng, updatedAt: admin.firestore.FieldValue.serverTimestamp() }, { merge: true });
    return { pt: { lat: p.lat, lng: p.lng, label: home }, calls: 1 };
  }

  async function build(inquiryId, { trigger, by, setId: fixedId, avoid = [] }) {
    const cx = await contextFor(inquiryId);
    if (!cx.home) throw new HttpsError('failed-precondition', 'June needs the couple’s city - send the engagement questionnaire first.');
    const radius = radiusOf(cx.byKey.travel);
    const hp = await homePoint(cx.home);
    let placesCalls = hp.calls, cacheHits = hp.calls ? 0 : 1;

    const lines = [
      `The couple${cx.names ? ' (' + cx.names + ')' : ''} lives in: ${cx.home}.`,
      cx.wedding && cx.wedding !== cx.home ? `Their wedding is in ${cx.wedding}.` : '',
      `Keep every spot within about ${radius} miles of where they live.`,
      `Today is ${new Date().toDateString()}.`,
      cx.pairs.length ? 'Their engagement-session answers:\n' + cx.pairs.map((p) => `- ${p.q}\n  ${p.a}`).join('\n') : 'They have not answered the questionnaire yet, so suggest a varied set for the season.',
      avoid.length ? 'Already suggested to this photographer, do not repeat: ' + avoid.slice(0, 30).join('; ') + '.' : '',
    ].filter(Boolean).join('\n\n');
    const { out, usage } = await askClaude(lines);

    const raw = Array.isArray(out.spots) ? out.spots.slice(0, 10) : [];
    const cityKey = keyOf(cx.home) || 'unknown';
    const kept = [];
    const avoidSet = new Set(avoid.map((a) => a.toLowerCase()));
    for (const s of raw) {
      if (kept.length >= KEEP) break;
      const name = str(s.name).trim().slice(0, 120);
      if (!name || avoidSet.has(name.toLowerCase())) continue;
      const area = str(s.area).trim().slice(0, 80);
      const cref = db().collection('engagementSpots').doc(cityKey).collection('spots').doc(hash(name + '|' + area));
      const cs = await cref.get();
      let pin = null;
      if (cs.exists) { pin = cs.data(); cacheHits++; }
      else {
        pin = await placesSearch([name, area || cx.home].join(', '), hp.pt);
        placesCalls++;
        if (pin) await cref.set({ ...pin, name, area, updatedAt: admin.firestore.FieldValue.serverTimestamp() });
      }
      if (!pin || !pin.placeId) continue;
      const mi = hp.pt ? miles(hp.pt, pin) : null;
      if (mi != null && mi > radius * 1.5 + 10) continue;
      if (kept.some((k) => k.placeId === pin.placeId)) continue;
      kept.push({
        name, area, placeId: pin.placeId, address: str(pin.address), lat: pin.lat, lng: pin.lng, mapsUrl: str(pin.mapsUrl),
        milesFromHome: mi == null ? null : Math.round(mi * 10) / 10,
        why: str(s.why).slice(0, 400), bestTime: str(s.bestTime).slice(0, 300), permit: str(s.permit).slice(0, 300),
        fee: str(s.fee).slice(0, 120), crowds: str(s.crowds).slice(0, 200), pets: str(s.pets).slice(0, 120),
        source: /^https?:\/\//.test(str(s.source)) ? str(s.source).slice(0, 400) : '', verified: true,
      });
    }
    if (!kept.length) throw new HttpsError('not-found', 'June couldn’t confirm any spots near ' + cx.home + ' - check the couple’s city and try again.');

    const estCost = Math.round((claudeCost(usage) + placesCalls * PLACES_EACH) * 100) / 100;
    const ref = fixedId
      ? db().collection('inquiries').doc(inquiryId).collection('engagementIdeas').doc(fixedId)
      : db().collection('inquiries').doc(inquiryId).collection('engagementIdeas').doc();
    const doc = {
      spots: kept, note: str(out.note).slice(0, 300),
      home: { label: cx.home, lat: hp.pt ? hp.pt.lat : null, lng: hp.pt ? hp.pt.lng : null }, radius,
      questionnaireId: cx.qn ? cx.qn.id : '', answered: cx.pairs.length > 0,
      trigger, by: by || '', day: dayOf(), hidden: [], shared: [],
      model: MODEL, usage, placesCalls, cacheHits, estCost,
      createdAt: admin.firestore.FieldValue.serverTimestamp(),
    };
    await ref.set(doc);
    logger.info('engagement spots', { inquiryId, trigger, kept: kept.length, placesCalls, cacheHits, estCost });
    return { setId: ref.id, spots: kept, home: doc.home, note: doc.note };
  }

  // Today's sets on this thread, and the names already shown (for "More like this").
  async function threadToday(inquiryId) {
    const s = await db().collection('inquiries').doc(inquiryId).collection('engagementIdeas').get();
    let today = 0; const names = [];
    for (const d of s.docs) {
      const x = d.data();
      if (x.day === dayOf()) today++;
      for (const sp of (x.spots || [])) if (sp && sp.name) names.push(sp.name);
    }
    return { today, names };
  }

  async function chargeVendor(vendorId) {
    const ref = db().collection('vendors').doc(vendorId);
    return db().runTransaction(async (tx) => {
      const v = (await tx.get(ref)).data() || {};
      const used = v.engSpotsDay === dayOf() ? Number(v.engSpotsCount || 0) : 0;
      if (used >= CAP_VENDOR) return false;
      tx.set(ref, { engSpotsDay: dayOf(), engSpotsCount: used + 1 }, { merge: true });
      return true;
    });
  }

  const juneEngagementSpots = onCall({ memory: '512MiB', timeoutSeconds: 300, secrets: [ANTHROPIC_API_KEY, PLACES_API_KEY] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const inquiryId = str(request.data && request.data.inquiryId);
    if (!inquiryId) throw new HttpsError('invalid-argument', 'inquiryId required');
    const is = await db().collection('inquiries').doc(inquiryId).get();
    if (!is.exists) throw new HttpsError('not-found', 'Thread not found.');
    const vendorId = str(is.get('vendorId'));
    const [vs, us] = await Promise.all([db().collection('vendors').doc(vendorId).get(), db().collection('users').doc(uid).get()]);
    const isOwner = vs.exists && str(vs.get('claimedBy')) === uid;
    const isMgr = us.exists && str(us.get('vendorId')) === vendorId && str(us.get('vendorRole')) === 'manager';
    if (!isOwner && !isMgr) throw new HttpsError('permission-denied', 'Not your thread.');
    const t = await threadToday(inquiryId);
    if (t.today >= CAP_THREAD) throw new HttpsError('resource-exhausted', 'June has found spots for this couple three times today - try again tomorrow.');
    if (!(await chargeVendor(vendorId))) throw new HttpsError('resource-exhausted', 'June has hit today’s limit for location ideas - she’ll be back tomorrow.');
    return build(inquiryId, { trigger: 'vendor', by: uid, avoid: request.data && request.data.more ? t.names : [] });
  });

  // Once per engagement questionnaire, when the couple sends their answers.
  const engagementSpotsAuto = onDocumentUpdated({ document: 'inquiries/{inquiryId}/questionnaires/{qId}', memory: '512MiB', timeoutSeconds: 300, secrets: [ANTHROPIC_API_KEY, PLACES_API_KEY] }, async (event) => {
    const before = event.data && event.data.before && event.data.before.data();
    const after = event.data && event.data.after && event.data.after.data();
    if (!after || after.type !== 'engagement' || after.status !== 'completed' || (before && before.status === 'completed')) return;
    const { inquiryId, qId } = event.params;
    const setId = 'auto_' + qId;
    const ref = db().collection('inquiries').doc(inquiryId).collection('engagementIdeas').doc(setId);
    if ((await ref.get()).exists) return;
    const is = await db().collection('inquiries').doc(inquiryId).get();
    const vendorId = str(is.exists && is.get('vendorId'));
    if (!vendorId || !(await chargeVendor(vendorId))) return;
    try { await build(inquiryId, { trigger: 'auto', setId }); }
    catch (e) { logger.warn('engagementSpotsAuto', inquiryId, e.message); }
  });

  return { juneEngagementSpots, engagementSpotsAuto };
};

module.exports._test = { qaOf, radiusOf, parseJson, keyOf };

// END OF FILE - JC-LAZO-FNDASH-1016-ENGAGE-001

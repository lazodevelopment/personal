// functions-dashboard/index.js
// Build ID: JC-LAZO-FNDASH-1007-024 (024: couple-notify.js + email-frame.js - couple milestone emails; base 023) (023: welcome.js - welcomeCouple/welcomeVendor emails at signup; base 022) (022: june-token.js - juneToken callable for the June hub hand-off; base 021) (021: team.js - teamRecommend/onReferralBooked; base 020) (020: hello.js - helloMatches/helloSend; base 019) (019: showcase.js - galleryShowcase; base 018) (018: demo.js - practice couple; base 017) (017: june-vendor.js - juneVendor with the MCP tools; 016: mcp.js; base 015) (015: scheduler.js - consultSlots/Book/Cancel + consultReminderSweep; 014: brand.js; base 013) (013: pipeline.js - onTaskWritten, taskReminderSweep; base 012) (012: leads.js - lead form ingest, onLeadMessage, telnyxInbound; base 011) (011: payments.js - plans, Whop rail, /f/ page; base 008) (008: the sweep reads the import@meetlazo.com mailbox's own Inbox with its own token - account looked up by email, no alias, no forwarding, no folder rule; 007: importMailSweep - every 2 minutes, reads the Import folder of the Zoho mailbox behind import@meetlazo.com, matches the sender to a Lazo couple, has June read the vendor confirmation and any attached PDF, files the vendor on their team with amounts and the contract, and replies with what was added; 006: juneImport callable - reads a public wedding-website URL or pasted text, a budget CSV/text/screenshot, or a list of booked vendors, and returns structured data for the couple app's "Switching from another planning site" screen; 005: vendors.bookedCount - distinct couples who booked, all time, for the "N Lazo couples have booked" proof on the public page; 004: gcf_gen1 CPU + concurrency 1 for the Cloud Run quota; 003: metroStats.priceFrom - real starting-price ranges per metro+category for the couple budget lines; redeemCoupleInvite for partners; 002: rank matches build.py exactly - every category a vendor holds is a bucket, missing scores sit at the 65 prior, names compare lowercase; base 001)
// Separate Firebase codebase ("dashboard") so nothing in functions/index.js
// (the Whop build) is touched. Deploy: firebase deploy --only functions:dashboard
//
// pulse              POST beacon from vendor pages -> vendorPulse/{vendorId}/days/{day}
// nightlyVendorStats 03:15 America/Phoenix -> vendors.{views,badges,rank}, metroStats/{metro__cat}
// vendorCalendar     GET ?v=&t=  -> ICS feed of booked weddings + blocked dates
// morningBrief       hourly; sends the 7am email to vendors with dailyBrief.enabled
// redeemVendorInvite callable {code} -> users/{uid}.vendorId (team access)

'use strict';

const { onRequest, onCall, HttpsError } = require('firebase-functions/v2/https');
const { onSchedule } = require('firebase-functions/v2/scheduler');
const { setGlobalOptions } = require('firebase-functions/v2');
const { defineSecret } = require('firebase-functions/params');
const admin = require('firebase-admin');

admin.initializeApp();
const db = admin.firestore();
const { FieldValue, Timestamp } = admin.firestore;

// gen-1 CPU share per instance, one request at a time - fits the region's
// 20-vCPU Cloud Run quota alongside the default codebase (see JC-LAZO-CPU-0907-001).
setGlobalOptions({ region: 'us-central1', maxInstances: 10, cpu: 'gcf_gen1', concurrency: 1 });

const RESEND_API_KEY = defineSecret('RESEND_API_KEY');
const ANTHROPIC_API_KEY = defineSecret('ANTHROPIC_API_KEY');
const ZOHO_CLIENT_ID = defineSecret('ZOHO_CLIENT_ID');
const ZOHO_CLIENT_SECRET = defineSecret('ZOHO_CLIENT_SECRET');
const ZOHO_REFRESH_TOKEN = defineSecret('ZOHO_REFRESH_TOKEN');
const FROM = 'Lazo <hello@meetlazo.com>';
const APP = 'https://app.meetlazo.com/dashboard';

// ---------------------------------------------------------------- labels --
const METROS = {
  'phoenix': 'Phoenix', 'denver': 'Denver', 'dallas-fort-worth': 'Dallas-Fort Worth',
  'houston': 'Houston', 'austin': 'Austin', 'san-antonio': 'San Antonio',
  'las-vegas': 'Las Vegas', 'atlanta': 'Atlanta', 'nashville': 'Nashville',
  'chicago': 'Chicago', 'los-angeles': 'Los Angeles', 'san-diego': 'San Diego',
  'miami': 'Miami', 'orlando': 'Orlando', 'tampa': 'Tampa', 'charlotte': 'Charlotte',
  'raleigh-durham': 'Raleigh-Durham', 'seattle': 'Seattle', 'salt-lake-city': 'Salt Lake City',
  'new-york-city': 'New York City', 'boston': 'Boston', 'philadelphia': 'Philadelphia',
  'washington-dc': 'Washington DC', 'san-francisco-bay': 'San Francisco Bay',
  'portland': 'Portland', 'minneapolis': 'Minneapolis', 'st-louis': 'St. Louis',
  'kansas-city': 'Kansas City', 'columbus': 'Columbus', 'new-orleans': 'New Orleans',
  'indianapolis': 'Indianapolis', 'sacramento': 'Sacramento', 'jacksonville': 'Jacksonville',
  'charleston': 'Charleston', 'savannah': 'Savannah', 'detroit': 'Detroit',
  'pittsburgh': 'Pittsburgh', 'cincinnati': 'Cincinnati', 'cleveland': 'Cleveland',
  'milwaukee': 'Milwaukee', 'richmond': 'Richmond', 'virginia-beach': 'Virginia Beach',
  'louisville': 'Louisville', 'memphis': 'Memphis', 'tucson': 'Tucson',
};
const CATS = {
  'wedding-photographers': 'photographers', 'wedding-videographers': 'videographers',
  'wedding-venues': 'venues', 'wedding-planners': 'planners', 'wedding-djs': 'DJs',
  'wedding-florists': 'florists', 'wedding-caterers': 'caterers',
  'wedding-cakes': 'cake and dessert makers', 'hair-and-makeup': 'hair and makeup artists',
  'wedding-officiants': 'officiants', 'wedding-transportation': 'transportation companies',
  'wedding-rentals': 'rental companies', 'wedding-bands': 'live bands',
  'wedding-invitations': 'invitation designers', 'day-of-coordination': 'day-of coordinators',
};
const TZ = {
  'phoenix': 'America/Phoenix', 'tucson': 'America/Phoenix', 'denver': 'America/Denver',
  'salt-lake-city': 'America/Denver', 'las-vegas': 'America/Los_Angeles',
  'los-angeles': 'America/Los_Angeles', 'san-diego': 'America/Los_Angeles',
  'san-francisco-bay': 'America/Los_Angeles', 'sacramento': 'America/Los_Angeles',
  'seattle': 'America/Los_Angeles', 'portland': 'America/Los_Angeles',
  'dallas-fort-worth': 'America/Chicago', 'houston': 'America/Chicago', 'austin': 'America/Chicago',
  'san-antonio': 'America/Chicago', 'chicago': 'America/Chicago', 'minneapolis': 'America/Chicago',
  'st-louis': 'America/Chicago', 'kansas-city': 'America/Chicago', 'new-orleans': 'America/Chicago',
  'milwaukee': 'America/Chicago', 'memphis': 'America/Chicago', 'nashville': 'America/Chicago',
  'atlanta': 'America/New_York', 'miami': 'America/New_York', 'orlando': 'America/New_York',
  'tampa': 'America/New_York', 'charlotte': 'America/New_York', 'raleigh-durham': 'America/New_York',
  'new-york-city': 'America/New_York', 'boston': 'America/New_York', 'philadelphia': 'America/New_York',
  'washington-dc': 'America/New_York', 'columbus': 'America/New_York', 'indianapolis': 'America/New_York',
  'jacksonville': 'America/New_York', 'charleston': 'America/New_York', 'savannah': 'America/New_York',
  'detroit': 'America/New_York', 'pittsburgh': 'America/New_York', 'cincinnati': 'America/New_York',
  'cleveland': 'America/New_York', 'richmond': 'America/New_York', 'virginia-beach': 'America/New_York',
  'louisville': 'America/New_York',
};

// ---------------------------------------------------------------- utils ---
const dayKey = (d) => d.toISOString().slice(0, 10);
const daysAgo = (n) => new Date(Date.now() - n * 86400000);
const toDate = (v) => (v && typeof v.toDate === 'function') ? v.toDate() : (v instanceof Date ? v : null);
const str = (v) => (v == null ? '' : String(v));

function weddingDate(inq) {
  const raw = str(inq && inq.structuredIntent && inq.structuredIntent.weddingDate).trim();
  if (!raw) return null;
  const d = new Date(raw.length === 10 ? raw + 'T12:00:00' : raw);
  return isNaN(d.getTime()) ? null : d;
}

function localParts(tz, date) {
  const f = new Intl.DateTimeFormat('en-US', {
    timeZone: tz, hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit',
  });
  const p = {};
  for (const part of f.formatToParts(date || new Date())) p[part.type] = part.value;
  return { day: `${p.year}-${p.month}-${p.day}`, hour: parseInt(p.hour, 10) % 24 };
}

function median(nums) {
  if (!nums.length) return null;
  const s = nums.slice().sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : Math.round((s[m - 1] + s[m]) / 2);
}

function money(n) {
  return '$' + Math.round(Number(n) || 0).toLocaleString('en-US');
}

function fmtDate(d) {
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function isUnread(m) {
  if (str(m.lastMessageRole) !== 'couple') {
    const st = str(m.status) || 'new';
    return (st === 'new' || st === '') && !m.seenByVendorAt;
  }
  const last = toDate(m.lastMessageAt);
  const read = toDate(m.vendorLastReadAt);
  if (!last) return false;
  if (!read) return true;
  return last > read;
}

async function sendEmail(to, subject, html, text) {
  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: FROM, to: [to], subject, html, text }),
  });
  if (!r.ok) throw new Error(`resend ${r.status}: ${await r.text()}`);
}

// ---------------------------------------------------------------- pulse ---
// The vendor page template sends:
//   navigator.sendBeacon('https://us-central1-lazo-513ec.cloudfunctions.net/pulse',
//     JSON.stringify({ v: '<vendor doc id>', r: document.referrer, s: utm_source }))
function classify(ref, s) {
  if (s) return s.toLowerCase().replace(/[^a-z0-9_-]/g, '').slice(0, 24) || 'other';
  if (!ref) return 'direct';
  let host = '';
  try { host = new URL(ref).hostname.toLowerCase(); } catch (e) { return 'other'; }
  if (/(^|\.)meetlazo\.com$/.test(host)) return 'lazo';
  if (/google\.|bing\.com|duckduckgo\.com|yahoo\.|search\.brave/.test(host)) return 'search';
  if (/instagram|facebook|fb\.com|pinterest|tiktok|threads\.net/.test(host)) return 'social';
  return 'other';
}

exports.pulse = onRequest({ cors: true, invoker: 'public', memory: '128MiB' }, async (req, res) => {
  if (req.method === 'OPTIONS') return res.status(204).send('');
  if (req.method !== 'POST') return res.status(405).send('');
  const ua = str(req.get('user-agent')).toLowerCase();
  if (/bot|crawl|spider|slurp|facebookexternalhit|preview|lighthouse|headless|python|curl/.test(ua)) {
    return res.status(204).send('');
  }
  let body = req.body;
  if (Buffer.isBuffer(body)) body = body.toString('utf8');
  if (typeof body === 'string') { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  body = body || {};
  const v = str(body.v).slice(0, 160);
  if (!/^[A-Za-z0-9_-]+$/.test(v)) return res.status(204).send('');
  const src = classify(str(body.r), str(body.s));
  try {
    await db.collection('vendorPulse').doc(v).collection('days').doc(dayKey(new Date())).set({
      day: dayKey(new Date()),
      views: FieldValue.increment(1),
      src: { [src]: FieldValue.increment(1) },
      updatedAt: FieldValue.serverTimestamp(),
    }, { merge: true });
  } catch (e) {
    console.error('pulse', e.message);
  }
  return res.status(204).send('');
});

// ------------------------------------------------------- nightly stats ----
// Rank is computed for every listed vendor exactly the way build.py orders a
// category page - cvs.sort(key=(-score, -reviewCount, name.lower())) with
// unscored vendors at the 65 prior - and written only to claimed vendors, for
// their primary category. Nobody else can see it, and the write count stays small.
const PRIOR_SCORE = 65;
exports.nightlyVendorStats = onSchedule({
  schedule: '15 3 * * *', timeZone: 'America/Phoenix', memory: '1GiB', timeoutSeconds: 540,
}, async () => {
  const vSnap = await db.collection('vendors')
    .select('name', 'score', 'reviewCount', 'metroId', 'categories', 'claimStatus',
      'claimedBy', 'delisted', 'verified', 'profileUpdatedAt', 'announcement', 'startingPrice')
    .get();
  // 003: what things really cost here - the first number in each vendor's
  // starting price, per metro+category. Couples see p25-p75 next to each
  // budget line. Only from listed vendors that state a price.
  const priceByBucket = new Map();
  const buckets = new Map();
  const claimed = [];
  for (const d of vSnap.docs) {
    const m = d.data();
    if (m.delisted === true) continue;
    if (!str(m.name)) continue;
    const metro = str(m.metroId);
    const cats = Array.isArray(m.categories) ? m.categories.map(str).filter(Boolean) : [];
    if (!metro || !cats.length) continue;
    const entry = { id: d.id, score: Number(m.score) || PRIOR_SCORE, reviews: Number(m.reviewCount) || 0, name: str(m.name).toLowerCase() };
    const pm = /\d[\d,]*(?:\.\d+)?/.exec(str(m.startingPrice));
    const price = pm ? Number(pm[0].replace(/,/g, '')) : 0;
    for (const cat of cats) {
      const key = `${metro}__${cat}`;
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(entry);
      if (price > 0) {
        if (!priceByBucket.has(key)) priceByBucket.set(key, []);
        priceByBucket.get(key).push(price);
      }
    }
    if (m.claimStatus === 'claimed') claimed.push({ id: d.id, key: `${metro}__${cats[0]}`, metro, cat: cats[0], m });
  }
  const rankOf = new Map(); // `${key}|${id}` -> {pos, of}
  for (const [key, list] of buckets) {
    list.sort((a, b) => (b.score - a.score) || (b.reviews - a.reviews) || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
    list.forEach((v, i) => rankOf.set(`${key}|${v.id}`, { pos: i + 1, of: list.length, key }));
  }

  // 005: booked couples, all time - the one number on the public page that
  // says "people like you chose them". Distinct couples, status booked.
  const bookedByVendor = new Map();
  {
    const bSnap = await db.collection('inquiries').where('status', '==', 'booked').select('vendorId', 'coupleUid').get();
    for (const d of bSnap.docs) {
      const m = d.data();
      const v = str(m.vendorId), c = str(m.coupleUid);
      if (!v || !c) continue;
      if (!bookedByVendor.has(v)) bookedByVendor.set(v, new Set());
      bookedByVendor.get(v).add(c);
    }
  }

  // Inquiries in the last 90 days, grouped by vendor.
  const since = Timestamp.fromDate(daysAgo(90));
  const iSnap = await db.collection('inquiries').where('createdAt', '>=', since).get();
  const byVendor = new Map();
  for (const d of iSnap.docs) {
    const m = d.data();
    const v = str(m.vendorId);
    if (!v) continue;
    if (!byVendor.has(v)) byVendor.set(v, []);
    byVendor.get(v).push(m);
  }
  const now = Date.now();
  const d7 = now - 7 * 86400000;
  const d15 = now - 15 * 86400000;
  const claimedKeys = new Set();
  let writes = 0;
  let batch = db.batch();
  const flush = async () => { if (writes) { await batch.commit(); batch = db.batch(); writes = 0; } };

  for (const c of claimed) {
    claimedKeys.add(c.key);
    const inqs = byVendor.get(c.id) || [];
    // reply speed over 90 days
    let answered = 0, within24 = 0;
    for (const q of inqs) {
      const ca = toDate(q.createdAt), ra = toDate(q.respondedAt);
      if (!ca) continue;
      if (ra) { answered++; if (ra - ca <= 24 * 3600000) within24++; }
    }
    const badges = [];
    if (c.m.verified === true) badges.push('verified');
    if (c.m.announcement && str(c.m.announcement.title).trim()) badges.push('offer');
    if (inqs.length >= 3 && within24 / inqs.length >= 0.8) badges.push('quick_responder');
    const pu = toDate(c.m.profileUpdatedAt);
    if (pu && pu.getTime() >= d15) badges.push('recently_updated');
    const last7 = inqs.filter((q) => { const t = toDate(q.createdAt); return t && t.getTime() >= d7; }).length;
    if (last7 >= 5) badges.push('popular');

    // views from the beacon
    const pSnap = await db.collection('vendorPulse').doc(c.id).collection('days')
      .where('day', '>=', dayKey(daysAgo(14))).get();
    let v7 = 0, vPrev = 0;
    const src = {};
    const cut = dayKey(daysAgo(7));
    for (const pd of pSnap.docs) {
      const p = pd.data();
      const n = Number(p.views) || 0;
      if (str(p.day) >= cut) {
        v7 += n;
        for (const [k, val] of Object.entries(p.src || {})) src[k] = (src[k] || 0) + (Number(val) || 0);
      } else {
        vPrev += n;
      }
    }
    const r = rankOf.get(`${c.key}|${c.id}`);
    const update = {
      badges,
      bookedCount: (bookedByVendor.get(c.id) || new Set()).size,
      statsUpdatedAt: FieldValue.serverTimestamp(),
    };
    if (pSnap.size > 0 || v7 > 0) {
      update.views = { d7: v7, d7Prev: vPrev, src, updatedAt: FieldValue.serverTimestamp() };
    }
    if (r) {
      update.rank = {
        pos: r.pos, of: r.of,
        label: `${METROS[c.metro] || c.metro} ${CATS[c.cat] || c.cat}`,
        updatedAt: FieldValue.serverTimestamp(),
      };
    }
    batch.set(db.collection('vendors').doc(c.id), update, { merge: true });
    if (++writes >= 400) await flush();
  }

  // Benchmarks per metro+category, only where a claimed vendor will read them.
  const vendorBucket = new Map();
  for (const c of claimed) vendorBucket.set(c.id, c.key);
  for (const [key, list] of buckets) for (const v of list) if (!vendorBucket.has(v.id)) vendorBucket.set(v.id, key);
  const replyByBucket = new Map();
  const inq30ByBucket = new Map();
  const d30 = now - 30 * 86400000;
  for (const [v, inqs] of byVendor) {
    const key = vendorBucket.get(v);
    if (!key || !claimedKeys.has(key)) continue;
    if (!replyByBucket.has(key)) { replyByBucket.set(key, []); inq30ByBucket.set(key, new Map()); }
    for (const q of inqs) {
      const ca = toDate(q.createdAt), ra = toDate(q.respondedAt);
      if (ca && ra) replyByBucket.get(key).push(Math.max(0, Math.round((ra - ca) / 60000)));
      if (ca && ca.getTime() >= d30) {
        const per = inq30ByBucket.get(key);
        per.set(v, (per.get(v) || 0) + 1);
      }
    }
  }
  // 003: price ranges are written for every bucket that has at least five
  // priced vendors - couples in every metro read them, not just claimed ones.
  const statKeys = new Set(claimedKeys);
  for (const [key, prices] of priceByBucket) if (prices.length >= 5) statKeys.add(key);
  for (const key of statKeys) {
    const list = buckets.get(key) || [];
    const replies = replyByBucket.get(key) || [];
    const per = inq30ByBucket.get(key) || new Map();
    const prices = (priceByBucket.get(key) || []).slice().sort((a, b) => a - b);
    const q = (p) => prices.length ? prices[Math.min(prices.length - 1, Math.floor(p * (prices.length - 1)))] : null;
    const doc = {
      metroId: key.split('__')[0],
      categoryId: key.split('__')[1],
      vendors: list.length,
      updatedAt: FieldValue.serverTimestamp(),
    };
    if (claimedKeys.has(key)) {
      doc.medianReplyMin = median(replies);
      doc.repliesSampled = replies.length;
      doc.medianInquiries30d = median([...per.values()]) || 0;
    }
    if (prices.length >= 5) {
      doc.priceFrom = { p25: q(0.25), p50: q(0.5), p75: q(0.75), sampled: prices.length };
    }
    batch.set(db.collection('metroStats').doc(key), doc, { merge: true });
    if (++writes >= 400) await flush();
  }
  await flush();
  console.log(`nightlyVendorStats: ${claimed.length} claimed vendors, ${claimedKeys.size} buckets, ${iSnap.size} inquiries`);
});

// ------------------------------------------------------- calendar feed ----
function icsEscape(s) {
  return str(s).replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');
}
function icsFold(line) {
  const out = [];
  let s = line;
  while (Buffer.byteLength(s, 'utf8') > 72) {
    let cut = 72;
    while (Buffer.byteLength(s.slice(0, cut), 'utf8') > 72) cut--;
    out.push(s.slice(0, cut));
    s = ' ' + s.slice(cut);
  }
  out.push(s);
  return out.join('\r\n');
}
function ymd(d) {
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
}
function nextDay(d) { const n = new Date(d); n.setDate(n.getDate() + 1); return n; }

exports.vendorCalendar = onRequest({ cors: true, invoker: 'public', memory: '256MiB' }, async (req, res) => {
  const v = str(req.query.v).slice(0, 160);
  const t = str(req.query.t).slice(0, 80);
  if (!/^[A-Za-z0-9_-]+$/.test(v) || !t) return res.status(400).send('missing v/t');
  const vDoc = await db.collection('vendors').doc(v).get();
  if (!vDoc.exists) return res.status(404).send('no such vendor');
  const vd = vDoc.data();
  const want = str(vd.calendarToken);
  if (!want || want.length !== t.length || want !== t) return res.status(403).send('bad token');

  const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z');
  const lines = [
    'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Lazo//Vendor Calendar//EN', 'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH', `X-WR-CALNAME:${icsEscape(str(vd.name) || 'Lazo')} - Lazo`, 'X-PUBLISHED-TTL:PT1H',
  ];
  const iSnap = await db.collection('inquiries').where('vendorId', '==', v).get();
  for (const d of iSnap.docs) {
    const m = d.data();
    const booked = str(m.status) === 'booked' || str(m.contractStatus) === 'signed';
    if (!booked) continue;
    const wd = weddingDate(m);
    if (!wd) continue;
    const intent = m.structuredIntent || {};
    const desc = [
      str(intent.venue || intent.venueName) && `Venue: ${str(intent.venue || intent.venueName)}`,
      str(intent.guestCount) && `Guests: ${str(intent.guestCount)}`,
      `Open in Lazo: ${APP}?thread=${d.id}`,
    ].filter(Boolean).join('\n');
    lines.push('BEGIN:VEVENT',
      `UID:lazo-${d.id}@meetlazo.com`,
      `DTSTAMP:${stamp}`,
      `DTSTART;VALUE=DATE:${ymd(wd)}`,
      `DTEND;VALUE=DATE:${ymd(nextDay(wd))}`,
      `SUMMARY:${icsEscape('Wedding - ' + (str(m.coupleName) || 'Booked couple'))}`,
      `DESCRIPTION:${icsEscape(desc)}`,
      `URL:${APP}?thread=${d.id}`,
      'END:VEVENT');
  }
  for (const iso of Array.isArray(vd.unavailableDates) ? vd.unavailableDates : []) {
    const d = new Date(str(iso) + 'T12:00:00');
    if (isNaN(d.getTime())) continue;
    lines.push('BEGIN:VEVENT',
      `UID:lazo-block-${str(iso)}-${v}@meetlazo.com`,
      `DTSTAMP:${stamp}`,
      `DTSTART;VALUE=DATE:${ymd(d)}`,
      `DTEND;VALUE=DATE:${ymd(nextDay(d))}`,
      'SUMMARY:Blocked on Lazo',
      'TRANSP:TRANSPARENT',
      'END:VEVENT');
  }
  lines.push('END:VCALENDAR');
  res.set('Content-Type', 'text/calendar; charset=utf-8');
  res.set('Cache-Control', 'public, max-age=300');
  res.set('Content-Disposition', 'inline; filename="lazo.ics"');
  return res.status(200).send(lines.map(icsFold).join('\r\n') + '\r\n');
});

// -------------------------------------------------------- morning brief ---
exports.morningBrief = onSchedule({
  schedule: '5 * * * *', timeZone: 'UTC', memory: '512MiB', timeoutSeconds: 300, secrets: [RESEND_API_KEY],
}, async () => {
  const vSnap = await db.collection('vendors').where('dailyBrief.enabled', '==', true).get();
  let sent = 0;
  for (const vDoc of vSnap.docs) {
    const vd = vDoc.data();
    const cfg = vd.dailyBrief || {};
    const tz = TZ[str(vd.metroId)] || 'America/Phoenix';
    const lp = localParts(tz);
    const hour = Number.isInteger(cfg.hour) ? cfg.hour : 7;
    if (lp.hour !== hour || str(cfg.lastSentDay) === lp.day) continue;

    let to = str(vd.publicEmail).trim();
    if (str(vd.claimedBy)) {
      const u = await db.collection('users').doc(str(vd.claimedBy)).get();
      if (u.exists && str(u.data().email)) to = str(u.data().email);
    }
    if (!to) continue;

    const iSnap = await db.collection('inquiries').where('vendorId', '==', vDoc.id).get();
    const waiting = [];
    const weddings = [];
    const now = new Date();
    const week = new Date(now.getTime() + 7 * 86400000);
    for (const d of iSnap.docs) {
      const m = d.data();
      if (str(m.status) === 'flagged') continue;
      if (isUnread(m)) waiting.push({ id: d.id, name: str(m.coupleName) || 'A verified couple', at: toDate(m.lastMessageAt) || toDate(m.createdAt) });
      const booked = str(m.status) === 'booked' || str(m.contractStatus) === 'signed';
      const wd = weddingDate(m);
      if (booked && wd && wd >= new Date(now.getFullYear(), now.getMonth(), now.getDate()) && wd <= week) {
        weddings.push({ id: d.id, name: str(m.coupleName) || 'A couple', wd });
      }
    }
    const due = [];
    const invSnap = await db.collectionGroup('invoices').where('vendorId', '==', vDoc.id).get();
    for (const d of invSnap.docs) {
      const m = d.data();
      const st = str(m.status);
      if (st === 'paid' || st === 'void') continue;
      const dd = toDate(m.dueDate);
      if (dd && dd <= week) due.push({ title: str(m.title) || 'Invoice', total: Number(m.total) || 0, dd, late: dd < now });
    }
    if (!waiting.length && !weddings.length && !due.length) {
      await vDoc.ref.set({ dailyBrief: { lastSentDay: lp.day } }, { merge: true });
      continue;
    }
    waiting.sort((a, b) => (a.at || 0) - (b.at || 0));
    weddings.sort((a, b) => a.wd - b.wd);
    due.sort((a, b) => a.dd - b.dd);

    const l1 = waiting.length
      ? `${waiting.length} waiting on you - ${waiting.slice(0, 3).map((w) => w.name).join(', ')}.`
      : 'Inbox is clear.';
    const l2 = due.length
      ? `${due.length} invoice${due.length === 1 ? '' : 's'} due this week - ${due.slice(0, 3).map((x) => `${x.title} ${money(x.total)}${x.late ? ' (late)' : ''}`).join(', ')}.`
      : 'Nothing due this week.';
    const l3 = weddings.length
      ? `Weddings this week - ${weddings.slice(0, 3).map((w) => `${w.name} on ${fmtDate(w.wd)}`).join(', ')}.`
      : 'No weddings this week.';
    const text = `${l1}\n${l2}\n${l3}\n\nOpen your dashboard: ${APP}`;
    const html = `<div style="font-family:Inter,Helvetica,Arial,sans-serif;color:#241E2B;font-size:15px;line-height:1.6;max-width:560px">
<p style="font-size:12px;letter-spacing:.12em;color:#8A6A2F;margin:0 0 12px">GOOD MORNING FROM LAZO</p>
<p style="margin:0 0 10px">${waiting.length ? `<b>${waiting.length} waiting on you</b> - ${waiting.slice(0, 3).map((w) => `<a href="${APP}?thread=${w.id}" style="color:#52284F">${w.name}</a>`).join(', ')}.` : 'Inbox is clear.'}</p>
<p style="margin:0 0 10px">${l2}</p>
<p style="margin:0 0 18px">${weddings.length ? `Weddings this week - ${weddings.slice(0, 3).map((w) => `<a href="${APP}?thread=${w.id}" style="color:#52284F">${w.name}</a> on ${fmtDate(w.wd)}`).join(', ')}.` : 'No weddings this week.'}</p>
<p style="margin:0"><a href="${APP}" style="background:#D9B77C;color:#3D1C3B;text-decoration:none;font-weight:700;padding:10px 16px;border-radius:10px;display:inline-block">Open your dashboard</a></p>
<p style="font-size:12px;color:#6B5F72;margin-top:22px">Turn this off any time under Account &rsaquo; Morning brief.</p></div>`;
    try {
      await sendEmail(to, `Lazo this morning: ${waiting.length} waiting, ${due.length} due, ${weddings.length} wedding${weddings.length === 1 ? '' : 's'} this week`, html, text);
      await vDoc.ref.set({ dailyBrief: { lastSentDay: lp.day, lastSentAt: FieldValue.serverTimestamp() } }, { merge: true });
      sent++;
    } catch (e) {
      console.error('morningBrief', vDoc.id, e.message);
    }
  }
  console.log(`morningBrief: ${sent} sent of ${vSnap.size} enabled`);
});

// ------------------------------------------------------ team invites ------
exports.redeemVendorInvite = onCall({ memory: '256MiB' }, async (request) => {
  const auth = request.auth;
  if (!auth) throw new HttpsError('unauthenticated', 'Sign in first.');
  const code = str(request.data && request.data.code).trim().toUpperCase();
  if (!/^[A-Z0-9]{4,12}$/.test(code)) throw new HttpsError('invalid-argument', 'That code did not work.');
  const snap = await db.collection('vendorInvites').where('code', '==', code).limit(5).get();
  const inv = snap.docs.find((d) => str(d.data().status) === 'pending');
  if (!inv) throw new HttpsError('not-found', 'That code is not active. Ask for a new invite.');
  const m = inv.data();
  const invitedEmail = str(m.email).toLowerCase();
  const myEmail = str(auth.token && auth.token.email).toLowerCase();
  if (invitedEmail && myEmail && invitedEmail !== myEmail) {
    throw new HttpsError('permission-denied', `This invite was sent to ${invitedEmail}. Sign in with that email.`);
  }
  const vendorId = str(m.vendorId);
  if (!vendorId) throw new HttpsError('failed-precondition', 'Invite is missing its business.');
  const batch = db.batch();
  batch.set(db.collection('users').doc(auth.uid), {
    vendorId, role: 'vendor', vendorRole: str(m.role) || 'manager', joinedVendorAt: FieldValue.serverTimestamp(),
  }, { merge: true });
  batch.set(inv.ref, { status: 'accepted', acceptedBy: auth.uid, acceptedAt: FieldValue.serverTimestamp() }, { merge: true });
  await batch.commit();
  return { vendorId };
});

// ------------------------------------------------------ june import --------
// The couple pastes what they have; June turns it into Lazo's shapes. Nothing
// here logs into another site: a website import fetches the public page the
// couple gave us, the same way a browser would.
const CATEGORY_SLUGS = Object.keys(CATS);

function stripHtml(html) {
  return String(html || '')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, ' ')
    .replace(/<br\s*\/?>/gi, '\n').replace(/<\/(p|div|li|h[1-6]|tr|section|article)>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/[ \t]+/g, ' ').replace(/\n\s*\n+/g, '\n').trim();
}

async function claudeJson(system, userContent, apiKey) {
  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'x-api-key': apiKey, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
    body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 2000, system, messages: [{ role: 'user', content: userContent }] }),
  });
  if (!r.ok) throw new Error(`anthropic ${r.status}: ${(await r.text()).slice(0, 200)}`);
  const j = await r.json();
  const text = (j.content || []).filter((c) => c.type === 'text').map((c) => c.text).join('\n');
  const m = /\{[\s\S]*\}/.exec(text.replace(/```json|```/g, ''));
  if (!m) throw new Error('no json in reply');
  return JSON.parse(m[0]);
}

exports.juneImport = onCall({ memory: '512MiB', timeoutSeconds: 90, secrets: [ANTHROPIC_API_KEY] }, async (request) => {
  if (!request.auth) throw new HttpsError('unauthenticated', 'Sign in first.');
  const kind = str(request.data && request.data.kind);
  let input = str(request.data && request.data.input).slice(0, 60000);
  const key = ANTHROPIC_API_KEY.value();
  if (!key) throw new HttpsError('failed-precondition', 'June is not configured.');

  if (kind === 'website') {
    // a URL: fetch the public page the couple gave us
    const urlMatch = /^https?:\/\/\S+$/i.exec(input.trim());
    if (urlMatch) {
      try {
        const resp = await fetch(input.trim(), { headers: { 'user-agent': 'Mozilla/5.0 (compatible; Lazo import; +https://meetlazo.com)', accept: 'text/html' }, redirect: 'follow' });
        const html = await resp.text();
        input = stripHtml(html).slice(0, 40000);
        if (input.length < 200) throw new HttpsError('not-found', 'That page didn\u2019t give us much to read. Try pasting its text instead.');
      } catch (e) {
        if (e instanceof HttpsError) throw e;
        throw new HttpsError('unavailable', 'Couldn\u2019t open that link. Try pasting the page\u2019s text instead.');
      }
    }
    const system = `You extract wedding website details into JSON. Return ONLY a JSON object:
{"site":{"names":"","dateIso":"YYYY-MM-DD or empty","dateDisplay":"","venueName":"","venueAddress":"","ceremonyTime":"","cocktailTime":"","receptionTime":"","sendOffTime":"","dressCode":"","hotelBlock":"","transport":"","parking":"","travelNotes":"","story":""},
 "registryLinks":[{"label":"","url":""}]}
Rules: copy the couple's own words for "story" (trim to ~900 characters, keep it in their voice, no marketing text from the host site). Times as they wrote them ("4:30 pm"). Leave any field you can't find as an empty string. registryLinks only for real registry/fund URLs. Never invent details.`;
    const out = await claudeJson(system, `Wedding website content:\n\n${input}`, key);
    return { site: out.site || {}, registryLinks: Array.isArray(out.registryLinks) ? out.registryLinks.slice(0, 8) : [] };
  }

  if (kind === 'budget') {
    const system = `You turn a wedding budget into JSON lines mapped to these Lazo categories (use the slug exactly): ${CATEGORY_SLUGS.join(', ')}.
Return ONLY: {"lines":[{"category":"<slug>","label":"<their wording>","planned":<number>,"paid":<number>}]}
Rules: numbers only (no $ or commas). "planned" is the budgeted/estimated amount; "paid" is what has actually been paid/spent (0 if unknown). Map line items to the closest category; put a line you truly cannot map under the closest reasonable one or drop it. Do not invent lines. Ignore totals, taxes and tips rows.`;
    const content = [];
    const img = str(request.data && request.data.imageBase64);
    if (img) {
      content.push({ type: 'image', source: { type: 'base64', media_type: str(request.data.imageType) || 'image/png', data: img } });
      content.push({ type: 'text', text: 'This is a screenshot of a wedding budget page. Extract the lines.' });
    } else {
      if (!input.trim()) throw new HttpsError('invalid-argument', 'Nothing to read.');
      content.push({ type: 'text', text: `Wedding budget:\n\n${input}` });
    }
    const out = await claudeJson(system, content, key);
    const lines = (Array.isArray(out.lines) ? out.lines : []).filter((l) => l && CATEGORY_SLUGS.includes(str(l.category)))
      .map((l) => ({ category: str(l.category), label: str(l.label).slice(0, 80), planned: Number(l.planned) || 0, paid: Number(l.paid) || 0 }));
    return { lines };
  }

  if (kind === 'vendors') {
    if (!input.trim()) throw new HttpsError('invalid-argument', 'Nothing to read.');
    const metroId = str(request.data && request.data.metroId);
    const system = `You turn a couple's list of booked wedding vendors into JSON mapped to these Lazo categories (use the slug exactly): ${CATEGORY_SLUGS.join(', ')}.
Return ONLY: {"vendors":[{"name":"","category":"<slug>","amount":<number or 0>}]}
Rules: one entry per business. Infer the category from the name or description when obvious ("Bloom Co" -> wedding-florists); if unclear, use the category they stated. amount = contract total if given, else 0. Never invent vendors.`;
    const out = await claudeJson(system, `Booked vendors:\n\n${input}`, key);
    const vendors = (Array.isArray(out.vendors) ? out.vendors : []).filter((v) => v && str(v.name) && CATEGORY_SLUGS.includes(str(v.category)))
      .map((v) => ({ name: str(v.name).slice(0, 120), category: str(v.category), amount: Number(v.amount) || 0, lazoVendorId: '' }));
    // match to a Lazo listing in the couple's metro by name (exact, then prefix)
    if (metroId) {
      for (const v of vendors) {
        try {
          const q = await db.collection('vendors').where('metroId', '==', metroId).where('name', '>=', v.name).where('name', '<=', v.name + '\uf8ff').limit(3).get();
          const hit = q.docs.find((d) => str(d.data().name).toLowerCase() === v.name.toLowerCase()) || q.docs[0];
          if (hit && str(hit.data().name).toLowerCase().startsWith(v.name.toLowerCase().slice(0, 8))) v.lazoVendorId = hit.id;
        } catch (e) { /* index may be missing; matching is best-effort */ }
      }
    }
    return { vendors };
  }

  throw new HttpsError('invalid-argument', 'Unknown import kind.');
});

// ------------------------------------------------------ email import -------
// import@meetlazo.com is its own Zoho user; the token belongs to that user, so
// the sweep reads that mailbox's Inbox directly. Account id is looked up from
// the token once per run (it is the only account the token can see).
const ZOHO_IMPORT_FOLDER = 'Inbox';
const IMPORT_ADDRESS = 'import@meetlazo.com';
let ZOHO_ACCOUNT_ID = '';

async function zohoAccountId(token) {
  if (ZOHO_ACCOUNT_ID) return ZOHO_ACCOUNT_ID;
  const r = await fetch('https://mail.zoho.com/api/accounts', { headers: { Authorization: `Zoho-oauthtoken ${token}` } });
  const j = await r.json().catch(() => ({}));
  const acc = (j.data || []).find((a) => str(a.primaryEmailAddress).toLowerCase() === IMPORT_ADDRESS) || (j.data || [])[0];
  if (!acc) throw new Error('zoho: no mailbox visible to this token');
  ZOHO_ACCOUNT_ID = str(acc.accountId);
  return ZOHO_ACCOUNT_ID;
}

async function zohoToken() {
  const r = await fetch('https://accounts.zoho.com/oauth/v2/token', {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ grant_type: 'refresh_token', client_id: ZOHO_CLIENT_ID.value(), client_secret: ZOHO_CLIENT_SECRET.value(), refresh_token: ZOHO_REFRESH_TOKEN.value() }),
  });
  const j = await r.json();
  if (!j.access_token) throw new Error('zoho token: ' + JSON.stringify(j).slice(0, 200));
  return j.access_token;
}

async function zoho(path, token, opts) {
  const r = await fetch(`https://mail.zoho.com/api/accounts/${ZOHO_ACCOUNT_ID}${path}`, {
    ...(opts || {}),
    headers: { Authorization: `Zoho-oauthtoken ${token}`, 'content-type': 'application/json', ...((opts && opts.headers) || {}) },
  });
  if (opts && opts.raw) return r;
  const j = await r.json().catch(() => ({}));
  return j;
}

exports.importMailSweep = onSchedule({
  schedule: 'every 2 minutes', timeZone: 'UTC', memory: '512MiB', timeoutSeconds: 120,
  secrets: [ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN, ANTHROPIC_API_KEY, RESEND_API_KEY],
}, async () => {
  const token = await zohoToken();
  await zohoAccountId(token);
  const folders = await zoho('/folders', token);
  const folder = (folders.data || []).find((f) => str(f.folderName).toLowerCase() === ZOHO_IMPORT_FOLDER.toLowerCase());
  if (!folder) { console.log('importMailSweep: no Inbox folder visible'); return; }
  const list = await zoho(`/messages/view?folderId=${folder.folderId}&status=unread&limit=20&sortorder=false`, token);
  const msgs = list.data || [];
  if (!msgs.length) return;
  const apiKey = ANTHROPIC_API_KEY.value();

  for (const m of msgs) {
    const messageId = str(m.messageId);
    const seen = await db.collection('emailImports').doc(messageId).get();
    if (seen.exists) continue;
    const sender = (str(m.fromAddress) || (/<([^>]+)>/.exec(str(m.sender)) || [])[1] || '').toLowerCase().trim();
    const subject = str(m.subject);
    const record = { sender, subject, receivedAt: FieldValue.serverTimestamp(), status: 'skipped' };
    try {
      // who forwarded it?
      const us = await db.collection('users').where('email', '==', sender).limit(1).get();
      if (us.empty) {
        await sendEmail(sender, 'Lazo: we couldn\u2019t match that email to your account',
          `<p>Thanks for forwarding that. We couldn\u2019t find a Lazo account under <b>${sender}</b>, so nothing was added.</p><p>Forward it again from the email address you use to sign in to Lazo, and it will land on your vendor team.</p>`,
          `We couldn't find a Lazo account under ${sender}. Forward it again from the address you use to sign in.`);
        record.status = 'no-account';
        await db.collection('emailImports').doc(messageId).set(record);
        await zoho('/updatemessage', token, { method: 'PUT', body: JSON.stringify({ mode: 'markAsRead', messageId: [messageId] }) });
        continue;
      }
      const uid = us.docs[0].id;
      const coupleUid = str(us.docs[0].data().coupleUid) || uid;
      const coupleDoc = await db.collection('couples').doc(coupleUid).get();
      const metroId = str(coupleDoc.data() && coupleDoc.data().metroId);

      // the message and its attachments
      const content = await zoho(`/folders/${folder.folderId}/messages/${messageId}/content`, token);
      const bodyText = stripHtml(content.data && content.data.content).slice(0, 30000);
      const parts = [];
      const attInfo = await zoho(`/folders/${folder.folderId}/messages/${messageId}/attachmentinfo`, token);
      const atts = ((attInfo.data && attInfo.data.attachments) || []).slice(0, 4);
      const stored = [];
      for (const a of atts) {
        const name = str(a.attachmentName), size = Number(a.attachmentSize) || 0;
        const isPdf = /\.pdf$/i.test(name), isImg = /\.(png|jpe?g|webp)$/i.test(name);
        if ((!isPdf && !isImg) || size > 8 * 1024 * 1024) continue;
        const resp = await zoho(`/folders/${folder.folderId}/messages/${messageId}/attachments/${a.attachmentId}`, token, { raw: true });
        const buf = Buffer.from(await resp.arrayBuffer());
        const b64 = buf.toString('base64');
        if (isPdf) parts.push({ type: 'document', source: { type: 'base64', media_type: 'application/pdf', data: b64 } });
        else parts.push({ type: 'image', source: { type: 'base64', media_type: /png$/i.test(name) ? 'image/png' : (/webp$/i.test(name) ? 'image/webp' : 'image/jpeg'), data: b64 } });
        if (isPdf) {
          try {
            const path = `couples/${coupleUid}/imports/${messageId}/${name.replace(/[^\w.\-]+/g, '_')}`;
            const file = admin.storage().bucket().file(path);
            await file.save(buf, { contentType: 'application/pdf', resumable: false });
            const [url] = await file.getSignedUrl({ action: 'read', expires: '2099-01-01' });
            stored.push({ name, url });
          } catch (e) { console.warn('attachment store failed', e.message); }
        }
      }
      parts.push({ type: 'text', text: `Forwarded email from a couple planning their wedding.\nSubject: ${subject}\n\n${bodyText}\n\nExtract the wedding vendor booking this email confirms.` });

      const system = `You read a vendor's booking confirmation (email body, and any attached contract or receipt) and return ONLY a JSON object:
{"vendor":{"name":"","category":"<one of: ${CATEGORY_SLUGS.join(', ')}>","amount":<contract total or 0>,"deposit":<amount already paid or 0>,"balanceDue":"<date or empty>","weddingDate":"YYYY-MM-DD or empty","notes":"<one short line: what's included, or empty>"},"confidence":<0-1>}
Rules: the vendor is the business the couple hired, not the couple and not Lazo. Numbers only. If this email is not a wedding vendor confirmation, return {"vendor":null,"confidence":0}. Never invent amounts.`;
      const out = await claudeJson(system, parts, apiKey);
      const v = out && out.vendor;
      if (!v || !str(v.name) || !CATEGORY_SLUGS.includes(str(v.category)) || Number(out.confidence) < 0.4) {
        await sendEmail(sender, 'Lazo: we couldn\u2019t read that one',
          `<p>Thanks for forwarding <i>${subject || 'that email'}</i>. June couldn\u2019t find a vendor booking in it, so nothing was added.</p><p>If it is a booking, you can add the vendor by name under <b>Switching from another planning site</b> in your Lazo account.</p>`,
          `June couldn't find a vendor booking in "${subject}". Nothing was added.`);
        record.status = 'unrecognized';
        await db.collection('emailImports').doc(messageId).set(record);
        await zoho('/updatemessage', token, { method: 'PUT', body: JSON.stringify({ mode: 'markAsRead', messageId: [messageId] }) });
        continue;
      }
      // match to a Lazo listing in their metro
      let lazoVendorId = '';
      if (metroId) {
        try {
          const q = await db.collection('vendors').where('metroId', '==', metroId).where('name', '>=', v.name).where('name', '<=', v.name + '\uf8ff').limit(3).get();
          const hit = q.docs.find((d) => str(d.data().name).toLowerCase() === str(v.name).toLowerCase()) || q.docs[0];
          if (hit && str(hit.data().name).toLowerCase().startsWith(str(v.name).toLowerCase().slice(0, 8))) lazoVendorId = hit.id;
        } catch (e) { /* best effort */ }
      }
      const amount = Number(v.amount) || 0, deposit = Number(v.deposit) || 0;
      const planPatch = {
        status: 'booked', vendorName: str(v.name).slice(0, 120), bookedAt: FieldValue.serverTimestamp(), source: 'email-import',
        ...(lazoVendorId ? { vendorId: lazoVendorId } : {}),
        ...(amount > 0 ? { budgetActual: amount } : {}),
        ...(deposit > 0 ? { depositPaid: deposit } : {}),
        ...(str(v.balanceDue) ? { balanceDue: str(v.balanceDue) } : {}),
        ...(str(v.notes) ? { notes: str(v.notes).slice(0, 300) } : {}),
        ...(stored.length ? { contractUrl: stored[0].url, contractName: stored[0].name } : {}),
      };
      await db.collection('couples').doc(coupleUid).collection('plan').doc(str(v.category)).set(planPatch, { merge: true });
      await db.collection('couples').doc(coupleUid).set({ importedAt: FieldValue.serverTimestamp() }, { merge: true });
      const catLabel = (CATS[str(v.category)] || str(v.category)).replace(/s$/, '');
      const moneyLine = amount > 0 ? ` ${money(amount)} total${deposit > 0 ? `, ${money(deposit)} paid` : ''}${str(v.balanceDue) ? `, balance due ${str(v.balanceDue)}` : ''}.` : '';
      await sendEmail(sender, `Lazo: added ${str(v.name)} to your vendor team`,
        `<p><b>${str(v.name)}</b> (${catLabel}) is on your vendor team as booked.${moneyLine}${stored.length ? ' The contract is attached to it.' : ''}</p><p><a href="${APP}">Open your planning home</a></p><p style="color:#6B5F72;font-size:12px">If that\u2019s wrong, open the vendor on your team and edit it. We keep what we read and the attachment - not the email.</p>`,
        `${str(v.name)} (${catLabel}) is on your vendor team as booked.${moneyLine} ${APP}`);
      record.status = 'added'; record.vendor = str(v.name); record.category = str(v.category); record.coupleUid = coupleUid;
      await db.collection('emailImports').doc(messageId).set(record);
      await zoho('/updatemessage', token, { method: 'PUT', body: JSON.stringify({ mode: 'markAsRead', messageId: [messageId] }) });
    } catch (e) {
      console.error('importMailSweep', messageId, e.message);
      record.status = 'error'; record.error = str(e.message).slice(0, 300);
      await db.collection('emailImports').doc(messageId).set(record);
      await zoho('/updatemessage', token, { method: 'PUT', body: JSON.stringify({ mode: 'markAsRead', messageId: [messageId] }) }).catch(() => {});
    }
  }
});

// ------------------------------------------------------ partner invites ----
// Same shape as vendor team invites: the inviter creates coupleInvites/{id}
// {coupleUid, email, code}; the partner signs up, enters the code, and their
// users doc points at the inviter's couple doc. Every couple query in the
// widget keys on that id from then on.
exports.redeemCoupleInvite = onCall({ memory: '256MiB' }, async (request) => {
  const auth = request.auth;
  if (!auth) throw new HttpsError('unauthenticated', 'Sign in first.');
  const code = str(request.data && request.data.code).trim().toUpperCase();
  if (!/^[A-Z0-9]{4,12}$/.test(code)) throw new HttpsError('invalid-argument', 'That code did not work.');
  const snap = await db.collection('coupleInvites').where('code', '==', code).limit(5).get();
  const inv = snap.docs.find((d) => str(d.data().status) === 'pending');
  if (!inv) throw new HttpsError('not-found', 'That code is not active. Ask your partner for a new one.');
  const m = inv.data();
  const invitedEmail = str(m.email).toLowerCase();
  const myEmail = str(auth.token && auth.token.email).toLowerCase();
  if (invitedEmail && myEmail && invitedEmail !== myEmail) {
    throw new HttpsError('permission-denied', `This invite was sent to ${invitedEmail}. Sign in with that email.`);
  }
  const coupleUid = str(m.coupleUid);
  if (!coupleUid || coupleUid === auth.uid) throw new HttpsError('failed-precondition', 'Invite is missing its plan.');
  const batch = db.batch();
  batch.set(db.collection('users').doc(auth.uid), { coupleUid, role: 'couple', joinedCoupleAt: FieldValue.serverTimestamp() }, { merge: true });
  batch.set(inv.ref, { status: 'accepted', acceptedBy: auth.uid, acceptedAt: FieldValue.serverTimestamp() }, { merge: true });
  const partnerName = str(auth.token && auth.token.name).split(' ')[0];
  if (partnerName) batch.set(db.collection('couples').doc(coupleUid), { partnerName, partnerUid: auth.uid }, { merge: true });
  await batch.commit();
  return { coupleUid };
});

// END OF FILE - JC-LAZO-FNDASH-0908-008


// price sheet -> page images + packages (priceSheet.js, JC-LAZO-FNDASH-0910-009)
const priceSheet = require('./priceSheet');
exports.priceSheetExtract = priceSheet.priceSheetExtract;
exports.priceSheetRerun = priceSheet.priceSheetRerun;

// JC-LAZO-FNDASH-0912-MUSIC-001
const music = require('./music')(ANTHROPIC_API_KEY);
exports.juneMusic = music.juneMusic;

// JC-LAZO-FNDASH-0912-SEATING-001
const seating = require('./seating')(ANTHROPIC_API_KEY);
exports.juneSeating = seating.juneSeating;

// JC-LAZO-FNDASH-0913-011: payment plans, Whop vendor rail, booking page
const payments = require('./payments')(RESEND_API_KEY);
Object.assign(exports, payments);

// JC-LAZO-FNDASH-0913-012: embeddable lead form + two-way SMS
const leads = require('./leads')(RESEND_API_KEY);
Object.assign(exports, leads);

// JC-LAZO-FNDASH-0913-013: pipeline tasks roll-up + reminders
const pipeline = require('./pipeline')(RESEND_API_KEY);
Object.assign(exports, pipeline);

// JC-LAZO-FNDASH-0913-015: consult scheduler
const scheduler = require('./scheduler')(RESEND_API_KEY);
Object.assign(exports, scheduler);

// JC-LAZO-FNDASH-0913-016/017: MCP connector + June for vendors
// JC-LAZO-DELETE-0918-001: real account deletion (the app only wiped
// couples/{cid}/plan before this, leaving the website, guests, inquiries,
// photos and the users doc behind).
// JC-LAZO-SAFETY-0918-001: couples can report and block a vendor from a thread.
const safety = require('./safety')();
exports.blockVendor = safety.blockVendor;
exports.reportVendor = safety.reportVendor;

const deleteAccount = require('./deleteAccount')();
exports.deleteMyAccount = deleteAccount.deleteMyAccount;
// JC-LAZO-DELETE-0924-002: vendor-side deletion (App Store 5.1.1(v))
Object.assign(exports, require('./deleteVendorAccount')());

Object.assign(exports, require('./mcp')());
Object.assign(exports, require('./june-vendor')(ANTHROPIC_API_KEY));
// 022: juneToken - custom token so the Talk to June button opens the hub signed in
Object.assign(exports, require('./june-token'));

// JC-LAZO-FNDASH-0913-018: the practice couple
Object.assign(exports, require('./demo')(RESEND_API_KEY, ANTHROPIC_API_KEY));

// JC-LAZO-FNDASH-1007-023: welcome emails at signup (couples on couples/{uid} create, vendors on users.role = vendor)
Object.assign(exports, require('./welcome')(RESEND_API_KEY));

// JC-LAZO-FNDASH-1007-024: the couple hears about every milestone (reply, proposal, booked, signed, invoice, receipt, questionnaire, sneak peek, delivered, released)
Object.assign(exports, require('./couple-notify')(RESEND_API_KEY));

// JC-LAZO-FNDASH-0913-019: real weddings showcase
Object.assign(exports, require('./showcase')());

// JC-LAZO-FNDASH-0913-020: say hello (Pro/Studio outreach)
Object.assign(exports, require('./hello')(RESEND_API_KEY));

// JC-LAZO-FNDASH-0913-021: the vendor team graph
Object.assign(exports, require('./team')(RESEND_API_KEY));

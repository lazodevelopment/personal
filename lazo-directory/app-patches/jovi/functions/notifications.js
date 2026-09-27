// Jovi Health — notification inbox + push delivery + schedulers.
// Version 2026.09.23-r3 (per-member timezones; r2 = full audit of events)
//
// Writes users/{uid}/notifications (read by JoviNotificationsInbox) and
// sends the matching push to the member's FCM tokens
// (users/{uid}/fcm_tokens, the collection FlutterFlow's addFcmToken fills).
// Push data carries initialPageName / parameterData so the FlutterFlow app
// routes on tap exactly like its own pushes.
//
// Install (kurv-functions/index.js):
//   Object.assign(exports, require('./notifications'));
// Deploy by name only (three live functions have no source in that folder):
//   firebase deploy --project kurv-health --only functions:onRequestCreated,functions:onRequestUpdated,functions:onAppointmentCancelled,functions:appointmentReminders,functions:onHumanClaimCreated,functions:onPetClaimCreated,functions:onHumanClaimUpdated,functions:onPetClaimUpdated,functions:onPaymentLogged,functions:onMembershipChanged,functions:billingReminders,functions:onRefillUpdated,functions:onSupportMessage,functions:onWeightAlertCreated,functions:fireScheduledReminders,functions:vaccinationDueSweep
//
// INDEXES (each first run logs a FAILED_PRECONDITION with a create link):
//   scheduled_reminders  collection group  fired ASC, fireAt ASC
//   vaccinations         collection group  expiresAt ASC        (people)
//   vaccinations         collection group  expirationDate ASC   (pets)
//
// EVENT COVERAGE (what fires, from which write):
//   Appointments  request created (pending)            requests onCreate
//                 confirmed / completed / no-show       requests onUpdate status
//                 reschedule submitted                  requests onUpdate date/time change
//                 cancelled                             cancelled_appointments onCreate
//                 reminders 24 h and 1 h before         appointmentReminders (every 15 min)
//   Claims        received                              users/{uid}/claims + pets/*/claims onCreate
//                 review / needs info / approved / paid users/{uid}/claims + pets/*/claims onUpdate
//   Billing       payment received / payment failed     payment_logs onCreate (PayArc webhook)
//                 debit in 3 days                       billingReminders (9 am, member's zone)
//                 renewal in 30 / 7 / 1 days            billingReminders
//                 renewed, suspended, cancellation       users/{uid} onUpdate
//                 scheduled, kept, ended, card status    (subscriptionStatus, renew, lastChargeStatus)
//   Refills       approved / ready / filled / denied     prescriptionRefills onUpdate
//   Support       reply from the Jovi team              helpTickets/*/messages onCreate
//   Pets          weight alert                          weight_alerts onCreate
//                 medication dose due                   fireScheduledReminders (every 5 min)
//   Vaccines      booster due in 30 / 7 days, overdue   vaccinationDueSweep (9 am, member's zone)

const functions = require('firebase-functions/v1');
const admin = require('firebase-admin');

if (!admin.apps.length) admin.initializeApp();

// FlutterFlow page names the inbox opens on tap. VERIFY every one against
// the page names in the FlutterFlow project: pushNamed fails silently on a
// name that does not exist.
const ROUTES = {
  claims: 'fileClaim',
  petClaims: 'filePetClaim',
  careRecords: 'careRecords',
  appointments: 'appointments',
  billing: 'billing',
  planDetails: 'planDetails',
  weightAlerts: 'weightAlerts',
  petMedications: 'petMedications',
  petVaccinations: 'petVaccinations',
  vaccinations: 'vaccinations',
  refills: 'prescriptionRefills',
  chat: 'chatWidget',
};

const REGION = 'us-central1';

// Appointment dates are stored as local wall-clock strings
// ("2026-04-20T00:00:00" + "10:30") with no zone. Members are nationwide,
// so every clock here is the member's own:
//   1. requests.timezone / users.timezone   IANA id written by the app
//      (Request Flow stamps each request; Home syncs the user doc)
//   2. users.state                          two-letter state → zone
//   3. users.tzOffsetMinutes                device offset → zone
//   4. DEFAULT_TIMEZONE                     last resort
const DEFAULT_TIMEZONE = 'America/Chicago';

const STATE_TZ = {
  CT: 'America/New_York', DE: 'America/New_York', DC: 'America/New_York', FL: 'America/New_York',
  GA: 'America/New_York', IN: 'America/Indiana/Indianapolis', ME: 'America/New_York', MD: 'America/New_York',
  MA: 'America/New_York', MI: 'America/Detroit', NH: 'America/New_York', NJ: 'America/New_York',
  NY: 'America/New_York', NC: 'America/New_York', OH: 'America/New_York', PA: 'America/New_York',
  RI: 'America/New_York', SC: 'America/New_York', VT: 'America/New_York', VA: 'America/New_York',
  WV: 'America/New_York', KY: 'America/New_York', TN: 'America/Chicago',
  AL: 'America/Chicago', AR: 'America/Chicago', IL: 'America/Chicago', IA: 'America/Chicago',
  KS: 'America/Chicago', LA: 'America/Chicago', MN: 'America/Chicago', MS: 'America/Chicago',
  MO: 'America/Chicago', NE: 'America/Chicago', ND: 'America/Chicago', OK: 'America/Chicago',
  SD: 'America/Chicago', TX: 'America/Chicago', WI: 'America/Chicago',
  CO: 'America/Denver', ID: 'America/Boise', MT: 'America/Denver', NM: 'America/Denver',
  UT: 'America/Denver', WY: 'America/Denver', AZ: 'America/Phoenix',
  CA: 'America/Los_Angeles', NV: 'America/Los_Angeles', OR: 'America/Los_Angeles', WA: 'America/Los_Angeles',
  AK: 'America/Anchorage', HI: 'Pacific/Honolulu', PR: 'America/Puerto_Rico',
};

const OFFSET_TZ = {
  '-240': 'America/Puerto_Rico', '-300': 'America/New_York', '-360': 'America/Chicago',
  '-420': 'America/Denver', '-480': 'America/Los_Angeles', '-540': 'America/Anchorage',
  '-600': 'Pacific/Honolulu',
};

function isValidTz(tz) {
  if (!tz || typeof tz !== 'string') return false;
  try {
    new Intl.DateTimeFormat('en-US', { timeZone: tz });
    return true;
  } catch (_) {
    return false;
  }
}

/** Zone for a user doc's data (no reads). */
function tzForUserData(u) {
  if (!u) return DEFAULT_TIMEZONE;
  if (isValidTz(u.timezone)) return u.timezone;
  const st = String(u.state || u.onboard_state || '').trim().toUpperCase();
  if (STATE_TZ[st]) return STATE_TZ[st];
  const off = Number(u.tzOffsetMinutes);
  if (Number.isFinite(off)) {
    // Offsets are ambiguous in summer (CDT = EST); the app normally sends
    // the IANA id above, so this is a coarse last resort.
    return OFFSET_TZ[String(off)] || OFFSET_TZ[String(off - 60)] || DEFAULT_TIMEZONE;
  }
  return DEFAULT_TIMEZONE;
}

const tzCache = new Map();
/** Zone for a uid, one user-doc read per uid per invocation. */
async function tzForUid(uid) {
  if (tzCache.has(uid)) return tzCache.get(uid);
  let tz = DEFAULT_TIMEZONE;
  try {
    const u = (await db().collection('users').doc(uid).get()).data();
    tz = tzForUserData(u);
  } catch (_) {}
  tzCache.set(uid, tz);
  return tz;
}

// ─────────────────────────────────────────────────────────────────────
// Core: inbox doc + push
// ─────────────────────────────────────────────────────────────────────

const db = () => admin.firestore();

async function notify(uid, { id, type, title, body, route, params, refPath }) {
  const inbox = db().collection('users').doc(uid).collection('notifications');
  const ref = id ? inbox.doc(id) : inbox.doc();
  await ref.set(
    {
      type,
      title,
      body: body || '',
      route: route || null,
      params: params || {},
      refPath: refPath || null,
      read: false,
      createdAt: admin.firestore.FieldValue.serverTimestamp(),
    },
    { merge: true },
  );
  await sendPush(uid, { title, body, route, params, type });
}

/// Same as notify but never fires twice for the same id (schedulers rerun).
async function notifyOnce(uid, payload) {
  if (!payload.id) return notify(uid, payload);
  const ref = db().collection('users').doc(uid).collection('notifications').doc(payload.id);
  const existing = await ref.get();
  if (existing.exists) return false;
  await notify(uid, payload);
  return true;
}

async function sendPush(uid, { title, body, route, params, type }) {
  const tokensSnap = await db().collection('users').doc(uid).collection('fcm_tokens').get();
  const tokens = [];
  const tokenDocs = new Map();
  tokensSnap.docs.forEach((d) => {
    const t = d.data().fcm_token;
    if (typeof t === 'string' && t.length > 0) {
      tokens.push(t);
      tokenDocs.set(t, d.ref);
    }
  });
  if (tokens.length === 0) return;

  const res = await admin.messaging().sendEachForMulticast({
    notification: { title, body: body || '' },
    data: {
      type: type || 'system',
      initialPageName: route || '',
      parameterData: JSON.stringify(params || {}),
    },
    apns: { payload: { aps: { sound: 'default', badge: 1 } } },
    android: { notification: { sound: 'default' } },
    tokens,
  });

  const dead = [];
  res.responses.forEach((r, i) => {
    const code = r.error && r.error.code;
    if (
      code === 'messaging/registration-token-not-registered' ||
      code === 'messaging/invalid-registration-token'
    ) {
      dead.push(tokens[i]);
    }
  });
  if (dead.length) {
    const batch = db().batch();
    dead.forEach((t) => batch.delete(tokenDocs.get(t)));
    await batch.commit();
  }
}

// ─────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────

const lower = (v) => String(v || '').toLowerCase();

function statusChanged(before, after) {
  const a = lower(before && before.status);
  const b = lower(after && after.status);
  return a !== b ? b : null;
}

function toDate(v) {
  if (!v) return null;
  if (v.toDate) return v.toDate();
  const d = new Date(v);
  return isNaN(d.getTime()) ? null : d;
}

function money(n) {
  return typeof n === 'number' ? `$${n.toFixed(2)}` : null;
}

function dayKey(d) {
  return d.toISOString().slice(0, 10);
}

/** Offset (ms) of `tz` at the given instant. */
function tzOffsetMs(date, tz) {
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone: tz || DEFAULT_TIMEZONE,
    hourCycle: 'h23',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
  const p = {};
  fmt.formatToParts(date).forEach((x) => { p[x.type] = x.value; });
  const asUtc = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second);
  return asUtc - date.getTime();
}

/** "2026-04-20T00:00:00" + "10:30" (wall clock in `tz`) → UTC Date. */
function appointmentInstant(dateStr, timeStr, tz) {
  if (!dateStr) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(dateStr));
  if (!m) return toDate(dateStr);
  let h = 9, min = 0;
  // The app writes display slots like '9:30 AM' / '2:00 PM'; 24-hour 'HH:mm' is also accepted.
  const t = /^(\d{1,2}):(\d{2})\s*([AaPp][Mm])?/.exec(String(timeStr || '').trim());
  if (t) {
    h = +t[1]; min = +t[2];
    const ap = (t[3] || '').toUpperCase();
    if (ap === 'PM' && h < 12) h += 12;
    if (ap === 'AM' && h === 12) h = 0;
  }
  const naive = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], h, min, 0));
  return new Date(naive.getTime() - tzOffsetMs(naive, tz));
}

function fmtWhen(date, tz) {
  if (!date) return '';
  return new Intl.DateTimeFormat('en-US', {
    timeZone: tz || DEFAULT_TIMEZONE,
    weekday: 'short', month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit',
  }).format(date);
}

function fmtDay(date, tz) {
  if (!date) return '';
  return new Intl.DateTimeFormat('en-US', {
    timeZone: tz || DEFAULT_TIMEZONE, month: 'long', day: 'numeric', year: 'numeric',
  }).format(date);
}

/** Calendar date in `tz` as yyyy-mm-dd for "now + days". */
function localDayString(daysFromNow, tz) {
  const d = new Date(Date.now() + daysFromNow * 86400000);
  return new Intl.DateTimeFormat('en-CA', { timeZone: tz || DEFAULT_TIMEZONE }).format(d);
}

/** Calendar date of an instant in `tz` as yyyy-mm-dd. */
function dayIn(date, tz) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: tz || DEFAULT_TIMEZONE }).format(date);
}

/** Start of a calendar day (yyyy-mm-dd) in `tz` as a UTC Date. */
function localDayStart(dayStr, tz) {
  const [y, m, d] = dayStr.split('-').map(Number);
  const naive = new Date(Date.UTC(y, m - 1, d, 0, 0, 0));
  return new Date(naive.getTime() - tzOffsetMs(naive, tz));
}

function userMonthlyTotal(u) {
  const grand = Number(u.grandTotal);
  if (grand > 0) return grand;
  const h = Number(u.totalPremium) || 0;
  const p = Number(u.petTotalPremium) || 0;
  return h + p > 0 ? h + p : null;
}

/** Walk up a doc ref to find the users/{uid} segment. */
function uidFromRef(ref) {
  let r = ref;
  while (r) {
    if (r.parent && r.parent.id === 'users' && !r.parent.parent) return r.id;
    r = r.parent ? r.parent.parent : null;
  }
  return null;
}

// ─────────────────────────────────────────────────────────────────────
// APPOINTMENTS — requests/{id} (top level, userId; cancel nulls userId)
// ─────────────────────────────────────────────────────────────────────

const ACTIVE_APPT = new Set(['pending', 'confirmed', 'scheduled', 'booked', 'rescheduled']);

function apptLabel(d) {
  const type = String(d.visitType || 'visit').replace(/_/g, ' ');
  return type.charAt(0).toUpperCase() + type.slice(1);
}

exports.onRequestCreated = functions
  .region(REGION)
  .firestore.document('requests/{requestId}')
  .onCreate(async (snap, ctx) => {
    const d = snap.data() || {};
    const uid = d.userId;
    if (!uid) return;
    const tz = isValidTz(d.timezone) ? d.timezone : await tzForUid(uid);
    const when = appointmentInstant(d.appointmentDate, d.appointmentTime, tz);
    await notify(uid, {
      id: `request_${ctx.params.requestId}_received`,
      type: 'appointment',
      title: 'Request received',
      body: when
        ? `${apptLabel(d)} requested for ${fmtWhen(when, tz)}. We'll confirm shortly.`
        : `Your ${apptLabel(d).toLowerCase()} request is in. We'll confirm shortly.`,
      route: ROUTES.appointments,
      params: { requestId: ctx.params.requestId },
      refPath: snap.ref.path,
    });
  });

exports.onRequestUpdated = functions
  .region(REGION)
  .firestore.document('requests/{requestId}')
  .onUpdate(async (change, ctx) => {
    const before = change.before.data() || {};
    const after = change.after.data() || {};
    const uid = after.userId;
    if (!uid) return; // cancellation nulls userId; handled by cancelled_appointments
    const id = ctx.params.requestId;
    const tz = isValidTz(after.timezone) ? after.timezone : await tzForUid(uid);
    const when = appointmentInstant(after.appointmentDate, after.appointmentTime, tz);
    const status = statusChanged(before, after);

    // Reschedule: the member's own reschedule keeps status 'pending' but
    // moves the date/time. Confirm we saw it.
    const moved =
      before.appointmentDate !== after.appointmentDate ||
      before.appointmentTime !== after.appointmentTime;
    if (moved && (status === null || status === 'pending')) {
      // Fresh reminders for the new time.
      await change.after.ref.set({ reminders: { h24: false, h1: false } }, { merge: true });
      await notify(uid, {
        id: `request_${id}_moved_${after.appointmentDate}_${after.appointmentTime}`,
        type: 'appointment',
        title: 'Reschedule received',
        body: when
          ? `New time requested: ${fmtWhen(when, tz)}. We'll confirm shortly.`
          : 'Your new time is in. We\'ll confirm shortly.',
        route: ROUTES.appointments,
        params: { requestId: id },
        refPath: change.after.ref.path,
      });
      if (!status) return;
    }
    if (!status) return;

    let title = null;
    let body = null;
    if (status === 'confirmed' || status === 'scheduled' || status === 'booked') {
      title = 'Appointment confirmed';
      body = when ? `You're booked for ${fmtWhen(when, tz)}.` : 'Your appointment is on the calendar.';
    } else if (status === 'rescheduled') {
      title = 'Appointment rescheduled';
      body = when ? `New time: ${fmtWhen(when, tz)}.` : 'Open your appointments for the new time.';
    } else if (status === 'completed') {
      title = 'Visit complete';
      body = 'Your visit record is ready in Care Records.';
    } else if (status === 'no_show' || status === 'missed') {
      title = 'Missed appointment';
      body = 'Looks like the visit didn\'t happen. Tap to book another time.';
    } else if (status === 'cancelled' || status === 'canceled' || status === 'declined') {
      title = 'Appointment cancelled';
      body = when ? `Your ${fmtWhen(when, tz)} appointment was cancelled.` : 'Your appointment was cancelled.';
    }
    if (!title) return;
    await notify(uid, {
      id: `request_${id}_${status}`,
      type: 'appointment',
      title,
      body,
      route: status === 'completed' ? ROUTES.careRecords : ROUTES.appointments,
      params: { requestId: id },
      refPath: change.after.ref.path,
    });
  });

exports.onAppointmentCancelled = functions
  .region(REGION)
  .firestore.document('cancelled_appointments/{cancelId}')
  .onCreate(async (snap, ctx) => {
    const d = snap.data() || {};
    const uid = d.userId;
    if (!uid) return;
    const tz = isValidTz(d.timezone) ? d.timezone : await tzForUid(uid);
    const when = appointmentInstant(d.appointmentDate, d.appointmentTime, tz);
    const byMember = lower(d.cancelledBy) === 'user' || lower(d.cancelledBy) === 'member';
    await notify(uid, {
      id: `cancel_${ctx.params.cancelId}`,
      type: 'appointment',
      title: byMember ? 'Appointment cancelled' : 'Appointment cancelled by the clinic',
      body: (when ? `Your ${fmtWhen(when, tz)} ${apptLabel(d).toLowerCase()} is cancelled.` : 'Your appointment is cancelled.') +
        (d.wasPriority ? ' Your Jovi Pass fee is non-refundable.' : ' Tap to book a new time.'),
      route: ROUTES.appointments,
      params: { requestId: d.originalAppointmentId || '' },
      refPath: snap.ref.path,
    });
  });

/// 24-hour and 1-hour reminders. Runs every 15 minutes; each request doc
/// records what was sent under `reminders` so nothing fires twice.
exports.appointmentReminders = functions
  .region(REGION)
  .pubsub.schedule('every 15 minutes synchronized')
  .onRun(async () => {
    // Members span every US zone, so pull yesterday through the day after
    // tomorrow (UTC) and decide per request in its own zone.
    const dayStrs = [];
    for (const off of [-1, 0, 1, 2]) {
      const s = localDayString(off, 'UTC');
      dayStrs.push(`${s}T00:00:00`, s);
    }
    const snap = await db().collection('requests').where('appointmentDate', 'in', dayStrs).get();
    const now = Date.now();
    let sent = 0;
    for (const doc of snap.docs) {
      const d = doc.data();
      if (!d.userId || !ACTIVE_APPT.has(lower(d.status))) continue;
      const tz = isValidTz(d.timezone) ? d.timezone : await tzForUid(d.userId);
      const when = appointmentInstant(d.appointmentDate, d.appointmentTime, tz);
      if (!when) continue;
      const mins = (when.getTime() - now) / 60000;
      const r = d.reminders || {};
      let key = null;
      let title = null;
      if (!r.h24 && mins <= 24 * 60 && mins > 23 * 60) {
        key = 'h24';
        title = 'Appointment tomorrow';
      } else if (!r.h1 && mins <= 60 && mins > 0) {
        key = 'h1';
        title = 'Appointment in about an hour';
      }
      if (!key) continue;
      try {
        await notify(d.userId, {
          id: `request_${doc.id}_${key}`,
          type: 'appointment',
          title,
          body: `${apptLabel(d)} at ${fmtWhen(when, tz)}${d.clinic ? ` · ${d.clinic}` : ''}.`,
          route: ROUTES.appointments,
          params: { requestId: doc.id },
          refPath: doc.ref.path,
        });
        await doc.ref.set({ reminders: { ...r, [key]: true } }, { merge: true });
        sent += 1;
      } catch (err) {
        functions.logger.error(`appointmentReminders: ${doc.ref.path}`, err);
      }
    }
    functions.logger.info(`appointmentReminders: sent ${sent} of ${snap.size} candidates`);
    return null;
  });

// ─────────────────────────────────────────────────────────────────────
// CLAIMS — users/{uid}/claims/{id} and users/{uid}/pets/{petId}/claims/{id}
// ─────────────────────────────────────────────────────────────────────

const CLAIM_COPY = {
  under_review: ['Claim under review', 'Our team is reviewing your claim.'],
  processing: ['Claim under review', 'Our team is reviewing your claim.'],
  in_progress: ['Claim under review', 'Our team is reviewing your claim.'],
  needs_more_info: ['We need a bit more for your claim', 'Open the claim to see what is missing.'],
  approved: ['Claim approved', 'Your reimbursement is on its way.'],
  paid: ['Reimbursement sent', 'Your claim has been paid out.'],
  rejected: ['Claim decision', 'This claim was not covered. Open it to see why.'],
  denied: ['Claim decision', 'This claim was not covered. Open it to see why.'],
};

exports.onHumanClaimCreated = functions
  .region(REGION)
  .firestore.document('users/{uid}/claims/{claimId}')
  .onCreate(async (snap, ctx) => {
    const d = snap.data() || {};
    if (lower(d.status) === 'draft') return;
    const amt = money(Number(d.amount));
    await notify(ctx.params.uid, {
      id: `claim_${ctx.params.claimId}_received`,
      type: 'claim',
      title: 'Claim received',
      body: `${amt ? `Your ${amt} claim` : 'Your claim'} is in. Most are reviewed within 3 to 5 business days.`,
      route: ROUTES.claims,
      params: { claimId: ctx.params.claimId },
      refPath: snap.ref.path,
    });
  });

exports.onPetClaimCreated = functions
  .region(REGION)
  .firestore.document('users/{uid}/pets/{petId}/claims/{claimId}')
  .onCreate(async (snap, ctx) => {
    const d = snap.data() || {};
    if (lower(d.status) === 'draft') return;
    const amt = money(Number(d.amount));
    await notify(ctx.params.uid, {
      id: `petclaim_${ctx.params.claimId}_received`,
      type: 'pet_claim',
      title: `Claim received${d.petName ? ` for ${d.petName}` : ''}`,
      body: `${amt ? `Your ${amt} claim` : 'Your claim'} is in. Most are reviewed within 3 to 5 business days.`,
      route: ROUTES.petClaims,
      params: { petId: ctx.params.petId, claimId: ctx.params.claimId },
      refPath: snap.ref.path,
    });
  });

exports.onHumanClaimUpdated = functions
  .region(REGION)
  .firestore.document('users/{uid}/claims/{claimId}')
  .onUpdate(async (change, ctx) => {
    const status = statusChanged(change.before.data(), change.after.data());
    if (!status) return;
    const copy = CLAIM_COPY[status];
    if (!copy) return;
    await notify(ctx.params.uid, {
      id: `claim_${ctx.params.claimId}_${status}`,
      type: 'claim',
      title: copy[0],
      body: copy[1],
      route: ROUTES.claims,
      params: { claimId: ctx.params.claimId },
      refPath: change.after.ref.path,
    });
  });

exports.onPetClaimUpdated = functions
  .region(REGION)
  .firestore.document('users/{uid}/pets/{petId}/claims/{claimId}')
  .onUpdate(async (change, ctx) => {
    const after = change.after.data() || {};
    const status = statusChanged(change.before.data(), after);
    if (!status) return;
    const copy = CLAIM_COPY[status];
    if (!copy) return;
    await notify(ctx.params.uid, {
      id: `petclaim_${ctx.params.claimId}_${status}`,
      type: 'pet_claim',
      title: `${copy[0]}${after.petName ? ` for ${after.petName}` : ''}`,
      body: copy[1],
      route: ROUTES.petClaims,
      params: { petId: ctx.params.petId, claimId: ctx.params.claimId },
      refPath: change.after.ref.path,
    });
  });

// ─────────────────────────────────────────────────────────────────────
// BILLING — payment_logs (PayArc webhook), users/{uid} state, daily sweep
// ─────────────────────────────────────────────────────────────────────

exports.onPaymentLogged = functions
  .region(REGION)
  .firestore.document('payment_logs/{logId}')
  .onCreate(async (snap, ctx) => {
    const d = snap.data() || {};
    const uid = d.userId;
    if (!uid) return;
    const amt = money(Number(d.amount));
    const ok = lower(d.status) === 'success' || lower(d.status) === 'succeeded';
    if (ok) {
      const user = (await db().collection('users').doc(uid).get()).data() || {};
      const tz = tzForUserData(user);
      const next = toDate(user.nextBillingDate);
      await notify(uid, {
        id: `payment_${ctx.params.logId}`,
        type: 'payment',
        title: amt ? `Payment received, ${amt}` : 'Payment received',
        body: next ? `Thanks. Your next payment is ${fmtDay(next, tz)}.` : 'Thanks. Your membership is current.',
        route: ROUTES.billing,
        params: {},
        refPath: snap.ref.path,
      });
    } else {
      const attempt = Number(d.attemptNumber) || 1;
      await notify(uid, {
        id: `payment_${ctx.params.logId}`,
        type: 'payment',
        title: 'Payment didn’t go through',
        body: `${amt ? `Your ${amt} payment` : 'Your payment'} failed${d.reason ? ` (${d.reason})` : ''}. ` +
          (attempt >= 3
            ? 'Your membership is paused until a payment succeeds. Update your card now.'
            : 'Update your card to keep your membership active. We\'ll retry.'),
        route: ROUTES.billing,
        params: {},
        refPath: snap.ref.path,
      });
    }
  });

exports.onMembershipChanged = functions
  .region(REGION)
  .firestore.document('users/{uid}')
  .onUpdate(async (change, ctx) => {
    const uid = ctx.params.uid;
    const b = change.before.data() || {};
    const a = change.after.data() || {};
    const tz = tzForUserData(a);
    const jobs = [];

    // Subscription state machine (PayArc webhook + cancelMembership + Keep).
    const sb = lower(b.subscriptionStatus);
    const sa = lower(a.subscriptionStatus);
    if (sb !== sa) {
      const end = toDate(a.willCancelOn || a.finalBillingDate);
      if (sa === 'canceling') {
        jobs.push({
          id: `membership_canceling_${dayKey(new Date())}`,
          type: 'membership',
          title: 'Cancellation scheduled',
          body: end ? `Coverage continues until ${fmtDay(end, tz)}. Change your mind any time before then.` : 'Coverage continues until the end of your billing period.',
          route: ROUTES.planDetails,
        });
      } else if (sa === 'canceled' || sa === 'cancelled') {
        jobs.push({
          id: `membership_canceled_${dayKey(new Date())}`,
          type: 'membership',
          title: 'Membership ended',
          body: 'Your Jovi membership has ended. Reach out any time if you\'d like to rejoin.',
          route: ROUTES.planDetails,
        });
      } else if (sa === 'suspended') {
        jobs.push({
          id: `membership_suspended_${dayKey(new Date())}`,
          type: 'payment',
          title: 'Membership paused',
          body: 'Three payments have failed, so coverage is paused. Update your card to restore it.',
          route: ROUTES.billing,
        });
      } else if (sa === 'active' && (sb === 'canceling' || sb === 'past_due' || sb === 'suspended')) {
        jobs.push({
          id: `membership_active_${dayKey(new Date())}`,
          type: 'membership',
          title: sb === 'canceling' ? 'Membership kept' : 'Membership restored',
          body: sb === 'canceling'
            ? 'Your cancellation was reversed. Everything renews as usual.'
            : 'Payment went through and your coverage is active again.',
          route: ROUTES.planDetails,
        });
      }
    }

    // Annual renewal processed: renew date moved forward.
    const rb = toDate(b.renew);
    const ra = toDate(a.renew);
    if (ra && (!rb || ra.getTime() > rb.getTime() + 86400000)) {
      jobs.push({
        id: `renewed_${dayKey(ra)}`,
        type: 'membership',
        title: 'Membership renewed',
        body: `You're covered through ${fmtDay(ra, tz)}.`,
        route: ROUTES.planDetails,
      });
    }

    // Card-on-file status written by the Billing widget contract (Zoho later).
    const cb = lower(b.lastChargeStatus);
    const ca = lower(a.lastChargeStatus);
    if (cb !== ca && (ca === 'failed' || ca === 'past_due' || ca === 'declined')) {
      jobs.push({
        id: `charge_${ca}_${dayKey(new Date())}`,
        type: 'payment',
        title: 'Payment didn’t go through',
        body: 'Update your card to keep your membership active.',
        route: ROUTES.billing,
      });
    }

    for (const j of jobs) {
      await notifyOnce(uid, { ...j, params: {}, refPath: change.after.ref.path });
    }
  });

/// Upcoming monthly debit (3 days out) and annual renewal (30 / 7 / 1 days
/// out), delivered at 9 am in each member's own zone: the job runs every
/// hour and only acts for members whose local hour is 9. notifyOnce keeps
/// reruns silent. Skips cancelling, cancelled, suspended or inactive accounts.
exports.billingReminders = functions
  .region(REGION)
  .runWith({ timeoutSeconds: 300, memory: '256MB' })
  .pubsub.schedule('every 1 hours synchronized')
  .onRun(async () => {
    const hourIn = (tz) => Number(new Intl.DateTimeFormat('en-US', {
      timeZone: tz, hour: 'numeric', hourCycle: 'h23',
    }).format(new Date()));
    let last = null;
    let sent = 0;
    for (;;) {
      let q = db().collection('users').orderBy(admin.firestore.FieldPath.documentId()).limit(300);
      if (last) q = q.startAfter(last);
      const snap = await q.get();
      if (snap.empty) break;
      for (const doc of snap.docs) {
        const u = doc.data() || {};
        const sub = lower(u.subscriptionStatus);
        if (u.isActive === false || lower(u.membershipStatus) === 'inactive') continue;
        if (sub === 'canceling' || sub === 'canceled' || sub === 'cancelled' || sub === 'suspended') continue;
        if (!u.renew && !u.nextBillingDate) continue; // never completed onboarding
        const tz = tzForUserData(u);
        if (hourIn(tz) !== 9) continue;
        const targets = {
          debit: localDayString(3, tz),
          renew30: localDayString(30, tz),
          renew7: localDayString(7, tz),
          renew1: localDayString(1, tz),
        };
        try {
          // Monthly debit, 3 days ahead.
          let next = toDate(u.nextBillingDate);
          const renew = toDate(u.renew);
          if (!next && renew) {
            // Anniversary-day fallback, same rule as the Billing widget.
            const today = localDayStart(localDayString(0, tz), tz);
            const y = today.getUTCFullYear();
            const m = today.getUTCMonth();
            const day = renew.getUTCDate();
            let cand = new Date(Date.UTC(y, m, Math.min(day, new Date(Date.UTC(y, m + 1, 0)).getUTCDate())));
            if (cand.getTime() <= today.getTime()) {
              cand = new Date(Date.UTC(y, m + 1, Math.min(day, new Date(Date.UTC(y, m + 2, 0)).getUTCDate())));
            }
            next = cand;
          }
          if (next && dayIn(next, tz) === targets.debit) {
            const amt = money(userMonthlyTotal(u));
            const card = u.cardLast4 ? ` to your card ending ${u.cardLast4}` : (u.paymentCard ? ` to your card ending ${String(u.paymentCard).slice(-4)}` : '');
            if (await notifyOnce(doc.id, {
              id: `debit_${dayKey(next)}`,
              type: 'payment',
              title: amt ? `${amt} payment on ${fmtDay(next, tz)}` : `Membership payment on ${fmtDay(next, tz)}`,
              body: `Your monthly Jovi payment will be charged${card} in 3 days. Nothing to do unless your card has changed.`,
              route: ROUTES.billing,
              params: {},
              refPath: doc.ref.path,
            })) sent += 1;
          }
          // Annual renewal.
          if (renew) {
            const rk = dayIn(renew, tz);
            const daysOut = rk === targets.renew30 ? 30 : rk === targets.renew7 ? 7 : rk === targets.renew1 ? 1 : 0;
            if (daysOut) {
              if (await notifyOnce(doc.id, {
                id: `renewal_${dayKey(renew)}_${daysOut}`,
                type: 'membership',
                title: daysOut === 1 ? 'Membership renews tomorrow' : `Membership renews in ${daysOut} days`,
                body: `Your Jovi membership renews on ${fmtDay(renew, tz)}. Review your plan or update your card before then.`,
                route: ROUTES.planDetails,
                params: {},
                refPath: doc.ref.path,
              })) sent += 1;
            }
          }
        } catch (err) {
          functions.logger.error(`billingReminders: ${doc.id}`, err);
        }
      }
      last = snap.docs[snap.docs.length - 1];
      if (snap.size < 300) break;
    }
    functions.logger.info(`billingReminders: sent ${sent}`);
    return null;
  });

// ─────────────────────────────────────────────────────────────────────
// REFILLS — prescriptionRefills/{id} (top level, userId)
// ─────────────────────────────────────────────────────────────────────

exports.onRefillUpdated = functions
  .region(REGION)
  .firestore.document('prescriptionRefills/{refillId}')
  .onUpdate(async (change, ctx) => {
    const after = change.after.data() || {};
    const status = statusChanged(change.before.data(), after);
    if (!status || !after.userId) return;
    const med = after.medicationName || 'Your prescription';
    const where = after.pharmacyName || after.lastFilledPharmacy;
    let title = null;
    let body = null;
    if (status === 'approved' || status === 'processing' || status === 'in_progress') {
      title = 'Refill approved';
      body = `${med} is being filled${where ? ` at ${where}` : ''}.`;
    } else if (status === 'ready') {
      title = 'Refill ready for pickup';
      body = `${med} is ready${where ? ` at ${where}` : ''}.`;
    } else if (status === 'filled' || status === 'completed') {
      title = 'Refill complete';
      body = `${med} has been filled${where ? ` at ${where}` : ''}.`;
    } else if (status === 'denied' || status === 'rejected') {
      title = 'Refill not approved';
      body = `We couldn't approve the ${med} refill. Open it to see why or to request a visit.`;
    } else if (status === 'cancelled' || status === 'canceled') {
      title = 'Refill cancelled';
      body = `The ${med} refill request was cancelled.`;
    }
    if (!title) return;
    await notify(after.userId, {
      id: `refill_${ctx.params.refillId}_${status}`,
      type: 'refill',
      title,
      body,
      route: ROUTES.refills,
      params: { refillId: ctx.params.refillId },
      refPath: change.after.ref.path,
    });
  });

// ─────────────────────────────────────────────────────────────────────
// SUPPORT — helpTickets/{ticketId}/messages/{messageId}
// ─────────────────────────────────────────────────────────────────────

exports.onSupportMessage = functions
  .region(REGION)
  .firestore.document('helpTickets/{ticketId}/messages/{messageId}')
  .onCreate(async (snap, ctx) => {
    const m = snap.data() || {};
    const ticketSnap = await db().collection('helpTickets').doc(ctx.params.ticketId).get();
    const t = ticketSnap.data() || {};
    const uid = t.userId;
    if (!uid) return;
    if (m.senderId === uid) return; // the member's own message
    if (m.readByUser === true) return;
    const text = String(m.text || '').trim();
    await notify(uid, {
      id: `ticket_${ctx.params.ticketId}_${ctx.params.messageId}`,
      type: 'message',
      title: 'New reply from Jovi support',
      body: text.length > 120 ? `${text.slice(0, 117)}…` : text || 'Tap to read the reply.',
      route: ROUTES.chat,
      params: { ticketId: ctx.params.ticketId },
      refPath: snap.ref.path,
    });
  });

// ─────────────────────────────────────────────────────────────────────
// PETS — weight alerts + medication reminders
// ─────────────────────────────────────────────────────────────────────

exports.onWeightAlertCreated = functions
  .region(REGION)
  .firestore.document('users/{uid}/weight_alerts/{alertId}')
  .onCreate(async (snap, ctx) => {
    const d = snap.data() || {};
    const pet = d.petName || 'Your pet';
    const lbs = typeof d.weightLbs === 'number' ? `${d.weightLbs.toFixed(1)} lbs` : 'a new weight';
    await notify(ctx.params.uid, {
      id: `weight_${ctx.params.alertId}`,
      type: 'weight',
      title: `${pet}’s weight is above range`,
      body: `${lbs} was logged at the vet. Tap to review.`,
      route: ROUTES.weightAlerts,
      params: { petId: d.petId || '', alertId: ctx.params.alertId },
      refPath: snap.ref.path,
    });
  });

exports.fireScheduledReminders = functions
  .region(REGION)
  .runWith({ timeoutSeconds: 120, memory: '256MB' })
  .pubsub.schedule('every 5 minutes synchronized')
  .onRun(async () => {
    const now = admin.firestore.Timestamp.now();
    const snap = await db()
      .collectionGroup('scheduled_reminders')
      .where('fired', '==', false)
      .where('fireAt', '<=', now)
      .limit(200)
      .get();
    if (snap.empty) return null;
    let sent = 0;
    for (const doc of snap.docs) {
      const d = doc.data();
      const uid = uidFromRef(doc.ref);
      if (!uid) continue;
      try {
        await notify(uid, {
          id: `reminder_${doc.id}`,
          // Clinic-scheduled reminders (staff app) set their own type/route; pet meds keep the defaults.
          type: d.type || 'pet_med',
          title: d.title || 'Medication reminder',
          body: d.body || 'Tap to log the dose',
          route: d.route || ROUTES.petMedications,
          params: d.params || { petId: d.petId || '', medicationId: d.medicationId || '' },
          refPath: doc.ref.path,
        });
        await doc.ref.update({ fired: true, firedAt: admin.firestore.FieldValue.serverTimestamp() });
        sent += 1;
      } catch (err) {
        functions.logger.error(`fireScheduledReminders: ${doc.ref.path}`, err);
      }
    }
    functions.logger.info(`fireScheduledReminders: fired ${sent}/${snap.size}`);
    return null;
  });

// ─────────────────────────────────────────────────────────────────────
// VACCINES — boosters due (people: expiresAt, pets: expirationDate)
// ─────────────────────────────────────────────────────────────────────

exports.vaccinationDueSweep = functions
  .region(REGION)
  .runWith({ timeoutSeconds: 300, memory: '256MB' })
  .pubsub.schedule('every 1 hours synchronized')
  .onRun(async () => {
    const windows = [
      { days: 30, label: 'in 30 days' },
      { days: 7, label: 'in a week' },
      { days: 0, label: 'today' },
    ];
    const hourIn = (tz) => Number(new Intl.DateTimeFormat('en-US', {
      timeZone: tz, hour: 'numeric', hourCycle: 'h23',
    }).format(new Date()));
    let sent = 0;
    for (const field of ['expiresAt', 'expirationDate']) {
      for (const w of windows) {
        // A day wide on each side in UTC covers every zone; the owner's
        // zone decides whether it is really "today + N" for them.
        const start = new Date(localDayStart(localDayString(w.days, 'UTC'), 'UTC').getTime() - 86400000);
        const end = new Date(start.getTime() + 3 * 86400000);
        let snap;
        try {
          snap = await db()
            .collectionGroup('vaccinations')
            .where(field, '>=', admin.firestore.Timestamp.fromDate(start))
            .where(field, '<', admin.firestore.Timestamp.fromDate(end))
            .limit(500)
            .get();
        } catch (err) {
          functions.logger.error(`vaccinationDueSweep: query ${field} failed (index missing?)`, err);
          continue;
        }
        for (const doc of snap.docs) {
          const d = doc.data() || {};
          const uid = uidFromRef(doc.ref);
          if (!uid) continue;
          const tz = await tzForUid(uid);
          if (hourIn(tz) !== 9) continue;
          if (dayIn(toDate(d[field]), tz) !== localDayString(w.days, tz)) continue;
          const isPet = field === 'expirationDate';
          let who = d.patientName || '';
          let petId = '';
          if (isPet) {
            const petRef = doc.ref.parent.parent;
            petId = petRef ? petRef.id : '';
            try {
              const pet = petRef ? (await petRef.get()).data() : null;
              who = (pet && pet.name) || 'Your pet';
            } catch (_) {
              who = 'Your pet';
            }
          }
          const vaccine = d.vaccineName || 'A vaccine';
          try {
            if (await notifyOnce(uid, {
              id: `vax_${doc.id}_${w.days}`,
              type: 'vaccine',
              title: w.days === 0 ? `${vaccine} booster due today` : `${vaccine} booster due ${w.label}`,
              body: `${who ? `${who}'s ` : ''}${vaccine} is due on ${fmtDay(toDate(d[field]), tz)}.`,
              route: isPet ? ROUTES.petVaccinations : ROUTES.vaccinations,
              params: isPet ? { petId } : { patientName: who },
              refPath: doc.ref.path,
            })) sent += 1;
          } catch (err) {
            functions.logger.error(`vaccinationDueSweep: ${doc.ref.path}`, err);
          }
        }
      }
    }
    functions.logger.info(`vaccinationDueSweep: sent ${sent}`);
    return null;
  });

// functions-dashboard/showcase.js
// Build ID: JC-LAZO-FNDASH-0913-019
//
// REAL WEDDINGS. A vendor can mark a delivered gallery as a showcase: it gets
// a public, indexable page at meetlazo.com/real/{slug} (worker SHOWCASE-001)
// and a strip on their public vendor page. Nothing else about the gallery
// changes - the couple's private /g/{slug} stays behind its passcode; only
// the thumb/web sizes become readable without one, never the full-size
// downloads.
//
//   galleryShowcase  callable {vendorId, slug, on, consent}
//     on=true requires consent=true (the vendor confirms the couple agreed).
//     Writes galleries/{slug}.showcase / showcaseAt / showcaseConsentBy and a
//     denormalised card on vendors/{id}.showcases[] for the public page.
'use strict';
const { onCall, HttpsError } = require('firebase-functions/v2/https');
const admin = require('firebase-admin');
const db = () => admin.firestore();
const { FieldValue } = admin.firestore;
const str = (v) => (v == null ? '' : String(v));

module.exports = function showcaseModule() {
  const galleryShowcase = onCall({ memory: '256MiB' }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const d = request.data || {};
    const vendorId = str(d.vendorId), slug = str(d.slug).toLowerCase();
    if (!vendorId || !/^[a-z0-9-]{1,80}$/.test(slug)) throw new HttpsError('invalid-argument', 'vendorId and slug required');
    const [vs, us, gs] = await Promise.all([
      db().collection('vendors').doc(vendorId).get(),
      db().collection('users').doc(uid).get(),
      db().collection('galleries').doc(slug).get(),
    ]);
    if (!vs.exists) throw new HttpsError('not-found', 'Vendor not found.');
    const ok = str(vs.get('claimedBy')) === uid || (us.exists && str(us.get('vendorId')) === vendorId && str(us.get('vendorRole')) === 'manager');
    if (!ok) throw new HttpsError('permission-denied', 'Not your vendor.');
    if (!gs.exists || str(gs.get('vendorId')) !== vendorId) throw new HttpsError('not-found', 'Gallery not found on this account.');
    if (str(gs.get('status')) !== 'live') throw new HttpsError('failed-precondition', 'Only a delivered (live) gallery can be shown.');
    const on = d.on === true;
    if (on && d.consent !== true) throw new HttpsError('failed-precondition', 'Confirm the couple agreed to be featured.');

    await gs.ref.set(on
      ? { showcase: true, showcaseAt: FieldValue.serverTimestamp(), showcaseConsentBy: uid, showcaseTitle: str(d.title).slice(0, 80) || str(gs.get('names')), showcaseBlurb: str(d.blurb).slice(0, 240) }
      : { showcase: false, showcaseOffAt: FieldValue.serverTimestamp() }, { merge: true });

    // denormalise the vendor's live showcases for the public page (max 12, newest first)
    const q = await db().collection('galleries').where('vendorId', '==', vendorId).where('showcase', '==', true).get();
    const cards = q.docs.map((g) => ({
      slug: g.id, title: str(g.get('showcaseTitle')) || str(g.get('names')), blurb: str(g.get('showcaseBlurb')),
      dateIso: str(g.get('dateIso')), coverId: str(g.get('coverId')), photoCount: g.get('photoCount') || 0,
      at: (g.get('showcaseAt') && g.get('showcaseAt').toMillis) ? g.get('showcaseAt').toMillis() : 0,
    })).sort((a, b) => b.at - a.at).slice(0, 12).map(({ at, ...rest }) => rest);
    await vs.ref.set({ showcases: cards, showcaseCount: cards.length }, { merge: true });
    return { ok: true, on, count: cards.length };
  });
  return { galleryShowcase };
};
// END OF FILE - JC-LAZO-FNDASH-0913-019

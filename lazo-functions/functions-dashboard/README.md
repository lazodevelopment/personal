# Lazo dashboard backend — JC-LAZO-FNDASH-0906-002

Pairs with vendor widget **JC-LAZO-VDASH-0906-151**. Nothing here touches `functions/index.js`
(the Whop build); this is a second Firebase codebase that deploys on its own.

## 1. Install the codebase

Copy the `functions-dashboard/` folder into `C:\Users\kurvh\lazo-functions\` next to `functions\`,
then add it to `firebase.json` (keep your existing `functions` entry exactly as it is; the file
becomes an array):

```json
{
  "functions": [
    { "source": "functions", "codebase": "default" },
    { "source": "functions-dashboard", "codebase": "dashboard", "runtime": "nodejs22" }
  ]
}
```

If your existing entry has extra keys (`predeploy`, `ignore`), keep them on the first object.

```powershell
cd C:\Users\kurvh\lazo-functions\functions-dashboard
npm install
cd ..
firebase deploy --only functions:dashboard
```

Secrets: it reuses the project's existing `RESEND_API_KEY` (Firebase grants access at deploy).
If Firebase's automatic public-invoker grant fails again for the two `onRequest` functions
(`pulse`, `vendorCalendar`), grant `allUsers` → Cloud Run Invoker on those services, same as before.

## 2. Firestore rules (add to firestore_rules_v2)

```
// v151: team invites — the vendor owner creates and reads them; the callable redeems them
match /vendorInvites/{inviteId} {
  allow create: if request.auth != null
    && request.resource.data.createdBy == request.auth.uid
    && request.resource.data.status == 'pending';
  allow read, update: if request.auth != null && resource.data.createdBy == request.auth.uid;
}
// v151/couple v91: metro benchmarks and price ranges — any signed-in user can read
match /metroStats/{key} {
  allow read: if request.auth != null;
}
// couple v91: partner invites, same shape as team invites
match /coupleInvites/{inviteId} {
  allow create: if request.auth != null
    && request.resource.data.createdBy == request.auth.uid
    && request.resource.data.status == 'pending';
  allow read, update: if request.auth != null && resource.data.createdBy == request.auth.uid;
}
// couple v91: a partner who joined through an invite reads and writes the
// inviter's couple doc, its plan, and the inquiries keyed to it. Wherever your
// rules today say `request.auth.uid == coupleId` (couples/{id} and its
// subcollections) or `resource.data.coupleUid == request.auth.uid` (inquiries),
// extend the condition with:
//   || get(/databases/$(database)/documents/users/$(request.auth.uid)).data.coupleUid == <that id>
// v151: beacon counters — server only
match /vendorPulse/{vendorId}/{document=**} {
  allow read, write: if false;
}
```

`vendors.{savedReplies, calendarToken, dailyBrief}` and `inquiries.status = 'lost'` ride on the
existing owner rules; nothing new needed there.

## 3. Vendor page template — the beacon

Already in `vendor.html` v2 (JC-LAZO-VPAGE-0906-002): the `.vp` section carries
`data-vendor-id` and the page sends the beacon itself. Nothing to add. The hero's *Profile views*
tile appears the morning after the first beacon lands (`nightlyVendorStats` writes
`vendors.views` at 03:15 Phoenix).

## 4. Lead SMS deep link

Done in `functions/index.js` (JC-LAZO-SMS-0906-001): the Telnyx lead text now ends with
`https://app.meetlazo.com/dashboard?thread=<inquiryId>` and names the couple when known.
Deploy with your normal `firebase deploy --only functions` (default codebase).

## 5. Close the loop — couple app contract (couple widget, not yet patched)

When a couple ends a conversation in the couple dashboard, write on `inquiries/{id}`:

```
status: 'lost', lostReason: 'price' | 'date' | 'style' | 'booked elsewhere' | 'other',
lostNote: <free text, optional>, lostAt: serverTimestamp()
```

The vendor dashboard already shows "Went another direction · Reason: …" on the thread, in the
inbox rail, and in the context column. Send me the couple widget (v90) and I'll add the sheet.

## 6. What the nightly job writes (002: rank matches build.py - every category a vendor holds, 65 prior, lowercase names)

- `vendors/{id}.views` — `{ d7, d7Prev, src: {search, lazo, social, direct, other, ...}, updatedAt }`
- `vendors/{id}.badges` — any of `verified`, `offer`, `quick_responder` (≥80% answered within
  24h over the last 90 days, min 3 inquiries), `recently_updated` (profile edited in 15 days),
  `popular` (5+ inquiries in 7 days)
- `vendors/{id}.rank` — `{ pos, of, label }`, position on the vendor's metro + primary-category
  page, ordered score → reviews → name. **If `build.py` orders those pages differently, tell me
  the sort and I'll match it — the number on the dashboard must be the number on the site.**
- `metroStats/{metro__category}` — `{ medianReplyMin, repliesSampled, medianInquiries30d, vendors }`

Only claimed vendors get written; ranks are computed across everyone.

## 7. Public card, per-vendor publish

- Badges and everything else the editor can change are on the public page now: `vendor.html` v2
  renders `vendors.badges` as pills in the hero, and its live hydration covers every editable
  field, so a saved profile is on meetlazo.com within seconds. The nightly build still rebuilds
  the static copy for search engines. (The editor's "next daily publish" toast is now wrong — fixed
  in the next widget build.)
- Rank stays off the public page on purpose. Vendors see it in the dashboard; couples see the
  ordered category page, which is the same thing.
- Couple widget: close-the-loop sheet (section 5) lands with the couple dashboard refresh.

## 8. Endpoints

- `POST https://us-central1-lazo-513ec.cloudfunctions.net/pulse` — beacon
- `GET  https://us-central1-lazo-513ec.cloudfunctions.net/vendorCalendar?v=<vendorId>&t=<calendarToken>` — ICS
- callable `redeemVendorInvite({ code })`
- schedules: `nightlyVendorStats` 03:15 America/Phoenix, `morningBrief` hourly at :05 UTC
  (sends at 7am in the vendor's metro time zone, only when there is something to say)

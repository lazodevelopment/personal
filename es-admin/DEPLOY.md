# Elizabeth Scott admin dashboard (admin.elizabethscottweddings.com)

Rebuilt 2026-09-26 from C:\Users\kurvh\atavia-admin (same three no-build pages + apple.css/apple.js), re-skinned navy/gold
and pointed at the elizabeth-scott-738e5 Firebase project. To re-clone after Atavia changes, run C:/Users/kurvh/es-admin-clone.py (kept outside this folder because everything here ships live).
It re-applies colours, fonts, wordmark, Firebase config and admin emails.

Deploy (PowerShell; wrangler logged in as info@ataviaweddings.com, which owns the elizabethscott-admin Pages project):
    cd C:\Users\kurvh\es-admin
    npx wrangler pages deploy . --project-name=elizabethscott-admin

Verify by content-type, not status (the catch-all returns 200 HTML for any missing file):
    curl -sI https://admin.elizabethscottweddings.com/apple.css   ->  Content-Type: text/css

Firebase (elizabeth-scott-738e5): security rules live in C:/Users/kurvh/es-firebase (firestore.rules, storage.rules,
firebase.json). Deploy with `firebase login --reauth` then `firebase deploy --only firestore:rules,storage` from that folder.
The Visitors page needs the sessions + collection-group hits rules from there.

Site side: es-site/assets/js/esw-track.js (ported from atv-track.js, bot gate) + es-site/functions/api/geo.js (bot verdict)
are loaded by every generated page via _src/build.py and by the four hand-maintained pages. Append ?demo to any admin page
for an authless render with mock data.

"""Nav items for the new pages, idle timeout, exam-room mode, kiosk CSS, rules, storage rules, functions exports."""
import pathlib, shutil, json
R = pathlib.Path(__file__).resolve().parent.parent

def patch(path, pairs):
    p = R / path; t = p.read_text(encoding="utf-8")
    for a, b in pairs:
        assert t.count(a) == 1, (path, a[:70], t.count(a)); t = t.replace(a, b)
    p.write_text(t, encoding="utf-8", newline="\n"); print("patched", path)

patch("assets/js/app.js", [
    ("      ['/ehr/tasks', 'Tasks', I.log],\n    ]],",
     "      ['/ehr/tasks', 'Tasks', I.log],\n      ['/ehr/caregaps', 'Care gaps', I.shield],\n    ]],"),
    ("      ['/ehr/messages', 'Messages', I.chat],\n    ]],",
     "      ['/ehr/messages', 'Messages', I.chat],\n      ['/ehr/orders', 'Orders & results', I.lab],\n      ['/ehr/fax', 'Fax', I.folder],\n    ]],"),
    ("      ['/ehr/records', 'Care records', I.folder],\n    ]],",
     "      ['/ehr/records', 'Care records', I.folder],\n      ['/ehr/templates', 'Templates & phrases', I.log],\n    ]],"),
    # idle timeout (HIPAA): sign out after 15 minutes without input; warn at 14.
    ("  if (!stopCounts) stopCounts = watchCounts(c => { counts = c; renderSidebar(); });",
     """  if (!stopCounts) stopCounts = watchCounts(c => { counts = c; renderSidebar(); });
  startIdleTimer();
  document.addEventListener('keydown', e => { if (e.key === 'F11' || (e.altKey && e.key.toLowerCase() === 'k')) { e.preventDefault(); toggleKiosk(); } });"""),
    ("onSession(s => {",
     """// ── Idle timeout & exam-room mode ──────────────────────────────────────
const IDLE_MS = 15 * 60 * 1000; let idleT = null, warnT = null, warned = null;
function startIdleTimer() {
  const reset = () => { clearTimeout(idleT); clearTimeout(warnT); if (warned) { warned.remove(); warned = null; }
    warnT = setTimeout(() => { warned = h('div', { class: 'toast toast-error in', style: { position: 'fixed', left: '50%', bottom: '22px', transform: 'translateX(-50%)', zIndex: 95 } }, 'Signing out in 60 seconds due to inactivity. Move the mouse to stay signed in.'); document.body.append(warned); }, IDLE_MS - 60000);
    idleT = setTimeout(() => { logOut(); toast('Signed out after 15 minutes of inactivity', 'info', 8000); }, IDLE_MS); };
  ['pointerdown', 'keydown', 'scroll', 'touchstart'].forEach(ev => document.addEventListener(ev, reset, { passive: true })); reset();
}
export function toggleKiosk(on) { const k = on == null ? !document.body.classList.contains('kiosk') : on; document.body.classList.toggle('kiosk', k); toast(k ? 'Exam room mode on (Alt+K to exit)' : 'Exam room mode off', 'info'); }
window.joviKiosk = toggleKiosk;

onSession(s => {"""),
])

R.joinpath("assets/css/admin.css").open("a", encoding="utf-8", newline="\n").write("""
/* Exam-room (kiosk) mode: chart fills the screen on a tablet */
body.kiosk .sidebar,body.kiosk .topbar{display:none!important}
body.kiosk .shell{grid-template-columns:1fr}
body.kiosk .content{padding:12px}
body.kiosk .chart-banner{border-radius:10px}
.scribe-rec{display:inline-flex;align-items:center;gap:8px;font-weight:600}
.scribe-rec .dot{width:10px;height:10px;border-radius:50%;background:var(--red);animation:pulse 1s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
""")
print("css ok")

# Rules: new collections
p = R / "firestore.rules"; t = p.read_text(encoding="utf-8")
old = "    match /clinical_tasks/{id} { allow read, write: if clinical() || businessWrite(); }\n"
new = old + """    match /note_templates/{id} { allow read: if isStaff(); allow write: if chartWrite(); }
    match /smart_phrases/{id} { allow read: if isStaff(); allow write: if chartWrite(); }
    match /schedule_blocks/{id} { allow read: if isStaff(); allow write: if chartWrite() || businessWrite(); }
    match /waitlist/{id} { allow read: if isStaff(); allow write: if chartWrite() || businessWrite(); }
    match /orders/{id} { allow read: if clinical(); allow create, update: if chartWrite(); }
    match /fax_outbox/{id} { allow read: if clinical(); allow create, update: if chartWrite(); }
    match /fax_inbox/{id} { allow read: if clinical(); allow update: if chartWrite(); }
"""
assert t.count(old) == 1; t = t.replace(old, new)
old2 = "    match /{path=**}/visit_records/{id} { allow read: if clinical(); }\n"
assert t.count(old2) == 1; t = t.replace(old2, old2 + "    match /{path=**}/lab_results/{id} { allow read: if clinical(); }\n")
p.write_text(t, encoding="utf-8", newline="\n"); print("rules ok")

# Storage rules (proposed): staff may read member files and write chart uploads; scribe audio is private to the recorder.
(R / "storage.rules").write_text("""rules_version = '2';
// Proposed Storage rules adding staff access. Merge with the live rules (FlutterFlow's default is usually
// "allow read, write: if request.auth != null"); keep member-side rules as they are.
service firebase.storage {
  match /b/{bucket}/o {
    function signedIn() { return request.auth != null; }
    function isStaff() { return signedIn() && firestore.exists(/databases/(default)/documents/staff/$(request.auth.uid)); }
    match /scribe/{uid}/{file} { allow read, write: if signedIn() && request.auth.uid == uid; }
    match /users/{uid}/{allPaths=**} { allow read: if signedIn() && (request.auth.uid == uid || isStaff()); allow write: if signedIn() && (request.auth.uid == uid || isStaff()); }
    match /uploads/{uid}/{allPaths=**} { allow read: if signedIn() && (request.auth.uid == uid || isStaff()); allow write: if signedIn() && request.auth.uid == uid; }
    match /pet_photos/{uid}/{allPaths=**} { allow read: if signedIn(); allow write: if signedIn() && request.auth.uid == uid; }
    match /request_photos/{file} { allow read: if signedIn(); allow write: if signedIn(); }
    match /helpTickets/{ticketId}/{allPaths=**} { allow read, write: if signedIn(); }
    match /{allPaths=**} { allow read, write: if signedIn(); }
  }
}
""", encoding="utf-8", newline="\n"); print("storage rules ok")

# Functions: copy into kurv-functions and export
KF = pathlib.Path("C:/Users/kurvh/kurv-functions")
for f in ["scribe.js", "orders.js", "fax.js", "fhir.js"]:
    shutil.copy(R / "functions" / f, KF / f)
idx = KF / "index.js"; t = idx.read_text(encoding="utf-8")
if "require('./scribe')" not in t:
    t = t.rstrip("\n") + """

// ── Staff app (jovi-admin) functions ─────────────────────────────────────
exports.scribe = require('./scribe').scribe;
Object.assign(exports, require('./orders'));   // transmitOrder, labResultsWebhook
Object.assign(exports, require('./fax'));      // sendFax, faxInboundWebhook
exports.fhir = require('./fhir').fhir;
"""
    idx.write_text(t, encoding="utf-8", newline="\n"); print("index.js exports added")
fj = KF / "firebase.json"; j = json.loads(fj.read_text(encoding="utf-8"))
j["storage"] = {"rules": "storage.rules"}
fj.write_text(json.dumps(j, indent=2), encoding="utf-8"); shutil.copy(R / "storage.rules", KF / "storage.rules"); shutil.copy(R / "firestore.rules", KF / "firestore.rules")
print("kurv-functions staged")

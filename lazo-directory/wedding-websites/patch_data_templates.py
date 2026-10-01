"""patch_data_templates.py - JC-LAZO-WWS-0930-DATA
Guest-facing reads leave Firestore and go through the worker, which checks the
passcode and returns only what the page needs:
  guestbook list  -> GET /api/w/{slug}/guestbook      (same {documents} shape)
  chapters list   -> GET /api/w/{slug}/chapters
  invite by token -> GET /api/w/{slug}/invite/{token} ({fields})
  seat finder     -> GET /api/w/{slug}/seat?q=name    (matches only)
  room map        -> GET /api/w/{slug}/room           (tables, no names)
Writes (RSVP, guestbook note) still go to Firestore; the rules validate them.
Applies to _base.html and every built template. Idempotent.
  python wedding-websites\\patch_data_templates.py
Then: python wedding-websites\\sync_dist.py; python deploy\\upload_r2.py --prefix wedding-websites
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = '"/api/w/"+encodeURIComponent(LS.slug)'

PAIRS = [
    # guestbook: list via the worker, note still written to Firestore
    (' var FS="https://firestore.googleapis.com/v1/projects/lazo-513ec/databases/(default)/documents/weddingSites/"+encodeURIComponent(LS.slug)+"/guestbook";',
     ' var FS="https://firestore.googleapis.com/v1/projects/lazo-513ec/databases/(default)/documents/weddingSites/"+encodeURIComponent(LS.slug)+"/guestbook";\n'
     ' var FSR=' + API + '+"/guestbook";  /* JC-LAZO-WWS-0930-DATA */'),
    ('  fetch(FS+"?pageSize=60").then(function(r){return r.json()})',
     '  fetch(FSR).then(function(r){return r.json()})'),
    # chapters
    (' fetch("https://firestore.googleapis.com/v1/projects/lazo-513ec/databases/(default)/documents/weddingSites/"+encodeURIComponent(LS.slug)+"/chapters?pageSize=40")',
     ' fetch(' + API + '+"/chapters")'),
    # invites + seat finder share FSB
    (' var FSB="https://firestore.googleapis.com/v1/projects/lazo-513ec/databases/(default)/documents/weddingSites/"+encodeURIComponent(LS.slug);',
     ' var FSB=' + API + ';  /* JC-LAZO-WWS-0930-DATA */'),
    ('  var loadSeats=function(){if(seatP)return seatP;seatP=fetch(FSB+"/seating/main")',
     '  var loadSeats=function(q){seatP=fetch(FSB+"/seat?q="+encodeURIComponent(q||""))'),
    ('   loadSeats().then(function(list){', '   loadSeats(v).then(function(list){'),
    ('   fetch(FSB+"/invites/"+encodeURIComponent(token))', '   fetch(FSB+"/invite/"+encodeURIComponent(token))'),
    # room map
    ('  var FSB="https://firestore.googleapis.com/v1/projects/lazo-513ec/databases/(default)/documents/weddingSites/"+encodeURIComponent(LS.slug)+"/seating/main";',
     '  var FSB=' + API + '+"/room";  /* JC-LAZO-WWS-0930-DATA */'),
]

files = [HERE / "_base.html"] + sorted(p for p in HERE.glob("*/index.html") if not p.parent.name.startswith("_"))
for f in files:
    s = f.read_text(encoding="utf-8")
    orig = s
    n = 0
    for old, new in PAIRS:
        if old in s:
            s = s.replace(old, new); n += 1
    if s != orig:
        f.write_text(s, encoding="utf-8", newline="\n")
    print(f"  {f.relative_to(HERE)}: {n} edit(s)")
left = [f.name for f in files if "documents/weddingSites/\"+encodeURIComponent(LS.slug)+\"/seating" in f.read_text(encoding="utf-8")
        or "/chapters?pageSize=40" in f.read_text(encoding="utf-8")]
if left:
    raise SystemExit(f"direct reads remain in {left}")
print("no direct Firestore reads remain in", len(files), "files")

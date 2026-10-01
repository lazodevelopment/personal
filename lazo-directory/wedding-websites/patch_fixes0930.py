"""patch_fixes0930.py - JC-LAZO-WWS-0930-FIXES
Fixes from the 2026-09-30 wedding-website audit, applied to _base.html and to
all built templates (wedding-websites/*/index.html) in one pass. Idempotent.
  1. XSS: the guestbook/chapters esc() mapped "<" to "\\u003c", which in JS is
     just "<" again, so nothing was escaped. Now real HTML entities.
  2. Tab title doubled on live sites ("A & B - A & B - wedding").
  3. Translation left the song pill (.oursong, not .lzsong), vendor names,
     guestbook notes, guest photo captions and event names alone.
  4. Timeline times in "4:00 PM" form parsed as 04:00.
  5. "The day" schedule hides when the hour-by-hour timeline renders.
  6. aria-labels on the song, guestbook, June, seat-finder and passcode inputs.
  python wedding-websites\\patch_fixes0930.py
Then: python wedding-websites\\sync_dist.py; python deploy\\upload_r2.py --prefix wedding-websites
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BAD = '{"<":"\\u003c",">":"\\u003e","&":"\\u0026",\'"\':"\\u0022"}'
GOOD = '{"<":"&lt;",">":"&gt;","&":"&amp;",\'"\':"&quot;"}'

PAIRS = [
    ('if(names[0]&&names[1])document.title=names[0]+" & "+names[1]+" — "+document.title;',
     'if(names[0]&&names[1]&&!window.LAZO_SITE)document.title=names[0]+" & "+names[1]+" — "+document.title;'),
    ('closest(".lzlang,.junep,.demo-bar,.cd,h1,.wallx,.lzsong,.seatr")',
     'closest(".lzlang,.junep,.demo-bar,.cd,h1,.wallx,.oursong,.seatr,.vtg,.gbwall,.gpwall,.evg h3")'),
    ('function hhmm(t){var m=/^(\\d{1,2}):(\\d{2})/.exec(t||"");if(!m)return null;return parseInt(m[1],10)*60+parseInt(m[2],10)}',
     'function hhmm(t){var m=/^(\\d{1,2}):(\\d{2})\\s*([AaPp][Mm]?)?/.exec(String(t||"").trim());if(!m)return null;var h=parseInt(m[1],10),ap=(m[3]||"").toLowerCase();if(ap.charAt(0)==="p"&&h<12)h+=12;if(ap.charAt(0)==="a"&&h===12)h=0;return h*60+parseInt(m[2],10)}'),
    (' var ol=s1.querySelector("#tlx");\n',
     ' var ol=s1.querySelector("#tlx");\n var schd=document.querySelector(".sched");if(schd)schd.style.display="none";\n'),
    ('<input data-song placeholder=', '<input data-song aria-label="Song request" placeholder='),
    ('<textarea placeholder="', '<textarea aria-label="A note with your song" placeholder="'),
    ('<input id="lzp" style=', '<input id="lzp" aria-label="Passcode" style='),
    ('<input data-gn placeholder=', '<input data-gn aria-label="Your name" placeholder='),
    ('<textarea data-gm placeholder=', '<textarea data-gm aria-label="Your note" placeholder='),
    ('<input id="ji" placeholder=', '<input id="ji" aria-label="Ask June a question" placeholder='),
    ('<input id="seatq" placeholder=', '<input id="seatq" aria-label="Your name, to find your table" placeholder='),
]

files = [HERE / "_base.html"] + sorted(p for p in HERE.glob("*/index.html") if not p.parent.name.startswith("_"))
for f in files:
    s = f.read_text(encoding="utf-8")
    orig = s
    hits = []
    if BAD in s:
        s = s.replace(BAD, GOOD); hits.append("esc")
    for old, new in PAIRS:
        if old in s and not (new in s and old not in new):
            s = s.replace(old, new)
            hits.append(old[:24])
    if s != orig:
        f.write_text(s, encoding="utf-8", newline="\n")
    print(f"  {f.relative_to(HERE)}: {len(hits)} edit(s)" + ("" if s != orig else " (already)"))
# the fix that matters most must be everywhere
left = [f.name for f in files if BAD in f.read_text(encoding="utf-8")]
if left:
    raise SystemExit(f"bad escaper still in: {left}")
print("escaper clean in", len(files), "files")

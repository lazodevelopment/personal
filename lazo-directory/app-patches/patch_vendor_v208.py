"""Vendor v208: video call production fixes (JC-LAZO-CALLFIX-1016-VENDOR).

    python app-patches\\patch_vendor_v208.py [base.txt]   # base defaults to Vendor_master_v207.txt
                                                          # writes Vendor_master_v208.txt
- call screen v3 (lazo_call_screen.dart.txt) and thread template v2 (lazo_call_thread.dart.txt)
- the Schedule button's Pro marker is a readable "Pro" pill beside the icon
- the plan sheet lists "Schedule Lazo video calls" under Pro
- the inbox card's status tags wrap instead of overflowing (Nora & Eli card, 23 px)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v207.txt"
DST = HERE / "Vendor_master_v208.txt"
SCREEN = (HERE / "lazo_call_screen.dart.txt").read_text(encoding="utf-8")
THREAD = (HERE / "lazo_call_thread.dart.txt").read_text(encoding="utf-8").replace("__ROLE__", "vendor")
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, f"expected {n}, found {c}: {a[:90]!r}"
    s = s.replace(a, b)


first_build = s.index("// Build ID:")
s = s[:first_build] + (
    "// Build ID: JC-LAZO-CALLFIX-1016-VENDOR (v208: VIDEO CALL POLISH - the call screen puts the couple's name and the camera "
    "control on two rows on phones, keeps five buttons on one row, shows Show/Hide video only once there is video, never stalls on a "
    "lost request; gold Join buttons in dark mode; Reschedule / Cancel under More on phones; a readable Pro pill on Schedule; "
    "'Schedule Lazo video calls' in the Pro plan; inbox status tags wrap instead of overflowing)\n"
) + s[first_build:]

# ---- thread template v2 (replace the v1 block)
start = s.index("  // ------------------------------------------------------------------ v167/v207\n  // SCHEDULE A LAZO VIDEO CALL + AUDIO ONLY.")
end = s.index("\n  static final RegExp _kOffCallStrong", start)
s = s[:start] + THREAD.rstrip("\n") + "\n" + s[end:]

# ---- 11. Pro marker: a pill beside the icon
rep("""      icon: Stack(clipBehavior: Clip.none, children: <Widget>[
        Icon(Icons.event_rounded, color: _lzFg(plum), size: 22),
        if (!pro)
          Positioned(
            right: -10,
            top: -6,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
              decoration: BoxDecoration(color: gold, borderRadius: BorderRadius.circular(6)),
              child: const Text('PRO',
                  style: TextStyle(color: Color(0xFF3B1E39), fontSize: 8, fontWeight: FontWeight.w900, letterSpacing: .4)),
            ),
          ),
      ]),""", """      icon: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
        Icon(Icons.event_rounded, color: _lzFg(plum), size: 22),
        if (!pro) ...<Widget>[
          const SizedBox(width: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(color: gold, borderRadius: BorderRadius.circular(999)),
            child: const Text('Pro',
                style: TextStyle(color: Color(0xFF3B1E39), fontSize: 11, fontWeight: FontWeight.w800)),
          ),
        ],
      ]),""")

# ---- 12. the plan sheet
rep("""                  'Reach couples in every market you serve - no metro cap',
                  'Enhanced profile with priority placement of your work',
                  'Inquiry and profile analytics',
                ],""", """                  'Reach couples in every market you serve - no metro cap',
                  'Enhanced profile with priority placement of your work',
                  'Inquiry and profile analytics',
                  'Schedule Lazo video calls with reminders for both of you',
                ],""")

# ---- 8. inbox card tags wrap
rep("""                      Row(children: <Widget>[
                        if (st == 'booked') _inboxPill('BOOKED', vGreen),""", """                      Wrap(spacing: 0, runSpacing: 4, children: <Widget>[ // v208: wrap, don't overflow
                        if (st == 'booked') _inboxPill('BOOKED', vGreen),""")

# ---- call screen v3
i = s.index("\n// ==========================================================================\n// LAZO VIDEO CALL SCREEN")
s = s[:i].rstrip("\n") + "\n" + SCREEN

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name}: {len(s):,} chars")

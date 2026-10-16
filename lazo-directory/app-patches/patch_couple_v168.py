"""Couple v168: video call production fixes (JC-LAZO-CALLFIX-1016-COUPLE).

    python app-patches\\patch_couple_v168.py [base.txt]   # base defaults to Couple_master_v167.txt
                                                          # writes Couple_master_v168.txt
- call screen v3 (lazo_call_screen.dart.txt) and thread template v2 (lazo_call_thread.dart.txt)
- on narrow phones the Schedule button moves into the thread's "..." menu so the
  vendor's name doesn't wrap
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v167.txt"
DST = HERE / "Couple_master_v168.txt"
SCREEN = (HERE / "lazo_call_screen.dart.txt").read_text(encoding="utf-8")
THREAD = (HERE / "lazo_call_thread.dart.txt").read_text(encoding="utf-8").replace("__ROLE__", "couple")
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
    "// Build ID: JC-LAZO-CALLFIX-1016-COUPLE (v168: VIDEO CALL POLISH - the call screen keeps its controls on one row on phones, "
    "explains a locked camera and says when it's allowed, never stalls on a lost request; gold Join buttons in dark mode; the call "
    "card's Reschedule / Cancel under More on phones; on narrow phones Schedule moves into the thread's ... menu)\n"
) + s[first_build:]

# ---- thread template v2 (replace the v1 block)
start = s.index("  // ------------------------------------------------------------------ v167/v207\n  // SCHEDULE A LAZO VIDEO CALL + AUDIO ONLY.")
end = s.index("\n  // Once, before a couple's first video call", start)
s = s[:start] + THREAD.rstrip("\n") + "\n" + s[end:]

# ---- Schedule: header on wide screens, the ... menu on narrow phones
rep("""            _scheduleHeaderButton(inquiryId, inq),
            IconButton(
                tooltip: 'Lazo video call',""", """            if (MediaQuery.of(ctx2).size.width >= 430)
              _scheduleHeaderButton(inquiryId, inq),
            IconButton(
                tooltip: 'Lazo video call',""")
rep("""          subtitle: 'Conversation options',
          children: <Widget>[
            const SizedBox(height: 14),""", """          subtitle: 'Conversation options',
          children: <Widget>[
            const SizedBox(height: 14),
            if (MediaQuery.of(ctx).size.width < 430)
              _scheduleMenuOpt(ctx, inquiryId, inq), // v168""")
rep("""  // Schedule (couples: only when the vendor is on Pro or Studio)""", """  // v168: the same, as a row in the thread's ... menu on narrow phones
  Widget _scheduleMenuOpt(BuildContext menuCtx, String inquiryId, Map<String, dynamic> inq) {
    final String vid = (inq['vendorId'] ?? '').toString();
    if (vid.isEmpty) return const SizedBox.shrink();
    return FutureBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      future: FirebaseFirestore.instance.collection('vendors').doc(vid).get(),
      builder: (BuildContext c, AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> snap) {
        final Map<String, dynamic> v = snap.data?.data() ?? <String, dynamic>{};
        final String t = (v['tier'] ?? '').toString();
        final dynamic exp = v['tierExpiresAt'];
        final bool pro = (t == 'pro' || t == 'studio') &&
            !(exp is Timestamp && exp.toDate().isBefore(DateTime.now()));
        if (!pro) return const SizedBox.shrink();
        return _pcC_opt(Icons.event_rounded, 'Schedule a Lazo video call',
            'Pick a time - you both get reminders', () {
          Navigator.pop(menuCtx);
          _scheduleCallSheet(inquiryId, inq);
        });
      },
    );
  }

  // Schedule (couples: only when the vendor is on Pro or Studio)""")

# ---- call screen v3
i = s.index("\n// ==========================================================================\n// LAZO VIDEO CALL SCREEN")
j = s.rfind("\n/// One-at-a-time queue", 0, i)
s = s[:i].rstrip("\n") + "\n" + SCREEN

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name}: {len(s):,} chars")

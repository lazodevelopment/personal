"""Vendor v207: SCHEDULE A LAZO VIDEO CALL + AUDIO ONLY (JC-LAZO-CALLSCHED-1016-VENDOR).

    python app-patches\\patch_vendor_v207.py [base.txt]   # base defaults to Vendor_master_v206.txt
                                                          # writes Vendor_master_v207.txt

- Thread header: the video button opens "Join with video / Join with audio only";
  a Schedule button next to it. Scheduling is Lazo Pro / Studio: a Free vendor
  sees the button with a small PRO badge and gets the upgrade sheet instead.
  (Video calls themselves stay free.)
- The scheduled-call card (lazo_call_thread.dart.txt): your time + the
  couple's, "Prefers audio only", Join with video / audio only (from 10
  minutes before), Add to calendar, Reschedule, Cancel.
- "Join the video call" under an invite and "Start a Lazo video call" under a
  call request open the same two choices.
- The call screen is replaced with v2 (lazo_call_screen.dart.txt).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v206.txt"
DST = HERE / "Vendor_master_v207.txt"
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
    "// Build ID: JC-LAZO-CALLSCHED-1016-VENDOR (v207: SCHEDULE A CALL + AUDIO ONLY - Join with video / Join with audio only "
    "everywhere you join; Schedule a call in the thread (Pro and Studio; Free shows a PRO badge and the upgrade sheet); the "
    "scheduled-call card with your time and the couple's, Prefers audio only, Join from 10 minutes before, Add to calendar, "
    "Reschedule, Cancel; the call screen shows both people as avatars with a speaking ring when nobody is on camera)\n"
) + s[first_build:]

# ---- join with video turns the vendor's camera on at join
rep("""  Future<void> _startLazoCall(String inquiryId, Map<String, dynamic> inq) async {""",
    """  Future<void> _startLazoCall(String inquiryId, Map<String, dynamic> inq, {bool withVideo = false}) async {""")
rep("""        onReport: () => _coupleSafetySheet(inquiryId, inq),
      ),
    ));
  }""", """        onReport: () => _coupleSafetySheet(inquiryId, inq),
        startCamera: withVideo,
      ),
    ));
  }""")

# ---- the Join buttons under an invite
rep("""  Widget _callJoinChip(String inquiryId, Map<String, dynamic> inq) => Padding(
        padding: const EdgeInsets.only(left: 6, bottom: 10),
        child: Align(
          alignment: Alignment.centerLeft,
          child: FilledButton.icon(
            onPressed: _h(() => _startLazoCall(inquiryId, inq)),
            icon: const Icon(Icons.videocam_rounded, size: 16),
            label: const Text('Join the video call',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
            style: FilledButton.styleFrom(
                backgroundColor: plum, shape: const StadiumBorder()),
          ),
        ),
      );""", """  Widget _callJoinChip(String inquiryId, Map<String, dynamic> inq) => Padding(
        padding: const EdgeInsets.only(left: 6, bottom: 10),
        child: Align(
          alignment: Alignment.centerLeft,
          child: _lzJoinButtons(inquiryId, inq),
        ),
      );

  // v207: one join path for the chooser, the invite and the card
  void _lzJoin(String inquiryId, Map<String, dynamic> inq, {required bool video}) {
    _startLazoCall(inquiryId, inq, withVideo: video);
  }

  // Schedule a call: Pro and Studio. Free sees a PRO badge and the upgrade sheet.
  Widget _scheduleHeaderButton(String inquiryId, Map<String, dynamic> inq) {
    final String vid = (inq['vendorId'] ?? '').toString();
    final Map<String, dynamic> v = _liveD['vendor:$vid']?.latest?.data() ?? <String, dynamic>{};
    final String t = (v['tier'] ?? '').toString();
    final dynamic exp = v['tierExpiresAt'];
    final bool pro = (t == 'pro' || t == 'studio') &&
        !(exp is Timestamp && exp.toDate().isBefore(DateTime.now()));
    return IconButton(
      tooltip: pro ? 'Schedule a call' : 'Schedule a call (Lazo Pro)',
      visualDensity: VisualDensity.compact,
      onPressed: _h(() => pro ? _scheduleCallSheet(inquiryId, inq) : _upgradeSheet(vid)),
      icon: Stack(clipBehavior: Clip.none, children: <Widget>[
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
      ]),
    );
  }
""" + THREAD)

# ---- "Start a Lazo video call" under a couple's call request -> the two choices
rep("""          FilledButton.icon(
            onPressed: _h(() => _startLazoCall(inquiryId, inq)),
            icon: const Icon(Icons.videocam_rounded, size: 16),
            label: const Text('Start a Lazo video call',""", """          FilledButton.icon(
            onPressed: _h(() => _lazoCallChooser(inquiryId, inq)),
            icon: const Icon(Icons.videocam_rounded, size: 16),
            label: const Text('Start a Lazo video call',""")

# ---- thread header
rep("""              IconButton(
                tooltip: 'Lazo video call',
                visualDensity: VisualDensity.compact,
                icon: Icon(Icons.videocam_rounded, color: _lzFg(plum), size: 22),
                onPressed: _h(() => _startLazoCall(inquiryId, inq)),
              ),""", """              _scheduleHeaderButton(inquiryId, inq),
            if (inq['demo'] != true &&
                !(inq['coupleUid'] ?? '').toString().startsWith('lead_'))
              IconButton(
                tooltip: 'Lazo video call',
                visualDensity: VisualDensity.compact,
                icon: Icon(Icons.videocam_rounded, color: _lzFg(plum), size: 22),
                onPressed: _h(() => _lazoCallChooser(inquiryId, inq)),
              ),""")

# ---- the call card, once per scheduled call
rep("""              final dynamic otherRead = inq['coupleLastReadAt'];
              for (int i = 0; i < mdocs.length; i++) {
                final Map<String, dynamic> mm = mdocs[i].data();""", """              final dynamic otherRead = inq['coupleLastReadAt'];
              final Set<String> lzCards = <String>{}; // v207: one card per call
              for (int i = 0; i < mdocs.length; i++) {
                final Map<String, dynamic> mm = mdocs[i].data();""")
rep("""                if (mm['callInvite'] is Map) {
                  bubbles.add(_callJoinChip(inquiryId, inq)); // v205
                }""", """                if (mm['callInvite'] is Map) {
                  bubbles.add(_callJoinChip(inquiryId, inq)); // v205
                }
                if (mm['callSchedule'] is Map) {
                  final String cid = ((mm['callSchedule'] as Map)['consultId'] ?? '').toString();
                  if (cid.isNotEmpty && lzCards.add(cid)) {
                    bubbles.add(_callCard(inquiryId, inq, cid)); // v207
                  }
                }""")

# ---- call screen v2
i = s.index("\n// ==========================================================================\n// LAZO VIDEO CALL SCREEN")
s = s[:i].rstrip("\n") + "\n" + SCREEN

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name}: {len(s):,} chars")

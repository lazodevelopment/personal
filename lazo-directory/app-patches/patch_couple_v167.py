"""Couple v167: SCHEDULE A LAZO VIDEO CALL + AUDIO ONLY (JC-LAZO-CALLSCHED-1016-COUPLE).

    python app-patches\\patch_couple_v167.py [base.txt]   # base defaults to Couple_master_v166.txt
                                                          # writes Couple_master_v167.txt

- Thread header: the video button opens "Join with video / Join with audio only";
  a Schedule button appears when the thread's vendor is on Pro or Studio
  (scheduling is Pro+, checked on the server too). With a Free vendor the
  couple only has "start a call now".
- The scheduled-call card (lazo_call_thread.dart.txt): your time + theirs,
  Join with video / audio only (from 10 minutes before), Add to calendar,
  Reschedule, Cancel, "I prefer audio only".
- "Join the video call" under an invite becomes the two Join buttons.
- The call screen is replaced with v2 (lazo_call_screen.dart.txt: audio-only
  view with avatars and a speaking ring, the couple's Audio only toggle).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v166.txt"
DST = HERE / "Couple_master_v167.txt"
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
    "// Build ID: JC-LAZO-CALLSCHED-1016-COUPLE (v167: SCHEDULE A CALL + AUDIO ONLY - Join with video / Join with audio only "
    "everywhere you join; a Schedule button in the thread when the vendor is on Pro or Studio; the scheduled-call card with your "
    "time and theirs, Join from 10 minutes before, Add to calendar, Reschedule, Cancel and I prefer audio only; the call screen "
    "shows both people as avatars with a speaking ring when nobody is on camera)\n"
) + s[first_build:]

# ---- callJoin carries the audio-only choice
rep("""  Future<Map<String, dynamic>> _callJoin(String inquiryId) async {
    final HttpsCallableResult<dynamic> out = await FirebaseFunctions.instance
        .httpsCallable('callJoin')
        .call(<String, dynamic>{'inquiryId': inquiryId});""", """  Future<Map<String, dynamic>> _callJoin(String inquiryId, {bool? audioOnly}) async {
    final HttpsCallableResult<dynamic> out = await FirebaseFunctions.instance
        .httpsCallable('callJoin')
        .call(<String, dynamic>{'inquiryId': inquiryId, if (audioOnly != null) 'audioOnly': audioOnly});""")
rep("""  Future<void> _startLazoCall(String inquiryId) async {
    Map<String, dynamic> r;
    try {
      r = await _callJoin(inquiryId);
      if (r['needPhone'] == true) {
        if (!await _phoneVerifySheet()) return;
        r = await _callJoin(inquiryId);
      }""", """  Future<void> _startLazoCall(String inquiryId, {bool? audioOnly}) async {
    Map<String, dynamic> r;
    try {
      r = await _callJoin(inquiryId, audioOnly: audioOnly);
      if (r['needPhone'] == true) {
        if (!await _phoneVerifySheet()) return;
        r = await _callJoin(inquiryId, audioOnly: audioOnly);
      }""")

# ---- the Join buttons under an invite
rep("""  Widget _callJoinChip(String inquiryId) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Align(
          alignment: Alignment.centerLeft,
          child: FilledButton.icon(
            onPressed: _h(() => _startLazoCall(inquiryId)),
            icon: const Icon(Icons.videocam_rounded, size: 18),
            label: const Text('Join the video call'),
            style: FilledButton.styleFrom(
                backgroundColor: plum, shape: const StadiumBorder()),
          ),
        ),
      );""", """  Widget _callJoinChip(String inquiryId) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Align(
          alignment: Alignment.centerLeft,
          child: _lzJoinButtons(inquiryId, const <String, dynamic>{}),
        ),
      );

  // v167: one join path for the chooser, the invite and the card
  void _lzJoin(String inquiryId, Map<String, dynamic> inq, {required bool video}) {
    _startLazoCall(inquiryId, audioOnly: !video);
  }

  // Schedule (couples: only when the vendor is on Pro or Studio)
  Widget _scheduleHeaderButton(String inquiryId, Map<String, dynamic> inq) {
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
        return IconButton(
            tooltip: 'Schedule a call',
            icon: Icon(Icons.event_rounded, color: _lzFg(plum)),
            onPressed: _h(() => _scheduleCallSheet(inquiryId, inq)));
      },
    );
  }
""" + THREAD)

# ---- thread header
rep("""            IconButton(
                tooltip: 'Lazo video call',
                icon: Icon(Icons.videocam_rounded, color: _lzFg(plum)),
                onPressed: _h(() => _startLazoCall(inquiryId))),""", """            _scheduleHeaderButton(inquiryId, inq),
            IconButton(
                tooltip: 'Lazo video call',
                icon: Icon(Icons.videocam_rounded, color: _lzFg(plum)),
                onPressed: _h(() => _lazoCallChooser(inquiryId, inq))),""")

# ---- the call card, once per scheduled call
rep("""                  for (int i = 0; i < mdocs.length; i++) {
                    final QueryDocumentSnapshot<Map<String, dynamic>> d =
                        mdocs[i];""", """                  final Set<String> lzCards = <String>{}; // v167: one card per call
                  for (int i = 0; i < mdocs.length; i++) {
                    final QueryDocumentSnapshot<Map<String, dynamic>> d =
                        mdocs[i];""")
rep("""                    if (mm['callInvite'] is Map) {
                      bubbles.add(_callJoinChip(inquiryId)); // v165
                    }""", """                    if (mm['callInvite'] is Map) {
                      bubbles.add(_callJoinChip(inquiryId)); // v165
                    }
                    if (mm['callSchedule'] is Map) {
                      final String cid = ((mm['callSchedule'] as Map)['consultId'] ?? '').toString();
                      if (cid.isNotEmpty && lzCards.add(cid)) {
                        bubbles.add(_callCard(inquiryId, liveInq, cid)); // v167
                      }
                    }""")

# ---- call screen v2
i = s.index("\n// ==========================================================================\n// LAZO VIDEO CALL SCREEN")
s = s[:i].rstrip("\n") + "\n" + SCREEN

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name}: {len(s):,} chars")

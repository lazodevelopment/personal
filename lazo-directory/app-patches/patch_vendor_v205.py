"""Vendor v205: LAZO VIDEO CALLS, Phase 1 (JC-LAZO-CALLS-1016-VENDOR).

    python app-patches\\patch_vendor_v205.py [base.txt]   # base defaults to Vendor_master_v204.txt
                                                          # writes Vendor_master_v205.txt

- A video button in the thread header starts or joins the thread's Lazo video
  call (callJoin). Website / booking leads with no Lazo account get no video
  (a toast that points to the booking link).
- Join chip under "Started a Lazo video call"; "Start a Lazo video call" next
  to "Send my booking link" under a couple's call request and in the
  outside-link warning.
- The call screen (_LazoCallScreen, app-patches/lazo_call_screen.dart.txt):
  camera off at join, the couple's video blurred until the vendor taps, "Let
  them use camera", hide, watermark, Leave and Leave + report.
- The consult scheduler loses its Zoom / Google Meet link field: video
  consults are Lazo video calls.
Needs the pub dependency flutter_webrtc and camera + microphone permissions.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v204.txt"
DST = HERE / "Vendor_master_v205.txt"
SCREEN = (HERE / "lazo_call_screen.dart.txt").read_text(encoding="utf-8")
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
    "// Build ID: JC-LAZO-CALLS-1016-VENDOR (v205: LAZO VIDEO CALLS - a video button in the thread starts or joins the thread's Lazo "
    "video call (callJoin, Cloudflare Realtime through the meetlazo.com worker); the call screen joins with the camera off, blurs the "
    "couple's video until you tap, lets you allow or take back their camera, watermarks every tile, and has Leave + report; Join chip "
    "under call invites; Start a Lazo video call under call requests and in the outside-link warning; the scheduler's Zoom/Meet link "
    "field is gone; needs the flutter_webrtc package)\n"
) + s[first_build:]

rep("import 'package:http/http.dart' as httpc;\n",
    "import 'package:http/http.dart' as httpc;\n"
    "import 'package:flutter_webrtc/flutter_webrtc.dart'; // v205: Lazo video calls\n"
    "import 'dart:ui' as rtcui;\n")

# ---- thread header: video call button (before the v200 shield)
rep("""            if (inq['demo'] != true &&
                !(inq['coupleUid'] ?? '').toString().startsWith('lead_'))
              IconButton(
                tooltip: 'Report or block',""", """            if (inq['demo'] != true &&
                !(inq['coupleUid'] ?? '').toString().startsWith('lead_'))
              IconButton(
                tooltip: 'Lazo video call',
                visualDensity: VisualDensity.compact,
                icon: Icon(Icons.videocam_rounded, color: _lzFg(plum), size: 22),
                onPressed: _h(() => _startLazoCall(inquiryId, inq)),
              ),
            if (inq['demo'] != true &&
                !(inq['coupleUid'] ?? '').toString().startsWith('lead_'))
              IconButton(
                tooltip: 'Report or block',""")

# ---- Join chip under a call invite
rep("""                if (!mine && mm['callRequest'] == true) {
                  bubbles.add(_callRequestChip(inquiryId, inq));
                }""", """                if (!mine && mm['callRequest'] == true) {
                  bubbles.add(_callRequestChip(inquiryId, inq));
                }
                if (mm['callInvite'] is Map) {
                  bubbles.add(_callJoinChip(inquiryId, inq)); // v205
                }""")

# ---- call request chip: Lazo video call first, booking link second
s2, c = re.subn(r"  Widget _callRequestChip\(String inquiryId, Map<String, dynamic> inq\) =>.*?\n      \);\n\n",
    r"""  Widget _callRequestChip(String inquiryId, Map<String, dynamic> inq) =>
      Padding(
        padding: const EdgeInsets.only(left: 6, bottom: 10),
        child: Wrap(spacing: 8, runSpacing: 6, children: <Widget>[
          FilledButton.icon(
            onPressed: _h(() => _startLazoCall(inquiryId, inq)),
            icon: const Icon(Icons.videocam_rounded, size: 16),
            label: const Text('Start a Lazo video call',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
            style: FilledButton.styleFrom(
                backgroundColor: plum, shape: const StadiumBorder()),
          ),
          OutlinedButton.icon(
            onPressed: _h(() => _sendBookingLink(inquiryId, inq)),
            icon: Icon(Icons.event_available_rounded,
                size: 16, color: _lzFg(plum)),
            label: Text('Send my booking link',
                style: TextStyle(
                    color: _lzFg(plum), fontSize: 12, fontWeight: FontWeight.w800)),
            style: OutlinedButton.styleFrom(
                side: BorderSide(color: _lzLine(gold.withOpacity(.7))),
                shape: const StadiumBorder()),
          ),
        ]),
      );

""", s, count=1, flags=re.S)
assert c == 1, "callRequestChip"
s = s2

# ---- outside-link warning: offer the Lazo call too
rep("""            _lzNote(Icons.edit_rounded, 'Close this to edit your message.'),""",
"""            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: () => Navigator.pop(ctx, 'call'),
                icon: Icon(Icons.videocam_rounded, color: _lzFg(plum), size: 18),
                label: Text('Start a Lazo video call instead',
                    style: TextStyle(
                        color: _lzFg(plum), fontSize: 13, fontWeight: FontWeight.w800)),
              ),
            ),
            _lzNote(Icons.edit_rounded, 'Close this to edit your message.'),""")
rep("""    if (pick == 'booking') {""", """    if (pick == 'call') {
      try {
        final DocumentSnapshot<Map<String, dynamic>> d = await FirebaseFirestore
            .instance
            .collection('inquiries')
            .doc(inquiryId)
            .get();
        await _startLazoCall(inquiryId, d.data() ?? <String, dynamic>{});
      } catch (e) {
        _toast('Could not start the call: ' + _errText(e));
      }
    }
    if (pick == 'booking') {""")

# ---- scheduler: no outside video links
rep("""                  label('Video link'),
                  TextField(
                    controller: videoC,
                    keyboardType: TextInputType.url,
                    style:  TextStyle(color: _lzFg(ink), fontSize: 13),
                    decoration: deco(
                        'Your Zoom / Google Meet room link (used for every video type)'),
                  ),
""", """                  // v205: no outside video links - video consults are Lazo video calls
                  _lzNote(Icons.videocam_rounded,
                      'Video consults happen as a Lazo video call right in your conversation. No Zoom or Meet links needed.'),
""")
rep("""                'videoLink': videoC.text.trim(),""", """                'videoLink': '', // v205: outside video links are gone""")
rep("""    final TextEditingController videoC =
        TextEditingController(text: (sch['videoLink'] ?? '').toString());
""", "")

# ---- helpers (before the v200 outside-call regexes)
rep("""  static final RegExp _kOffCallStrong = RegExp(""", r"""  // ------------------------------------------------------------------ v205
  // LAZO VIDEO CALLS.  JC-LAZO-CALLS-1016-VENDOR
  Future<void> _startLazoCall(String inquiryId, Map<String, dynamic> inq) async {
    Map<String, dynamic> r;
    try {
      final HttpsCallableResult<dynamic> out = await FirebaseFunctions.instance
          .httpsCallable('callJoin')
          .call(<String, dynamic>{'inquiryId': inquiryId});
      r = Map<String, dynamic>.from((out.data as Map?) ?? <String, dynamic>{});
    } catch (e) {
      _toast(_lzFnMsg(e, 'Could not start the call. Try again in a moment.'));
      return;
    }
    if (r['ok'] != true || !mounted) return;
    await Navigator.of(context).push(MaterialPageRoute<void>(
      fullscreenDialog: true,
      builder: (BuildContext _) => _LazoCallScreen(
        callId: (r['callId'] ?? '').toString(),
        token: (r['token'] ?? '').toString(),
        role: 'vendor',
        myName: (r['myName'] ?? 'You').toString(),
        otherName: (r['otherName'] ?? 'The couple').toString(),
        workerBase: (r['workerBase'] ?? 'https://meetlazo.com').toString(),
        onReport: () => _coupleSafetySheet(inquiryId, inq),
      ),
    ));
  }

  Widget _callJoinChip(String inquiryId, Map<String, dynamic> inq) => Padding(
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
      );

  static final RegExp _kOffCallStrong = RegExp(""")

s = s.rstrip("\n") + "\n" + SCREEN

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name}: {len(s):,} chars")

"""Couple v165: LAZO VIDEO CALLS, Phase 1 (JC-LAZO-CALLS-1016-COUPLE).

    python app-patches\\patch_couple_v165.py [base.txt]   # base defaults to Couple_master_v164.txt
                                                          # writes Couple_master_v165.txt

- A video button in the thread header starts or joins the thread's Lazo video
  call (callJoin). The first time, the couple confirms a phone number by text
  code (phoneStart / phoneConfirm).
- A "Started a Lazo video call" message in the thread gets a Join chip.
- The call screen (_LazoCallScreen, app-patches/lazo_call_screen.dart.txt):
  camera off at join, the couple's camera locked until the vendor allows it,
  watermark on every tile, one-tap leave.
Needs the pub dependency flutter_webrtc and camera + microphone permissions.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v164.txt"
DST = HERE / "Couple_master_v165.txt"
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
    "// Build ID: JC-LAZO-CALLS-1016-COUPLE (v165: LAZO VIDEO CALLS - a video button in the thread starts or joins the thread's Lazo "
    "video call (callJoin, Cloudflare Realtime through the meetlazo.com worker); the first time, the couple confirms a phone by text code; "
    "a Join chip under 'Started a Lazo video call'; the call screen joins with the camera off, keeps the couple's camera locked until the "
    "vendor allows it, and watermarks every tile with who, when and the call id; needs the flutter_webrtc package)\n"
) + s[first_build:]

rep("import 'package:http/http.dart' as httpc;\n",
    "import 'package:http/http.dart' as httpc;\n"
    "import 'package:flutter_webrtc/flutter_webrtc.dart'; // v165: Lazo video calls\n"
    "import 'dart:ui' as rtcui;\n")

# ---- thread header: video call button
rep("""            IconButton(
                tooltip: 'More',
                icon:  Icon(Icons.more_horiz_rounded, color: _lzFg(muted)),
                onPressed: _h(() => _threadMenu(ctx2, inquiryId, inq))),""",
"""            IconButton(
                tooltip: 'Lazo video call',
                icon: Icon(Icons.videocam_rounded, color: _lzFg(plum)),
                onPressed: _h(() => _startLazoCall(inquiryId))),
            IconButton(
                tooltip: 'More',
                icon:  Icon(Icons.more_horiz_rounded, color: _lzFg(muted)),
                onPressed: _h(() => _threadMenu(ctx2, inquiryId, inq))),""")

# ---- Join chip under a call invite
rep("""                        onLongPress: mine
                            ? () => _editCoupleMessage(
                                inquiryId, d.id, (mm['text'] ?? '') as String)
                            : null));
                  }
""", """                        onLongPress: mine
                            ? () => _editCoupleMessage(
                                inquiryId, d.id, (mm['text'] ?? '') as String)
                            : null));
                    if (mm['callInvite'] is Map) {
                      bubbles.add(_callJoinChip(inquiryId)); // v165
                    }
                  }
""")

# ---- helpers
rep("""  Future<bool> _safeCoupleSend(String inquiryId, String text) async {""", r"""  // ------------------------------------------------------------------ v165
  // LAZO VIDEO CALLS.  JC-LAZO-CALLS-1016-COUPLE
  Future<Map<String, dynamic>> _callJoin(String inquiryId) async {
    final HttpsCallableResult<dynamic> out = await FirebaseFunctions.instance
        .httpsCallable('callJoin')
        .call(<String, dynamic>{'inquiryId': inquiryId});
    return Map<String, dynamic>.from((out.data as Map?) ?? <String, dynamic>{});
  }

  Future<void> _startLazoCall(String inquiryId) async {
    Map<String, dynamic> r;
    try {
      r = await _callJoin(inquiryId);
      if (r['needPhone'] == true) {
        if (!await _phoneVerifySheet()) return;
        r = await _callJoin(inquiryId);
      }
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
        role: 'couple',
        myName: (r['myName'] ?? 'You').toString(),
        otherName: (r['otherName'] ?? 'Your vendor').toString(),
        workerBase: (r['workerBase'] ?? 'https://meetlazo.com').toString(),
      ),
    ));
  }

  Widget _callJoinChip(String inquiryId) => Padding(
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
      );

  // Once, before a couple's first video call: a phone number confirmed by a
  // texted code (phoneStart / phoneConfirm). It keeps throwaway accounts off
  // Lazo video.
  Future<bool> _phoneVerifySheet() async {
    final TextEditingController phoneC = TextEditingController();
    final TextEditingController codeC = TextEditingController();
    bool sent = false;
    bool busy = false;
    bool open = true;
    String err = '';
    String sentTo = '';
    if (!mounted) return false;
    final bool? ok = await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 460),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setP) {
          void up(VoidCallback f) {
            if (open) setP(f);
          }

          Future<void> send() async {
            up(() {
              busy = true;
              err = '';
            });
            try {
              final HttpsCallableResult<dynamic> out = await FirebaseFunctions
                  .instance
                  .httpsCallable('phoneStart')
                  .call(<String, dynamic>{'phone': phoneC.text.trim()});
              final Map<String, dynamic> r = Map<String, dynamic>.from(
                  (out.data as Map?) ?? <String, dynamic>{});
              up(() {
                busy = false;
                sent = true;
                sentTo = (r['sentTo'] ?? 'your phone').toString();
              });
            } catch (e) {
              up(() {
                busy = false;
                err = _lzFnMsg(e, 'Could not text that number. Check it and try again.');
              });
            }
          }

          Future<void> confirm() async {
            up(() {
              busy = true;
              err = '';
            });
            try {
              await FirebaseFunctions.instance
                  .httpsCallable('phoneConfirm')
                  .call(<String, dynamic>{'code': codeC.text.trim()});
              if (ctx2.mounted) Navigator.pop(ctx2, true);
            } catch (e) {
              up(() {
                busy = false;
                err = _lzFnMsg(e, 'That code didn’t work.');
              });
            }
          }

          return _lzFrame(ctx2,
              icon: Icons.verified_user_rounded,
              title: 'Confirm your phone',
              subtitle:
                  'Once, before your first video call. It keeps fake accounts off Lazo video.',
              children: <Widget>[
                const SizedBox(height: 12),
                if (!sent)
                  TextField(
                    controller: phoneC,
                    keyboardType: TextInputType.phone,
                    autofocus: true,
                    style: TextStyle(color: _lzFg(ink), fontSize: 15),
                    decoration: _lightDeco('Mobile number', hint: '(480) 555-1212'),
                    onChanged: (_) => up(() {}),
                  )
                else ...<Widget>[
                  Text('We texted a 6-digit code to $sentTo.',
                      style: TextStyle(color: _lzFg(ink), fontSize: 13.5)),
                  const SizedBox(height: 10),
                  TextField(
                    controller: codeC,
                    keyboardType: TextInputType.number,
                    autofocus: true,
                    maxLength: 6,
                    style: TextStyle(color: _lzFg(ink), fontSize: 20, letterSpacing: 6),
                    decoration: _lightDeco('Code'),
                    onChanged: (_) => up(() {}),
                  ),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton(
                      onPressed: busy
                          ? null
                          : () => up(() {
                                sent = false;
                                codeC.clear();
                              }),
                      child: const Text('Use a different number'),
                    ),
                  ),
                ],
                if (err.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(err,
                        style: const TextStyle(color: Color(0xFFB3261E), fontSize: 12.5)),
                  ),
                const SizedBox(height: 8),
                Text(
                    'Message and data rates may apply. We only use your number to keep video calls safe.',
                    style: TextStyle(color: _lzFg(muted), fontSize: 11.5)),
              ],
              footer: _lzActions(
                  secondary: 'Not now',
                  onSecondary: () => Navigator.pop(ctx2, false),
                  primary: sent ? 'Confirm' : 'Text me a code',
                  busy: busy,
                  onPrimary: sent
                      ? (codeC.text.trim().length == 6 ? confirm : null)
                      : (phoneC.text.replaceAll(RegExp(r'\D'), '').length >= 10 ? send : null)));
        },
      ),
    ).whenComplete(() => open = false);
    return ok == true;
  }

  Future<bool> _safeCoupleSend(String inquiryId, String text) async {""")

s = s.rstrip("\n") + "\n" + SCREEN

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name}: {len(s):,} chars")

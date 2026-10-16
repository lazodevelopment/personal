"""Couple v160: SAFETY - "let's get on a Zoom call" (JC-LAZO-SAFETY-1016-COUPLE).

    python app-patches\\patch_couple_v160.py [base.txt]   # base defaults to Couple_master_v159.txt
                                                          # writes Couple_master_v160.txt

Re-runnable on any later master that still has these anchors (v161 and v163
branch from v159 too; run it on the merged master when they come together).

What changes:
  - The composer and June's "Questions you could ask" send through the
    sendThreadMessage callable (functions-dashboard/safety-guard.js). A held
    message (outside call app or link, a video-call request, a phone number or
    email in the first few messages) is never delivered; the couple sees the
    nudge, keeps the text to edit, and can tap "Request a Lazo video call".
  - A new thread's first message runs safetyPrecheck before the inquiry is
    created; a held first message is not sent.
  - A safety-blocked account sees "Account under review".
Untouched (the rules floor covers them): file sends, the goodbye note, edits.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v159.txt"
DST = HERE / "Couple_master_v160.txt"
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, f"expected {n}, found {c}: {a[:90]!r}"
    s = s.replace(a, b)


def rx(pattern, repl, n=1):
    global s
    s2, c = re.subn(pattern, repl, s)
    assert c == n, f"expected {n}, found {c}: {pattern[:90]!r}"
    s = s2


# ---- header
first_build = s.index("// Build ID:")
s = s[:first_build] + (
    "// Build ID: JC-LAZO-SAFETY-1016-COUPLE (v160: SAFETY - \"let's get on a Zoom call\": the composer and June's questions send through "
    "sendThreadMessage, which holds an outside call app or link, a video-call request, or a phone number or email in the first few messages; "
    "the couple gets a nudge and a Request a Lazo video call button; a new thread's first message is prechecked (safetyPrecheck); "
    "a blocked account sees Account under review)\n"
) + s[first_build:]

# ---- 1. composer
rep("""    setSheet(() => setSending(true));
    try {
      await FirebaseFirestore.instance
          .collection('inquiries')
          .doc(inquiryId)
          .collection('messages')
          .add(<String, dynamic>{
        'senderRole': 'couple',
        'text': t,
        'at': FieldValue.serverTimestamp(),
      });
      c.clear();
    } catch (e) {
      _toast('Could not send: $e');
    } finally {
      setSheet(() => setSending(false));
    }
  }
""", """    setSheet(() => setSending(true));
    try {
      // v160: through the safety check. A held message stays in the box to edit.
      if (await _safeCoupleSend(inquiryId, t)) c.clear();
    } finally {
      setSheet(() => setSending(false));
    }
  }
""")

# ---- 2. June's "Questions you could ask"
rx(r"""await FirebaseFirestore\.instance\s*\.collection\('inquiries'\)\s*\.doc\(inquiryId\)\s*\.collection\('messages'\)\s*\.add\(<String, dynamic>\{\s*'senderRole': 'couple',\s*'text': q,\s*'at': FieldValue\.serverTimestamp\(\),\s*\}\);""",
   "if (!await _safeCoupleSend(inquiryId, q)) return; // v160")

# ---- 3. a new thread's first message
rep("""          Future<void> send() async {
            up(() {
              busy = true;
              err = '';
            });
            try {
              final Map<String, dynamic>? refBy = _pendingReferral != null &&""",
"""          Future<void> send() async {
            up(() {
              busy = true;
              err = '';
            });
            // v160: the first message gets the safety check before the thread exists
            final Map<String, dynamic> pre =
                await _safetyFirstCheck(placeId, msgC.text.trim());
            if (pre['held'] == true) {
              up(() => busy = false);
              await _safetyNudge(null, pre);
              return;
            }
            try {
              final Map<String, dynamic>? refBy = _pendingReferral != null &&""")

# ---- 4. helpers
rep("""  Future<void> _coupleSend(
      String inquiryId,""", r"""  // ------------------------------------------------------------------ v160
  // SAFETY: "LET'S GET ON A ZOOM CALL".  JC-LAZO-SAFETY-1016-COUPLE
  // A scam is working through wedding vendors: a fake couple pulls the vendor
  // onto an outside video call, plays porn on camera, screenshots it and
  // demands money. Couple messages go through sendThreadMessage, which holds
  // an outside call app or link, a video-call request, or (in the first few
  // messages) a phone number or email, and answers with a nudge to use Lazo.
  Future<bool> _safeCoupleSend(String inquiryId, String text) async {
    try {
      final HttpsCallableResult<dynamic> out = await FirebaseFunctions.instance
          .httpsCallable('sendThreadMessage')
          .call(<String, dynamic>{'inquiryId': inquiryId, 'text': text});
      final Map<String, dynamic> r = Map<String, dynamic>.from(
          (out.data as Map?) ?? <String, dynamic>{});
      if (r['ok'] == true) return true;
      if (r['held'] == true) {
        await _safetyNudge(inquiryId, r);
        return false;
      }
      _toast('Could not send that just now. Try again.');
      return false;
    } on FirebaseFunctionsException catch (e) {
      final dynamic d = e.details;
      if (d is Map && d['code'] == 'account-under-review') {
        await _safetyNudge(inquiryId, <String, dynamic>{
          'blocked': true,
          'nudge': (d['nudge'] ?? '').toString(),
        });
        return false;
      }
      _toast(_lzFnMsg(e, 'Could not send that just now. Try again.'));
      return false;
    } catch (_) {
      _toast('Could not send that just now. Check your connection and try again.');
      return false;
    }
  }

  // The same check for a new thread's first message, before it exists. A
  // network failure lets it through: the rules still refuse an outside link.
  Future<Map<String, dynamic>> _safetyFirstCheck(
      String vendorId, String text) async {
    if (text.isEmpty) return <String, dynamic>{};
    try {
      final HttpsCallableResult<dynamic> out = await FirebaseFunctions.instance
          .httpsCallable('safetyPrecheck')
          .call(<String, dynamic>{'vendorId': vendorId, 'text': text});
      return Map<String, dynamic>.from(
          (out.data as Map?) ?? <String, dynamic>{});
    } catch (_) {
      return <String, dynamic>{};
    }
  }

  Future<void> _safetyNudge(String? inquiryId, Map<String, dynamic> r) async {
    if (!mounted) return;
    final bool blocked = r['blocked'] == true;
    final bool video = (r['reason'] ?? '') == 'video';
    String nudge = (r['nudge'] ?? '').toString();
    if (blocked && nudge.isEmpty) {
      nudge =
          'Your account is under review. Contact support@meetlazo.com and we’ll sort it out.';
    }
    if (!blocked && video && inquiryId == null) {
      nudge =
          'Video calls happen inside Lazo, so you and your vendor are both protected. Send your note without the outside call, and once you’re talking you can request a Lazo video call right in the conversation.';
    }
    bool busy = false;
    bool open = true;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 480),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setN) {
          void up(VoidCallback f) {
            if (open) setN(f);
          }

          Future<void> requestCall() async {
            up(() => busy = true);
            try {
              await FirebaseFunctions.instance
                  .httpsCallable('sendThreadMessage')
                  .call(<String, dynamic>{
                'inquiryId': inquiryId,
                'callRequest': true,
              });
              if (ctx2.mounted) Navigator.pop(ctx2);
              _toast(
                  'Asked for a Lazo video call ✓ They’ll reply with a time.');
            } catch (e) {
              up(() => busy = false);
              _toast(_lzFnMsg(e, 'Could not send that just now. Try again.'));
            }
          }

          return _lzFrame(ctx2,
              icon: blocked ? Icons.shield_outlined : Icons.videocam_rounded,
              title: blocked
                  ? 'Account under review'
                  : (video
                      ? 'Let’s keep calls in Lazo'
                      : 'Keep the first messages in Lazo'),
              children: <Widget>[
                const SizedBox(height: 10),
                Text(nudge,
                    style: TextStyle(
                        color: _lzFg(ink), fontSize: 14, height: 1.5)),
                if (blocked) ...<Widget>[
                  const SizedBox(height: 12),
                  _lzNote(Icons.mail_outline_rounded, 'support@meetlazo.com'),
                ],
              ],
              footer: (!blocked && video && inquiryId != null)
                  ? _lzActions(
                      secondary: 'Edit my message',
                      onSecondary: () => Navigator.pop(ctx2),
                      primary: 'Request a Lazo video call',
                      icon: Icons.videocam_rounded,
                      busy: busy,
                      onPrimary: requestCall)
                  : _lzActions(
                      primary: blocked ? 'OK' : 'Edit my message',
                      onPrimary: () => Navigator.pop(ctx2)));
        },
      ),
    ).whenComplete(() => open = false);
  }

  Future<void> _coupleSend(
      String inquiryId,""")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name}: {len(s):,} chars")

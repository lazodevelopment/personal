"""Vendor v200: SAFETY - "let's get on a Zoom call" (JC-LAZO-SAFETY-1016-VENDOR).

    python app-patches\\patch_vendor_v200.py [base.txt]   # base defaults to Vendor_master_v199.txt
                                                          # writes Vendor_master_v200.txt

Re-runnable on any later master that still has these anchors (v201-v203
branch from v199 too; run it on the merged master when they come together).

What changes (vendors are never filtered or blocked):
  - Composer: an outside video link or a video-call ask opens a warning first:
    "Send my booking link" (the Lazo consult scheduler) or "Send anyway". Sent
    anyway goes through sendThreadMessage with confirm:true, so it is logged
    for review. Ordinary messages keep their direct path.
  - Thread header: a shield button - Report or block this couple
    (reportCouple / blockCouple in functions-dashboard/safety.js), Unblock.
  - Safety strip on the thread: Lazo blocked this account / you blocked them /
    this lead asked to move to an outside video call (safetyFlag from
    website-form, text and booking leads).
  - A couple message with safetyFlag gets a small scam note under it; a
    couple's Lazo video call request gets a "Send my booking link" chip.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v199.txt"
DST = HERE / "Vendor_master_v200.txt"
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, f"expected {n}, found {c}: {a[:90]!r}"
    s = s.replace(a, b)


# ---- header
first_build = s.index("// Build ID:")
s = s[:first_build] + (
    "// Build ID: JC-LAZO-SAFETY-1016-VENDOR (v200: SAFETY - \"let's get on a Zoom call\": an outside video link in the composer gets a "
    "warning first (Send my booking link / Send anyway, logged through sendThreadMessage); a shield in the thread header reports or blocks "
    "the couple (reportCouple / blockCouple); a safety strip for blocked accounts, blocked threads and leads that asked for an outside call; "
    "a scam note under flagged messages and a booking-link chip under a couple's Lazo video call request)\n"
) + s[first_build:]

# ---- 1. _sendVendorMessage: optional path through the callable
rep("""  Future<void> _sendVendorMessage(
      String inquiryId, String text, String status) async {
    final DocumentReference<Map<String, dynamic>> ref =
        FirebaseFirestore.instance.collection('inquiries').doc(inquiryId);
    await ref.collection('messages').add(<String, dynamic>{
      'senderRole': 'vendor',
      'text': text,
      'at': FieldValue.serverTimestamp(),
    });
""", """  Future<void> _sendVendorMessage(
      String inquiryId, String text, String status,
      {bool viaSafety = false}) async {
    final DocumentReference<Map<String, dynamic>> ref =
        FirebaseFirestore.instance.collection('inquiries').doc(inquiryId);
    if (viaSafety) {
      // v200: sent anyway after the outside-call warning - logged for review
      await FirebaseFunctions.instance
          .httpsCallable('sendThreadMessage')
          .call(<String, dynamic>{
        'inquiryId': inquiryId,
        'text': text,
        'confirm': true,
      });
    } else {
      await ref.collection('messages').add(<String, dynamic>{
        'senderRole': 'vendor',
        'text': text,
        'at': FieldValue.serverTimestamp(),
      });
    }
""")

# ---- 2. composer
rep("""    final String tx = _inboxMsgC.text.trim();
    if (tx.isEmpty) {
      return;
    }
    setState(() => _inboxSending = true);
    try {
      await _sendVendorMessage(inquiryId, tx, 'responded');
""", """    final String tx = _inboxMsgC.text.trim();
    if (tx.isEmpty) {
      return;
    }
    // v200: an outside video link gets the warning first
    bool viaSafety = false;
    if (_offPlatformCall(tx)) {
      final String pick = await _offPlatformWarning(inquiryId);
      if (pick != 'anyway') {
        return;
      }
      viaSafety = true;
    }
    setState(() => _inboxSending = true);
    try {
      await _sendVendorMessage(inquiryId, tx, 'responded',
          viaSafety: viaSafety);
""")

# ---- 3. header shield
rep("""            if ((inq['status'] ?? '') != 'booked' &&
                (inq['status'] ?? '') != 'lost' &&
                inq['demo'] != true)
              Builder(builder: (BuildContext fc) {
                final _Fit fit = _fitOf(""", """            if (inq['demo'] != true &&
                !(inq['coupleUid'] ?? '').toString().startsWith('lead_'))
              IconButton(
                tooltip: 'Report or block',
                visualDensity: VisualDensity.compact,
                icon: Icon(
                    inq['blockedByVendor'] == true
                        ? Icons.shield_rounded
                        : Icons.shield_outlined,
                    color: _lzFg(inq['blockedByVendor'] == true
                        ? const Color(0xFFB3261E)
                        : muted),
                    size: 20),
                onPressed: _h(() => _coupleSafetySheet(inquiryId, inq)),
              ),
            if ((inq['status'] ?? '') != 'booked' &&
                (inq['status'] ?? '') != 'lost' &&
                inq['demo'] != true)
              Builder(builder: (BuildContext fc) {
                final _Fit fit = _fitOf(""")

# ---- 4. safety strip
rep("""                _practiceStrip(inquiryId, inq, vendorId),
                _leadSourceStrip(inquiryId, inq),""", """                _safetyStrip(inquiryId, inq),
                _practiceStrip(inquiryId, inq, vendorId),
                _leadSourceStrip(inquiryId, inq),""")

# ---- 5. per-message notes
rep("""                    onLongPress: mine
                        ? () => _editMessageDialog(inquiryId, mdocs[i].id,
                            (mm['text'] ?? '').toString())
                        : null));
              }
              if (bubbles.isEmpty) {""", """                    onLongPress: mine
                        ? () => _editMessageDialog(inquiryId, mdocs[i].id,
                            (mm['text'] ?? '').toString())
                        : null));
                // v200: safety notes under a couple's message
                if (!mine && mm['safetyFlag'] is Map) {
                  bubbles.add(_safetyMsgNote());
                }
                if (!mine && mm['callRequest'] == true) {
                  bubbles.add(_callRequestChip(inquiryId, inq));
                }
              }
              if (bubbles.isEmpty) {""")

# ---- 6. helpers
rep("""  // v148: a draft belongs to a couple, not to the composer.""", r"""  // ------------------------------------------------------------------ v200
  // SAFETY: "LET'S GET ON A ZOOM CALL".  JC-LAZO-SAFETY-1016-VENDOR
  // A scam is working through wedding vendors on Zola and The Knot: a fake
  // couple pulls the vendor onto an outside video call, plays porn on camera,
  // screenshots it and demands money. Couples' outside-call asks are held on
  // the server (safety-guard.js); vendors are warned, never blocked.
  static final RegExp _kOffCallStrong = RegExp(
      r'(zoom\.us|meet\.google|teams\.microsoft|teams\.live|wa\.me/|whats ?app|face ?time|telegram|skype|webex|whereby|google meet|\bg-?meet\b|\bzoom (call|meeting|link|chat|id|invite)|\b(on|via|over) zoom\b(?! ?(lens|in\b|out\b|shot)))',
      caseSensitive: false);
  static final RegExp _kOffCallWeak = RegExp(
      r'\b(video|vid|virtual) ?(call|chat|meeting)s?\b',
      caseSensitive: false);
  bool _offPlatformCall(String t) =>
      _kOffCallStrong.hasMatch(t) || _kOffCallWeak.hasMatch(t);

  // 'booking' (sent the booking link instead), 'anyway', or '' (edit)
  Future<String> _offPlatformWarning(String inquiryId) async {
    if (!mounted) return '';
    final String? pick = await _lzSheet<String>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 480),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.shield_outlined,
          title: 'Keep this call in Lazo',
          children: <Widget>[
            const SizedBox(height: 10),
            Text(
                'Outside video links aren’t protected. A scam going around wedding vendors starts exactly here: a “couple” asks for a Zoom or FaceTime call, records it, then demands money.',
                style: TextStyle(color: _lzFg(ink), fontSize: 14, height: 1.5)),
            const SizedBox(height: 10),
            Text(
                'Send your Lazo booking link instead. They pick a time and everything stays in this conversation.',
                style: TextStyle(color: _lzFg(ink), fontSize: 14, height: 1.5)),
            const SizedBox(height: 12),
            _lzNote(Icons.edit_rounded, 'Close this to edit your message.'),
          ],
          footer: _lzActions(
              secondary: 'Send anyway',
              onSecondary: () => Navigator.pop(ctx, 'anyway'),
              primary: 'Send my booking link',
              icon: Icons.event_available_rounded,
              onPrimary: () => Navigator.pop(ctx, 'booking'))),
    );
    if (pick == 'booking') {
      try {
        final DocumentSnapshot<Map<String, dynamic>> d = await FirebaseFirestore
            .instance
            .collection('inquiries')
            .doc(inquiryId)
            .get();
        await _sendBookingLink(inquiryId, d.data() ?? <String, dynamic>{});
      } catch (e) {
        _toast('Could not send the booking link: ' + _errText(e));
      }
    }
    return pick ?? '';
  }

  Widget _safetyStrip(String inquiryId, Map<String, dynamic> inq) {
    String text;
    Color c;
    IconData icon = Icons.shield_outlined;
    if (inq['coupleSafetyBlocked'] == true) {
      text =
          'Lazo blocked this account for safety: it tried to move vendors to an outside video call. Don’t join any call or open any link from them.';
      c = const Color(0xFFB3261E);
      icon = Icons.gpp_bad_outlined;
    } else if (inq['blockedByVendor'] == true) {
      text = 'You blocked this couple. They can’t message you here.';
      c = muted;
    } else if (inq['safetyFlag'] is Map) {
      text =
          'This lead asked to move to an outside video call. A known scam against wedding vendors starts this way. Keep it in Lazo and send your booking link.';
      c = const Color(0xFF8A6A2F);
      icon = Icons.warning_amber_rounded;
    } else {
      return const SizedBox.shrink();
    }
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 10, 16, 0),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: _lzBg(c.withOpacity(.10)),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _lzLine(c.withOpacity(.5))),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Icon(icon, size: 18, color: _lzFg(c)),
        const SizedBox(width: 10),
        Expanded(
            child: Text(text,
                style: TextStyle(
                    color: _lzFg(ink), fontSize: 12.5, height: 1.45))),
        if (inq['coupleSafetyBlocked'] != true)
          TextButton(
            onPressed: _h(() => _coupleSafetySheet(inquiryId, inq)),
            child: Text(inq['blockedByVendor'] == true ? 'Unblock' : 'Report',
                style: TextStyle(
                    color: _lzFg(plum), fontSize: 12, fontWeight: FontWeight.w800)),
          ),
      ]),
    );
  }

  Widget _safetyMsgNote() => Padding(
        padding: const EdgeInsets.only(left: 6, bottom: 10),
        child: Row(children: <Widget>[
          Icon(Icons.warning_amber_rounded,
              size: 14, color: _lzFg(const Color(0xFF8A6A2F))),
          const SizedBox(width: 5),
          Expanded(
            child: Text(
                'Asked for an outside video call. Don’t join links from people you haven’t met.',
                style: TextStyle(color: _lzFg(muted), fontSize: 11.5)),
          ),
        ]),
      );

  Widget _callRequestChip(String inquiryId, Map<String, dynamic> inq) =>
      Padding(
        padding: const EdgeInsets.only(left: 6, bottom: 10),
        child: Align(
          alignment: Alignment.centerLeft,
          child: OutlinedButton.icon(
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
        ),
      );

  // Report or block a couple (functions-dashboard/safety.js). Blocking is for
  // this conversation; Lazo reviews reports and can block the account.
  Future<void> _coupleSafetySheet(
      String inquiryId, Map<String, dynamic> inq) async {
    final String who = (inq['coupleName'] ?? '').toString().isEmpty
        ? 'this couple'
        : (inq['coupleName'] ?? '').toString();
    final bool isBlocked = inq['blockedByVendor'] == true;
    final TextEditingController detailC = TextEditingController();
    String reason = '';
    bool busy = false;
    bool open = true;
    String err = '';
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setR) {
          void up(VoidCallback f) {
            if (open) setR(f);
          }

          Future<void> block(bool on) async {
            up(() {
              busy = true;
              err = '';
            });
            try {
              await FirebaseFunctions.instance
                  .httpsCallable('blockCouple')
                  .call(<String, dynamic>{'inquiryId': inquiryId, 'blocked': on});
              if (ctx2.mounted) Navigator.pop(ctx2);
              _toast(on ? 'Blocked. They can’t message you here.' : 'Unblocked.');
            } catch (e) {
              up(() {
                busy = false;
                err = _lzFnMsg(e, 'Could not do that just now. Try again.');
              });
            }
          }

          Future<void> report() async {
            up(() {
              busy = true;
              err = '';
            });
            try {
              await FirebaseFunctions.instance
                  .httpsCallable('reportCouple')
                  .call(<String, dynamic>{
                'inquiryId': inquiryId,
                'reason': reason,
                'detail': detailC.text.trim(),
              });
              if (ctx2.mounted) Navigator.pop(ctx2);
              _toast('Thank you. They’re blocked here and our team is looking into it.');
            } catch (e) {
              up(() {
                busy = false;
                err = _lzFnMsg(e, 'Could not send that just now. Try again.');
              });
            }
          }

          if (isBlocked) {
            return _lzFrame(ctx2,
                icon: Icons.shield_rounded,
                title: 'You blocked $who',
                subtitle: 'They can’t message you in this conversation.',
                children: <Widget>[
                  const SizedBox(height: 10),
                  if (err.isNotEmpty)
                    Text(err,
                        style: const TextStyle(
                            color: Color(0xFFB3261E), fontSize: 12.5)),
                ],
                footer: _lzActions(
                    secondary: 'Close',
                    onSecondary: () => Navigator.pop(ctx2),
                    primary: 'Unblock',
                    busy: busy,
                    onPrimary: () => block(false)));
          }

          Widget pill(String key, String label) {
            final bool on = reason == key;
            return ChoiceChip(
              label: Text(label),
              selected: on,
              onSelected: (_) => up(() => reason = key),
              selectedColor: _lzBg(const Color(0xFFB3261E).withOpacity(.14)),
              labelStyle: TextStyle(
                  color: _lzFg(on ? const Color(0xFFB3261E) : ink),
                  fontSize: 12.5,
                  fontWeight: FontWeight.w700),
            );
          }

          return _lzFrame(ctx2,
              icon: Icons.flag_rounded,
              title: 'Report or block $who',
              subtitle: 'A real person on the Lazo team reads every report.',
              children: <Widget>[
                const SizedBox(height: 12),
                _lzNote(Icons.shield_outlined,
                    'Being pressured for money after a call? Don’t pay and don’t reply. Report it here and keep everything. You can also report it to the FBI at ic3.gov.'),
                _lzSection('What happened'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  pill('offplatform_call', 'Wanted an outside video call'),
                  pill('extortion', 'Threats or demands for money'),
                  pill('inappropriate', 'Sexual or inappropriate'),
                  pill('harassment', 'Harassment'),
                  pill('scam', 'Scam or fake couple'),
                  pill('spam', 'Spam'),
                  pill('other', 'Something else'),
                ]),
                const SizedBox(height: 14),
                TextField(
                  controller: detailC,
                  minLines: 3,
                  maxLines: 6,
                  textCapitalization: TextCapitalization.sentences,
                  style: TextStyle(color: _lzFg(ink), fontSize: 14),
                  decoration: const InputDecoration(
                      labelText: 'Details (optional)',
                      hintText: 'Anything that helps us act faster',
                      border: OutlineInputBorder()),
                ),
                const SizedBox(height: 10),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton(
                    onPressed: busy ? null : () => block(true),
                    child: Text('Just block them, no report',
                        style: TextStyle(
                            color: _lzFg(plum),
                            fontSize: 12.5,
                            fontWeight: FontWeight.w800)),
                  ),
                ),
                if (err.isNotEmpty)
                  Text(err,
                      style: const TextStyle(
                          color: Color(0xFFB3261E), fontSize: 12.5)),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: 'Report and block',
                  icon: Icons.flag_rounded,
                  danger: true,
                  busy: busy,
                  onPrimary: reason.isEmpty ? null : report));
        },
      ),
    ).whenComplete(() => open = false);
  }

  // v148: a draft belongs to a couple, not to the composer.""")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name}: {len(s):,} chars")

"""Vendor v218: clear the inbox, report spam on any lead (JC-LAZO-INBOXCLEAR-1018-VENDOR).

    python app-patches\\patch_vendor_v218.py [base.txt]   # base defaults to Vendor_master_v217.txt
                                                          # writes Vendor_master_v218.txt
- Inbox: threads marked Lost (or closed) leave All / Unread / New / Replied; a new "Lost" filter
  shows them. Mark lost stamps inquiries.lostAt; a couple message after that brings the thread back.
- Off-platform leads (website form, Zola/Knot forwards, booking link, added clients) get the
  shield too: "Report or remove" opens a sheet with Spam or scam (reports it to the Lazo team,
  blocks the sender's email and phone on your listing - vendors.blockedSenders, which the lead
  form and leads@ now honour - and clears the thread), Not a fit (clears the thread), or Keep.
  Lazo-account couples keep the existing Report or block sheet.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v217.txt"
DST = HERE / "Vendor_master_v218.txt"
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
    "// Build ID: JC-LAZO-INBOXCLEAR-1018-VENDOR (v218: CLEAR THE INBOX - Lost threads leave the inbox and live under a "
    "Lost filter; off-platform leads get Report or remove: Spam or scam reports it, blocks the sender on your listing "
    "(vendors.blockedSenders) and clears the thread, Not a fit clears it; base v217)\n"
) + s[first_build:]

# ---- inbox: hide lost unless the Lost filter is on
rep("""            final String st = (m['status'] ?? 'new').toString();
            if (_inboxFilter == 'unread' && !_isUnread(m)) return false;
            if (_inboxFilter == 'new' && !(st == 'new' || st.isEmpty)) {
              return false;
            }
            if (_inboxFilter == 'responded' && st != 'responded') return false;
            if (_inboxFilter == 'booked' && st != 'booked') return false;""",
    """            final String st = (m['status'] ?? 'new').toString();
            // v218: lost threads leave the inbox; the Lost filter is where they live.
            // A message from the couple after Mark lost brings the thread back.
            final DateTime? lostAt = (m['lostAt'] as Timestamp?)?.toDate();
            final DateTime? lastAt = (m['lastMessageAt'] as Timestamp?)?.toDate();
            final bool cameBack = (m['lastMessageRole'] ?? '') == 'couple' &&
                lostAt != null && lastAt != null && lastAt.isAfter(lostAt);
            final bool gone = (st == 'lost' || st == 'closed') && !cameBack;
            if (_inboxFilter == 'lost') return gone;
            if (gone) return false;
            if (_inboxFilter == 'unread' && !_isUnread(m)) return false;
            if (_inboxFilter == 'new' && !(st == 'new' || st.isEmpty)) {
              return false;
            }
            if (_inboxFilter == 'responded' && st != 'responded') return false;
            if (_inboxFilter == 'booked' && st != 'booked') return false;""")
rep("""              <String>['responded', 'Replied'],
              <String>['booked', 'Booked'],
            ].map((List<String> f) {""",
    """              <String>['responded', 'Replied'],
              <String>['booked', 'Booked'],
              <String>['lost', 'Lost'],
            ].map((List<String> f) {""")

# ---- Mark lost stamps lostAt (the inbox uses it to tell a later couple message apart)
rep("""    if (status == 'booked') {
      update['bookedAt'] = FieldValue.serverTimestamp();
    }
    await FirebaseFirestore.instance
        .collection('inquiries')
        .doc(id)
        .update(update);""",
    """    if (status == 'booked') {
      update['bookedAt'] = FieldValue.serverTimestamp();
    }
    if (status == 'lost') {
      update['lostAt'] = FieldValue.serverTimestamp(); // v218
    }
    await FirebaseFirestore.instance
        .collection('inquiries')
        .doc(id)
        .update(update);""")

# ---- thread header: the shield for off-platform leads too
rep("""            if (inq['demo'] != true &&
                !(inq['coupleUid'] ?? '').toString().startsWith('lead_'))
              IconButton(
                tooltip: 'Report or block',""",
    """            // v218: off-platform leads get their own sheet (report spam, block the sender, clear)
            if (inq['demo'] != true &&
                (inq['coupleUid'] ?? '').toString().startsWith('lead_'))
              IconButton(
                tooltip: 'Report or remove',
                visualDensity: VisualDensity.compact,
                icon: Icon(Icons.shield_outlined, color: _lzFg(muted), size: 20),
                onPressed: _h(() => _leadSafetySheet(inquiryId, inq)),
              ),
            if (inq['demo'] != true &&
                !(inq['coupleUid'] ?? '').toString().startsWith('lead_'))
              IconButton(
                tooltip: 'Report or block',""")

NEW = r'''
  // v218: an off-platform lead (form, forward, booking link, added client) can be reported as spam,
  // its sender blocked on this listing, and the thread cleared from the inbox.
  Future<void> _leadSafetySheet(String inquiryId, Map<String, dynamic> inq) async {
    final Map<String, dynamic> c = Map<String, dynamic>.from((inq['contact'] as Map?) ?? <String, dynamic>{});
    final String email = (c['email'] ?? '').toString().trim().toLowerCase();
    final String phone = (c['phone'] ?? '').toString().trim();
    final String who = (inq['coupleName'] ?? 'this lead').toString();
    final String vendorId = (inq['vendorId'] ?? _vendorIdCache).toString();
    Widget opt(IconData ic, String title, String note, Color tone, Future<void> Function() go) {
      return _Press(
        onTap: () async {
          Navigator.of(context).pop();
          await go();
        },
        child: Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
          decoration: BoxDecoration(
              color: _lzBg(Colors.white),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: _lzLine(tone.withOpacity(.45)))),
          child: Row(children: <Widget>[
            Container(
                width: 36, height: 36,
                decoration: BoxDecoration(shape: BoxShape.circle, color: _lzBg(tone.withOpacity(.12))),
                child: Icon(ic, size: 18, color: _lzFg(tone))),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                Text(title, style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: _lzFg(tone))),
                Text(note, style: TextStyle(fontSize: 12, height: 1.35, color: _lzFg(muted))),
              ]),
            ),
            Icon(Icons.chevron_right_rounded, size: 18, color: _lzFg(muted)),
          ]),
        ),
      );
    }

    Future<void> clear(String reason) async {
      final bool ok = await _setStatus(inquiryId, 'lost');
      if (ok) {
        try {
          await FirebaseFirestore.instance.collection('inquiries').doc(inquiryId).set(
              <String, dynamic>{'lostReason': reason}, SetOptions(merge: true));
        } catch (_) {}
      }
    }

    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.shield_outlined,
          title: 'Report or remove',
          subtitle: '$who came in from outside Lazo. Nothing here is sent to them.',
          children: <Widget>[
            opt(Icons.report_rounded, 'Spam or scam',
                'Reports it to the Lazo team, blocks ${email.isNotEmpty ? email : (phone.isNotEmpty ? phone : 'this sender')} on your listing so they can’t come back through your form or forwards, and clears the thread.',
                const Color(0xFFB3261E), () async {
              try {
                await FirebaseFunctions.instance.httpsCallable('reportCouple').call(<String, dynamic>{
                  'inquiryId': inquiryId, 'reason': 'spam', 'detail': 'Off-platform lead marked spam by the vendor; sender blocked on the listing.',
                });
              } catch (_) {}
              final List<String> block = <String>[if (email.isNotEmpty) email, if (phone.isNotEmpty) phone];
              if (block.isNotEmpty && vendorId.isNotEmpty) {
                try {
                  await FirebaseFirestore.instance.collection('vendors').doc(vendorId).set(
                      <String, dynamic>{'blockedSenders': FieldValue.arrayUnion(block)}, SetOptions(merge: true));
                } catch (_) {}
              }
              await clear('spam');
              _toast('Reported and cleared. ${block.isNotEmpty ? 'That sender is blocked on your listing.' : ''}');
            }),
            opt(Icons.do_not_disturb_on_outlined, 'Not a fit',
                'Clears the thread from your inbox. It stays under Lost, and a reply from them brings it back.',
                plum, () async {
              await clear('not-a-fit');
              _toast('Cleared. Find it under Lost if you need it.');
            }),
            if (email.isNotEmpty || phone.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 2, bottom: 6),
                child: Text('Blocked senders are kept on your listing under Account › Lead form. Lazo also reviews every spam report.',
                    style: TextStyle(fontSize: 11.5, color: _lzFg(muted))),
              ),
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: Text('Keep it', style: TextStyle(fontSize: 13, color: _lzFg(muted))),
            ),
          ]),
    );
  }

  Future<void> _coupleSafetySheet('''
rep("\n  Future<void> _coupleSafetySheet(", NEW)

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")

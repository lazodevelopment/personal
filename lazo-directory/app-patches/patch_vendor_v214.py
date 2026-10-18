"""Vendor v214: Part 3 before-launch gaps (JC-LAZO-GAPS-1018-VENDOR).

    python app-patches\\patch_vendor_v214.py [base.txt]   # base defaults to Vendor_master_v213.txt
                                                          # writes Vendor_master_v214.txt
- Automations: one page for every rule Lazo runs for the vendor - auto-reply to new
  inquiries (on/off, June's words or yours, the instant / day-3 / day-5 texts), review
  request after each wedding, the morning brief, a Google review link that rides along
  with the review request (vendors.googleReviewUrl), and the always-on rules listed
  plainly (quiet-lead follow-ups, final-count reminders, COI renewals, consult reminders).
  From Account > Your business, What you can do, and the Reviews card.
- Export your data: leads and payments as CSV (download on web, copied on phones).
Server note: functions/reviews.js should add the vendor's googleReviewUrl to the stage-1
email when set; see prelaunch-build-2026-10-18.md.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v213.txt"
DST = HERE / "Vendor_master_v214.txt"
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
    "// Build ID: JC-LAZO-GAPS-1018-VENDOR (v214: AUTOMATIONS + EXPORT - an Automations page with every rule Lazo runs "
    "for the vendor (auto-reply and its texts, review requests, morning brief, a Google review link, the always-on rules "
    "listed plainly) from Account, What you can do and the Reviews card; leads and payments as CSV from Account; base v213)\n"
) + s[first_build:]

NEW_METHODS = r'''
  // ---------------- v214: AUTOMATIONS + EXPORT ----------------
  Future<void> _setVendorField(String vendorId, Map<String, dynamic> data) async {
    if (vendorId.isEmpty) return;
    try {
      await FirebaseFirestore.instance.collection('vendors').doc(vendorId).set(data, SetOptions(merge: true));
    } catch (e) {
      _toast('Could not save: ' + _errText(e));
    }
  }

  Future<void> _automationsSheet(String vendorId) async {
    if (vendorId.isEmpty) return;
    final TextEditingController gC = TextEditingController(
        text: (_liveD['vendor:$vendorId']?.latest?.data()?['googleReviewUrl'] ?? '').toString());
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 640),
      builder: (BuildContext ctx) => StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
        stream: _liveDoc('vendor:$vendorId', () => FirebaseFirestore.instance.collection('vendors').doc(vendorId)),
        initialData: _liveD['vendor:$vendorId']?.latest,
        builder: (BuildContext c2, AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> sn) {
          final Map<String, dynamic> vd = sn.data?.data() ?? <String, dynamic>{};
          final Map<String, dynamic> ar = vd['autoReply'] is Map ? Map<String, dynamic>.from(vd['autoReply'] as Map) : <String, dynamic>{};
          final bool arOn = ar['enabled'] == true;
          final String arMode = (ar['mode'] ?? 'june').toString();
          final bool reviews = vd['reviewRequestsEnabled'] != false;
          final Map<String, dynamic> db = vd['dailyBrief'] is Map ? Map<String, dynamic>.from(vd['dailyBrief'] as Map) : <String, dynamic>{};
          final bool brief = db['enabled'] == true;
          Widget rule(IconData ic, String title, String note, {bool? on, ValueChanged<bool>? onChanged, Widget? extra}) {
            return Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
              decoration: BoxDecoration(
                  color: _lzBg(Colors.white),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: _lzLine(const Color(0xFFEADFD3)))),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                Row(children: <Widget>[
                  Icon(ic, size: 18, color: _lzFg(plum)),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      Text(title, style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: _lzFg(plum))),
                      Text(note, style: TextStyle(fontSize: 12, height: 1.35, color: _lzFg(muted))),
                    ]),
                  ),
                  if (on == null)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(color: _lzBg(const Color(0xFFE6F2EC)), borderRadius: BorderRadius.circular(999)),
                      child: const Text('ALWAYS ON', style: TextStyle(fontSize: 9, letterSpacing: 1.2, fontWeight: FontWeight.w800, color: Color(0xFF2E8B6B))),
                    )
                  else
                    Switch(value: on, activeColor: plum, activeTrackColor: gold, onChanged: onChanged),
                ]),
                if (extra != null) extra,
              ]),
            );
          }

          return _lzFrame(ctx,
              icon: Icons.bolt_rounded,
              title: 'Automations',
              subtitle: 'Everything Lazo does for you without being asked. Switch any of it off.',
              children: <Widget>[
                rule(Icons.reply_rounded, 'Reply to new inquiries',
                    arMode == 'own' ? 'The instant reply in your words, then day-3 and day-5 nudges if they go quiet.' : 'June answers in your voice within a minute, then nudges on day 3 and day 5 if they go quiet.',
                    on: arOn,
                    onChanged: (bool v) => _setVendorField(vendorId, <String, dynamic>{'autoReply': <String, dynamic>{'enabled': v}}),
                    extra: arOn
                        ? Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                              ChoiceChip(
                                label: Text('June writes them', style: TextStyle(fontSize: 12, color: arMode == 'june' ? plum : _lzFg(plum))),
                                selected: arMode == 'june', selectedColor: gold, backgroundColor: _lzBg(Colors.white), side: BorderSide(color: gold.withOpacity(.6)),
                                onSelected: (_) => _setVendorField(vendorId, <String, dynamic>{'autoReply': <String, dynamic>{'mode': 'june'}}),
                              ),
                              ChoiceChip(
                                label: Text('My own words', style: TextStyle(fontSize: 12, color: arMode == 'own' ? plum : _lzFg(plum))),
                                selected: arMode == 'own', selectedColor: gold, backgroundColor: _lzBg(Colors.white), side: BorderSide(color: gold.withOpacity(.6)),
                                onSelected: (_) => _setVendorField(vendorId, <String, dynamic>{'autoReply': <String, dynamic>{'mode': 'own'}}),
                              ),
                              TextButton(
                                onPressed: () { Navigator.of(ctx).pop(); _openProfileEditor(vendorId, vd); },
                                child: Text('Edit the texts →', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: _lzFg(plum))),
                              ),
                            ]),
                          )
                        : null),
                rule(Icons.star_rounded, 'Ask for a review after each wedding',
                    'Three days after, in your name; two gentle nudges on day 10 and day 20. Verified reviews drive your ranking.',
                    on: reviews,
                    onChanged: (bool v) => _setVendorField(vendorId, <String, dynamic>{'reviewRequestsEnabled': v}),
                    extra: Padding(
                      padding: const EdgeInsets.only(top: 10),
                      child: Row(children: <Widget>[
                        Expanded(
                          child: TextField(
                            controller: gC,
                            style: TextStyle(color: _lzFg(ink), fontSize: 13),
                            decoration: _epDeco('Google review link (optional)', 'https://g.page/r/...'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        FilledButton(
                          style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plum, padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14)),
                          onPressed: () {
                            final String u = gC.text.trim();
                            if (u.isNotEmpty && !u.startsWith('http')) { _toast('Paste the full link, starting with https://'); return; }
                            _setVendorField(vendorId, <String, dynamic>{'googleReviewUrl': u});
                            _toast(u.isEmpty ? 'Google link removed.' : 'Saved - the review request will offer Google too.');
                          },
                          child: const Text('Save', style: TextStyle(fontWeight: FontWeight.w800)),
                        ),
                      ]),
                    )),
                rule(Icons.wb_sunny_rounded, 'Morning brief at 7am',
                    'Three lines by email: who is waiting, what is due, weddings this week.',
                    on: brief,
                    onChanged: (bool v) => _setVendorField(vendorId, <String, dynamic>{'dailyBrief': <String, dynamic>{'enabled': v, 'hour': 7}})),
                Padding(
                  padding: const EdgeInsets.fromLTRB(2, 6, 0, 8),
                  child: Text('ALWAYS ON', style: TextStyle(fontSize: 10.5, letterSpacing: 2, fontWeight: FontWeight.w800, color: _lzFg(plum))),
                ),
                rule(Icons.restaurant_rounded, 'Final meal counts', 'Couples get a reminder 7 days and 2 days before the final-count date you set.'),
                rule(Icons.verified_user_rounded, 'Insurance renewals', 'Venues and planners holding your COI get the new one; you get a nudge before it lapses.'),
                rule(Icons.event_available_rounded, 'Consult reminders', 'Both sides get a reminder the day before and 15 minutes before a consult or a scheduled call.'),
                rule(Icons.notifications_active_rounded, 'Quiet leads', 'June flags a couple who went silent after your reply, and a nudge is one tap on Today.'),
              ]);
        },
      ),
    );
  }

  String _csvCellV(Object? v) {
    String t = v == null ? '' : (v is Timestamp ? v.toDate().toIso8601String().substring(0, 10) : v.toString());
    if (t.contains(',') || t.contains('"') || t.contains('\n')) t = '"${t.replaceAll('"', '""')}"';
    return t;
  }

  void _deliverCsvV(String name, String csv) {
    if (!kIsWeb) {
      Clipboard.setData(ClipboardData(text: csv));
      _toast('Copied as CSV - paste it into Numbers, Sheets or an email.');
      return;
    }
    try {
      final html.Blob blob = html.Blob(<String>[csv], 'text/csv');
      final String url = html.Url.createObjectUrlFromBlob(blob);
      html.AnchorElement(href: url)
        ..setAttribute('download', name)
        ..click();
      html.Url.revokeObjectUrl(url);
    } catch (e) {
      Clipboard.setData(ClipboardData(text: csv));
      _toast('Copied as CSV.');
    }
  }

  Future<void> _exportSheetV(String vendorId) async {
    if (vendorId.isEmpty) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.download_rounded,
          title: 'Export your data',
          subtitle: 'Your leads and your money, as files you own.',
          children: <Widget>[
            _acctLive(Icons.inbox_rounded, 'Leads', 'Couple, wedding date, venue, status, stage, tags, first message, when they wrote.', () {
              final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs =
                  _liveQ['leads:$vendorId']?.latest?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
              final StringBuffer b = StringBuffer('couple,weddingDate,venue,status,stage,tags,message,createdAt,lastMessageAt\n');
              for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) {
                final Map<String, dynamic> m = d.data();
                final Map<String, dynamic> si = m['structuredIntent'] is Map ? Map<String, dynamic>.from(m['structuredIntent'] as Map) : <String, dynamic>{};
                b.writeln(<Object?>[
                  m['coupleName'], si['weddingDate'] ?? m['weddingDate'], si['venue'], m['status'], m['stage'],
                  ((m['tags'] as List?) ?? const <dynamic>[]).join(' '), m['message'] ?? si['message'], m['createdAt'], m['lastMessageAt'],
                ].map(_csvCellV).join(','));
              }
              _deliverCsvV('lazo-leads.csv', b.toString());
            }),
            _acctLive(Icons.payments_rounded, 'Payments', 'Every invoice: couple, title, total, status, due, paid.', () {
              final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs =
                  _liveQ['invoices:$vendorId']?.latest?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
              final StringBuffer b = StringBuffer('couple,title,total,status,dueDate,paidAt,createdAt\n');
              for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) {
                final Map<String, dynamic> m = d.data();
                b.writeln(<Object?>[m['coupleName'], m['title'], m['total'], m['status'], m['dueDate'], m['paidAt'], m['createdAt']].map(_csvCellV).join(','));
              }
              if (docs.isEmpty) _toast('Open Money once so the invoices load, then export.');
              _deliverCsvV('lazo-payments.csv', b.toString());
            }),
          ]),
    );
  }

'''

rep("  // ---------------- v213: FIRST SESSION, JUNE POINTERS, WHAT'S NEW ----------------\n",
    NEW_METHODS + "  // ---------------- v213: FIRST SESSION, JUNE POINTERS, WHAT'S NEW ----------------\n")

# Account > Your business: Automations + Export
rep("""                    _acctLive(Icons.calendar_month_rounded, 'Calendar feed', 'Booked weddings and blocked dates in Google or Apple Calendar.', () => _calendarFeedSheet(vendorId)),
""",
    """                    _acctLive(Icons.calendar_month_rounded, 'Calendar feed', 'Booked weddings and blocked dates in Google or Apple Calendar.', () => _calendarFeedSheet(vendorId)),
                    _acctLive(Icons.bolt_rounded, 'Automations', 'Auto-replies, review requests, reminders - every rule Lazo runs for you, with switches.', () => _automationsSheet(vendorId)),
                    _acctLive(Icons.download_rounded, 'Export your data', 'Leads and payments as CSV.', () => _exportSheetV(vendorId)),
""")

# What you can do: Automations tile
rep("""      <dynamic>['Leads', 'Add a client', 'A couple from outside Lazo: they sign and pay without an account', Icons.person_add_alt_1_rounded, false, () { if (vendorId.isNotEmpty) _addClientSheet(vendorId); }],""",
    """      <dynamic>['Leads', 'Add a client', 'A couple from outside Lazo: they sign and pay without an account', Icons.person_add_alt_1_rounded, false, () { if (vendorId.isNotEmpty) _addClientSheet(vendorId); }],
      <dynamic>['Leads', 'Automations', 'Auto-replies, follow-ups, review requests and reminders, each with a switch', Icons.bolt_rounded, true, () { _automationsSheet(vendorId); }],""")

# Reviews card: Google link line under the switch box
rep("""          const SizedBox(height: 12),
          StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
            stream: _liveQuery(
                'reviews:$vendorId',""",
    """          // v214: the Google review link rides along with the request
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: _Press(
              onTap: _h(() => _automationsSheet(vendorId)),
              child: Row(children: <Widget>[
                Icon(Icons.rate_review_rounded, size: 15, color: _lzFg(muted)),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                      (vd['googleReviewUrl'] ?? '').toString().trim().isEmpty
                          ? 'Add your Google review link and the request offers Google too'
                          : 'Also asks for a Google review \\u00b7 ${Uri.tryParse((vd['googleReviewUrl'] ?? '').toString())?.host ?? 'link set'}',
                      style: TextStyle(fontSize: 11.5, color: _lzFg(muted))),
                ),
                Icon(Icons.chevron_right_rounded, size: 16, color: _lzFg(muted)),
              ]),
            ),
          ),
          const SizedBox(height: 12),
          StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
            stream: _liveQuery(
                'reviews:$vendorId',""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")

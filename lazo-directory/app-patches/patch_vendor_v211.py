"""Vendor v211: pre-launch review fixes (JC-LAZO-PRELAUNCH-1018-VENDOR).

    python app-patches\\patch_vendor_v211.py [base.txt]   # base defaults to Vendor_master_v210.txt
                                                          # writes Vendor_master_v211.txt
- the past-due banner reads proSubscriptions/{vendorId} directly: the old list query
  (where vendorId == ...) can never pass the rule `allow read: if vendorAccess(vendorId)`
  on the doc-id wildcard, so a declined card never showed the banner
- the booking-link send and the meal-count ask no longer write lastMessageAt /
  lastMessageRole / lastMessagePreview on the inquiry (the live rules refuse those
  keys from a vendor, which left the booking link posted but a "Could not send" toast
  on screen); the server keeps those fields on every message create
- pipeline cards print the wedding date as "Mar 7, 2027", not the raw ISO string
- the inbox header no longer overflows on phones (Add a client and the chime toggle shrink to icons under 480 px)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v210.txt"
DST = HERE / "Vendor_master_v211.txt"
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
    "// Build ID: JC-LAZO-PRELAUNCH-1018-VENDOR (v211: PRE-LAUNCH FIXES - the declined-card banner reads the subscription "
    "doc itself (the list query was always refused by the rules); the booking link and the meal-count ask no longer touch "
    "the inquiry's last-message fields (the rules refuse them from a vendor, which showed 'Could not send' after the message "
    "had gone out); pipeline cards show a readable wedding date; the inbox header fits a phone; base v210)\n"
) + s[first_build:]

# ---- 1. past-due banner: doc stream instead of a list query
rep("""    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _liveQuery(
          'pastDue:$vendorId',
          () => FirebaseFirestore.instance
              .collection('proSubscriptions')
              .where('vendorId', isEqualTo: vendorId)
              .where('status', isEqualTo: 'past_due')
              .limit(1)),
      builder: (BuildContext c,
          AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> ps) {
        final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs =
            ps.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
        if (docs.isEmpty) return const SizedBox.shrink();
""",
    """    // v211: read the doc itself - the rules allow proSubscriptions/{vendorId} by id,
    // and a list query filtered on a field can never prove that, so it was refused.
    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: _liveDoc(
          'pastDue:$vendorId',
          () => FirebaseFirestore.instance
              .collection('proSubscriptions')
              .doc(vendorId)),
      builder: (BuildContext c,
          AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> ps) {
        final Map<String, dynamic> sub = ps.data?.data() ?? <String, dynamic>{};
        if ((sub['status'] ?? '') != 'past_due') return const SizedBox.shrink();
""")

# ---- 2. no vendor-side last-message writes (rules refuse them; the server keeps the fields)
rep("""      await FirebaseFirestore.instance
          .collection('inquiries')
          .doc(inquiryId)
          .set(<String, dynamic>{
        'lastMessageAt': FieldValue.serverTimestamp(),
        'lastMessageRole': 'vendor',
        'status':
            ((inq['status'] ?? '') == 'new' || (inq['status'] ?? '') == '')
                ? 'responded'
                : inq['status'],
        'respondedAt': inq['respondedAt'] ?? FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));""",
    """      // v211: only keys the rules allow a vendor to touch (the message trigger
      // maintains lastMessageAt / lastMessageRole / lastMessagePreview)
      await FirebaseFirestore.instance
          .collection('inquiries')
          .doc(inquiryId)
          .set(<String, dynamic>{
        'status':
            ((inq['status'] ?? '') == 'new' || (inq['status'] ?? '') == '')
                ? 'responded'
                : inq['status'],
        'respondedAt': inq['respondedAt'] ?? FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));""")
rep("""                try {
                  await FirebaseFirestore.instance
                      .collection('inquiries')
                      .doc(inquiryId)
                      .set(<String, dynamic>{
                    'lastMessageAt': FieldValue.serverTimestamp(),
                    'lastMessageRole': 'vendor',
                    'lastMessagePreview': 'Asked for updated meal choices',
                  }, SetOptions(merge: true));
                } catch (_) {}
""",
    """                // v211: the message trigger updates the thread's last-message
                // fields; a vendor write of those keys is refused by the rules
""")

# ---- 3. pipeline cards: readable date ("Mar 7, 2027" instead of "2027-03-07")
rep("""          if (wd.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child:
                  Text(wd, style:  TextStyle(fontSize: 11, color: _lzFg(muted))),
            ),""",
    """          if (wd.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child:
                  Text(_pipeWd(wd), style:  TextStyle(fontSize: 11, color: _lzFg(muted))),
            ),""")
rep("""  Widget _pipeCard(
      String vendorId, QueryDocumentSnapshot<Map<String, dynamic>> d) {""",
    """  // v211: a yyyy-mm-dd wedding date reads as "Mar 7, 2027"; anything else stays as typed
  static const List<String> _kPipeMon = <String>['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  String _pipeWd(String wd) {
    final RegExpMatch? m = RegExp(r'^(\d{4})-(\d{2})-(\d{2})').firstMatch(wd.trim());
    if (m == null) return wd;
    final int mo = int.tryParse(m.group(2)!) ?? 0;
    final int d = int.tryParse(m.group(3)!) ?? 0;
    if (mo < 1 || mo > 12 || d < 1) return wd;
    return '${_kPipeMon[mo - 1]} $d, ${m.group(1)}';
  }

  Widget _pipeCard(
      String vendorId, QueryDocumentSnapshot<Map<String, dynamic>> d) {""")

# ---- 4. inbox header: no overflow on phones (390 px: "Inbox · 2 new · Add a client · Alert Sound On" was 31 px too wide)
rep("""          const Spacer(),
          // v199: add a client from outside Lazo
          TextButton.icon(
            onPressed: _h(() => _addClientSheet(_inboxVendorId)),
            icon: Icon(Icons.person_add_alt_1_rounded,
                size: 15, color: _lzFg(plum)),
            label: Text('Add a client',
                style: TextStyle(
                    color: _lzFg(plum),
                    fontSize: 12,
                    fontWeight: FontWeight.w800)),
            style: TextButton.styleFrom(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                visualDensity: VisualDensity.compact),
          ),
          const SizedBox(width: 6),
          InkWell(""",
    """          const Spacer(),
          // v199: add a client from outside Lazo (v211: icon only on phones - the
          // row overflowed at 390 px)
          if (MediaQuery.of(context).size.width < 480)
            IconButton(
              tooltip: 'Add a client',
              onPressed: _h(() => _addClientSheet(_inboxVendorId)),
              icon: Icon(Icons.person_add_alt_1_rounded,
                  size: 18, color: _lzFg(plum)),
              visualDensity: VisualDensity.compact,
            )
          else
          TextButton.icon(
            onPressed: _h(() => _addClientSheet(_inboxVendorId)),
            icon: Icon(Icons.person_add_alt_1_rounded,
                size: 15, color: _lzFg(plum)),
            label: Text('Add a client',
                style: TextStyle(
                    color: _lzFg(plum),
                    fontSize: 12,
                    fontWeight: FontWeight.w800)),
            style: TextButton.styleFrom(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                visualDensity: VisualDensity.compact),
          ),
          const SizedBox(width: 6),
          InkWell(""")
rep("""                const SizedBox(width: 5),
                Text(_chimeMuted ? 'Alert Sound Off' : 'Alert Sound On',
                    style: TextStyle(
                        color: _lzFg(_chimeMuted ? muted : plum),
                        fontSize: 10.5,
                        fontWeight: FontWeight.w800)),
              ]),""",
    """                // v211: phones keep the icon and a short word
                if (MediaQuery.of(context).size.width >= 480) ...<Widget>[
                const SizedBox(width: 5),
                Text(_chimeMuted ? 'Alert Sound Off' : 'Alert Sound On',
                    style: TextStyle(
                        color: _lzFg(_chimeMuted ? muted : plum),
                        fontSize: 10.5,
                        fontWeight: FontWeight.w800)),
                ],
              ]),""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")

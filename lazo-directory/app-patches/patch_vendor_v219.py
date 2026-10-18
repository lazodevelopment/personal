"""Vendor v219: unblock senders, thread header fits every width (JC-LAZO-UNBLOCK-1018-VENDOR).

    python app-patches\\patch_vendor_v219.py [base.txt]   # base defaults to Vendor_master_v218.txt
                                                          # writes Vendor_master_v219.txt
- Account > Lead form: a "Blocked senders" section lists every email / phone the vendor blocked
  from a lead's Report or remove sheet (vendors.blockedSenders), each with an x that unblocks it
  (arrayRemove). Lazo-account couples are unblocked from the thread as before.
- Inbox: three columns from 1100 px (was 900) so the thread column never shrinks to ~250 px, and
  the thread header drops the "fit" / "Mark booked" words below 520 px of header width (icons stay),
  so the five-icon header no longer overflows at any width.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v218.txt"
DST = HERE / "Vendor_master_v219.txt"
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
    "// Build ID: JC-LAZO-UNBLOCK-1018-VENDOR (v219: UNBLOCK + HEADER FITS - Blocked senders list with unblock in "
    "Account > Lead form (vendors.blockedSenders arrayRemove); inbox goes three-column at 1100 px and the thread "
    "header hides the fit / Mark booked words under 520 px so it never overflows; base v218)\n"
) + s[first_build:]

# ---- Lead form sheet: Blocked senders with unblock
rep("""                  child: const Text('Add', style: TextStyle(fontWeight: FontWeight.w800)),
                ),
              ]),
            ]),
          ),
        ]);""",
    """                  child: const Text('Add', style: TextStyle(fontWeight: FontWeight.w800)),
                ),
              ]),
              // v219: senders blocked from a lead's Report or remove sheet, each with an unblock
              if (((vd['blockedSenders'] as List?) ?? const <dynamic>[]).isNotEmpty) ...<Widget>[
                const SizedBox(height: 14),
                Text('Blocked senders', style: TextStyle(fontSize: 11, letterSpacing: 1.5, fontWeight: FontWeight.w800, color: _lzFg(muted))),
                const SizedBox(height: 2),
                Text('These emails and numbers can\\u2019t reach you through your form, your booking link or forwards. Tap the x to unblock.',
                    style: TextStyle(fontSize: 12, height: 1.4, color: _lzFg(muted))),
                const SizedBox(height: 6),
                Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                  for (final dynamic b in (vd['blockedSenders'] as List?) ?? const <dynamic>[])
                    Chip(
                      avatar: const Icon(Icons.block_rounded, size: 14, color: Color(0xFFB3261E)),
                      label: Text(b.toString(), style: TextStyle(fontSize: 12, color: _lzFg(ink))),
                      backgroundColor: _lzBg(const Color(0xFFB3261E).withOpacity(.08)),
                      side: BorderSide(color: _lzLine(const Color(0xFFB3261E).withOpacity(.35))),
                      deleteIcon: const Icon(Icons.close_rounded, size: 15),
                      deleteButtonTooltipMessage: 'Unblock',
                      onDeleted: () {
                        FirebaseFirestore.instance.collection('vendors').doc(vendorId).set(<String, dynamic>{'blockedSenders': FieldValue.arrayRemove(<String>[b.toString()])}, SetOptions(merge: true));
                        _toast('Unblocked ${b.toString()}. Reopen this sheet to see the list.');
                      },
                    ),
                ]),
              ],
            ]),
          ),
        ]);""")

# ---- inbox: three columns only from 1100 px
rep("final bool three = w >= 900;", "final bool three = w >= 1100; // v219: was 900, left the thread column ~250 px")

# ---- thread header: words drop below 520 px of header width
rep("""        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 10, 6),
          child: Row(children: <Widget>[
            Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(coupleName.isEmpty ? 'Conversation' : coupleName,""",
    """        LayoutBuilder(builder: (BuildContext hc, BoxConstraints hcons) {
          final bool tight = hcons.maxWidth < 520; // v219: icons only when the column is narrow
          return Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 10, 6),
          child: Row(children: <Widget>[
            Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(coupleName.isEmpty ? 'Conversation' : coupleName,""")
rep("""                      const SizedBox(width: 4),
                      Text('${fit.grade} fit',""",
    """                      if (!tight) const SizedBox(width: 4),
                      if (!tight) Text('${fit.grade} fit',""")
rep("""                    const SizedBox(width: 5),
                    Text(booked ? 'Booked' : 'Mark booked',""",
    """                    if (!tight) const SizedBox(width: 5),
                    if (!tight) Text(booked ? 'Booked' : 'Mark booked',""")
rep("""          ]),
        ),
        Divider(height: 1, color: gold.withOpacity(.35)),""",
    """          ]),
        );
        }),
        Divider(height: 1, color: gold.withOpacity(.35)),""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")

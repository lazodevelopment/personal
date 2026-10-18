"""Couple v176: a clear inbox and a blocked-vendors list (JC-LAZO-INBOXCLEAR-1018-COUPLE).

    python app-patches\\patch_couple_v176.py [base.txt]   # base defaults to Couple_master_v175.txt
                                                          # writes Couple_master_v176.txt
- Messages: conversations the couple closed with "We went another direction" (status lost) leave the
  list and sit in a collapsed "past conversations" section at the bottom (tap one to reopen it),
  next to the existing blocked section. Report, block and unblock stay in the thread menu.
- Account > More > Blocked vendors: every vendor the couple blocked, with Unblock, so blocking can be
  undone without hunting for the thread.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v175.txt"
DST = HERE / "Couple_master_v176.txt"
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
    "// Build ID: JC-LAZO-INBOXCLEAR-1018-COUPLE (v176: CLEAR INBOX + BLOCKED VENDORS - 'went another direction' "
    "threads collapse into a past-conversations section; Account > More > Blocked vendors lists blocks with Unblock; "
    "base v175)\n"
) + s[first_build:]

# ---- inbox: past (lost) conversations collapse like blocked ones
rep("""        docs.removeWhere((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
            (d.data()['blockedByCouple'] ?? false) == true);""",
    """        docs.removeWhere((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
            (d.data()['blockedByCouple'] ?? false) == true);
        // v176: "We went another direction" threads leave the list too; a collapsed
        // section keeps them a tap away.
        final List<QueryDocumentSnapshot<Map<String, dynamic>>> pastDocs = docs
            .where((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
                (d.data()['status'] ?? '').toString() == 'lost')
            .toList();
        docs.removeWhere((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
            (d.data()['status'] ?? '').toString() == 'lost');""")
rep("""            if (blockedDocs.isNotEmpty) _blockedSection(blockedDocs),""",
    """            if (pastDocs.isNotEmpty) _pastSection(pastDocs), // v176
            if (blockedDocs.isNotEmpty) _blockedSection(blockedDocs),""")

NEW = r'''
  // v176: conversations the couple closed ("We went another direction"), collapsed, tap to reopen.
  Widget _pastSection(
      List<QueryDocumentSnapshot<Map<String, dynamic>>> pastDocs) {
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: _glass(
        padding: const EdgeInsets.symmetric(horizontal: 2, vertical: 2),
        radius: 18,
        tint: .5,
        borderColor: muted.withOpacity(.35),
        child: Theme(
          data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
          child: ExpansionTile(
            tilePadding: const EdgeInsets.symmetric(horizontal: 12),
            iconColor: _lzFg(muted),
            collapsedIconColor: muted,
            leading: Icon(Icons.history_rounded, color: _lzFg(muted), size: 20),
            title: Text(
                pastDocs.length == 1
                    ? '1 past conversation'
                    : '${pastDocs.length} past conversations',
                style: TextStyle(
                    color: _lzFg(plum), fontSize: 13.5, fontWeight: FontWeight.w700)),
            subtitle: Text('Vendors you went another direction on',
                style: TextStyle(color: _lzFg(muted), fontSize: 11.5)),
            children: <Widget>[
              for (final QueryDocumentSnapshot<Map<String, dynamic>> d in pastDocs)
                ListTile(
                  dense: true,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12),
                  onTap: _h(() => _openCoupleThread(d.id, d.data())),
                  title: Text((d.data()['vendorName'] ?? 'Vendor').toString(),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                          color: _lzFg(ink), fontSize: 13.5, fontWeight: FontWeight.w600)),
                  subtitle: Text('Tap to read or reply',
                      style: TextStyle(color: _lzFg(muted), fontSize: 11.5)),
                  trailing: Icon(Icons.chevron_right_rounded, size: 18, color: _lzFg(muted)),
                ),
              const SizedBox(height: 6),
            ],
          ),
        ),
      ),
    );
  }

  // v176: Account > More > Blocked vendors - every block in one place, with Unblock.
  Future<void> _blockedVendorsSheet() async {
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.block_rounded,
          title: 'Blocked vendors',
          subtitle: 'They can’t message you and they stay out of your search. Unblock any time.',
          children: <Widget>[
            const SizedBox(height: 10),
            StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
              stream: FirebaseFirestore.instance
                  .collection('inquiries')
                  .where('coupleUid', isEqualTo: _cid)
                  .where('blockedByCouple', isEqualTo: true)
                  .snapshots(),
              builder: (BuildContext c2, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> snap) {
                final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs =
                    snap.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
                if (snap.connectionState == ConnectionState.waiting && docs.isEmpty) {
                  return Padding(
                      padding: const EdgeInsets.all(18),
                      child: Center(child: Text('Loading…', style: TextStyle(color: _lzFg(muted), fontSize: 13))));
                }
                if (docs.isEmpty) {
                  return Padding(
                    padding: const EdgeInsets.fromLTRB(4, 8, 4, 12),
                    child: Text('You haven’t blocked anyone. Block or report a vendor from the menu at the top of any conversation.',
                        style: TextStyle(color: _lzFg(muted), fontSize: 13, height: 1.45)),
                  );
                }
                return Column(children: <Widget>[
                  for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs)
                    Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.fromLTRB(14, 8, 6, 8),
                      decoration: BoxDecoration(
                          color: _lzBg(Colors.white),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: _lzLine(goldLine))),
                      child: Row(children: <Widget>[
                        Icon(Icons.block_rounded, size: 18, color: _lzFg(const Color(0xFFB3413A))),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                            Text((d.data()['vendorName'] ?? 'Vendor').toString(),
                                maxLines: 1, overflow: TextOverflow.ellipsis,
                                style: TextStyle(color: _lzFg(ink), fontSize: 14, fontWeight: FontWeight.w700)),
                            Text((d.data()['reportId'] ?? '').toString().isNotEmpty ? 'Blocked and reported' : 'Blocked',
                                style: TextStyle(color: _lzFg(muted), fontSize: 11.5)),
                          ]),
                        ),
                        TextButton(
                          onPressed: _h(() async {
                            Navigator.of(ctx).pop();
                            await _confirmBlock(context, d.id, d.data(), true);
                          }),
                          child: Text('Unblock', style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w800)),
                        ),
                      ]),
                    ),
                ]);
              },
            ),
            const SizedBox(height: 4),
          ]),
    );
  }

  Widget _blockedSection('''
rep("\n  Widget _blockedSection(", NEW)

# ---- Account > More: Blocked vendors row
rep("""        _accountGroup(label: 'MORE', rows: <Widget>[
          _accountRow(
            icon: Icons.auto_awesome_motion_rounded,""",
    """        _accountGroup(label: 'MORE', rows: <Widget>[
          _accountRow(
            icon: Icons.block_rounded,
            title: 'Blocked vendors',
            value: 'Who you blocked, and a way to undo it',
            onTap: () => _blockedVendorsSheet(),
          ),
          _accountRow(
            icon: Icons.auto_awesome_motion_rounded,""")

# ---- planning desk: scrolls on short screens (16 tiles in 4 rows overflowed at ~724 px tall)
rep("""            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                // the clear sheet gets no handle from _lzSheet, so the desk""",
    """            child: SingleChildScrollView( // v176: the desk scrolls when the screen is short
              child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                // the clear sheet gets no handle from _lzSheet, so the desk""")
rep("""                      _deskSheetTile(ctx, it),
                  ],
                ),
              ],
            ),
          ),""",
    """                      _deskSheetTile(ctx, it),
                  ],
                ),
              ],
            ),
            ),
          ),""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")

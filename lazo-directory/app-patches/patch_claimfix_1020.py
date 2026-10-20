"""JC-LAZO-CLAIMFIX-1020: Vendor v223 from v222.

Brian Alan (Veiled Rose Films, Denver) wrote on 2026-10-20: "After adding my
email and phone number to verify, your submit button doesn't do anything."
No claimRequests doc ever landed. The claim sheet (STEP 2 - VERIFY OWNERSHIP)
requires a proof photo; without one, Submit set an inline error that renders
BELOW the proof picker, past the bottom of the sheet's scroll area, with the
keyboard up - so nothing visible changed. The Add-your-business sheet was
worse: no proof -> a bare `return`, no message at all.

Now both sheets: scroll to the error, say it in a toast over the popup, label
the proof section REQUIRED, and a failed upload/write shows the error code.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "Vendor_master_v222.txt"
DST = HERE / "Vendor_master_v223.txt"

SHOW_ERR = '''            // v223: an error must be seen - scroll the sheet to it and say it over the popup
            void showErr(String m) {
              setD(() {
                busy = false;
                formError = m;
              });
              _lzToastOver(m);
              WidgetsBinding.instance.addPostFrameCallback((_) {
                if (sheetScroll.hasClients) {
                  sheetScroll.animateTo(sheetScroll.position.maxScrollExtent,
                      duration: const Duration(milliseconds: 260),
                      curve: Curves.easeOut);
                }
              });
            }

'''

REPS: list[tuple[str, str, int]] = [
    # header + what's new
    ("// Build ID: JC-LAZO-RELEASE-1020-VENDOR (v222:",
     "// Build ID: JC-LAZO-CLAIMFIX-1020-VENDOR (v223: CLAIM SHEET SAYS WHAT IS MISSING - Submit for verification "
     "without a proof photo used to set an error below the fold (nothing visible happened; Veiled Rose Films, "
     "2026-10-20); now both the claim and Add-your-business sheets scroll to the error, toast it over the popup, "
     "label proof REQUIRED, and a failed upload or write shows its code; base v222)\n"
     "// Build ID: JC-LAZO-RELEASE-1020-VENDOR (v222:", 1),
    ("// What's new: Lazo tells you when it has been updated | On your phone, a note when a newer Lazo is in the App Store or Google Play, with what changed. | On the web, what's new opens once per release, and lives in Account. | leads",
     "// What's new: Claiming your business tells you what is missing | If Submit for verification needs a proof photo, the sheet now scrolls to it and says so. | A failed upload tells you why instead of going quiet. | leads", 1),
    ("  static const String kBuildId = 'JC-LAZO-RELEASE-1020-222';",
     "  static const String kBuildId = 'JC-LAZO-CLAIMFIX-1020-223';\n"
     "  /// v223: a short, user-safe reason from a Firebase error, for the sheets' error line.\n"
     "  String _lzErrShort(Object e) {\n"
     "    String s = e is FirebaseException ? e.code : e.runtimeType.toString();\n"
     "    if (e is FirebaseException && e.message != null && e.message!.isNotEmpty) {\n"
     "      s += ': ' + e.message!;\n"
     "    }\n"
     "    return s.length > 90 ? s.substring(0, 90) : s;\n"
     "  }", 1),
    ("  static const int kLzWidgetVersion = 222;", "  static const int kLzWidgetVersion = 223;", 1),
    # the sheet takes a scroll controller
    ("    required List<Widget> body,\n    required Widget footer,\n  }) {\n    final Size sz = MediaQuery.of(ctx).size;",
     "    required List<Widget> body,\n    required Widget footer,\n    ScrollController? scroll, // v223\n  }) {\n    final Size sz = MediaQuery.of(ctx).size;", 1),
    ("                child: SingleChildScrollView(\n                  padding: const EdgeInsets.fromLTRB(24, 22, 24, 8),",
     "                child: SingleChildScrollView(\n                  controller: scroll, // v223\n                  padding: const EdgeInsets.fromLTRB(24, 22, 24, 8),", 1),
    ("            return _onbSheet(\n              ctx: ctx2,",
     "            return _onbSheet(\n              ctx: ctx2,\n              scroll: sheetScroll, // v223", 2),
    ("_onbLabel('PROOF OF OWNERSHIP')", "_onbLabel('PROOF OF OWNERSHIP \\u00b7 REQUIRED')", 2),
    # claim flow
    ("    String claimantRole = 'Owner';\n",
     "    String claimantRole = 'Owner';\n    final ScrollController sheetScroll = ScrollController(); // v223\n", 1),
    ('''            Future<void> doSubmit() async {
              final Uint8List? bytes = proofBytes;
              if (bizEmailC.text.trim().isEmpty ||
                  bizPhoneC.text.trim().isEmpty) {
                setD(() {
                  formError = 'Business email and phone are required.';
                });
                return;
              }
              if (bytes == null) {
                setD(() {
                  formError =
                      'Please attach a proof photo so we can verify you.';
                });
                return;
              }
''',
     SHOW_ERR + '''            Future<void> doSubmit() async {
              final Uint8List? bytes = proofBytes;
              if (bizEmailC.text.trim().isEmpty ||
                  bizPhoneC.text.trim().isEmpty) {
                showErr('Business email and phone are required.');
                return;
              }
              if (bytes == null) {
                showErr(
                    'One more thing: attach a proof photo (a license, an invoice or a business card with the business name) so we can verify you.');
                return;
              }
''', 1),
    ('''                debugPrint('LAZO claim submit error: ' + e.toString());
                setD(() {
                  busy = false;
                  formError = 'Something went wrong submitting - try again.';
                });
''',
     '''                debugPrint('LAZO claim submit error: ' + e.toString());
                showErr('Something went wrong submitting - try again. (' +
                    _lzErrShort(e) +
                    ')');
''', 1),
    # add-your-business flow
    ("    final TextEditingController heardOtherC = TextEditingController();\n",
     "    final TextEditingController heardOtherC = TextEditingController();\n    final ScrollController sheetScroll = ScrollController(); // v223\n", 1),
    ('''            Future<void> doSubmit() async {
              final Uint8List? bytes = proofBytes;
              if (bytes == null) {
                return;
              }
''',
     SHOW_ERR + '''            Future<void> doSubmit() async {
              final Uint8List? bytes = proofBytes;
              if (bytes == null) {
                showErr(
                    'One more thing: attach a proof photo (a license, an invoice or a business card with the business name) so we can verify you.');
                return;
              }
''', 1),
    ('''                debugPrint('LAZO listing submit error: ' + e.toString());
                setD(() {
                  busy = false;
                  formError = 'Something went wrong submitting - try again.';
                });
''',
     '''                debugPrint('LAZO listing submit error: ' + e.toString());
                showErr('Something went wrong submitting - try again. (' +
                    _lzErrShort(e) +
                    ')');
''', 1),
]

text = SRC.read_text(encoding="utf-8")
for old, new, n in REPS:
    c = text.count(old)
    if c != n:
        print(f"!! expected {n}, found {c}:\n{old[:140]}")
        sys.exit(1)
    text = text.replace(old, new)
DST.write_text(text, encoding="utf-8", newline="\n")
print(f"wrote {DST.name} ({text.count(chr(10))} lines)")

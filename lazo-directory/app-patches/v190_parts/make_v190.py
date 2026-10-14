"""Build Vendor_master_v190.txt from v189 plus the v190_parts onboarding blocks.
JC-LAZO-ONBOARD-1014-190. Run from anywhere: python make_v190.py"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE.parent / "Vendor_master_v189.txt"
DST = HERE.parent / "Vendor_master_v190.txt"
part = lambda n: (HERE / n).read_text(encoding="utf-8")

s = SRC.read_text(encoding="utf-8")


def once(old, new, text, start=0):
    i = text.find(old, start)
    assert i >= 0, "anchor not found: " + old[:80]
    assert text.find(old, i + 1) < 0 or start, "anchor not unique: " + old[:80]
    return text[:i] + new + text[i + len(old):]


def between(text, fn_anchor, start_anchor, end_anchor, new):
    f = text.find(fn_anchor)
    assert f >= 0, fn_anchor
    a = text.find(start_anchor, f)
    b = text.find(end_anchor, a)
    assert a >= 0 and b > a, (start_anchor, end_anchor)
    return text[:a] + new + text[b:]


# 0. header
s = once("// Build ID: JC-LAZO-VDASH-1012-188",
         "// Build ID: JC-LAZO-VDASH-1014-190 (v190: ONBOARDING - the first five minutes, made premium: a plum welcome hero "
         "with the vendor's first name, Find -> Verify -> Go live and three perks; one search card (city re-runs the search) with "
         "monogram result cards and Add your business always in reach; the claim sheet and a three-step Add your business sheet "
         "(Business, Services, Verify) in one plum-headed frame with a private-document uploader and errors that say what is missing; "
         "the review screen gets a timeline, while-you-wait tips, an honest Approved state, Rejected treated like Denied and a Start "
         "over button; confetti when the approval lands while they watch. The newest open request across claims and new listings "
         "decides the screen. JC-LAZO-ONBOARD-1014-190; base v189)\n"
         "// Build ID: JC-LAZO-VDASH-1012-188", s)

# 1. state
s = once("  String _claimMetro = 'phoenix';\n",
         "  String _claimMetro = 'phoenix';\n"
         "  bool _onbRetry = false; // v190: a declined vendor chose to start over\n"
         "  bool _onbSawPending = false; // v190: they watched the review, so celebrate going live\n", s)

# 2. add-business sheet keeps its step
s = once("    String? heardAbout; // JC-LAZO-VDASH-1012-188\n",
         "    String? heardAbout; // JC-LAZO-VDASH-1012-188\n"
         "    int step = 0; // v190: Business -> Services -> Verify\n", s)

# 3. the sheets
s = between(s, "  Future<void> _submitClaim(", "            return Dialog(", "    if (submitted == true) {",
            part("onb_claim_dialog.dart"))
s = between(s, "  Future<void> _addListing()", "            final List<Widget> chips = [];", "    if (submitted == true) {",
            part("onb_add_dialog.dart"))

# 3b. the old field styles and enable flags the sheets no longer use
s = between(s, "  Future<void> _submitClaim(", "    InputDecoration deco(String label, String helper) {",
            "    final bool? submitted", "")
s = between(s, "  Future<void> _addListing()", "    InputDecoration ldeco(String label) {",
            "    final bool? submitted", "")
s = once("""            final bool canSubmit = bizEmailC.text.trim().isNotEmpty &&
                bizPhoneC.text.trim().isNotEmpty &&
                pb != null;
""", "", s)
s = once("""            final bool canSubmit = nameC.text.trim().isNotEmpty &&
                phoneC.text.trim().isNotEmpty &&
                picked.isNotEmpty &&
                heardAbout != null &&
                pb != null;
""", "", s)

# 4. which screen
s = once("""            if (vendorId.isNotEmpty) {
              return _claimedView(vendorId);
            }
            return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
              stream: _liveQuery(
                  'claims:$_uid',""",
         """            if (vendorId.isNotEmpty) {
              if (_onbSawPending) {
                _onbSawPending = false;
                WidgetsBinding.instance
                    .addPostFrameCallback((_) => _onbCelebrateLive());
              }
              return _claimedView(vendorId);
            }
            return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
              stream: _liveQuery(
                  'claims:$_uid',""", s)

old_pick = """                if (claimSnap.hasData &&
                    claimSnap.data != null &&
                    claimSnap.data!.docs.isNotEmpty) {
                  return _pendingView(claimSnap.data!.docs.first.data());
                }
                return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
                  stream: _liveQuery(
                      'listings:$_uid',
                      () => FirebaseFirestore.instance
                          .collection('listingRequests')
                          .where('uid', isEqualTo: _uid)),
                  builder: (BuildContext context,
                      AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>>
                          listSnap) {
                    if (listSnap.hasData &&
                        listSnap.data != null &&
                        listSnap.data!.docs.isNotEmpty) {
                      return _pendingView(listSnap.data!.docs.first.data());
                    }
                    return _claimView();"""
new_pick = """                // v190: claims and new listings together - the newest open
                // request decides the screen (see _onbPick).
                return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
                  stream: _liveQuery(
                      'listings:$_uid',
                      () => FirebaseFirestore.instance
                          .collection('listingRequests')
                          .where('uid', isEqualTo: _uid)),
                  builder: (BuildContext context,
                      AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>>
                          listSnap) {
                    final Map<String, dynamic>? req =
                        _onbPick(<QueryDocumentSnapshot<Map<String, dynamic>>>[
                      ...(claimSnap.data?.docs ??
                          <QueryDocumentSnapshot<Map<String, dynamic>>>[]),
                      ...(listSnap.data?.docs ??
                          <QueryDocumentSnapshot<Map<String, dynamic>>>[]),
                    ]);
                    if (req != null) {
                      return _pendingView(req);
                    }
                    return _claimView();"""
s = once(old_pick, new_pick, s)

# 5. the screens
s = between(s, "  Widget _claimView() {", "  Widget _claimView() {", "  Widget _pendingView(", part("onb_claim.dart"))
s = between(s, "  Widget _pendingView(", "  Widget _pendingView(", "  // ---------------- ADMIN DESK", part("onb_pending.dart"))

# 6. weather, take two (shared with the couple dashboard v154)
sys.path.insert(0, str(HERE.parent))
import patch_weather_1014b
s = patch_weather_1014b.apply(s, "vendor")

DST.write_text(s, encoding="utf-8", newline="")
print("wrote", DST, len(s.splitlines()), "lines")

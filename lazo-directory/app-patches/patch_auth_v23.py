r"""patch_auth_v23.py - Auth v22 -> v23: THE BOOKING EMAIL.  JC-LAZO-OFFPLATFORM-1016-AUTH

A client who booked a Lazo vendor without an account gets "make your free account" emails. Their link opens signup
with ref=lead:<inquiry>.<token>. Her thread moves into the new account only when the account's verified email is
the one her vendor has for her (functions-dashboard join.js). So on that path the signup screen:
  - asks joinInfo for that email, pre-fills it and locks it ("The email <Vendor> has for you"),
  - after signup, says a confirm link went to that address (j***@gmail.com) - the server sends it,
  - after a sign-in to an existing account, calls claimMyLeadThreads and says what happened: moved in / confirm
    your email / this account uses a different email (use j***@gmail.com).
Everyone else sees no change.

Needs the functions-dashboard joinInfo + claimMyLeadThreads callables deployed first.

    python app-patches\patch_auth_v23.py      # writes Auth_master_v23.txt
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC, DST = HERE / "Auth_master_v22.txt", HERE / "Auth_master_v23.txt"
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, f"expected {n} match(es), found {c}: {old[:90]!r}"
    s = s.replace(old, new)


rep("// lazo_auth_flow.dart\n",
    "// lazo_auth_flow.dart\n"
    "// Build ID: JC-LAZO-OFFPLATFORM-1016-AUTH (v23: THE BOOKING EMAIL - a join link from a vendor's booking "
    "(ref=lead:<inquiry>.<token>) pre-fills and locks the email the vendor has for her (joinInfo), says a confirm "
    "link is on its way after signup, and after a sign-in calls claimMyLeadThreads and says whether the booking "
    "moved in, needs a confirmed email, or needs the vendor's address; the thread only moves for a verified match; "
    "base v22)\n")

rep("import 'package:shared_preferences/shared_preferences.dart';\n",
    "import 'package:shared_preferences/shared_preferences.dart';\n"
    "import 'package:cloud_functions/cloud_functions.dart';\n")

# ---- state
rep("  final Map<String, String> _attrib = <String, String>{};\n",
    """  final Map<String, String> _attrib = <String, String>{};
  // v23: a join link from a vendor's booking - which thread, and the email it is tied to
  String _joinInq = '';
  String _joinTok = '';
  String _joinVendor = '';
  String _joinMasked = '';
  bool _joinLock = false;
""")

# ---- read the link on arrival
rep("""      final String path = Uri.base.path;
      if (path.isNotEmpty && path != '/') _attrib['landing'] = path;
    } catch (_) {}""",
    """      final String path = Uri.base.path;
      if (path.isNotEmpty && path != '/') _attrib['landing'] = path;
      // v23: ref=lead:<inquiry>.<token> - the booking this signup is for
      final RegExpMatch? jm =
          RegExp(r'^lead:([A-Za-z0-9]{10,40})\\.([A-Za-z0-9_-]{16,64})$')
              .firstMatch((q['ref'] ?? '').trim());
      if (jm != null) {
        _joinInq = jm.group(1)!;
        _joinTok = jm.group(2)!;
      }
    } catch (_) {}""")
rep("""      _stashWelcome();
      _stashDeepLink();""",
    """      _stashWelcome();
      _stashDeepLink();
      _loadJoin(); // v23""")

# ---- helpers
rep("  Future<void> _clearPendingRole() async {\n",
    """  // v23: the email her vendor has for her, pre-filled and locked on signup
  Future<void> _loadJoin() async {
    if (_joinInq.isEmpty) return;
    try {
      final HttpsCallableResult<dynamic> r = await FirebaseFunctions.instance
          .httpsCallable('joinInfo')
          .call(<String, dynamic>{'inquiryId': _joinInq, 't': _joinTok});
      final Map<dynamic, dynamic> d = (r.data as Map?) ?? <dynamic, dynamic>{};
      if (d['open'] != true) {
        _joinInq = '';
        return;
      }
      final String em = (d['email'] ?? '').toString().trim();
      if (!mounted || em.isEmpty) return;
      setState(() {
        _joinVendor = (d['vendorName'] ?? 'your vendor').toString();
        _joinMasked = (d['masked'] ?? '').toString();
        _email.text = em;
        _joinLock = true;
      });
    } catch (e) {
      debugPrint('LAZO joinInfo: $e');
    }
  }

  // v23: after a sign-in from a join link - move the booking in if the email matches
  Future<void> _claimJoin() async {
    if (_joinInq.isEmpty) return;
    String msg = '';
    try {
      final HttpsCallableResult<dynamic> r = await FirebaseFunctions.instance
          .httpsCallable('claimMyLeadThreads')
          .call(<String, dynamic>{
        'inquiryId': _joinInq,
        't': _joinTok,
        'step': _attrib['utm_content'] ?? '',
      });
      final Map<dynamic, dynamic> d = (r.data as Map?) ?? <dynamic, dynamic>{};
      final String st = (d['status'] ?? '').toString();
      final String v = (d['vendorName'] ?? _joinVendor).toString();
      final String m = (d['masked'] ?? _joinMasked).toString();
      if (st == 'claimed') {
        msg = 'Your booking with $v is in your account.';
      } else if (st == 'verify') {
        msg = 'Check $m and tap Confirm - your booking with $v moves in then.';
      } else if (st == 'relay') {
        msg = 'Apple\\u2019s private email can\\u2019t be matched to your booking. Use $m, the email $v has for you.';
      } else if (st == 'mismatch') {
        msg = 'This account uses a different email. Use the email $v has for you: $m';
      }
    } catch (e) {
      debugPrint('LAZO claimMyLeadThreads: $e');
    }
    if (msg.isEmpty || !mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(
        content: Text(msg), duration: const Duration(seconds: 8)));
  }

  Future<void> _clearPendingRole() async {
""")

# ---- after signup: the confirm link is on its way
rep("""      if (_rolePick == 'couple') {
        _setMode(_Mode.date);
      } else {
        _goVendor();
      }
    } on FirebaseAuthException catch (e) {
      _fail(_authMessage(e.code),""",
    """      if (_rolePick == 'couple') {
        _setMode(_Mode.date);
        // v23: the server sends the confirm link; the booking moves in once it's tapped
        if (_joinLock && _joinMasked.isNotEmpty && mounted) {
          setState(() => _notice =
              'We sent a link to $_joinMasked. Tap Confirm and your booking with $_joinVendor moves into your account.');
        }
      } else {
        _goVendor();
      }
    } on FirebaseAuthException catch (e) {
      _fail(_authMessage(e.code),""")

# ---- after sign-in: try the claim
rep("""      if (role == 'couple') {
        await _routeCouple(u.uid, userDoc: snap.data());""",
    """      if (role == 'couple') {
        await _claimJoin(); // v23
        if (!mounted) return;
        await _routeCouple(u.uid, userDoc: snap.data());""")

# ---- the email field: locked on the booking path, with the reason under it
rep("""        _field(_email, 'Email', TextInputType.emailAddress,
            focus: _emailFocus,
            hints: const [AutofillHints.email],
            next: true,
            error: emailNote != null),
        _note(emailNote),""",
    """        _field(_email, 'Email', TextInputType.emailAddress,
            focus: _emailFocus,
            hints: const [AutofillHints.email],
            next: true,
            error: emailNote != null,
            readOnly: _joinLock && isSignup),
        _note(emailNote),
        // v23: why it's locked
        _note(_joinLock && isSignup
                ? 'The email $_joinVendor has for you. Your booking moves in once you confirm it.'
                : null,
            ok: true),""")

rep("""      bool error = false,
      TextCapitalization cap = TextCapitalization.none}) {
    return TextField(
      controller: c,
      focusNode: focus,""",
    """      bool error = false,
      bool readOnly = false,
      TextCapitalization cap = TextCapitalization.none}) {
    return TextField(
      controller: c,
      focusNode: focus,
      readOnly: readOnly,""")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} ({len(s):,} chars)")

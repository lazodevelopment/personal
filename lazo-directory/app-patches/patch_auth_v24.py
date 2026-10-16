r"""patch_auth_v24.py - Auth v23 -> v24: CONFIRM YOUR EMAIL.  JC-LAZO-VERIFY-1016-AUTH

Anyone could sign up with any address (xxy@aol.com + a password and they were in). Now an email/password account
has to type in a six-digit code we email it before it goes anywhere:
  - after signup (couple or vendor) -> "Check your email" with the code field, then on to the date step / vendor home;
  - after a login, and on a cold open into this page, an account that never confirmed gets the same screen;
  - the code fills itself in from the phone's keyboard (oneTimeCode) and submits at six digits;
  - "Send a new code" with a countdown (the server allows one every 45s, six an hour);
  - "Wrong email? Use a different one" signs out and goes back to the form.
Accounts made before v24 carry the legacy claim (scripts/mark_legacy_users.js) and are never asked.
The signup form also explains the server's refusals (functions-dashboard verify.js blockBadSignupEmail): throwaway
inboxes and domains that cannot receive mail.
v23's booking path is kept: after the code, a join link's booking is claimed (claimMyLeadThreads), so the confirm
LINK v23 announced after signup is replaced by this code.

Needs the functions-dashboard sendEmailCode + verifyEmailCode callables deployed first.

    python app-patches\patch_auth_v24.py      # writes Auth_master_v24.txt
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC, DST = HERE / "Auth_master_v23.txt", HERE / "Auth_master_v24.txt"
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, f"expected {n} match(es), found {c}: {old[:90]!r}"
    s = s.replace(old, new)


rep("// Build ID: JC-LAZO-OFFPLATFORM-1016-AUTH (v23:",
    "// Build ID: JC-LAZO-VERIFY-1016-AUTH (v24: CONFIRM YOUR EMAIL - an email/password account types in a six-digit "
    "code we email it (sendEmailCode / verifyEmailCode) before it goes anywhere: after signup, after login and on a "
    "cold open; accounts with the legacy claim are never asked; the form explains the server's refusal of throwaway "
    "and dead-domain addresses; a join link's booking is claimed after the code; base v23)\n"
    "// Build ID: JC-LAZO-OFFPLATFORM-1016-AUTH (v23:")

rep("import 'dart:convert';\n", "import 'dart:async';\nimport 'dart:convert';\n")

rep("enum _Mode { welcome, signup, login, rolepick, date }",
    "enum _Mode { welcome, signup, login, rolepick, date, verify }")

rep("""  bool _joinLock = false;
""", """  bool _joinLock = false;
  // v24: the six-digit email code, and where to go once it's in ('couple' | 'vendor' | 'route')
  final _code = TextEditingController();
  final FocusNode _codeFocus = FocusNode();
  String _verifyNext = '';
  int _resendIn = 0;
  Timer? _resendT;
""")

rep("""    _pass2Focus.dispose();
    super.dispose();""", """    _pass2Focus.dispose();
    _resendT?.cancel();
    _code.dispose();
    _codeFocus.dispose();
    super.dispose();""")

# ---- the code step: helpers
rep("""  Future<void> _clearPendingRole() async {""", r"""  // v24: an email/password account confirms its email before anything else.
  // Accounts made before v24 carry the legacy claim and are never asked.
  Future<bool> _needsVerify() async {
    final User? u = FirebaseAuth.instance.currentUser;
    if (u == null || u.emailVerified) return false;
    if (!u.providerData.any((UserInfo p) => p.providerId == 'password')) return false;
    // a join link's booking only moves to a proven email, so an older unverified
    // account arriving from one is asked too (the legacy claim doesn't count there)
    if (_joinInq.isEmpty) {
      try {
        final IdTokenResult t = await u.getIdTokenResult();
        if (t.claims?['legacy'] == true) return false;
      } catch (_) {}
    }
    try {
      await u.reload();
      if (FirebaseAuth.instance.currentUser?.emailVerified == true) return false;
    } catch (_) {}
    return true;
  }

  Future<void> _startVerify(String next) async {
    _verifyNext = next;
    _code.clear();
    if (mounted) setState(() => _resolving = false);
    _setMode(_Mode.verify);
    await _sendCode(quiet: true);
  }

  Future<void> _sendCode({bool quiet = false}) async {
    if (_resendIn > 0) return;
    try {
      final HttpsCallableResult<dynamic> r = await FirebaseFunctions.instance
          .httpsCallable('sendEmailCode')
          .call(<String, dynamic>{});
      final Map<dynamic, dynamic> d = (r.data as Map?) ?? <dynamic, dynamic>{};
      if (d['verified'] == true) {
        await _verified();
        return;
      }
      if (!mounted) return;
      _countdown((d['retryIn'] as num?)?.toInt() ?? 45);
      if (!quiet && d['sent'] == true) {
        setState(() {
          _error = null;
          _notice = 'New code sent.';
        });
      }
    } on FirebaseFunctionsException catch (e) {
      if (mounted) setState(() => _error = e.message ?? 'Could not send the code. Try again.');
    } catch (e) {
      if (mounted) setState(() => _error = 'Could not send the code. Try again.${_why(e)}');
    }
  }

  void _countdown(int secs) {
    _resendT?.cancel();
    setState(() => _resendIn = secs);
    _resendT = Timer.periodic(const Duration(seconds: 1), (Timer t) {
      if (!mounted) {
        t.cancel();
        return;
      }
      setState(() => _resendIn = _resendIn > 0 ? _resendIn - 1 : 0);
      if (_resendIn == 0) t.cancel();
    });
  }

  Future<void> _checkCode() async {
    final String c = _code.text.replaceAll(RegExp(r'\D'), '');
    if (c.length != 6) {
      _fail('Enter the 6-digit code from the email.', focus: _codeFocus);
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
    });
    try {
      final HttpsCallableResult<dynamic> r = await FirebaseFunctions.instance
          .httpsCallable('verifyEmailCode')
          .call(<String, dynamic>{
        'code': c,
        // the server claims a join link's booking right after the code (join.js claimLeadThreads)
        if (_joinInq.isNotEmpty) 'inquiryId': _joinInq,
        if (_joinInq.isNotEmpty) 't': _joinTok,
        if (_joinInq.isNotEmpty) 'step': _attrib['utm_content'] ?? '',
      });
      final Map<dynamic, dynamic> d = (r.data as Map?) ?? <dynamic, dynamic>{};
      if (d['ok'] == true) {
        await _verified(claim: (d['claim'] as Map?) ?? <dynamic, dynamic>{}, viaCode: true);
        return;
      }
      final int left = (d['left'] as num?)?.toInt() ?? 0;
      _code.clear();
      _fail(
          left > 0
              ? 'That code doesn’t match. $left ${left == 1 ? 'try' : 'tries'} left.'
              : 'That code doesn’t match.',
          focus: _codeFocus);
    } on FirebaseFunctionsException catch (e) {
      _code.clear();
      _fail(e.message ?? 'That didn’t work. Try again.', focus: _codeFocus);
    } catch (e) {
      _fail('Something went wrong. Try again.${_why(e)}');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  // The server set emailVerified. Refresh the token so the rules see it, then carry on.
  // After a code, verifyEmailCode has already claimed a join link's booking and says how it went;
  // if the account was verified some other way, ask the claim directly (v23).
  Future<void> _verified({Map<dynamic, dynamic>? claim, bool viaCode = false}) async {
    try {
      await FirebaseAuth.instance.currentUser?.reload();
      await FirebaseAuth.instance.currentUser?.getIdToken(true);
    } catch (_) {}
    _resendT?.cancel();
    if (!mounted) return;
    final String next = _verifyNext;
    _verifyNext = '';
    if (viaCode) {
      _claimSnack(claim ?? <dynamic, dynamic>{});
    } else {
      await _claimJoin();
    }
    if (!mounted) return;
    if (next == 'couple') {
      _setMode(_Mode.date);
    } else if (next == 'vendor') {
      _goVendor();
    } else {
      await _routeIfSignedIn();
    }
  }

  Future<void> _startOver() async {
    _resendT?.cancel();
    try {
      await FirebaseAuth.instance.signOut();
    } catch (_) {}
    if (!mounted) return;
    _code.clear();
    _pass.clear();
    _pass2.clear();
    setState(() => _resendIn = 0);
    _setMode(_Mode.signup);
  }

  // v24: the server's signup check (verify.js blockBadSignupEmail) refused the address
  String? _signupBlocked(FirebaseAuthException e) {
    final String m = (e.message ?? '').toLowerCase();
    if (m.contains('temporary inbox')) {
      return 'Please use your own email address - temporary inboxes can’t be used for Lazo.';
    }
    if (m.contains('receive mail')) {
      return 'That email address can’t receive mail. Check it for typos.';
    }
    return null;
  }

  Future<void> _clearPendingRole() async {""")

# ---- v23's claim message, shared by the login path and the code step
rep("""      final Map<dynamic, dynamic> d = (r.data as Map?) ?? <dynamic, dynamic>{};
      final String st = (d['status'] ?? '').toString();
      final String v = (d['vendorName'] ?? _joinVendor).toString();
      final String m = (d['masked'] ?? _joinMasked).toString();
      if (st == 'claimed') {""", """      _claimSnack((r.data as Map?) ?? <dynamic, dynamic>{});
    } catch (e) {
      debugPrint('LAZO claimMyLeadThreads: $e');
    }
  }

  // v24: what happened to a join link's booking (claimMyLeadThreads, or verifyEmailCode's claim)
  void _claimSnack(Map<dynamic, dynamic> d) {
    String msg = '';
    {
      final String st = (d['status'] ?? '').toString();
      final String v = (d['vendorName'] ?? _joinVendor).toString();
      final String m = (d['masked'] ?? _joinMasked).toString();
      if (st == 'claimed') {""")

rep("""        msg = 'This account uses a different email. Use the email $v has for you: $m';
      }
    } catch (e) {
      debugPrint('LAZO claimMyLeadThreads: $e');
    }
    if (msg.isEmpty || !mounted) return;""", """        msg = 'This account uses a different email. Use the email $v has for you: $m';
      }
    }
    if (msg.isEmpty || !mounted) return;""")

rep("""        msg = 'Check $m and tap Confirm - your booking with $v moves in then.';""",
    """        msg = 'Confirm your email with the code we send to $m - your booking with $v moves in then.';""")

rep("""  Future<void> _claimJoin() async {
    if (_joinInq.isEmpty) return;
    String msg = '';
    try {""", """  Future<void> _claimJoin() async {
    if (_joinInq.isEmpty) return;
    try {""")

# ---- cold open into this page
rep("""    final u = FirebaseAuth.instance.currentUser;
    if (u == null) return;
    String? role;""", """    final u = FirebaseAuth.instance.currentUser;
    if (u == null) return;
    if (await _needsVerify()) {
      await _startVerify('route'); // v24
      return;
    }
    String? role;""")

# ---- signup: the code step instead of going straight in
rep("""      if (_rolePick == 'couple') {
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
      _fail(_authMessage(e.code),
          focus: e.code == 'email-already-in-use' ? _emailFocus : null);""", """      // v24: confirm the email first; the booking from a join link moves in after the code
      await _startVerify(_rolePick == 'couple' ? 'couple' : 'vendor');
    } on FirebaseAuthException catch (e) {
      final String? blocked = _signupBlocked(e);
      _fail(blocked ?? _authMessage(e.code),
          focus: (blocked != null || e.code == 'email-already-in-use') ? _emailFocus : null);""")

# ---- login: an account that never confirmed gets the code step
rep("""      final u = cred.user!;
      final snap = await _userRef(u.uid).get();
      final role = snap.data()?['role'] as String?;
      TextInput.finishAutofillContext();""", """      final u = cred.user!;
      if (await _needsVerify()) {
        TextInput.finishAutofillContext();
        await _startVerify('route'); // v24
        return;
      }
      final snap = await _userRef(u.uid).get();
      final role = snap.data()?['role'] as String?;
      TextInput.finishAutofillContext();""")

# ---- the screen
rep("""      case _Mode.date:
        if (_building) {""", """      case _Mode.verify:
        return KeyedSubtree(
            key: const ValueKey<String>('verify'),
            child: _shakeable(_verifyView()));
      case _Mode.date:
        if (_building) {""")

rep("""  Widget _rolePickView() => Column(children: [""", r"""  // v24: the six-digit code
  Widget _verifyView() {
    final String em = FirebaseAuth.instance.currentUser?.email ?? '';
    final bool ready = _code.text.replaceAll(RegExp(r'\D'), '').length == 6;
    return AutofillGroup(
      child: Column(children: <Widget>[
        Text('Check your email', style: _serif(30)),
        const SizedBox(height: 6),
        Text('We sent a 6-digit code to',
            textAlign: TextAlign.center,
            style: TextStyle(color: ivory.withOpacity(.8), fontSize: 13)),
        const SizedBox(height: 2),
        Text(em,
            textAlign: TextAlign.center,
            style: const TextStyle(color: gold, fontSize: 15, fontWeight: FontWeight.w700)),
        const SizedBox(height: 22),
        TextField(
          controller: _code,
          focusNode: _codeFocus,
          autofocus: true,
          keyboardType: TextInputType.number,
          textAlign: TextAlign.center,
          autofillHints: const <String>[AutofillHints.oneTimeCode],
          inputFormatters: <TextInputFormatter>[
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(6),
          ],
          onTap: () => _codeFocus.requestFocus(),
          onChanged: (String v) {
            setState(() {});
            if (v.length == 6 && !_busy) _checkCode();
          },
          onSubmitted: (_) {
            if (!_busy) _checkCode();
          },
          cursorColor: plum,
          style: const TextStyle(
              color: ink, fontSize: 28, fontWeight: FontWeight.w700, letterSpacing: 12),
          decoration: _deco('000000'),
        ),
        const SizedBox(height: 16),
        _bigButton('Confirm', gold, plum, (_busy || !ready) ? null : _checkCode, busy: _busy),
        const SizedBox(height: 12),
        TextButton(
          onPressed: (_busy || _resendIn > 0) ? null : () => _sendCode(),
          child: Text(
              _resendIn > 0 ? 'Send a new code in ${_resendIn}s' : 'Send a new code',
              style: TextStyle(
                  color: _resendIn > 0 ? ivory.withOpacity(.5) : gold,
                  fontWeight: FontWeight.w600)),
        ),
        TextButton(
          onPressed: _busy ? null : _startOver,
          child: Text('Wrong email? Use a different one',
              style: TextStyle(color: ivory.withOpacity(.75), fontSize: 13)),
        ),
        const SizedBox(height: 4),
        Text('Can’t find it? Check spam or promotions - it comes from hello@meetlazo.com.',
            textAlign: TextAlign.center,
            style: TextStyle(color: ivory.withOpacity(.6), fontSize: 12)),
      ]),
    );
  }

  Widget _rolePickView() => Column(children: [""")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} ({len(s):,} chars)")

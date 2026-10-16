r"""patch_vendor_v199.py - Vendor v198 -> v199: ADD A CLIENT.  JC-LAZO-OFFPLATFORM-1016-VENDOR

A client who found the vendor somewhere else (Google, a referral, a call) can now be added by hand: name, email,
optional phone, wedding date and venue. The addClient callable makes the same off-platform thread a website lead
gets, so the agreement, invoices and payment plan work as usual and reach the client by email with the login-free
booking page (meetlazo.com/f/...). They never need a Lazo account. Entry points: a person-add button next to "Open
inbox" on the dashboard card, and "Add a client" in the full-screen inbox header. On save the inbox opens on the
new thread. Optional: email them their booking page straight away.

Needs the functions-dashboard addClient callable deployed first.

    python app-patches\patch_vendor_v199.py      # writes Vendor_master_v199.txt
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC, DST = HERE / "Vendor_master_v198.txt", HERE / "Vendor_master_v199.txt"
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, f"expected {n} match(es), found {c}: {old[:90]!r}"
    s = s.replace(old, new)


rep("// lazo_vendor_dashboard.dart\n",
    "// lazo_vendor_dashboard.dart\n"
    "// Build ID: JC-LAZO-OFFPLATFORM-1016-VENDOR (v199: ADD A CLIENT - a client from outside Lazo is added by hand "
    "(name, email, phone, date, venue) through the addClient callable; their thread works like a website lead's: the "
    "agreement, invoices and payments reach them by email with the login-free booking page; person-add button on the "
    "inbox card, 'Add a client' in the full inbox; base v198)\n")

# ---- the sheet
rep("  Future<void> _disconnectWhop(String vendorId) async {\n",
    """  // v199: a client from outside Lazo, added by hand. Same off-platform thread
  // a website lead gets: agreement, invoices and payments reach them by email
  // with the login-free booking page. They never need a Lazo account.
  Future<void> _addClientSheet(String vendorId) async {
    if (vendorId.isEmpty) {
      _toast('One moment - your profile is still loading.');
      return;
    }
    final TextEditingController nameC = TextEditingController();
    final TextEditingController emailC = TextEditingController();
    final TextEditingController phoneC = TextEditingController();
    final TextEditingController venueC = TextEditingController();
    DateTime? date;
    bool sendLink = false;
    bool busy = false;
    String err = '';
    String two(int n) => n < 10 ? '0$n' : '$n';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx2) {
        return StatefulBuilder(
            builder: (BuildContext sc, StateSetter setSheet) {
          final bool ready = nameC.text.trim().isNotEmpty &&
              RegExp(r'^[^\\s@]+@[^\\s@]+\\.[^\\s@]{2,}$')
                  .hasMatch(emailC.text.trim());
          Future<void> save() async {
            setSheet(() {
              busy = true;
              err = '';
            });
            try {
              final HttpsCallable fn =
                  FirebaseFunctions.instance.httpsCallable('addClient');
              final HttpsCallableResult<dynamic> r =
                  await fn.call(<String, dynamic>{
                'vendorId': vendorId,
                'name': nameC.text.trim(),
                'email': emailC.text.trim(),
                'phone': phoneC.text.trim(),
                'venue': venueC.text.trim(),
                'weddingDate': date == null
                    ? ''
                    : '${date!.year}-${two(date!.month)}-${two(date!.day)}',
                'sendLink': sendLink,
              });
              final Map<dynamic, dynamic> d =
                  (r.data as Map?) ?? <dynamic, dynamic>{};
              final String id = (d['inquiryId'] ?? '').toString();
              if (ctx2.mounted) {
                Navigator.pop(ctx2);
              }
              if (!mounted) return;
              if (id.isNotEmpty) {
                setState(() {
                  _showInbox = true;
                  _setInboxThread(id);
                });
              }
              _toast(d['existing'] == true
                  ? 'They were already in your inbox - opened their thread.'
                  : d['emailed'] == true
                      ? 'Added, and their booking page is in their inbox.'
                      : 'Added. Send the agreement or an invoice from their thread - it reaches them by email.');
            } on FirebaseFunctionsException catch (e) {
              setSheet(() {
                busy = false;
                err = _lzFnMsg(e, 'Could not add them.');
              });
            } catch (e) {
              setSheet(() {
                busy = false;
                err = _errText(e);
              });
            }
          }

          Widget gap() => const SizedBox(height: 12);
          return _lzFrame(sc,
              icon: Icons.person_add_alt_1_rounded,
              title: 'Add a client',
              subtitle:
                  'Someone who found you outside Lazo. They sign and pay from one page - no account needed.',
              children: <Widget>[
                const SizedBox(height: 14),
                TextField(
                  controller: nameC,
                  textCapitalization: TextCapitalization.words,
                  textInputAction: TextInputAction.next,
                  onChanged: (_) => setSheet(() => err = ''),
                  style: TextStyle(color: _lzFg(ink), fontSize: 14),
                  decoration: _epDeco('Name', 'Maya Ortiz & Sam Lee'),
                ),
                gap(),
                TextField(
                  controller: emailC,
                  keyboardType: TextInputType.emailAddress,
                  autocorrect: false,
                  textInputAction: TextInputAction.next,
                  onChanged: (_) => setSheet(() => err = ''),
                  style: TextStyle(color: _lzFg(ink), fontSize: 14),
                  decoration: _epDeco(
                      'Email', 'Agreements and invoices go here'),
                ),
                gap(),
                TextField(
                  controller: phoneC,
                  keyboardType: TextInputType.phone,
                  textInputAction: TextInputAction.next,
                  style: TextStyle(color: _lzFg(ink), fontSize: 14),
                  decoration: _epDeco('Phone (optional)', '(602) 555-0142'),
                ),
                gap(),
                InkWell(
                  borderRadius: BorderRadius.circular(13),
                  onTap: () async {
                    final DateTime now = DateTime.now();
                    final DateTime? picked = await showDatePicker(
                      context: sc,
                      initialDate:
                          date ?? DateTime(now.year, now.month + 6, now.day),
                      firstDate: DateTime(now.year - 1),
                      lastDate: DateTime(now.year + 5),
                    );
                    if (picked != null) setSheet(() => date = picked);
                  },
                  child: InputDecorator(
                    decoration: _epDeco('Wedding date (optional)', ''),
                    child: Text(
                        date == null
                            ? 'Pick a date'
                            : '${date!.month}/${date!.day}/${date!.year}',
                        style: TextStyle(
                            color: _lzFg(date == null ? muted : ink),
                            fontSize: 14)),
                  ),
                ),
                gap(),
                TextField(
                  controller: venueC,
                  textCapitalization: TextCapitalization.words,
                  textInputAction: TextInputAction.done,
                  style: TextStyle(color: _lzFg(ink), fontSize: 14),
                  decoration: _epDeco('Venue (optional)', 'Fills the agreement'),
                ),
                const SizedBox(height: 6),
                CheckboxListTile(
                  value: sendLink,
                  onChanged: (bool? v) => setSheet(() => sendLink = v == true),
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  controlAffinity: ListTileControlAffinity.leading,
                  activeColor: plum,
                  title: Text('Email them their booking page now',
                      style: TextStyle(
                          color: _lzFg(ink),
                          fontSize: 13.5,
                          fontWeight: FontWeight.w600)),
                  subtitle: Text(
                      'Leave it off if you are about to send the agreement - that email carries the same page.',
                      style: TextStyle(color: _lzFg(muted), fontSize: 12)),
                ),
                if (err.isNotEmpty) _pv3Err(err),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: busy ? 'Adding\\u2026' : 'Add client',
                  icon: Icons.person_add_alt_1_rounded,
                  busy: busy,
                  onPrimary: !ready || busy ? null : save));
        });
      },
    );
  }

  Future<void> _disconnectWhop(String vendorId) async {
""")

# ---- entry point 1: the dashboard's inbox card
rep("""                  const SizedBox(width: 12),
                  OutlinedButton(
                    style: OutlinedButton.styleFrom(
                        foregroundColor: _lzFg(plum),
                        side: const BorderSide(color: gold),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 10),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10))),
                    onPressed: _h(() => setState(() => _showInbox = true)),""",
    """                  const SizedBox(width: 8),
                  IconButton(
                    tooltip: 'Add a client',
                    visualDensity: VisualDensity.compact,
                    icon: Icon(Icons.person_add_alt_1_rounded,
                        color: _lzFg(plum), size: 20),
                    onPressed: _h(() => _addClientSheet(vendorId)),
                  ),
                  const SizedBox(width: 4),
                  OutlinedButton(
                    style: OutlinedButton.styleFrom(
                        foregroundColor: _lzFg(plum),
                        side: const BorderSide(color: gold),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 10),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10))),
                    onPressed: _h(() => setState(() => _showInbox = true)),""")

# ---- entry point 2: the full-screen inbox header
rep("""          const Spacer(),
          InkWell(
            onTap: () {
              setState(() => _chimeMuted = !_chimeMuted);""",
    """          const Spacer(),
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
          InkWell(
            onTap: () {
              setState(() => _chimeMuted = !_chimeMuted);""")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} ({len(s):,} chars)")

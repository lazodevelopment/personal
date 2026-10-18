"""Vendor v215: leads@meetlazo.com in the app (JC-LAZO-LEADSMAIL-1018-VENDOR).

    python app-patches\\patch_vendor_v215.py [base.txt]   # base defaults to Vendor_master_v214.txt
                                                          # writes Vendor_master_v215.txt
- Lead form sheet: a "From other sites" section - forward any Knot, Zola, WeddingWire or
  Instagram inquiry to leads@meetlazo.com from the email you sign in with; it lands in
  the inbox as a lead (Copy address); "Also accept forwards from" adds extra addresses
  (vendors.forwardFrom, e.g. the Gmail the Zola notices go to)
- Automations: "Forwarded inquiries" listed as always on
- What you can do: the Lead form tile mentions it
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v214.txt"
DST = HERE / "Vendor_master_v215.txt"
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
    "// Build ID: JC-LAZO-LEADSMAIL-1018-VENDOR (v215: FORWARD YOUR LEADS - the Lead form sheet and Automations tell vendors "
    "to forward any Knot / Zola / WeddingWire / Instagram inquiry to leads@meetlazo.com from their sign-in email, and it "
    "lands in the inbox as a lead; base v214)\n"
) + s[first_build:]

# Lead form sheet: a section before "OR JUST A LINK"
rep("""    final String hosted = 'https://meetlazo.com/lead/$vendorId?k=$key';""",
    """    final String hosted = 'https://meetlazo.com/lead/$vendorId?k=$key';
    // v215: forwarded inquiries from other sites
    final TextEditingController fwdC = TextEditingController();
    Widget forwardSection() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          const SizedBox(height: 18),
          _lzSection('From other sites'),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: _lzBg(Colors.white), borderRadius: BorderRadius.circular(14), border: Border.all(color: _lzLine(gold.withOpacity(.6)))),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Text('Forward any inquiry to', style: TextStyle(fontSize: 13, color: _lzFg(muted))),
              const SizedBox(height: 4),
              Row(children: <Widget>[
                Expanded(child: SelectableText('leads@meetlazo.com', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: _lzFg(plum)))),
                TextButton.icon(
                  onPressed: () { Clipboard.setData(const ClipboardData(text: 'leads@meetlazo.com')); _toast('Address copied.'); },
                  icon: Icon(Icons.copy_rounded, size: 15, color: _lzFg(plum)),
                  label: Text('Copy', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, color: _lzFg(plum))),
                ),
              ]),
              const SizedBox(height: 6),
              Text('The Knot, Zola, WeddingWire, Instagram, your own inbox: forward the email from the address you sign in to Lazo with and June files the couple in your inbox as a lead within two minutes. Reply here and they get it by email.',
                  style: TextStyle(fontSize: 12.5, height: 1.4, color: _lzFg(muted))),
              const SizedBox(height: 10),
              Text('Also accept forwards from', style: TextStyle(fontSize: 11, letterSpacing: 1.5, fontWeight: FontWeight.w800, color: _lzFg(muted))),
              const SizedBox(height: 4),
              Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                for (final dynamic a in (vd['forwardFrom'] as List?) ?? const <dynamic>[])
                  Chip(
                    label: Text(a.toString(), style: TextStyle(fontSize: 12, color: _lzFg(plum))),
                    backgroundColor: _lzBg(const Color(0xFFF3EADF)),
                    side: BorderSide.none,
                    deleteIcon: const Icon(Icons.close_rounded, size: 15),
                    onDeleted: () {
                      FirebaseFirestore.instance.collection('vendors').doc(vendorId).set(<String, dynamic>{'forwardFrom': FieldValue.arrayRemove(<String>[a.toString()])}, SetOptions(merge: true));
                      _toast('Removed ${a.toString()}. Reopen this sheet to see the list.');
                    },
                  ),
              ]),
              const SizedBox(height: 6),
              Row(children: <Widget>[
                Expanded(
                  child: TextField(
                    controller: fwdC,
                    keyboardType: TextInputType.emailAddress,
                    style: TextStyle(color: _lzFg(ink), fontSize: 13),
                    decoration: _epDeco('The inbox your Zola or Knot notices go to', 'you@gmail.com'),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plum, padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14)),
                  onPressed: () {
                    final String a = fwdC.text.trim().toLowerCase();
                    if (!a.contains('@') || !a.contains('.')) { _toast('That does not look like an email address.'); return; }
                    FirebaseFirestore.instance.collection('vendors').doc(vendorId).set(<String, dynamic>{'forwardFrom': FieldValue.arrayUnion(<String>[a])}, SetOptions(merge: true));
                    fwdC.clear();
                    _toast('Added $a. Forwards from it land in your inbox from now on.');
                  },
                  child: const Text('Add', style: TextStyle(fontWeight: FontWeight.w800)),
                ),
              ]),
            ]),
          ),
        ]);""")
rep("""              _lzSection('Or just a link'),""", """              forwardSection(),
              const SizedBox(height: 6),
              _lzSection('Or just a link'),""")

# Automations: always-on row
rep("""                rule(Icons.notifications_active_rounded, 'Quiet leads', 'June flags a couple who went silent after your reply, and a nudge is one tap on Today.'),""",
    """                rule(Icons.notifications_active_rounded, 'Quiet leads', 'June flags a couple who went silent after your reply, and a nudge is one tap on Today.'),
                rule(Icons.forward_to_inbox_rounded, 'Forwarded inquiries', 'Forward any Knot, Zola or WeddingWire inquiry to leads@meetlazo.com from your sign-in email and it lands in your inbox as a lead.'),""")

# What you can do tile
rep("""      <dynamic>['Leads', 'Lead form for your website', 'One line of code, or a link; inquiries from anywhere land here', Icons.web_rounded, false, () { if (vendorId.isNotEmpty) _leadFormSheet(vendorId); }],""",
    """      <dynamic>['Leads', 'Lead form and forwarding', 'One line of code or a link for your site; forward Knot and Zola inquiries to leads@meetlazo.com', Icons.web_rounded, true, () { if (vendorId.isNotEmpty) _leadFormSheet(vendorId); }],""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")

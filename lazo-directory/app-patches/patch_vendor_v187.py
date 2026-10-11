"""patch_vendor_v187.py - JC-LAZO-VDASH-1011-187
Vendor_master_v186 -> v187:
  1. DIALOGS THAT HOLD STILL: every AlertDialog whose content is a bare Column or TextField grew
     wider with each character typed (an unconstrained content takes its intrinsic width). Each is
     now a fixed 440 px wide - the FAQ dialog, the add-package, saved-reply, tag and note dialogs.
  2. FIFTEEN FAQs on a profile (was six).
  3. READABLE CHIPS IN DARK MODE: selected gold chips (markets, categories, event types) kept a light
     label in dark mode; a gold chip's label is always plum.
  4. THE ACCOUNT SCREEN, PREMIUM: a plum hero with the photo, your name, your business and plan; then
     grouped cards with eyebrow labels (Your details, Your business, June, Plan and billing, Help)
     and flat rows with icon tiles and hairlines, instead of a stack of same-looking boxes.
  python app-patches\\patch_vendor_v187.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent


def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    return s.replace(old, new)


def match_paren(s, i):
    """i at '('; returns index of the matching ')' (string-aware)."""
    depth, j, n = 0, i, len(s)
    while j < n:
        c = s[j]
        if c in "'\"":
            q = c
            j += 1
            while j < n and s[j] != q:
                if s[j] == '\\':
                    j += 1
                j += 1
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise SystemExit('unbalanced')


s = (HERE / "Vendor_master_v186.txt").read_text(encoding="utf-8-sig")
NOTE = ("DIALOGS HOLD STILL (a bare Column/TextField content took its intrinsic width and grew as you typed; now 440 wide), "
        "15 FAQs, gold chips keep a plum label in dark mode, and the Account screen rebuilt as a plum hero plus grouped cards "
        "with eyebrow labels and flat rows. JC-LAZO-VDASH-1011-187")
s = rep(s, "// Build ID: JC-LAZO-VDASH-1010-186 (v186:", "// Build ID: JC-LAZO-VDASH-1011-187 (v187: " + NOTE + "; base v186) (v186:", 'note')
s = rep(s, "// END OF FILE - JC-LAZO-VDASH-1010-186", "// END OF FILE - JC-LAZO-VDASH-1011-187", 'end')

# ---------------------------------------------------------------- 1. dialogs hold still
for needle in ("content: Column(", "content: TextField("):
    pos = 0
    while True:
        i = s.find(needle, pos)
        if i < 0:
            break
        op = i + len(needle) - 1
        cl = match_paren(s, op)
        inner = s[i + len("content: "):cl + 1]
        s = s[:i] + "content: SizedBox(\n          width: 440,\n          child: " + inner + ",\n        )" + s[cl + 1:]
        pos = i + 20
assert s.count("content: SizedBox(\n          width: 440") == 7, 'dialog wraps'

# ---------------------------------------------------------------- 2. fifteen FAQs
s = rep(s, "    if (_epFaqs.length >= 6) {\n      _toast('Up to 6 FAQs on a profile.');", "    if (_epFaqs.length >= 15) {\n      _toast('Up to 15 FAQs on a profile.');", 'faq cap')

# ---------------------------------------------------------------- 3. gold chips keep a plum label
s = rep(s, "color: _lzFg(on ? plum : muted))),\n                selectedColor: gold,", "color: on ? plumDeep : _lzFg(muted))),\n                selectedColor: gold,", 'chip a', count=2)
s = rep(s, "color: _lzFg(on ? plum : muted))),\n                    selectedColor: gold,", "color: on ? plumDeep : _lzFg(muted))),\n                    selectedColor: gold,", 'chip b')
s = s.replace("                    checkmarkColor: _lzFg(plum),\n", "                    checkmarkColor: plumDeep,\n")
s = s.replace("                checkmarkColor: _lzFg(plum),\n", "                checkmarkColor: plumDeep,\n")

# ---------------------------------------------------------------- 4. the account screen
a = s.index("        final TextEditingController nameC = _acctNameC;\n        return ListView(\n          padding: const EdgeInsets.fromLTRB(18, 8, 18, 40),")
b = s.index("  // v179: deletion runs server-side")
NEW_BODY = r'''        final TextEditingController nameC = _acctNameC;
        // JC-LAZO-VDASH-1011-187: the business behind the login, for the hero
        final Map<String, dynamic> vdoc = vendorId.isEmpty
            ? <String, dynamic>{}
            : (_liveD['vendor:$vendorId']?.latest?.data() ?? <String, dynamic>{});
        final String bizName = (vdoc['name'] ?? '').toString();
        final String tier = (vdoc['tier'] ?? 'free').toString();
        final String tierLabel = tier == 'studio' ? 'June Studio' : tier == 'pro' ? 'Lazo Pro' : 'Free plan';
        final bool verified = vdoc['verified'] == true;
        final bool wideA = MediaQuery.of(context).size.width >= 700;
        return Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 760),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(18, 8, 18, 40),
              children: <Widget>[
                Row(children: <Widget>[
                  _Press(
                    onTap: () => setState(() => _showAccount = false),
                    child: Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(shape: BoxShape.circle, color: _lzBg(const Color(0xFFF1E9E0)), border: Border.all(color: _lzLine(goldLine))),
                      child: Icon(Icons.arrow_back_rounded, color: _lzFg(plum), size: 20),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Text('Account', style: _serif(size: 26, color: _lzFg(plum), weight: FontWeight.w500)),
                ]),
                const SizedBox(height: 16),
                // the hero: always plum, like the deck
                Container(
                  padding: EdgeInsets.fromLTRB(wideA ? 26 : 20, wideA ? 24 : 20, wideA ? 26 : 20, wideA ? 24 : 20),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: <Color>[Color(0xFF52284F), Color(0xFF3D1C3B), Color(0xFF241022)]),
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(color: gold),
                    boxShadow: <BoxShadow>[BoxShadow(color: plumDeep.withOpacity(.25), blurRadius: 28, offset: const Offset(0, 10))],
                  ),
                  child: Row(children: <Widget>[
                    InkWell(
                      onTap: _acctBusy ? null : _acctChangePhoto,
                      borderRadius: BorderRadius.circular(999),
                      child: Stack(children: <Widget>[
                        Container(
                          width: wideA ? 96 : 76,
                          height: wideA ? 96 : 76,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: ivory.withOpacity(.12),
                            border: Border.all(color: gold, width: 2),
                            image: photo.isNotEmpty ? DecorationImage(image: NetworkImage(photo), fit: BoxFit.cover) : null,
                          ),
                          child: photo.isEmpty
                              ? Center(child: Text(name.isEmpty ? 'A' : name[0].toUpperCase(), style: _serif(size: wideA ? 40 : 32, color: ivory, weight: FontWeight.w500)))
                              : null,
                        ),
                        Positioned(
                          bottom: 0,
                          right: 0,
                          child: Container(
                            padding: const EdgeInsets.all(6),
                            decoration: const BoxDecoration(color: gold, shape: BoxShape.circle),
                            child: _acctBusy
                                ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(color: plum, strokeWidth: 2))
                                : const Icon(Icons.camera_alt_rounded, size: 13, color: plumDeep),
                          ),
                        ),
                      ]),
                    ),
                    const SizedBox(width: 18),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: <Widget>[
                        Text(name.isEmpty ? 'Add your name' : name, maxLines: 1, overflow: TextOverflow.ellipsis, style: _serif(size: wideA ? 28 : 23, color: ivory, weight: FontWeight.w500, height: 1.05)),
                        const SizedBox(height: 4),
                        Text(email, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: ivory.withOpacity(.72), fontSize: 13)),
                        if (bizName.isNotEmpty) ...<Widget>[
                          const SizedBox(height: 12),
                          Wrap(spacing: 8, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
                            Text(bizName, style: const TextStyle(color: gold, fontSize: 13.5, fontWeight: FontWeight.w700)),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                              decoration: BoxDecoration(color: ivory.withOpacity(.1), borderRadius: BorderRadius.circular(999), border: Border.all(color: ivory.withOpacity(.25))),
                              child: Text(tierLabel.toUpperCase(), style: const TextStyle(color: ivory, fontSize: 9.5, letterSpacing: 1.6, fontWeight: FontWeight.w800)),
                            ),
                            if (verified)
                              Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                                const Icon(Icons.verified_rounded, color: gold, size: 14),
                                const SizedBox(width: 4),
                                Text('Verified', style: TextStyle(color: ivory.withOpacity(.85), fontSize: 12, fontWeight: FontWeight.w600)),
                              ]),
                          ]),
                        ],
                      ]),
                    ),
                  ]),
                ),
                const SizedBox(height: 22),
                _acctGroup('Your details', <Widget>[
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 14, 16, 6),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      TextField(
                        controller: nameC,
                        cursorColor: _lzFg(plum),
                        style: TextStyle(color: _lzFg(ink), fontSize: 15),
                        decoration: _epDeco('Your name', ''),
                        onSubmitted: _acctSaveName,
                      ),
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton(
                          onPressed: _h(() {
                            _acctSaveName(nameC.text);
                          }),
                          child: Text('Save name', style: TextStyle(color: _lzFg(plum), fontSize: 12.5, fontWeight: FontWeight.w700)),
                        ),
                      ),
                    ]),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 14),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      Text('APPEARANCE', style: TextStyle(color: _lzFg(muted.withOpacity(.9)), fontSize: 10, letterSpacing: 1.8, fontWeight: FontWeight.w800)),
                      const SizedBox(height: 3),
                      Text(_lzThemePref == 'system' ? 'Follows your device' : (_lzDark ? 'Dark - mission control' : 'Light'), style: TextStyle(fontSize: 12.5, color: _lzFg(muted))),
                      const SizedBox(height: 10),
                      _lzThemePicker(_lzSetTheme),
                    ]),
                  ),
                ]),
                if (vendorId.isEmpty)
                  _acctGroup('Your business', <Widget>[
                    _acctSoon(Icons.group_add_rounded, 'Team', 'Claim your business first, then invite a manager.'),
                  ])
                else ...<Widget>[
                  _acctGroup('Your business', <Widget>[
                    _acctLive(Icons.group_add_rounded, 'Team', 'Invite a manager to run leads and your profile with you.', () => _teamSheet(vendorId)),
                    _acctLive(Icons.event_available_rounded, 'Consult scheduler', 'Couples book a call or a tour from your link. Reminders go out on their own.', () => _schedulerSheet(vendorId)),
                    _acctLive(Icons.palette_rounded, 'Your brand', 'Your colors and type on booking pages, galleries and every email couples get.', () => _brandSheet(vendorId)),
                    _acctLive(Icons.web_rounded, 'Lead form for your website', 'One line of code, or a link - inquiries from anywhere land here.', () => _leadFormSheet(vendorId)),
                    _acctLive(Icons.calendar_month_rounded, 'Calendar feed', 'Booked weddings and blocked dates in Google or Apple Calendar.', () => _calendarFeedSheet(vendorId)),
                  ]),
                  _acctGroup('June', <Widget>[
                    _acctBriefRow(vendorId),
                    _acctLive(Icons.auto_awesome_rounded, 'Connect Claude or ChatGPT', 'Ask your assistant about leads, money and dates - and have it reply for you.', () => _mcpSheet(vendorId)),
                    _acctLive(Icons.school_rounded, 'Practice with a test couple', 'Jordan & Sam (played by June) send an inquiry - try the whole flow with no stakes.', () => _startPracticeCouple(vendorId, announce: true)),
                    _acctLive(Icons.tour_rounded, 'Take the tour', 'A one-minute walk through the dashboard.', () {
                      setState(() {
                        _showAccount = false;
                        _showInbox = false;
                        _editingProfile = false;
                        _dashMode = 'leads';
                      });
                      Future<void>.delayed(const Duration(milliseconds: 450), () {
                        if (mounted) _startTour(_vendorTourSteps());
                      });
                    }),
                  ]),
                ],
                _acctGroup('Plan and billing', <Widget>[_acctProRows(vendorId)]),
                _acctGroup('Help', <Widget>[
                  _acctLive(Icons.bug_report_rounded, 'Report a bug', 'Something broke or looks wrong? Tell us - we attach the details.', _reportBugSheet),
                  _acctIdeasRow(),
                  _acctSupportRow(),
                ]),
                const SizedBox(height: 6),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(foregroundColor: _lzFg(plum), side: BorderSide(color: gold.withOpacity(.8)), padding: const EdgeInsets.symmetric(vertical: 13), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                    onPressed: _h(_logOut),
                    icon: const Icon(Icons.logout_rounded, size: 18),
                    label: const Text('Sign out', style: TextStyle(fontWeight: FontWeight.w600)),
                  ),
                ),
                // v179: App Store 5.1.1(v) - account deletion, in the app, complete.
                const SizedBox(height: 10),
                Center(
                  child: TextButton(
                    onPressed: _h(_deleteVendorAccount),
                    child: Text('Delete my account', style: TextStyle(color: _lzFg(const Color(0xFFB3413A)), fontSize: 13, fontWeight: FontWeight.w600)),
                  ),
                ),
                if (vendorId.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Center(child: Text('Business id $vendorId', style: TextStyle(color: _lzFg(muted.withOpacity(.7)), fontSize: 10.5, letterSpacing: .4))),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  // JC-LAZO-VDASH-1011-187: a group of rows under an eyebrow label, hairlines between
  Widget _acctGroup(String label, List<Widget> rows) {
    final List<Widget> kids = <Widget>[];
    for (int i = 0; i < rows.length; i++) {
      if (i > 0) kids.add(Divider(height: 1, thickness: 1, color: _lzLine(const Color(0xFFEFE6DA))));
      kids.add(rows[i]);
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Padding(
          padding: const EdgeInsets.fromLTRB(6, 0, 6, 8),
          child: Text(label.toUpperCase(), style: TextStyle(color: _lzFg(const Color(0xFF8A6A2F)), fontSize: 10.5, letterSpacing: 2.2, fontWeight: FontWeight.w800)),
        ),
        Container(
          decoration: BoxDecoration(
            color: _lzBg(card),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: _lzLine(goldLine)),
            boxShadow: _lzDark ? null : <BoxShadow>[BoxShadow(color: plumDeep.withOpacity(.06), blurRadius: 18, offset: const Offset(0, 6))],
          ),
          clipBehavior: Clip.antiAlias,
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: kids),
        ),
      ]),
    );
  }

  Widget _acctIconTile(IconData icon) => Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(color: gold.withOpacity(_lzDark ? .16 : .2), borderRadius: BorderRadius.circular(11), border: Border.all(color: gold.withOpacity(.45))),
        child: Icon(icon, color: _lzFg(plum), size: 18),
      );

'''
s = s[:a] + NEW_BODY + s[b:]

# the rows: flat, inside a group
a = s.index("  Widget _acctSoon(IconData icon, String title, String note) {")
b = s.index("  // v110: live, tier-aware Lazo Pro + Billing rows on the account page.")
s = s[:a] + '''  Widget _acctSoon(IconData icon, String title, String note) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 13, 14, 13),
      child: Row(children: <Widget>[
        _acctIconTile(icon),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Text(title, style: TextStyle(color: _lzFg(plum), fontSize: 14, fontWeight: FontWeight.w700)),
            const SizedBox(height: 2),
            Text(note, style: TextStyle(fontSize: 12, color: _lzFg(muted), height: 1.3)),
          ]),
        ),
        const SizedBox(width: 10),
        Text('SOON', style: TextStyle(color: _lzFg(muted), fontSize: 9.5, letterSpacing: 1.5, fontWeight: FontWeight.w700)),
      ]),
    );
  }

''' + s[b:]
a = s.index("  Widget _acctLive(IconData icon, String title, String note, VoidCallback onTap,\n      {String? badge}) {")
b = s.index("  // JC-LAZO-THEME-1009-001: light / dark / auto, remembered on this device")
s = s[:a] + '''  Widget _acctLive(IconData icon, String title, String note, VoidCallback onTap,
      {String? badge}) {
    return _Press(
      scale: .985,
      dim: .92,
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 13, 14, 13),
        child: Row(children: <Widget>[
          _acctIconTile(icon),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Text(title, style: TextStyle(color: _lzFg(plum), fontSize: 14, fontWeight: FontWeight.w700)),
              const SizedBox(height: 2),
              Text(note, maxLines: 2, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 12, color: _lzFg(muted), height: 1.3)),
            ]),
          ),
          const SizedBox(width: 10),
          if (badge != null)
            Container(
              margin: const EdgeInsets.only(right: 8),
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
              decoration: BoxDecoration(color: plum, borderRadius: BorderRadius.circular(999)),
              child: Text(badge, style: const TextStyle(color: gold, fontSize: 9, letterSpacing: 1.5, fontWeight: FontWeight.w800)),
            ),
          Icon(Icons.chevron_right_rounded, color: _lzFg(muted.withOpacity(.8)), size: 20),
        ]),
      ),
    );
  }


''' + s[b:]

# the auto-reply editor: June writes them, or the vendor keeps their own words
s = rep(s, '  final TextEditingController _epAutoInstantC = TextEditingController();', "  final TextEditingController _epAutoInstantC = TextEditingController();\n  String _epAutoMode = 'june'; // JC-LAZO-VDASH-1011-187: June writes the replies unless the vendor keeps their own words\n  final TextEditingController _epAutoNoteC = TextEditingController();", 'autoreply mode')
s = rep(s, "    _epAutoOn = ar['enabled'] == true;\n", "    _epAutoOn = ar['enabled'] == true;\n    _epAutoMode = ar['mode'] == 'own' ? 'own' : 'june';\n    _epAutoNoteC.text = ar['note'] == null ? '' : ar['note'].toString();\n", 'autoreply load')
s = rep(s, '      _epAutoOn.toString(),\n      _epAutoInstantC.text,\n', '      _epAutoOn.toString(),\n      _epAutoMode,\n      _epAutoNoteC.text,\n      _epAutoInstantC.text,\n', 'autoreply dirty')
s = rep(s, "          'enabled': _epAutoOn,\n          'instant': _epAutoInstantC.text.trim(),\n", "          'enabled': _epAutoOn,\n          'mode': _epAutoMode,\n          'note': _epAutoNoteC.text.trim(),\n          'instant': _epAutoInstantC.text.trim(),\n", 'autoreply save')
s = rep(s, "        _epCard(\n            'Lead auto-replies',\n            'Written by you, sent by Lazo - instantly, then day 3 and day 5 if they haven\\u2019t booked. Use {date} and {vendor} anywhere.',\n            <Widget>[", "        _epCard(\n            'Lead auto-replies',\n            'A first reply within a minute of every inquiry, then a day-3 and day-5 nudge if they go quiet. June writes each one from the couple\\u2019s own message and your packages and FAQs - or use your own words.',\n            <Widget>[", 'autoreply card head')
s = rep(s, '              if (_epAutoOn) ...<Widget>[\n                const SizedBox(height: 6),\n                TextField(\n                    controller: _epAutoInstantC,', "              if (_epAutoOn) ...<Widget>[\n                const SizedBox(height: 10),\n                // JC-LAZO-VDASH-1011-187: who writes them\n                Row(children: <Widget>[\n                  for (final List<String> m in <List<String>>[\n                    <String>['june', 'June writes each reply'],\n                    <String>['own', 'Use my own words'],\n                  ])\n                    Padding(\n                      padding: const EdgeInsets.only(right: 8),\n                      child: ChoiceChip(\n                        label: Text(m[1],\n                            style: TextStyle(\n                                fontSize: 12.5,\n                                fontWeight: FontWeight.w600,\n                                color: _epAutoMode == m[0] ? plumDeep : _lzFg(muted))),\n                        selected: _epAutoMode == m[0],\n                        selectedColor: gold,\n                        backgroundColor: _lzBg(ivory),\n                        checkmarkColor: plumDeep,\n                        side: BorderSide(color: gold.withOpacity(.6)),\n                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),\n                        onSelected: _hb((bool _) => setState(() => _epAutoMode = m[0])),\n                      ),\n                    ),\n                ]),\n                const SizedBox(height: 10),\n                if (_epAutoMode == 'june') ...<Widget>[\n                  Container(\n                    padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),\n                    decoration: BoxDecoration(\n                        color: _lzBg(const Color(0xFFF7F0E1)),\n                        borderRadius: BorderRadius.circular(12),\n                        border: Border.all(color: gold.withOpacity(.5))),\n                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[\n                      Icon(Icons.auto_awesome_rounded, size: 16, color: _lzFg(plum)),\n                      const SizedBox(width: 8),\n                      Expanded(\n                        child: Text(\n                            'June reads what the couple wrote - their date, venue, budget, the questions they asked - and answers it with your packages, your FAQs and your availability. Nothing generic, nothing invented. It lands in the thread as you, and you can follow up any time.',\n                            style: TextStyle(fontSize: 12.5, color: _lzFg(ink), height: 1.45)),\n                      ),\n                    ]),\n                  ),\n                  const SizedBox(height: 10),\n                  TextField(\n                      controller: _epAutoNoteC,\n                      maxLines: 3,\n                      maxLength: 400,\n                      cursorColor: _lzFg(plum),\n                      style: TextStyle(color: _lzFg(ink), fontSize: 14),\n                      decoration: _epDeco('Standing note for June (optional)',\n                          'e.g. Always offer a 20-minute call. Mention we travel statewide. Never quote a price for Saturdays in October.')),\n                ],\n                if (_epAutoMode == 'own') ...<Widget>[\n                TextField(\n                    controller: _epAutoInstantC,", 'autoreply ui')
s = rep(s, "                    decoration: _epDeco('Day 5 follow-up (optional)',\n                        'One last friendly check-in')),\n              ],\n            ]),", "                    decoration: _epDeco('Day 5 follow-up (optional)',\n                        'One last friendly check-in')),\n                ],\n              ],\n            ]),", 'autoreply ui end')
(HERE / "Vendor_master_v187.txt").write_text(s, encoding="utf-8")
print("wrote Vendor_master_v187.txt", len(s))

r"""patch_vendor_v192.py - Vendor v191 -> v192 (JC-LAZO-VDASH-1014-192)
June walks a new vendor through the dashboard out loud. The first-run tour
already ran once per vendor; now each step is spoken by June (JuneSpeech from
JuneNative v8): she greets them by name and welcomes them to Lazo, explains
each part as the ring lands on it, and signs off. A speaker on the tour card
mutes her for the rest of the tour. While the tour talks, June's dashboard line
keeps quiet. The Profile step now says what is true: edits show on the public
page right away (pages render live since JC-LAZO-LIVEPAGE-1014).

Needs JuneNative v8 pasted first (JuneNative.say / stopSpeaking / holdLine live there).

    python app-patches\patch_vendor_v192.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "Vendor_master_v191.txt").read_text(encoding="utf-8")
OUT = HERE / "Vendor_master_v192.txt"


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor found {n}x (want {count}): {old[:80]!r}")
    s = s.replace(old, new)


# the step carries what June says
rep("""class _TourStep {
  const _TourStep(this.title, this.body, {this.key, this.before});
  final String title;
  final String body;
  final GlobalKey? key;
  final VoidCallback? before;
}""", """class _TourStep {
  const _TourStep(this.title, this.body, {this.key, this.before, this.say});
  final String title;
  final String body;
  final GlobalKey? key;
  final VoidCallback? before;
  final String? say; // v192: what June says on this step (else title + body)
}""")

# start: June holds her dashboard line and the tour voice is on
rep("""  void _startTour(List<_TourStep> steps) {
    if (steps.isEmpty) return;
    setState(() {""", """  bool _tourVoice = true; // v192: June narrates the tour; the speaker on the card mutes her

  void _startTour(List<_TourStep> steps) {
    if (steps.isEmpty) return;
    JuneNative.holdLine = true;
    _tourVoice = true;
    setState(() {""")

# speak each step once its target is found (a skipped step never talks)
rep("""    if (tc == null && st.key != null) {
      // target not on this screen - skip it
      if (mounted) _tourGo(1);
      return;
    }""", """    if (tc == null && st.key != null) {
      // target not on this screen - skip it
      if (mounted) _tourGo(1);
      return;
    }
    if (_tourVoice) JuneNative.say(st.say ?? '${st.title}. ${st.body}');""")

# the card: a speaker beside "n of N"
rep("""                      Text('${_tourIdx + 1} of ${_tourSteps.length}',
                          style:  TextStyle(
                              color: _lzFg(Color(0xFF6B5F72)),
                              fontSize: 11,
                              fontWeight: FontWeight.w700)),
                    ]),""", """                      Text('${_tourIdx + 1} of ${_tourSteps.length}',
                          style:  TextStyle(
                              color: _lzFg(Color(0xFF6B5F72)),
                              fontSize: 11,
                              fontWeight: FontWeight.w700)),
                      const SizedBox(width: 6),
                      Tooltip(
                        message: _tourVoice ? 'Mute June' : 'Let June talk me through it',
                        child: InkWell(
                          customBorder: const CircleBorder(),
                          onTap: () {
                            setState(() => _tourVoice = !_tourVoice);
                            if (_tourVoice) {
                              final _TourStep cur = _tourSteps[_tourIdx];
                              JuneNative.say(cur.say ?? '${cur.title}. ${cur.body}');
                            } else {
                              JuneNative.stopSpeaking();
                            }
                          },
                          child: Padding(
                            padding: const EdgeInsets.all(4),
                            child: Icon(
                                _tourVoice ? Icons.volume_up_rounded : Icons.volume_off_rounded,
                                size: 17,
                                color: _tourVoice ? plum : _lzFg(Color(0xFF6B5F72))),
                          ),
                        ),
                      ),
                    ]),""")

# end: June signs off (or goes quiet on Skip) and lets her line speak again
rep("""  Future<void> _endTour({required bool completed}) async {
    _tourChecked = true;""", """  Future<void> _endTour({required bool completed}) async {
    _tourChecked = true;
    JuneNative.holdLine = false;
    if (completed && _tourVoice) {
      JuneNative.say('That\\'s the tour. I\\'m right here on your dashboard whenever you need me. Ask me anything, any time.');
    } else {
      JuneNative.stopSpeaking();
    }""")

# the steps, in June's voice
rep("""  List<_TourStep> _vendorTourSteps() {
    final bool phone = MediaQuery.of(context).size.width < 1100;
    return <_TourStep>[
      _TourStep('Welcome to your Lazo dashboard',
          'Leads, conversations, contracts, money and your public page - all here. Thirty seconds and you will know where everything is.'),""", """  List<_TourStep> _vendorTourSteps() {
    final bool phone = MediaQuery.of(context).size.width < 1100;
    // v192: June greets them by first name when the listing has an owner
    final Map<String, dynamic> tvd =
        _liveD['vendor:$_vendorIdCache']?.latest?.data() ?? <String, dynamic>{};
    final String tOwner = (tvd['ownerName'] ?? '').toString().trim();
    final String tFirst = tOwner.isEmpty ? '' : tOwner.split(RegExp(r'\\s+')).first;
    final String tBiz = (tvd['name'] ?? '').toString().trim();
    return <_TourStep>[
      _TourStep('Welcome to your Lazo dashboard',
          'Leads, conversations, contracts, money and your public page - all here. Thirty seconds and you will know where everything is.',
          say: 'Hi${tFirst.isEmpty ? '' : ' ' + tFirst}, I\\'m June. Welcome to Lazo${tBiz.isEmpty ? '' : ', and congratulations on getting ' + tBiz + ' live'}. This is your dashboard. Your leads, conversations, contracts, money and your public page all live here. Let me show you around. It takes about thirty seconds.'),""")
rep("""          'What needs you right now: new leads, replies waiting, weddings coming up, and what is left to finish on your profile.',
          key: _kTourHero),""", """          'What needs you right now: new leads, replies waiting, weddings coming up, and what is left to finish on your profile.',
          key: _kTourHero,
          say: 'This is Today. It shows what needs you right now: new leads, replies waiting on you, weddings coming up, and anything left to finish on your profile.'),""")
rep("""          'Every couple who inquired, newest first. Open a thread to reply, send a proposal, contract, invoice or payment plan - all from the + beside the reply box.',
          key: _kTourInbox),""", """          'Every couple who inquired, newest first. Open a thread to reply, send a proposal, contract, invoice or payment plan - all from the + beside the reply box.',
          key: _kTourInbox,
          say: 'Here\\'s your inbox. Every couple who writes to you lands here, newest first. Open a thread to reply, or send a proposal, a contract, an invoice or a payment plan from the plus button beside the reply box.'),""")
rep("""          key: _kTourModes, before: () => setState(() => _dashMode = 'leads')),""", """          key: _kTourModes, before: () => setState(() => _dashMode = 'leads'),
          say: 'Your dashboard has five tabs, each with one job. Today is where you are now. Pipeline shows your couples as a board you can drag. Money is payments and how you get paid. Studio holds contracts, galleries and files. And Profile is how couples see you.'),""")
rep("""          key: _kTourJune),""", """          key: _kTourJune,
          say: 'And this is me. Tap the microphone or type to me. Ask who\\'s waiting on you, or what\\'s due this week. I read your real threads and money, draft replies for you, add tasks when you ask, and read you a short brief every morning. I can even play some music while you work.'),""")
rep("""          key: _kTourMoney, before: () => setState(() => _dashMode = 'money')),""", """          key: _kTourMoney, before: () => setState(() => _dashMode = 'money'),
          say: 'Money shows what\\'s outstanding and what\\'s come in, across every couple, and how you get paid.'),""")
rep("""          'Edit profile is how couples see you on meetlazo.com - photos, packages, price sheet. It updates live within a minute. Profile strength tells you what to add next.',
          key: _kTourActions,
          before: () => setState(() => _dashMode = 'profile')),""", """          'Edit profile is how couples see you on meetlazo.com - photos, packages, price sheet. Changes show on your public page right away. Profile strength tells you what to add next.',
          key: _kTourActions,
          before: () => setState(() => _dashMode = 'profile'),
          say: 'Profile is your public page on meetlazo.com. Add your photos, packages and price sheet here, and every change shows on your page right away. Profile strength tells you what to add next.'),""")
rep("""            'Inbox, Pipeline, Studio, June, your profile, scheduler, lead form, payments and Account - one tap from anywhere.',
            key: _kTourFab, before: () => setState(() => _dashMode = 'leads'))""", """            'Inbox, Pipeline, Studio, June, your profile, scheduler, lead form, payments and Account - one tap from anywhere.',
            key: _kTourFab, before: () => setState(() => _dashMode = 'leads'),
            say: 'Last thing: this is your desk button. Inbox, Pipeline, Studio, me, your profile, the scheduler, payments and your account are all one tap away from anywhere.')""")
rep("""            'Team invites, calendar feed, morning brief, your brand, the consult scheduler, the website lead form, Whop and Stripe, and this tour again - all behind your avatar.',
            key: _kTourAvatar,
            before: () => setState(() => _dashMode = 'leads')),""", """            'Team invites, calendar feed, morning brief, your brand, the consult scheduler, the website lead form, Whop and Stripe, and this tour again - all behind your avatar.',
            key: _kTourAvatar,
            before: () => setState(() => _dashMode = 'leads'),
            say: 'Last thing: your account lives behind your picture. Team invites, your calendar feed, the morning brief, your brand, the consult scheduler, payments, and this tour again if you ever want it.'),""")

# the editor's save toast tells the truth now too
s = s.replace("public page updates within a minute", "public page updates right away")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")

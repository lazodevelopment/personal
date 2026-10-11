"""patch_june_native_v4.py - JC-LAZO-JUNE-NATIVE-1011-004
JuneNative_v3.txt -> JuneNative_v4.txt. The everyday layer on the deck (pairs with the worker's
JC-LAZO-JUNE-DAILY-1011-001 and functions-dashboard 026 push):
  1. TODAY: one thing to do, with a Do it button (asks June) and a Done tick that advances a streak.
  2. RECALL: a line she brings up herself from memory ("You told me ...").
  3. MILESTONES in the headline: "100 days to go".
  4. NUMBERS (vendors): rank and its move, views and the trend, price position, reviews - a sheet.
  5. RSVPs (couples): the pulse - yes / no / pending, who is silent, a nudge to copy.
  6. POST IDEA (vendors): one caption a day from their gallery, copy or hand to June to post.
  7. FOCUS: 25 / 50 / 90 minutes with the radio on; the state label counts down; she says when.
  8. More chips from the day: numbers this week, questions for a vendor call, where money can move.
  python app-patches\\patch_june_native_v4.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent


def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    return s.replace(old, new)


s = (HERE / "JuneNative_v3.txt").read_text(encoding="utf-8-sig")
s = rep(s, "// Build ID: JC-LAZO-JUNE-NATIVE-1011-003 (003:",
        "// Build ID: JC-LAZO-JUNE-NATIVE-1011-004 (004: the everyday layer - today's one thing with a streak, recall, milestones, Numbers, RSVPs, the daily post idea, Focus; base 003) (003:", 'build id')

# ---------------------------------------------------------------- state: focus timer + today
s = rep(s, "  bool _chipsAll = false;\n",
        '''  bool _chipsAll = false;

  // JC-LAZO-JUNE-NATIVE-1011-004: focus mode and today's one thing
  DateTime? _focusEnd;
  Timer? _focusT;
  bool _doneBusy = false;
  Map<String, dynamic>? _postIdea;
  bool _postBusy = false;

  String _localDay() {
    final DateTime d = DateTime.now();
    return '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  }

  Future<void> _markDone() async {
    final Map<String, dynamic> t = _map(_snap['todayTask']);
    if (_doneBusy) return;
    setState(() => _doneBusy = true);
    try {
      final dynamic j = await _api.post('/api/today/done', <String, dynamic>{'id': _s(t['id']), 'day': _localDay()});
      final Map<String, dynamic> st = _map(j);
      if (mounted) {
        setState(() {
          _snap['streak'] = st;
        });
        HapticFeedback.mediumImpact();
        final int n = _n(st['count']).toInt();
        _addMsg('ai', n > 1 ? 'Done. That\\'s $n days in a row.' : 'Done. One thing a day, that\\'s how it gets finished.');
      }
    } catch (e) {
      _addMsg('sys', 'Couldn\\'t save that: ' + e.toString());
    }
    if (mounted) setState(() => _doneBusy = false);
  }

  void _focusStart(int minutes) {
    _focusT?.cancel();
    setState(() => _focusEnd = DateTime.now().add(Duration(minutes: minutes)));
    if (_radioName.isEmpty) _radioPlay(1);
    _focusT = Timer.periodic(const Duration(seconds: 1), (Timer t) {
      if (!mounted) return;
      final DateTime? end = _focusEnd;
      if (end == null) {
        t.cancel();
        return;
      }
      if (DateTime.now().isAfter(end)) {
        t.cancel();
        setState(() => _focusEnd = null);
        _voice.say('Time. Stretch, have some water, then back to it.');
        _addMsg('ai', 'Focus block done. Nice work.');
      } else {
        setState(() {});
      }
    });
  }

  void _focusStop() {
    _focusT?.cancel();
    setState(() => _focusEnd = null);
  }

  String _focusLeft() {
    final DateTime? end = _focusEnd;
    if (end == null) return '';
    final Duration d = end.difference(DateTime.now());
    final int m = d.inMinutes.clamp(0, 999), sec = (d.inSeconds % 60).clamp(0, 59);
    return 'focus ${m.toString().padLeft(2, '0')}:${sec.toString().padLeft(2, '0')}';
  }
''', 'state')

s = rep(s, "  Widget _stateLabel() => Text(_mode == 'idle' && _radioName.isNotEmpty ? '♪ $_radioName' : _mode, style: const TextStyle(color: _muted, fontSize: 10.5, letterSpacing: 2));",
        "  Widget _stateLabel() => Text(_focusEnd != null && _mode == 'idle' ? _focusLeft() : (_mode == 'idle' && _radioName.isNotEmpty ? '♪ $_radioName' : _mode), style: TextStyle(color: _focusEnd != null && _mode == 'idle' ? _goldSoft : _muted, fontSize: 10.5, letterSpacing: 2));", 'state label')

# dispose the timer
s = rep(s, "  void dispose() {\n    _ticker.dispose();\n", "  void dispose() {\n    _focusT?.cancel();\n    _ticker.dispose();\n", 'dispose')

# ---------------------------------------------------------------- headline: milestones
s = rep(s, '''  String _headline() {
    if (_loading && _snap.isEmpty) return 'Reading your day…';
    final String brief = _s(_map(_snap['brief'])['text']).trim();''',
        '''  String _headline() {
    if (_loading && _snap.isEmpty) return 'Reading your day…';
    final Map<String, dynamic> ms = _map(_snap['milestone']);
    final String mark = _s(ms['label']).isNotEmpty ? (_couple ? '${ms['label']}. ' : '${ms['label']} for ${_s(ms['who'])}. ') : '';
    final String brief = mark + _s(_map(_snap['brief'])['text']).trim();''', 'headline milestone')

# ---------------------------------------------------------------- today card + recall on the deck
s = rep(s, '''        Text(_headline(), maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _goldSoft, fontSize: 14, height: 1.5)),
        const SizedBox(height: 14),
        if (_chat.isNotEmpty) _chatBox(wide ? 240 : 200),''',
        '''        Text(_headline(), maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _goldSoft, fontSize: 14, height: 1.5)),
        if (_s(_map(_snap['recall'])['text']).isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              const Icon(Icons.psychology_rounded, size: 14, color: _muted),
              const SizedBox(width: 6),
              Expanded(child: Text('You told me: ${_s(_map(_snap['recall'])['text'])}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 12.5, fontStyle: FontStyle.italic, height: 1.4))),
            ]),
          ),
        const SizedBox(height: 12),
        _todayCard(),
        const SizedBox(height: 12),
        if (_chat.isNotEmpty) _chatBox(wide ? 240 : 200),''', 'deck today')

s = rep(s, "  Widget _deck(BuildContext context) {",
        '''  // ---- today's one thing (JC-LAZO-JUNE-NATIVE-1011-004)
  Widget _todayCard() {
    final Map<String, dynamic> t = _map(_snap['todayTask']);
    final Map<String, dynamic> st = _map(_snap['streak']);
    if (t.isEmpty) return const SizedBox.shrink();
    final bool done = st['doneToday'] == true;
    final int streak = _n(st['count']).toInt();
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 10, 12, 10),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: <Color>[_gold.withOpacity(done ? .10 : .20), _gold.withOpacity(.05)]),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _gold.withOpacity(done ? .3 : .6)),
      ),
      child: Row(children: <Widget>[
        Container(
          width: 34,
          height: 34,
          decoration: BoxDecoration(shape: BoxShape.circle, color: done ? _sage.withOpacity(.25) : _gold.withOpacity(.18), border: Border.all(color: done ? _sage : _gold.withOpacity(.6))),
          child: Icon(done ? Icons.check_rounded : Icons.flag_rounded, size: 18, color: done ? _sage : _goldSoft),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: <Widget>[
            Row(children: <Widget>[
              Text(done ? 'DONE FOR TODAY' : 'TODAY', style: const TextStyle(color: _muted, fontSize: 9.5, letterSpacing: 2, fontWeight: FontWeight.w700)),
              if (streak > 0) ...<Widget>[
                const SizedBox(width: 8),
                const Icon(Icons.local_fire_department_rounded, size: 13, color: _rose),
                const SizedBox(width: 2),
                Text('$streak day${streak == 1 ? '' : 's'}', style: const TextStyle(color: _rose, fontSize: 11, fontWeight: FontWeight.w700)),
              ],
            ]),
            const SizedBox(height: 2),
            Text(done ? 'Tomorrow brings the next one. Keep the streak.' : _s(t['title']), maxLines: 2, overflow: TextOverflow.ellipsis, style: TextStyle(color: _ivory, fontSize: 14.5, fontWeight: FontWeight.w700, height: 1.25, decoration: done ? TextDecoration.none : null)),
            if (!done && _s(t['why']).isNotEmpty) Text(_s(t['why']), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 12)),
          ]),
        ),
        const SizedBox(width: 8),
        if (!done) ...<Widget>[
          _btn('Do it', () => _ask(_s(t['ask'])), gold: true, icon: Icons.auto_awesome_rounded),
          const SizedBox(width: 6),
          _btn('', _doneBusy ? null : _markDone, icon: Icons.check_rounded),
        ],
      ]),
    );
  }

  // ---- the numbers vendors check (JC-LAZO-JUNE-NATIVE-1011-004)
  Widget _intelCard() {
    final Map<String, dynamic> i = _map(_snap['intel']);
    final Map<String, dynamic> rank = _map(i['rank']);
    final Map<String, dynamic> views = _map(i['views']);
    final Map<String, dynamic> rv = _map(i['reviews']);
    final Map<String, dynamic> wk = _map(i['week']);
    final num delta = _n(i['rankDelta']);
    final String pos = _s(i['pricePos']);
    String line(String k, String v, {Color? c}) => '$k|$v';
    final List<String> rows = <String>[
      if (rank.isNotEmpty) line('Rank in ${_s(_map(_snap['vendor'])['metro'])}', '#${_n(rank['pos']).toInt()} of ${_n(rank['of']).toInt()}${delta != 0 ? (delta > 0 ? '  ▲ up ${delta.abs().toInt()} this week' : '  ▼ down ${delta.abs().toInt()} this week') : ''}'),
      if (views.isNotEmpty) line('Profile views, 7 days', '${_n(views['d7']).toInt()}${_n(views['d7Prev']) > 0 ? '  (${_n(views['d7Prev']).toInt()} the week before)' : ''}'),
      if (pos.isNotEmpty) line('Starting price', '\\$${_n(i['startingPrice']).toInt()} - ${pos == 'below' ? 'below' : pos == 'above' ? 'above' : 'about'} the ${_s(_map(_snap['vendor'])['metro'])} median'),
      if (_n(rv['count']) > 0) line('Reviews', '${_n(rv['count']).toInt()} · ${_n(rv['average']).toStringAsFixed(1)} average'),
      if (wk.isNotEmpty) line('Last 7 days', 'leads ${_n(wk['leads']).toInt()} (${_n(wk['leadsPrev']).toInt()} before) · replies ${_n(wk['replies']).toInt()} · booked ${_n(wk['booked']).toInt()}'),
      if (_n(i['metroVendors']) > 0) line('Your category here', '${_n(i['metroVendors']).toInt()} vendors'),
    ];
    return _card(
      title: 'Your numbers',
      sub: 'What couples see when they compare. Ask me "what changed this week?" for the story behind them.',
      child: rows.isEmpty
          ? const Text('No numbers yet - they fill in after your first week on Lazo.', style: TextStyle(color: _muted, fontSize: 13))
          : Column(children: <Widget>[
              for (final String r in rows)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                    SizedBox(width: 150, child: Text(r.split('|')[0], style: const TextStyle(color: _muted, fontSize: 12.5))),
                    Expanded(child: Text(r.split('|')[1], style: const TextStyle(color: _ivory, fontSize: 13.5, fontWeight: FontWeight.w600))),
                  ]),
                ),
            ]),
    );
  }

  // ---- the RSVP pulse (JC-LAZO-JUNE-NATIVE-1011-004)
  Widget _rsvpCard() {
    final Map<String, dynamic> r = _map(_snap['rsvp']);
    final List<String> silent = (r['silent'] is List ? (r['silent'] as List) : <dynamic>[]).map((dynamic e) => _s(e)).where((String e) => e.isNotEmpty).toList();
    final String nudge = 'Hi! We\\'re finalising numbers for the wedding - could you let us know if you can make it? The RSVP link is on our site. Thank you! x';
    return _card(
      title: 'RSVPs',
      sub: _n(r['total']) == 0 ? 'Add guests and the pulse starts here.' : '${_n(r['yes']).toInt()} yes · ${_n(r['no']).toInt()} no · ${_n(r['pending']).toInt()} pending',
      trailing: _n(r['pending']) > 0 ? _btn('Who\\'s silent?', () => _ask('Who hasn\\'t RSVP\\'d?'), gold: true) : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Row(children: <Widget>[_stat('${_n(r['yes']).toInt()}', 'coming', color: _sage), _stat('${_n(r['pending']).toInt()}', 'pending', color: _goldSoft), _stat('${_n(r['no']).toInt()}', 'can\\'t', color: _rose)]),
        if (silent.isNotEmpty) ...<Widget>[
          const SizedBox(height: 10),
          Text('Still quiet: ${silent.take(8).join(', ')}${silent.length > 8 ? ' and more' : ''}', style: const TextStyle(color: _ivory, fontSize: 13, height: 1.4)),
          const SizedBox(height: 10),
          Row(children: <Widget>[
            _btn('Copy a nudge', () {
              Clipboard.setData(ClipboardData(text: nudge));
              _addMsg('sys', 'Nudge copied - paste it into a text or email.');
            }, icon: Icons.copy_rounded),
            const SizedBox(width: 8),
            _btn('Write one for me', () => _ask('Write a friendly RSVP nudge I can text to the guests who haven\\'t replied'), gold: true),
          ]),
        ],
      ]),
    );
  }

  // ---- the daily post idea (JC-LAZO-JUNE-NATIVE-1011-004)
  Future<void> _loadPostIdea() async {
    if (_postBusy) return;
    setState(() => _postBusy = true);
    try {
      final Map<String, dynamic> j = await _api.get('/api/post-idea');
      if (mounted) setState(() => _postIdea = j);
    } catch (e) {
      if (mounted) setState(() => _postIdea = <String, dynamic>{'error': e.toString()});
    }
    if (mounted) setState(() => _postBusy = false);
  }

  Widget _postIdeaCard() {
    final Map<String, dynamic> p = _postIdea ?? <String, dynamic>{};
    final String caption = _s(p['caption']);
    final String photo = _s(p['photo']);
    final bool studio = _map(_snap['vendor'])['studio'] == true;
    if (_postIdea == null && !_postBusy) _loadPostIdea();
    return _card(
      title: 'Today\\'s post',
      sub: 'One caption a day from your own work. Copy it, or hand it to me.',
      trailing: _btn('', _postBusy ? null : () {
        _postIdea = null;
        _loadPostIdea();
      }, icon: Icons.refresh_rounded),
      child: _postBusy || _postIdea == null
          ? const Padding(padding: EdgeInsets.symmetric(vertical: 10), child: Text('June is looking through your gallery…', style: TextStyle(color: _muted, fontStyle: FontStyle.italic)))
          : caption.isEmpty
              ? Text(_s(p['error']).isNotEmpty ? 'Couldn\\'t write one: ${_s(p['error'])}' : 'Add a few photos to your gallery and she will have something to say.', style: const TextStyle(color: _muted, fontSize: 13))
              : Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                  if (photo.isNotEmpty)
                    ClipRRect(borderRadius: BorderRadius.circular(12), child: Image.network(photo, height: 160, width: double.infinity, fit: BoxFit.cover, errorBuilder: (_, __, ___) => const SizedBox.shrink())),
                  if (photo.isNotEmpty) const SizedBox(height: 10),
                  Text(caption, style: const TextStyle(color: _ivory, fontSize: 13.5, height: 1.5)),
                  const SizedBox(height: 10),
                  Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                    _btn('Copy caption', () {
                      Clipboard.setData(ClipboardData(text: caption));
                      _addMsg('sys', 'Caption copied.');
                    }, icon: Icons.copy_rounded, gold: !studio),
                    if (studio) _btn('Post it with June', () => _ask('Post this to Instagram and Facebook: $caption'), gold: true, icon: Icons.send_rounded),
                    _btn('Different angle', () => _ask('Give me another caption idea for today, a different angle'), icon: Icons.auto_awesome_rounded),
                  ]),
                ]),
    );
  }

  // ---- focus (JC-LAZO-JUNE-NATIVE-1011-004)
  Widget _focusCard() {
    final bool on = _focusEnd != null;
    return _card(
      title: 'Focus',
      sub: on ? 'Head down. ${_focusLeft().replaceAll('focus ', '')} left. The radio stays on; I\\'ll tell you when.' : 'A block of real work with the radio on. I\\'ll keep quiet and tell you when time is up.',
      trailing: on ? _btn('Stop', _focusStop, icon: Icons.stop_rounded) : null,
      child: Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
        for (final int m in <int>[25, 50, 90]) _btn('$m min', on ? null : () => _focusStart(m), gold: m == 50, icon: Icons.timer_rounded),
      ]),
    );
  }

  Widget _deck(BuildContext context) {''', 'cards')

# ---------------------------------------------------------------- the dock grows
s = rep(s, "      _dockBtn(Icons.radio_rounded, 'Radio', () => _sheet('Radio', _radioCard), on: _radioName.isNotEmpty),",
        '''      if (!_couple) _dockBtn(Icons.insights_rounded, 'Numbers', () => _sheet('Numbers', _intelCard)),
      if (_couple) _dockBtn(Icons.mail_rounded, 'RSVPs', () => _sheet('RSVPs', _rsvpCard), badge: _n(_map(_snap['rsvp'])['pending']) > 0 ? '${_n(_map(_snap['rsvp'])['pending']).toInt()}' : null),
      if (!_couple) _dockBtn(Icons.camera_alt_rounded, 'Post idea', () => _sheet('Post idea', _postIdeaCard)),
      _dockBtn(Icons.timer_rounded, 'Focus', () => _sheet('Focus', _focusCard), on: _focusEnd != null),
      _dockBtn(Icons.radio_rounded, 'Radio', () => _sheet('Radio', _radioCard), on: _radioName.isNotEmpty),''', 'dock')

# ---------------------------------------------------------------- chips from the day
s = rep(s, "      if (_n(money['open']) > 0) out.add('What\\'s due this month?');",
        '''      if (_n(money['open']) > 0) out.add('What\\'s due this month?');
      if (_n(_map(_snap['budgetRoom'])['unallocated']) > 500) out.add('Where can we move money?');
      final List<Map<String, dynamic>> threads = _list(_snap['threads']);
      if (threads.isNotEmpty && _s(threads.first['vendor']).isNotEmpty) out.add('Questions for our call with ${_s(threads.first['vendor'])}');''', 'couple chips')
s = rep(s, "      if (reminders.isNotEmpty) out.add('What are my reminders?');",
        '''      if (reminders.isNotEmpty) out.add('What are my reminders?');
      if (_n(_map(_snap['intel'])['rankDelta']) != 0) out.add('What changed in my numbers this week?');''', 'vendor chips')

s = rep(s, "// END OF FILE - JC-LAZO-JUNE-NATIVE-1011-003", "// END OF FILE - JC-LAZO-JUNE-NATIVE-1011-004", 'end')

# clear the chat from the box itself, the dock, or by saying so
s = rep(s, '  Widget _chatBox(double height) => Container(\n        height: height,\n        decoration: BoxDecoration(color: Colors.black.withOpacity(.25), borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.white.withOpacity(.08))),\n        child: _chat.isEmpty', '  // JC-LAZO-JUNE-NATIVE-1011-004: a clean page - from the box, the dock, or "clear the chat"\n  void _clearChat() {\n    _voice.stop();\n    setState(() {\n      _chat.clear();\n      _hist = <Map<String, dynamic>>[];\n      _heard = \'\';\n      _mode = \'idle\';\n    });\n  }\n\n  Widget _chatBox(double height) => Container(\n        height: height,\n        decoration: BoxDecoration(color: Colors.black.withOpacity(.25), borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.white.withOpacity(.08))),\n        clipBehavior: Clip.antiAlias,\n        child: Stack(children: <Widget>[\n          Positioned.fill(child: _chatList()),\n          if (_chat.isNotEmpty)\n            Positioned(\n              top: 6,\n              right: 6,\n              child: GestureDetector(\n                onTap: _clearChat,\n                child: Container(\n                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),\n                  decoration: BoxDecoration(color: Colors.black.withOpacity(.45), borderRadius: BorderRadius.circular(999), border: Border.all(color: Colors.white.withOpacity(.16))),\n                  child: const Row(mainAxisSize: MainAxisSize.min, children: <Widget>[Icon(Icons.close_rounded, size: 12, color: _muted), SizedBox(width: 4), Text(\'Clear\', style: TextStyle(color: _muted, fontSize: 11, fontWeight: FontWeight.w700))]),\n                ),\n              ),\n            ),\n        ]),\n      );\n\n  Widget _chatList() => _chat.isEmpty', 'chat clear box')
s = rep(s, "    if (RegExp(r'^(what time is it|time)$').hasMatch(t)) {", "    if (RegExp(r'^(clear|reset|wipe|start over)( the| our| my)? ?(chat|conversation|page)?$').hasMatch(t) && t.length > 4) {\n      _clearChat();\n      return 'Fresh page. What next?';\n    }\n    if (RegExp(r'^(what time is it|time)$').hasMatch(t)) {", 'chat clear voice')
s = rep(s, "      if (_chat.isNotEmpty)\n        _dockBtn(Icons.cleaning_services_rounded, 'Clear chat', () => setState(() {\n              _chat.clear();\n              _hist = <Map<String, dynamic>>[];\n            })),", "      if (_chat.isNotEmpty) _dockBtn(Icons.cleaning_services_rounded, 'Clear chat', _clearChat),", 'chat clear dock')
# the Morning sheet, first in the dock
s = rep(s, "    return Wrap(spacing: 6, runSpacing: 6, children: <Widget>[\n      _dockBtn(Icons.auto_stories_rounded, 'Brief', () => _sheet('Brief', _briefCard)),", "    return Wrap(spacing: 6, runSpacing: 6, children: <Widget>[\n      _dockBtn(Icons.wb_twilight_rounded, 'Morning', () => _sheet('Morning', _morningCard)),\n      _dockBtn(Icons.auto_stories_rounded, 'Brief', () => _sheet('Brief', _briefCard)),", 'dock morning')
s = rep(s, "  Widget _deck(BuildContext context) {", "  // ---- the morning (JC-LAZO-JUNE-NATIVE-1011-004): the sky, the city, the trade, the calendar\n  Widget _morningCard() {\n    final List<Map<String, dynamic>> news = _list(_snap['news']);\n    final List<Map<String, dynamic>> ind = _list(_snap['industry']);\n    final String metro = _s(_map(_snap[_couple ? 'couple' : 'vendor'])['metro']);\n    final List<Map<String, dynamic>> cal = <Map<String, dynamic>>[];\n    if (_couple) {\n      cal.addAll(_list(_snap['upcoming']).take(4));\n    } else {\n      for (final Map<String, dynamic> c in _list(_snap['consults']).take(3)) cal.add(<String, dynamic>{'when': _s(c['startAt']), 'kind': 'Consult', 'who': _s(c['who']), 'time': true});\n      for (final Map<String, dynamic> w in _list(_snap['weddings']).take(2)) cal.add(<String, dynamic>{'when': _s(w['weddingDate']), 'kind': 'Wedding', 'who': _s(w['couple'])});\n      cal.sort((Map<String, dynamic> a, Map<String, dynamic> b) => _s(a['when']).compareTo(_s(b['when'])));\n    }\n    Widget head(String t) => Padding(padding: const EdgeInsets.only(top: 14, bottom: 6), child: Text(t.toUpperCase(), style: const TextStyle(color: _muted, fontSize: 10, letterSpacing: 2, fontWeight: FontWeight.w700)));\n    Widget headline(Map<String, dynamic> n) => Padding(\n          padding: const EdgeInsets.symmetric(vertical: 5),\n          child: GestureDetector(\n            onTap: () {\n              final String u = _s(n['url']);\n              if (u.isNotEmpty) launchUrl(Uri.parse(u), mode: LaunchMode.externalApplication);\n            },\n            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[\n              const Padding(padding: EdgeInsets.only(top: 6), child: Icon(Icons.circle, size: 5, color: _gold)),\n              const SizedBox(width: 9),\n              Expanded(child: Text(_s(n['title']), style: const TextStyle(color: _ivory, fontSize: 13.5, height: 1.4))),\n              if (_s(n['source']).isNotEmpty) Padding(padding: const EdgeInsets.only(left: 8, top: 2), child: Text(_s(n['source']), style: const TextStyle(color: _muted, fontSize: 11))),\n            ]),\n          ),\n        );\n    String when(Map<String, dynamic> e) {\n      final String w = _s(e['when']);\n      if (w.length < 10) return w;\n      return e['time'] == true && w.length >= 16 ? w.replaceFirst('T', ' ').substring(5, 16) : w.substring(5, 10);\n    }\n    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[\n      _weatherCard(),\n      _card(\n        title: 'This morning',\n        sub: 'The city, the trade, and what is on your calendar. Ask me about any of it.',\n        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[\n          head(metro.isEmpty ? 'In your city' : 'In $metro'),\n          if (news.isEmpty) const Text('Nothing local came through this morning.', style: TextStyle(color: _muted, fontSize: 13)) else for (final Map<String, dynamic> n in news.take(3)) headline(n),\n          if (ind.isNotEmpty) ...<Widget>[head('In the wedding world'), headline(ind.first)],\n          head('On your calendar'),\n          if (cal.isEmpty)\n            Text(_couple ? 'Nothing booked. A quiet day is a planning day.' : 'No consults or weddings on the books this week.', style: const TextStyle(color: _muted, fontSize: 13))\n          else\n            for (final Map<String, dynamic> e in cal)\n              Padding(\n                padding: const EdgeInsets.symmetric(vertical: 4),\n                child: Row(children: <Widget>[\n                  SizedBox(width: 92, child: Text(when(e), style: const TextStyle(color: _goldSoft, fontSize: 12.5, fontWeight: FontWeight.w700))),\n                  Expanded(child: Text(_s(e['kind']) + (_s(e['who']).isNotEmpty ? ' · ' + _s(e['who']) : ''), style: const TextStyle(color: _ivory, fontSize: 13.5))),\n                ]),\n              ),\n        ]),\n      ),\n    ]);\n  }\n\n  Widget _deck(BuildContext context) {", 'morning card')

# the chat list is its own expression now; drop the Container's old closing
s = rep(s, '                itemBuilder: (BuildContext c, int i) => _bubble(_chat[i]),\n              ),\n      );\n\n  Widget _inputRow() => Row(children: <Widget>[', '                itemBuilder: (BuildContext c, int i) => _bubble(_chat[i]),\n              );\n\n  Widget _inputRow() => Row(children: <Widget>[', 'chat list tail')

# iOS: currentTime is not on the phone stub of AudioElement; read it dynamically
s = rep(s, '        final html.AudioElement? a = _el;\n        if (a != null) return a.currentTime.toDouble();', '        // read dynamically: the phone stub of the element has no currentTime (iOS archive failed on it)\n        final dynamic a = _el;\n        if (a != null) return ((a.currentTime as num?) ?? 0).toDouble();', 'ios currentTime')
(HERE / "JuneNative_v4.txt").write_text(s, encoding="utf-8")
print("wrote JuneNative_v4.txt", len(s))

"""patch_couple_v150.py - JC-LAZO-COUPLE-1010-V150
Couple_master_v149 -> v150: THE DECK. The home hero is a command deck: names, date and city, the
countdown, this week's step and the four numbers along the top, and June herself across it
(JuneNative layout 'deck': her core moving with her real voice, her read of the day, chat, mic, the
brief). The floating Ask June bar stays on every other screen but leaves Home, where she already is.
Cards get a soft lift in light mode. Needs JuneNative_v2.
  python app-patches\\patch_couple_v150.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent


def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    return s.replace(old, new)


s = (HERE / "Couple_master_v149.txt").read_text(encoding="utf-8-sig")
NOTE = ("THE DECK - June is the hero of Home: names, date, the countdown, this week's step and the four numbers along "
        "the top of the deck, June herself across it (JuneNative layout 'deck': her core moving with her real voice, her "
        "read of the day, chat, mic, the brief). The floating Ask June bar leaves Home and stays on every other screen. "
        "Cards get a soft lift in light mode. Needs JuneNative_v2. JC-LAZO-COUPLE-1010-V150")
s = rep(s, "// (v149: ", "// (v150: " + NOTE + "; base v149)\n// (v149: ", 'note')
s = rep(s, "// END OF FILE - JC-LAZO-COUPLE-1009-V149", "// END OF FILE - JC-LAZO-COUPLE-1010-V150", 'end')

# the floating bar leaves Home (June is in the deck there) and keeps its tour key elsewhere
s = rep(s, "                    if (_view != _View.june && _uid != null) _askJuneBar(),",
        "                    // JC-LAZO-COUPLE-1010-V150: not on Home either - June is the deck there\n"
        "                    if (_view != _View.june && _view != _View.hub && _uid != null) _askJuneBar(),", 'bar')

# the hero becomes the deck
a = s.index("  Widget _heroToday(")
b = s.index("  String _bookedLine(Map<String, Map<String, dynamic>> plan) {")
h = s[a:b]
h = rep(h, '''                  colors: <Color>[
                    Color(0x333D1C3B),
                    Color(0xC63D1C3B),
                    Color(0xF23D1C3B)
                  ],
                  stops: <double>[0, .55, 1],''',
        '''                  colors: <Color>[
                    Color(0x663D1C3B),
                    Color(0xE63D1C3B),
                    Color(0xF9241022)
                  ],
                  stops: <double>[0, .4, 1],''', 'overlay')
h = rep(h, "        constraints: BoxConstraints(minHeight: wide ? 220 : 0),\n", "", 'minheight')
h = rep(h, '''            child: wide
                ? Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: <Widget>[
                        Expanded(child: nameBlock),
                        const SizedBox(width: 22),
                        grid,
                      ])
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                        nameBlock,
                        const SizedBox(height: 16),
                        grid,
                      ]),
          ),''',
        '''            // JC-LAZO-COUPLE-1010-V150: the deck - the day along the top,
            // June across it.
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                wide
                    ? Row(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: <Widget>[
                            Expanded(child: nameBlock),
                            const SizedBox(width: 22),
                            grid,
                          ])
                    : Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                            nameBlock,
                            const SizedBox(height: 16),
                            grid,
                          ]),
                SizedBox(height: wide ? 22 : 18),
                Container(height: 1, color: gold.withOpacity(.38)),
                SizedBox(height: wide ? 22 : 18),
                KeyedSubtree(
                    key: _kTourJune,
                    child: const JuneNative(role: 'couple', layout: 'deck')),
              ],
            ),
          ),''', 'hero body')
s = s[:a] + h + s[b:]

# cards: a soft lift in light mode
s = rep(s, '''        border: Border.all(color: _lzLine(borderColor ?? goldLine), width: 1),
      ),
      child: child,
    );
  }

  @override
  Widget build(BuildContext context) {''',
        '''        border: Border.all(color: _lzLine(borderColor ?? goldLine), width: 1),
        // JC-LAZO-COUPLE-1010-V150: a soft lift in light mode
        boxShadow: _lzDark
            ? null
            : <BoxShadow>[
                BoxShadow(
                    color: plumDeep.withOpacity(.07),
                    blurRadius: 22,
                    offset: const Offset(0, 8)),
              ],
      ),
      child: child,
    );
  }

  @override
  Widget build(BuildContext context) {''', 'glass shadow')

# the tour's welcome step has no target: paint the dim without a tween
s = rep(s, "              child: TweenAnimationBuilder<Rect?>(\n                // v130: re-key when the ring first appears so it doesn't\n                // grow out of the top-left corner (Rect.lerp from null).\n                key: ValueKey<bool>(r == null),\n                tween: RectTween(begin: r, end: r),\n                duration:\n                    Duration(milliseconds: _reducedMotion(context) ? 0 : 260),\n                curve: Curves.easeOutCubic,\n                builder: (BuildContext bc, Rect? v, Widget? _) =>\n                    CustomPaint(painter: _SpotlightPainter(v, plum)),\n              ),",
        "              // JC-LAZO-COUPLE-1010-V150: a step with no target (the welcome card) paints the\n              // dim directly - a RectTween with a null end trips an assert in\n              // debug builds, and there is nothing to animate to anyway.\n              child: r == null\n                  ? CustomPaint(painter: _SpotlightPainter(null, plum))\n                  : TweenAnimationBuilder<Rect?>(\n                      // v130: re-key when the ring first appears so it doesn't\n                      // grow out of the top-left corner (Rect.lerp from null).\n                      key: const ValueKey<bool>(false),\n                      tween: RectTween(begin: r, end: r),\n                      duration: Duration(\n                          milliseconds: _reducedMotion(context) ? 0 : 260),\n                      curve: Curves.easeOutCubic,\n                      builder: (BuildContext bc, Rect? v, Widget? _) =>\n                          CustomPaint(painter: _SpotlightPainter(v, plum)),\n                    ),", 'tour null rect')

# the tour waits for a step's screen to build before deciding the target is absent
s = rep(s, '    st.before?.call();\n    await Future<void>.delayed(const Duration(milliseconds: 60));\n    BuildContext? tc = st.key?.currentContext;\n    if (tc == null && st.key != null) {',
        "    st.before?.call();\n    // JC-LAZO-COUPLE-1010-V150: a step's screen can take a few frames to build (a tab switch\n    // on a slow phone) - look for the target across frames before calling\n    // it absent, so Money and Profile are never skipped.\n    BuildContext? tc = st.key?.currentContext;\n    for (int i = 0; i < 12 && st.key != null && tc == null; i++) {\n      await WidgetsBinding.instance.endOfFrame;\n      await Future<void>.delayed(const Duration(milliseconds: 40));\n      if (!mounted) return;\n      tc = st.key?.currentContext;\n    }\n    if (tc == null && st.key != null) {", 'tour wait')

# ...and for the target to have a size before scrolling to it; the measurement retries too
s = rep(s, '    BuildContext? tc = st.key?.currentContext;\n    for (int i = 0; i < 12 && st.key != null && tc == null; i++) {\n      await WidgetsBinding.instance.endOfFrame;\n      await Future<void>.delayed(const Duration(milliseconds: 40));\n      if (!mounted) return;\n      tc = st.key?.currentContext;\n    }\n    if (tc == null && st.key != null) {',
        '    BuildContext? tc = st.key?.currentContext;\n    bool laidOut(BuildContext? c) {\n      if (c == null) return false;\n      final RenderObject? ro = c.findRenderObject();\n      return ro is RenderBox && ro.hasSize;\n    }\n\n    for (int i = 0; i < 12 && st.key != null && !laidOut(tc); i++) {\n      await WidgetsBinding.instance.endOfFrame;\n      await Future<void>.delayed(const Duration(milliseconds: 40));\n      if (!mounted) return;\n      tc = st.key?.currentContext;\n    }\n    if (tc == null && st.key != null) {', 'tour laid out')
s = rep(s, '    if (!mounted) return;\n    _tourMeasuring = true;\n    WidgetsBinding.instance.addPostFrameCallback((_) {\n      _tourMeasuring = false;\n      if (!mounted) return;\n      final RenderObject? rootRo =\n          _tourRootKey.currentContext?.findRenderObject();\n      final RenderObject? ro = st.key?.currentContext?.findRenderObject();\n      Rect? r;\n      if (rootRo is RenderBox && ro is RenderBox && ro.hasSize) {\n        final Offset o = ro.localToGlobal(Offset.zero, ancestor: rootRo);\n        r = Rect.fromLTWH(o.dx, o.dy, ro.size.width, ro.size.height).inflate(6);\n      }\n      setState(() => _tourRect = r);\n    });\n  }',
        '    if (!mounted) return;\n    _tourMeasuring = true;\n    // measure after the frame; if the target has no size yet, try again for\n    // a few frames rather than leaving the ring off the screen\n    Rect? measure() {\n      final RenderObject? rootRo =\n          _tourRootKey.currentContext?.findRenderObject();\n      final RenderObject? ro = st.key?.currentContext?.findRenderObject();\n      if (rootRo is RenderBox && ro is RenderBox && ro.hasSize) {\n        final Offset o = ro.localToGlobal(Offset.zero, ancestor: rootRo);\n        return Rect.fromLTWH(o.dx, o.dy, ro.size.width, ro.size.height)\n            .inflate(6);\n      }\n      return null;\n    }\n\n    for (int i = 0; i < 10; i++) {\n      await WidgetsBinding.instance.endOfFrame;\n      if (!mounted) return;\n      final Rect? r = measure();\n      if (r != null || st.key == null || i == 9) {\n        _tourMeasuring = false;\n        setState(() => _tourRect = r);\n        return;\n      }\n    }\n  }', 'tour measure')

# the tour's June step says where she is now
s = rep(s, '      _TourStep(\'Ask June anything\',\n          \'She knows your plan, your budget and your city. "Is \\u002435k realistic here?" "What should I ask a photographer?" Ask from any screen.\',\n          key: _kTourJune),',
        '      _TourStep(\'June\',\n          \'She lives on your deck, and she talks. Tap the mic or type - "Is \\u002435k realistic here?" "What should I ask a photographer?" She knows your plan, your budget and your city, and reads you the day\\\'s brief aloud.\',\n          key: _kTourJune),', 'tour june copy')
(HERE / "Couple_master_v150.txt").write_text(s, encoding="utf-8")
print("wrote Couple_master_v150.txt", len(s))

"""patch_vendor_v186.py - JC-LAZO-VDASH-1010-186
Vendor_master_v185 -> v186: THE DECK. June is no longer a card on the rail. On Today the hero is a
command deck: the business name and the live numbers (waiting, reply, next wedding, views) along the
top, and June herself across it - her core moving with her real voice, her read of the day, the chat,
the mic, the brief. The rail keeps the sky and the consults. Cards get a soft lift in light mode.
Needs JuneNative_v2 (layout: 'deck').
  python app-patches\\patch_vendor_v186.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent


def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    return s.replace(old, new)


s = (HERE / "Vendor_master_v185.txt").read_text(encoding="utf-8-sig")
NOTE = ("THE DECK - June is the hero of Today: the business name and the live numbers along the top of the deck, "
        "June herself across it (JuneNative layout 'deck': her core moving with her real voice, her read of the day, "
        "chat, mic, the brief). The Ask June card is gone from the rail; the sky and consults stay. Cards get a soft "
        "lift in light mode. Needs JuneNative_v2. JC-LAZO-VDASH-1010-186")
s = rep(s, "// Build ID: JC-LAZO-VDASH-1009-185 (v185:", "// Build ID: JC-LAZO-VDASH-1010-186 (v186: " + NOTE + "; base v185) (v185:", 'note')
s = rep(s, "// END OF FILE - JC-LAZO-VDASH-1009-185", "// END OF FILE - JC-LAZO-VDASH-1010-186", 'end')

# the Ask June card leaves the Today column and the rail
s = rep(s, '''              final Widget june = KeyedSubtree(
                  key: _kTourJune,
                  child: _fold(
                      'june',
                      'Ask June',
                      _foldSummary('june', vendorId, vd),
                      _askJuneCard(vendorId, vd)));
''', "              // JC-LAZO-VDASH-1010-186: June lives in the deck now (see _heroToday)\n", 'june var')
s = rep(s, "                if (!wide) ...<Widget>[june, const SizedBox(height: 16)],\n", "", 'june phone')
s = rep(s, "                  ? <Widget>[june, const SizedBox(height: 14), sky, consults]", "                  ? <Widget>[sky, consults]", 'june rail')

# the hero becomes the deck
a = s.index("  Widget _heroToday(String vendorId, Map<String, dynamic> vd, bool wide) {")
b = s.index("  Widget _verifyState(String vendorId, Map<String, dynamic> vd) {")
h = s[a:b]
h = rep(h, '''                      colors: <Color>[
                        Color(0x333D1C3B),
                        Color(0xC63D1C3B),
                        Color(0xF23D1C3B)
                      ],
                      stops: <double>[0, .55, 1],''',
        '''                      colors: <Color>[
                        Color(0x663D1C3B),
                        Color(0xE63D1C3B),
                        Color(0xF9241022)
                      ],
                      stops: <double>[0, .4, 1],''', 'hero overlay')
h = rep(h, '''                child: wide
                    ? Row(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: <Widget>[
                          Expanded(child: nameBlock),
                          const SizedBox(width: 20),
                          grid,
                        ],
                      )
                    : Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          nameBlock,
                          const SizedBox(height: 16),
                          grid,
                        ],
                      ),''',
        '''                // JC-LAZO-VDASH-1010-186: the deck - the name and the numbers along
                // the top, June across it.
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    wide
                        ? Row(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: <Widget>[
                              Expanded(child: nameBlock),
                              const SizedBox(width: 20),
                              grid,
                            ],
                          )
                        : Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              nameBlock,
                              const SizedBox(height: 16),
                              grid,
                            ],
                          ),
                    SizedBox(height: wide ? 22 : 18),
                    Container(height: 1, color: gold.withOpacity(.38)),
                    SizedBox(height: wide ? 22 : 18),
                    KeyedSubtree(
                        key: _kTourJune,
                        child: const JuneNative(role: 'vendor', layout: 'deck')),
                  ],
                ),''', 'hero body')
h = rep(h, "    return Container(\n          constraints: BoxConstraints(minHeight: wide ? 176 : 0),\n", "    return Container(\n", 'hero minheight') if "constraints: BoxConstraints(minHeight: wide ? 176 : 0)," in h and False else h
h = rep(h, "          constraints: BoxConstraints(minHeight: wide ? 176 : 0),\n", "", 'hero minheight')
s = s[:a] + h + s[b:]

# cards: a soft lift in light mode (dark mode keeps the flat glass)
s = rep(s, '''        border: Border.all(color: _lzLine(borderColor ?? goldLine), width: 1),
      ),
      child: child,
    );
  }

  @override
  Widget build(BuildContext context) {''',
        '''        border: Border.all(color: _lzLine(borderColor ?? goldLine), width: 1),
        // JC-LAZO-VDASH-1010-186: a soft lift in light mode
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
s = rep(s, "              child: TweenAnimationBuilder<Rect?>(\n                // v175: re-key when the ring first appears so it doesn't\n                // grow out of the top-left corner (Rect.lerp from null).\n                key: ValueKey<bool>(r == null),\n                tween: RectTween(begin: r, end: r),\n                duration:\n                    Duration(milliseconds: _reducedMotion(context) ? 0 : 260),\n                curve: Curves.easeOutCubic,\n                builder: (BuildContext bc, Rect? v, Widget? _) =>\n                    CustomPaint(painter: _SpotlightPainter(v, plum)),\n              ),",
        "              // JC-LAZO-VDASH-1010-186: a step with no target (the welcome card) paints the\n              // dim directly - a RectTween with a null end trips an assert in\n              // debug builds, and there is nothing to animate to anyway.\n              child: r == null\n                  ? CustomPaint(painter: _SpotlightPainter(null, plum))\n                  : TweenAnimationBuilder<Rect?>(\n                      // v175: re-key when the ring first appears so it doesn't\n                      // grow out of the top-left corner (Rect.lerp from null).\n                      key: const ValueKey<bool>(false),\n                      tween: RectTween(begin: r, end: r),\n                      duration: Duration(\n                          milliseconds: _reducedMotion(context) ? 0 : 260),\n                      curve: Curves.easeOutCubic,\n                      builder: (BuildContext bc, Rect? v, Widget? _) =>\n                          CustomPaint(painter: _SpotlightPainter(v, plum)),\n                    ),", 'tour null rect')

# the tour waits for a step's screen to build before deciding the target is absent
s = rep(s, '    st.before?.call();\n    await Future<void>.delayed(const Duration(milliseconds: 60));\n    BuildContext? tc = st.key?.currentContext;\n    if (tc == null && st.key != null) {',
        "    st.before?.call();\n    // JC-LAZO-VDASH-1010-186: a step's screen can take a few frames to build (a tab switch\n    // on a slow phone) - look for the target across frames before calling\n    // it absent, so Money and Profile are never skipped.\n    BuildContext? tc = st.key?.currentContext;\n    for (int i = 0; i < 12 && st.key != null && tc == null; i++) {\n      await WidgetsBinding.instance.endOfFrame;\n      await Future<void>.delayed(const Duration(milliseconds: 40));\n      if (!mounted) return;\n      tc = st.key?.currentContext;\n    }\n    if (tc == null && st.key != null) {", 'tour wait')

# ...and for the target to have a size before scrolling to it; the measurement retries too
s = rep(s, '    BuildContext? tc = st.key?.currentContext;\n    for (int i = 0; i < 12 && st.key != null && tc == null; i++) {\n      await WidgetsBinding.instance.endOfFrame;\n      await Future<void>.delayed(const Duration(milliseconds: 40));\n      if (!mounted) return;\n      tc = st.key?.currentContext;\n    }\n    if (tc == null && st.key != null) {',
        '    BuildContext? tc = st.key?.currentContext;\n    bool laidOut(BuildContext? c) {\n      if (c == null) return false;\n      final RenderObject? ro = c.findRenderObject();\n      return ro is RenderBox && ro.hasSize;\n    }\n\n    for (int i = 0; i < 12 && st.key != null && !laidOut(tc); i++) {\n      await WidgetsBinding.instance.endOfFrame;\n      await Future<void>.delayed(const Duration(milliseconds: 40));\n      if (!mounted) return;\n      tc = st.key?.currentContext;\n    }\n    if (tc == null && st.key != null) {', 'tour laid out')
s = rep(s, '    if (!mounted) return;\n    _tourMeasuring = true;\n    WidgetsBinding.instance.addPostFrameCallback((_) {\n      _tourMeasuring = false;\n      if (!mounted) return;\n      final RenderObject? rootRo =\n          _tourRootKey.currentContext?.findRenderObject();\n      final RenderObject? ro = st.key?.currentContext?.findRenderObject();\n      Rect? r;\n      if (rootRo is RenderBox && ro is RenderBox && ro.hasSize) {\n        final Offset o = ro.localToGlobal(Offset.zero, ancestor: rootRo);\n        r = Rect.fromLTWH(o.dx, o.dy, ro.size.width, ro.size.height).inflate(6);\n      }\n      setState(() => _tourRect = r);\n    });\n  }',
        '    if (!mounted) return;\n    _tourMeasuring = true;\n    // measure after the frame; if the target has no size yet, try again for\n    // a few frames rather than leaving the ring off the screen\n    Rect? measure() {\n      final RenderObject? rootRo =\n          _tourRootKey.currentContext?.findRenderObject();\n      final RenderObject? ro = st.key?.currentContext?.findRenderObject();\n      if (rootRo is RenderBox && ro is RenderBox && ro.hasSize) {\n        final Offset o = ro.localToGlobal(Offset.zero, ancestor: rootRo);\n        return Rect.fromLTWH(o.dx, o.dy, ro.size.width, ro.size.height)\n            .inflate(6);\n      }\n      return null;\n    }\n\n    for (int i = 0; i < 10; i++) {\n      await WidgetsBinding.instance.endOfFrame;\n      if (!mounted) return;\n      final Rect? r = measure();\n      if (r != null || st.key == null || i == 9) {\n        _tourMeasuring = false;\n        setState(() => _tourRect = r);\n        return;\n      }\n    }\n  }', 'tour measure')

# the tour's June step says where she is now
s = rep(s, '      _TourStep(\'Ask June\',\n          \'"Who is waiting on me?" "What is due this week?" She reads your real threads and money, drafts replies, and adds tasks when you ask.\',\n          key: _kTourJune),',
        '      _TourStep(\'June\',\n          \'She lives on your deck. Tap the mic or type - "Who is waiting on me?" "What is due this week?" She reads your real threads and money, drafts replies, adds tasks when you ask, and reads you today\\\'s brief aloud.\',\n          key: _kTourJune),', 'tour june copy')
(HERE / "Vendor_master_v186.txt").write_text(s, encoding="utf-8")
print("wrote Vendor_master_v186.txt", len(s))

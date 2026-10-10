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
(HERE / "Couple_master_v150.txt").write_text(s, encoding="utf-8")
print("wrote Couple_master_v150.txt", len(s))

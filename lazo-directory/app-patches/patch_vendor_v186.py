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
(HERE / "Vendor_master_v186.txt").write_text(s, encoding="utf-8")
print("wrote Vendor_master_v186.txt", len(s))

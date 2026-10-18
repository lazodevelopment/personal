"""Couple v171: pre-launch review fixes (JC-LAZO-PRELAUNCH-1018-COUPLE).

    python app-patches\\patch_couple_v171.py [base.txt]   # base defaults to Couple_master_v170.txt
                                                          # writes Couple_master_v171.txt
- "This week, with June": on phones the title, the two June buttons and the fold chevron
  shared one row, so the title wrapped one word per line in a 90 px column; the buttons
  now drop under the title when the card is narrower than 520 px
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v170.txt"
DST = HERE / "Couple_master_v171.txt"
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
    "// Build ID: JC-LAZO-PRELAUNCH-1018-COUPLE (v171: PRE-LAUNCH FIXES - the This week, with June header puts its "
    "buttons under the title on phones instead of squeezing the title into a one-word-per-line column; base v170)\n"
) + s[first_build:]

OLD_HEADER = """    final List<List<dynamic>> show = steps.take(3).toList();
    return _glass(
      padding: const EdgeInsets.fromLTRB(22, 18, 22, 14),
      child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Expanded(
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text('This week, with June', style: _serif(size: 24)),
                          const SizedBox(height: 2),
                          Text(
                              show.isEmpty
                                  ? 'Nothing is waiting on you. That is the whole point.'
                                  : '${show.length == 1 ? 'One thing' : show.length == 2 ? 'Two things' : 'Three things'}, in order - from your date, your list and your budget.',
                              style:
                                   TextStyle(fontSize: 13, color: _lzFg(muted))),
                        ]),
                  ),
                  const SizedBox(width: 12),
                  OutlinedButton(
                    style: OutlinedButton.styleFrom(
                        foregroundColor: _lzFg(plum),
                        side: const BorderSide(color: gold),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 10),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10))),
                    onPressed: _h(() => _askJune('')),
                    child: const Text('Ask June',
                        style: TextStyle(
                            fontSize: 13, fontWeight: FontWeight.w700)),
                  ),
                  const SizedBox(width: 6),
                  // v145: the full June, in her own voice, at june.meetlazo.com
                  FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: gold,
                        foregroundColor: plum,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 10),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10))),
                    onPressed: _h(() => _talkToJune()),
                    child: const Text('Talk to June',
                        style: TextStyle(
                            fontSize: 13, fontWeight: FontWeight.w700)),
                  ),
                  const SizedBox(width: 6),
                  _foldBtn('week'),
                ]),
            const SizedBox(height: 6),
"""

NEW_HEADER = """    final List<List<dynamic>> show = steps.take(3).toList();
    // v171: the header's title block and its two buttons; on phones the buttons
    // go under the title (one row squeezed the title to one word per line)
    final Widget weekTitle = Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('This week, with June', style: _serif(size: 24)),
          const SizedBox(height: 2),
          Text(
              show.isEmpty
                  ? 'Nothing is waiting on you. That is the whole point.'
                  : '${show.length == 1 ? 'One thing' : show.length == 2 ? 'Two things' : 'Three things'}, in order - from your date, your list and your budget.',
              style:
                   TextStyle(fontSize: 13, color: _lzFg(muted))),
        ]);
    final Widget askBtn = OutlinedButton(
      style: OutlinedButton.styleFrom(
          foregroundColor: _lzFg(plum),
          side: const BorderSide(color: gold),
          padding: const EdgeInsets.symmetric(
              horizontal: 14, vertical: 10),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10))),
      onPressed: _h(() => _askJune('')),
      child: const Text('Ask June',
          style: TextStyle(
              fontSize: 13, fontWeight: FontWeight.w700)),
    );
    // v145: the full June, in her own voice, at june.meetlazo.com
    final Widget talkBtn = FilledButton(
      style: FilledButton.styleFrom(
          backgroundColor: gold,
          foregroundColor: plum,
          padding: const EdgeInsets.symmetric(
              horizontal: 14, vertical: 10),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10))),
      onPressed: _h(() => _talkToJune()),
      child: const Text('Talk to June',
          style: TextStyle(
              fontSize: 13, fontWeight: FontWeight.w700)),
    );
    return _glass(
      padding: const EdgeInsets.fromLTRB(22, 18, 22, 14),
      child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            LayoutBuilder(builder: (BuildContext c, BoxConstraints box) {
              if (box.maxWidth < 520) {
                return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Expanded(child: weekTitle),
                            const SizedBox(width: 6),
                            _foldBtn('week'),
                          ]),
                      const SizedBox(height: 10),
                      Row(children: <Widget>[
                        askBtn,
                        const SizedBox(width: 6),
                        talkBtn,
                      ]),
                    ]);
              }
              return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Expanded(child: weekTitle),
                    const SizedBox(width: 12),
                    askBtn,
                    const SizedBox(width: 6),
                    talkBtn,
                    const SizedBox(width: 6),
                    _foldBtn('week'),
                  ]);
            }),
            const SizedBox(height: 6),
"""
rep(OLD_HEADER, NEW_HEADER)

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")

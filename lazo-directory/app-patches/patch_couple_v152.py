"""patch_couple_v152.py - JC-LAZO-COUPLE-1011-V152
Couple_master_v151 -> v152: "New to Lazo" expires. The browse card said it for every vendor with
no reviews, forever. Now it shows only within 120 days of the vendor claiming their listing; after
that a vendor with a Google rating shows the rating alone, and one with nothing shows "No reviews yet".
  python app-patches\\patch_couple_v152.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent


def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    return s.replace(old, new)


s = (HERE / "Couple_master_v151.txt").read_text(encoding="utf-8-sig")
s = rep(s, "// (v151: ", "// (v152: NEW TO LAZO EXPIRES - the browse badge shows for 120 days after a vendor claims their listing, then the rating alone or 'No reviews yet'. JC-LAZO-COUPLE-1011-V152; base v151)\n// (v151: ", 'note')
s = rep(s, "// END OF FILE - JC-LAZO-COUPLE-1011-V151", "// END OF FILE - JC-LAZO-COUPLE-1011-V152", 'end')
s = rep(s, '''      if (rating > 0) {
        return Row(children: <Widget>[
          const Icon(Icons.star_rounded, color: Color(0xFFC9A45C), size: 15),
          const SizedBox(width: 3),
          Text(rating.toStringAsFixed(1),
              style:  TextStyle(
                  color: _lzFg(Color(0xFF8A6A2F)),
                  fontSize: 13,
                  fontWeight: FontWeight.w800)),
          const SizedBox(width: 6),
           Text('\\u00b7 New to Lazo',
              style: TextStyle(color: _lzFg(muted), fontSize: 12)),
        ]);
      }
      return  Text('New to Lazo',
          style: TextStyle(color: _lzFg(muted), fontSize: 12));''',
        '''      // JC-LAZO-COUPLE-1011-V152: "New to Lazo" for 120 days after the claim, then it goes quiet
      bool isNew = false;
      final dynamic claimedRaw = v['claimedAt'] ?? v['verifiedAt'];
      if (claimedRaw is Timestamp) {
        isNew = DateTime.now().difference(claimedRaw.toDate()).inDays <= 120;
      }
      if (rating > 0) {
        return Row(children: <Widget>[
          const Icon(Icons.star_rounded, color: Color(0xFFC9A45C), size: 15),
          const SizedBox(width: 3),
          Text(rating.toStringAsFixed(1),
              style:  TextStyle(
                  color: _lzFg(Color(0xFF8A6A2F)),
                  fontSize: 13,
                  fontWeight: FontWeight.w800)),
          if (isNew) ...<Widget>[
            const SizedBox(width: 6),
            Text('\\u00b7 New to Lazo',
                style: TextStyle(color: _lzFg(muted), fontSize: 12)),
          ],
        ]);
      }
      return Text(isNew ? 'New to Lazo' : 'No reviews yet',
          style: TextStyle(color: _lzFg(muted), fontSize: 12));''', 'new to lazo')
(HERE / "Couple_master_v152.txt").write_text(s, encoding="utf-8")
print("wrote Couple_master_v152.txt", len(s))

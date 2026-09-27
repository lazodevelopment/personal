"""patch_nearby3.py - JC-LAZO-WORKER-0915-NEARBY-003
Three things the second run showed against a real venue:
  1. the same business twice - two Butters Pancakes branches, different place
     ids. De-duplicate by name and keep the branch closest to the venue.
  2. no variety - "Coffee & breakfast" came back as four breakfast restaurants
     and not one cafe. Cap each primary type at two per group so a list cannot
     be six steakhouses or four pancake houses.
  3. chains on top - Yard House, First Watch, Snooze. Google's own editorial
     summary usually says "chain"; when it does, take 0.3 off the score. A
     wedding guest flying in wants the local place, not the one they have at home.
Also trims long editorial lines to one clause, and bumps the cache key to v3.
"""
import shutil
from pathlib import Path

P = Path(__file__).resolve().parent / "src" / "index.js"
s = P.read_text(encoding="utf-8")
TAG = "JC-LAZO-WORKER-0915-NEARBY-003"
if TAG in s:
    raise SystemExit("[patch] already applied")
shutil.copy(P, P.with_name("index.js.bak-20260915-nearby3"))


def rep(old, new, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, (n, old[:70])
    s = s.replace(old, new)


rep("""// JC-LAZO-WORKER-0915-NEARBY-002: places are judged by their primary type, so a""",
    f"""// {TAG}: one branch per business (the closest), at most
//   two of any one type per group, and a penalty for places Google itself
//   describes as a chain. Cache key bumped to v3.
// JC-LAZO-WORKER-0915-NEARBY-002: places are judged by their primary type, so a""")

# ---- scoring: local over familiar ----
rep("""// Rating first. Review count is credibility, not a popularity contest: it is
// worth at most +0.16, so it breaks ties and nothing more.
function nbScore(p) {
  return p.rating + Math.min(Math.log10(Math.max(p.votes, 1)), 4) * 0.04;
}""",
    """// Rating first. Review count is credibility, not a popularity contest: it is
// worth at most +0.16, so it breaks ties and nothing more. Google's editorial
// summary says "chain" when a place is one, and a guest who flew in wants the
// place they cannot get at home.
function nbScore(p) {
  const chain = /\\bchains?\\b/i.test(p.blurb || "") ? 0.3 : 0;
  return p.rating + Math.min(Math.log10(Math.max(p.votes, 1)), 4) * 0.04 - chain;
}

// "Butters Pancakes & Cafe" and "Butters Pancakes and Cafe #2" are one business.
function nbName(n) {
  return String(n || "").toLowerCase()
    .replace(/\\b(the|a|an|and)\\b/g, " ")
    .replace(/[^a-z0-9]+/g, " ").trim();
}

// One clause is enough under a name; Google's summaries run long.
function nbTrim(t) {
  t = String(t || "").trim();
  if (t.length <= 98) return t;
  const cut = t.slice(0, 98);
  return cut.slice(0, Math.max(cut.lastIndexOf(" "), 60)).replace(/[,;:]$/, "") + "\\u2026";
}""")

# ---- selection: one branch per business, and a mix of types ----
rep("""    const items = raw
      .map((p) => shapePlace(p, at))
      .filter((p) => p.name && p.rating >= 4.2 && p.votes >= 80 && nbFits(g.key, p.type))
      .filter((p) => (p.id && seen.has(p.id) ? false : (seen.add(p.id), true)))
      .sort((a, b) => nbScore(b) - nbScore(a))
      .slice(0, g.take);
    for (const p of items) { delete p.id; delete p.type; }""",
    """    const ok = raw
      .map((p) => shapePlace(p, at))
      .filter((p) => p.name && p.rating >= 4.2 && p.votes >= 80 && nbFits(g.key, p.type))
      .filter((p) => !seen.has(nbName(p.name)));
    // one branch per business: the one a guest can walk to
    const byName = new Map();
    for (const p of ok) {
      const k = nbName(p.name);
      const had = byName.get(k);
      if (!had || (p.miles ?? 99) < (had.miles ?? 99)) byName.set(k, p);
    }
    const items = [];
    const perType = new Map();
    for (const p of [...byName.values()].sort((a, b) => nbScore(b) - nbScore(a))) {
      const used = perType.get(p.type) || 0;
      if (used >= 2) continue;            // never six steakhouses
      perType.set(p.type, used + 1);
      p.blurb = nbTrim(p.blurb);
      seen.add(nbName(p.name));
      items.push(p);
      if (items.length >= g.take) break;
    }
    for (const p of items) { delete p.id; delete p.type; }""")

rep("""  const cacheKey = `nearby/v2/${at.lat.toFixed(3)}_${at.lng.toFixed(3)}.json`;""",
    """  const cacheKey = `nearby/v3/${at.lat.toFixed(3)}_${at.lng.toFixed(3)}.json`;""")

P.write_text(s, encoding="utf-8", newline="\n")
print(f"worker patched ({len(s):,} bytes)")

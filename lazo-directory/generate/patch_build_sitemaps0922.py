"""patch_build_sitemaps0922.py - JC-LAZO-SEO-0922-001
Sitemaps by page tier instead of by position. Search Console reports indexing
per submitted sitemap, so with one undifferentiated 45k-URL shard series we
cannot see which kind of page Google accepts. Now:

  sitemap-hubs.xml        home, metros, categories, guides, cost, license, templates, styles
  sitemap-rich.xml        vendor pages with real content (gallery, bio, packages, reviews...)
  sitemap-venues-N.xml    wedding-venue pages (they carry hotels and nearby-venue data)
  sitemap-vendors-N.xml   the remaining vendor stubs, still indexable and still submitted
  sitemap-couples.xml     unchanged (served live by the worker)

The index lists them all. Old sitemap-N.xml shards are deleted from dist so
they drop out of the sync; the index no longer references them. Idempotent.

  python generate\\patch_build_sitemaps0922.py
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
bp = ROOT / "generate" / "build.py"; b = bp.read_text(encoding="utf-8")
if "SEO-0922-001" in b:
    raise SystemExit("already patched")

def rep(s, old, new, label):
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"{label}: anchor found {n}x: {old[:70]!r}")
    return s.replace(old, new)

# remember which vendor URLs are rich, at render time
b = rep(b, "_rich_count = [0]\n", "_rich_count = [0]\n_RICH_URLS = set()  # JC-LAZO-SEO-0922-001: rich vendor pages get their own sitemap\n", "rich set")
b = rep(b, "                urls.append(f\"{BASE_URL}/{mid}/{cat['slug']}/{v['slug']}/\")\n",
        "                urls.append(f\"{BASE_URL}/{mid}/{cat['slug']}/{v['slug']}/\")\n"
        "                if _rich:\n                    _RICH_URLS.add(f\"{BASE_URL}/{mid}/{cat['slug']}/{v['slug']}/\")\n", "rich record")

old_block = '''    SM_CHUNK = 45000
    sm_shards = [urls[i:i + SM_CHUNK] for i in range(0, len(urls), SM_CHUNK)]
    from datetime import date as _sm_date
    _sm_today = _sm_date.today().isoformat()
    # JC-LAZO-GONE-0903: each shard's index <lastmod> is the newest URL lastmod inside it,
    # not the build date. Google only trusts lastmod that means something.
    sm_shard_lastmod = []
    for sm_n, sm_chunk in enumerate(sm_shards, 1):
        sm = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        _newest = ""
        for u in sm_chunk:
            _lm = _stable_lastmod(u)
            if _lm > _newest:
                _newest = _lm
            sm.append(f"<url><loc>{html.escape(u)}</loc><lastmod>{_lm}</lastmod></url>")
        sm.append("</urlset>")
        (DIST / f"sitemap-{sm_n}.xml").write_text("\\n".join(sm), encoding="utf-8")
        sm_shard_lastmod.append(_newest or _sm_today)
    sm_idx = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm_idx += [f"<sitemap><loc>{BASE_URL}/sitemap-{n}.xml</loc><lastmod>{sm_shard_lastmod[n - 1]}</lastmod></sitemap>"
               for n in range(1, len(sm_shards) + 1)]
'''
new_block = '''    SM_CHUNK = 45000
    from datetime import date as _sm_date
    _sm_today = _sm_date.today().isoformat()
    # JC-LAZO-SEO-0922-001: one sitemap series per page tier, so Search Console
    # shows indexing per tier (hubs / rich vendors / venues / stubs).
    _metro_ids = set(BY_ID); _cat_slugs = set(BY_SLUG)
    def _tier(u):
        segs = [s for s in u[len(BASE_URL):].split("/") if s]
        if len(segs) == 3 and segs[0] in _metro_ids and segs[1] in _cat_slugs:
            if u in _RICH_URLS:
                return "rich"
            return "venues" if segs[1] == "wedding-venues" else "vendors"
        return "hubs"
    _tiers = {"hubs": [], "rich": [], "venues": [], "vendors": []}
    for u in urls:
        _tiers[_tier(u)].append(u)
    for _old in DIST.glob("sitemap-[0-9]*.xml"):
        _old.unlink()
    sm_files = []  # (filename, newest lastmod)
    # JC-LAZO-GONE-0903: each shard's index <lastmod> is the newest URL lastmod inside it,
    # not the build date. Google only trusts lastmod that means something.
    for _name, _list in _tiers.items():
        _shards = [_list[i:i + SM_CHUNK] for i in range(0, len(_list), SM_CHUNK)] or [[]]
        for sm_n, sm_chunk in enumerate(_shards, 1):
            if not sm_chunk:
                continue
            sm = ['<?xml version="1.0" encoding="UTF-8"?>',
                  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
            _newest = ""
            for u in sm_chunk:
                _lm = _stable_lastmod(u)
                if _lm > _newest:
                    _newest = _lm
                sm.append(f"<url><loc>{html.escape(u)}</loc><lastmod>{_lm}</lastmod></url>")
            sm.append("</urlset>")
            _fn = f"sitemap-{_name}.xml" if len(_shards) == 1 else f"sitemap-{_name}-{sm_n}.xml"
            (DIST / _fn).write_text("\\n".join(sm), encoding="utf-8")
            sm_files.append((_fn, _newest or _sm_today))
    print("[build] sitemaps: " + ", ".join(f"{k} {len(v):,}" for k, v in _tiers.items()) + f" -> {len(sm_files)} file(s)")
    sm_idx = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm_idx += [f"<sitemap><loc>{BASE_URL}/{_fn}</loc><lastmod>{_lm}</lastmod></sitemap>" for _fn, _lm in sm_files]
'''
b = rep(b, old_block, new_block, "sitemap block")
bp.write_text(b, encoding="utf-8", newline="\n")
print("build.py: tiered sitemaps")

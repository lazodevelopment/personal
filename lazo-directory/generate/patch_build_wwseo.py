"""patch_build_wwseo.py - JC-LAZO-WWSEO-0919-004
build.py: ship wedding-websites/ (hub + template demos) inside dist so the
nightly deploy carries them and their sitemap lastmod stays stable, put the
14 URLs in the sitemap, and point the sitemap index at /sitemap-couples.xml
(served live by the worker). Refuses to run twice.
  python generate\\patch_build_wwseo.py
"""
from pathlib import Path

P = Path(__file__).resolve().parent / "build.py"
s = P.read_text(encoding="utf-8")
if "JC-LAZO-WWSEO-0919-004" in s:
    raise SystemExit("already applied")


def rep(old, new):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"anchor {old[:70]!r}: found {n}, wanted 1")
    s = s.replace(old, new)


rep('    urls.append(f"{BASE_URL}/guests/")\n',
    '    urls.append(f"{BASE_URL}/guests/")\n'
    '\n'
    '    # JC-LAZO-WWSEO-0919-004: the wedding-website hub and every template demo are\n'
    '    # copied from wedding-websites/ (the source of truth) into dist, so the nightly\n'
    '    # upload ships them and lastmod is hashed off a real file. Helper files\n'
    '    # (_base.html, *.py, themes.json) never leave the source folder.\n'
    '    _ww_src = ROOT / "wedding-websites"\n'
    '    if (_ww_src / "index.html").exists():\n'
    '        import shutil as _wws\n'
    '        _ww_dst = DIST / "wedding-websites"\n'
    '        _ww_dst.mkdir(exist_ok=True)\n'
    '        _wws.copy2(_ww_src / "index.html", _ww_dst / "index.html")\n'
    '        urls.append(f"{BASE_URL}/wedding-websites/")\n'
    '        for _wd in sorted(p for p in _ww_src.iterdir()\n'
    '                          if p.is_dir() and not p.name.startswith("_") and (p / "index.html").exists()):\n'
    '            (_ww_dst / _wd.name).mkdir(exist_ok=True)\n'
    '            _wws.copy2(_wd / "index.html", _ww_dst / _wd.name / "index.html")\n'
    '            urls.append(f"{BASE_URL}/wedding-websites/{_wd.name}/")\n')

rep('    sm_idx.append("</sitemapindex>")\n',
    '    # JC-LAZO-WWSEO-0919-004: public couple sites, listed live by the worker\n'
    '    sm_idx.append(f"<sitemap><loc>{BASE_URL}/sitemap-couples.xml</loc></sitemap>")\n'
    '    sm_idx.append("</sitemapindex>")\n')

P.write_text(s, encoding="utf-8", newline="\n")
print("generate/build.py patched")

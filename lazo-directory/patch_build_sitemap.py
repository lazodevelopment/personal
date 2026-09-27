#!/usr/bin/env python3
r"""
patch_build_sitemap.py - permanent sharded-sitemap patch for build.py
Replaces the single-file sitemap writer (lines ~299-303) with a sharded
writer: sitemap-N.xml files of <=45,000 URLs + sitemap.xml as a sitemapindex.
Run from C:\Users\kurvh\lazo-directory:
    python patch_build_sitemap.py
Idempotent; asserts the exact old block before changing anything.
"""
import pathlib, sys

BP = pathlib.Path(__file__).resolve().parent / "generate" / "build.py"
src = BP.read_text(encoding="utf-8")
lines = src.splitlines()

if "SM_CHUNK" in src:
    print("Already patched - nothing to do.")
    sys.exit(0)

# locate anchor
try:
    a = next(i for i, l in enumerate(lines) if l.strip() == "# sitemap + robots")
except StopIteration:
    sys.exit("!! anchor '# sitemap + robots' not found - aborting, nothing changed")

expect = [
    "sm = ['<?xml",          # 299
    "'<urlset",              # 300
    "sm += [f\"<url><loc>",  # 301
    "sm.append(\"</urlset>\")",  # 302
    "(DIST / \"sitemap.xml\").write_text",  # 303
]
block = lines[a+1:a+6]
for got, want in zip(block, expect):
    if want not in got:
        sys.exit(f"!! unexpected line, aborting (nothing changed):\n  wanted ~{want}\n  found  {got}")

new_block = [
    '    # sitemap + robots (sharded: 50k-URL protocol cap; sitemap.xml is an index)',
    '    SM_CHUNK = 45000',
    '    sm_shards = [urls[i:i + SM_CHUNK] for i in range(0, len(urls), SM_CHUNK)]',
    '    for sm_n, sm_chunk in enumerate(sm_shards, 1):',
    "        sm = ['<?xml version=\"1.0\" encoding=\"UTF-8\"?>',",
    "              '<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">']",
    '        sm += [f"<url><loc>{html.escape(u)}</loc></url>" for u in sm_chunk]',
    '        sm.append("</urlset>")',
    '        (DIST / f"sitemap-{sm_n}.xml").write_text("\\n".join(sm), encoding="utf-8")',
    '    from datetime import date as _sm_date',
    '    _sm_today = _sm_date.today().isoformat()',
    "    sm_idx = ['<?xml version=\"1.0\" encoding=\"UTF-8\"?>',",
    "              '<sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">']",
    '    sm_idx += [f"<sitemap><loc>{BASE_URL}/sitemap-{n}.xml</loc><lastmod>{_sm_today}</lastmod></sitemap>"',
    '               for n in range(1, len(sm_shards) + 1)]',
    '    sm_idx.append("</sitemapindex>")',
    '    (DIST / "sitemap.xml").write_text("\\n".join(sm_idx), encoding="utf-8")',
]

out = lines[:a] + new_block + lines[a+6:]
BP.write_text("\n".join(out) + "\n", encoding="utf-8")  # LF, no BOM
print(f"Patched {BP}")
print("Old 6-line block replaced with sharded writer.")
import py_compile
py_compile.compile(str(BP), doraise=True)
print("py_compile: build.py syntax OK")

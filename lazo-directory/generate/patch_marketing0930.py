"""patch_marketing0930.py - JC-LAZO-MKT-0930
Site-wide polish from the 2026-09-30 marketing audit. Idempotent; every edit
is a literal find/replace that is skipped once applied.
  home.html       garbled check mark (content:"¹3" -> "\\2713"); grey "them"
                  column now readable; JSON-LD operatingSystem is honest
                  (Android is still in review)
  _features.html  "Her side, his side" -> "Your side, their side"; platform
                  line matches what is actually shipping
  pages/*.html    hardcoded "88,000+ vendor pages across 45/58 metros" ->
                  the live vendor_total_display / metro_count the renderers
                  already pass in
  base.html       og:url and twitter:image so shares carry the right link
                  and picture
  lazo.css        .eyebrow uses gold-ink (readable on cream), not gold
  _footer.html    duplicate "Why Lazo" link -> the two comparison pages
  worker          HSTS, nosniff, referrer-policy, permissions-policy on every
                  static response
  dist/index.html the three home fixes applied live (nightly build re-renders it)
  python generate\\patch_marketing0930.py
Then: python deploy\\render_pages.py; python deploy\\upload_r2.py --prefix index.html ...
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "generate" / "templates"


def edit(path, pairs, regex=False):
    s = path.read_text(encoding="utf-8")
    orig = s
    for old, new in pairs:
        if new in s:
            continue
        if regex:
            s2 = re.sub(old, new, s)
            if s2 == s:
                raise SystemExit(f"{path.relative_to(ROOT)}: regex not found: {old[:60]}")
            s = s2
        else:
            if old not in s:
                raise SystemExit(f"{path.relative_to(ROOT)}: anchor not found: {old[:60]}")
            s = s.replace(old, new)
    if s != orig:
        path.write_text(s, encoding="utf-8", newline="\n")
        print(f"  patched {path.relative_to(ROOT)}")
    else:
        print(f"  already  {path.relative_to(ROOT)}")


HOME = [
    ('content:"¹3"', 'content:"\\2713"'),
    (".stance .them h3,.stance .them p{color:#9A8FA1}", ".stance .them h3,.stance .them p{color:#786C83}"),
    ('"operatingSystem":"Web, iOS, Android"', '"operatingSystem":"iOS, Web"'),
]
edit(T / "home.html", HOME)
edit(ROOT / "dist" / "index.html", HOME)

edit(T / "_features.html", [
    ("Her side, his side, the front row", "Your side, their side, the front row"),
    ("iOS, Android and the web.", "On iPhone and the web today; Android is in review with Google Play."),
])

# Comparison pages: the numbers come from the build, never from a template.
for p in sorted((T / "pages").glob("*.html")):
    s = p.read_text(encoding="utf-8")
    if "88,000+" not in s and not re.search(r"\b(45|58) metros", s):
        continue
    s = s.replace("88,000+", "{{ vendor_total_display|default('70,000+') }}")
    s = re.sub(r"\b(45|58) metros", "{{ metro_count|default(45) }} metros", s)
    p.write_text(s, encoding="utf-8", newline="\n")
    print(f"  patched {p.relative_to(ROOT)} (live counts)")

edit(T / "base.html", [
    ('<meta property="og:image" content="{% block ogimage %}{{ base }}/assets/photos/hero-3.jpg{% endblock %}">\n<meta name="twitter:card" content="summary_large_image">',
     '<meta property="og:image" content="{% block ogimage %}{{ base }}/assets/photos/hero-3.jpg{% endblock %}">\n'
     '<meta property="og:url" content="{{ self.canonical() }}">\n'
     '<meta name="twitter:card" content="summary_large_image">\n'
     '<meta name="twitter:title" content="{{ self.title() }}">\n'
     '<meta name="twitter:description" content="{{ self.desc() }}">\n'
     '<meta name="twitter:image" content="{{ self.ogimage() }}">'),
])
# vendor.html already carries its own og:url; base's would duplicate it
edit(T / "vendor.html", [
    ('<meta property="og:url" content="{{ base }}/{{ metro.id }}/{{ cat.slug }}/{{ v.slug }}/">\n', ""),
])

edit(ROOT / "generate" / "static" / "lazo.css", [
    (".eyebrow{letter-spacing:.18em;text-transform:uppercase;font-size:11.5px;color:var(--gold);",
     ".eyebrow{letter-spacing:.18em;text-transform:uppercase;font-size:11.5px;color:var(--gold-ink);"),
])

edit(T / "_footer.html", [
    ('          <a href="/why-lazo/">How our rankings work</a>\n',
     '          <a href="/the-knot-alternative/">Lazo vs The Knot</a>\n'
     '          <a href="/zola-alternative/">Lazo vs Zola</a>\n'),
])

edit(ROOT / "worker" / "src" / "index.js", [
    ('      "cache-control": cache,\n      "access-control-allow-origin": "*",\n      "x-lazo": "tied-together",\n    }});\n    // The home page follows the visitor',
     '      "cache-control": cache,\n      "access-control-allow-origin": "*",\n'
     '      // JC-LAZO-MKT-0930: the headers every scanner asks for on a public site\n'
     '      "strict-transport-security": "max-age=31536000; includeSubDomains",\n'
     '      "x-content-type-options": "nosniff",\n'
     '      "referrer-policy": "strict-origin-when-cross-origin",\n'
     '      "permissions-policy": "camera=(), microphone=(), payment=()",\n'
     '      "x-lazo": "tied-together",\n    }});\n    // The home page follows the visitor'),
])
print("done")

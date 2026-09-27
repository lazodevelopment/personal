#!/usr/bin/env python3
"""
gen_blog.py — Atavia Weddings /blog/ (The Atavia Journal).

Reads _src/posts/*.md (front-matter + markdown), renders:
  /blog/            hub
  /blog/<slug>      one page per post with status: publish
  /blog/rss.xml     feed
  sitemap-blog.xml  (picked up automatically by build.py's sitemap index)

Front-matter keys: title, slug, date (YYYY-MM-DD), description, hero,
seed, keywords, source, status (only 'publish' renders).

Run:  python _src/gen_blog.py   then   python _src/build.py
"""
import sys, re, json, pathlib, html as H

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import build as B

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS = ROOT / "_src" / "posts"
OUT = ROOT / "blog"
BASE = B.BASE

# ---------------------------------------------------------------- front-matter
def parse_post(path):
    raw = path.read_text(encoding="utf-8").lstrip("\ufeff")
    m = re.match(r"---\s*\n(.*?)\n---\s*\n?(.*)$", raw, re.S)
    if not m:
        return None
    meta, body = {}, m.group(2)
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.split("#")[0].strip() if k.strip() == "status" else v.strip()
        if v.startswith(('"', "[")):
            try:
                v = json.loads(v)
            except Exception:
                pass
        meta[k] = v
    meta["_body"] = body
    return meta

# ---------------------------------------------------------------- markdown -> html
INLINE = [
    (re.compile(r"!\[([^\]]*)\]\(([^)\s]+)[^)]*\)"),
     r'''<img src="\2" alt="\1" loading="lazy" decoding="async" style="max-width:100%;border-radius:3px;margin:8px 0" onerror="this.style.display='none'">'''),
    (re.compile(r"\[([^\]]+)\]\(([^)\s]+)[^)]*\)"), r'<a href="\2">\1</a>'),
    (re.compile(r"\*\*([^*]+)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)"), r"<em>\1</em>"),
    (re.compile(r"`([^`]+)`"), r"<code>\1</code>"),
]

def inline(s):
    for rx, rep in INLINE:
        s = rx.sub(rep, s)
    return s

def md_to_sections(md, title):
    """Return list of (heading_html_or_None, [block_html,...]) grouped by h2."""
    lines = md.replace("\r\n", "\n").split("\n")
    blocks, buf, mode = [], [], None  # mode: p|ul|ol|quote|table

    def flush():
        nonlocal buf, mode
        if not buf:
            mode = None; return
        if mode == "ul":
            blocks.append("<ul>%s</ul>" % "".join("<li>%s</li>" % b for b in buf))
        elif mode == "ol":
            blocks.append("<ol>%s</ol>" % "".join("<li>%s</li>" % b for b in buf))
        elif mode == "quote":
            blocks.append("<blockquote><p>%s</p></blockquote>" % "<br>".join(buf))
        elif mode == "table":
            rows = [r for r in buf if not re.match(r"^[\s|:-]+$", r)]
            trs = []
            for i, r in enumerate(rows):
                cells = [c.strip() for c in r.strip().strip("|").split("|")]
                tag = "th" if i == 0 else "td"
                trs.append("<tr>%s</tr>" % "".join('<%s style="border:1px solid var(--line);padding:10px 14px;text-align:left">%s</%s>' % (tag, c, tag) for c in cells))
            blocks.append('<div style="overflow-x:auto"><table style="width:100%%;border-collapse:collapse;margin:12px 0;color:var(--ivory-dim);font-size:15px">%s</table></div>' % "".join(trs))
        else:
            blocks.append("<p>%s</p>" % " ".join(buf))
        buf, mode = [], None

    first_h1_dropped = False
    for ln in lines:
        raw = ln.rstrip()
        e = inline(H.escape(raw, quote=False))
        if re.match(r"^#{1,6}\s", raw):
            flush()
            level = len(raw) - len(raw.lstrip("#"))
            text = inline(H.escape(raw.lstrip("#").strip(), quote=False))
            if level == 1 and not first_h1_dropped:
                first_h1_dropped = True
                if _similar(raw.lstrip("#").strip(), title):
                    continue  # template already shows the title
                level = 2
            blocks.append("<h%d>%s</h%d>" % (min(max(level, 2), 4), text, min(max(level, 2), 4)))
        elif re.match(r"^(-{3,}|\*{3,})\s*$", raw):
            flush(); blocks.append("<hr>")
        elif re.match(r"^\s*[-*]\s+", raw):
            if mode != "ul": flush(); mode = "ul"
            buf.append(inline(H.escape(re.sub(r"^\s*[-*]\s+", "", raw), quote=False)))
        elif re.match(r"^\s*\d+\.\s+", raw):
            if mode != "ol": flush(); mode = "ol"
            buf.append(inline(H.escape(re.sub(r"^\s*\d+\.\s+", "", raw), quote=False)))
        elif raw.startswith(">"):
            if mode != "quote": flush(); mode = "quote"
            buf.append(inline(H.escape(raw.lstrip("> ").strip(), quote=False)))
        elif raw.strip().startswith("|") and raw.strip().endswith("|"):
            if mode != "table": flush(); mode = "table"
            buf.append(e)
        elif not raw.strip():
            flush()
        else:
            if mode not in (None, "p"): flush()
            mode = "p"; buf.append(e)
    flush()

    # group into sections at h2 boundaries
    secs, cur_head, cur = [], None, []
    for b in blocks:
        if b.startswith("<h2>"):
            if cur or cur_head: secs.append((cur_head, cur))
            cur_head, cur = b, []
        else:
            cur.append(b)
    if cur or cur_head: secs.append((cur_head, cur))
    return secs

def _similar(a, b):
    n = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
    return n(a)[:40] == n(b)[:40]

# ---------------------------------------------------------------- rendering
def h(s): return H.escape(str(s or ""), quote=True)

HERO_IMG = ("https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/"
            "o/DSC_4772.jpg?alt=media&token=5182d7b9-096f-4902-a8b6-7ef2cd2e865a")

def pretty_date(d):
    try:
        y, m, dd = d.split("-")
        months = ["January","February","March","April","May","June","July",
                  "August","September","October","November","December"]
        return "%s %d, %s" % (months[int(m)-1], int(dd), y)
    except Exception:
        return d

def post_body(p, others):
    secs = md_to_sections(p["_body"], p.get("title", ""))
    parts = []
    for head, blocks in secs:
        parts.append('<div class="guide-sec">%s%s</div>' % (head or "", "".join(blocks)))
    more = "".join('<p style="text-align:center;margin-bottom:10px"><a href="/blog/%s" '
                   'style="color:var(--copper)">%s</a></p>' % (o["slug"], h(o["title"]))
                   for o in others[:3])
    return (
        '<section class="page-hero page-hero--short"><div class="page-hero__bg" aria-hidden="true">'
        '<img src="%s" alt=""></div><span class="page-hero__watermark" aria-hidden="true">A</span>'
        '<div class="wrap"><nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a> <span>/</span> '
        '<a href="/blog/">Journal</a> <span>/</span> <span>%s</span></nav>'
        '<div class="eyebrow center rules reveal">The Atavia Journal</div>'
        '<h1 class="page-hero__title reveal d1">%s</h1>'
        '<p class="page-hero__sub reveal d2">%s</p>'
        '<p class="reveal d3" style="color:var(--copper);font-size:13px;letter-spacing:.2em;margin-top:14px">%s</p>'
        "</div></section>"
        '<section class="sec"><div class="wrap guide-body">%s'
        '<div class="guide-cta"><h3>Planning your wedding?</h3>'
        "<p>Atavia films and photographs weddings nationwide &mdash; local teams, no travel fees, "
        "and a <strong>$500 deposit</strong> reserves your date.</p>"
        '<a class="btn btn--solid" href="/book/">Reserve Your Date</a></div>'
        '<div class="guide-more"><h3>Keep Reading</h3>%s'
        '<p style="text-align:center;margin-top:18px"><a href="/blog/" style="color:var(--copper)">'
        "All journal entries &rarr;</a> &nbsp;&middot;&nbsp; "
        '<a href="/guides/" style="color:var(--copper)">Wedding guides &rarr;</a></p></div>'
        "</div></section>"
    ) % (HERO_IMG.replace("&", "&amp;"), h(p["title"]), h(p["title"]),
         h(p.get("description", "")), pretty_date(p.get("date", "")), "".join(parts), more)

def post_schema(p, canon):
    art = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": p.get("title", ""), "description": p.get("description", ""),
        "datePublished": p.get("date", ""), "dateModified": p.get("date", ""),
        "mainEntityOfPage": canon,
        "author": {"@type": "Organization", "name": "Atavia Weddings", "url": BASE + "/"},
        "publisher": {"@type": "Organization", "name": "Atavia Weddings",
                      "logo": {"@type": "ImageObject", "url": B.CTA if hasattr(B, "CTA") else HERO_IMG}},
    }
    if p.get("keywords"): art["keywords"] = ", ".join(p["keywords"]) if isinstance(p["keywords"], list) else str(p["keywords"])
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Journal", "item": BASE + "/blog/"},
        {"@type": "ListItem", "position": 3, "name": p.get("title", ""), "item": canon},
    ]}
    return ('<script type="application/ld+json">%s</script>'
            '<script type="application/ld+json">%s</script>'
            % (json.dumps(art), json.dumps(crumbs)))

def hub_body(posts):
    cards = "".join(
        '<a class="venue-card" style="display:block;text-align:left;margin-bottom:18px;text-decoration:none" href="/blog/%s">'
        '<div class="venue-card__label">%s</div>'
        '<div style="font-family:var(--display);font-size:clamp(20px,2.6vw,26px);color:var(--ivory-bright);line-height:1.35;margin:6px 0 10px">%s</div>'
        '<p style="color:var(--ivory-dim);font-size:15px;line-height:1.8;margin:0">%s</p></a>'
        % (p["slug"], pretty_date(p.get("date", "")), h(p["title"]), h(p.get("description", "")))
        for p in posts)
    return (
        '<section class="page-hero page-hero--short"><div class="page-hero__bg" aria-hidden="true">'
        '<img src="%s" alt=""></div><span class="page-hero__watermark" aria-hidden="true">A</span>'
        '<div class="wrap"><nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a> <span>/</span> <span>Journal</span></nav>'
        '<div class="eyebrow center rules reveal">The Atavia Journal</div>'
        '<h1 class="page-hero__title reveal d1">Stories &amp; <em>Advice</em></h1>'
        '<p class="page-hero__sub reveal d2">Planning wisdom from sixteen years behind the lens &mdash; '
        "%d entries and counting.</p></div></section>"
        '<section class="sec"><div class="wrap" style="max-width:820px">%s</div></section>'
    ) % (HERO_IMG.replace("&", "&amp;"), len(posts), cards)

def rss(posts):
    items = "".join(
        "<item><title>%s</title><link>%s/blog/%s</link><guid>%s/blog/%s</guid>"
        "<pubDate>%sT09:00:00Z</pubDate><description>%s</description></item>"
        % (h(p["title"]), BASE, p["slug"], BASE, p["slug"], p.get("date", ""),
           h(p.get("description", ""))) for p in posts)
    return ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
            "<title>The Atavia Journal</title><link>%s/blog/</link>"
            "<description>Wedding photography and film advice from Atavia Weddings.</description>%s"
            "</channel></rss>" % (BASE, items))

# ---------------------------------------------------------------- main
def main():
    OUT.mkdir(exist_ok=True)
    files = sorted(POSTS.glob("*.md")) if POSTS.exists() else []
    posts, skipped = [], 0
    for f in files:
        p = parse_post(f)
        if not p or str(p.get("status", "")).strip() != "publish":
            skipped += 1; continue
        if not p.get("slug"):
            p["slug"] = re.sub(r"[^a-z0-9-]", "-", f.stem.lower())
        posts.append(p)
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)

    urls = [("blog/", "0.7")]
    for i, p in enumerate(posts):
        canon = "%s/blog/%s" % (BASE, p["slug"])
        others = [x for x in posts if x is not p]
        html_page = B.render_page(
            "%s | The Atavia Journal" % p["title"],
            (p.get("description") or p["title"])[:158],
            canon, post_body(p, others), post_schema(p, canon), nav_key="blog")
        (OUT / ("%s.html" % p["slug"])).write_text(html_page, encoding="utf-8")
        urls.append(("blog/%s" % p["slug"], "0.6"))

    hub = B.render_page(
        "The Atavia Journal | Wedding Advice & Stories",
        "Wedding planning advice, photography and film insight from the Atavia Weddings team.",
        BASE + "/blog/", hub_body(posts), "", nav_key="blog")
    (OUT / "index.html").write_text(hub, encoding="utf-8")
    (OUT / "rss.xml").write_text(rss(posts), encoding="utf-8")

    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, pr in urls:
        xml.append("<url><loc>%s/%s</loc><priority>%s</priority></url>" % (BASE, u, pr))
    xml.append("</urlset>")
    (ROOT / "sitemap-blog.xml").write_text("\n".join(xml), encoding="utf-8")

    print("blog: %d posts rendered, %d skipped (not status: publish)" % (len(posts), skipped))
    print("wrote /blog/, rss.xml, sitemap-blog.xml — now run: python _src/build.py")

if __name__ == "__main__":
    main()

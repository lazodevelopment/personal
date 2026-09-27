#!/usr/bin/env python3
"""
gen_blog.py — Elizabeth Scott /blog/ (The Journal).

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
    raw = path.read_text(encoding="utf-8").lstrip("﻿")
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

HERO_IMG = ""

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
        parts.append((head or "") + "".join(blocks))
    more = "".join('<p style="text-align:center;margin-bottom:8px"><a href="/blog/%s" style="color:var(--champagne)">%s</a></p>' % (o["slug"], h(o["title"])) for o in others[:3])
    return (
        '<header class="hero" style="min-height:44vh"><div class="hero-bg"><img data-img="hero2" alt=""></div>'
        '<div class="wrap"><span class="hero-badge fade-up d1">The Journal &middot; %s</span>'
        '<h1 class="fade-up d2" style="font-family:var(--serif);font-size:clamp(30px,4.4vw,48px)">%s</h1>'
        '<p class="fade-up d3" style="color:var(--mist);max-width:640px;margin:14px auto 0">%s</p></div></header>'
        '<section class="section"><div class="wrap"><div class="post-body">%s'
        '<div class="glass" style="padding:28px;border-radius:var(--radius);text-align:center;margin-top:36px">'
        '<h3 style="font-family:var(--serif);color:var(--ice)">Planning your wedding?</h3>'
        '<p style="margin:8px 0 16px">Elizabeth Scott photographs and films weddings nationwide &mdash; travel included, dates limited.</p>'
        '<a class="btn btn-gold" href="/book/">Check Your Date</a></div>'
        '<div style="margin-top:34px"><h3 style="font-family:var(--serif);color:var(--ice);text-align:center;margin-bottom:14px">Keep Reading</h3>%s'
        '<p style="text-align:center;margin-top:14px"><a href="/blog/" style="color:var(--champagne)">All entries &rarr;</a></p></div>'
        '</div></div></section>'
    ) % (pretty_date(p.get("date", "")), h(p["title"]), h(p.get("description", "")), "".join(parts), more)

def post_schema(p, canon):
    art = {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": p.get("title", ""), "description": p.get("description", ""),
        "datePublished": p.get("date", ""), "dateModified": p.get("date", ""),
        "mainEntityOfPage": canon,
        "author": {"@type": "Organization", "name": "Elizabeth Scott", "url": BASE + "/"},
        "publisher": {"@type": "Organization", "name": "Elizabeth Scott",
                      "logo": {"@type": "ImageObject", "url": BASE + "/favicon/icon-512.png"}},
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
        '<a class="post-card glass" href="/blog/%s"><time>%s</time><h3>%s</h3><p>%s</p></a>'
        % (p["slug"], pretty_date(p.get("date", "")), h(p["title"]), h(p.get("description", "")))
        for p in posts)
    return (
        '<header class="hero" style="min-height:44vh"><div class="hero-bg"><img data-img="hero2" alt=""></div>'
        '<div class="wrap"><span class="hero-badge fade-up d1">The Journal</span>'
        '<h1 class="fade-up d2" style="font-family:var(--serif);font-size:clamp(32px,4.6vw,52px)">Notes, <em>signed</em></h1>'
        '<p class="fade-up d3" style="color:var(--mist);max-width:620px;margin:14px auto 0">Planning wisdom from a studio that shoots every week &mdash; %d entries and counting.</p></div></header>'
        '<section class="section"><div class="wrap" style="max-width:820px">%s</div></section>'
    ) % (len(posts), cards)

def rss(posts):
    items = "".join(
        "<item><title>%s</title><link>%s/blog/%s</link><guid>%s/blog/%s</guid>"
        "<pubDate>%sT09:00:00Z</pubDate><description>%s</description></item>"
        % (h(p["title"]), BASE, p["slug"], BASE, p["slug"], p.get("date", ""),
           h(p.get("description", ""))) for p in posts)
    return ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
            "<title>The Journal</title><link>%s/blog/</link>"
            "<description>Wedding photography and film advice from Elizabeth Scott.</description>%s"
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
            "%s | Elizabeth Scott" % p["title"],
            (p.get("description") or p["title"])[:158],
            canon, post_body(p, others), post_schema(p, canon), nav_key="blog")
        (OUT / ("%s.html" % p["slug"])).write_text(html_page, encoding="utf-8")
        urls.append(("blog/%s" % p["slug"], "0.6"))

    hub = B.render_page(
        "Wedding Planning Journal &amp; Advice | Elizabeth Scott",
        "Wedding planning advice, photography and film insight from the Elizabeth Scott team.",
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

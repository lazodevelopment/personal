#!/usr/bin/env python3
"""gen_gallery.py — Elizabeth Scott full /portfolio gallery (all ESCOTT_WED frames).
Regenerates _src/pages/portfolio.html. Bump COUNT when new frames upload.
Run: python _src/gen_gallery.py && python _src/build.py"""
import pathlib, urllib.parse

COUNT = 463
EAGER = 24
FB = "https://firebasestorage.googleapis.com/v0/b/danbren-media.firebasestorage.app/o/"

def ws(name, params):
    return ("https://images.weserv.nl/?url="
            + urllib.parse.quote(FB + urllib.parse.quote(name, safe="") + "?alt=media", safe="")
            + params).replace("&", "&amp;")

def main():
    cells = []
    for n in range(1, COUNT + 1):
        name = "ESCOTT_WED (%d).jpg" % n
        thumb = ws(name, "&w=440&q=78&output=webp")
        full = ws(name, "&w=1920&q=84&output=webp")
        loading = "eager" if n <= EAGER else "lazy"
        cells.append(
            '<div class="es-masonry__item" data-glb="%s" data-glb-full="%s">'
            '<img src="%s" alt="Elizabeth Scott wedding photograph %d" loading="%s" decoding="async"></div>'
            % (thumb, full, thumb, n, loading))

    body = '''<header class="hero" style="min-height:44vh">
  <div class="hero-bg"><img data-img="hero4" alt=""></div>
  <div class="wrap">
    <span class="hero-badge fade-up d1">Selected Work &middot; %d Frames</span>
    <h1 class="fade-up d2" style="font-family:var(--serif);font-size:clamp(32px,4.6vw,52px)">Moments we&rsquo;ve <em>signed</em></h1>
    <p class="fade-up d3" style="color:var(--mist);max-width:640px;margin:14px auto 0">Real weddings, unstaged. Tap any frame to view it full-screen &mdash; and ask us for complete galleries from venues like yours.</p>
  </div>
</header>
<section class="section" style="padding-top:54px"><div class="wrap" style="max-width:1180px">
  <div class="es-masonry">%s</div>
  <p style="text-align:center;margin-top:40px">
    <a class="btn btn-solid" href="/contact">Check Your Date</a>
    &nbsp;&nbsp;<a class="btn" href="/films" style="margin-left:8px">See Our Films</a></p>
</div></section>
<div class="glb" id="esLightbox" role="dialog" aria-modal="true" aria-label="Photo viewer">
  <button class="glb__close" aria-label="Close">&times;</button>
  <button class="glb__nav glb__prev" aria-label="Previous">&larr;</button>
  <img class="glb__img" src="" alt="Elizabeth Scott wedding photograph">
  <button class="glb__nav glb__next" aria-label="Next">&rarr;</button>
  <div class="glb__count"></div>
</div>
''' % (COUNT, "".join(cells))

    pathlib.Path(__file__).resolve().parent.joinpath("pages", "portfolio.html").write_text(body, encoding="utf-8")
    print("portfolio.html: %d frames (%d eager) + lightbox" % (COUNT, EAGER))

if __name__ == "__main__":
    main()

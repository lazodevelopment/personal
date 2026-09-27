# Gallery generator — thumbnails + page background images served through the
# free images.weserv.nl resizing/caching proxy (Option A).
# Each <img> falls back to the direct bucket original if the proxy fails.
from urllib.parse import quote

COUNT = 349

def weserv(src_url, w, q):
    return "https://images.weserv.nl/?url=%s&w=%d&q=%d&output=webp" % (quote(src_url, safe=""), w, q)

def esc(u):
    return u.replace("&", "&amp;")

# --- gallery images (public GCS bucket) ---
def src_raw(n):
    return "https://storage.googleapis.com/atavia_bucket/Site Files/gallery-01 (" + str(n) + ").jpg"
def direct(n):
    return "https://storage.googleapis.com/atavia_bucket/Site%20Files/gallery-01%20(" + str(n) + ").jpg"

# --- page background images (Firebase) ---
HERO_SRC = "https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/o/DSC_4772.jpg?alt=media&token=5182d7b9-096f-4902-a8b6-7ef2cd2e865a"
CTA_SRC  = "https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/o/atavia16.png?alt=media&token=4fff66fd-0144-474e-8fc1-d4ad8b6ab499"

ZOOM = ('<span class="zoom" aria-hidden="true"><svg width="15" height="15" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="7"/>'
        '<path d="M21 21l-4.5-4.5M11 8v6M8 11h6"/></svg></span>')

tiles = []
for n in range(1, COUNT + 1):
    thumb = weserv(src_raw(n), 800, 80)     # grid thumbnail (~webp, small)
    full  = weserv(src_raw(n), 1920, 82)    # lightbox large view
    tiles.append(
        '      <div class="masonry__item" data-glb="%s" data-glb-full="%s" role="button" tabindex="0" aria-label="Open photo">\n'
        '        <img src="%s" alt="Atavia wedding photograph" loading="lazy" decoding="async" '
        'onerror="this.onerror=null;this.src=\'%s\'">\n'
        '        %s\n'
        '      </div>' % (esc(thumb), esc(full), esc(thumb), esc(direct(n)), ZOOM))
tiles_html = "\n".join(tiles)

hero_img = esc(weserv(HERO_SRC, 1920, 80))
cta_img  = esc(weserv(CTA_SRC, 1600, 80))

body = '''<!-- ===== PAGE HERO ===== -->
<section class="page-hero">
  <div class="page-hero__bg" aria-hidden="true">
    <img src="%s" alt="" onerror="this.onerror=null;this.src='%s'">
  </div>
  <span class="page-hero__watermark" aria-hidden="true">A</span>
  <div class="wrap">
    <div class="eyebrow center rules reveal">Selected Work</div>
    <h1 class="page-hero__title reveal d1">The <em>Gallery</em></h1>
    <p class="page-hero__sub reveal d2">Stills with feeling &mdash; light, gesture, and the quiet space between vows, toasts, and the first dance.</p>
  </div>
</section>

<!-- ===== MASONRY ===== -->
<section class="sec sec--tight">
  <div class="wrap">
    <div class="masonry reveal">
%s
    </div>
    <div style="text-align:center;margin-top:52px" class="reveal">
      <a href="/book/" class="btn btn--copper">Reserve Your Date <span class="arr">&#8599;</span></a>
    </div>
  </div>
</section>

<!-- ===== CTA ===== -->
<section class="cta-band cta-band--img" aria-label="Book Atavia Weddings">
  <img src="%s" alt="" loading="lazy" onerror="this.onerror=null;this.src='%s'">
  <div class="wrap reveal">
    <span class="eyebrow center rules">Your Day, Beautifully Captured</span>
    <h2 class="cta-band__title" style="font-size:clamp(30px,4.6vw,58px);margin-top:20px">Let's create<br><em>something timeless.</em></h2>
    <a href="/book/" class="btn btn--copper" style="margin-top:26px">Book Now <span class="arr">&#8599;</span></a>
  </div>
</section>

<!-- gallery lightbox -->
<div class="glb" id="galleryLightbox" role="dialog" aria-modal="true" aria-label="Photo viewer">
  <button class="glb__close" aria-label="Close">&times;</button>
  <button class="glb__nav glb__prev" aria-label="Previous photo">&larr;</button>
  <img class="glb__img" src="" alt="Atavia wedding photograph">
  <button class="glb__nav glb__next" aria-label="Next photo">&rarr;</button>
  <div class="glb__count"></div>
</div>

<script>
document.querySelectorAll('.masonry__item[role=button]').forEach(function(el){
  el.addEventListener('keydown',function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); el.click(); } });
});
</script>
''' % (hero_img, esc(HERO_SRC), tiles_html, cta_img, esc(CTA_SRC))

import os
out = os.path.join(os.path.dirname(__file__), "pages", "gallery.html")
open(out, "w").write(body)
print("wrote gallery.html — %d images via weserv proxy" % COUNT)

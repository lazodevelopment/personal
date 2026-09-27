#!/usr/bin/env python3
"""gallery.py - shared access to the Elizabeth Scott frame pool.

The portfolio is ESCOTT_WED (1..463).jpg in the danbren-media Firebase bucket,
served through the images.weserv.nl resizing proxy. This module centralises that
URL construction so the pattern lives in one place instead of being rebuilt by
every generator, and hands out deterministic per-page selections.

Deterministic matters: the same city must get the same frames on every rebuild,
or every deploy churns 302 pages of image URLs for no reason.
"""
import hashlib, urllib.parse

BUCKET = "danbren-media.firebasestorage.app"
PREFIX = "ESCOTT_WED"
COUNT = 463                       # frames in the pool; 463 is prime - see pick()

THUMB = dict(w=440, q=78)
CARD = dict(w=760, q=80)
FULL = dict(w=1920, q=84)


def frame_url(n, w=760, q=80):
    """weserv-proxied WebP URL for frame n."""
    # Firebase /o/ takes an ALREADY percent-encoded object name, and weserv then
    # encodes the whole URL again - hence the %2520 / %2528 double-encoding seen
    # on the live portfolio. Encoding only once yields 404s on every frame.
    obj = urllib.parse.quote("%s (%d).jpg" % (PREFIX, n), safe="")
    fb = ("https://firebasestorage.googleapis.com/v0/b/%s/o/%s?alt=media" % (BUCKET, obj))
    return ("https://images.weserv.nl/?url=%s&amp;w=%d&amp;q=%d&amp;output=webp"
            % (urllib.parse.quote(fb, safe=""), w, q))


def pick(seed, k=4, count=COUNT):
    """k distinct frames for `seed`, stable across rebuilds and well spread.

    Walks the pool with a hash-derived stride rather than taking a contiguous
    run, so neighbouring cities don't end up showing near-identical sequences.
    COUNT is prime, so every stride in 1..COUNT-1 is coprime with it and the walk
    visits distinct frames for any k <= COUNT.
    """
    hx = int(hashlib.md5(str(seed).encode("utf-8")).hexdigest(), 16)
    start = hx % count
    stride = 1 + ((hx >> 64) % (count - 1))
    return [1 + ((start + i * stride) % count) for i in range(min(k, count))]


def strip(seed, k=4, w=760, q=80, alt="Wedding photograph by Elizabeth Scott",
          heading="Recent work", note=""):
    """A responsive image strip in the site's glass-card idiom.

    Alt text is deliberately generic. These are portfolio frames, not photographs
    of the page's city - captioning them with a location we cannot verify would
    be false, and would poison image search besides.
    """
    frames = pick(seed, k)
    cells = "".join(
        '<div style="position:relative;aspect-ratio:4/5;border-radius:12px;overflow:hidden;background:rgba(255,255,255,.04)">'
        '<img src="%s" alt="%s" loading="lazy" decoding="async" '
        'style="position:absolute;inset:0;width:100%%;height:100%%;object-fit:cover">'
        '</div>' % (frame_url(n, w, q), alt) for n in frames)
    note_html = ('<p style="color:var(--mist);font-size:13.5px;margin-top:14px;opacity:.85">%s</p>'
                 % note) if note else ""
    return ('\n  <div class="glass" style="padding:26px;border-radius:var(--radius);margin-top:20px">'
            '<h2 style="font-family:var(--serif);font-size:25px">%s</h2>'
            '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));'
            'gap:12px;margin-top:16px">%s</div>%s'
            '<p style="text-align:center;margin-top:18px">'
            '<a class="btn" href="/portfolio">See the full portfolio &rarr;</a></p></div>'
            % (heading, cells, note_html))


if __name__ == "__main__":
    seen = {}
    for c in ["Nashville TN", "Franklin TN", "Seattle WA", "Charleston SC", "Charleston WV"]:
        f = pick(c)
        seen[c] = f
        print("%-16s %s" % (c, f))
    flat = [n for v in seen.values() for n in v]
    print("\ndistinct frames across %d cities: %d of %d slots"
          % (len(seen), len(set(flat)), len(flat)))
    print("stable on repeat:", pick("Nashville TN") == seen["Nashville TN"])

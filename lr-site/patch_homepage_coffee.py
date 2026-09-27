#!/usr/bin/env python3
"""Insert the coffee-card promo section into the LeaseReputation homepage.

Mojibake-safe (UTF-8 in/out), idempotent (marker-guarded: safe to run
twice), and reversible (--remove). Inserts just above the site footer, or
above </body> if no footer is found.

Usage, from C:\\Users\\kurvh\\lr-site:
    python patch_homepage_coffee.py            # insert
    python patch_homepage_coffee.py --remove   # take it back out
Then: python kv_sync.py --site "C:\\Users\\kurvh\\lr-site" --namespace-id 9ff61a4f0e694e37ac439964e04e6ddf
"""
import io
import re
import sys

INDEX = "index.html"
MARK_START = "<!-- lrcoffee:start -->"
MARK_END = "<!-- lrcoffee:end -->"

SECTION = MARK_START + """
<section class="lrcoffee">
  <style>
    .lrcoffee{max-width:1060px;margin:26px auto;padding:0 20px}
    .lrcoffee .lrcoffee-card{position:relative;overflow:hidden;display:flex;
      align-items:center;gap:22px;flex-wrap:wrap;background:#17112E;
      border:1px solid rgba(196,181,253,.35);border-radius:22px;
      padding:26px 28px}
    .lrcoffee .lrcoffee-card:before{content:"";position:absolute;inset:0 0 auto 0;
      height:5px;background:linear-gradient(90deg,#4C4FE6,#C4B5FD)}
    .lrcoffee-cup{flex:0 0 auto;width:62px;height:62px;border-radius:50%;
      display:flex;align-items:center;justify-content:center;font-size:30px;
      background:rgba(76,79,230,.18);border:1.5px solid rgba(196,181,253,.5)}
    .lrcoffee-body{flex:1 1 260px;min-width:240px}
    .lrcoffee-body h2{margin:0 0 6px;font-size:1.35rem;color:#fff;font-weight:800}
    .lrcoffee-body h2 span{color:#C4B5FD}
    .lrcoffee-body p{margin:0;color:#A6A0C4;font-size:.95rem;line-height:1.5}
    .lrcoffee-count{display:inline-block;margin-top:10px;padding:5px 13px;
      border-radius:20px;font-size:.8rem;font-weight:700;color:#3DDC97;
      background:rgba(61,220,151,.10);border:1px solid rgba(61,220,151,.45)}
    .lrcoffee-cta{flex:0 0 auto}
    .lrcoffee-cta a{display:inline-block;background:#4C4FE6;color:#fff;
      text-decoration:none;font-weight:700;font-size:.95rem;
      padding:13px 26px;border-radius:13px}
    .lrcoffee-cta a:hover{background:#6D6FF0}
    .lrcoffee-fine{margin-top:10px;color:#6E698C;font-size:.75rem;line-height:1.45}
  </style>
  <div class="lrcoffee-card">
    <div class="lrcoffee-cup">&#9749;</div>
    <div class="lrcoffee-body">
      <h2>Coffee <span>on us.</span></h2>
      <p>The first 1,000 verified reviewers get a $5 coffee card, mailed to
      you — our thank-you for telling the truth about where you lived.</p>
      <span class="lrcoffee-count" id="lrcoffee-count">First 1,000 reviewers</span>
      <div class="lrcoffee-fine">One per reviewer &middot; The gift is the
      same for everyone and never conditioned on what your review says.</div>
    </div>
    <div class="lrcoffee-cta">
      <a href="https://app.leasereputation.com">Write a verified review</a>
    </div>
  </div>
  <script>
  (function(){
    fetch('https://firestore.googleapis.com/v1/projects/lease-reputation/databases/(default)/documents/meta/coffeeCard')
      .then(function(r){return r.ok?r.json():null})
      .then(function(d){
        if(!d||!d.fields)return;
        var n=parseInt((d.fields.claimed&&d.fields.claimed.integerValue)||'0',10);
        var left=Math.max(0,1000-n);
        var el=document.getElementById('lrcoffee-count');
        if(!el)return;
        if(left>0){el.textContent=left+' of 1,000 still available';}
        else{var card=document.querySelector('.lrcoffee');if(card)card.style.display='none';}
      }).catch(function(){});
  })();
  </script>
</section>
""" + MARK_END


def main():
    remove = "--remove" in sys.argv
    with io.open(INDEX, "r", encoding="utf-8") as f:
        html = f.read()

    if remove:
        if MARK_START not in html:
            print("nothing to remove"); return
        html = re.sub(re.escape(MARK_START) + r".*?" + re.escape(MARK_END),
                      "", html, flags=re.S)
        with io.open(INDEX, "w", encoding="utf-8", newline="") as f:
            f.write(html)
        print("coffee section removed from " + INDEX); return

    if MARK_START in html:
        print("already inserted — nothing to do"); return

    m = re.search(r"<footer\b", html, flags=re.I)
    if m:
        idx = m.start()
        where = "above <footer>"
    else:
        m = re.search(r"</body>", html, flags=re.I)
        if not m:
            print("ERROR: no <footer> or </body> found in " + INDEX)
            sys.exit(1)
        idx = m.start()
        where = "above </body>"

    html = html[:idx] + SECTION + "\n" + html[idx:]
    with io.open(INDEX, "w", encoding="utf-8", newline="") as f:
        f.write(html)
    print("coffee section inserted " + where + " in " + INDEX)


if __name__ == "__main__":
    main()

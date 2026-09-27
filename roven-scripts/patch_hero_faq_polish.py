#!/usr/bin/env python3
# ============================================================================
# ROVEN - patch_hero_faq_polish.py
# Build ID: JC-ROVEN-POLISH-0801-001
#
#   1. Hero: three clean lines instead of an awkward wrap.
#        No ghost jobs.
#        No ghosting.
#        Get hired on Roven.      (accent)
#
#   2. FAQ: two-column grid on desktop, so 16 questions stop being an
#      endless scroll. Tighter cards, hover state, green left rule when
#      open, group headers with a hairline. Single column on mobile.
#
# Idempotent. Asserts anchors, reports anything it cannot find.
# Usage: python patch_hero_faq_polish.py --site C:\\Users\\kurvh\\roven-site
# ============================================================================

import argparse
import os
import sys

NEW_H1 = ('<h1>No ghost jobs.<br>No ghosting.<br>'
          '<span class="accent">Get hired on Roven.</span></h1>')

OLD_H1S = [
    ('<h1>No ghost jobs. No ghosting.<br>'
     '<span class="accent">Get hired on Roven.</span></h1>'),
    ('<h1>Stop applying into silence.<br>'
     'Every employer here <span class="accent">answers.</span></h1>'),
]

NEW_FAQ_CSS = """/* --- homepage FAQ --- */
#faq{background:#F2F5F4;scroll-margin-top:80px}
.hp-faq{display:grid;grid-template-columns:1fr 1fr;gap:12px 16px;align-items:start;margin-top:6px}
.hp-faq-group{grid-column:1/-1;display:flex;align-items:center;gap:14px;font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.14em;font-weight:700;color:#0F7A45;margin:26px 0 6px}
.hp-faq-group::after{content:'';flex:1;height:1px;background:#D8DEDC}
.hp-faq-group:first-child{margin-top:8px}
.hp-faq details{border:1px solid #DDE4E2;border-left:3px solid #DDE4E2;border-radius:12px;background:#fff;overflow:hidden;transition:border-color .16s ease,box-shadow .16s ease,transform .16s ease}
.hp-faq details:hover{border-color:#BFD3CA;border-left-color:#1CA45F;box-shadow:0 4px 14px rgba(22,32,46,.06)}
.hp-faq details[open]{border-color:#C7DCD1;border-left-color:#1CA45F;box-shadow:0 6px 20px rgba(22,32,46,.08)}
.hp-faq summary{cursor:pointer;list-style:none;padding:15px 18px;font-family:'Instrument Sans',sans-serif;font-size:15px;font-weight:600;line-height:1.4;color:#16202E;display:flex;justify-content:space-between;align-items:flex-start;gap:14px}
.hp-faq summary::-webkit-details-marker{display:none}
.hp-faq summary::after{content:'+';font-family:'IBM Plex Mono',monospace;font-size:18px;font-weight:700;color:#1CA45F;flex:none;line-height:1.25;transition:transform .16s ease}
.hp-faq details[open] summary::after{content:'\\2212'}
.hp-faq details p{margin:0;padding:0 18px 16px;font-size:13.5px;line-height:1.68;color:#41505F;border-top:1px solid #EDF1EF;padding-top:14px;margin-top:-2px}
.hp-faq details p a{color:#0F7A45;text-decoration:none;border-bottom:1px solid rgba(28,164,95,.4)}
.hp-faq details p a:hover{border-bottom-color:#1CA45F}
@media(max-width:820px){.hp-faq{grid-template-columns:1fr}}"""


def patch(path):
    with open(path, "r", encoding="utf-8") as f:
        h = f.read()
    original = h
    done, skipped = [], []

    # ---- 1. hero line break ----
    if NEW_H1 in h:
        skipped.append("hero already on three lines")
    else:
        hit = False
        for old in OLD_H1S:
            if old in h:
                h = h.replace(old, NEW_H1, 1)
                hit = True
                break
        if hit:
            done.append("hero split onto three clean lines")
        else:
            skipped.append("H1 NOT FOUND - paste me your current <h1>")

    # ---- 2. FAQ restyle ----
    if "grid-template-columns:1fr 1fr;gap:12px 16px" in h:
        skipped.append("FAQ already restyled")
    else:
        start = h.find("/* --- homepage FAQ --- */")
        if start == -1:
            skipped.append("FAQ CSS BLOCK NOT FOUND - send me your <style>")
        else:
            # find the end of the block: last rule of either prior version
            end = -1
            for marker in ("@media(max-width:820px){.hp-faq{grid-template-columns:1fr}}",
                           ".hp-faq details p + p{padding-top:0}",
                           ".hp-faq details p a{color:#0F7A45;text-decoration:none;"
                           "border-bottom:1px solid rgba(28,164,95,.4)}"):
                pos = h.find(marker, start)
                if pos != -1:
                    end = max(end, pos + len(marker))
            if end == -1:
                skipped.append("FAQ CSS end marker not found - fix manually")
            else:
                h = h[:start] + NEW_FAQ_CSS + h[end:]
                done.append("FAQ -> two-column grid, tighter cards, "
                            "hover + open states")

    if h == original:
        print("  nothing changed.")
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(h)

    print("\nDONE:")
    for d in done:
        print("  + " + d)
    if skipped:
        print("\nSKIPPED / CHECK:")
        for s in skipped:
            print("  ! " + s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    args = ap.parse_args()
    p = os.path.join(args.site, "index.html")
    if not os.path.exists(p):
        sys.exit(f"index.html not found at {p}")
    patch(p)
    print("\nOpen index.html locally: hero should be three lines, FAQ two "
          "columns with questions readable.")


if __name__ == "__main__":
    main()

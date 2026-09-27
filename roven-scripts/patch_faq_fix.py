#!/usr/bin/env python3
# ============================================================================
# ROVEN - patch_faq_fix.py
# Build ID: JC-ROVEN-FAQFIX-0801-001
#
# Two fixes to index.html:
#
#   1. FAQ TEXT INVISIBLE. The FAQ styles were written for a dark section
#      and the FAQ landed in a light one - white text on a light background,
#      so every question rendered blank with only the "+" showing. Restyled
#      for a light background, and the section now sets its own background
#      explicitly so it can never silently invert again.
#
#   2. HERO PILL CLUTTER. Four stat pills were added on top of the two that
#      already existed. Six pills in a hero is noise; trimmed to three, and
#      the strongest three.
#
# Idempotent. Asserts anchors, reports anything it cannot find.
# Usage: python patch_faq_fix.py --site C:\\Users\\kurvh\\roven-site
# ============================================================================

import argparse
import os
import re
import sys

# ---- light-background FAQ styling -----------------------------------------
NEW_FAQ_CSS = """/* --- homepage FAQ --- */
#faq{background:#F2F5F4}
.hp-faq{max-width:860px}
.hp-faq-group{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.14em;font-weight:700;color:#0F7A45;margin:34px 0 14px}
.hp-faq details{border:1px solid #D8DEDC;border-radius:14px;background:#fff;margin-bottom:10px;overflow:hidden}
.hp-faq details[open]{border-color:#1CA45F;box-shadow:0 4px 18px rgba(22,32,46,.07)}
.hp-faq summary{cursor:pointer;list-style:none;padding:17px 20px;font-family:'Instrument Sans',sans-serif;font-size:15.5px;font-weight:600;color:#16202E;display:flex;justify-content:space-between;align-items:center;gap:14px}
.hp-faq summary::-webkit-details-marker{display:none}
.hp-faq summary::after{content:'+';font-family:'IBM Plex Mono',monospace;font-size:19px;color:#1CA45F;flex:none;line-height:1}
.hp-faq details[open] summary::after{content:'\\2212'}
.hp-faq details p{margin:0;padding:0 20px 18px;font-size:14px;line-height:1.68;color:#41505F}
.hp-faq details p a{color:#0F7A45;text-decoration:none;border-bottom:1px solid rgba(28,164,95,.4)}
.hp-faq details p + p{padding-top:0}"""

OLD_STRIP_4 = ('<div class="hp-stats">'
               '<div class="hp-stat"><b>$0</b><span>FOREVER, FOR JOB SEEKERS</span></div>'
               '<div class="hp-stat"><b>100%</b><span>OF EMPLOYERS VERIFIED</span></div>'
               '<div class="hp-stat"><b>30 DAY</b><span>CONFIRMATION CLOCK ON EVERY LISTING</span></div>'
               '<div class="hp-stat"><b>1</b><span>UPLOAD &mdash; NEVER RETYPE YOUR HISTORY</span></div>'
               '</div>')

NEW_STRIP_3 = ('<div class="hp-stats">'
               '<div class="hp-stat"><b>$0</b><span>FOREVER, FOR JOB SEEKERS</span></div>'
               '<div class="hp-stat"><b>100%</b><span>OF EMPLOYERS VERIFIED</span></div>'
               '<div class="hp-stat"><b>30 DAY</b><span>FRESHNESS CLOCK ON EVERY JOB</span></div>'
               '</div>')


def patch(path):
    with open(path, "r", encoding="utf-8") as f:
        h = f.read()
    original = h
    done, skipped = [], []

    # ---- 1. replace the FAQ CSS block ----
    if "#faq{background:#F2F5F4}" in h:
        skipped.append("FAQ styles already fixed")
    else:
        start = h.find("/* --- homepage FAQ --- */")
        if start == -1:
            skipped.append("FAQ CSS BLOCK NOT FOUND - send me your <style> block")
        else:
            # the block ends at the last rule I wrote
            marker = ".hp-faq details p + p{padding-top:0}"
            end = h.find(marker, start)
            if end == -1:
                skipped.append("FAQ CSS end marker not found - fix manually")
            else:
                end += len(marker)
                h = h[:start] + NEW_FAQ_CSS + h[end:]
                done.append("FAQ restyled for a light background "
                            "(questions were white-on-white)")

    # ---- 2. trim the hero pills ----
    if "FRESHNESS CLOCK ON EVERY JOB" in h:
        skipped.append("hero pills already trimmed")
    elif OLD_STRIP_4 in h:
        h = h.replace(OLD_STRIP_4, NEW_STRIP_3, 1)
        done.append("hero stat pills 4 -> 3")
    else:
        skipped.append("stat strip not in expected form - trim manually")

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
    print("\nOpen index.html locally and expand a FAQ question before "
          "deploying - the text should be dark on white.")


if __name__ == "__main__":
    main()

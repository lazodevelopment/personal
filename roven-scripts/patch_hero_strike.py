#!/usr/bin/env python3
# ============================================================================
# ROVEN - patch_hero_strike.py
# Build ID: JC-ROVEN-HEROSTRIKE-0801-001
#
# Hero ->
#     Ghost jobs.        (struck through, red angled rule)
#     Ghosting.          (struck through)
#     Get hired on Roven. (accent green)
#
# The strikethrough does the negating, so the word "No" is dropped - keeping
# it would make "No ~ghost jobs~" a double negative. Same treatment already
# used in the /employers hero, so the two pages now rhyme.
#
# Idempotent. Usage:
#   python patch_hero_strike.py --site C:\\Users\\kurvh\\roven-site
# ============================================================================

import argparse
import os
import sys

STRIKE_CSS = """/* --- hero strikethrough --- */
.hero h1 .strike,.hp-strike{position:relative;color:rgba(255,255,255,.42);white-space:nowrap}
.hero h1 .strike::after,.hp-strike::after{content:"";position:absolute;left:-3%;right:-3%;top:52%;height:5px;background:#C0483B;transform:rotate(-2.2deg);border-radius:3px}"""

NEW_H1 = ('<h1><span class="hp-strike">Ghost jobs.</span><br>'
          '<span class="hp-strike">Ghosting.</span><br>'
          '<span class="accent">Get hired on Roven.</span></h1>')

OLD_H1S = [
    ('<h1>No ghost jobs.<br>No ghosting.<br>'
     '<span class="accent">Get hired on Roven.</span></h1>'),
    ('<h1>No ghost jobs. No ghosting.<br>'
     '<span class="accent">Get hired on Roven.</span></h1>'),
    ('<h1>Stop applying into silence.<br>'
     'Every employer here <span class="accent">answers.</span></h1>'),
]


def patch(path):
    with open(path, "r", encoding="utf-8") as f:
        h = f.read()
    original = h
    done, skipped = [], []

    # ---- styles ----
    if "hp-strike" in h and "/* --- hero strikethrough --- */" in h:
        skipped.append("strike styles already present")
    else:
        if "</style>" in h:
            h = h.replace("</style>", STRIKE_CSS + "\n</style>", 1)
            done.append("strike styles injected")
        elif "</head>" in h:
            h = h.replace("</head>", f"<style>{STRIKE_CSS}</style>\n</head>", 1)
            done.append("strike styles injected as new <style>")
        else:
            skipped.append("no </style> or </head> - styles NOT added")

    # ---- headline ----
    if NEW_H1 in h:
        skipped.append("headline already struck through")
    else:
        hit = False
        for old in OLD_H1S:
            if old in h:
                h = h.replace(old, NEW_H1, 1)
                hit = True
                break
        if hit:
            done.append("hero -> Ghost jobs. / Ghosting. / Get hired on Roven.")
        else:
            skipped.append("H1 NOT FOUND - paste me your current <h1>")

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
    print("\nCheck locally: the red rule should sit across the middle of each "
          "struck word, angled slightly, matching the /employers hero.")


if __name__ == "__main__":
    main()

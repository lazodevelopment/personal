#!/usr/bin/env python3
# ============================================================================
# ROVEN - patch_hero_v3.py
# Build ID: JC-ROVEN-HEROV3-0801-001
#
# Hero headline ->
#     No ghost jobs. No ghosting.
#     Get hired on Roven.
#
# The substantiating lede underneath is deliberately kept. The headline makes
# the claim; the lede is the receipt. A hero that is all assertion is the one
# thing this brand cannot be.
#
# Idempotent. Asserts anchors and reports anything it cannot find.
# Usage: python patch_hero_v3.py --site C:\\Users\\kurvh\\roven-site
# ============================================================================

import argparse
import os
import sys

NEW_H1 = ('<h1>No ghost jobs. No ghosting.<br>'
          '<span class="accent">Get hired on Roven.</span></h1>')

OLD_H1S = [
    ('<h1>Stop applying into silence.<br>'
     'Every employer here <span class="accent">answers.</span></h1>'),
    ('<h1>Stop paying to post.<br>'
     'Pay when you <span class="accent">actually hire.</span></h1>'),
    ('<h1>Every job is real.<br>'
     'Every employer <span class="accent">answers.</span></h1>'),
]


def patch(path):
    with open(path, "r", encoding="utf-8") as f:
        h = f.read()
    original = h
    done, skipped = [], []

    if NEW_H1 in h:
        skipped.append("headline already updated")
    else:
        hit = False
        for old in OLD_H1S:
            if old in h:
                h = h.replace(old, NEW_H1, 1)
                hit = True
                break
        if hit:
            done.append("H1 -> 'No ghost jobs. No ghosting. / "
                        "Get hired on Roven.'")
        else:
            skipped.append("H1 NOT FOUND - paste me your current <h1> line")

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


if __name__ == "__main__":
    main()

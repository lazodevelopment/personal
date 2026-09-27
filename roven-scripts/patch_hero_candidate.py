#!/usr/bin/env python3
# ============================================================================
# ROVEN - patch_hero_candidate.py
# Build ID: JC-ROVEN-HEROFIX-0801-001
#
# The homepage belongs to job seekers. /employers carries the employer
# argument. This reverts the three things that were pulled employer-facing:
#
#   1. H1        -> candidate outcome
#   2. Subhead   -> candidate promise (was leading with recruiter costs)
#   3. Stat strip-> was 2/4 employer stats; now all four speak to candidates
#
# Everything else added yesterday stays: the FAQ, the ticker, the scorecard
# labels, the nationwide fix.
#
# Idempotent. Asserts every anchor and reports what it could not find.
# Usage: python patch_hero_candidate.py --site C:\\Users\\kurvh\\roven-site
# ============================================================================

import argparse
import os
import sys

NEW_H1 = ('<h1>Stop applying into silence.<br>'
          'Every employer here <span class="accent">answers.</span></h1>')

OLD_H1S = [
    '<h1>Stop paying to post.<br>Pay when you <span class="accent">actually hire.</span></h1>',
    '<h1>Every job is real.<br>Every employer <span class="accent">answers.</span></h1>',
]

OLD_SUBS = [
    ("A recruiter costs thousands. Sponsored ads bill you whether you hire "
     "or not. Roven is free to post and charges one flat fee only when "
     "someone accepts your offer &mdash; and it is free for job seekers "
     "forever. Every employer is verified, every listing is a confirmed open "
     "role, and how employers treat applicants goes on their permanent "
     "public record."),
    ("Roven is the hiring marketplace with receipts. Employers are "
     "identity-verified before they can post, every listing is a confirmed "
     "open role, and how they treat applicants goes on their permanent "
     "record."),
]

NEW_SUB = ("Every job on Roven is a real, confirmed-open role at a verified "
           "business &mdash; and every employer's response rate is published "
           "on their listings, so you can see who actually answers before "
           "you spend an hour applying. Free for job seekers. Forever.")

OLD_STRIP = ('<div class="hp-stats">'
             '<div class="hp-stat"><b>$0</b><span>TO POST A ROLE</span></div>'
             '<div class="hp-stat"><b>$0</b><span>FOREVER FOR JOB SEEKERS</span></div>'
             '<div class="hp-stat"><b>3 MIN</b><span>TO POST WITH AI DRAFTING</span></div>'
             '<div class="hp-stat"><b>30 DAY</b><span>CONFIRMATION CLOCK ON EVERY LISTING</span></div>'
             '</div>')

NEW_STRIP = ('<div class="hp-stats">'
             '<div class="hp-stat"><b>$0</b><span>FOREVER, FOR JOB SEEKERS</span></div>'
             '<div class="hp-stat"><b>100%</b><span>OF EMPLOYERS VERIFIED</span></div>'
             '<div class="hp-stat"><b>30 DAY</b><span>CONFIRMATION CLOCK ON EVERY LISTING</span></div>'
             '<div class="hp-stat"><b>1</b><span>UPLOAD &mdash; NEVER RETYPE YOUR HISTORY</span></div>'
             '</div>')


def patch(path):
    with open(path, "r", encoding="utf-8") as f:
        h = f.read()
    original = h
    done, skipped = [], []

    # ---- 1. headline ----
    if NEW_H1 in h:
        skipped.append("headline already candidate-facing")
    else:
        hit = False
        for old in OLD_H1S:
            if old in h:
                h = h.replace(old, NEW_H1, 1)
                hit = True
                break
        if hit:
            done.append("H1 -> 'Stop applying into silence.'")
        else:
            skipped.append("H1 NOT FOUND - send me the current <h1> line")

    # ---- 2. subhead ----
    if NEW_SUB[:45] in h:
        skipped.append("subhead already candidate-facing")
    else:
        hit = False
        for old in OLD_SUBS:
            if old in h:
                h = h.replace(old, NEW_SUB, 1)
                hit = True
                break
        if hit:
            done.append("subhead -> candidate promise")
        else:
            skipped.append("SUBHEAD NOT FOUND - send me the current lede")

    # ---- 3. stat strip ----
    if "FOREVER, FOR JOB SEEKERS" in h:
        skipped.append("stat strip already candidate-facing")
    elif OLD_STRIP in h:
        h = h.replace(OLD_STRIP, NEW_STRIP, 1)
        done.append("stat strip -> four candidate-facing stats")
    else:
        skipped.append("STAT STRIP not found in expected form - check manually")

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
    path = os.path.join(args.site, "index.html")
    if not os.path.exists(path):
        sys.exit(f"index.html not found at {path}")
    patch(path)
    print("\nThe employer argument stays where it belongs: /employers")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# ============================================================================
# ROVEN - patch_pricing_ctas.py
# Build ID: JC-ROVEN-PRICECTA-0801-001
#
# The three pricing cards on /employers had no call to action - a reader got
# to the most persuasive part of the page and had nothing to click. Adds a
# button to each, with copy matched to that card:
#
#   contract card  -> "Post a contract role - free"
#   full-time card -> "Post a full-time role - free"
#   founding card  -> "Claim founding status"      (solid green, it is the
#                                                   one with scarcity behind it)
#
# Idempotent. Usage:
#   python patch_pricing_ctas.py --site C:\\Users\\kurvh\\roven-site
# ============================================================================

import argparse
import os
import sys

CTA_CSS = """
/* ---- pricing card CTAs ---- */
.emp-price-cta{display:block;margin-top:16px;text-align:center;padding:12px 16px;border-radius:100px;font-family:'Instrument Sans',sans-serif;font-size:14px;font-weight:600;text-decoration:none;color:#fff;border:1px solid rgba(255,255,255,.26);background:rgba(255,255,255,.04);transition:background .16s ease,border-color .16s ease,transform .16s ease}
.emp-price-cta:hover{border-color:#1CA45F;background:rgba(28,164,95,.14);transform:translateY(-1px)}
.emp-price-card.featured .emp-price-cta{background:#1CA45F;border-color:#1CA45F;box-shadow:0 6px 22px rgba(28,164,95,.34)}
.emp-price-card.featured .emp-price-cta:hover{background:#178F52;border-color:#178F52;box-shadow:0 10px 28px rgba(28,164,95,.42)}
.emp-price-note{margin:10px 0 0;text-align:center;font-family:'IBM Plex Mono',monospace;font-size:8.5px;letter-spacing:.1em;font-weight:700;color:rgba(255,255,255,.38)}"""

APP = "https://app.rovenhr.com"

# (anchor that ends the card body, button html)
INSERTS = [
    ("List price $249. Launch pricing published today and honored while it stands.</p>",
     f'\n        <a class="emp-price-cta" href="{APP}">Post a contract role &mdash; free</a>'),
    ("List price $499. One flat fee at the moment your offer is accepted.</p>",
     f'\n        <a class="emp-price-cta" href="{APP}">Post a full-time role &mdash; free</a>'),
    ("Once 100 spots fill, founding terms close permanently.</p>",
     f'\n        <a class="emp-price-cta" href="{APP}">Claim founding status</a>'
     f'\n        <p class="emp-price-note">VERIFICATION TAKES MINUTES</p>'),
]


def patch(path):
    with open(path, "r", encoding="utf-8") as f:
        h = f.read()
    original = h
    done, skipped = [], []

    # ---- styles ----
    if "emp-price-cta" in h:
        skipped.append("CTA styles already present")
    else:
        if "</style>" in h:
            h = h.replace("</style>", CTA_CSS + "\n</style>", 1)
            done.append("CTA styles injected")
        else:
            skipped.append("no </style> found - styles NOT added")

    # ---- buttons ----
    added = 0
    for anchor, button in INSERTS:
        if button.strip() in h:
            continue
        if anchor in h:
            h = h.replace(anchor, anchor + button, 1)
            added += 1
        else:
            skipped.append(f"anchor not found: ...{anchor[-42:]}")
    if added:
        done.append(f"added {added} pricing CTA button(s)")
    elif not skipped:
        skipped.append("buttons already present")

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
    p = os.path.join(args.site, "employers.html")
    if not os.path.exists(p):
        sys.exit(f"employers.html not found at {p}")
    patch(p)
    print("\nCheck locally: three buttons, the founding one solid green.")


if __name__ == "__main__":
    main()

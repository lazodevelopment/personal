#!/usr/bin/env python3
# ============================================================================
# ROVEN - patch_faq_split.py
# Build ID: JC-ROVEN-FAQSPLIT-0801-001
#
# The homepage belongs to job seekers, so the FOR EMPLOYERS questions move
# off it.
#
#   index.html
#     - removes the FOR EMPLOYERS group and its 8 questions
#     - REBUILDS the FAQPage schema with only the 8 remaining questions.
#       This matters: schema that declares questions not visible on the page
#       is a structured-data violation, not a harmless leftover.
#     - drops the now-redundant FOR JOB SEEKERS header (one audience left)
#     - adds a quiet line pointing employers to /employers
#
#   employers.html
#     - adds "Can I pay to have my listing seen first?" - the one homepage
#       employer question with no equivalent there, and the strongest single
#       answer Roven has.
#
# Idempotent. Usage:
#   python patch_faq_split.py --site C:\\Users\\kurvh\\roven-site
# ============================================================================

import argparse
import json
import os
import re
import sys

SEEKER_QA = [
    ("Is Roven really free for job seekers?",
     "Yes, permanently. There is no premium tier, no paid placement, no way "
     "to pay for your application to be seen sooner, and no charge to "
     "download anything you make here. It is written into our Terms of "
     "Service, because a promise that is not written down is not a promise."),
    ("Do I have to pay to download my resume?",
     "No. Most resume builders let you build one free and then ask for a card "
     "at the download step. The Roven resume builder is free to build, free "
     "to improve with AI, and free to download - with no watermark. The file "
     "is yours to send anywhere, including to jobs that are not on Roven."),
    ("What does 'confirmed open' actually mean?",
     "Every listing runs on a 30-day confirmation clock. The employer has to "
     "re-confirm the role is genuinely still open, or it comes down "
     "automatically. You can see how recently that happened on the listing "
     "itself. It is the single biggest reason ghost jobs cannot survive here."),
    ("Will I actually hear back?",
     "That is the whole product. Every employer's response rate, average "
     "response speed and confirmed hires are computed automatically from real "
     "activity and published on every listing they post. They cannot edit it "
     "and they cannot buy it. Passing on someone is a perfectly good answer; "
     "silence is the only wrong one, and here it is visible."),
    ("How is this different from Indeed or ZipRecruiter?",
     "They charge employers per application or per month, so the incentive is "
     "volume. Roven charges one flat fee only when a hire actually happens, "
     "so our incentive is your outcome. We also verify every employer and "
     "publish their response record."),
    ("Do I have to upload a resume?",
     "You need a work history, but you can type it in instead of uploading "
     "anything. Either way you only enter it once: it becomes your profile, "
     "your resume, and what the match engine scores new roles against."),
    ("Do employers see my photo?",
     "Only if you add one, and it is entirely optional. When you do, it "
     "appears alongside your application so an employer sees a person rather "
     "than a username."),
    ("Can I delete my account and my data?",
     "Yes, from your profile in the app. Your sign-in is deleted immediately, "
     "your profile, work history, resume files and photo are purged, and past "
     "applications are anonymized so employers keep the record of how they "
     "handled an application without keeping your identity."),
]

EMPLOYER_LINK = ('      <p style="grid-column:1/-1;margin:24px 0 0;font-size:13.5px;'
                 'color:#5B6874">Hiring instead? The employer questions - '
                 'pricing, verification, how the accountability record works - '
                 'are answered on the <a href="/employers" '
                 'style="color:#0F7A45;font-weight:600">employers page</a>.</p>\n')

NEW_EMP_Q = (
    "Can I pay to have my listing seen first?",
    "No, and we will not build it. Visibility on Roven cannot be purchased "
    "by anyone, at any price. Roles surface on fit. The moment placement is "
    "for sale, every listing becomes a question about budget rather than "
    "about the job - which is the problem we exist to fix.")


def patch_index(path):
    with open(path, "r", encoding="utf-8") as f:
        h = f.read()
    original = h
    done, skipped = [], []

    # ---- remove the FOR EMPLOYERS block ----
    marker = '<p class="hp-faq-group">FOR EMPLOYERS</p>'
    if marker not in h:
        skipped.append("FOR EMPLOYERS block already removed")
    else:
        start = h.index(marker)
        # everything from that header to the final </details> in the FAQ
        last_close = h.rfind("</details>")
        if last_close == -1 or last_close < start:
            skipped.append("could not locate end of employer questions")
        else:
            end = last_close + len("</details>")
            removed = h[start:end].count("<details>")
            h = h[:start] + EMPLOYER_LINK + h[end:]
            done.append(f"removed {removed} employer questions from homepage")

    # ---- drop the now-redundant seeker header ----
    seeker_hdr = '<p class="hp-faq-group">FOR JOB SEEKERS</p>'
    if seeker_hdr in h:
        h = h.replace(seeker_hdr, "", 1)
        done.append("dropped 'FOR JOB SEEKERS' header (only one audience left)")

    # ---- rebuild the FAQ schema ----
    m = re.search(r'<script type="application/ld\+json">\s*\{"@context":'
                  r'"https://schema\.org","@type":"FAQPage".*?</script>',
                  h, re.S)
    if not m:
        skipped.append("FAQPage schema not found - CHECK MANUALLY")
    else:
        entities = [{"@type": "Question", "name": q,
                     "acceptedAnswer": {"@type": "Answer", "text": a}}
                    for q, a in SEEKER_QA]
        payload = {"@context": "https://schema.org", "@type": "FAQPage",
                   "mainEntity": entities}
        new_schema = ('<script type="application/ld+json">'
                      + json.dumps(payload, separators=(",", ":"))
                      + "</script>")
        if len(re.findall(r'"@type":"Question"', m.group(0))) == len(SEEKER_QA):
            skipped.append("schema already trimmed to 8 questions")
        else:
            h = h[:m.start()] + new_schema + h[m.end():]
            done.append(f"FAQ schema rebuilt with {len(SEEKER_QA)} questions "
                        f"(was 16 - must match what is on the page)")

    if h != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(h)
    return done, skipped


def patch_employers(path):
    with open(path, "r", encoding="utf-8") as f:
        h = f.read()
    original = h
    done, skipped = [], []

    q, a = NEW_EMP_Q
    if q in h:
        skipped.append("employers page already has the paid-placement answer")
    else:
        block = f"      <details>\n        <summary>{q}</summary>\n        <p>{a}</p>\n      </details>\n"
        anchor = '<div class="faq">'
        if anchor in h:
            idx = h.index(anchor) + len(anchor)
            h = h[:idx] + "\n" + block + h[idx:]
            done.append("added 'Can I pay to be seen first?' to employers FAQ")
        else:
            skipped.append("employers FAQ container not found - add manually")

    if h != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(h)
    return done, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    args = ap.parse_args()

    idx = os.path.join(args.site, "index.html")
    emp = os.path.join(args.site, "employers.html")
    for p in (idx, emp):
        if not os.path.exists(p):
            sys.exit(f"not found: {p}")

    d1, s1 = patch_index(idx)
    d2, s2 = patch_employers(emp)

    print("\nDONE:")
    for d in d1 + d2:
        print("  + " + d)
    if s1 + s2:
        print("\nSKIPPED / CHECK:")
        for s in s1 + s2:
            print("  ! " + s)
    print("\nHomepage FAQ is now job-seeker only. Employer questions live on "
          "/employers.")


if __name__ == "__main__":
    main()

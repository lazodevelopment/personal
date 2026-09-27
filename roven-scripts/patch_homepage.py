#!/usr/bin/env python3
# ============================================================================
# ROVEN - patch_homepage.py
# Build ID: JC-ROVEN-HOMEPATCH-0730-003
#
# Targeted edits to index.html. Every edit asserts its anchor first, so if
# the markup has moved the script tells you exactly what it couldn't find
# and changes nothing. Idempotent - safe to run twice.
#
#   1. Hero: outcome-led headline + subhead that leads with the model
#   2. Honest stat strip above the fold (no invented performance data)
#   3. "NOW LIVE - PHOENIX" -> nationwide (stale since the cap went national)
#   4. Label the illustrative employer scorecards as examples
#      (they currently read as real employer records - on the receipts
#       company that is the one thing we cannot leave ambiguous)
#   5. Mount point + styles for the live activity ticker
#   6. Homepage FAQ - dual audience, FAQPage schema, and deliberately an
#      internal-linking hub: nearly every answer points at a product page.
#
# Usage: python patch_homepage.py --site C:\\Users\\kurvh\\roven-site
# ============================================================================

import argparse
import os
import re
import sys

STAT_CSS = """
/* --- homepage additions --- */
.hp-stats{display:flex;flex-wrap:wrap;gap:10px;margin:22px 0 4px}
.hp-stat{display:inline-flex;align-items:center;gap:9px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.15);border-radius:100px;padding:9px 16px}
.hp-stat b{font-family:'Bricolage Grotesque',sans-serif;font-size:17px;font-weight:800;color:#3ADB8B;letter-spacing:-.4px}
.hp-stat span{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.1em;font-weight:700;color:rgba(255,255,255,.62)}
.hp-example-tag{display:inline-flex;align-items:center;gap:6px;background:rgba(232,196,111,.14);border:1px solid rgba(232,196,111,.45);border-radius:100px;padding:5px 11px;margin-bottom:12px;font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.12em;font-weight:700;color:#E8C46F}
/* live activity ticker */
#hp-ticker{display:none;border-top:1px solid rgba(255,255,255,.09);border-bottom:1px solid rgba(255,255,255,.09);background:rgba(255,255,255,.025);overflow:hidden;padding:13px 0}
#hp-ticker .lbl{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.14em;font-weight:700;color:#3ADB8B;padding:0 18px;white-space:nowrap;display:inline-flex;align-items:center;gap:7px}
#hp-ticker .dot{width:7px;height:7px;border-radius:50%;background:#3ADB8B;box-shadow:0 0 8px rgba(58,219,139,.8);flex:none}
#hp-ticker .track{display:flex;align-items:center;gap:0;animation:hp-scroll 46s linear infinite;width:max-content}
#hp-ticker:hover .track{animation-play-state:paused}
#hp-ticker .item{display:inline-flex;align-items:center;gap:10px;padding:0 26px;border-right:1px solid rgba(255,255,255,.09);white-space:nowrap;font-size:13.5px;color:rgba(255,255,255,.72)}
#hp-ticker .item em{font-style:normal;color:#fff;font-weight:600}
#hp-ticker .item .ago{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.08em;color:rgba(255,255,255,.42)}
@keyframes hp-scroll{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@media(prefers-reduced-motion:reduce){#hp-ticker .track{animation:none;flex-wrap:wrap}}
"""

TICKER_HTML = """<div id="hp-ticker" aria-label="Recent activity on Roven">
  <div class="track" id="hp-ticker-track"></div>
</div>
<script>
(function () {
  var MIN_ITEMS = 6;  // below this the ticker stays hidden - a nearly empty
                      // ticker is worse than no ticker, and faking rows is
                      // exactly what we criticise other boards for.
  fetch('/activity.json', { cache: 'no-store' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) {
      if (!d || !d.items || d.items.length < MIN_ITEMS) return;
      var track = document.getElementById('hp-ticker-track');
      var html = d.items.map(function (i) {
        return '<span class="item"><em>' + i.what + '</em> &middot; ' +
               i.where + ' <span class="ago">' + i.ago + '</span></span>';
      }).join('');
      track.innerHTML = html + html;   // duplicated for a seamless loop
      document.getElementById('hp-ticker').style.display = 'block';
    })
    .catch(function () { /* stay hidden */ });
})();
</script>
"""


# ---------------------------------------------------------------- FAQ

FAQ_CSS = """
/* --- homepage FAQ --- */
.hp-faq{max-width:860px}
.hp-faq-group{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.14em;font-weight:700;color:#3ADB8B;margin:34px 0 14px}
.hp-faq details{border:1px solid rgba(255,255,255,.12);border-radius:14px;background:rgba(255,255,255,.04);margin-bottom:10px;overflow:hidden}
.hp-faq details[open]{border-color:rgba(58,219,139,.4);background:rgba(28,164,95,.06)}
.hp-faq summary{cursor:pointer;list-style:none;padding:17px 20px;font-family:'Instrument Sans',sans-serif;font-size:15.5px;font-weight:600;color:#fff;display:flex;justify-content:space-between;align-items:center;gap:14px}
.hp-faq summary::-webkit-details-marker{display:none}
.hp-faq summary::after{content:'+';font-family:'IBM Plex Mono',monospace;font-size:19px;color:#3ADB8B;flex:none;line-height:1}
.hp-faq details[open] summary::after{content:'\2212'}
.hp-faq details p{margin:0;padding:0 20px 18px;font-size:14px;line-height:1.68;color:rgba(255,255,255,.72)}
.hp-faq details p a{color:#3ADB8B;text-decoration:none;border-bottom:1px solid rgba(58,219,139,.35)}
.hp-faq details p + p{padding-top:0}
"""

FAQ_SEEKERS = [
    ("Is Roven really free for job seekers?",
     "Yes, permanently. There is no premium tier, no paid placement, no way "
     "to pay for your application to be seen sooner, and no charge to "
     "download anything you make here. It is written into our "
     "<a href=\"/terms.html\">Terms of Service</a>, because a promise that "
     "is not written down is not a promise."),
    ("Do I have to pay to download my resume?",
     "No. Most resume builders let you build one free and then ask for a card "
     "at the download step. The <a href=\"/alternatives/free-resume-builder."
     "html\">Roven resume builder</a> is free to build, free to improve with "
     "AI, and free to download &mdash; with no watermark. The file is yours "
     "to send anywhere, including to jobs that are not on Roven."),
    ("What does &ldquo;confirmed open&rdquo; actually mean?",
     "Every listing runs on a 30-day confirmation clock. The employer has to "
     "re-confirm the role is genuinely still open, or it comes down "
     "automatically. You can see how recently that happened on the listing "
     "itself &mdash; &ldquo;confirmed open 2 days ago&rdquo;. It is the "
     "single biggest reason ghost jobs cannot survive here."),
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
     "publish their response record. There is a full breakdown on our "
     "<a href=\"/alternatives/index.html\">comparison pages</a>."),
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
     "handled an application without keeping your identity. The details are "
     "in our <a href=\"/privacy.html\">privacy policy</a>."),
]

FAQ_EMPLOYERS = [
    ("What does Roven cost an employer?",
     "Posting, searching and messaging are free permanently. The only charge "
     "is one flat placement fee when a hire is completed: list pricing is "
     "$249 for a contract, part-time or temporary hire and $499 for a "
     "full-time W-2 hire, with launch pricing currently at $99 and $199. "
     "Right now placement fees are waived entirely while the marketplace "
     "grows. You can compare it to what you pay today with our "
     "<a href=\"/tools/cost-per-hire-calculator.html\">cost-per-hire "
     "calculator</a>."),
    ("When exactly do I pay?",
     "At the moment your offer is accepted &mdash; not the start date, not a "
     "monthly bill, not when applications arrive. If you do not hire, there "
     "is no bill. Ever."),
    ("What if the hire does not work out?",
     "If a hire ends within 30 days, the placement fee is credited in full "
     "toward your next placement. We only want to be paid for hires that "
     "stick."),
    ("Can I pay to have my listing seen first?",
     "No, and we will not build it. Visibility on Roven cannot be purchased "
     "by anyone, at any price. Roles surface on fit. The moment placement is "
     "for sale, every listing becomes a question about budget rather than "
     "about the job."),
    ("What is the accountability record, and can I appeal it?",
     "It is your response rate, response speed and confirmed hires, computed "
     "automatically from what actually happened on the platform. It is not a "
     "review site &mdash; no human writes any part of it. It cannot be "
     "edited, bought or removed, including by us. It also weights recent "
     "behaviour most heavily, so answering your applicants promptly improves "
     "it quickly."),
    ("How does employer verification work?",
     "Every business is checked before it can post its first role. It takes a "
     "few minutes once, and the verified badge then appears on your profile "
     "and on every listing. It is the reason candidates take Roven listings "
     "seriously instead of assuming bait."),
    ("Can I post contract or 1099 roles?",
     "Yes. Full-time W-2, part-time, contract and temporary are all "
     "first-class, every listing is labelled with its type, and the fee "
     "follows the type of engagement."),
    ("Why is it free right now?",
     "Because charging before we have delivered candidates would make us "
     "every other job board. Fees activate only after the platform records "
     "its first 25 confirmed hires and only with 30 days' published notice. "
     "The first 100 verified employers nationwide lock founding terms: free "
     "then, free for 12 months after activation, and 50% off list pricing for "
     "life. Full detail on the <a href=\"/employers.html\">employers "
     "page</a>."),
]


def _details(items):
    out = ""
    for q, a in items:
        out += (f"      <details><summary>{q}</summary><p>{a}</p></details>\n")
    return out


def _faq_schema(all_items):
    import html as _html
    import re as _re

    def clean(t):
        t = _re.sub(r"<[^>]+>", "", t)
        t = _html.unescape(t)
        return t.replace('"', "'").replace("\n", " ").strip()

    q = ",".join(
        '{"@type":"Question","name":"%s","acceptedAnswer":{"@type":"Answer",'
        '"text":"%s"}}' % (clean(a), clean(b)) for a, b in all_items)
    return ('<script type="application/ld+json">{"@context":'
            '"https://schema.org","@type":"FAQPage","mainEntity":[%s]}'
            "</script>" % q)


def faq_section():
    return f"""<section class="section" id="faq">
  <div class="wrap">
    <p class="kicker">Questions</p>
    <h2>Straight answers.</h2>
    <div class="hp-faq">
      <p class="hp-faq-group">FOR JOB SEEKERS</p>
{_details(FAQ_SEEKERS)}      <p class="hp-faq-group">FOR EMPLOYERS</p>
{_details(FAQ_EMPLOYERS)}    </div>
  </div>
</section>
{_faq_schema(FAQ_SEEKERS + FAQ_EMPLOYERS)}
"""


def patch(path):
    with open(path, "r", encoding="utf-8") as f:
        h = f.read()
    original = h
    done, skipped = [], []

    # ---------- 1. styles ----------
    if "hp-stats" not in h:
        if "</style>" in h:
            h = h.replace("</style>", STAT_CSS + "\n</style>", 1)
            done.append("injected homepage styles into existing <style>")
        elif "</head>" in h:
            h = h.replace("</head>", f"<style>{STAT_CSS}</style>\n</head>", 1)
            done.append("injected homepage styles as new <style>")
        else:
            skipped.append("no </style> or </head> found - styles NOT added")
    else:
        skipped.append("styles already present")

    # ---------- 2. hero headline ----------
    old_h1 = "Every job is real.  Every employer answers."
    old_h1_br = "Every job is real. <br>Every employer answers."
    new_h1 = "Stop paying to post.<br>Pay when you actually hire."
    if "Pay when you actually hire" in h:
        skipped.append("hero headline already updated")
    else:
        hit = False
        for cand in (old_h1_br, old_h1,
                     "Every job is real.<br>Every employer answers.",
                     "Every job is real. Every employer answers."):
            if cand in h:
                h = h.replace(cand, new_h1, 1)
                hit = True
                break
        if hit:
            done.append("hero headline -> outcome-led")
        else:
            skipped.append("HERO HEADLINE NOT FOUND - patch manually")

    # ---------- 3. hero subhead ----------
    old_sub = ("Roven is the hiring marketplace with receipts. Employers are "
               "identity-verified before they can post, every listing is a "
               "confirmed open role, and how they treat applicants goes on "
               "their permanent record.")
    new_sub = ("A recruiter costs thousands. Sponsored ads bill you whether "
               "you hire or not. Roven is free to post and charges one flat "
               "fee only when someone accepts your offer &mdash; and it is "
               "free for job seekers forever. Every employer is verified, "
               "every listing is a confirmed open role, and how employers "
               "treat applicants goes on their permanent public record.")
    if new_sub[:40] in h:
        skipped.append("hero subhead already updated")
    elif old_sub in h:
        h = h.replace(old_sub, new_sub, 1)
        done.append("hero subhead -> leads with the model")
    else:
        skipped.append("hero subhead not found - patch manually")

    # ---------- 4. honest stat strip ----------
    strip = ('<div class="hp-stats">'
             '<div class="hp-stat"><b>$0</b><span>TO POST A ROLE</span></div>'
             '<div class="hp-stat"><b>$0</b><span>FOREVER FOR JOB SEEKERS</span></div>'
             '<div class="hp-stat"><b>3 MIN</b><span>TO POST WITH AI DRAFTING</span></div>'
             '<div class="hp-stat"><b>30 DAY</b><span>CONFIRMATION CLOCK ON EVERY LISTING</span></div>'
             '</div>')
    if "hp-stats" in original:
        skipped.append("stat strip already present")
    else:
        anchor = None
        for cand in ('NOW LIVE · PHOENIX', 'NOW LIVE &middot; PHOENIX',
                     'FREE FOR JOB SEEKERS. ALWAYS.'):
            if cand in h:
                anchor = cand
                break
        if anchor:
            idx = h.index(anchor)
            # walk back to the start of that element's line
            start = h.rfind("<", 0, idx)
            start = h.rfind("\n", 0, start) + 1
            h = h[:start] + strip + "\n" + h[start:]
            done.append("stat strip added above the fold")
        else:
            skipped.append("STAT STRIP anchor not found - add manually")

    # ---------- 5. stale Phoenix ----------
    n = 0
    for a, b in [("NOW LIVE · PHOENIX", "NOW LIVE NATIONWIDE"),
                 ("NOW LIVE &middot; PHOENIX", "NOW LIVE NATIONWIDE"),
                 ("Live in Phoenix", "Live nationwide"),
                 ("NOW LIVE · PHOENIX ", "NOW LIVE NATIONWIDE ")]:
        if a in h:
            h = h.replace(a, b)
            n += 1
    if n:
        done.append(f"removed stale Phoenix-only copy ({n} spot(s))")
    else:
        skipped.append("no Phoenix-only copy found (already fixed?)")

    # ---------- 6. label the illustrative scorecards ----------
    tag = ('<div class="hp-example-tag">ILLUSTRATIVE EXAMPLE &middot; '
           'NOT A REAL EMPLOYER</div>')
    if "hp-example-tag" in original:
        skipped.append("example scorecards already labelled")
    else:
        count = 0
        # one label per scorecard, first occurrence only - inserting inside a
        # loop that re-searches the mutated string is how you write an
        # infinite loop, so this deliberately does a single pass each.
        for company in ("Meridian Field Services", "Copperline Dental Group"):
            idx = h.find(company)
            if idx == -1:
                continue
            start = h.rfind("<", 0, idx)
            if start == -1:
                continue
            line_start = h.rfind("\n", 0, start) + 1
            h = h[:line_start] + tag + "\n" + h[line_start:]
            count += 1
        if count:
            done.append(f"labelled {count} illustrative scorecard(s)")
        else:
            skipped.append("SCORECARDS not found - label them manually")

    # ---------- 7. ticker mount ----------
    if 'id="hp-ticker"' in original:
        skipped.append("ticker already present")
    else:
        m = re.search(r"</header>", h)
        if m:
            h = h[:m.end()] + "\n" + TICKER_HTML + h[m.end():]
            done.append("activity ticker mounted after </header>")
        else:
            skipped.append("TICKER: no </header> found - mount manually")

    # ---------- 8. homepage FAQ ----------
    if 'id="faq"' in original or "hp-faq-group" in original:
        skipped.append("homepage FAQ already present")
    else:
        if "hp-faq{" not in h:
            if "</style>" in h:
                h = h.replace("</style>", FAQ_CSS + "\n</style>", 1)
            elif "</head>" in h:
                h = h.replace("</head>", f"<style>{FAQ_CSS}</style>\n</head>", 1)
        m = re.search(r"<footer", h)
        if m:
            h = h[:m.start()] + faq_section() + "\n" + h[m.start():]
            done.append("homepage FAQ added (16 Q&A + FAQPage schema)")
        else:
            skipped.append("FAQ: no <footer> found - add manually")

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
    return h != original


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    args = ap.parse_args()
    path = os.path.join(args.site, "index.html")
    if not os.path.exists(path):
        sys.exit(f"index.html not found at {path}")
    bak = path + ".bak"
    if not os.path.exists(bak):
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        with open(bak, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"  backup written: {bak}")
    patch(path)
    print("\nReview index.html, then deploy. The ticker stays hidden until "
          "activity.json has 6+ real items - run refresh_activity.py to "
          "generate it.")


if __name__ == "__main__":
    main()

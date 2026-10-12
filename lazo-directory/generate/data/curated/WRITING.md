# Writing curated picks for a metro (JC-LAZO-CURATE-1012)

You are writing `generate/data/curated/<metro>.py` for one Lazo metro, from the candidate sheet produced by
`python generate/curate_sheet.py <metro>`. Use `generate/data/curated/phoenix.py` as the model for tone, length and
structure. The file must define `UPDATED = "<YYYY-MM-DD>"` and `CATS = {...}` with exactly these six keys:
`wedding-venues`, `wedding-photographers`, `wedding-videographers`, `wedding-planners`, `wedding-florists`, `wedding-djs`.

Each category is `dict(excluded=str, ask=[q1, q2, q3], picks=[...])`.

## The one rule
Every sentence in a blurb restates something the vendor's own site says, as shown on the sheet. Nothing inferred,
nothing generic. If the sheet does not say it, you do not know it. In particular:
- No ratings, review counts or "top-rated" / "award-winning" unless the sheet text literally says it.
- A dollar figure appears only if the sheet shows it (`$=[...]` or the PRICE PAGE text). Otherwise say "pricing on request" or "publishes pricing" and no number.
- `since=<year>` only when the sheet shows that year (`since=[...]` or in the text). `from_price="$1,250"` only when that figure is on the sheet.
- Town comes from the sheet's third field; if blank, do not name a town.

## Choosing picks (8 to 12 per category, aim for 12)
1. VERIFIED or CLAIMED vendors first, always.
2. Then vendors who are plainly wedding businesses (high `wed=`, low `off=`), say what they do, show work, and
   explain how they work (experience, approach, packages, pricing).
3. Spread across towns when quality is equal. Skip travel-from vendors, directories, aggregators ("find your venue
   and vendors here"), chains with a landing page per city, link pages, parked domains, and anything whose site is
   really about headshots, newborns, corporate video, podcasts, funerals, retail delivery, quinceaneras-only, etc.
4. A vendor may appear in two categories only if its site genuinely covers both (photo + video teams, planner + florist).
5. If a category has fewer than 8 plausible wedding vendors, use what is there (minimum 6) and say so in `excluded`.

## Writing
- `blurb`: two or three sentences, 150 to 420 characters, plain and specific. Name the person when the site does.
  Lead with what makes them distinct (years, approach, specialty, pricing transparency), then where they are based or
  what they cover. No marketing adjectives of your own ("stunning", "amazing"), no exclamation marks.
- `tags`: two to four short lowercase phrases, the distinct facts (e.g. "since 1995", "weddings only", "from $4,000",
  "husband and wife", "South Asian weddings").
- `excluded`: a short list of the kinds of listings you set aside, in words a couple would understand.
- `ask`: three questions a couple should put to every vendor of this type in this metro. Make at least one local
  (season, heat, snow, permits, venue rules) using the metro facts on the guide; the others practical.
- Vary the sentence openings across a category. Do not start every blurb with the vendor's name.

## Then
Run `python generate/curate_emit.py <metro>` and `python generate/curate_check.py <metro>` and fix every PROBLEM
the checker prints. Report the per-category counts and anything you were unsure about.

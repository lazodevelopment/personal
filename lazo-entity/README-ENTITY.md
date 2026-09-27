# ENTITY PACK — INSTALL (Friday batch 1)

1. ORGANIZATION SCHEMA → open generate\templates\home.html, paste
   org-schema-snippet.html contents inside <head>. (Verify sameAs URLs match
   your real handles first.)

2. TRADITION PAGE →
   Copy-Item lazo_tradition.html C:\Users\kurvh\lazo-directory\generate\templates\
   cd C:\Users\kurvh\lazo-directory
   python patch_build_tradition.py     (prints PATCHED)
   → page renders at /what-is-a-lazo/ on every build from now on, sitemap included.

3. BADGES → paste each snippet into that site's footer template, rebuild/deploy
   Atavia + ES per their own pipelines (their normal deploy rituals).

4. SOCIALS → run the checklist (~30 min, phone-friendly).

5. Everything site-side ships with today's post-recrawl build:
   python generate\build.py --tranche 4  →  python deploy\upload_r2.py
   Verify after: getlazo.com/what-is-a-lazo/ renders; view-source on homepage
   shows the ld+json block.

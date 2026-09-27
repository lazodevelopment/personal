# LAZO FAVICON — INSTALL

1. Copy these files into C:\Users\kurvh\lazo-directory\generate\static\
   (so they land at the SITE ROOT in dist/ — favicon.ico MUST be at /favicon.ico):
   favicon.ico, favicon-16.png, favicon-32.png, favicon-48.png,
   apple-touch-icon.png, icon-192.png, icon-512.png, site.webmanifest
   NOTE: if build.py copies static/ into an assets/ subfolder instead of dist root,
   also copy favicon.ico directly into dist\ after building (root placement is
   what Google reads first).

2. Add head-snippet.html contents to the base page template <head>
   (the template all pages extend — same file that holds the GA/meta tags).

3. Rebuild + deploy:  python generate\build.py --tranche 4  then  python deploy\upload_r2.py
   (rides along with the wave deploy — no separate push needed)

4. Verify: https://getlazo.com/favicon.ico renders the plum/gold knot in a browser.

5. Google refresh: search result favicons update on Google's own crawl cadence —
   typically days to ~2 weeks after the new icon is live. No action forces it,
   but a homepage Request Indexing in GSC nudges a recrawl.

Want Batul's exact mark instead? Put her square mark PNG anywhere and run:
   python favicon_make.py path\to\mark.png
then repeat steps 1–3 with the regenerated files.

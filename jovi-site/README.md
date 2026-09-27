# Jovi Health marketing site

Static site for jovihealth.com (temporary: the Cloudflare Pages `*.pages.dev` URL until the domain is bought).

- Pages are generated: edit `_src/build.py`, then run `python _src/build.py` from this folder. Do not hand-edit the `.html` files.
- `assets/js/pricing.js` is the membership quote engine. It mirrors `_computeQuote` / `_computePetQuote` in the Jovi app's Onboarding widget. If pricing changes in the app, change it here too (the clinic site has its own copy of the calculator as well).
- Design tokens match jovihealth.clinic (Sora + DM Sans, navy/mint/coral).
- Store links: `APP_STORE` / `PLAY_STORE` in `build.py` are placeholders until the app is listed.
- Legal pages link to the clinic site's copies.

Deploy (Cloudflare Pages, direct upload). PowerShell 5.1 has no `&&`, so chain with `;`:

    cd C:\Users\kurvh\jovi-site; python _src/build.py; npx wrangler pages deploy . --project-name jovihealth --branch main --commit-dirty=true

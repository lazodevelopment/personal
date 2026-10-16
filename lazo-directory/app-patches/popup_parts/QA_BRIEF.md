# Popup QA pass 2 (JC-LAZO-POPUP-1014) - brief for each tester

Jesse asked: check that everything works - buttons do what they are meant to, saving works, etc. You are testing
the Lazo couple and vendor dashboards (Couple v158 / Vendor v197, FlutterFlow custom widgets) after a rebuild of
every popup. You TEST and REPORT. Do not edit the masters, the patch files or the harness.

## The setup (already running)
- A debug dev server serves the real dashboards against an in-memory Firebase with seeded test data:
  `http://localhost:8790/?w=couple` (Avery & Jordan, Phoenix, wedding 2027-03-27, guests, vendors, threads) and
  `?w=vendor` (Golden Hour Studio, 4 inquiries, invoices, a review). `&mode=dark` for dark mode.
- June's import call (`juneImport`) returns canned data. Every other Cloud Function is unreachable, so actions that
  call one should fail GRACEFULLY: a clear inline message (or toast), the popup stays usable, no crash. Firebase
  Storage uploads and native file pickers cannot be driven here: note "not testable" and move on.
- You have your own headless Chrome. Driver: `node <scratch>/lz.mjs <cmd>` with env `CDP_PORT=<your port>`
  (and `LZ_VIEW=desktop` for the 1280x860 desktop view; default is a 375x812 iPhone).
  `<scratch>` = `C:/Users/kurvh/AppData/Local/Temp/claude/C--Users-kurvh-lazo-directory/b55c7a64-e6b6-478b-b1a7-f2d9fa8b7e7b/scratchpad`
  Commands: `open couple|vendor [light|dark]` (takes 1-3 min; reload = fresh data), `nodes [filter]`,
  `taptext "<label>" [n]`, `tap x y`, `fields`, `type <text>`, `key Enter`, `scroll x y dy`, `shot <file.png>`,
  `dump <firestore/path>` (e.g. `dump couples/c1/guests`, `dump couples/c1`, `dump inquiries/q0/invoices`,
  `dump vendors/ven1`), `errors` (console errors since the last call - run it after every action), `eval <js>`.
  Read the header comment of lz.mjs. Always `cd` to `<scratch>` first; prefix each call with `timeout 60`.
  Tips: `nodes` lists only what is on screen; scroll to reach more. To type, `tap` the field (from `fields`) first.
  Taps by label prefer exact button labels. Screenshots: read them with the Read tool to look at them.
- Source to understand intent: `C:\Users\kurvh\lazo-directory\app-patches\Couple_master_v158.txt` and
  `Vendor_master_v197.txt` (search for the popup function names). What each button should do is in the code.

## What to check for every popup in your area
1. It opens from its button, looks right (no overflow stripes, no clipped text, no double handles/close buttons),
   and closes (X, Cancel, tap outside).
2. Every button in it does what its label says. Fields accept input; the primary button disables/enables sensibly.
3. SAVING: after a save, `dump` the relevant path and confirm the exact fields were written with the values you
   entered (and nothing obviously wrong). Then confirm the dashboard shows the change (re-open, or read `nodes`).
4. Validation and errors: empty/invalid input, the failure path for actions that call a Cloud Function.
5. `errors` after each step: any red Flutter error (overflow, setState after dispose, null check, GlobalKey) is a
   finding, with the action that caused it.
Known and NOT to report: the GlobalKey error when the couple Account page opens (already filed); "client is offline"
from `_manageProSheet` (harness limit); Cloud Function calls failing (expected - only report if the UI handles it badly).

## Report
Write `C:\Users\kurvh\lazo-directory\app-patches\popup_parts\qa_<ID>.md`:
- A table: popup | what you did | result (PASS / BUG / NOT TESTABLE) | evidence (dump excerpt, error text, screenshot path).
- Then each BUG in detail: steps, expected, actual, and the suspected code (function name + what looks wrong).
Save screenshots under `<scratch>/qa/<ID>/`. Keep going after a bug; cover your whole area. Your final reply:
counts (pass/bug/not testable) and the bug list in one line each.

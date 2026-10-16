# Vendor v197 final pre-ship check (qf, CDP 9342, phone 375x812)

Build under test: harness `lib/custom_code/widgets/vendor.dart` (byte-identical to `Vendor_master_v197.txt`), dev server 8790,
page reloaded 2026-10-15 ~17:35 after the compiler went idle. Screenshots: `<scratch>/qa/qf/`.
Note: `qq.sh` runs `clr.mjs`, which empties `window.__lz` at the start of every call, so console checks were done inside the same call as the action.

**Result: 10 PASS, 1 FAIL (item 8).**

| # | check | result | evidence |
|---|---|---|---|
| 1 | Hello sheet after a failed couple search | PASS | Today card and the sheet both say "Couldn't load couples right now. Check your connection and try again soon." The sheet still shows "0 couples / 10 hellos left this week". `01_hello_sheet.png` |
| 2a | Connect Square failure | PASS | toast "Could not start Square connect." `02b_square.png` |
| 2b | Payment plan Send failure | PASS (minor) | total 3000, 50/50, Send 2 payments: inline "Could not create the plan." (red box), sheet stays usable. Minor: the error sits at the bottom of the scroll area under the footer, so you have to scroll to see it (`02d_plan_sent.png` vs `02e_plan_err.png`) |
| 2c | Contract Generate failure | PASS | starter > add > review > Activate > all fields filled > Generate contract: inline "Could not generate - try again." and the form stays filled. `02k_generate.png` |
| 3 | Proposal card money | PASS | price 1250.50: card "$1,250.50 · Awaiting reply", message "...The Verse - 8 hours, $1,250.50." Dump `price:1250.5, status:"sent"`. `03c_sent.png` |
| 4 | Grid button hidden with a thread open (phone) | PASS | no floating button in Maya & Leo, Nora & Eli or Tess & Ava. Send button is clear. `04_thread.png`, `11a_reply.png` |
| 5 | "RenderFlex overflowed by 23 pixels" on thread open | PASS (no longer logs) | Cleared `__lz`, then opened Maya & Leo, Nora & Eli and Tess & Ava. Also replied, tagged, sent a proposal, marked paid and added a task. Zero overflow, error or exception lines. Checked that the hook captures `console.log`. So there is no "relevant error-causing widget" text to report for the 23 px overflow. Note: the harness `FlutterError.onError` (main.dart l.79) prints only `exceptionAsString()` and a stack, never the "relevant error-causing widget" block, so a future overflow will not show it either |
| 6 | Dark mode brand preview | PASS | Dark > Your brand > Blush: the preview "Pay $500" button is blush (#E7C6C0) with plum text on a plum (#52284F) card. `06b_blush.png`. Cancelled, `brand` still null, switched back to Light |
| 7 | Default retainer, flat | PASS | Empty amount + Save shows inline "Enter the retainer amount, or pick another option." and nothing is written (`retainerMode`/`defaultRetainer` undefined, `07d_empty.png`). With 750 + Save: `retainerMode:"flat", defaultRetainer:750, retainerPercent:50` |
| 8 | Profile editor save bar / ListTile warnings | **FAIL** | No ListTile warnings while scrolling the whole editor (top to Reviews, past the switch tiles): `__lz` stayed empty. "Save profile" is not under the floating button. **But the save bar is broken on the phone:** `FLUTTER ERROR: A RenderFlex overflowed by 7.0 pixels on the right.` as soon as the editor opens. A yellow/black overflow stripe shows. "Profile strength" is drawn one letter per line, the "Next: ..." line is gone, and "Save profile" is clipped to "Save profi". `08a_editor.png`, `08b_editor_bar.png`, `08d_scrolled.png` |
| 9 | Preferred vendor "Added" | PASS-by-code | Only `vendors/ven1` is seeded, and search leaves out your own doc, so "Golden" returns "No vendors start with that name." (`09b_search.png`). Code (`resultRow`, vendor.dart ~l.7128): `already = _epPreferred.any(p.placeId == r.placeId)` shows a green "Added" label, and tapping it toasts "<name> is already on your list." `_epPreferred` loads `preferredVendors` maps with their `placeId` (l.6436), so a saved vendor matches |
| 10 | Invoice due date from the calendar | PASS | Pick a date > Oct 30 > OK > Send $450: `dueDate:"2026-10-30T12:00:00.000"`, which is local noon (`createdAt` is printed in the same local format, 17:48). `10c_filled.png`, `10d_sent.png` |
| 11 | Regression sweep | PASS | Reply in open lead q0: `status:"responded"`, `respondedAt` set, bubble shown. Tag "Referral": q0 `tags:["referral"]`, `tagPalette:["referral"]`, chip shown. Task "Confirm shot list", Tomorrow: `tasks/{id}: dueAt 2026-10-16 12:00, assignedTo:"vendor", done:false`, "1 open task" strip. Mark paid (Check) on the $1,300 balance: `i1 status:"paid", paidVia:"Check", paidAt`, q2 `invoiceStatus:"paid"`. Scheduler: In person + Save writes `scheduler{enabled, hours mon-fri 09-17, types:[{mode:"in_person"}], updatedAt}`. Widgets sheet opens, Fold, scroll and Close work. `errors` showed no new console errors anywhere except item 8 |

## FAIL in detail

**F1 (item 8) - Profile editor save bar overflows on the phone (RenderFlex overflowed by 7.0 pixels on the right).**
- Steps: phone, open the floating grid button, tap Edit profile.
- Expected: a full-width bar with the strength ring, "Profile strength / Next: ...", Discard and Save profile.
- Actual: the bar stops about 80 px short of the right edge. Its Row has about 251 px for about 258 px of fixed children (ring 42 + gap 12 + gap 10 + Discard about 72 + gap 4 + Save profile about 118), so the `Expanded` text column gets 0 px wide. "Profile strength" stacks one letter per line, the bar grows tall, and Save profile is clipped.
- Code: `_epSaveBar()` (vendor.dart l.9287). The new right padding `EdgeInsets.fromLTRB(14, 0, MediaQuery.of(context).size.width < 1100 ? 80 : 14, 14)` (l.9321) moves the bar out of the floating button's way, but the Row (l.9330) no longer fits on 375 px.
- Possible fixes: hide the floating button while the editor is open (as the thread view does with `!_showInbox`) and keep the 14 px padding. Or, on narrow widths, drop the "Profile strength" column or move the buttons to a second line.
- The harness prints no "relevant error-causing widget" line (see item 5 note). The widget was found from the on-screen stripe, the node positions (bar 14-295 px) and the width arithmetic, which comes to exactly 7 px.

## Other observations (not in the list)
- Payment plan: the inline error is below the fold (see 2b).
- Invoice sheet: after I typed into the title and line fields, the saved invoice read `title:"Wedding balanceAlbum"` with one line `"Wedding balanceAlbum" $450`. This is probably my typing landing in a prefilled field ("Wedding balance") through the driver, not a confirmed bug.
- Inbox list preview for Maya & Leo still showed the couple's first message after my reply (list snippet not refreshed).

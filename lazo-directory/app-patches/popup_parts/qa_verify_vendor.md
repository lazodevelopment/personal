# Vendor v197 fix verification (qv, CDP 9342, phone 375x812)

Status: DONE. Totals: 15 PASS, 2 FAIL (9 hello sheet, 11 Square) of the 17 items; 7 new findings (N1-N7). Harness fix CONFIRMED. Screenshots: `<scratch>/qa/qv/`.

## Harness check (first)
FieldValue writes now work: adding tag "Hot lead" to q0 wrote `tags:["hot lead"]` and `vendors/ven1.tagPalette:["hot lead"]`;
thread open wrote `vendorActiveAt/vendorLastReadAt/seenByVendorAt` (serverTimestamp); a reply wrote `respondedAt` and the message doc.
New harness/driver gaps this run: (a) the machine is heavily loaded (python/chrome processes at high CPU) - every CDP call takes 10-30 s;
(b) each driver session that sets its own viewport override and then closes makes the page jump back to 1264 px, which triggers
Flutter "Semantics node map was inconsistent after update" dumps (thousands of console lines) that make the next `Runtime.enable` hang.
Fix used: keeper holds the phone viewport, driver runs with NOEMU=1, and `Runtime.discardConsoleEntries` before every call
(`<scratch>/qq.sh`, `qv.mjs` = q.mjs + `hwheel`/`drag`).

## Results (filled as I go)
| # | check | result | evidence |
|---|---|---|---|
| 1a | reply in booked thread q2 | PASS | after "See you on the big day!" q2 `status:"booked"`, `respondedAt` set, header still "Booked"; `10_q2_reply.png` |
| 1b | proposal in booked thread q2 | PASS | after Send proposal q2 `status:"booked"`; proposal doc `price:1250.5,status:"sent"` |
| 1c | reply in open lead q0 | PASS | q0 `status:"new"` -> `"responded"`, `respondedAt` set; card moved New -> Talking; `06_q0_reply.png` |
| 7 | proposal $1,250.50 | PASS | Their view `$1,250.50` (`11_proposal.png`); message "...The Verse - 8 hours, $1,250.50. It's just above." |
| 8 | tag > 24 chars / normal tag | PASS | 35-char tag: inline "Could not tag it: Tags can be up to 24 characters - try a shorter one.", sheet stays open, nothing written (`04_tag_long.png`); "Hot lead" saved as above (`05_tag_ok.png`) |
| 9 | hello failure copy | PASS | Today card: "Couldn't load couples right now. Check your connection and try again soon." (`00_open.png`) |
| 5 | invoice line with amount, no label | PASS | Title "Extras", lines "Album" $400 + unlabeled $300: total and button "Send $700"; saved `lineItems:[{label:"Album",amount:400},{label:"Extras",amount:300}], total:700, status:"sent"`; q2 `lastInvoiceId`, `invoiceUpdatedAt`; `14_inv_filled.png`, `15_inv_sent.png` |
| 6a | mark paid with another invoice open | PASS | Extras marked paid by Zelle: invoice `status:"paid", paidAt, paidVia:"Zelle"`; q2 `invoiceStatus` stays `"sent"` (Balance $1,300 still open); `17_paid.png` |
| 6b | void asks first, rollup | PASS | trash icon -> "Void this invoice?" with Keep it / Void invoice; Keep it left i1 `sent`; Void wrote i1 `status:"void", voidedAt`; q2 `invoiceStatus` -> `"paid"` (remaining Retainer + Extras both paid); `18_void_confirm.png`, `19_voided.png` |
| 2a | drop non-booked lead on Delivered | PASS | Tess & Ava (q3, new) -> toast "Mark them booked first - delivery comes after the booking.", q3 unchanged; `21_drop_delivered_new.png` |
| 2b | drop lead on Lost | PASS | Priya & Sam (q1) -> "Mark this lead lost?" (Keep it / Mark lost) -> q1 `status:"lost"`, card under Lost; `22_drop_lost.png`, `23_lost.png` |
| 2c | drop booked lead on Delivered | PASS | Nora & Eli (q2) -> `deliveredAt` written, status stays `booked`, card under Delivered; `24_deliv.png` |
| 4 | mark booked: toast only on success | PASS | drag Maya to Booked -> "Mark as booked" -> q0 `status:"booked", bookedAt`; June banner "Maya and Leo booked you..." + confetti (`26_booked_toast.png`). Code: `_needsBooked` toasts only `if (go && await _setStatus(...))` and `_setStatus` returns bool |
| 3 | release with cancel reason | PASS | drag booked Maya to Lost -> "This couple is booked" release sheet -> "The couple cancelled" -> Release: q0 `status:"closed", unbookReason:"couple_cancelled", unbookLabel, unbookedAt`; card shows under **Lost (2)**; `27_release.png`, `28_released.png` |

(Items 2-4 were driven at desktop width (1280) because the phone board shows one column at a time and a drag cannot cross columns; the logic is the same.)
| 17 saved replies | New saved reply "Availability" with {couple}/{date}/{vendor} | PASS | `vendors/ven1.savedReplies:[{title:"Availability",text:"Hi {couple}, {date} is open with {vendor}."}]`, listed in the sheet; `29_saved_reply.png` |
| 17 tasks add | Add a task "Send the timeline", Tomorrow, Me | PASS | `inquiries/q2/tasks/oiPC..: {title, dueAt:2026-10-16, assignedTo:"vendor", done:false, createdAt, createdBy:"v1"}`; "1 open task" strip; `30_task.png` |
| 17 tasks edit | tap task -> Edit task (prefilled), title + " and shot list", Next week, Save | PASS | `title:"Send the timeline and shot list", dueAt:2026-10-22`; `31_task_edit.png` |
| 17 tasks delete | Edit task > Delete > "Delete task" confirm | PASS | tasks collection `{}` |
| 17 payment plan | Set up a payment plan: total 3000, 50/50 (1500 now + 1500 4/13/2027), Send 2 payments | PASS (opens + validates; send fails at the function as expected) / minor FAIL on copy | Sheet opens immediately now (was a hang). `planCreate` fails -> inline error reads just **"internal [0]"** - `_paymentPlanSheet` uses `err = e.message ?? ...` instead of `_errText(e)`. Same class as item 11. `32_plan.png`, `33_plan_filled.png`, `34_plan_sent.png` |
| 17 questionnaire editor | Send a questionnaire > Start from the Lazo set > Save questionnaire | PASS | `vendors/ven1/questionnaireTemplates/OEWm..: {title:"Wedding Day Details", questions:[12], type:"custom", createdAt, updatedAt}`; `36_quest_editor.png` |
| 17 questionnaire send | reopen > tap "Wedding Day Details" | PASS | `inquiries/q2/questionnaires/t8PI..: {type:"custom", title:"Wedding Day Details", vendorName:"Golden Hour Studio", questions:[...]}`; thread card "WAITING", side panel "Questionnaire - Waiting on them"; `39_quest_sent.png` |
| 17 contract from starter | Send a contract > "Add a contract template first" > Use a Lazo starter > Wedding Photography Agreement > Add to my templates; Send a contract again > "One quick review first" > Activate and continue > values form, filled all 12 > Generate contract | PASS (handled) | `vendors/ven1/contractTemplates/Rxms..: {name:"Wedding Photography Agreement", status:"draft", source:"starter", body:...}`; values form counts "12 to fill" -> "3 fields left" -> "All filled in"; Generate fails at the function with inline **"internal [0]"**, form stays filled and usable (raw code again - see N3). `40_contract.png`, `43_review.png`, `44_values.png`, `46_values_filled.png`, `47_generate.png` |
| 17 edit a sent message | long-press own bubble > Edit > append " Can't wait." > Save | PASS | message `text:"See you on the big day! Can't wait.", editedAt` set; bubble shows "1:38 PM · edited"; `48_edited.png` |
| 17 mark booked (tools gate) | Tess & Ava (new) > Studio tools > June Sneak Peek (locked) > "Sneak Peek opens once they're booked" > Mark booked | PASS | q3 `status:"booked", bookedAt`; toast "Booked. Delivery tools are open for this thread." + June banner; `50_needsbooked_toast.png` |
| 10 | scheduler save | PASS | Mon end 5:00 pm -> 12:00 pm (time picker) + "another window" 1:00-5:00 pm; Save -> toast "Scheduler is live at https://meetlazo.com/book/ven1"; dump `scheduler.hours:{mon:[{"0":"09:00","1":"12:00"},{"0":"13:00","1":"17:00"}], tue..fri:[{"0":"09:00","1":"17:00"}], sat:[], sun:[]}`, plus slotMinutes/buffer/notice/types/updatedAt. Reopen shows Mon 9:00 am-12:00 pm and 1:00 pm-5:00 pm. `55_sched_saved.png`, `56_sched_reopen.png` |
| 14 | bug report build id | PASS | sheet reads "We attach your plan, build 197, ..." (`57_bug.png`); sent ticket `context.build:"JC-LAZO-VDASH-1014-197"`, category/subject/severity/view correct |
| 11c | Claude/ChatGPT link failure | PASS | inline "Could not create the link: Something went wrong on our side. Try again in a moment." (`59_mcp_fail.png`) |
| 17 team invite | Team > assistant@goldenhour.com > Create invite | PASS | `vendorInvites/UnY6..: {vendorId:"ven1", email, role:"manager", code:"9XKH29", status:"pending", createdBy:"v1", createdAt}`; row "Waiting for them · code 9XKH29" with Copy code / Cancel invite; `60_team.png` |
| 17 lead form | Account > Lead form for your website | PASS | sheet opens (was a create-loop before); `vendors/ven1.leadForm:{key:"85QC...", enabled:true, redirect:"", thanks:"", createdAt}` created once; thank-you message typed + Done -> `thanks:"Thanks! We will reply within a day."`; `61_leadform.png` |
| 11a | Connect Square failure | **FAIL** | toast reads just **"internal [0]"** (`63_square_toast.png`, `66_money.png`). `_connectSquare` still does `on FirebaseFunctionsException catch (e) { _toast(e.message ?? 'Could not start Square connect.'); }` - needs `_lzFnMsg(e, ...)` / `_errText(e)` like Whop and MCP |
| 11b | Set up Whop failure | PASS | toast "Could not reach Whop: Something went wrong on our side. Try again in a moment." (`64_whop.png`) |
| 17 default retainer | Money > Retainer, invoiced automatically > A flat amount 750 > Save | PASS (opens and saves) / old bug remains | sheet opens now (was "client is offline"); toast "Saved - $750 at signing."; dump `retainerMode:"flat", defaultRetainer:750`. Still: empty amount saves `defaultRetainer:0` with toast "Saved - $0 at signing." (qa5 bug 6, unchanged) |
| 13 | Who I work with From 200 / Up to 50 | PASS | Save -> "Saved - your leads are graded against it from now on."; dump `prefs:{guestMin:50, guestMax:200, ...}` (swapped to 50-200); `70_prefs_saved.png` |
| 15a | FAQ card copy | PASS | Profile editor card: "...shown on your profile. Up to 15." (`72_faq_card.png`); `_epAddFaq` limit toast "Up to 15 FAQs on a profile." |
| 15b | gallery limit message | PASS (code; file picker not drivable) | `_epUploadGalleryPhotos` at the cap now toasts "Your gallery holds 10 photos. Remove one to add another." (admin: "Gallery is at its 30-photo limit.") - no more "Unlimited gallery is coming with Lazo Pro". Card reads "0 of 10". Cap itself is still 10 for a Pro vendor (`_epGalleryCap => _isAdminUser ? 30 : 10`) - copy is now honest, cap unchanged |
| 9b | hello SHEET after failed load | **FAIL** | card is fixed, but tapping it opens the sheet with "0 couples / 10 hellos left this week / Nobody to greet right now. New couples set their date every week - check back." (`73_hello_sheet.png`). `_helloSheet` reads `_helloCache['matches']` only and never checks `_helloCache['error']` (set by `_loadHellos` on failure) |
| 12 | errors visible on phone | PASS (code; failure path no longer reachable) | Report a bug, Support and the scheduler now call `_toast(err)` in their catch as well as setting the inline error; `_toast` -> `_lzToastOver` draws an Overlay toast above the open sheet (root overlay, bottom of screen), so it shows without scrolling. Could not trigger live: with the harness fixed all three writes succeed (bug ticket saved, scheduler saved) |
| 16 | dark mode: Your brand swatches | PASS | Account > Appearance Dark > Your brand: Blush, Ivory, Lilac, Champagne, Terracotta, Sage, Sky show their real light colours; selected Plum / Navy and Gold / Blush carry a clear gold ring (`75_dark_brand.png`, `76_dark_brand_pick.png`). See N5 for the preview. Switched back to Light afterwards; nothing saved |

## Summary per item
1 PASS · 2 PASS · 3 PASS · 4 PASS · 5 PASS · 6 PASS · 7 PASS (preview + message; see N1 for the thread card) · 8 PASS · **9 FAIL** (card fixed, sheet not) ·
10 PASS · **11 FAIL** (Square only; Whop + MCP pass) · 12 PASS (code + overlay toast; failure not reachable live) · 13 PASS · 14 PASS · 15 PASS · 16 PASS · 17 PASS (every listed save writes the right fields).

## Fails in detail
**F1 (item 9) - Hello sheet still says "Nobody to greet right now" after a failed load.** Steps: Today > Say hello first card (it now reads
"Couldn't load couples right now...") > tap. Actual: sheet "0 couples / 10 hellos left this week / Nobody to greet right now...". Code:
`_helloSheet` builds from `(_helloCache['matches'] ?? [])` and never looks at `_helloCache['error']`; show the error copy + a Retry
(`_loadHellos(vendorId, force: true)`) when it is set.

**F2 (item 11) - Connect Square toasts "internal [0]".** `_connectSquare`: `on FirebaseFunctionsException catch (e) { _toast(e.message ?? 'Could not start Square connect.'); }`.
Use `_lzFnMsg(e, 'Square didn't answer - try again in a minute.')` (as `_errText` does for Whop/MCP).

## New findings (not in the list)
- **N1 (LOW, money) - Proposal card in the thread still rounds cents.** After sending $1,250.50 the proposal strip card reads **"$1251 · Awaiting reply"** (no cents, no thousands comma) while the preview and the message say $1,250.50. Seen on phone and desktop (`15_inv_sent.png` nodes, `41_contract_values.png`). Same `_invMoney`/round pattern in the proposals strip.
- **N2 (LOW) - Payment plan send error is raw "internal [0]".** `_paymentPlanSheet` `on FirebaseFunctionsException catch (e) { err = e.message ?? ... }` - use `_errText(e)`. (`34_plan_sent.png`)
- **N3 (LOW) - Contract "Generate contract" error is raw "internal [0]".** Values form handles the failure (form stays filled) but the inline text is the bare code (`47_generate.png`). Same fix.
- **N4 (LOW, phone) - Thread open still logs `A RenderFlex overflowed by 23 pixels on the right`** (qa4 B1), every time a thread opens on the 375-wide phone (2-4x per open, also on reply). Not visible on screen. On one occasion it was followed by `Bad state: Semantics node map was inconsistent after update` dumps when the viewport changed (that part is likely the harness viewport flip).
- **N5 (LOW, dark) - Brand preview still remaps the accent.** In dark mode with Blush accent the preview's "Pay $500" button renders dark plum, not blush (`76_dark_brand_pick.png`). `_brandSheet` preview still uses `_lzBg(pCol)` (l.23305), `_lzFg(aCol)` (l.23321), `_lzBg(aCol)` (l.23344); the swatches were fixed but the preview should use the raw colours too.
- **N6 (LOW) - Floating grid button covers the thread Send button on phone** (bottom-right, `06_q0_reply.png`, `17_paid.png`): the round FAB sits on top of the paper-plane send button.
- **N7 (LOW) - Flat retainer still saves $0** (qa5 bug 6 unchanged): A flat amount with an empty field > Save -> `defaultRetainer:0`, toast "Saved - $0 at signing.".
- Minor observations: the contract values form leaves "Your business" and "Venue" empty although the vendor name and the thread venue (Desert Botanical Garden) are known; the scheduler accepts overlapping windows (adding a window on Mon gave 9-5 and 1-5 until edited); Task edit still has Delete where Cancel would be (qa4 B10).

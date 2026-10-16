# Couple v158 FINAL pre-ship check (phone 375x812, CDP 9341)

Tester: final-couple. Fresh load of `?w=couple` after the final recompile (the first load hung on the DDC bootstrap and was reloaded; r_couple.dart dated Oct 15 16:33).
Screenshots: `<scratch>/qa/final/` (scratch = C:/Users/kurvh/AppData/Local/Temp/claude/C--Users-kurvh-lazo-directory/b55c7a64-e6b6-478b-b1a7-f2d9fa8b7e7b/scratchpad).
Driver: qv.mjs through q41.sh (same as qq.sh, port 9341), keep.mjs holding the phone viewport, NOEMU=1. `errors` was run after every step.

## Summary
**All 6 items PASS. No new console errors.**

## Results

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Vendor team month road, Overdue column with 3+ categories | PASS | team1.png: "Overdue" shows "Photo", "Video", "+7 more" (9 overdue categories). "Oct 26" shows 2 rows and "+2 more". No stripe. Console: 0 lines matching overflow/RenderFlex after opening Vendor team |
| 2a | Day-of timeline: remove a moment, then Undo | PASS (app). The harness is slow to show it | The "Moment removed. Undo" toast shows on top of the open Day-of timeline sheet (tl_removed.png). I removed Ceremony and Cocktail hour and tapped Undo each time. Right after Undo, the collection dump did not list them yet, but doc reads `couples/c1/dayof/d1` = `{time:"16:00",label:"Ceremony"}` and `d2` = `{time:"16:45",label:"Cocktail hour"}` showed both had been written back. Dinner (d3) had no Undo (the toast expired) and stayed `null`. A few steps later the collection lists d1 and d2, and the Day-of card shows "4:00 PM Ceremony" and "4:45 PM Cocktail hour" again (dayof_after_add.png). The website publish mirror also had them. The delay is fake_cloud_firestore 4.3.0: `delete()` removes the doc node from the parent tree and `set()` on the same ref writes docsData without putting it back at once. This explains the "restore FAIL" in qa_verify_couple 7a; the app code is fine |
| 2b | Shopping: hold to remove, then Undo | PASS (same harness delay) | Hold on "Sparklers" shows the "Removed. Undo" toast (shop_removed.png). After Undo, `couples/c1/shopping/s2` = `{name:"Sparklers",bought:false,est:60,order:2}`. The later collection dump lists s0, s1 and s2 |
| 3 | Marriage license window | PASS | dayof1.png: "Apply any time before Mar 28, 2027". No "Mar 28 and Mar 28" |
| 4 | Day-of bottom vs Ask June bar | PASS | dayof_bottom.png: scrolled to the end, "Tap to edit · hold to remove" sits under the timeline card, clear of the Ask June bar |
| 5 | Toast over popup, plus the object.dart assertion | PASS, and the assertion did NOT fire | Partner > Invite my partner (jordan@example.com, code HLRS5H) > Copy code: "Code copied ✓" shows over the Plan together sheet (codecopied.png; the clipboard permission was granted to the harness Chrome first). I checked the console for `object.dart`, assert, error and exception after: this toast, the Undo toasts, the website editor "Our story in dates > Add a moment" sheet closing after Save, and the Day-of "Add a moment" sheet closing. Every check was empty |
| 6a | Widgets sheet | PASS | "Your widgets" with Countdown and the Phoenix weather widget (widgets.png), no errors |
| 6b | Import vendors: review, then Done | PASS | Account > Switching from The Knot or Zola > Zola > Booked vendors > Read my list returned the canned review: 3 rows, with the venue-replacement note (imp_review.png). "Add 2 to my team" showed "2 vendors on your team". Writes: `plan/wedding-videographers:{status:"booked",vendorName:"Atavia Weddings",vendorId:"ven1",budgetActual:3200,source:"import",...}` and `plan/wedding-venues:{vendorName:"The Farm at South Mountain",budgetActual:9500,budgetPlanned:12000,...}`. Done closed the sheet |
| 6c | Add guest, then save | PASS | "Final Tester", Friends > Add guest wrote `{name:"Final Tester",group:"friends",side:"both",rsvp:"pending",plusOnes:0,...,createdAt,updatedAt}`. The row "Final Tester · Pending" shows in the list |
| 6d | Edit website, then publish | PASS | Partner name changed to "Jordyn", plus a story moment "First trip". Publish changes opened "Your website is live" (web_pub.png). `weddingSites/avery-and-jordan.names:"Avery & Jordyn"`, `milestones:[{title:"First trip",...}]`, plus the timeline and vendorTeam mirrors |
| 6e | Account > Contracts | PASS | Opens "Your contracts / Every signed agreement, kept for you." with the empty state (contracts.png) |

## Notes (not failures)
- The machine is very slow: every driver call takes 30-120 s, so the 6 s Undo toast can only be tapped inside the same multi-step call as the remove.
- Re-testing Undo in this harness: read the restored doc by its own path (`dump couples/c1/dayof/d1`). The collection dump can lag right after a delete followed by a re-create.

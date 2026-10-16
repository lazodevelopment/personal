# QA pass 2 - qa2 (couple dashboard, phone 375x812)

Area: wedding website editor, chapters, registry, live share sheet, budget, vendor team / wanted vendors, Browse + vendor sheet + inquiry + refine + saved, shopping list, dream board.
Screenshots: `C:/Users/kurvh/AppData/Local/Temp/claude/C--Users-kurvh-lazo-directory/b55c7a64-e6b6-478b-b1a7-f2d9fa8b7e7b/scratchpad/qa/qa2/`. The machine crashed twice during the pass, so the data was reseeded twice. Every save below was checked with `dump` after the reseed it happened in.

Harness notes (not counted as widget bugs):
- Opening any popup logs `FLUTTER ERROR: Bad state: Semantics node map was inconsistent after update:` with no stack. A viewport switch also triggers it. It comes from the web engine's forced semantics tree in the harness, not from a popup.
- With semantics on, Flutter treats the app as `accessibleNavigation`, so a SnackBar with an action ("Removed Amazon. / Undo") never times out. It followed me across every view.
- The couple harness seeds NO `vendors` docs (`seed_more.dart` seeds `vendors/ven1` only for `?w=vendor`). Browse shows "No vendors here yet" and Saved vendors is empty, so the vendor profile sheet and the inquiry composer cannot be reached.
- Native file pickers and Storage uploads (chapter photos, board Photo) are not testable here.
- `ListTile background color or ink splashes may be invisible` (a debug assertion) showed up once while I was moving between Website, Registry and Shopping. I could not pin it to a popup in my area.

## Results

| popup | what I did | result | evidence |
|---|---|---|---|
| `_budgetSheet` | Home > BUDGET tile; layout, X | PASS | budget1.png |
| `_setBudgetSheet` | pencil; `abc` (Save disabled, aria-disabled=true); `42,500` > Save budget | PASS (write) | `couples/c1.budgetTotal: 42500` |
| `_budgetSheet` after a total change | the open sheet still shows "of $38,000" | **BUG 1** | BUG_budget_stale.png |
| Vendor team view (month road) | opened Vendor team | **BUG 2** | team.png, `RenderFlex overflowed by 19 pixels / 5.0 pixels on the bottom` |
| `_editWantedSheet` | Live Band + Rentals off (count 15 > 13), booked Photographer can't be turned off, Save; reopen, toggle one back on (14), X (no write), reopen + Save | PASS | plan: `wedding-rentals {"status":"skipped"}`, `wedding-bands` skipped > `needed`; view "The 14 you said you need" |
| `_editVendor` | Videographer: name `Reel Love Films`, Budget `3,250`, Spent `1500`, Save | **BUG 3** | `"budgetPlanned":null` (was 3000), `"vendorName":"Reel Love Films","budgetActual":1500` |
| `_editVendor` | Cancel after typing (no write); Budget `3250`, Save | PASS | `"budgetPlanned":3250`; row "Reel Love Films · $3250" |
| Website view | opened Website from the Home tile | **BUG 4** | `Multiple widgets used the same GlobalKey. [GlobalKey#c09b2] was used by 2 widgets: KeyedSubtree-[GlobalKey#c09b2], Center-[GlobalKey#c09b2]` |
| `_editWebsite` open, close, discard | Edit; Cancel > "Discard your changes?" > Keep editing (stays); Cancel > Discard changes (closes, nothing written) | PASS | discard.png; dump unchanged |
| `_editWebsite` validation | cleared both names > Publish: "Add at least one name - it's the title of your site." and the dialog stays | PASS | noname.png |
| `_editWebsite` fields + design | template Dune (palette auto `golden`), story typed via the "Your story" jump chip, Publish changes | PASS (write) | `template:"dune", palette:"golden", story:"We met at ASU in 2019."`; venue/times prefilled from the plan |
| `_editWebsite` names | Your name `Alexandra`, Publish ("Alexandra & Jordan"), then Edit > Publish changes with no edits | **BUG 5** | BUG_names_split.png: the site title became "Alex & ra & Jordan" |
| `_editWebsite` after publish | the "Your website is live" share sheet never opens; no activity row; no error | **BUG 6 (check on device)** | `couples/c1/activity` = {}, `weddingSites/.../playlist` = {} |
| `_siteLiveShareSheet` (share icon on Website) | opens; Copy link > "Copied" + "Link copied"; Instagram opens instagram.com; Done | PASS | share.png (Facebook not driven: it opens an external tab) |
| `_chaptersSheet` | empty state, Done | PASS | chapters.png |
| `_addChapterDialog` | Publish disabled until a title; "The honeymoon" + story > Publish chapter; tap the row > Edit chapter (prefilled) > Save; delete > "Delete this chapter?" > Keep (kept) > Delete chapter | PASS | chapters dump: title/text/dateIso/photos written, then title "The honeymoon in Lisbon", then `{}`; photos NOT TESTABLE (picker) |
| `_addRegistryLink` | Add registry disabled while empty; `notaurl` > "That doesn't look like a web address."; `amazon.com/wedding/registry/avery-jordan-2027` (detects "Amazon", adds https://) | PASS (couple write) | `couples/c1.registryLinks:[{"label":"Amazon","url":"https://amazon.com/wedding/...","store":"Amazon"}]` |
| registry > website sync | `weddingSites/avery-and-jordan.registryLinks` stays `[]`; the sheet sits on its busy button for about 10 s before closing | **BUG 6 (same)** | dump after 45 s+ |
| `_editRegistryNote` | "Your presence is the gift." > Save note | PASS (couple) / site not synced (BUG 6) | `couples/c1.registryNote` set; site `registryNote:""` |
| Remove registry + undo toast | Remove > row gone; the "Removed Amazon." toast came about 20 s later | PASS (write) / slow (BUG 6) | `registryLinks: []` |
| Copy guest link | no toast at all in 12 s (screenshots at 4/8/12 s) | BUG 6 (same) | cg4/cg8/cg12.png |
| `_editShopItem` add | Card box, qty 2, About `12.50`, Ceremony, link `etsy.com/listing/123`, note | **BUG 7** | `"est":1250`; header "about $1355 still to spend" (BUG_shop_decimal.png); link saved as `https://etsy.com/listing/123` |
| `_editShopItem` edit | tap a name > Edit item (prefilled); empty name disables Save; qty 3, About 40, Save | PASS | `s0: {"name":"Card box","qty":3,"est":40,"cat":"reception"}` (see minor note) |
| shopping "bought" circle | tapped | PASS | `bought:true, boughtAt` set; "2 of 4 bought" |
| `_bdAddNote` | Add disabled until text; green paper; Add note; Edit (prefilled) > Save | PASS | `board/main.items[0] {"kind":"note","color":"E7EFE6",...}`, text updated |
| `_bdCommentSheet` | Send with empty text does nothing; typed comment > Send; field clears; "1 comment" badge | PASS | `comments:[{"by":"c1","ini":"A","name":"Avery","text":"Love this - and no tall centrepieces"}]` |
| `_bdAddSwatch` | hex `8A9A5B` + "Dusty sage" (preview updates); then hex `zz12` > Add color | PASS (minor note) | `{"kind":"swatch","color":"8A9A5B","text":"Dusty sage"}` |
| `_bdAddLink` | Pin it disabled while empty; `example.com` > the unfurl has no image, so it pins a note | PASS (minor note: placement) | `{"kind":"note","text":"Example Domain","src":"https://example.com"}` |
| `_refineSheet` | Browse > All vendors: $2-5k, LGBTQ+ and Top rated on > "3 filters on", Clear all appears; Show vendors > field "3 filters"; reopen > Clear all > "All vendors" | PASS | refine.png, refine2.png |
| `_vendorSheet` (Save / Check your date / We already hired them) | - | NOT TESTABLE (no vendor docs in the couple harness) | Browse: "No vendors here yet" |
| `_sendInquiry` | - | NOT TESTABLE (same) | |
| Saved vendors | - | NOT TESTABLE (same) | Home tile "None saved" |

Counts: 23 PASS, 7 BUG (one, BUG 6, may be the harness), 3 NOT TESTABLE (plus chapter/board photo uploads).

## Bugs

### BUG 1 - Budget sheet does not update after you change the total
Steps: Home > BUDGET > pencil > `42,500` > Save budget.
Expected: the open sheet reads "of $42,500".
Actual: Firestore has `budgetTotal: 42500`, but the sheet still shows "$15,200 of $38,000" and "$22,800 still to spend" until you close and reopen it.
Code: `_budgetSheet(couple, plan)` streams the plan live but hands `_budgetCard` the `couple` map captured when the sheet opened, and `_budgetCard` reads `couple['budgetTotal']`. Wrap it in `_liveDoc('couple:$_cid', () => _coupleRef)`, as the vendor sheet's Save button does.

### BUG 2 - Vendor team month road overflows (yellow/black stripes)
Steps: open Vendor team (Overdue has Photo, Video, Venue, Planner +5; Oct 26 has 4 items).
Actual: "BOTTOM OVERFLOWED BY 19 PIXELS" and "5.0 PIXELS" on the Overdue and Oct 26 columns (team.png).
Code: `_roadCol` (about line 15938) sits in `SizedBox(height: 92)` (about line 15898). The label, 4 rows (`take(4)`) and the "+N" line don't fit in 92. Take 3 rows when there is a "+N", or make the road about 112 high.

### BUG 3 - A comma in a vendor's Budget or Spent wipes the amount
Steps: Vendor team > Every category > Videographer (Budget $3000) > Budget `3,250` > Save.
Expected: 3250 saved, or a validation message.
Actual: `budgetPlanned: null` is written and the $3,000 is lost silently.
Code: `_editVendor` saves `double.tryParse(planC.text.trim())` and `double.tryParse(spentC.text.trim())` with no cleanup and no validation. `_setBudgetSheet` and `_setupSheet` strip commas. Strip `,` and `$`, and keep the old value (or disable Save) when the text still doesn't parse.

### BUG 4 - GlobalKey error when the Website view opens
Steps: Home > WEBSITE tile (happened on both tries, after both reseeds).
Actual: `Multiple widgets used the same GlobalKey. The key [GlobalKey#c09b2] was used by 2 widgets: KeyedSubtree-[GlobalKey#c09b2], Center-[GlobalKey#c09b2]` (stack: `_debugVerifyIllFatedPopulation`). Nothing visibly broke. It is the same shape as the known Account-page GlobalKey error, so it may share a root cause (probably a keyed child in the view switcher / AnimatedSwitcher), but this one fires on Website, not on Account.

### BUG 5 - Names containing "and" are cut apart, and republishing saves the damage
Steps: Website > Edit > Your name `Alexandra` > Publish ("Alexandra & Jordan" is saved). Edit again: the fields show "Alex" and "ra & Jordan". Publish changes without touching anything.
Actual: `weddingSites/avery-and-jordan.names` = "Alex & ra & Jordan" and the title on the Website card shows the same (BUG_names_split.png).
Code: `_editWebsite`: `_joined.split(RegExp(r'\s*(?:&|\+|and)\s*', caseSensitive: false))`. There is no word boundary on `and`, so it also splits Alexandra, Brandon, Amanda, Sandra, Andrew, Randy, Fernando, and so on. Use `\s+and\s+` (or `\band\b`) next to `&` and `+`.

### BUG 6 (check on device) - Follow-up writes to the site never land: no share sheet after publish, no registry sync, no copy-link toast
Seen four ways, after both reseeds:
- Publish changes writes the `weddingSites` doc, but the "Your website is live" sheet never opens. `couples/c1/activity` stays empty and `weddingSites/.../playlist` is never written. So the code after `set()` (`_mirrorSeating(slug, false)` > `_mirrorPlaylist` > `_logActivity` > `_siteLiveShareSheet`) never finishes, and the catch never toasts.
- Add registry / Save note save `couples/c1` but `_syncRegistryToSite` never updates the site (`registryLinks:[]` 45 s+ later). The sheet sits on its busy button for about 10 s first.
- Copy guest link (`_copyRegistryLink`, the same `where('coupleUid').limit(1).get()`) shows no toast at all.
- The Remove-registry undo toast arrives about 20 s late.
This may be the in-memory Firestore in the harness (the `where(...).limit(1).get()` query and the `seating/main` delete). The `_websiteMini` snapshot of the same query works, though, so please check it on a phone. Whatever the cause, two things are worth fixing: `_editWebsite` should open the share sheet right after the main `set()` and run the mirrors after it, and the registry sheets shouldn't wait on the site sync before closing.

### BUG 7 - Shopping list "About, in total" drops the decimal point
Steps: Shopping > Add something > About `12.50` > Add to list.
Actual: `est: 1250`; the item shows "about $1250" and the header "about $1355 still to spend".
Code: `_editShopItem.save`: `int.tryParse(estC.text.trim().replaceAll(RegExp(r'[^0-9]'), ''))` strips the `.` too. Parse it as a double after stripping `$` and `,` (then round, or store a num).

## Minor notes (not counted)
- `_editShopItem`: an item without `cat` (the seeded Guest book) moved from "Everything else" to "Reception" when edited. The default `cat` is 'reception' unless a category filter is active.
- `_bdAddSwatch`: typing an invalid hex (`zz12`) gives no feedback; Add color silently uses the last valid color.
- Dream board on a phone: new pins go to fixed board spots (`_bdSpot`: x 200, 290, 380 ...), not the visible area. The third pin ("Example Domain") was off-screen to the right, so on a phone a new pin looks like nothing happened.
- Website card: the share icon button has no semantics label (screen readers read nothing).
- `_editWebsite`: Cancel always asks "Discard your changes?" even when nothing changed.

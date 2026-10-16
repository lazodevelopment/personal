# QA qa3 - couple dashboard, phone view (375x812)

Area: message threads (thread, menu, block/unblock, report, went elsewhere, edit message, emoji, proposals,
questionnaire, contract review, contracts vault, leave review), June's feed, Account popups, "Bring your wedding to Lazo".

Done on CDP 9343 (first part) and 9342 (after the restarts, fresh data). Screenshots: `scratchpad/qa/qa3/`.
Driver: `scratchpad/qa/qa3/drv.mjs` + `d.sh` run a whole step sequence in ONE CDP session. Separate `lz.mjs type`
calls lost the field's focus between processes, so nothing was typed. On this loaded machine, popups need about 3 s
before the next tap. Taps sent sooner landed on the barrier and closed them, which made some popups look broken
when they were not.

Counts: **PASS 27 · BUG 6 · NOT TESTABLE 8**

| Popup | What I did | Result | Evidence |
|---|---|---|---|
| June's feed `_cFeedSheet` | Tapped the bell (badge 1) | PASS | `feed.png` "From June - 1 new since you last looked", 3 items, 3h/1d/2d. `dump users/c1/juneFeed`: f0 `read:true, readAt:<now>`, badge cleared |
| Feed item -> thread | Tapped "Golden Hour Studio replied..." | PASS | Thread `ia` opened (Golden Hour Studio, invoice strip) |
| Open a thread | Messages -> Desert Bloom Florals | PASS | `thread_ib.png` |
| Send a message | Typed + Enter, and the send button | PASS | `dump inquiries/ib/messages`: `{senderRole:'couple', text:'Hello! Quick question', at}`, bubble "Delivered" |
| Emoji `_emojiSheet` | Opened, 💍 (Wedding), Warm tab, ❤, closed, sent | PASS | `emoji3.png`, `emoji_in_field.png`; message saved as `"💍❤"` |
| Edit sent message `_editCoupleMessage` | Long-press own bubble; Save with no change; appended " about May 3"; Save | PASS | Save does nothing while unchanged; dump: `text:'Hello! Quick question about May 3', editedAt:<now>`; bubble shows "edited" (`edited.png`) |
| Thread menu `_threadMenu` | More on a `responded` thread and on a `booked` thread | PASS | `menu.png` 3 options; `menu_booked.png` has only Block and Report (no "went another direction") as designed |
| Report `_reportSheet` | Send disabled with no reason; picked Spam, typed detail, Send | PASS | `report.png` greyed Send; `report_err.png` inline "Could not send that just now..." with the chip and text kept |
| Block confirm `_confirmBlock` | More -> Block -> Block vendor | BUG 1 | Dialog is fine (`block_confirm.png`). After the blockVendor failure, no feedback is visible (`block_toast.png`, `block3.png`, polled 8 s) |
| Unblock / blocked section | - | NOT TESTABLE | Blocking needs the blockVendor function, so no thread can become blocked |
| Went elsewhere `_wentElsewhereSheet` | Send disabled until a reason; picked Price, blank note, "Let them know" | PASS | `dump inquiries/ib`: `status:'lost', lostReason:'price', lostNote:'', lostAt`; message `system:'lost'` with the default thank-you text; thread closed, toast "Told Desert Bloom Florals. That was kind.", list shows "Went another direction" (`elsewhere_done.png`) |
| Proposals `_coupleProposals` | - | NOT TESTABLE | No `proposals` seeded and no way to write one from the couple side |
| Questionnaire `_fillQuestionnaire` | - | NOT TESTABLE | No `questionnaires` seeded |
| Contract review `_juneReviewContract` | - | NOT TESTABLE | No sent `contracts` seeded (the card that opens it never renders) |
| Contracts vault `_contractsVaultSheet` | Searched for an entry point | NOT TESTABLE (note) | The function has **no caller** in v158 (also none in v150-v157): dead code, unreachable from the UI |
| Leave a review `_leaveReviewSheet` | - | NOT TESTABLE | The card needs `reviewRequestStage > 0`, which is not seeded |
| Setup `_setupSheet` | Account -> "Your names, city and budget": 5 steps, Back/Next, city Phoenix -> Denver, budget 38000 -> 42000, toggled DJ and Videographer, Done | PASS (+ BUG 3) | `dump couples/c1`: `metroId:'denver', budgetTotal:42000, setupDoneAt, updatedAt`; row reads "Avery & Jordan · Denver · $42,000"; existing plan statuses kept |
| Setup city dropdown | First pick of Denver | BUG 4 (intermittent) | The sheet vanished, nothing was saved, and the error was "setState() or markNeedsBuild() called during build ... ListenableBuilder". The second try worked |
| Display name `_editDisplayName` | Cleared it (Save does nothing), typed "Avery Rivera", Save | PASS | `dump users/c1`: `display_name:'Avery Rivera'`; header shows "Avery Rivera" |
| Partner `_partnerSheet` invite | "jordan" -> Invite does nothing; "jordan@example.com" -> Invite | PASS | `dump coupleInvites`: `{coupleUid:'c1', email:'jordan@example.com', code:'MD8NWB', status:'pending', createdBy:'c1'}`; row "Code MD8NWB - waiting for them" + Copy code |
| Partner join | "abc" -> Join does nothing; "abcd12" -> Join | BUG 2 | Inline error reads **"internal [0]"** (`partner_join.png`) |
| Notifications `_maybeAskPush(force)` | Not now; then Yes, let me know | PASS (+ BUG 5) | Not now: `pushAskAnswer:'no', pushAsk.c1.answer:'no'`. Yes: the stamp is `'blocked'` (push cannot register in this browser), but the user sees nothing (`push_yes_a.png`) |
| Support `_openSupportSheet` | Chips; "Which vendor?" only under Report a vendor; Send disabled until subject and message; sent a bug report | PASS | `dump supportTickets`: `{role:'couple', uid:'c1', category:'Report a bug', subject:'Bell does not clear', message:'After opening the feed the badge stays.', vendorName:'', status:'open', context:{source:'couple_dashboard', build:'v90'}}` (`build` is stale, minor) |
| Delete account `_deleteAccount` | Opened; "Delete my account" | PASS (+ BUG 2) | Busy state, then the error is inline and the sheet stays usable, but the text reads **"internal [0]"** (`delete_err.png`). "Keep my account" closes it |
| Import home `_importSheet` | Account -> Switching from The Knot or Zola; chose Zola | PASS | `import_home.png`; tiles turn green with summaries after each import ("3 on your team", "6 details", "3 lines", "Linked on your website"); footer "Maybe later" changes to "Done", and Done closes the sheet |
| Import: forward emails | Mode switch | PASS | `imp_email.png`: import@meetlazo.com, Copy, 3 steps, Done |
| Import: vendors | Typed 1 line -> Read my list (canned 3); set Bloom & Vine -> Florist; "Add 3 to my team" | PASS (+ BUG 6a) | Busy state, review with an "On Lazo" badge; the button counts only rows with a category ("Add 2" -> "Add 3"). `dump couples/c1/plan`: videographers `{status:'booked', vendorName:'Atavia Weddings', vendorId:'ven1', budgetActual:3200, source:'import', bookedAt}`, venues `{vendorName:'The Farm at South Mountain', budgetActual:9500}`, florists `{vendorName:'Bloom & Vine', status:'booked'}`; activity "Avery added 3 booked vendors from Zola." |
| Import: vendor category dropdown | First pick of Florist | BUG 4 (intermittent) | Same "setState() called during build" error, and the pick was lost; the second try worked |
| Import: website | Pasted a link -> Read my website; unticked Dress code; "Use 6 details" | PASS | `dump weddingSites/avery-and-jordan`: `dateIso:'2027-03-27', venueName, ceremonyTime:'4:30 PM', story, updatedAt`, no dressCode; `couples/c1.registryLinks:[{label:'Zola', url:'https://www.zola.com/registry/averyjordan', store:'Zola'}]`, `importedAt`; done screen "Your Lazo website is updated" (it took about 8 s on this machine) |
| Import: budget | Paste it -> typed -> Read my budget -> "Use 3 lines" | PASS (+ BUG 6b) | Review "$15,100 planned", 3 lines with paid amounts. `dump plan`: photographers `budgetPlanned:3200, budgetActual:800`, florists `2400`, venues `9500/2000`; `budgetTotal` stays 42000 (it already had one) |
| Import: guest list | Opened | NOT TESTABLE | Zola export steps shown correctly; the native file picker cannot be driven |
| Import: budget upload | - | NOT TESTABLE | File picker |
| Import: registry tile `_addRegistryLink` | Pasted an Amazon link -> Add registry | PASS | `registryLinks` gained `{label:'Amazon', url:'https://www.amazon.com/wedding/registry/AJ2027', store:'Amazon'}`; tile "Linked on your website" |
| Attach a file | - | NOT TESTABLE | File picker / Storage |

## Bugs

### BUG 1 - Block failure shows no feedback while the thread is open
Steps: thread -> More -> Block <vendor> -> Block vendor (blockVendor fails).
Expected: a visible failure message, so the user knows the vendor is NOT blocked.
Actual: the confirm closes, the thread stays, and nothing appears (`block_toast.png`, `block3.png`; nothing found when
polling for 8 s). The same kind of toast shows fine once the thread is closed ("Told Desert Bloom Florals. That was
kind." in `elsewhere_done.png`).
Suspected code: `_confirmBlock` reports failure (and "unblocked") with `_toast(...)` ->
`ScaffoldMessenger.of(context)` of the dashboard. That SnackBar paints in the dashboard Scaffold, under the modal
thread sheet, which stays open on the failure path. The same applies to every `_toast/_toastC` fired while a sheet is
open: the partner sheet's "Invite created - send them the code." and "Code copied", `_juneReviewContract`'s "Could
not send that question", and `_fillQuestionnaire`'s success toast. Fix: show the failure inline in the confirm (it
already has `_pcC_err`), or raise the toast from the sheet's own context or an Overlay.

### BUG 2 - Raw "internal [0]" shown as the error text
Steps: Account -> Your partner -> code "abcd12" -> Join; or Account -> Delete my account -> Delete my account.
Expected: a human message ("That code did not work." / "We could not delete your account just now.").
Actual: the inline error reads `internal [0]` (`partner_join.png`, `delete_err.png`).
Suspected code: `_partnerSheet.join()` uses `joinErr = e.message ?? ...` and `_deleteAccount.go()` uses
`err = e.message ?? ...` in their `on FirebaseFunctionsException` branches. For network or internal failures the
plugin's `message` is the code string, so the `??` fallback never runs. `_confirmBlock` has the same pattern
(`_toast(e.message ?? ...)`). Use the friendly text unless `e.code` is a known, user-meaningful one (for example
`not-found` or `failed-precondition`, where the server sends its own message).

### BUG 3 - Setup step 5 ("Which vendors do you need?") does nothing when reopened from Account
Steps: Account -> Your names, city and budget -> go to step 5 -> untick DJ, tick Videographer -> Done.
Expected: the plan reflects the choices, or the step is not shown.
Actual: `couples/c1/plan` is unchanged (DJ still `researching`; skipped categories still `skipped`). After the first
setup, every category has a plan doc with a status, so the v139 guard `if (hasPlan.contains(slug)) continue;` skips
all of them. The chips also always start from the hard-coded default set, not from the plan. The user is offered a
choice that is silently ignored. Suggest hiding step 5 when `couple.setupDoneAt` is set (the Account row says
"names, city and budget"), or seeding `wanted` from the plan and writing only `needed` <-> `skipped` changes.

### BUG 4 - Picking from a dropdown inside a sheet sometimes loses the pick (intermittent)
Seen twice, both times on the first dropdown pick after the sheet opened: in setup step 3 (city), the whole setup
sheet closed and nothing was saved; in the import vendor review (category), the pick was lost. Both times the console
showed `setState() or markNeedsBuild() called during build. This ListenableBuilder widget cannot be marked as needing
to build...`. A retry worked both times. It may be the menu route closing while the sheet rebuilds, or focus moving
from a focused TextField during build. Worth a check on a device: `DropdownButtonFormField` in `_setupSheet` and
`DropdownButton` in `_importSheet` vendors.

### BUG 5 - "Yes, let me know" gives no feedback when push cannot be enabled
Steps: Account -> Notifications -> Yes, let me know (registration fails or permission is denied).
Expected: a line telling them to allow notifications in system or browser settings.
Actual: the sheet closes and nothing is shown. `pushAskAnswer` becomes `'blocked'`, and only success shows a toast
(`if (ok) _toast(...)` in `_maybeAskPush`). Also, the forced path from Account still waits the 1.4 s "let the Sent
confirmation land" delay before the sheet appears, which feels laggy from a settings row.

### BUG 6 - Import overwrites existing data without saying so
a) Vendors: the seeded plan had venue `Desert Botanical Garden` booked at 12000. Importing "The Farm at South Mountain"
as Venue silently replaced the vendor name and set `budgetActual` to 9500. The review shows no hint that a booked
venue will be replaced. The only note is about duplicates *within* the import. Suggest flagging rows whose category
already has a booked vendor ("Replaces Desert Botanical Garden").
b) Budget: `_saveImportedBudget` writes `budgetActual: paid` whenever `paid > 0`. Photographers went from
`budgetActual:3200` to `800`, and venues from `9500` to `2000`. The review note only says "These replace the planned
amounts". Real spent figures get lowered. Suggest `max(existing, paid)` (the rule `_spentOf` already uses), or say so
in the note.

## Observations (not counted)
- Contracts vault (`_contractsVaultSheet`) is unreachable: it has no caller in v158, nor in v150-v157.
- `_leaveReviewSheet` posts to `reviews` but never sets `reviewSubmittedAt` / `reviewOptOut` on the inquiry, so
  `_coupleReviewCard` keeps showing "HOW WAS IT?" unless a Cloud Function sets it. I could not find that function in
  this checkout (functions-dashboard is not here), so it is worth confirming. Proposal Accept/Decline call
  `d.reference.update` without try/catch, so a failure throws uncaught.
- Website import: the site got `dateIso 2027-03-27` while the plan date is 2027-03-28. The plan date is correctly not
  overwritten, but the mismatch is not mentioned.
- Support ticket context `build:'v90'` is hard-coded and stale.
- `Assertion failed: rendering/object.dart:3687:12` appeared twice in the first session, while using the harness's
  per-call re-emulation. It did not come back with the single-session driver.

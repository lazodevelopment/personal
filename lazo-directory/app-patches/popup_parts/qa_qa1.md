# QA pass 2 - qa1 (couple, phone 375x812): guests and the wedding day

Tester: qa1, CDP 9341. Screenshots: `<scratch>/qa/qa1/`. The machine crashed twice during the pass; data was
re-seeded after each restart, so dumps below come from whichever session the step ran in.

Harness notes (not app bugs): after a few interactions the semantics tree goes stale ("Semantics node map was
inconsistent after update" floods the console), so most taps were made by coordinates from screenshots. Each new
driver call re-applies the device metrics, which resets the page scroll to the top (scroll + tap had to run in one
call). Storage uploads retry for ~45 s before failing.

## Summary
PASS 17 · BUG 12 (BUG-1..BUG-12; 5 of them minor/visual) · NOT TESTABLE / NOT COVERED 1 row (photo uploads; edit+remove
of an existing website event/moment not reached after two machine crashes).

## Results

| Popup | What I did | Result | Evidence |
|---|---|---|---|
| Widgets chip -> "Your widgets" sheet | Opened from the home strip, read it, closed with X | PASS | widgets.png, afterclose.png |
| Single widget sheet (strip chip, e.g. weather) | Opened the weather chip, tapped the card | BUG-1 | wxchip_tap.png; console `Multiple widgets used the same GlobalKey.` |
| `_addKeyDate` | Add a date -> idea chip "Rehearsal dinner" -> Pick the day -> Oct 23 -> OK -> Add date | PASS (minor UX note, BUG-6) | `couples/c1.keyDates = [{"label":"Rehearsal dinner","date":"2026-10-23T12:00:00.000"}]`; chip "Rehearsal dinner Oct 23" and weather card switched to it |
| Weather card on "Your wedding day" with a key date selected | Looked at it | BUG-5 (visual) | share.png / share2.png: title breaks as "Weathe / r" |
| `_timelineBuilderSheet` (Open from "Share with your vendors") | Opened, header, anchor chip, rows, footer | PASS | tl_builder.png |
| `_editTimelineEvent` (edit) | Ceremony: note "Under the arch", 30 min, Officiant + Photographer, anchor on, Save | PASS | `d1: {time:"16:00", label:"Ceremony", note:"Under the arch", dur:30, owners:["officiant","photo"], anchor:true}`; row shows 4:00-4:30 PM + tags (tl_after_save.png) |
| `_editTimelineEvent` (add) | Add a moment "Toasts", time 7:00 PM via picker, 15 min, DJ, Add moment | PASS | new doc `{time:"19:00", label:"Toasts", dur:15, owners:["dj"], anchor:false}` (tl_after_add.png) |
| Anchor re-time (`_tlReanchor`, "Ceremony at 4:00 PM · change") | Picked 5 PM | PASS (but see BUG-2) | every moment shifted +60 min in the dump (16:30, 17:00, 17:45, 19:00, 20:00, 21:00); chip reads "Ceremony at 5:00 PM" |
| Remove a moment (x) + Undo | Removed Toasts, then First dance, closed the sheet, tapped Undo | PASS on data / BUG-2 on UI | doc deleted; Undo restored "First dance"; tl_removed.png (no toast in sheet), tl_removed2_closed.png (toast only after closing) |
| Empty timeline state | Removed every moment | BUG-3 | tl_empty2.png / BUG_tl_empty_footer_overflow.png; `A RenderFlex overflowed by 18 pixels on the right.` |
| Classic-day starter (`_seedClassicDay`) | Start from a classic day -> picker 4:00 PM -> OK | PASS | 16 moments written 12:00..21:10, Ceremony 16:00 `anchor:true`, owners/dur as in code (classic_done.png) |
| `_sendToVendors` (day-of timeline) | Send to vendors -> toggled the vendor off (button disables) and on -> Send | PASS (slow, BUG-7) | `inquiries/ia/messages` got the couple message with the full timeline text; `couples/c1/sends/timeline = {kind:"timeline", to:[{inquiryId:"ia", vendorName:"Golden Hour Studio"}]}`; "Sending…" ~45 s while Storage retried (send_after.png); console `LAZO send attach: [firebase_storage/retry-limit-exceeded]` |
| Guest list page | Opened from the "Guest list & meals" pencil | see BUG-4 | guests.png: a "Moment removed. Undo" toast from minutes earlier still appears here; header line starts with a missing-glyph box |

| `_editGuest` (edit) | Mia Chen: party "The Chens", RSVP Attending, +1s 1, group Wedding party, side Partner 2, meal "Veg", Thank-you on, Save | PASS | `g2: {party:"The Chens", rsvp:"yes", group:"wedding-party", side:"partner2", meal:"Veg", plusOnes:1, thankYouAt:<ts>}`; row "The Chens · +1 · Veg · thanked", counts 5/4/1/1, "1 Veg", "Thank-you notes: 1 of 4" (guest_saved.png). The Thank-you switch appears only once Attending is picked, as coded |
| `_editGuest` (add) | Add guest: Add button disabled while name empty; name "Taylor Kim", meal "Chicken", Attending, Add guest | PASS | new doc `{name:"Taylor Kim", group:"friends", side:"both", rsvp:"yes", meal:"Chicken", plusOnes:0, thankYouAt:null, createdAt}`; counts 6/5, "1 Veg · 1 Chicken" |
| `_editGuest` (remove) | Uncle Ben -> Remove guest -> confirm "Remove Uncle Ben?" -> Remove guest | PASS (see BUG-9) | `g1` gone from `couples/c1/guests`; Declined count 1 -> 0 |
| Guest list "Add guest" button | Looked for it with the full list | BUG-8 | BUG_add_guest_under_june_bar.png, BUG_add_guest_low_contrast.png |
| `_dayBeforeSheet` | Write it -> edited the note (+" QA1 test.") -> Send a test to me; then Send to everyone -> confirm sheet -> Not yet | PASS | worker unreachable -> inline red "Couldn't send - network." (daybefore_test.png), popup stays usable; `weddingSites/avery-and-jordan.dayBeforeNote` saved with the edit; confirm sheet reads right, "Not yet" backs out without sending |
| `_guestPhotosSheet` | Manage -> sheet opens with Waiting for approval / Refresh / Copy all links (disabled) / Download all (disabled), empty state, Close / See the wall | PASS (see BUG-10) | guestphotos.png |
| `_pendingPhotosSheet` | Waiting for approval | BUG-10 | pendingphotos.png: "Nothing waiting. You're all caught up." although the worker call failed |
| `_plusEditor` (website "Our story in dates" -> Add a moment) | Save disabled with only "What happened" filled; filled "When" June 2019 -> Save; then Publish changes | PASS with BUG-11 | plus_titleonly.png (Save disabled), plus_saved.png (card "The wrong number / June 2019"); after publish `milestones:[{when:"June 2019", title:"The wrong number", text:"", photo:""}]` |
| `_eventEditor` (The weekend -> Add an event) | Name "Welcome dinner", time "6:30 PM", place "Hotel Valley Ho", RSVP switch on, Add event; Publish changes | PASS (see BUG-12) | `events:[{name:"Welcome dinner", dateIso:"", time:"6:30 PM", venueName:"Hotel Valley Ho", rsvp:true, ...}]` after publish; console `Assertion failed: ... rendering/object.dart:3687` right after the sheet closed |
| Plus editor / event editor: edit + Remove of an existing item, photo upload | not done | NOT TESTABLE (photo: Storage/file picker) / NOT COVERED (edit+remove: ran out of time after two machine crashes) | - |

## Bugs

### BUG-1 Single-widget sheet: tapping the card navigates the page behind and leaves the sheet open
Steps: Home -> tap the weather chip in the widget strip -> the weather widget opens in a sheet -> tap the card.
Expected: the sheet closes and "Your wedding day" opens (or the card is not tappable inside the sheet).
Actual: the page behind switches to "Your wedding day" but the sheet stays on top of it; console logs
`Multiple widgets used the same GlobalKey.` when the single-widget sheet opens.
Code: `_crStrip.open(id)` puts `_crBody(id, ...)` inside `_lzSheet`; the weather body's `_Press(onTap: () => setState(() => _view = _View.dayof))`
(around line 9371) does not pop the sheet first. The GlobalKey error suggests `_crBody` reuses a keyed widget that is
also mounted on the page (the strip/stack behind the sheet). In the full "Your widgets" sheet the same tap did nothing visible.

### BUG-2 Undo toasts are hidden behind the sheet they belong to
Steps: open the Day-of timeline sheet -> tap x on a moment (or change the ceremony time with the anchor chip).
Expected: "Moment removed. Undo" (6 s) is visible so the instant delete can be undone.
Actual: nothing visible while the sheet is open; the toast shows only once the sheet is closed, and queued toasts
surface much later on other pages (the "Moment removed. Undo" toast appeared on the Guest list minutes later).
Delete has no confirm step, so with the toast hidden the delete is effectively irreversible from inside the sheet.
Code: `_toastUndo` / `_toast` use `ScaffoldMessenger.of(context)` of the page, which paints under the modal route.
Affects `_timelineBuilderSheet` (remove moment), `_tlReanchor` (shift undo) and `_seedClassicDay` (toast).

### BUG-3 Empty timeline footer overflows at phone width
Steps: Day-of timeline with no moments (fresh couple, or remove all).
Actual: footer "Add one moment" + "Start from a classic day" overflows by 18 px (yellow/black stripe, label cut to
"Start from a classic d"). Code: `_timelineBuilderSheet` empty footer `_lzActions(secondary: 'Add one moment', primary: 'Start from a classic day', icon: ...)` - labels too long for 375 px; shorten ("Add one", "Classic day") or let `_lzActions` wrap/stack.

### BUG-4 Stale toast + missing glyph on the Guest list (minor)
The queued "Moment removed. Undo" toast (from BUG-2) appears on the Guest list; the "Thank-you notes: 0 of 3 sent"
line starts with an unrendered glyph box (emoji/icon character with no font on web).

### BUG-5 Weather card title wraps mid-word when a key date is selected (visual)
"Your wedding day" -> Weather card with "Rehearsal dinner · October 23, 2026" selected: the serif title renders
"Weathe" / "r". The header Row gives the right-hand date text the space; the title needs `Flexible`/no-wrap or the date
should ellipsize. (Fine when "Wedding day · March 28, 2027" is selected.)

### BUG-6 `_addKeyDate` primary button reads like an action but is disabled (minor UX)
With a name and no day, the primary reads "Pick the day" but is disabled; tapping it does nothing. Either make it
open the date picker (`onPrimary: picked == null ? pickDay : save`) or label it as a hint.

### BUG-7 Send to vendors waits ~45 s on the attachment upload (harness-amplified)
`_sendArtifact` awaits `putData` with no timeout; the button sits on "Sending…" until Storage gives up, then the
message goes without the attachment (good fallback). On a bad connection a real user waits the full retry window.
Suggest a `.timeout(...)` on the upload.

### BUG-8 Guest list: "Add guest" is hidden under the June bar, and nearly invisible when shown
With the full list (6 guests) the "Add guest" outlined button sits at the end of the list, directly under the floating
"Ask June…" bar; I could not scroll it into a tappable spot on a 375x812 phone (BUG_add_guest_under_june_bar.png).
It only became reachable with the Declined filter on an empty list, and there it renders plum text on the dark plum
page, close to invisible (BUG_add_guest_low_contrast.png). Expected: bottom padding below the list so the last
item/button clears the June bar, and a light foreground for that button on the dark page.
Code: guest list view, `OutlinedButton.icon(onPressed: _h(() => _editGuest()), ... color: _lzFg(plum))` (~line 27509) -
`_lzFg(plum)` on the dark page background; the list needs bottom padding ~ June bar height.

### BUG-9 Remove guest: the busy state shows on the Save button
After confirming Remove, the Edit guest sheet shows a spinner inside the primary "Save" button ("Removing them…" is
below the fold) while the delete runs (guests_declined.png). Minor: the user sees "Save" spinning for a delete.
Code: `_editGuest` footer `busy: deleting` on the primary.

### BUG-10 Waiting for approval says "all caught up" when the photos call failed
`_pendingPhotosSheet` fetches before opening; on any failure `_workerGet` returns `{ok:false}` and the sheet shows the
happy empty state "Nothing waiting. You're all caught up." The couple would believe nothing is pending.
Expected: an error line ("Couldn't load the photos waiting - try again") with a retry when `j['ok'] == false` /
no `photos` key. Same pattern in `_guestPhotosSheet` (empty state "Nothing shared yet" on failure).

### BUG-11 Plus editor validates the wrong field for "Our story in dates"
In "Add a moment" the Save button stays disabled with "What happened" filled; it enables only when "When" is filled,
because `_plusEditor` validates `fields.first` and `_kPlusMilestone` lists `when` first. The title is the field that
matters (the card shows it as the heading) and the date may be unknown. Fix: validate a designated required key
(e.g. `title`), or reorder `_kPlusMilestone`.

### BUG-12 Website editor jumps to "While you're in town" after a nested sheet closes
After closing the event editor (Add event, or Escape) the website editor's body is scrolled to the WHILE YOU'RE IN
TOWN section with the "A line for your guests" field focused (event_added.png / event_open first attempt), not back
to THE WEEKEND where the user was. A Flutter assertion (`rendering/object.dart:3687`) is logged at the same moment.
Likely the focus returns to the nearby-note TextField, which scrolls itself into view.

Other notes: the time pickers use the default Material purple theme, not Lazo colors. Seeded inquiries have no
category, so the vendor row in Send shows an empty subtitle line (data, not code).

# QA pass 2 - qa4 (vendor, phone 375x812): pipeline and a lead's thread

Run on CDP 9341 after the restarts (fresh data). Screenshots: `scratchpad/qa/qa4/` (numbered 00-62).

## Harness gaps that blocked most saves (tell the harness owner)
1. Every write that contains a `FieldValue` (serverTimestamp, arrayUnion, arrayRemove, delete) fails in this harness with
   `TypeError: Instance of 'FieldValueWeb': type 'FieldValueWeb' is not a subtype of type 'MockFieldValuePlatform'`.
   That is nearly every save in my area (tags, tasks, proposals, invoices, mark paid, mark booked / release, saved replies,
   sending a message). Where the write was a `.update()`/`.set()`, the fake store sometimes applied the plain fields
   before throwing (q0 got `status: booked` with no `bookedAt`; i1 got `status: paid` with no `paidAt`/`paidVia`; q2 got
   `status: closed` with no `unbookReason`). Real Firestore is atomic, so those partial dumps prove only the plain values.
   The UI side was still checked: every one of these popups showed an inline error and stayed usable (good).
2. "client is offline" hang (FirebaseFirestore / .instance split over two lines): `_paymentPlanSheet` and
   `_sendQuestionnaireSheet` never open (waited 90 s / 45 s). `_invoiceComposeSheet` opened only after ~20 s.
3. Touch scrolling stopped working mid-session (vertical scroll of Today did nothing either), so the pipeline board
   could not be scrolled sideways to Talking/Booked/Lost on the phone; I reached Nora & Eli (q2) through the bell feed.
4. The first tap after a sheet closes is often swallowed (had to tap the + twice); the semantics tree is sometimes stale
   (`taptext` hit a stale node at 95,260 and dismissed the stages sheet).

## Results

| popup | what I did | result | evidence |
|---|---|---|---|
| _stagesSheet | Pipeline > Stages; added "Tour scheduled" (Enter) and "Waiting on deposit" (Add); moved the 2nd up; Save stages | PASS | `"pipeline":[{"key":"c_guskwc","label":"Waiting on deposit"},{"key":"c_c6c5tl","label":"Tour scheduled"}]`; 02, 06, 07 |
| _stagesSheet close | tap outside | PASS (closes, nothing saved) | 05 |
| Thread open (q0) | tap a pipeline card | BUG B1 | `A RenderFlex overflowed by 23 pixels on the right` (x2-3 every time the thread opens); 08 |
| _addTagSheet | + tag; field autofocus; Add tag disabled while empty; typed "Hot  Lead", Add tag | UI PASS / save NOT TESTABLE (FieldValue) | inline "Could not tag it: ..." and sheet stays usable; 10, 12, 13 |
| (sheet close after an inline error) | Cancel on the tag sheet / invoice sheet after their error | BUG B13 | `Looking up a deactivated widget's ancestor is unsafe` x3 + `RawTooltipState is a SingleTickerProviderStateMixin but multiple tickers were created` x6-15 |
| _fitSheet | tap "Silver fit" | PASS | 60/100, "Date is open +20", "No budget given"; Edit who I work with opens the prefs sheet; 14, 15 |
| _bookingStatusSheet (not booked) | Mark booked > Mark booked | NOT TESTABLE (FieldValue) | `LAZO setStatus: TypeError ... FieldValueWeb`; toast path; 16, 17 |
| _bookingStatusSheet (booked, q2) | Booked > "The couple cancelled" > Release the date | UI PASS / confirms B8 | primary disabled until a reason is picked, label switches; dump q2 `"status":"closed"` (rest of the write failed: FieldValue); 53-55 |
| _needsBooked | locked rows in Studio tools | NOT TESTABLE | thread status could not change (FieldValue) |
| _composerToolsSheet | + in the thread | PASS | all rows, sections, locked "Once they're booked" rows; 18, 25 |
| _taskSheet (add) | Add a task; Add disabled until a title; Tomorrow chip (shows 10/16/2026 + No date); The couple (note appears); Add task | UI PASS / save NOT TESTABLE | inline raw `TypeError: ...FieldValueWeb...` (no "Could not save:" prefix); 19-21 |
| _taskSheet (edit/delete) | - | NOT TESTABLE | no task could be created |
| _sendProposal | title "The Verse - 8 hours", price "1,250.50", includes; Send | BUG B12 / save NOT TESTABLE | preview reads **$1,251** for $1,250.50; inline "Could not send: TypeError..."; 22-24 |
| _invoiceComposeSheet | Custom; line 1 "Balance" $500; Add a line; line 2 amount $300, no label; Send | BUG B4 (confirmed in UI) / save NOT TESTABLE | Total and button read **Send $800**; send() went ahead (no "add a label" error) - by the code it saves `total: 500` with one line; 27-30 |
| _markInvoicePaid (q2 Balance $1,300) | Mark paid; Zelle; Mark paid | UI PASS / save NOT TESTABLE | note text follows the chip ("saved as paid by Zelle"); inline "Could not mark paid: ..."; partial dump `i1.status: paid`, inquiry `invoiceStatus: sent`; 51, 52 |
| _paymentPlanSheet | Studio tools > Set up a payment plan | NOT TESTABLE (client-offline hang) | nothing after 90 s; 33 |
| _sendQuestionnaireSheet / _questionnaireEditor / _questionnaireAnswersSheet / _juneQuestions | Studio tools > Send a questionnaire | NOT TESTABLE (hang; editor and answers are reached from it; no completed questionnaire seeded) | 34 |
| _startContractFlow + _noActiveTemplateSheet | Studio tools > Send a contract (q2) | PASS | "Add a contract template first" with Upload / Lazo starter; 58 |
| _contractValuesForm / _contractActionsSheet / _rescindContract | Starter > Wedding Photography Agreement > Add to my templates | NOT TESTABLE | the add never completed (no template in `vendors/ven1/contractTemplates`, sheet then would not close); no contracts seeded; 59-62 |
| _savedRepliesSheet | bolt icon | PASS (empty state + New saved reply) | 35 |
| _savedReplyEditor | Name "Availability", message with {couple} {date} {vendor}; Save disabled until both filled; Save | UI PASS / save NOT TESTABLE | inline "Couldn't save: ..."; 36, 37 |
| _editMessageDialog | - | NOT TESTABLE | no messages seeded and sending fails (FieldValue) |
| Teaser | - | N/A | vendor is a photographer; row only shows for videographers |
| Sneak peek | - | NOT TESTABLE | file picker / Storage |
| _helloSheet | Today > Say hello first card | BUG B9 (confirmed) | helloMatches fails, sheet shows "0 couples / 10 hellos left / Nobody to greet right now"; the card says "No couples in Phoenix need a photographer right now"; 41 |
| _helloCompose | - | NOT TESTABLE | no matches |
| Recommend team | - | NOT TESTABLE | row locked (status could not change) |

Counts: PASS 10 (stages, stages close, fit, tools, no-template sheet, plus the UI/validation/error paths of tag, task, release, mark paid, saved reply); BUG 6 seen in the harness (B1, B4, B8, B9, B12, B13) + 7 from code reading (B2, B3, B5, B6, B7, B10, B11); NOT TESTABLE 13.

## Bugs in detail

**B1 - Thread overflow (phone).** Steps: Pipeline > tap Maya & Leo. Actual: `A RenderFlex overflowed by 23 pixels on the right` on every open (not visible on screen, so likely a hidden/collapsed row - candidates: `_inboxThread` header Row (name column + fit chip + Mark booked pill) or one of the strips above the bubbles at 375 wide). Expected: no overflow.

**B2 (HIGH, code) - Replying to a booked couple un-books them.** `_sendVendorMessage` always does `ref.update({'status': status, ...})` and `_inboxSend` / `_sendProposal` pass `'responded'`. Any reply or proposal in a booked thread flips `booked` -> `responded`: the card leaves Booked, `_isBooked` turns false and the delivery tools lock. `_teaserSheet.send()` writes `'status': 'responded'` too, although teasers are only offered once booked. Fix: only set responded when the current status is new/empty.

**B3 (HIGH, code) - Dragging to Lost/Delivered opens the wrong sheet.** `_moveToStage` sends every status column (booked, delivered, lost) to `_bookingStatusSheet`. Dropping a new lead on Lost shows "Mark as booked" and its button books them; dropping a booked couple on Delivered shows the release sheet. Nothing marks lost/delivered from a drag. (Could not drag in the harness - see gap 3.)

**B4 (MEDIUM, money, seen) - Invoice total counts lines that will not be saved.** Steps: Send an invoice > Custom > "Balance" $500 > Add a line > $300 with no label > Send. Actual: total and button say $800, send proceeds; `send()` skips the unlabeled line (`if (lb.isEmpty || am == null) continue;`) so the invoice is written with `total: 500`. Expected: block the send ("Name every line") or compute the total the same way the save does.

**B5 (MEDIUM, money, code) - invoiceStatus follows the last invoice touched.** `_markInvoicePaid` writes `invoiceStatus: 'paid'` and the trash icon writes `invoiceStatus: 'void'` regardless of other open invoices, so "Where things stand" can say Paid while a balance is still due. The trash icon voids with no confirm.

**B6 (LOW, code) - Long tag silently dropped.** `_addTagSheet.apply()` returns without writing when the tag is over 24 chars, then `pick()` closes the sheet as if it worked. Field has no maxLength.

**B7 (LOW, code) - `_needsBooked` toasts success after a failure.** `_setStatus` swallows its error (toast "Could not update"), then `_needsBooked` toasts "Booked. Delivery tools are open" anyway.

**B8 (LOW, seen) - Released bookings are not Lost.** Release with "The couple cancelled" / "I had to cancel" writes `status: 'closed'` (dump confirms). `_stageOf` has no 'closed' case, so the card falls back into New/Talking.

**B9 (LOW, seen) - Hello failure looks like "no couples".** When `helloMatches` fails, `_helloCache = {'error': ...}`; the card says "No couples in Phoenix need a photographer right now" and the sheet "Nobody to greet right now" with "10 hellos left". Show the error and a retry instead.

**B10 (LOW, code) - Task edit has no Cancel.** In edit mode the secondary button is Delete; Cancel only via X / outside tap.

**B11 (LOW, code) - Contract veil can stick.** `_startContractFlow` awaits the `contractTemplates` get outside any try; if it throws, the June veil never comes down.

**B12 (LOW, money, seen) - Proposal rounds cents.** $1,250.50 shows as **$1,251** in "Their view" and in the auto message (`_invMoney` uses `v.round()`); the stored price is 1250.5. Show cents when present.

**B13 (MEDIUM, seen) - Errors when a sheet closes after an inline error.** After an inline error (tag sheet, invoice sheet), Cancel logs `Looking up a deactivated widget's ancestor is unsafe` (x3) and `RawTooltipState is a SingleTickerProviderStateMixin but multiple tickers were created` (many). Suspect: the async catch in the sheet calls setState / Theme.of on the sheet context after the route is popping (e.g. the busy/err setSheet), or a Tooltip (X close IconButton) rebuilt during the pop. Not seen when a sheet closes without an error.

Minor observations: `_invoiceComposeSheet` is a centered dialog on phone while every other popup is a bottom sheet; it (and the payment plan) gives no feedback between tapping the tools row and the query finishing. The "<- Maya & Leo" thread back arrow did not respond to taps and is not a button in semantics (the "Back to dashboard" arrow above it works) - may be harness, worth a look on device.

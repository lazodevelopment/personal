# QA pass 2 - qa5 (vendor profile/settings popups + look and feel)

Status: DONE (both parts). Run on CDP 9342 after the restarts.
Screenshots: `<scratch>/qa/qa5/` (`p1_*` part 1 phone, `d_*` desktop, `k_*` dark; `d_grid*.png` / `k_grid*.png` are contact sheets).

Totals: Part 1 - 28 popups: 20 PASS, 3 BUG, 5 NOT TESTABLE (several PASS rows have a write that is NOT TESTABLE in the harness). Part 2 - 16 desktop popups PASS; dark mode 14 PASS + 1 BUG. 12 distinct bugs in all (1 high, 3 medium, 8 low).

Driver notes for whoever runs this next: every `lz.mjs` call opens a new CDP session and re-applies
`Emulation.setDeviceMetricsOverride`; when the session closes the override drops, the page resizes and long views (Money tab,
profile editor) jump back to the top. I ran a background "keeper" session that holds the emulation (`<scratch>/keep.mjs`) and a
multi-step runner (`<scratch>/q.mjs`, `wheel` and `seek` commands) so scroll position survives between calls.

Harness note: every write that carries `FieldValue.serverTimestamp()` fails in the mock store with
`TypeError: Instance of 'FieldValueWeb' ... not a subtype of 'MockFieldValue...'` (same gap qa4 saw). For `set(merge)` the
plain fields still land (dump shows them, timestamp missing); for `.add()` nothing lands. Those saves are marked
"NOT TESTABLE (harness)" for the write itself, and PASS/BUG for how the popup handles the failure.

| Popup | What I did | Result | Evidence |
|---|---|---|---|
| June's feed (`_feedSheet`, bell) | Opened bell with 2 unread; dumped `users/v1/juneFeed` | PASS | f0/f1 `read:false` -> `read:true` + `readAt`; badge cleared. `p1_feed.png` |
| Team (`_teamSheet`) | Opened from Account; invalid email `notanemail`; valid `assistant@goldenhour.com` + Create invite | PASS (UI) / NOT TESTABLE (write) | Invalid: Create invite `aria-disabled=true`, nothing written. Valid: `.add()` hits harness FieldValue gap; inline error shown, sheet stays usable. Closes by tapping outside. `p1_team.png`, `p1_team_invite.png` |
| Brand (`_brandSheet`) | Typed bad hex; picked Navy + Sage + Sans; Save | PASS | Bad hex: inline "Colors need to be six-digit hex", Save disabled. Dump: `brand:{primary:"#1F3A5F",accent:"#B8C9B0",font:"sans"}` (updatedAt dropped by harness, banner shown). Preview recolours live. `p1_brand.png`, `p1_brand_badhex.png`, `p1_brand_reopen.png` |
| Consult scheduler (`_schedulerSheet`) | Typed video link, + hours on Sat, 45 min slots, no buffer, 2 days notice, In person, Save | **BUG** | Save always fails: "Could not save: Invalid argument: Nested arrays are not supported.: Instance of 'JSArray<List<String>>'"; nothing written (`scheduler` absent from dump). See bug 1. `p1_sched_edit.png`, `p1_sched_err.png` |
| Lead form (`_leadFormSheet`) | Tapped row twice | NOT TESTABLE (harness) | First-time create writes `createdAt: serverTimestamp()` -> harness error toast; sheet never opens and every tap mints a new key (V3FA... then 7GSY...). Failure path itself is graceful (toast). |
| Calendar feed (`_calendarFeedSheet`) | Opened, Copy feed link, X, reopened | PASS | `calendarToken: "G9L6BTBHZE2Y64B88B6W9WC9SKV9"` written once, unchanged on reopen; button flips to "Copied". `p1_calfeed.png` |
| Connect Claude/ChatGPT (`_mcpSheet`) | Make my link (function); tap outside | PASS | Inline "Could not create the link: [firebase_functions/internal] internal [0]", button re-enabled, closes on outside tap. `p1_mcp.png`, `p1_mcp_fail.png` |
| Report a bug (`_reportBugSheet`) | Contracts + Blocks me; 5-char text (Send disabled), longer text, Send | PASS (UI) / NOT TESTABLE (write) / minor BUGs | Send disabled under 8 chars; `.add()` fails in harness -> "Couldn't send that..." BUT the error renders below the fold (bug 3). Note reads "build 177" (bug 2). `p1_bug.png`, `p1_bug_after.png` |
| Ideas (`_ideasSheet` + composer) | Opened board (empty state), Suggest an idea, typed, Calendar chip, Post it, Back, Close | PASS (UI) / NOT TESTABLE (write) | Tabs, composer, char counter, Back all work; post `.add()` fails in harness (toast). `p1_ideas.png`, `p1_ideas_compose.png` |
| Support (`_openSupportSheet`) | Billing question, subject only (Send disabled), subject+message, Send | PASS (UI) / NOT TESTABLE (write) | Inline "Couldn't send the ticket..." (also below the fold until scrolled). `p1_support.png`, `p1_support_send.png` |
| Rail goal (`_railGoalDialog`) | Set a goal: 24 weddings, "96,000" revenue, Save | PASS | `users/v1.vendorGoals.2026 = {bookings:24, revenue:96000}`; widget shows "1 of 24", "$1,800 of $96,000". `p1_goal.png`, `p1_goal_saved.png` |
| Widgets sheet + Customize (`_railSheet`) | Opened Widgets; Customize; switched Quiet leads off; Done | PASS | `layout.rail` = [weather, consults, analytics, deposits, calendar, funnel, goal]; counts 8->7 / 9->10. `p1_widgets.png`, `p1_customize_off.png` |
| Payment links (`_addPaymentLink`) | Money > Add; Venmo default (Add disabled while empty); PayPal chip; `paypal.me/goldenhour`; Add PayPal | PASS | `paymentLinks:[{label:"PayPal",url:"paypal.me/goldenhour"}]`; button label follows the chip; row appears in "Your other payment methods". `p1_paylink.png`, `p1_paylink_added.png` |
| Default retainer (`_setDefaultRetainer`) | Tapped "Retainer, invoiced automatically" | NOT TESTABLE (harness) | Opens with a `.get()`; log "LAZO retainer read: [cloud_firestore/unavailable] ... client is offline" -> toast "Could not open that". No spinner while the read runs (see note). Flat-amount validation reviewed in code: bug 6. |
| Whop (`_connectWhopSheet`) | Set up Whop | PASS (failure path) / NOT TESTABLE (sheet) | Toast "Could not reach Whop: [firebase_functions/internal] internal [0]"; the biz_ id sheet only opens after the function returns an install URL. `p1_whop_wait.png` |
| Square (`_connectSquare`) | Connect Square | PASS (failure path) | Veil, then toast "internal [0]" (raw code, bug 4). `p1_square.png` |
| Upgrade / plan (`_upgradeSheet` > `_showUpgradeSheet`) | Studio > About Studio; Monthly / Pay for the year; Choose Pro Studio; tap outside | PASS | Pro marked YOUR PLAN with disabled "Your current plan"; prices flip $79/mo->$790/yr, $129/mo->$1,290/yr, "Two months free"; Choose calls createProIntent (fails, toast behind sheet - known). `_mobilePlanSheet` is native-only (kIsWeb) - NOT TESTABLE. `p1_upgrade.png`, `p1_upgrade_choose.png` |
| Starter templates + preview (`_starterLibrarySheet`, `_starterPreviewSheet`) | Studio > Browse starter templates > Wedding Photography Agreement > Add to my templates | PASS (UI) / NOT TESTABLE (write) | Library filtered to the photographer starter; preview renders headings, numbered sections, highlighted placeholders, "10 sections / 16 details" pills. Add `.add()` hits the harness gap (error below the fold, bug 3). `p1_starter.png`, `p1_starter_added.png` |
| Who I work with (`_prefsSheet`) | $4,000 min, guests From 200 Up to 50, Weddings+Elopements, Mon off, 50 mi, note; Save | PASS (write) / **BUG** (validation) | `prefs:{minBudget:4000,guestMin:200,guestMax:50,travelMiles:50,eventTypes:["wedding","elopement"],daysOff:[1],note:"Intimate weddings are my favorite"}` - min > max accepted (bug 5). Card did not refresh (harness: failed timestamp write does not notify). `p1_prefs_filled.png`, `p1_prefs_saved.png` |
| Add teammate (`_addTeammateSheet`) | Profile > Your team > Add; search "zz"; category chip | PASS (UI) / NOT TESTABLE (add) | Only `ven1` is seeded, so "No pros in this category here yet." / "No one by that name..." - picking a pro and `_editTeammate` cannot be reached. `p1_addteam.png` |
| Edit teammate (`_editTeammate`) | - | NOT TESTABLE | No team seeded / no other vendors to add. |
| Showcase (`_toggleShowcase`) | Profile > Real weddings | NOT TESTABLE | No live galleries seeded (`galleries` empty); card shows the empty copy. |
| Redeem invite (`_redeemInviteDialog`) | - | NOT TESTABLE | Only on the claim screen; the seeded vendor is already claimed. |
| Lead form | see above | NOT TESTABLE | |
| Profile editor discard (`_epTryClose`) | Discard with no edits; edit bio then Discard > Keep editing; later Discard > Discard changes | PASS | No edits: closes straight away. Edited: "Discard your changes?" with Keep editing / Discard changes; both work. `p1_discard_confirm.png` |
| Add package (`_epAddPackage`) | Name only (Add disabled), + "$2,400", "8 hours", includes; Add package; Save profile | PASS | Strength 10 -> 25; dump `packages:[{name:"The Verse",price:"$2,400",offPeak:"",hours:"8 hours",includes:"Two shooters"}]` (Save toast "Could not save" = harness timestamp gap, fields landed). `p1_addpkg.png`, `p1_addpkg_filled.png` |
| Add FAQ (`_epAddFaq`) | Question only (Add disabled), + answer, Add FAQ, Save | PASS / minor BUG | `vendorFaqs:[{q:"Are you insured?",a:"Yes, two million in liability cover."}]`. Card says "Up to 6" but the code allows 15 (bug 7). `p1_faq.png`, `p1_faq_added.png` |
| Preferred vendor (`_epPickPreferred`) | Add a vendor; searched "golden" | PASS (UI) / NOT TESTABLE (pick) | Hint before search, "No vendors start with that name" after (own listing excluded; nothing else seeded). Code review: no duplicate check (bug 8). `p1_pref.png`, `p1_pref_search.png` |
| Gallery upload limit | Read the gallery card ("0 of 10") and `_epUploadGalleryPhotos` | NOT TESTABLE (file picker) / **BUG** (code) | Pro vendor capped at 10 with copy promising more "with Lazo Pro" (bug 9). |

## Bugs

### 1. Consult scheduler can never be saved (Nested arrays) - HIGH
Steps: Account > Consult scheduler > change anything (or nothing) > Save scheduler.
Expected: `vendors/ven1.scheduler` written, sheet closes, toast "Scheduler is live at ...".
Actual: inline error "Could not save: Invalid argument: Nested arrays are not supported.: Instance of 'JSArray<List<String>>'"; nothing written.
Code: `_schedulerSheet` > `save()` writes `'hours': hours` where `hours` is `Map<String, List<List<String>>>` (each day a list of `[start, end]` lists). Firestore rejects arrays inside arrays. Store each window as a map (`{'from':'09:00','to':'17:00'}`) or a "09:00-17:00" string, and read both shapes back in the loader (it currently expects `List` of `List`). The public booking page / functions that read `scheduler.hours` need the same shape change.

### 2. Bug report / support carry a stale build id - LOW
`kBuildId = 'JC-LAZO-VDASH-0915-177'` in Vendor v197; the bug sheet says "We attach your plan, build 177" and every ticket's `context.build` is 177. Bump it with each version.

### 3. Errors in long popups render below the fold on phone - LOW
In Report a bug and Support (and the scheduler) the inline error (`_onbError` / `_pv3Err` at the end of the scrolling body) appears under the fold; on a 375x812 phone tapping Send looks like nothing happened until you scroll. Suggest scrolling the body to the end when `err` is set, or showing the error just above the footer.

### 4. Raw function error codes shown to vendors - LOW
Connect Square toasts just "internal [0]"; Whop "Could not reach Whop: [firebase_functions/internal] internal [0]"; MCP
"Could not create the link: [firebase_functions/internal] internal [0]". `_connectSquare` uses `e.message` verbatim,
`_connectWhopSheet` / `_mcpSheet` append `_errText(e)`. Map `internal` / `unavailable` / `deadline-exceeded` to plain copy
("Square didn't answer - try again in a minute.").

### 5. "Who I work with" accepts a guest range where From > Up to - LOW/MED
Steps: Profile > Who I work with > From 200, Up to 50 > Save. Written as `guestMin:200, guestMax:50`; every lead's Fit grade
and the public "200-50 guests" line use it. `_prefsSheet.save()` has no check; swap or block with an inline error.

### 6. Flat retainer can be saved as $0 - LOW (code review; the sheet could not open in the harness)
`_setDefaultRetainer.save()`: `num.tryParse(flatC.text) ?? 0` with no check, so "A flat amount" + empty/"abc" saves
`retainerMode:'flat', defaultRetainer:0` and toasts "Saved - $0 at signing."; the card then reads "Set". Disable Save or show
an inline error when mode is flat and the amount is not > 0. (Also: subtitle says "Set your own" but only 25/30/50% chips exist.)

### 7. FAQ card says "Up to 6", code allows 15 - LOW
Your FAQs card: "...shown on your profile. Up to 6."; `_epAddFaq` stops at 15 ("Up to 15 FAQs on a profile.").

### 8. Preferred vendor picker allows the same vendor twice - LOW (code review)
`_epPickPreferred` > `resultRow.onTap` adds `r` without checking `_epPreferred` for the same `placeId` (the team flow does check).
Filter results already in `_epPreferred` or toast "already added".

### 9. Gallery cap ignores the paid tier - LOW/MED (code review)
`_epGalleryCap => _isAdminUser ? 30 : 10`. Golden Hour Studio is `tier:'pro'` and the card reads "0 of 10"; at the cap a Pro
vendor gets "Free profiles include 10 photos. Unlimited gallery is coming with Lazo Pro." - wrong for someone already on Pro.
Either raise the cap for pro/studio or change the copy.

### 10. Profile editor: SwitchListTiles without a Material ancestor - LOW
Scrolling the editor logs "ListTile background color or ink splashes may be invisible" (x8) plus one
`Assertion failed: rendering/object.dart:3687`. Source: the `SwitchListTile`s in Style & specialties / lead alerts / auto-replies
(lines ~8419-8556) sit in `_epCard` containers with a fill colour; wrap each card body in `Material(type: MaterialType.transparency)`.

### 11. Floating dashboard button covers "Save profile" on phone - LOW
The round grid FAB (bottom-right) overlaps the right end of the editor's Save profile button (`tmp.png` / `p1_saveprofile.png`).
Hide the FAB while `_editingProfile`, or pad the save bar.

### 12. Dark mode: brand swatches show the wrong colours - MED (look and feel)
Steps: `open vendor dark` > Account > Your brand. Accent swatches Blush, Ivory, Lilac, Champagne, Terracotta render as dark
browns/navy instead of their real light colours (only Gold, Sage and Sky look right); the selected-swatch ring (`_lzLine(ink)`)
is nearly invisible on the dark sheet. Evidence: `k_v_2.png` (vs light `p1_brand.png`).
Code: `_brandSheet` > `swatchRow` paints `color: _lzBg(_hexColor(w[0], plum))` - `_lzBg` remaps light backgrounds to the dark
palette, which is right for surfaces but wrong for a colour picker. Use the raw `_hexColor(...)` for swatches and the preview
(`_lzBg(pCol)`, `_lzBg(aCol)` and `_lzFg(aCol)` in the preview have the same problem once a light accent is chosen), and give
the selected ring a fixed contrasting colour (e.g. gold).

## Part 2 - look and feel

### Desktop (LZ_VIEW=desktop, 1280x860)
| Dashboard | Popups opened | Centred card | Scrolls | Closes on outside click | Evidence |
|---|---|---|---|---|---|
| Vendor | June's feed, Your brand, Consult scheduler, Team, Calendar feed, Connect Claude/ChatGPT, Ideas, Support (8) | PASS - all centred cards with rounded border, none stretched | PASS - scheduler body scrolls with the footer pinned | PASS - all 8 | `d_grid1.png`, `d_grid2.png`, `d_grid3.png` |
| Couple | Plan together, From June (bell), Your widgets (scrolled), Budget, RSVPs, Vendor team, Payments due, Weather (8) | PASS | PASS - widgets sheet scrolls | PASS - all 8 | `d_grid4.png`, `d_grid5.png` |

### Dark mode, phone
| Dashboard | Popups checked | Result | Evidence |
|---|---|---|---|
| Couple (`open couple dark`) | From June, Your widgets (+ scrolled: countdown, weather, RSVPs), Countdown mini, Who's getting married (June step 1 of 5), payment card in the Golden Hour Studio thread, Ask June page | PASS - text readable, no white boxes, no dark-on-dark | `k_grid1.png`, `k_grid2.png`, `k_grid3.png` |
| Vendor (`open vendor dark`) | From June, Your brand, Consult scheduler, Team, Support, Report a bug, Ideas + composer | PASS except Your brand (bug 12) | `k_grid4.png`, `k_grid5.png`, `k_v_10.png`, `k_grid6.png` |

Phone note: tall phone sheets (scheduler, Report a bug) reach the top of the screen, so "tap outside" has nowhere to land;
X / Cancel / drag handle close them. Not a bug, just how a full-height sheet behaves.

## Seen in passing (outside my area, not counted)
- Couple, phone (light and dark): the "This week, with June" card squeezes its serif title into a 1-word-per-line column next to
  the Ask June / Talk to June buttons (`k_grid3.png` left).
- Same invoice, two due dates: vendor Money card "Balance · $1,300 Due Oct 18"; couple thread payment card "Due 10/17/2026".
  Looks like a UTC vs local date conversion on one side.
- Vendor Get paid card still offers "Accept cards with Stripe / Connect Stripe", and the Whop turn-off veil says "Stripe or
  Square takes over if connected." (Jesse does not use Stripe.)
- Profile editor header on phone says "The preview on the right updates as you edit." There is no preview on the right at phone width.

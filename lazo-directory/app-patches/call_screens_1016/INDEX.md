# Lazo video call: screenshots (2026-10-16)

The in-call screens are the real call screen (`_LazoCallScreen`, identical in Couple v166 / Vendor v206, commit 4999eb14). They ran against the live call service on a throwaway call with test tokens. No accounts, no threads, nothing written to Firestore. The coloured "VENDOR CAM / COUPLE CAM" pictures are a test camera, because the test browser has no real camera. "call test" in the watermark is the harness's placeholder call id; a real call shows the first 6 characters of its call id.

The dashboard screens (01, 02, 05, 06) are Couple v166 / Vendor v206 rendered with in-memory sample data and fake functions.

| File | What it shows |
|---|---|
| 01a_couple_phone_thread_video_button_join.jpg | Couple, phone: the thread with the new video button in the header, the vendor's "Started a Lazo video call." and the "Join the video call" button. |
| 01b_vendor_desktop_thread_video_shield_join.jpg | Vendor, desktop: the thread header with the video button and the shield (report / block), and "Join the video call" under the couple's invite. |
| 02a_couple_phone_confirm_number.jpg | Couple, phone: first call only, "Confirm your phone" with the mobile number. |
| 02b_couple_phone_confirm_code.jpg | Couple, phone: the 6-digit code step ("We texted a 6-digit code to (480) ***-1212"). |
| 05a_vendor_report_or_block_sheet.jpg | Vendor: Report or block (also opened by "Leave + report" in a call), with the money-demand advice and the reasons. |
| 05b_vendor_report_sending.jpg | Vendor: reason picked, "Report and block" sending. (In the harness the report isn't saved, so the closed-thread strip that follows in the real app isn't shown.) |
| 06_vendor_desktop_thread_dark_mode.jpg | Vendor, dark mode: the same thread. The call screen itself is always dark (03/04). |
| 03a_vendor_phone_waiting.jpg | Vendor, phone: just joined, waiting for the couple. Both cameras off; "Let them use camera" at the top. |
| 03b_vendor_phone_couple_camera_locked.jpg | Vendor, phone: their own camera on (watermarked "Lazo · from Golden Hour Studio · time · call"); the couple is connected but their camera is still locked. |
| 03c_vendor_phone_couple_video_blurred.jpg | Vendor, phone: after "Let them use camera", the couple's video arrives blurred behind "Show Avery & Jordan's video". The watermark is on top. |
| 03d_vendor_phone_revealed_both_on.jpg | Vendor, phone: after tapping Show, both feeds are live and watermarked. Controls: Mute, Camera off, Hide their video, Leave, Leave + report. |
| 03e_vendor_desktop_revealed_both_on.jpg | Vendor, desktop: same state side by side. |
| 04a_couple_desktop_camera_locked.jpg | Couple, desktop: connected, own camera "Camera locked" (the vendor hasn't allowed it). |
| 04b_couple_phone_locked_vendor_on.jpg | Couple, phone: the vendor's video with the watermark; own camera still locked. |
| 04c_couple_phone_locked_no_hint.jpg | Couple, phone: before the vendor's video arrives; the locked state has no explanation (see fix 4). |
| 04d_couple_phone_camera_allowed.jpg | Couple, phone: the vendor allowed the camera, and the button now reads "Camera on". |
| 04e_couple_phone_camera_on.jpg | Couple, phone: the couple's camera is on; both tiles watermarked. |

## Fix proposals (nothing changed or deployed; waits on Jesse's OK)
1. **Vendor header on a phone (03a-03d):** "Lazo video call · Avery & Jordan" wraps to two lines beside "Let them use camera". Put the name on its own line and the camera control on a second row, or shorten the title to just the name.
2. **"Their video hidden" before any video exists (03a-03c):** this label shows even when the couple has no camera on. Hide or disable it until their video arrives.
3. **"Leave + report" drops to a second row on a phone** when the labels are long (03a-03c), and fits when they're short (03d). Use a fixed five-button row with shorter labels ("Report").
4. **The couple's locked camera has no explanation once both are connected (04a, 04c, 04d).** Show a steady line, "Golden Hour Studio turns your camera on when they're ready", and when it's allowed, a short notice: "You can turn your camera on now".
5. **Robustness, found while shooting:** if a vendor's request to the call service never answers, the app's media queue can stall, so a video that arrives later never shows (it came back after rejoining). Add a timeout to every call-service request and recover the queue. This matters on bad networks.
6. **Dark mode (06):** "Join the video call" is dark plum on a near-black background; use the gold/light style there.
7. **Desktop watermark (03e):** small and dense at desktop size. Make the font a little bigger and the rows sparser on wide tiles.
8. **Not from the call work:** the vendor inbox's tag row overflows by 23 px (Nora & Eli card, 01b and 06, visible in debug builds).

## Schedule call + audio only (Couple v167 / Vendor v207, commit 01f18d8f; NOT deployed)
Dashboard shots use the harness with sample scheduled calls and fake functions. In-call shots ran against the live call service with test tokens.

| File | What it shows |
|---|---|
| 07a_couple_phone_thread_schedule_button_card.jpg | Couple, phone (vendor on Pro): the Schedule button (calendar) next to the video button, "Join with video / Join with audio only" under an invite, and a scheduled-call card. |
| 07b_couple_phone_card_upcoming.jpg | The card for an upcoming call: your time, the vendor's time, "Join opens 10 minutes before", Add to calendar, Reschedule, Cancel, "I prefer audio only". |
| 07c_couple_phone_card_open_now.jpg | The same card from 10 minutes before the start: "Open now" with Join with video / Join with audio only. |
| 08_couple_phone_free_vendor_no_schedule.jpg | Couple with a Free vendor: no Schedule button, only the video button (start a call now). |
| 09a_vendor_desktop_card_both_timezones_prefers_audio.jpg | Vendor: the card shows "3:00 PM (your time)" and "That's Saturday at 5:00 PM EST for Maya & Leo", plus "Prefers audio only". |
| 10a_vendor_desktop_schedule_picker.jpg | The schedule picker: day, time in your own time zone, length (15/30/45/60). Couples also get "I prefer audio only". |
| 10b_vendor_desktop_join_chooser.jpg | The video button now asks: Join with video / Join with audio only. |
| 11a_vendor_free_schedule_pro_badge_closeup.png | Free vendor: the Schedule button with its PRO badge. |
| 11b_vendor_free_upgrade_sheet.jpg | Free vendor taps it and gets the existing plan sheet. |
| 12a_vendor_phone_incall_audio_only_prefers_audio.jpg | In call, vendor: nobody on camera, so both people show as avatars with a speaking ring. "Prefers audio only" replaces "Let them use camera". (That chip is simulated in the harness: the live call service doesn't have the preference until this is deployed.) |
| 12b_couple_phone_incall_audio_only.jpg | In call, couple: the same audio-only view, with the "Audio only" toggle next to "Camera locked". |

### More fix proposals (schedule / audio only)
9. **Couple thread header on a phone:** with the extra Schedule button, the vendor's name wraps to two lines (07a). Move Schedule into the "…" menu on narrow screens, or shrink the icons.
10. **Card buttons on a phone:** "Cancel" drops to its own row (07b). Use a "More" menu for Reschedule / Cancel.
11. **PRO badge** (11a): too small to read; make it bigger, or show "Pro" beside the icon.
12. **Plan sheet** (11b): add "Schedule Lazo video calls" to the Pro list, so the upsell matches the tap.
13. **Speaking ring:** it lit for yourself; the other person's ring didn't light in the test, probably because the background test tab is silent. Check on two real devices.
14. **Phone-width harness:** opening a sheet from the thread header closed the thread, the same as the existing "…" menu does. That looks like the harness rather than the change, but confirm on a phone after the paste.
15. **Fixed in this round:** scheduled calls now carry the couple's name, so the vendor's "Upcoming consults" card shows it instead of "A couple".

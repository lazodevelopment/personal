# Couple v168 / Vendor v208: the fixes, as they look now (2026-10-16)

The in-call shots ran against the live call service with test tokens (test camera pictures, no accounts). The dashboard shots use the harness with sample data.

| File | Fix | What it shows |
|---|---|---|
| a1_couple_phone_locked_hint_one_row.jpg | 3, 4 | Couple: "Golden Hour Studio turns your camera on when they're ready." under the name; Mute / Locked / Audio only / Leave on one row. |
| a2_vendor_phone_two_row_header_one_row_controls.jpg | 1, 2, 3 | Vendor: the couple's name on its own line, "Let them use camera" on the next; no Show/Hide button before there's video; the controls on one row. |
| a3_couple_phone_camera_allowed_notice.jpg | 4 | Couple, right after the vendor allows it: "You can turn your camera on now." |
| a4_vendor_phone_five_buttons_show_video.jpg | 2, 3 | Vendor with the couple's video in: blurred, and five buttons on one row (Mute, Stop video, Show video, Leave, Report). |
| a5_vendor_desktop_watermark_bigger.jpg | 7 | Desktop: a bigger, sparser watermark on the wide tiles. |
| b1_vendor_dark_gold_join_inbox_tags_wrap.jpg | 6, 8 | Dark mode: "Join with video" in gold; Nora & Eli's tags wrap to a second line (no overflow). |
| b2_vendor_free_pro_pill.png | 11 | Free vendor: a readable "Pro" pill beside the Schedule icon. |
| b3_plan_sheet_schedule_bullet.jpg | 12 | The plan sheet lists "Schedule Lazo video calls with reminders for both of you" under Pro. |
| b4_couple_phone_header_fits_card_more.jpg | 9, 10 | Couple on a phone: the vendor's name fits on one line (Schedule moved into the ... menu); the card shows "Add to calendar" and "More". |
| b5_couple_phone_card_more_menu.jpg | 10 | "More" opens Reschedule / Cancel the call. |

Fix 5 (timeouts + a queue that can't stall) has no screen. It's covered by test/call_queue_test.dart: a stuck step is given up and the next step still runs (3/3).

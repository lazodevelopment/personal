#!/usr/bin/env python3
"""JC-ATV-PAY-0927: 24-hour heads-up before the scheduled balance charge.

Run from ~/bs:  python3 patch_balance_heads_up.py
Anchor-and-assert: every edit must find its anchor exactly once or the script
stops without writing anything.

1. lib/emails.py  — new balance_heads_up() email.
2. main.py        — _send_balance_heads_up(db, now): the run 24 h before a
                    card-on-file balance falls due emails the couple once and
                    stamps balance_heads_up_sent_at. Wired into charge_balances
                    ahead of the charge loop.
3. main.py        — the no-card branch now emails the owner when a Zoho payment
                    link fails to mint (previously only print()).
"""
import pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
edits = []   # (path, anchor, replacement)

# ------------------------------------------------------------ 1. emails.py --
EMAIL_ANCHOR = "def balance_charge_failed(api_key, booking, amount, attempt, max_attempts,"
EMAIL_NEW = '''def balance_heads_up(api_key, booking, amount, when="tomorrow morning"):
    """Sent by charge_balances the run before a card-on-file balance falls
    due. The welcome email named the date weeks ago; this is the reminder so
    the charge never surprises anyone, and it gives an expired card a day to
    be swapped before it declines."""
    first = booking["client_names"].split("&")[0].strip().split()[0]
    card = (f"your {booking.get('card_brand','card')} "
            f"\\u2022\\u2022\\u2022\\u2022{booking['card_last4']}"
            if booking.get("card_last4") else "the card on file")
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ATAVIA WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>A quick heads-up: <b>{when}</b> we'll charge your remaining balance of
      <b>${amount:,.2f}</b> to {card}, exactly as scheduled in your agreement.
      Once it goes through, your package is paid in full and you'll get a
      receipt from us.</p>
      <table style="width:100%;border-collapse:collapse;margin:20px 0">
        <tr><td style="padding:3px 14px 3px 0;color:#6B6B6B;font-size:12px">Package</td>
            <td style="padding:3px 0;font-size:13px">{booking.get('package_name','')}</td></tr>
        <tr><td style="padding:3px 14px 3px 0;color:#6B6B6B;font-size:12px">Wedding date</td>
            <td style="padding:3px 0;font-size:13px">{booking.get('event_date','')}</td></tr>
        <tr><td style="padding:3px 14px 3px 0;color:#6B6B6B;font-size:12px">Amount</td>
            <td style="padding:3px 0;font-size:13px">${amount:,.2f}</td></tr>
      </table>
      <p><b>Nothing for you to do</b> &mdash; unless that card has changed or
      you'd rather use a different one. If so, just reply to this email today
      and we'll sort it out before the charge runs.</p>
      <p>It will appear on your statement as <b>Atavia Weddings</b>.</p>
      <p style="color:#B0713F">&mdash; The Atavia Weddings Team<br>
      (336) 537-9590 &middot; ataviaweddings.com</p>
    </div>"""
    return _send(api_key, booking["email"],
                 f"Heads-up: your balance is scheduled for {when} "
                 f"\\u2014 {booking.get('event_date','')}", html)


'''
edits.append(("lib/emails.py", EMAIL_ANCHOR, EMAIL_NEW + EMAIL_ANCHOR))

# ----------------------------------------------- 2. main.py: helper + call --
FN_ANCHOR = "# ========================================================= charge_balances =="
FN_NEW = '''def _send_balance_heads_up(db, now):
    """Email couples whose card-on-file balance falls due within the next 24 h
    (i.e. it will be charged on tomorrow's 07:00 run). Once per booking, stamped
    in balance_heads_up_sent_at. No-card bookings get a payment link instead of
    a charge, so they are skipped here."""
    from google.cloud.firestore_v1.base_query import FieldFilter
    soon = (db.collection("bookings")
              .where(filter=FieldFilter("status", "==", "confirmed"))
              .where(filter=FieldFilter("payment_option", "==", "standard"))
              .where(filter=FieldFilter("balance_due_at", ">", now))
              .where(filter=FieldFilter("balance_due_at", "<=", now + timedelta(hours=24)))
              .get())
    for snap in soon:
        b = snap.to_dict()
        if (b.get("balance_paid_at") or b.get("balance_heads_up_sent_at")
                or b.get("test_mode")
                or not (b.get("zoho_payment_method_id") and b.get("zoho_customer_id"))):
            continue
        try:
            emails.balance_heads_up(RESEND_API_KEY.value, b, b["balance"])
            snap.reference.update({"balance_heads_up_sent_at": firestore.SERVER_TIMESTAMP})
            emails.notify_owner(
                RESEND_API_KEY.value, OWNER_EMAIL,
                f"BALANCE HEADS-UP SENT \\u2014 {b['client_names']} \\u2014 ${b['balance']:,}",
                [f"Booking {b['booking_id']}: the couple was told their balance "
                 f"charges tomorrow morning. Charge runs on the next 07:00 job."])
        except Exception as e:
            print(f"balance heads-up failed {b['booking_id']}: {e}")


'''
edits.append(("main.py", FN_ANCHOR, FN_NEW + FN_ANCHOR))

CALL_ANCHOR = '''    db = firestore.client()
    now = datetime.now(timezone.utc)
    from google.cloud.firestore_v1.base_query import FieldFilter
    due = (db.collection("bookings")'''
CALL_NEW = '''    db = firestore.client()
    now = datetime.now(timezone.utc)
    try:
        _send_balance_heads_up(db, now)   # 24 h notice before tomorrow's charge
    except Exception as e:
        print(f"balance heads-up sweep failed: {e}")
    from google.cloud.firestore_v1.base_query import FieldFilter
    due = (db.collection("bookings")'''
edits.append(("main.py", CALL_ANCHOR, CALL_NEW))

# ------------------------------- 3. main.py: owner alert on link failure --
LINK_ANCHOR = '''            except Exception as e:
                snap.reference.update({
                    "balance_attempts": b.get("balance_attempts", 0) + 1,
                    "balance_last_error": str(e)[:500]})
                print(f"balance link failed {b['booking_id']}: {e}")
            continue'''
LINK_NEW = '''            except Exception as e:
                attempts = b.get("balance_attempts", 0) + 1
                snap.reference.update({
                    "balance_attempts": attempts,
                    "balance_last_error": str(e)[:500]})
                print(f"balance link failed {b['booking_id']}: {e}")
                # Previously print-only: two unbilled couples sat here for
                # weeks with nobody told (JC-ATV-PAY-0927).
                try:
                    emails.notify_owner(
                        RESEND_API_KEY.value, OWNER_EMAIL,
                        f"BALANCE LINK FAILED (attempt {attempts}/3) \\u2014 "
                        f"{b['client_names']} \\u2014 ${b['balance']:,}",
                        [f"Booking {b['booking_id']} has no card on file and Zoho "
                         f"refused to create a payment link: {str(e)[:300]}",
                         "Bill them from the Zoho dashboard by hand." if attempts >= 3
                         else "Will retry tomorrow."])
                except Exception as e2:
                    print(f"balance link owner alert failed: {e2}")
            continue'''
edits.append(("main.py", LINK_ANCHOR, LINK_NEW))

# ------------------------------------------------------------------ apply --
texts = {}
for path, anchor, _ in edits:
    t = texts.setdefault(path, (ROOT / path).open(encoding="utf-8", newline="").read())
    n = t.count(anchor)
    if n != 1:
        sys.exit(f"ABORT: anchor found {n}x in {path}:\n{anchor[:90]}")
if "def balance_heads_up(" in texts["lib/emails.py"] or "_send_balance_heads_up" in texts["main.py"]:
    sys.exit("ABORT: patch already applied")
for path, anchor, new in edits:
    texts[path] = texts[path].replace(anchor, new, 1)
for path, t in texts.items():
    (ROOT / path).open("w", encoding="utf-8", newline="").write(t)
    print("patched", path)

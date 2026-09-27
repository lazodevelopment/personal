"""Resend transactional email — Atavia booking flow.

Requires the ataviaweddings.com domain verified in Resend (Resend already in
the Danbren stack; verify domain status before first live send).
"""

import requests

API = "https://api.resend.com/emails"
FROM = "Atavia Weddings <info@ataviaweddings.com>"


def _send(api_key, to, subject, html, reply_to="info@ataviaweddings.com"):
    r = requests.post(API, json={
        "from": FROM, "to": [to] if isinstance(to, str) else to,
        "subject": subject, "html": html, "reply_to": reply_to,
    }, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
    r.raise_for_status()
    return r.json()


def welcome_email(api_key, booking, q_link=None):
    first = booking["client_names"].split("&")[0].strip().split()[0]
    plan = booking["payment_option"]
    if plan == "standard":
        money_line = (
            f"Your remaining balance of <b>${booking['balance']:,}</b> will be "
            f"automatically charged to your card on file on "
            f"<b>{booking['balance_due_date']}</b>, exactly as outlined in "
            f"your agreement — nothing for you to do."
        )
    else:
        money_line = ("Your package is <b>paid in full</b> — nothing further "
                      "is due. Enjoy the planning!")
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ATAVIA WEDDINGS</h1>
      <p>Hi {first},</p>
      <p><b>Your date is officially reserved.</b> We're honored to be part of
      your day on <b>{booking['event_date']}</b>.</p>
      <p>{money_line}</p>
      <p><b>One thing we need from you:</b> your Wedding Day Questionnaire —
      venues, timeline, key people, must-have shots. It takes about ten
      minutes and helps us capture everything perfectly. Please complete it
      at least two weeks before your date.</p>
      QBTN_PLACEHOLDER
      <p>If any details change afterward — venues, times, guest count — just
      reopen the same link and update your answers.</p>
      <p>Your signed agreement is attached to the signature confirmation you
      received separately. Keep it handy.</p>
      <p style="color:#B0713F">— The Atavia Weddings Team<br>
      (336) 537-9590 · ataviaweddings.com</p>
    </div>"""
    qbtn = ("" if not q_link else
            '<p style="text-align:center;margin:22px 0">'
            f'<a href="{q_link}" style="background:#B0713F;color:#FAF7F2;'
            'padding:14px 30px;text-decoration:none;letter-spacing:2px;'
            'font-family:Arial,sans-serif;font-size:13px">'
            'COMPLETE YOUR QUESTIONNAIRE</a></p>')
    html = html.replace("QBTN_PLACEHOLDER", qbtn)
    return _send(api_key, booking["email"],
                 "Your date is reserved! — Atavia Weddings", html)


def notify_owner(api_key, owner_email, subject, lines):
    html = "<div style='font-family:monospace'>" + "<br>".join(lines) + "</div>"
    return _send(api_key, owner_email, subject, html)


def gratuity_receipt(api_key, booking, amount):
    first = booking["client_names"].split("&")[0].strip().split()[0]
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ATAVIA WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>Thank you so much for your generosity. Your gratuity of
      <b>${amount:,.2f}</b> has been received and 100% of it goes directly to
      the team who served your event.</p>
      <p>It means the world to them — truly.</p>
      <p style="color:#B0713F">— The Atavia Weddings Team</p>
    </div>"""
    return _send(api_key, booking["email"],
                 "Thank you for your gratuity — Atavia Weddings", html)


def gratuity_invite(api_key, booking, link):
    first = booking["client_names"].split("&")[0].strip().split()[0]
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ATAVIA WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>Congratulations again — we hope your wedding day was everything you imagined.
      It was an honor to capture it.</p>
      <p>One small note: our team members don't accept cash tips at events. If the people
      who served your day made it special and you'd like to recognize them,
      you can do so here — <b>100% goes directly to your event team</b>:</p>
      <p style="text-align:center;margin:26px 0">
        <a href="{link}" style="background:#B0713F;color:#FAF7F2;padding:14px 30px;
        text-decoration:none;letter-spacing:2px;font-family:Arial,sans-serif;
        font-size:13px">THANK THE TEAM</a></p>
      <p>Entirely optional, always appreciated, never expected. Your gallery and films
      are on their way per your agreement — we'll be in touch.</p>
      <p style="color:#B0713F">— The Atavia Weddings Team</p>
    </div>"""
    return _send(api_key, booking["email"],
                 f"Thank you, {first} — from all of us at Atavia", html)


def questionnaire_reminder(api_key, booking, link, days_left):
    first = booking["client_names"].split("&")[0].strip().split()[0]
    urgency = ("is coming up fast" if days_left <= 15 else "is approaching")
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ATAVIA WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>Your wedding on <b>{booking['event_date']}</b> {urgency} — and we still
      need your Wedding Day Questionnaire so we can plan your coverage down to
      the minute. It takes about ten minutes:</p>
      <p style="text-align:center;margin:26px 0">
        <a href="{link}" style="background:#B0713F;color:#FAF7F2;padding:14px 30px;
        text-decoration:none;letter-spacing:2px;font-family:Arial,sans-serif;
        font-size:13px">COMPLETE YOUR QUESTIONNAIRE</a></p>
      <p>Per your agreement, we need your day-of details at least fourteen (14)
      days before your wedding. Questions? Just reply to this email.</p>
      <p style="color:#B0713F">— The Atavia Weddings Team</p>
    </div>"""
    return _send(api_key, booking["email"],
                 f"Your questionnaire — {booking['event_date']}", html)


def questionnaire_summary(api_key, owner_email, booking, answers, sections):
    rows = ""
    for sec_title, fields in sections:
        rows += (f'<tr><td colspan="2" style="padding:14px 0 4px;color:#B0713F;'
                 f'font-family:Arial;font-size:12px;letter-spacing:2px">'
                 f'{sec_title.upper()}</td></tr>')
        for fid, label in fields:
            val = (answers.get(fid) or "").strip() or "—"
            rows += (f'<tr><td style="padding:3px 14px 3px 0;color:#6B6B6B;'
                     f'font-size:12px;vertical-align:top;white-space:nowrap">{label}</td>'
                     f'<td style="padding:3px 0;font-size:13px">{val}</td></tr>')
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:640px;margin:0 auto">
      <h2 style="font-weight:normal">Questionnaire — {booking['client_names']}</h2>
      <p style="color:#6B6B6B">{booking['package_name']} · {booking['event_date']}
      · booking {booking['booking_id']}</p>
      <table style="width:100%;border-collapse:collapse">{rows}</table>
    </div>"""
    return _send(api_key, owner_email,
                 f"QUESTIONNAIRE RECEIVED — {booking['client_names']} — "
                 f"{booking['event_date']}", html)


def signature_nudge(api_key, booking, signing_url):
    first = booking["client_names"].split("&")[0].strip().split()[0]
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ATAVIA WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>Your service agreement for <b>{booking['event_date']}</b> is signed-ready
      and waiting — but your date isn't reserved until it's signed and the $500
      retainer is paid. Dates are first-come, first-served, and popular
      {booking.get('event_date','').split(',')[0]} dates go quickly.</p>
      <p style="text-align:center;margin:26px 0">
        <a href="{signing_url}" style="background:#B0713F;color:#FAF7F2;padding:14px 30px;
        text-decoration:none;letter-spacing:2px;font-family:Arial,sans-serif;
        font-size:13px">REVIEW &amp; SIGN</a></p>
      <p>Changed your mind or have questions first? Just reply — a real person reads
      every message.</p>
      <p style="color:#B0713F">— The Atavia Weddings Team</p>
    </div>"""
    return _send(api_key, booking["email"],
                 f"Your date isn't reserved yet — {booking['event_date']}", html)


def payment_nudge(api_key, booking):
    first = booking["client_names"].split("&")[0].strip().split()[0]
    amount = booking.get("invoice_amount", booking.get("retainer", 500))
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ATAVIA WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>You're one step from officially locking in <b>{booking['event_date']}</b> —
      your agreement is signed, and only the <b>${amount:,} retainer</b> remains.
      Until it's paid, your date stays open to other couples.</p>
      <p>Your secure payment link is in the invoice email from our payment processor
      (the charge appears as <b>Danbren Media LLC</b>). Can't find it? We've just
      re-sent it — check spam too.</p>
      <p>Any trouble with the payment link, reply here and we'll sort it personally.</p>
      <p style="color:#B0713F">— The Atavia Weddings Team</p>
    </div>"""
    return _send(api_key, booking["email"],
                 f"One step left to reserve {booking['event_date']}", html)


def balance_receipt(api_key, booking, amount, last4=None):
    """Sent to the client when the remaining balance is charged to the card on
    file. The welcome email promises this charge on a named date, so it should
    not land silently."""
    first = booking["client_names"].split("&")[0].strip().split()[0]
    card = f" ending in {last4}" if last4 else " on file"
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ATAVIA WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>Your remaining balance of <b>${amount:,.2f}</b> has been charged to the
      card{card}, as scheduled in your agreement. <b>Your package is now paid in
      full</b> — nothing further is due.</p>
      <table style="width:100%;border-collapse:collapse;margin:22px 0;font-size:13px">
        <tr><td style="padding:4px 14px 4px 0;color:#6B6B6B">Package</td>
            <td style="padding:4px 0">{booking.get('package_name','')}</td></tr>
        <tr><td style="padding:4px 14px 4px 0;color:#6B6B6B">Wedding date</td>
            <td style="padding:4px 0">{booking.get('event_date','')}</td></tr>
        <tr><td style="padding:4px 14px 4px 0;color:#6B6B6B">Amount charged</td>
            <td style="padding:4px 0">${amount:,.2f}</td></tr>
        <tr><td style="padding:4px 14px 4px 0;color:#6B6B6B">Booking</td>
            <td style="padding:4px 0">{booking.get('booking_id','')}</td></tr>
      </table>
      <p>The charge appears on your statement as <b>Danbren Media LLC</b>.
      Questions about it? Just reply — a real person reads every message.</p>
      <p style="color:#B0713F">— The Atavia Weddings Team<br>
      (336) 537-9590 · ataviaweddings.com</p>
    </div>"""
    return _send(api_key, booking["email"],
                 f"Payment received — your balance is settled ({booking.get('event_date','')})",
                 html)


def balance_charge_failed(api_key, booking, amount, attempt, max_attempts,
                          update_link=None):
    """Sent to the client when the scheduled balance charge is declined.

    Without this the couple never learns anything went wrong — only the studio
    is alerted — so an expired card goes unnoticed until someone calls them.
    Deliberately blame-free and free of contractual threats: the tone stays
    'this happens, here is the fix'.
    """
    first = booking["client_names"].split("&")[0].strip().split()[0]
    retrying = attempt < max_attempts
    next_line = (
        "We'll automatically try the same card again tomorrow morning, so if "
        "it was a temporary hold or a daily limit, it may simply go through."
        if retrying else
        "We've tried a few times now, so we won't attempt it again "
        "automatically — we'd rather sort it out with you directly."
    )
    action = ('<p style="text-align:center;margin:26px 0">'
              f'<a href="{update_link}" style="background:#B0713F;color:#FAF7F2;'
              'padding:14px 30px;text-decoration:none;letter-spacing:2px;'
              'font-family:Arial,sans-serif;font-size:13px">'
              'UPDATE YOUR CARD</a></p>'
              if update_link else
              '<p><b>To sort it out:</b> just reply to this email and we\'ll send '
              'a secure link to update the card or take payment another way.</p>')
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ATAVIA WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>A quick heads-up: we tried to charge the remaining balance of
      <b>${amount:,.2f}</b> for <b>{booking.get('event_date','')}</b> to the card
      on file, and the payment didn't go through. Usually it's something small —
      an expired card, a new number, or the bank flagging an unfamiliar charge.</p>
      <p>{next_line}</p>
      {action}
      <p><b>Your date and your coverage are not affected</b> — this is only about
      the payment method. We just didn't want you to find out from a bank alert.</p>
      <p style="color:#B0713F">— The Atavia Weddings Team<br>
      (336) 537-9590 · ataviaweddings.com</p>
    </div>"""
    return _send(api_key, booking["email"],
                 f"We couldn't process your balance payment — {booking.get('event_date','')}",
                 html)

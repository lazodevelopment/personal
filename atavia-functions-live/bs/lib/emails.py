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


def payment_nudge(api_key, booking, pay_url=None):
    first = booking["client_names"].split("&")[0].strip().split()[0]
    amount = booking.get("invoice_amount", booking.get("retainer", 500))
    if pay_url:
        link_para = (f'<p><a href="{pay_url}" style="color:#B0713F"><b>Pay the '
                     f'retainer securely here</b></a> (card or bank transfer; '
                     f'the charge appears as <b>Atavia Weddings</b>).</p>')
    else:
        link_para = ('<p>Your secure payment link is in the email from our payment '
                     'processor (the charge appears as <b>Atavia Weddings</b>). '
                     "Can't find it? Check spam, or reply here.</p>")
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ATAVIA WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>You're one step from officially locking in <b>{booking['event_date']}</b> —
      your agreement is signed, and only the <b>${amount:,} retainer</b> remains.
      Until it's paid, your date stays open to other couples.</p>
      {link_para}
      <p>Any trouble with the payment link, reply here and we'll sort it personally.</p>
      <p style="color:#B0713F">— The Atavia Weddings Team</p>
    </div>"""
    return _send(api_key, booking["email"],
                 f"One step left to reserve {booking['event_date']}", html)


def card_recovery(api_key, lead, resume_url, second=False, code=None):
    """Couple filled the booking form but closed the card window. Sent from
    the daily scheduler (first the morning after, then once more 3 days on)."""
    first = (lead.get("client_names") or "there").split("&")[0].strip().split()[0]
    date = lead.get("event_date_display") or ""
    pkg = lead.get("package_name") or ""
    what = (f"<b>{pkg}</b> for <b>{date}</b>" if pkg and date else
            f"<b>{date}</b>" if date else "your wedding date")
    if not second:
        lead_in = (f"<p>You were one step from reserving {what} \u2014 your details are "
                   f"in, and only the card window was left.</p>"
                   f"<p>Nothing was charged and nothing is held yet. Your date stays open "
                   f"to other couples until the agreement is signed.</p>")
        subject = f"Finish reserving {date}" if date else "Finish reserving your date"
    else:
        lead_in = (f"<p>Just checking in \u2014 {what} is still open on our calendar, "
                   f"but we can\u2019t hold it without a signed agreement.</p>"
                   f"<p>If plans changed, no problem at all. If you\u2019d still like the "
                   f"date, it takes about two minutes to finish.</p>")
        subject = f"Still want {date}?" if date else "Still want your date?"
        if code:   # JC-ATV-NUDGE-0928
            from datetime import datetime as _dt
            try:
                exp = _dt.fromisoformat(code["expires_at"]).strftime("%A, %B %d")
            except Exception:
                exp = "3 days"
            lead_in += (f"<p>To make it easy: code <b>{code['code']}</b> takes "
                        f"<b>${code['amount']}</b> off any collection if you finish before "
                        f"<b>{exp}</b>. It is already applied on the link below.</p>")
            subject = (f"${code['amount']} off {date} — this week only" if date
                       else f"${code['amount']} off your date — this week only")
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ATAVIA WEDDINGS</h1>
      <p>Hi {first},</p>
      {lead_in}
      <p style="text-align:center;margin:26px 0">
        <a href="{resume_url}" style="background:#B0713F;color:#FAF7F2;padding:14px 30px;
        text-decoration:none;letter-spacing:2px;font-family:Arial,sans-serif;
        font-size:13px">FINISH MY BOOKING</a></p>
      <p>Questions about the card step, the retainer, or anything else? Just reply \u2014
      a real person reads every message.</p>
      <p style="color:#B0713F">\u2014 The Atavia Weddings Team</p>
    </div>"""
    return _send(api_key, lead["email"], subject, html)


def balance_receipt(api_key, booking, amount):
    """Receipt for the scheduled balance charge.

    welcome_email promises this charge on a named date, so it must not land on
    the couple's statement with no word from us.
    """
    first = booking["client_names"].split("&")[0].strip().split()[0]
    card = (f"your {booking.get('card_brand','card')} "
            f"••••{booking['card_last4']}"
            if booking.get("card_last4") else "the card on file")
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ATAVIA WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>Your remaining balance of <b>${amount:,.2f}</b> has been charged to
      {card}, exactly as scheduled in your agreement. <b>Your package is now
      paid in full</b> — there is nothing further to do.</p>
      <table style="width:100%;border-collapse:collapse;margin:20px 0">
        <tr><td style="padding:3px 14px 3px 0;color:#6B6B6B;font-size:12px">Package</td>
            <td style="padding:3px 0;font-size:13px">{booking.get('package_name','')}</td></tr>
        <tr><td style="padding:3px 14px 3px 0;color:#6B6B6B;font-size:12px">Wedding date</td>
            <td style="padding:3px 0;font-size:13px">{booking.get('event_date','')}</td></tr>
        <tr><td style="padding:3px 14px 3px 0;color:#6B6B6B;font-size:12px">Amount charged</td>
            <td style="padding:3px 0;font-size:13px">${amount:,.2f}</td></tr>
        <tr><td style="padding:3px 14px 3px 0;color:#6B6B6B;font-size:12px">Booking</td>
            <td style="padding:3px 0;font-size:13px">{booking.get('booking_id','')}</td></tr>
      </table>
      <p>The charge appears on your statement as <b>Atavia Weddings</b>.
      Questions about it? Just reply — a real person reads every message.</p>
      <p style="color:#B0713F">— The Atavia Weddings Team<br>
      (336) 537-9590 · ataviaweddings.com</p>
    </div>"""
    return _send(api_key, booking["email"],
                 f"Payment received — {booking.get('event_date','')}", html)


def balance_heads_up(api_key, booking, amount, when="tomorrow morning"):
    """Sent by charge_balances the run before a card-on-file balance falls
    due. The welcome email named the date weeks ago; this is the reminder so
    the charge never surprises anyone, and it gives an expired card a day to
    be swapped before it declines."""
    first = booking["client_names"].split("&")[0].strip().split()[0]
    card = (f"your {booking.get('card_brand','card')} "
            f"\u2022\u2022\u2022\u2022{booking['card_last4']}"
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
                 f"\u2014 {booking.get('event_date','')}", html)


def balance_charge_failed(api_key, booking, amount, attempt, max_attempts,
                          pay_url=None):
    """The scheduled balance charge was declined.

    Without this the couple never finds out: only the studio is alerted, so an
    expired card is invisible to them until someone calls. Deliberately
    blame-free, and it makes no threat about their date — the coverage is not
    contingent on this, and implying otherwise would frighten people over what
    is usually an expired card.
    """
    first = booking["client_names"].split("&")[0].strip().split()[0]
    retrying = attempt < max_attempts
    if retrying:
        next_line = ("We'll try the same card again tomorrow morning — if it was "
                     "a temporary hold or a daily limit, it may simply go through.")
        action = ("<p>Nothing for you to do right now. If you know the card has "
                  "changed, reply and we'll send a secure link.</p>")
    else:
        next_line = ("We've tried a few times now, so we've stopped automatic "
                     "attempts — we'd rather sort this out with you directly.")
        action = (
            '<p style="text-align:center;margin:26px 0">'
            f'<a href="{pay_url}" style="background:#B0713F;color:#FAF7F2;'
            'padding:14px 30px;text-decoration:none;letter-spacing:2px;'
            'font-family:Arial,sans-serif;font-size:13px">'
            'PAY YOUR BALANCE</a></p>'
            if pay_url else
            "<p>Just reply to this email and we'll send a secure payment link "
            "or take it another way — whichever is easier.</p>")
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ATAVIA WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>A quick heads-up: we tried to charge the remaining balance of
      <b>${amount:,.2f}</b> for <b>{booking.get('event_date','')}</b> to the card
      on file, and it didn't go through. Usually it's something small — an expired
      card, a new number, or the bank querying an unfamiliar charge.</p>
      <p>{next_line}</p>
      {action}
      <p><b>Your date and your coverage are not affected</b> — this is only about
      the payment method. We just didn't want you to hear it from your bank
      first.</p>
      <p style="color:#B0713F">— The Atavia Weddings Team<br>
      (336) 537-9590 · ataviaweddings.com</p>
    </div>"""
    return _send(api_key, booking["email"],
                 f"We couldn't process your balance payment — "
                 f"{booking.get('event_date','')}", html)


def lazo_invite(api_key, booking):
    """JC-LZ-INVITE-0928: one-time recommendation of Lazo (free planning tool)
    to a booked couple, sent by charge_balances a few days after booking.
    Marketing, not transactional: unsubscribe link + List-Unsubscribe header
    and the postal address in the footer."""
    first = booking["client_names"].split("&")[0].strip().split()[0]
    link = "https://meetlazo.com/?utm_source=atavia&utm_medium=email&utm_campaign=couples-invite"
    unsub = "mailto:info@ataviaweddings.com?subject=unsubscribe"
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ATAVIA WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>A quick one from us, not about your photos or film.</p>
      <p>The tool we use with our couples to keep the wedding day organized &mdash; the
      timeline, the vendor list, who needs to be where and when &mdash; is called
      <b>Lazo</b>. It is free, and when your planner, your venue and we are all looking
      at the same plan, the day runs the way you pictured it.</p>
      <p style="text-align:center;margin:26px 0">
        <a href="{link}" style="background:#B0713F;color:#FAF7F2;padding:14px 30px;
        text-decoration:none;letter-spacing:2px;font-family:Arial,sans-serif;
        font-size:13px">TRY LAZO, IT&rsquo;S FREE</a></p>
      <p>If your planning is already sorted, ignore this with our blessing. Nothing about
      your booking changes either way.</p>
      <p style="color:#B0713F">&mdash; Lauren McKinnon<br>Atavia Weddings · (336) 537-9590 · ataviaweddings.com</p>
      <p style="font-size:11px;color:#8a8580;margin-top:30px">You are receiving this
      because you booked with Atavia Weddings. 1095 Sugarview Dr Ste 100, Sheridan, WY 82801.
      <a href="{unsub}" style="color:#8a8580">Unsubscribe</a> from notes like this one.</p>
    </div>"""
    r = requests.post(API, json={
        "from": FROM, "to": [booking["email"]], "reply_to": "info@ataviaweddings.com",
        "subject": "The free planning tool we use with our couples",
        "html": html, "headers": {"List-Unsubscribe": f"<{unsub}>"},
    }, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
    r.raise_for_status()
    return r.json()

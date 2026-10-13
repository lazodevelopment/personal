"""Resend transactional email — Elizabeth Scott Weddings booking flow.
Build: JC-ES-EMAILS-0818-004 (v1 · 2026-08-18 · derived from Atavia)

Requires the elizabethscottweddings.com domain verified in Resend (same
Danbren Resend account as Atavia; verify domain status before first live
send).

Payment model reflected below: 50% retainer at signing, balance auto-charged
14 days before the Event. booking["retainer"] is the computed 50% figure set
by main.py — never a fixed amount.
"""

import requests

API = "https://api.resend.com/emails"
FROM = "Elizabeth Scott Weddings <hello@elizabethscottweddings.com>"
REPLY_TO = "hello@elizabethscottweddings.com"

# Editorial palette. ACCENT drives buttons/rules; override to match the site
# if a brand accent is ever formalized (keep in sync with the "accent" key
# in elizabethscott_packages.json used by the contract generator).
ACCENT = "#1F1F1F"
BTN_TEXT = "#FAF7F2"

_SIGNOFF = (f'<p style="color:{ACCENT}">— The Elizabeth Scott Weddings Team<br>'
            'hello@elizabethscottweddings.com · elizabethscottweddings.com</p>')


def _send(api_key, to, subject, html, reply_to=REPLY_TO):
    r = requests.post(API, json={
        "from": FROM, "to": [to] if isinstance(to, str) else to,
        "subject": subject, "html": html, "reply_to": reply_to,
    }, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
    r.raise_for_status()
    return r.json()


def _btn(href, label):
    return ('<p style="text-align:center;margin:26px 0">'
            f'<a href="{href}" style="background:{ACCENT};color:{BTN_TEXT};'
            'padding:14px 30px;text-decoration:none;letter-spacing:2px;'
            f'font-family:Arial,sans-serif;font-size:13px">{label}</a></p>')


def welcome_email(api_key, booking, q_link=None):
    # JC-ES-NEXT-1012: the confirmation carries the what-happens-next timeline
    first = booking["client_names"].split("&")[0].strip().split()[0]
    plan = booking["payment_option"]
    if plan == "standard":
        money_line = (
            f"Your remaining balance of <b>${booking['balance']:,}</b> will be "
            f"automatically charged to your card on file on "
            f"<b>{booking['balance_due_date']}</b> — fourteen days before your "
            f"wedding, exactly as outlined in your agreement. Nothing for you "
            f"to do."
        )
    else:
        money_line = ("Your collection is <b>paid in full</b> — nothing further "
                      "is due. Enjoy the planning!")
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ELIZABETH SCOTT WEDDINGS</h1>
      <p>Hi {first},</p>
      <p><b>Your date is officially reserved.</b> We're honored to be part of
      your day on <b>{booking['event_date']}</b>.</p>
      <p><b>What happens next.</b> We work in a few set milestones and we come
      to you at each one, so you never need to chase us.</p>
      <ol style="line-height:1.8;padding-left:20px">
        <li><b>Now.</b> {money_line}</li>
        <li><b>At your pace.</b> Your Wedding Day Questionnaire: venues, timeline,
        key people, must-have shots. About ten minutes, and you can reopen the
        same link to update it until two weeks before your date.</li>
        <li><b>Every six weeks.</b> A short note from the studio with one question
        that shapes how we film your day. Reply or ignore; both are fine.</li>
        <li><b>Ten days out.</b> Final details: we send back everything we have and
        ask you to confirm it in one reply.</li>
        <li><b>Your wedding day.</b> We arrive at the time set in your questionnaire
        and film the day as planned.</li>
        <li><b>After.</b> Your film, delivered as set out in your agreement.</li>
      </ol>
      <p><b>The one thing we need from you</b> is the questionnaire.</p>
      QBTN_PLACEHOLDER
      <p>Questions at any point: reply to this email. It reaches the studio
      directly and is answered by a person, usually the same day.</p>
      <p>Your signed agreement is attached to the signature confirmation you
      received separately. Keep it handy.</p>
      {_SIGNOFF}
    </div>"""
    qbtn = "" if not q_link else _btn(q_link, "COMPLETE YOUR QUESTIONNAIRE")
    html = html.replace("QBTN_PLACEHOLDER", qbtn)
    return _send(api_key, booking["email"],
                 "Your date is reserved! — Elizabeth Scott Weddings", html)


def notify_owner(api_key, owner_email, subject, lines):
    html = "<div style='font-family:monospace'>" + "<br>".join(lines) + "</div>"
    return _send(api_key, owner_email, subject, html)


def gratuity_receipt(api_key, booking, amount):
    first = booking["client_names"].split("&")[0].strip().split()[0]
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ELIZABETH SCOTT WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>Thank you so much for your generosity. Your gratuity of
      <b>${amount:,.2f}</b> has been received and 100% of it goes directly to
      the team who served your event.</p>
      <p>It means the world to them — truly.</p>
      {_SIGNOFF}
    </div>"""
    return _send(api_key, booking["email"],
                 "Thank you for your gratuity — Elizabeth Scott Weddings", html)


def gratuity_invite(api_key, booking, link):
    first = booking["client_names"].split("&")[0].strip().split()[0]
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ELIZABETH SCOTT WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>Congratulations again — we hope your wedding day was everything you imagined.
      It was an honor to capture it.</p>
      <p>One small note: our team members don't accept cash tips at events. If the people
      who served your day made it special and you'd like to recognize them,
      you can do so here — <b>100% goes directly to your event team</b>:</p>
      {_btn(link, "THANK THE TEAM")}
      <p>Entirely optional, always appreciated, never expected. Your gallery and films
      are on their way per your agreement — we'll be in touch.</p>
      {_SIGNOFF}
    </div>"""
    return _send(api_key, booking["email"],
                 f"Thank you, {first} — from all of us at Elizabeth Scott", html)


def questionnaire_reminder(api_key, booking, link, days_left):
    first = booking["client_names"].split("&")[0].strip().split()[0]
    urgency = ("is coming up fast" if days_left <= 15 else "is approaching")
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ELIZABETH SCOTT WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>Your wedding on <b>{booking['event_date']}</b> {urgency} — and we still
      need your Wedding Day Questionnaire so we can plan your coverage down to
      the minute. It takes about ten minutes:</p>
      {_btn(link, "COMPLETE YOUR QUESTIONNAIRE")}
      <p>Per your agreement, we need your day-of details at least fourteen (14)
      days before your wedding. Questions? Just reply to this email.</p>
      {_SIGNOFF}
    </div>"""
    return _send(api_key, booking["email"],
                 f"Your questionnaire — {booking['event_date']}", html)


def questionnaire_summary(api_key, owner_email, booking, answers, sections):
    rows = ""
    for sec_title, fields in sections:
        rows += (f'<tr><td colspan="2" style="padding:14px 0 4px;color:{ACCENT};'
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
    retainer = booking.get("retainer") or 0
    ret_txt = (f"${retainer:,} retainer (50% of your total)"
               if retainer else "50% retainer")
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ELIZABETH SCOTT WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>Your service agreement for <b>{booking['event_date']}</b> is signed-ready
      and waiting — but your date isn't reserved until it's signed and the
      {ret_txt} is paid. Dates are first-come, first-served, and popular
      {booking.get('event_date','').split(',')[0]} dates go quickly.</p>
      {_btn(signing_url, "REVIEW &amp; SIGN")}
      <p>Changed your mind or have questions first? Just reply — a real person reads
      every message.</p>
      {_SIGNOFF}
    </div>"""
    return _send(api_key, booking["email"],
                 f"Your date isn't reserved yet — {booking['event_date']}", html)


def payment_nudge(api_key, booking, pay_url=None):
    first = booking["client_names"].split("&")[0].strip().split()[0]
    amount = booking.get("invoice_amount") or booking.get("retainer") or 0
    amt_txt = f"<b>${amount:,} retainer</b>" if amount else "<b>retainer</b>"
    if pay_url:
        link_para = (f'<p><a href="{pay_url}" style="color:#1F1F1F"><b>Pay the '
                     f'retainer securely here</b></a> (the charge appears as '
                     f'<b>Elizabeth Scott Wed</b> on your statement).</p>')
    else:
        link_para = ('<p>Your secure payment link is in the email from our payment '
                     'processor (the charge appears as <b>Elizabeth Scott Wed</b>). '
                     "Can't find it? Check spam, or reply here.</p>")
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ELIZABETH SCOTT WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>You're one step from officially locking in <b>{booking['event_date']}</b> —
      your agreement is signed, and only the {amt_txt} remains.
      Until it's paid, your date stays open to other couples.</p>
      {link_para}
      <p>Any trouble with the payment link, reply here and we'll sort it personally.</p>
      {_SIGNOFF}
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
        if code:   # JC-ESW-NUDGE-0928
            from datetime import datetime as _dt
            try:
                exp = _dt.fromisoformat(code["expires_at"]).strftime("%A, %B %d")
            except Exception:
                exp = "3 days"
            lead_in += (f"<p>To make it easy: inquiry code <b>{code['code']}</b> takes "
                        f"<b>${code['amount']}</b> off any collection if you finish before "
                        f"<b>{exp}</b>. It is already applied on the link below.</p>")
            subject = (f"${code['amount']} off {date} \u2014 this week only" if date
                       else f"${code['amount']} off your date \u2014 this week only")
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ELIZABETH SCOTT WEDDINGS</h1>
      <p>Hi {first},</p>
      {lead_in}
      <p style="text-align:center;margin:26px 0">
        <a href="{resume_url}" style="background:#1F1F1F;color:#FAF7F2;padding:14px 30px;
        text-decoration:none;letter-spacing:2px;font-family:Arial,sans-serif;
        font-size:13px">FINISH MY BOOKING</a></p>
      <p>Questions about the card step, the retainer, or anything else? Just reply \u2014
      a real person reads every message.</p>
      {_SIGNOFF}
    </div>"""
    return _send(api_key, lead["email"], subject, html)


def lazo_invite(api_key, booking):
    """JC-LZ-INVITE-0928: one-time recommendation of Lazo (free planning tool)
    to a booked couple, sent by charge_balances a few days after booking.
    Marketing, not transactional: unsubscribe link + List-Unsubscribe header
    and the postal address in the footer."""
    first = booking["client_names"].split("&")[0].strip().split()[0]
    link = "https://meetlazo.com/?utm_source=elizabethscott&utm_medium=email&utm_campaign=couples-invite"
    unsub = "mailto:hello@elizabethscottweddings.com?subject=unsubscribe"
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ELIZABETH SCOTT WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>A quick one from us, not about your photos or film.</p>
      <p>The tool we use with our couples to keep the wedding day organized &mdash; the
      timeline, the vendor list, who needs to be where and when &mdash; is called
      <b>Lazo</b>. It is free, and when your planner, your venue and we are all looking
      at the same plan, the day runs the way you pictured it.</p>
      <p style="text-align:center;margin:26px 0">
        <a href="{link}" style="background:#B08D57;color:#FAF7F2;padding:14px 30px;
        text-decoration:none;letter-spacing:2px;font-family:Arial,sans-serif;
        font-size:13px">TRY LAZO, IT&rsquo;S FREE</a></p>
      <p>If your planning is already sorted, ignore this with our blessing. Nothing about
      your booking changes either way.</p>
      <p style="color:#B08D57">&mdash; Elizabeth Scott Weddings<br>hello@elizabethscottweddings.com · elizabethscottweddings.com</p>
      <p style="font-size:11px;color:#8a8580;margin-top:30px">You are receiving this
      because you booked with Elizabeth Scott Weddings. 1095 Sugarview Dr Ste 100, Sheridan, WY 82801.
      <a href="{unsub}" style="color:#8a8580">Unsubscribe</a> from notes like this one.</p>
    </div>"""
    r = requests.post(API, json={
        "from": FROM, "to": [booking["email"]], "reply_to": "hello@elizabethscottweddings.com",
        "subject": "The free planning tool we use with our couples",
        "html": html, "headers": {"List-Unsubscribe": f"<{unsub}>"},
    }, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
    r.raise_for_status()
    return r.json()


def balance_link(api_key, booking, amount, pay_url):
    """Balance due, no card on file, processor does not email its own link
    (Whop). Zoho bookings never use this: Zoho sends the link itself."""
    first = booking["client_names"].split("&")[0].strip().split()[0]
    html = f"""
    <div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">
      <h1 style="font-weight:normal;letter-spacing:2px">ELIZABETH SCOTT WEDDINGS</h1>
      <p>Hi {first},</p>
      <p>Your remaining balance of <b>${amount:,}</b> for <b>{booking['event_date']}</b>
      is now due. We don't have a card on file for you, so here is a secure link:</p>
      <p><a href="{pay_url}" style="color:#1F3A5F"><b>Pay your balance securely here</b></a>
      (the charge appears as <b>Elizabeth Scott Wed</b>).</p>
      <p>Any trouble with the link, reply here and we'll sort it personally.</p>
      <p>— The Elizabeth Scott Weddings Team</p>
    </div>"""
    return _send(api_key, booking["email"],
                 f"Your balance for {booking['event_date']} is due", html)


# ============================================================ milestones ==
# JC-ES-ENGAGE-1012: the studio's planning rhythm between signing and the
# wedding. Written for ES's editorial voice (not the Atavia timeline emails):
#   planning_roadmap  3 days after signing   - the five milestones, in order
#   studio_note       every 6 weeks          - one question for the couple, while > 45 days out
#   final_details     10 days before         - confirm the day, reply required
# Driven by _send_milestones in main.py.

_ES_WRAP = ('<div style="font-family:Georgia,serif;color:#2B2B2B;max-width:560px;margin:0 auto">'
            '<h1 style="font-weight:normal;letter-spacing:2px">ELIZABETH SCOTT WEDDINGS</h1>'
            '{body}' + _SIGNOFF + '</div>')


def _es_first(booking):
    return booking["client_names"].split("&")[0].strip().split()[0]


def planning_roadmap(api_key, booking, q_link=None):
    first = _es_first(booking)
    plan = booking.get("payment_option")
    money = ("Your collection is paid in full. There is nothing further to pay."
             if plan != "standard" else
             f"Your balance is scheduled for <b>{booking.get('balance_due_date','')}</b>, fourteen days "
             "before the wedding, to the card you reserved with, exactly as your agreement sets out.")
    body = f"""
      <p>Hi {first},</p>
      <p>Your agreement is signed and <b>{booking.get('event_date','')}</b> is yours. From here we
      work in five milestones, and we will come to you at each one. You never need to chase us.</p>
      <ol style="line-height:1.8;padding-left:20px">
        <li><b>Now.</b> {money}</li>
        <li><b>At your pace.</b> Your Wedding Day Questionnaire: venues, timeline, the people who
        matter. Ten minutes, editable until two weeks out.</li>
        <li><b>Every six weeks.</b> A short note from the studio with one question that shapes how we
        film your day. Reply or ignore; both are fine.</li>
        <li><b>Ten days out.</b> Final details: we send back everything we have and ask you to confirm
        it in one reply.</li>
        <li><b>After.</b> Your film, delivered as set out in your agreement, with a note from the
        editor on what we loved.</li>
      </ol>
      {_btn(q_link, "BEGIN YOUR QUESTIONNAIRE") if q_link else ""}
      <p>Questions at any point: reply to this email. It reaches the studio directly and is answered
      by a person, usually the same day.</p>"""
    return _send(api_key, booking["email"],
                 f"Your planning roadmap — {booking.get('event_date','')}", _ES_WRAP.format(body=body))


_STUDIO_QUESTIONS = [
    ("Who is the one person you most want to see react when you walk in?",
     "Tell us who, and we will have a camera on them."),
    ("Are you writing your own vows, or reading letters to each other beforehand?",
     "Either way, we record the audio separately so every word survives."),
    ("Is there a song, a place, or an object that will mean something only to the two of you?",
     "These are the details that make a film yours and not a template."),
    ("Would you rather we are invisible, or part of the room?",
     "Some couples want us never noticed; others like a little direction. Both are good answers."),
    ("What is the one moment you are nervous about?",
     "Often it is the one we can make easiest, if we know in advance."),
]


def studio_note(api_key, booking, q_link, n, days_to_event, q_done):
    first = _es_first(booking)
    q, why = _STUDIO_QUESTIONS[n % len(_STUDIO_QUESTIONS)]
    weeks = max(1, round(days_to_event / 7))
    qline = ("" if q_done else
             f'<p style="font-size:13px;color:#6B6B6B">Your questionnaire is still open: '
             f'<a href="{q_link}" style="color:{ACCENT}">complete it when you have ten minutes</a>.</p>')
    body = f"""
      <p>Hi {first},</p>
      <p>A note from the studio, {weeks} weeks out from {booking.get('event_date','')}.
      Everything is on track and nothing is required of you.</p>
      <p style="font-size:18px;line-height:1.5;margin:22px 0 6px"><i>{q}</i></p>
      <p>{why} Reply with a line or two if you like.</p>
      {qline}
      <p>And if anything has changed since we last spoke, that is the other reason to reply.</p>"""
    return _send(api_key, booking["email"],
                 f"A note from the studio — {booking.get('event_date','')}", _ES_WRAP.format(body=body))


def final_details(api_key, booking, q_link, q_done):
    first = _es_first(booking)
    rows = ""
    for label, key in (("Ceremony", "ceremony_venue"), ("Reception", "reception_venue"),
                       ("Coverage begins", "start_time"), ("Coverage ends", "end_time"),
                       ("Collection", "package_name")):
        v = booking.get(key)
        if v:
            rows += (f'<tr><td style="padding:4px 14px 4px 0;color:#6B6B6B;font-size:12px">{label}</td>'
                     f'<td style="padding:4px 0;font-size:13px">{v}</td></tr>')
    table = f'<table style="width:100%;border-collapse:collapse;margin:16px 0">{rows}</table>' if rows else ""
    missing = ("" if q_done else
               f'<p><b>We do not yet have your questionnaire.</b> Please <a href="{q_link}" '
               f'style="color:{ACCENT}">complete it now</a>, or simply reply with your timeline and '
               'the names that matter, and we will build the plan from that.</p>')
    body = f"""
      <p>Hi {first},</p>
      <p>Ten days out. This is everything we are working from for <b>{booking.get('event_date','')}</b>:</p>
      {table}
      {missing}
      <p><b>Please reply to this email with one word, "confirmed", or with any corrections.</b>
      We lock the plan and assign the crew on your reply.</p>
      <p>Thank you for trusting us with this.</p>"""
    return _send(api_key, booking["email"],
                 f"Final details, please confirm — {booking.get('event_date','')}", _ES_WRAP.format(body=body))

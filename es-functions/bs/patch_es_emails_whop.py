"""Add emails.balance_link() to the Elizabeth Scott lib/emails.py (Cloud Shell only copy).

Run from ~/es-deploy/functions:  python3 patch_es_emails_whop.py
Idempotent: does nothing if balance_link already exists.
Whop never emails its hosted links the way Zoho does, so when a Whop booking
has no card on file at balance time, the balance scheduler sends this.
"""
import io, os, sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib", "emails.py")
src = io.open(P, encoding="utf-8").read()
if "def balance_link(" in src:
    print("balance_link already present; nothing to do")
    sys.exit(0)

anchor = "def balance_heads_up("
if anchor not in src:
    # ES may lack the heads-up email; append at the end instead
    anchor = None

NEW = '''def balance_link(api_key, booking, amount, pay_url):
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


'''
if anchor:
    src = src.replace(anchor, NEW + anchor, 1)
else:
    src = src.rstrip("\n") + "\n\n\n" + NEW.rstrip("\n") + "\n"
io.open(P, "w", encoding="utf-8", newline="\n").write(src)
print("balance_link added to", P)

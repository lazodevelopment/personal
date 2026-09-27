import os, datetime, html
E = html.escape
SITE = "https://leasereputation.com"
APP = "https://app.leasereputation.com"
TODAY = datetime.date.today().isoformat()

CSS = """
:root{--indigo:#4C4FE6;--indigo-bright:#6E72F0;--deep:#1E1A5C;--ink:#15102E;--ink-deep:#0E0A20;
--lilac:#C4B5FD;--gold:#FFC83D;--mint:#3DDC97;--warn:#FF8B8B;--text:#EFEDFB;
--text-dim:rgba(233,231,251,.64);--text-faint:rgba(233,231,251,.42);
--border:rgba(255,255,255,.10);--glass:rgba(255,255,255,.04);--glass-2:rgba(255,255,255,.06);
--pad:24px;--maxw:780px}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:'Plus Jakarta Sans',system-ui,sans-serif;background:var(--ink-deep);color:var(--text);line-height:1.7;-webkit-font-smoothing:antialiased;overflow-x:hidden}
img,svg{display:block;max-width:100%}
a{color:var(--lilac)}
header#hdr{position:sticky;top:0;z-index:50;background:rgba(14,10,32,.82);backdrop-filter:blur(14px);border-bottom:1px solid var(--border)}
.hnav{max-width:1080px;margin:0 auto;padding:0 var(--pad);display:flex;align-items:center;justify-content:space-between;gap:18px;height:74px}
.logo{display:inline-flex;align-items:center;gap:11px;flex:none;text-decoration:none}
.logo svg{width:38px;height:38px;border-radius:11px;box-shadow:0 6px 16px rgba(0,0,0,.35)}
.logo .wm{font-size:1.3rem;letter-spacing:-.02em;line-height:1;white-space:nowrap}
.logo .wm .l{font-weight:500;color:rgba(255,255,255,.6)}
.logo .wm .r{font-weight:800;color:#fff}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;font-family:inherit;font-weight:700;font-size:.95rem;padding:12px 24px;border-radius:100px;border:0;cursor:pointer;white-space:nowrap;background:var(--indigo);color:#fff;text-decoration:none;box-shadow:0 8px 24px rgba(76,79,230,.35);transition:transform .15s,box-shadow .15s,background .15s}
.btn:hover{transform:translateY(-2px);box-shadow:0 14px 34px rgba(76,79,230,.5);background:var(--indigo-bright)}
.btn-ghost{background:transparent;color:var(--text);border:1px solid var(--border);box-shadow:none}
.btn-ghost:hover{background:var(--glass-2);border-color:var(--lilac);box-shadow:none;transform:translateY(-2px)}
.wrap{max-width:var(--maxw);margin:0 auto;padding:34px var(--pad) 60px;width:100%}
.crumb{font-size:.8rem;color:var(--text-faint);margin-bottom:22px}
.crumb a{color:var(--text-faint);text-decoration:none}
.crumb a:hover{color:var(--lilac)}
h1{font-size:clamp(1.9rem,5vw,2.7rem);line-height:1.15;font-weight:800;letter-spacing:-.02em;margin-bottom:14px}
h1 .accent{color:var(--lilac)}
.lede{color:var(--text-dim);font-size:1.08rem;margin-bottom:8px}
.meta{font-size:.8rem;color:var(--text-faint);margin-bottom:34px}
article h2{font-size:1.35rem;font-weight:800;margin:38px 0 12px;letter-spacing:-.01em;color:var(--text)}
article p{color:var(--text-dim);margin-bottom:16px}
article strong{color:var(--text)}
article a{color:var(--lilac)}
article ul,article ol{color:var(--text-dim);margin:0 0 16px 22px}
article li{margin-bottom:8px}
article li strong{color:var(--text)}
.callout{border:1px solid var(--border);background:var(--glass);border-radius:14px;padding:18px 20px;margin:22px 0}
.callout.mint{border-color:rgba(61,220,151,.35)}
.callout.gold{border-color:rgba(255,200,61,.35)}
.callout p{margin:0;color:var(--text-dim)}
.cta-band{border:1px solid var(--border);background:linear-gradient(135deg,rgba(76,79,230,.16),var(--glass));border-radius:18px;padding:26px;margin:44px 0 26px;text-align:center}
.cta-band h3{font-size:1.25rem;font-weight:800;margin-bottom:8px}
.cta-band p{color:var(--text-dim);margin-bottom:16px;font-size:.95rem}
.morehead{font-size:.9rem;font-weight:800;color:var(--text)}
.morelinks{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}
.morelinks a{border:1px solid var(--border);background:var(--glass);border-radius:999px;padding:8px 16px;font-size:.85rem;color:var(--text-dim);text-decoration:none;transition:color .15s,border-color .15s}
.morelinks a:hover{color:var(--text);border-color:var(--lilac)}
.gcard{display:block;border:1px solid var(--border);background:var(--glass);border-radius:16px;padding:20px 22px;margin-bottom:14px;text-decoration:none;transition:border-color .15s,transform .15s}
.gcard h2{margin:0 0 6px;font-size:1.15rem;color:var(--text);font-weight:800}
.gcard p{margin:0;font-size:.92rem;color:var(--text-faint)}
.gcard:hover{border-color:var(--lilac);transform:translateY(-2px)}
footer{border-top:1px solid var(--border);padding:26px var(--pad);text-align:center;font-size:.8rem;color:var(--text-faint)}
footer a{color:var(--text-faint)}
@media(max-width:560px){.hnav{height:64px}.logo .wm{font-size:1.1rem}.btn{padding:10px 18px;font-size:.88rem}}
"""

ICON = """<svg viewBox="0 0 512 512" aria-hidden="true"><defs><linearGradient id="lg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1E1A5C"/><stop offset="1" stop-color="#4C4FE6"/></linearGradient></defs><rect width="512" height="512" rx="115" fill="url(#lg)"/><path d="M172 126 L340 126 Q362 126 362 148 L362 268 C362 330 300 372 256 388 C212 372 150 330 150 268 L150 148 Q150 126 172 126 Z" fill="#fff"/><path d="M210 240 L242 272 L304 206" fill="none" stroke="#4C4FE6" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

FAVICON = """<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cpath d='M16 2l11 5v8c0 7.5-4.7 12.7-11 15C9.7 27.7 5 22.5 5 15V7l11-5z' fill='%234F46E5'/%3E%3Cpath d='M11 16.5l3.5 3.5 6.5-7' stroke='%2334D399' stroke-width='2.6' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E" />"""

def page(title, desc, canon, body, schema=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}" />
<link rel="canonical" href="{canon}" />
{FAVICON}
<meta property="og:title" content="{E(title)}" />
<meta property="og:description" content="{E(desc)}" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
<style>{CSS}</style>
{schema}
</head>
<body>
<header id="hdr">
  <div class="hnav">
    <a class="logo" href="{SITE}/" aria-label="LeaseReputation home">
      {ICON}
      <span class="wm"><span class="l">lease</span><span class="r">reputation</span></span>
    </a>
    <a class="btn" href="{APP}">Open the app</a>
  </div>
</header>
{body}
<footer>© 2026 LeaseReputation · Danbren Media LLC · <a href="{SITE}/community/">Browse communities</a> · <a href="{SITE}/guides/">Renter guides</a></footer>
</body>
</html>"""

def article_page(a, others):
    canon = f"{SITE}/guides/{a['slug']}.html"
    schema = f"""<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article","headline":"{E(a['title'])}","description":"{E(a['desc'])}","datePublished":"{TODAY}","dateModified":"{TODAY}","author":{{"@type":"Organization","name":"LeaseReputation"}},"publisher":{{"@type":"Organization","name":"LeaseReputation","url":"{SITE}"}},"mainEntityOfPage":"{canon}"}}</script>"""
    more = "".join(f'<a href="{SITE}/guides/{o["slug"]}.html">{E(o["short"])}</a>' for o in others)
    body = f"""<div class="wrap">
<div class="crumb"><a href="{SITE}/">Home</a> / <a href="{SITE}/guides/">Renter guides</a> / {E(a['short'])}</div>
<h1>{a['h1']}</h1>
<p class="lede">{E(a['lede'])}</p>
<p class="meta">By the LeaseReputation team · Updated {TODAY}</p>
<article>
{a['body']}
</article>
<div class="cta-band">
  <h3>Know before you lease.</h3>
  <p>Verified apartment reviews from residents who actually lived there — scores that can't be bought, boosted, or buried.</p>
  <a class="btn" href="{SITE}/community/">Find your community</a>
</div>
<div class="morehead">More renter guides</div>
<div class="morelinks">{more}</div>
</div>"""
    return page(f"{a['title']} | LeaseReputation", a['desc'], canon, body, schema)

# ════════════════ THE SIX ARTICLES ════════════════
ARTICLES = [
{
"slug":"how-to-get-your-security-deposit-back",
"short":"Get your deposit back",
"title":"How to Get Your Full Security Deposit Back",
"h1":"How to get your <span class=\"accent\">full deposit</span> back.",
"lede":"Deposit deductions are where good tenancies go to die. Most of them are preventable — if you start on move-in day, not move-out day.",
"desc":"A practical, step-by-step guide to getting your full apartment security deposit back: move-in documentation, normal wear and tear, the walkthrough, and what to do if they keep it anyway.",
"body":"""
<h2>The game is won on move-in day</h2>
<p>Deposit disputes come down to one question: <strong>was the damage there before you moved in?</strong> If you can't prove it was, the property's version wins by default. So before a single box crosses the threshold:</p>
<ul>
<li><strong>Photograph everything.</strong> Every wall, every corner of carpet, inside the oven, under the sinks, every blind and screen. Wide shots for context, close-ups for existing damage. Video works too — narrate the date as you walk.</li>
<li><strong>Fill out the move-in condition report completely.</strong> If the property gives you a checklist, treat it like a legal document — because it is. "Everything fine" is what they hope you write. Write the truth: the scuff behind the door, the chipped tile, the stain the size of a coffee mug.</li>
<li><strong>Send it in writing.</strong> Email the completed report and a link to your photos to the leasing office so there's a timestamp neither side can dispute.</li>
</ul>
<h2>Know what they're allowed to charge you for</h2>
<p>Landlords can deduct for <strong>damage</strong>, not for <strong>normal wear and tear</strong> — and the difference is defined by law in most states, not by the property's mood. Faded paint, minor scuffs, worn carpet in walkways, small nail holes from hanging pictures: that's wear, and in most states it can't come out of your deposit. Broken doors, pet stains, holes in drywall, burns: that's damage.</p>
<div class="callout gold"><p><strong>Watch for "cleaning fee" games.</strong> Some properties deduct a flat cleaning fee from everyone regardless of condition. In many states that's only enforceable if it's explicitly in your lease — and sometimes not even then. Read the deposit section of your lease before you sign, not after you move out.</p></div>
<h2>Move-out: run the same play in reverse</h2>
<ul>
<li><strong>Clean like it matters, because it does.</strong> Ovens, baseboards, inside the fridge. Cleaning charges are the most common deduction and the easiest to prevent.</li>
<li><strong>Patch small nail holes</strong> with spackle — five dollars of supplies against a "wall repair" line item.</li>
<li><strong>Photograph everything again</strong>, same coverage as move-in. Same-day timestamps.</li>
<li><strong>Request a walkthrough with staff</strong> and get any "looks good" in writing. Several states give you the legal right to a pre-move-out inspection — use it.</li>
<li><strong>Give your forwarding address in writing.</strong> In most states the deadline clock for returning your deposit doesn't start until they have it.</li>
</ul>
<h2>If they keep it anyway</h2>
<p>Every state sets a deadline (commonly 14–30 days) for the landlord to return your deposit or send an <strong>itemized list of deductions</strong>. Miss the deadline or skip the itemization, and in many states they forfeit the right to keep anything — some states award you two or three times the deposit as a penalty.</p>
<ol>
<li><strong>Send a demand letter.</strong> Certified mail. State the amount, cite your state's deposit statute, attach your move-in and move-out photos, give them 10 days.</li>
<li><strong>Small claims court is built for exactly this.</strong> Filing costs $30–75, you don't need a lawyer, and a tenant with dated photos and a paper trail wins far more often than not.</li>
<li><strong>Tell the next renter.</strong> A property that plays deposit games with you is playing them with everyone. A verified review — with your deposit outcome on the record — is how the pattern becomes visible.</li>
</ol>
"""},
{
"slug":"questions-to-ask-on-an-apartment-tour",
"short":"Apartment tour questions",
"title":"15 Questions to Ask on an Apartment Tour (That Leasing Agents Hope You Won't)",
"h1":"15 tour questions <span class=\"accent\">leasing agents hope you skip.</span>",
"lede":"The tour is a sales presentation. These questions turn it back into an inspection.",
"desc":"The 15 apartment tour questions that actually reveal what living somewhere is like — maintenance speed, real monthly costs, noise, turnover, and the answers that should worry you.",
"body":"""
<h2>Money — the real number, not the advertised one</h2>
<ol>
<li><strong>"What does the total move-in cost come to, all-in?"</strong> Application fee, admin fee, deposit, first month, pet deposit — get the single number in writing. Admin fees alone routinely add $150–500 and appear after you're emotionally committed.</li>
<li><strong>"What's the monthly total with every mandatory fee?"</strong> Valet trash, package lockers, "amenity fees," mandatory internet packages. A $1,500 apartment is often a $1,680 apartment.</li>
<li><strong>"How much did rent increase at renewal for current residents this year?"</strong> The move-in special is bait; the renewal increase is the business model. If they won't say, that's your answer.</li>
<li><strong>"Is the deposit refundable, and what were the top three deductions last year?"</strong> A confident property answers this easily.</li>
</ol>
<h2>Maintenance — the thing that actually determines your happiness</h2>
<ol start="5">
<li><strong>"What's the average time to close a non-emergency maintenance request?"</strong> The single most predictive question on this list. "We're usually pretty quick" is not a number.</li>
<li><strong>"Is maintenance in-house or contracted?"</strong> In-house teams turn requests around in days; some contracted setups take weeks.</li>
<li><strong>"What's the after-hours emergency process?"</strong> Ask who actually answers at 11pm on a Saturday when the water heater fails.</li>
</ol>
<h2>The building's honest condition</h2>
<ol start="8">
<li><strong>"Can I see the actual unit I'd rent — not the model?"</strong> Model units are staged theater. If your unit "isn't ready to show," ask why.</li>
<li><strong>"How old are the HVAC, water heater, and appliances in my unit?"</strong> A 15-year-old AC in Phoenix is a summer of emergency requests waiting to happen.</li>
<li><strong>"Any planned construction, renovation, or ownership changes?"</strong> New ownership almost always means new fees and new rules mid-lease.</li>
</ol>
<h2>The neighbors and the noise</h2>
<ol start="11">
<li><strong>"What's the resident turnover rate?"</strong> High turnover is the building telling you something its marketing won't.</li>
<li><strong>"Can I come back at 9pm?"</strong> A property that says no to an evening walk-by has a reason. Parking lots, hallway noise, and the pool crowd all tell the truth after dark.</li>
<li><strong>"What's the wall construction between units?"</strong> Concrete between floors is a different life than wood-frame. Ask; agents know.</li>
</ol>
<h2>The exit</h2>
<ol start="14">
<li><strong>"What exactly does breaking the lease cost?"</strong> Life happens — jobs move, relationships change. Know the number before you need it.</li>
<li><strong>"What are the renewal terms and notice requirements?"</strong> Some leases quietly auto-renew or require 60–90 days' notice; missing the window costs a month's rent.</li>
</ol>
<div class="callout mint"><p><strong>Then check their answers.</strong> Every one of these questions has already been answered — by people who lived there. Verified resident reviews are the tour's fact-checker.</p></div>
"""},
{
"slug":"apartment-lease-red-flags",
"short":"Lease red flags",
"title":"9 Apartment Lease Red Flags to Catch Before You Sign",
"h1":"9 lease clauses that should <span class=\"accent\">stop your pen.</span>",
"lede":"Nobody reads the lease — which is exactly what the worst clauses count on. These nine are worth the twenty minutes.",
"desc":"The nine apartment lease red flags to find before signing: fee stacking, mandatory arbitration, automatic renewals, entry rights, and the clauses that cost renters the most.",
"body":"""
<h2>1. Fee stacking buried past page one</h2>
<p>The rent on the listing and the monthly total in the lease are often different documents' worth apart. Scan for: <strong>valet trash, amenity fees, package fees, pest control fees, mandatory insurance programs, "utility administration" fees.</strong> Add every recurring line to get your real rent — then judge the value.</p>
<h2>2. Automatic renewal with a long notice window</h2>
<p>Some leases quietly convert to another full term unless you give notice 60–90 days out. Miss the window and you owe another year — or a steep month-to-month premium. Calendar the notice date the day you sign.</p>
<h2>3. Vague "excessive cleaning" deposit language</h2>
<p>Deposit deduction clauses that don't define standards ("unit must be returned in satisfactory condition") are blank checks. Look for leases that reference <strong>normal wear and tear</strong> explicitly — and read our <a href="how-to-get-your-security-deposit-back.html">deposit guide</a> before move-in day either way.</p>
<h2>4. Unlimited entry rights</h2>
<p>Most states require notice (commonly 24–48 hours) before non-emergency entry. A lease claiming the right to enter "at any time for any purpose" is either unenforceable, a sign of how management operates, or both.</p>
<h2>5. The rent-increase-anytime clause</h2>
<p>Fixed-term leases should fix the rent. Month-to-month arrangements and some sneaky fixed leases allow mid-term increases with 30 days' notice. Know which document you're holding.</p>
<h2>6. Mandatory arbitration and class-action waivers</h2>
<p>Increasingly common: a clause waiving your right to sue or join class actions, routing everything to an arbitrator. Courts treat these differently by state; at minimum, know you're signing one — it changes your leverage in every future dispute.</p>
<h2>7. Repairs shifted onto you</h2>
<p>Clauses making the tenant responsible for appliance repair, drain clearing, or "first $100 of every request" convert maintenance from their obligation into your bill, one service call at a time.</p>
<h2>8. Early-termination terms that don't exist</h2>
<p>A lease that's silent on early termination doesn't mean freedom — it usually means you owe every remaining month. The best leases name a concrete buyout (commonly two months' rent). No clause at all is the red flag.</p>
<h2>9. The "as-is" unit acceptance</h2>
<p>Language stating you accept the unit "as-is, in good condition" — signed before you've spent a night there — undercuts every future claim about pre-existing problems. Pair your signature with a written condition report and dated photos, same day.</p>
<div class="callout gold"><p><strong>The meta-flag:</strong> how the office reacts to questions about the lease. A property that bristles at "what does this clause mean?" is showing you exactly how disputes will go later.</p></div>
"""},
{
"slug":"how-to-break-a-lease",
"short":"Breaking a lease",
"title":"How to Break an Apartment Lease (Without Destroying Your Finances)",
"h1":"Breaking a lease, <span class=\"accent\">the least-expensive way.</span>",
"lede":"Life doesn't schedule itself around lease terms. Here's the damage-minimization playbook, in order of preference.",
"desc":"How to break an apartment lease with minimal cost: legal exits, buyout clauses, lease transfers, negotiation scripts, and what actually happens to your credit.",
"body":"""
<h2>First: check for a free exit</h2>
<p>Several situations let you leave with little or no penalty, depending on state law:</p>
<ul>
<li><strong>Active-duty military orders</strong> — federal law (SCRA) guarantees this one nationwide.</li>
<li><strong>Uninhabitable conditions</strong> — no heat, no water, serious mold or pest issues that management won't fix after written notice. Document everything; this is "constructive eviction."</li>
<li><strong>Domestic violence situations</strong> — most states provide early-termination rights with documentation.</li>
<li><strong>Landlord violations</strong> — repeated illegal entry, harassment, failure to maintain. Paper trail required.</li>
</ul>
<h2>Second: read your lease for the buyout</h2>
<p>Many leases include an <strong>early-termination clause</strong>: typically 30–60 days' notice plus a fee of one to two months' rent. If yours has one, that's your ceiling — everything below is about doing better.</p>
<h2>Third: the transfer play</h2>
<p>If your market is hot, the cheapest exit is often replacing yourself:</p>
<ul>
<li><strong>Lease transfer / assignment</strong> — a new tenant takes over your lease entirely. Needs management approval, but they keep a paying unit with zero vacancy.</li>
<li><strong>Subletting</strong> — you remain on the hook but someone else pays. Check whether your lease allows it; many require written consent.</li>
</ul>
<h2>Fourth: negotiate — you have more leverage than you think</h2>
<p>In most states, landlords have a legal <strong>duty to mitigate</strong>: they must make reasonable efforts to re-rent your unit rather than letting it sit empty and billing you. In a market where units rent in two weeks, your realistic exposure is often far less than the remaining term. The script:</p>
<div class="callout"><p>"I need to end my lease on [date]. I'd like to make this easy: I'll keep the unit spotless for showings, I'm flexible on timing, and I can offer [one month's rent] as a termination fee. Given how quickly units here are renting, can we agree in writing that my liability ends when a new lease is signed or on [date], whichever comes first?"</p></div>
<h2>What it actually does to your credit</h2>
<p>Breaking a lease isn't itself on your credit report. What hurts is an <strong>unpaid balance sent to collections</strong>. Pay what you legitimately owe (or settle it in writing), get a zero-balance letter, and the episode ends with the lease. Walk away owing money, and it follows you to every future application.</p>
<div class="callout mint"><p><strong>Leaving because the property failed you?</strong> Your verified review — with the documentation you gathered — is how the next renter avoids your year. Former residents can review on LeaseReputation, deposit outcome and all.</p></div>
"""},
{
"slug":"first-apartment-checklist",
"short":"First apartment checklist",
"title":"The First Apartment Checklist: Everything Before, During, and After the Lease",
"h1":"The first-apartment <span class=\"accent\">checklist.</span>",
"lede":"Everything nobody tells you before your first lease — budgeting reality, application paperwork, move-in protection, and the first-week setup.",
"desc":"A complete first apartment checklist: what you can actually afford, application documents, move-in day documentation, utilities, and the mistakes first-time renters make.",
"body":"""
<h2>Before you tour: the honest budget</h2>
<ul>
<li><strong>The classic rule is rent ≤ 30% of gross income</strong> — and most properties enforce a version of it, requiring documented income of 2.5–3× rent to approve you.</li>
<li><strong>Budget the real monthly:</strong> rent + mandatory fees + utilities (ask the property for average bills — they know) + internet + renter's insurance ($10–25/mo) + parking.</li>
<li><strong>Budget the move-in wall:</strong> first month + deposit + application/admin fees + moving costs. It's commonly 2.5–3× a month's rent, due at once.</li>
</ul>
<h2>The application packet (have it ready before you tour)</h2>
<ul>
<li>Photo ID, recent pay stubs (or offer letter), bank statements, prior landlord reference if you have one</li>
<li><strong>No rental history?</strong> Expect to need a co-signer/guarantor (usually required to show 5–6× rent in income) or a larger deposit. Line yours up in advance — units don't wait.</li>
<li>Credit check happens on nearly every application; know your score going in.</li>
</ul>
<h2>Before you sign</h2>
<ul>
<li>Tour with our <a href="questions-to-ask-on-an-apartment-tour.html">15 questions</a> and check the lease against the <a href="apartment-lease-red-flags.html">nine red flags</a>.</li>
<li>Read verified resident reviews — the tour shows you the pool; residents tell you about the maintenance response time.</li>
<li>Get every promise in writing. "We'll replace that carpet before move-in" is worth nothing verbally.</li>
</ul>
<h2>Move-in day: one hour of documentation</h2>
<ul>
<li><strong>Photograph and video every room before furniture arrives</strong> — this hour is what gets your deposit back in a year (full playbook: <a href="how-to-get-your-security-deposit-back.html">the deposit guide</a>).</li>
<li>Complete the condition report in obsessive detail and email it in.</li>
<li>Test everything: every burner, faucet, outlet, lock, window, the AC and heat both. Submit maintenance requests for failures on day one, in writing.</li>
</ul>
<h2>The first week</h2>
<ul>
<li>Utilities in your name (electric/gas often required before keys), internet scheduled, renter's insurance active from day one — most leases require it, and it's the cheapest insurance you'll ever carry.</li>
<li>Change of address with USPS, driver's license update, find the water shutoff and breaker panel before you need them at midnight.</li>
<li>Meet the maintenance team. Being a known, polite human moves your requests up every queue in the building.</li>
</ul>
<div class="callout mint"><p><strong>Twelve months from now, you'll know things about this building nobody told you.</strong> That's exactly when your verified review matters — write the one you wish you'd been able to read.</p></div>
"""},
{
"slug":"how-to-spot-fake-apartment-reviews",
"short":"Spotting fake reviews",
"title":"How to Spot Fake Apartment Reviews (and Buried Real Ones)",
"h1":"How to spot <span class=\"accent\">fake apartment reviews</span> — and buried real ones.",
"lede":"Apartment review fraud runs in both directions: manufactured praise and vanished complaints. Here's how to read through both.",
"desc":"How to identify fake apartment reviews: the tells of manufactured 5-stars, how negative reviews get buried, what the FTC banned in 2024, and how to research a community properly.",
"body":"""
<h2>The economics make fraud inevitable</h2>
<p>A community's review score directly moves lease-up speed, which directly moves revenue. Where a number is worth that much, an industry grows around manipulating it: reputation-management firms, review-generation campaigns, takedown services. In 2024 the FTC formally banned buying fake reviews, suppressing honest ones, and review-gating (only inviting happy residents to post) — but a rule on paper doesn't un-bury a review. The manipulation just got quieter.</p>
<h2>The tells of a manufactured 5-star</h2>
<ul>
<li><strong>Clusters.</strong> Eight glowing reviews in the same two weeks — especially around lease-up season or right after a bad press cycle — is a campaign, not a coincidence.</li>
<li><strong>Marketing vocabulary.</strong> Real residents say "maintenance actually shows up." Campaigns say "luxurious resort-style amenities and a seamless leasing experience."</li>
<li><strong>Reviewer history.</strong> An account whose only review ever is this apartment community, posted the week it opened, is not your neighbor.</li>
<li><strong>Specificity asymmetry.</strong> Real praise names things: a staff member, an incident, a timeframe. Fake praise is adjectives all the way down.</li>
<li><strong>The staff-name pattern.</strong> A suspicious run of reviews all praising the same leasing agent by name often traces to an internal contest — reviews solicited by staff, for staff.</li>
</ul>
<h2>How real reviews disappear</h2>
<ul>
<li><strong>Platform disputes.</strong> On most sites, a business can flag reviews as "fake" or "policy-violating" — and an angry-but-honest review reads exactly like a fake one to an overworked moderator.</li>
<li><strong>Review gating.</strong> Resident portals that ask "How was your experience?" and only route the happy answers to public review sites. Banned in 2024; still everywhere.</li>
<li><strong>Settle-and-delete.</strong> "We'll refund your deposit if you take the review down." The review economy's quietest transaction.</li>
</ul>
<h2>Reading any review site defensively</h2>
<ul>
<li><strong>Read the 2- and 3-stars first.</strong> Fraud concentrates at 1 and 5; the middle is where the honest texture lives.</li>
<li><strong>Sort by recent.</strong> Management companies change; a 4.5 built in 2021 says nothing about the team running the building today.</li>
<li><strong>Look for patterns, not incidents.</strong> One angry deposit story is a data point. Five deposit stories across two years is the business model.</li>
<li><strong>Check whether the platform sells services to the properties it rates.</strong> If the review site's revenue comes from the buildings being reviewed, you know whose interests win the close calls.</li>
</ul>
<h2>Or: remove the doubt entirely</h2>
<p>Every review on LeaseReputation comes from a <strong>verified resident</strong> — someone who proved, with documentation, that they actually lived at the community, before anything published. One review per resident. Scores computed by algorithm, with statistical safeguards against single-review swings. Nothing sponsored, nothing buried, nothing for sale — operators can respond publicly, but they cannot touch the score.</p>
<div class="callout mint"><p><strong>The whole idea in one sentence:</strong> if verification happens before publication, fraud stops being a moderation problem — it becomes structurally impossible.</p></div>
"""},
]

# index page
def index_page():
    cards = "".join(
        f'<a class="gcard" href="{SITE}/guides/{a["slug"]}.html"><h2>{E(a["title"])}</h2><p>{E(a["lede"])}</p></a>'
        for a in ARTICLES)
    body = f"""<div class="wrap">
<div class="crumb"><a href="{SITE}/">Home</a> / Renter guides</div>
<h1>Renter <span class="accent">guides.</span></h1>
<p class="lede">The playbook for the biggest recurring financial decision most people make — written by the platform whose whole job is telling renters the truth.</p>
<p class="meta">Updated {TODAY}</p>
{cards}
<div class="cta-band">
  <h3>Know before you lease.</h3>
  <p>14,600+ communities with verified-resident reviews — scores that can't be bought, boosted, or buried.</p>
  <a class="btn" href="{SITE}/community/">Browse communities</a>
</div>
</div>"""
    return page("Renter Guides — Deposits, Tours, Leases & More | LeaseReputation",
                "Practical renter guides from LeaseReputation: getting your deposit back, apartment tour questions, lease red flags, breaking a lease, first-apartment checklist, and spotting fake reviews.",
                f"{SITE}/guides/", body)

os.makedirs("guides", exist_ok=True)
for a in ARTICLES:
    others = [o for o in ARTICLES if o is not a]
    with open(f"guides/{a['slug']}.html", "w", encoding="utf-8") as f:
        f.write(article_page(a, others))
    print(f"  + guides/{a['slug']}.html")
with open("guides/index.html", "w", encoding="utf-8") as f:
    f.write(index_page())
print("  + guides/index.html")

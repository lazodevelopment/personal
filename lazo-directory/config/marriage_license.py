"""Marriage licenses, state by state.  JC-LAZO-LICENSE-0920-001

/marriage-license/ and /marriage-license/<state>/, plus data.json for the
couple app's Marriage license card. Every couple asks the same five things
and nobody puts them on one page: how much, where, how long before the
wedding, how long it lasts, and who has to be there. The metro pages point
at the county office that actually issues it.

Accuracy: fees and rules are as published by the issuing offices in 2025 to
2026 and they change - most often the fee, by a few dollars, and county by
county. Every page says so and links to the office. `fee` is the typical
in-person fee in dollars (a range where counties differ), `wait_days` the
days between application and ceremony, `valid_days` how long the license
lasts once issued (0 = no expiry), `witnesses` how many must sign at the
ceremony, `issuer` the office in plain words. `course` notes a premarital
course discount where one exists. `notes` is the one thing that trips people
up in that state.

COUNTIES: for each Lazo metro, the office(s) that serve it. `site` is the
office's own domain; `apply` a direct page when one is stable.
"""

STATES = {
    "alabama": dict(name="Alabama", abbr="AL", issuer="County probate court (recording)", fee="70-85", wait_days=0, valid_days=30,
                    witnesses=0, min_age=18, course="",
                    notes="Alabama has no license since 2019. You complete and notarize a marriage certificate form, then record it with any probate court within 30 days of signing. No ceremony is legally required."),
    "alaska": dict(name="Alaska", abbr="AK", issuer="Bureau of Vital Statistics", fee="60", wait_days=3, valid_days=90, witnesses=2, min_age=18, course="",
                   notes="Three-day wait after applying. Two witnesses over 18 at the ceremony."),
    "arizona": dict(name="Arizona", abbr="AZ", issuer="Clerk of the Superior Court", fee="83", wait_days=0, valid_days=365, witnesses=2, min_age=18, course="",
                    notes="Valid a full year anywhere in Arizona. Both of you appear with photo ID."),
    "arkansas": dict(name="Arkansas", abbr="AR", issuer="County clerk", fee="60", wait_days=0, valid_days=60, witnesses=0, min_age=18, course="",
                     notes="Return the signed license to the clerk within 60 days of the ceremony."),
    "california": dict(name="California", abbr="CA", issuer="County clerk-recorder", fee="35-120", wait_days=0, valid_days=90, witnesses=1, min_age=18, course="",
                       notes="Two kinds: a public license (one witness, public record) and a confidential license (no witness, you must already live together, not public). Fees differ by county; San Francisco is the high end."),
    "colorado": dict(name="Colorado", abbr="CO", issuer="County clerk and recorder", fee="30", wait_days=0, valid_days=35, witnesses=0, min_age=18, course="",
                     notes="Colorado lets you marry yourselves: no officiant or witnesses needed. Only 35 days to use it, so apply close to the date."),
    "connecticut": dict(name="Connecticut", abbr="CT", issuer="Town or city clerk where the ceremony happens", fee="50", wait_days=0, valid_days=65, witnesses=0, min_age=18, course="",
                        notes="Apply in the town where you will marry, not where you live."),
    "delaware": dict(name="Delaware", abbr="DE", issuer="Clerk of the Peace", fee="50-100", wait_days=1, valid_days=30, witnesses=2, min_age=18, course="",
                     notes="Residents pay less than non-residents. 24-hour wait, then 30 days to use it."),
    "district-of-columbia": dict(name="Washington, DC", abbr="DC", issuer="Marriage Bureau, DC Superior Court", fee="45", wait_days=0, valid_days=0, witnesses=0, min_age=18, course="",
                                 notes="Apply online. Your officiant must be registered with the court before the ceremony, which is the step people miss."),
    "florida": dict(name="Florida", abbr="FL", issuer="Clerk of the circuit court", fee="86", wait_days=3, valid_days=60, witnesses=0, min_age=18, course="A registered premarital course (4 hours) cuts the fee to about $61 and removes the three-day wait for Florida residents.",
                    notes="The three-day wait applies only to Florida residents, and the course waives it. Out-of-state couples can marry the same day."),
    "georgia": dict(name="Georgia", abbr="GA", issuer="County probate court", fee="56-76", wait_days=0, valid_days=0, witnesses=0, min_age=18, course="A qualifying premarital course (6 hours) drops the fee by about $40.",
                    notes="If neither of you lives in Georgia, apply in the county where the ceremony is. No expiry once issued."),
    "hawaii": dict(name="Hawaii", abbr="HI", issuer="Department of Health, through a licensed agent", fee="65", wait_days=0, valid_days=30, witnesses=0, min_age=18, course="",
                   notes="Apply online first, then both of you meet a licensed agent in person to be issued. Only 30 days to use it, so plan the agent visit for the week of."),
    "idaho": dict(name="Idaho", abbr="ID", issuer="County recorder", fee="30", wait_days=0, valid_days=0, witnesses=0, min_age=18, course="",
                  notes="No wait, no expiry, one of the cheapest in the country."),
    "illinois": dict(name="Illinois", abbr="IL", issuer="County clerk", fee="60", wait_days=1, valid_days=60, witnesses=0, min_age=18, course="",
                     notes="You must marry in the county that issued the license. One-day wait: apply the day before at the latest."),
    "indiana": dict(name="Indiana", abbr="IN", issuer="Clerk of the circuit court", fee="25-65", wait_days=0, valid_days=60, witnesses=0, min_age=18, course="",
                    notes="Indiana residents pay about $25; couples from out of state pay about $65 and must apply in the county where they marry."),
    "iowa": dict(name="Iowa", abbr="IA", issuer="County recorder", fee="35", wait_days=3, valid_days=180, witnesses=1, min_age=18, course="",
                 notes="Three-day wait (a judge can waive it for a small fee). One witness signs the application, not just the ceremony."),
    "kansas": dict(name="Kansas", abbr="KS", issuer="Clerk of the district court", fee="86", wait_days=3, valid_days=180, witnesses=2, min_age=18, course="",
                   notes="Three-day wait after applying. Valid six months anywhere in Kansas."),
    "kentucky": dict(name="Kentucky", abbr="KY", issuer="County clerk", fee="50", wait_days=0, valid_days=30, witnesses=2, min_age=18, course="",
                     notes="Only 30 days to use it. Two witnesses at the ceremony."),
    "louisiana": dict(name="Louisiana", abbr="LA", issuer="Clerk of court (Orleans Parish: Vital Records)", fee="28-36", wait_days=1, valid_days=30, witnesses=2, min_age=18, course="",
                      notes="24-hour wait, waivable by a judge. Bring a certified birth certificate; Louisiana asks for it where most states do not."),
    "maine": dict(name="Maine", abbr="ME", issuer="Town or city clerk", fee="40", wait_days=0, valid_days=90, witnesses=2, min_age=18, course="",
                  notes="Residents apply in their own town; visitors apply in the town where they will marry."),
    "maryland": dict(name="Maryland", abbr="MD", issuer="Clerk of the circuit court", fee="35-85", wait_days=2, valid_days=180, witnesses=0, min_age=18, course="",
                     notes="Apply in the county where the ceremony is, not where you live. 48-hour wait. If one of you cannot come, the other can bring a notarized affidavit."),
    "massachusetts": dict(name="Massachusetts", abbr="MA", issuer="City or town clerk", fee="25-50", wait_days=3, valid_days=60, witnesses=0, min_age=18, course="",
                          notes="Three-day wait after filing intentions, then pick up the license. Any city or town clerk in the state will do."),
    "michigan": dict(name="Michigan", abbr="MI", issuer="County clerk", fee="20-30", wait_days=3, valid_days=33, witnesses=2, min_age=18, course="",
                     notes="Residents apply in their own county; out-of-state couples apply where they will marry. Three-day wait and only 33 days of validity."),
    "minnesota": dict(name="Minnesota", abbr="MN", issuer="County (local registrar)", fee="115", wait_days=0, valid_days=180, witnesses=2, min_age=18, course="Twelve hours of premarital education with a licensed provider cuts the fee to about $40.",
                      notes="The full fee is one of the highest in the country; the course discount is real money."),
    "mississippi": dict(name="Mississippi", abbr="MS", issuer="Circuit clerk", fee="20-35", wait_days=0, valid_days=0, witnesses=0, min_age=18, course="",
                        notes="Bring a certified birth certificate. No wait and no expiry."),
    "missouri": dict(name="Missouri", abbr="MO", issuer="Recorder of deeds", fee="51", wait_days=0, valid_days=30, witnesses=0, min_age=18, course="",
                     notes="Only 30 days to use it. Apply the month of the wedding."),
    "montana": dict(name="Montana", abbr="MT", issuer="Clerk of the district court", fee="53", wait_days=0, valid_days=180, witnesses=2, min_age=18, course="",
                    notes="Valid six months. Montana also recognises marriage by declaration."),
    "nebraska": dict(name="Nebraska", abbr="NE", issuer="County clerk", fee="25", wait_days=0, valid_days=365, witnesses=2, min_age=19, course="",
                     notes="Minimum age is 19 without parental consent, the only state where it is. Valid one year."),
    "nevada": dict(name="Nevada", abbr="NV", issuer="County clerk (Clark County Marriage License Bureau in Las Vegas)", fee="102", wait_days=0, valid_days=365, witnesses=1, min_age=18, course="",
                   notes="The Las Vegas bureau is open late every day and takes an online pre-application. One witness at the ceremony."),
    "new-hampshire": dict(name="New Hampshire", abbr="NH", issuer="Town or city clerk", fee="50", wait_days=0, valid_days=90, witnesses=0, min_age=18, course="",
                          notes="Any town clerk in the state; no wait."),
    "new-jersey": dict(name="New Jersey", abbr="NJ", issuer="Local registrar of the municipality", fee="28", wait_days=3, valid_days=30, witnesses=1, min_age=18, course="",
                       notes="72-hour wait, and a witness over 18 must come with you to apply. Apply where either of you lives, or where you will marry if neither lives in New Jersey."),
    "new-mexico": dict(name="New Mexico", abbr="NM", issuer="County clerk", fee="25", wait_days=0, valid_days=0, witnesses=2, min_age=18, course="",
                       notes="No wait, no expiry. Two witnesses at the ceremony."),
    "new-york": dict(name="New York", abbr="NY", issuer="City or town clerk (Office of the City Clerk in NYC)", fee="35-40", wait_days=1, valid_days=60, witnesses=1, min_age=18, course="",
                     notes="24-hour wait between issue and ceremony, which a judge can waive. NYC takes an online application, then one in-person visit."),
    "north-carolina": dict(name="North Carolina", abbr="NC", issuer="Register of deeds", fee="60", wait_days=0, valid_days=60, witnesses=2, min_age=18, course="",
                           notes="Any county's register of deeds, valid statewide. Two witnesses at the ceremony."),
    "north-dakota": dict(name="North Dakota", abbr="ND", issuer="County recorder", fee="65", wait_days=0, valid_days=60, witnesses=2, min_age=18, course="",
                         notes="No wait. Two witnesses over 18."),
    "ohio": dict(name="Ohio", abbr="OH", issuer="County probate court", fee="40-75", wait_days=0, valid_days=60, witnesses=0, min_age=18, course="",
                 notes="Ohio residents must apply in the county where one of you lives; out-of-state couples apply where they will marry. Fees differ by county."),
    "oklahoma": dict(name="Oklahoma", abbr="OK", issuer="Court clerk", fee="50", wait_days=0, valid_days=10, witnesses=0, min_age=18, course="A premarital counseling certificate drops the fee to about $5.",
                     notes="Only ten days to use it, the shortest in the country. Apply the week of the wedding."),
    "oregon": dict(name="Oregon", abbr="OR", issuer="County clerk", fee="60", wait_days=3, valid_days=60, witnesses=2, min_age=18, course="",
                   notes="Three-day wait, waivable for a small fee. Two witnesses at the ceremony."),
    "pennsylvania": dict(name="Pennsylvania", abbr="PA", issuer="Register of Wills / Clerk of Orphans' Court", fee="40-90", wait_days=3, valid_days=60, witnesses=0, min_age=18, course="",
                         notes="Three-day wait. Pennsylvania offers a self-uniting license, no officiant, with two witnesses instead."),
    "rhode-island": dict(name="Rhode Island", abbr="RI", issuer="City or town clerk", fee="24", wait_days=0, valid_days=90, witnesses=2, min_age=18, course="",
                         notes="Residents apply in their own town; visitors where they will marry."),
    "south-carolina": dict(name="South Carolina", abbr="SC", issuer="County probate court", fee="30-100", wait_days=1, valid_days=0, witnesses=0, min_age=18, course="",
                           notes="24-hour wait after applying, then no expiry. Fees vary widely by county."),
    "south-dakota": dict(name="South Dakota", abbr="SD", issuer="Register of deeds", fee="40", wait_days=0, valid_days=20, witnesses=0, min_age=18, course="",
                         notes="Only 20 days to use it."),
    "tennessee": dict(name="Tennessee", abbr="TN", issuer="County clerk", fee="100", wait_days=0, valid_days=30, witnesses=0, min_age=18, course="A premarital preparation course (4 hours) cuts the fee by $60.",
                      notes="Valid only 30 days, so apply the month of. The course discount is worth taking."),
    "texas": dict(name="Texas", abbr="TX", issuer="County clerk", fee="71-85", wait_days=3, valid_days=90, witnesses=0, min_age=18, course="The free Twogether in Texas course (8 hours) waives the 72-hour wait and $60 of the fee.",
                  notes="72-hour wait unless you take the course or one of you is active military. Any county clerk, valid statewide."),
    "utah": dict(name="Utah", abbr="UT", issuer="County clerk", fee="30-50", wait_days=0, valid_days=32, witnesses=2, min_age=18, course="",
                 notes="Only 32 days to use it. Two witnesses at the ceremony."),
    "vermont": dict(name="Vermont", abbr="VT", issuer="Town clerk", fee="80", wait_days=0, valid_days=60, witnesses=0, min_age=18, course="",
                    notes="Residents apply in their own town; visitors in the town where they will marry."),
    "virginia": dict(name="Virginia", abbr="VA", issuer="Clerk of the circuit court", fee="30", wait_days=0, valid_days=60, witnesses=0, min_age=18, course="",
                     notes="Any circuit court clerk, valid statewide, no wait, no witnesses."),
    "washington": dict(name="Washington", abbr="WA", issuer="County auditor", fee="62-72", wait_days=3, valid_days=60, witnesses=2, min_age=18, course="",
                       notes="Three-day wait after applying, then 60 days to use it. Two witnesses at the ceremony."),
    "west-virginia": dict(name="West Virginia", abbr="WV", issuer="County clerk", fee="36-61", wait_days=0, valid_days=60, witnesses=0, min_age=18, course="A premarital course drops the fee by about $20.",
                          notes="Residents apply in the county where one of you lives."),
    "wisconsin": dict(name="Wisconsin", abbr="WI", issuer="County clerk", fee="75-125", wait_days=3, valid_days=30, witnesses=2, min_age=18, course="",
                      notes="Wisconsin residents apply in the county where one of you has lived for 30 days; the three-day wait can be waived for a fee. Only 30 days to use it."),
    "wyoming": dict(name="Wyoming", abbr="WY", issuer="County clerk", fee="30", wait_days=0, valid_days=365, witnesses=2, min_age=18, course="",
                    notes="Valid one year. Two witnesses at the ceremony."),
}

BY_ABBR = {v["abbr"]: k for k, v in STATES.items()}

# metro id -> offices. (county/city, office, site, fee override or "", note)
COUNTIES = {
    "phoenix": [("Maricopa County", "Clerk of the Superior Court", "https://www.clerkofcourt.maricopa.gov", "83", "Several locations; some take walk-ins, others need an appointment.")],
    "tucson": [("Pima County", "Clerk of the Superior Court", "https://www.sc.pima.gov", "83", "")],
    "denver": [("City and County of Denver", "Clerk and Recorder", "https://www.denvergov.org", "30", "Online application, then a short in-person visit.")],
    "dallas-fort-worth": [("Dallas County", "County Clerk", "https://www.dallascounty.org", "81", ""), ("Tarrant County", "County Clerk", "https://www.tarrantcountytx.gov", "81", "")],
    "houston": [("Harris County", "County Clerk", "https://www.cclerk.hctx.net", "74", "Many annex locations; check hours.")],
    "austin": [("Travis County", "County Clerk", "https://www.traviscountyclerk.org", "81", "")],
    "san-antonio": [("Bexar County", "County Clerk", "https://www.bexar.org", "81", "")],
    "las-vegas": [("Clark County", "Marriage License Bureau", "https://www.clarkcountynv.gov", "102", "Open every day until midnight; pre-apply online and bring the confirmation.")],
    "atlanta": [("Fulton County", "Probate Court", "https://www.fultoncountyga.gov", "56", "Bring the premarital course certificate for the discount.")],
    "savannah": [("Chatham County", "Probate Court", "https://www.chathamcountyga.gov", "", "")],
    "nashville": [("Davidson County", "County Clerk", "https://www.nashville.gov", "100", "Any Davidson County Clerk office.")],
    "memphis": [("Shelby County", "County Clerk", "https://www.shelbycountytn.gov", "100", "")],
    "chicago": [("Cook County", "County Clerk", "https://www.cookcountyclerkil.gov", "60", "Downtown and suburban offices; you must marry within Cook County.")],
    "los-angeles": [("Los Angeles County", "Registrar-Recorder/County Clerk", "https://www.lavote.gov", "91", "Public license about $91, confidential about $85; appointments online.")],
    "san-diego": [("San Diego County", "County Clerk", "https://www.sdarcc.gov", "70", "Appointments online.")],
    "orange-county": [("Orange County", "Clerk-Recorder", "https://www.ocrecorder.com", "61", "Public about $61, confidential about $66.")],
    "inland-empire": [("Riverside County", "Assessor-County Clerk-Recorder", "https://www.rivcoacr.org", "", ""), ("San Bernardino County", "Assessor-Recorder-County Clerk", "https://www.sbcounty.gov", "", "")],
    "palm-springs": [("Riverside County", "Assessor-County Clerk-Recorder", "https://www.rivcoacr.org", "", "The Palm Desert office is closest to Palm Springs.")],
    "san-francisco-bay": [("San Francisco", "County Clerk", "https://www.sf.gov", "120", "City Hall; appointments online."), ("Alameda County", "Clerk-Recorder", "https://www.acgov.org", "", ""), ("Santa Clara County", "Clerk-Recorder", "https://www.sccgov.org", "", "")],
    "sacramento": [("Sacramento County", "Clerk/Recorder", "https://ccr.saccounty.gov", "", "")],
    "santa-barbara": [("Santa Barbara County", "Clerk-Recorder", "https://www.countyofsb.org", "", "")],
    "miami": [("Miami-Dade County", "Clerk of the Courts", "https://www.miamidadeclerk.gov", "86", "Several courthouse locations; the course certificate cuts the fee.")],
    "orlando": [("Orange County", "Clerk of Courts", "https://www.myorangeclerk.com", "86", "")],
    "tampa": [("Hillsborough County", "Clerk of Court", "https://www.hillsclerk.com", "86", "")],
    "jacksonville": [("Duval County", "Clerk of Courts", "https://www.duvalclerk.com", "86", "")],
    "charlotte": [("Mecklenburg County", "Register of Deeds", "https://www.mecknc.gov", "60", "")],
    "raleigh-durham": [("Wake County", "Register of Deeds", "https://www.wake.gov", "60", ""), ("Durham County", "Register of Deeds", "https://www.dconc.gov", "60", "")],
    "asheville": [("Buncombe County", "Register of Deeds", "https://www.buncombecounty.org", "60", "")],
    "seattle": [("King County", "Recorder's Office", "https://kingcounty.gov", "72", "Apply online or in person; the three-day wait starts at application.")],
    "salt-lake-city": [("Salt Lake County", "County Clerk", "https://www.slco.org", "50", "Online application, then pick up.")],
    "new-york-city": [("New York City", "Office of the City Clerk", "https://www.cityclerk.nyc.gov", "35", "Apply online, then one visit to a borough office; 24-hour wait before the ceremony.")],
    "buffalo": [("City of Buffalo", "City Clerk", "https://www.buffalony.gov", "40", "")],
    "boston": [("City of Boston", "City Clerk", "https://www.boston.gov", "50", "File intentions, wait three days, pick up.")],
    "providence": [("City of Providence", "City Clerk", "https://www.providenceri.gov", "24", "")],
    "hartford-new-haven": [("City of Hartford", "Town and City Clerk", "https://www.hartfordct.gov", "50", "Apply in the town where the ceremony is."), ("City of New Haven", "City Clerk", "https://www.newhavenct.gov", "50", "")],
    "philadelphia": [("Philadelphia", "Marriage License Bureau, Register of Wills", "https://www.phila.gov", "90", "City Hall; three-day wait.")],
    "pittsburgh": [("Allegheny County", "Marriage License Bureau", "https://www.alleghenycounty.us", "80", "")],
    "washington-dc": [("District of Columbia", "Marriage Bureau, DC Superior Court", "https://www.dccourts.gov", "45", "Apply online; register your officiant with the court first.")],
    "baltimore": [("Baltimore City", "Clerk of the Circuit Court", "https://www.mdcourts.gov", "85", "Apply in the jurisdiction where the ceremony is."), ("Baltimore County", "Clerk of the Circuit Court", "https://www.mdcourts.gov", "55", "")],
    "richmond": [("City of Richmond", "Clerk of the Circuit Court", "https://www.rva.gov", "30", "")],
    "virginia-beach": [("City of Virginia Beach", "Clerk of the Circuit Court", "https://www.vbgov.com", "30", "")],
    "portland": [("Multnomah County", "County Clerk", "https://www.multco.us", "60", "Three-day wait, waivable for a fee.")],
    "minneapolis": [("Hennepin County", "Service Centers", "https://www.hennepin.us", "115", "About $40 with the education certificate.")],
    "st-louis": [("St. Louis City", "Recorder of Deeds", "https://www.stlouis-mo.gov", "51", ""), ("St. Louis County", "Recorder of Deeds", "https://stlouiscountymo.gov", "51", "")],
    "kansas-city": [("Jackson County", "Recorder of Deeds", "https://www.jacksongov.org", "51", "")],
    "columbus": [("Franklin County", "Probate Court", "https://probate.franklincountyohio.gov", "65", "")],
    "cincinnati": [("Hamilton County", "Probate Court", "https://www.probatect.org", "75", "")],
    "cleveland": [("Cuyahoga County", "Probate Court", "https://probate.cuyahogacounty.gov", "60", "")],
    "new-orleans": [("Orleans Parish", "Marriage License Office, Louisiana Vital Records", "https://ldh.la.gov", "28", "Bring a certified birth certificate; 24-hour wait.")],
    "indianapolis": [("Marion County", "County Clerk", "https://www.indy.gov", "25", "About $65 for couples from out of state.")],
    "charleston": [("Charleston County", "Probate Court", "https://www.charlestoncounty.org", "70", "24-hour wait.")],
    "detroit": [("Wayne County", "County Clerk", "https://www.waynecounty.com", "20", "About $30 for couples from out of state.")],
    "grand-rapids": [("Kent County", "County Clerk", "https://www.accesskent.com", "20", "")],
    "milwaukee": [("Milwaukee County", "County Clerk", "https://county.milwaukee.gov", "", "Three-day wait, waivable for a fee.")],
    "louisville": [("Jefferson County", "County Clerk", "https://www.jeffersoncountyclerk.org", "50", "")],
    "oklahoma-city": [("Oklahoma County", "Court Clerk", "https://www.oklahomacounty.org", "50", "About $5 with a premarital counseling certificate.")],
    "birmingham": [("Jefferson County", "Probate Court", "https://www.jccal.org", "", "Alabama records a notarized marriage certificate form; no license is issued.")],
    "honolulu": [("Honolulu", "Department of Health, Vital Records (licensed agents)", "https://health.hawaii.gov/vitalrecords", "65", "Apply online, then meet an agent in person; 30 days to use it.")],
    # tranche 7 (2026-09-21)
    'rochester': [('Monroe County', 'County Clerk', 'https://www.monroecounty.gov', '', '')],
    'albany': [('Albany County', 'County Clerk', 'https://www.albanycounty.com', '', ''), ('Saratoga County', 'County Clerk', 'https://www.saratogacountyny.gov', '', '')],
    'syracuse': [('Onondaga County', 'County Clerk', 'https://www.ongov.net', '', '')],
    'lehigh-valley': [('Lehigh County', "Clerk of Orphans' Court", 'https://www.lehighcounty.org', '', ''), ('Northampton County', "Clerk of Orphans' Court", 'https://www.norcopa.gov', '', '')],
    'tulsa': [('Tulsa County', 'Court Clerk', 'https://www.tulsacounty.org', '', '')],
    'omaha': [('Douglas County', 'County Clerk', 'https://www.douglascounty-ne.gov', '', ''), ('Lancaster County', 'County Clerk', 'https://www.lancaster.ne.gov', '', '')],
    'albuquerque': [('Bernalillo County', 'County Clerk', 'https://www.bernco.gov', '', ''), ('Santa Fe County', 'County Clerk', 'https://www.santafecountynm.gov', '', '')],
    'el-paso': [('El Paso County', 'County Clerk', 'https://www.epcounty.com', '', '')],
    'fresno': [('Fresno County', 'County Clerk/Registrar', 'https://www.fresnocountyca.gov', '', '')],
    'bakersfield': [('Kern County', 'County Clerk', 'https://www.kerncounty.com', '', '')],
    'colorado-springs': [('El Paso County', 'Clerk and Recorder', 'https://clerkandrecorder.elpasoco.com', '', ''), ('Pueblo County', 'Clerk and Recorder', 'https://county.pueblo.org', '', '')],
    'boise': [('Ada County', 'County Recorder', 'https://adacounty.id.gov', '', '')],
    'des-moines': [('Polk County', 'County Recorder', 'https://www.polkcountyiowa.gov', '', '')],
    'madison': [('Dane County', 'County Clerk', 'https://www.danecounty.gov', '', '')],
    'knoxville': [('Knox County', 'County Clerk', 'https://www.knoxcounty.org', '', '')],
    'greenville-sc': [('Greenville County', 'Probate Court', 'https://www.greenvillecounty.org', '', ''), ('Spartanburg County', 'Probate Court', 'https://www.spartanburgcounty.org', '', '')],
    'columbia-sc': [('Richland County', 'Probate Court', 'https://www.richlandcountysc.gov', '', ''), ('Lexington County', 'Probate Court', 'https://www.lex-co.sc.gov', '', '')],
    'baton-rouge': [('East Baton Rouge Parish', 'Clerk of Court', 'https://www.ebrclerkofcourt.org', '', ''), ('Lafayette Parish', 'Clerk of Court', 'https://www.lpclerk.com', '', '')],
    'dayton': [('Montgomery County', 'Probate Court', 'https://www.mcohio.org', '', '')],
    'toledo': [('Lucas County', 'Probate Court', 'https://www.co.lucas.oh.us', '', '')],
    'fort-myers-naples': [('Lee County', 'Clerk of Court', 'https://www.leeclerk.org', '', ''), ('Collier County', 'Clerk of Court', 'https://www.collierclerk.com', '', '')],
    'sarasota': [('Sarasota County', 'Clerk of Court', 'https://www.sarasotaclerk.com', '', ''), ('Manatee County', 'Clerk of Court', 'https://www.manateeclerk.com', '', '')],
    'daytona-beach': [('Volusia County', 'Clerk of Court', 'https://www.clerk.org', '', ''), ('St. Johns County', 'Clerk of Court', 'https://www.stjohnsclerk.com', '', '')],
    'key-west': [('Monroe County', 'Clerk of Court', 'https://www.monroe-clerk.com', '', '')],
    'greensboro': [('Guilford County', 'Register of Deeds', 'https://www.guilfordcountync.gov', '', ''), ('Forsyth County', 'Register of Deeds', 'https://www.forsyth.cc', '', '')],
    'wilmington-nc': [('New Hanover County', 'Register of Deeds', 'https://www.nhcgov.com', '', '')],
    'outer-banks': [('Dare County', 'Register of Deeds', 'https://www.darenc.gov', '', '')],
    'napa-sonoma': [('Napa County', 'County Clerk-Recorder', 'https://www.countyofnapa.org', '', ''), ('Sonoma County', 'Clerk-Recorder', 'https://sonomacounty.ca.gov', '', '')],
    'lake-tahoe-reno': [('Washoe County', 'County Clerk', 'https://www.washoecounty.gov', '', ''), ('El Dorado County', 'Recorder-Clerk', 'https://www.edcgov.us', '', 'Serves South Lake Tahoe on the California side.')],
    'maui': [('Maui County', 'Department of Health, Marriage License Office', 'https://health.hawaii.gov', '', 'Apply online through the state health department, then meet an agent in person.')],
    'sedona': [('Yavapai County', 'Clerk of the Superior Court', 'https://www.yavapaiaz.gov', '', ''), ('Coconino County', 'Clerk of the Superior Court', 'https://www.coconino.az.gov', '', '')],
    'monterey-big-sur': [('Monterey County', 'County Clerk-Recorder', 'https://www.countyofmonterey.gov', '', '')],
    'aspen-vail': [('Pitkin County', 'Clerk and Recorder', 'https://pitkincounty.com', '', ''), ('Eagle County', 'Clerk and Recorder', 'https://www.eaglecounty.us', '', '')],
    'jackson-hole': [('Teton County', 'County Clerk', 'https://www.tetoncountywy.gov', '', '')],
    'cape-cod': [('Town of Barnstable', 'Town Clerk', 'https://www.townofbarnstable.us', '', 'Any Massachusetts city or town clerk issues a license valid statewide.')],
    'hudson-valley': [('Dutchess County', 'County Clerk', 'https://www.dutchessny.gov', '', ''), ('Ulster County', 'County Clerk', 'https://ulstercountyny.gov', '', '')],
    'hamptons': [('Town of Southampton', 'Town Clerk', 'https://www.southamptontownny.gov', '', 'Any New York town or city clerk issues a license valid statewide.')],
    'poconos': [('Monroe County', "Clerk of Orphans' Court", 'https://www.monroecountypa.gov', '', '')],
    'smoky-mountains': [('Sevier County', 'County Clerk', 'https://www.seviercountytn.gov', '', 'One of the busiest marriage license offices in the state; no wait, no residency requirement.')],
    'anchorage': [('Anchorage', 'Bureau of Vital Statistics', 'https://health.alaska.gov', '', '')],
    'little-rock': [('Pulaski County', 'County Clerk', 'https://www.pulaskiclerk.com', '', '')],
    'wichita': [('Sedgwick County', 'District Court Clerk', 'https://www.sedgwickcounty.org', '', '')],
    'portland-maine': [('City of Portland', 'City Clerk', 'https://www.portlandmaine.gov', '', 'Any Maine town or city clerk; visitors apply where they will marry.')],
    'jackson-ms': [('Hinds County', 'Circuit Clerk', 'https://www.hindscountyms.com', '', '')],
    'billings': [('Yellowstone County', 'Clerk of District Court', 'https://www.yellowstonecountymt.gov', '', ''), ('Gallatin County', 'Clerk of District Court', 'https://www.gallatinmt.gov', '', '')],
    'fargo': [('Cass County', 'County Recorder', 'https://www.casscountynd.gov', '', '')],
    'manchester-nh': [('City of Manchester', 'City Clerk', 'https://www.manchesternh.gov', '', 'Any New Hampshire town or city clerk issues a license valid statewide.')],
    'sioux-falls': [('Minnehaha County', 'Register of Deeds', 'https://www.minnehahacounty.gov', '', '')],
    'burlington-vt': [('City of Burlington', 'City Clerk', 'https://www.burlingtonvt.gov', '', 'Any Vermont town clerk issues a license valid statewide.')],
    'charleston-wv': [('Kanawha County', 'County Clerk', 'https://kanawha.us', '', '')],
}


def fee_text(fee):
    """'71-85' -> 'About $71 to $85'; '86' -> 'About $86'; '' -> ''."""
    if not fee:
        return ""
    if "-" in fee:
        a, b = fee.split("-", 1)
        return f"About ${a} to ${b}"
    return f"About ${fee}"


def wait_text(d):
    return "No waiting period" if d == 0 else (f"{d}-day wait" if d > 1 else "24-hour wait")


def valid_text(d):
    if d == 0:
        return "Does not expire"
    if d % 365 == 0:
        return "Valid 1 year" if d == 365 else f"Valid {d // 365} years"
    if d % 30 == 0 and d >= 90:
        return f"Valid {d // 30} months"
    return f"Valid {d} days"

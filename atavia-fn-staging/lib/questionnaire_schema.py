"""Wedding Day Questionnaire schema — single source of truth for the web form
and the server-side accepted-field list. Mirrors the PDF's 9 sections
(signatures replaced by the tokenized link + accuracy confirmation)."""

# (field_id, label, input_type, placeholder/options)
QUESTIONNAIRE_SECTIONS = [
    ("01 · Client Information", [
        ("p1_name", "Partner 1 — Full Name", "text", ""),
        ("p2_name", "Partner 2 — Full Name", "text", ""),
        ("contact_phone", "Best Contact Phone", "tel", ""),
        ("contact_email", "Email Address", "email", ""),
        ("wedding_date", "Wedding Date", "date", ""),
    ]),
    ("02 · Ceremony Details", [
        ("cer_venue", "Ceremony Venue Name", "text", ""),
        ("cer_address", "Ceremony Venue Address", "text", "Street, City, State, ZIP"),
        ("cer_start", "Ceremony Start Time", "time", ""),
        ("cer_end", "Estimated End Time", "time", ""),
        ("cer_contact_name", "Venue Contact Name", "text", ""),
        ("cer_contact_phone", "Venue Contact Phone", "tel", ""),
        ("officiant", "Officiant / Ceremony Coordinator — Name & Phone", "text", ""),
        ("indoor_outdoor", "Indoor / Outdoor?", "radio",
         ["Indoor", "Outdoor", "Both"]),
        ("parking_notes", "Parking & Vendor Access Notes", "textarea",
         "Gate codes, lot info, load-in restrictions, etc."),
    ]),
    ("03 · Reception Details", [
        ("same_venue", "Same venue as ceremony?", "radio",
         ["Yes — same venue", "No — different venue"]),
        ("rec_venue", "Reception Venue Name", "text", ""),
        ("rec_address", "Reception Venue Address", "text", "Street, City, State, ZIP"),
        ("cocktail_start", "Cocktail Hour Start Time", "time", ""),
        ("rec_start", "Reception Start Time", "time", ""),
        ("rec_end", "Reception End Time", "time", ""),
        ("grand_exit", "Grand Exit Time (if applicable)", "time", ""),
        ("rec_contact_name", "Reception Venue Contact Name", "text", ""),
        ("rec_contact_phone", "Reception Venue Contact Phone", "tel", ""),
        ("coordinator", "Day-Of Coordinator / Planner — Name & Phone", "text", ""),
    ]),
    ("04 · Day-Of Timeline", [
        ("ready_location", "Getting Ready — Full Address / Location", "text",
         "Hotel room number, suite name, bridal suite address, etc."),
        ("arrival_time", "Photographer / Videographer Arrival Time", "time", ""),
        ("ready_start", "Getting Ready Start Time", "time", ""),
        ("firstlook_time", "First Look — Time (or N/A)", "text", "e.g. 2:30 PM or N/A"),
        ("firstlook_loc", "First Look — Location", "text", ""),
        ("party_time", "Bridal Party Photos — Time", "text", ""),
        ("party_loc", "Bridal Party Photos — Location", "text", ""),
        ("formals_time", "Family Formals — Time", "text", ""),
        ("formals_loc", "Family Formals — Location", "text", ""),
        ("portraits_time", "Couple Portraits — Time", "text", ""),
        ("portraits_loc", "Couple Portraits — Location", "text", ""),
    ]),
    ("05 · Key People & Family", [
        ("moh", "Maid / Matron of Honor — Name", "text", ""),
        ("best_man", "Best Man — Name", "text", ""),
        ("parents", "Parents to be Featured", "textarea",
         "Full names and relationship to couple"),
        ("vips", "Other VIPs to Watch For", "textarea",
         "Grandparents, godparents, special guests — names and relationship"),
    ]),
    ("06 · Must-Have Shots & Special Moments", [
        ("must_haves", "Must-Have Photo / Video Moments", "textarea",
         "List every specific shot or moment you cannot miss"),
        ("traditions", "Special Traditions or Rituals?", "checkbox",
         ["Unity Candle", "Sand Ceremony", "Handfasting", "Ring Warming", "Other"]),
        ("traditions_desc", "Describe Any Traditions or Special Moments",
         "textarea", ""),
    ]),
    ("07 · Other Vendors", [
        ("dj_name", "DJ / Band Name", "text", ""),
        ("dj_phone", "DJ / Band Contact Phone", "tel", ""),
        ("florist_name", "Florist Name", "text", ""),
        ("florist_phone", "Florist Contact Phone", "tel", ""),
        ("planner_name", "Wedding Planner / Coordinator", "text", ""),
        ("planner_phone", "Planner Contact Phone", "tel", ""),
        ("caterer_name", "Caterer / Catering Company", "text", ""),
        ("caterer_phone", "Catering Contact Phone", "tel", ""),
        ("hmua_name", "Hair & Makeup Artist(s)", "text", ""),
        ("hmua_phone", "Hair & Makeup Contact Phone", "tel", ""),
    ]),
    ("08 · Special Requests & Additional Notes", [
        ("requests", "Specific Requests for Photography / Videography",
         "textarea", ""),
        ("avoid", "Areas or People We Should AVOID Photographing", "textarea", ""),
        ("anything_else", "Anything Else We Should Know?", "textarea",
         "Allergies, mobility needs, surprise moments, weather contingency, etc."),
    ]),
]

ALL_FIELD_IDS = [f[0] for _, fields in QUESTIONNAIRE_SECTIONS for f in fields]

# (section_title, [(field_id, label), ...]) — for the owner summary email
SUMMARY_LAYOUT = [(title, [(f[0], f[1]) for f in fields])
                  for title, fields in QUESTIONNAIRE_SECTIONS]

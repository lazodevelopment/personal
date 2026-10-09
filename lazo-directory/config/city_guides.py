"""City guides on the top metro x category hubs.  JC-LAZO-GUIDE-1008

Zola (checked 2026-10-08) noindexes every faceted "city + category" search page it
has and ranks with ~700 curated pages instead: a local intro, a short list of picks,
"how we choose", and links to the same category in other cities. Lazo's hubs at
/<metro>/<category>/ already earn the impressions, so the guide is added to those
pages in place rather than on new URLs.

What may go on a guide, in this order of preference:
  1. computed facts  - sunset / golden hour (generate/solar.py), vendor counts by town
  2. config facts    - marriage license (marriage_license.py), lead time (booking.py),
                       typical cost (pricing.py / cost_guides.py)
  3. the notes below - one short, general, checkable paragraph per metro about where
                       and when people marry there. Geography and climate only: no
                       venue names, no rankings, no claims about any vendor.

Picks are NOT a ranking. Unclaimed vendors carry no reviews or ratings on Lazo, so
the shortlist says exactly how it was chosen: verified/claimed vendors first, then
vendors with their own website, at most two per town so the list spans the metro.

peak:  months (1-12) when most weddings happen there, used for the sunset table.
"""

GUIDE_CATS = ["wedding-venues", "wedding-photographers", "wedding-videographers",
              "wedding-planners", "wedding-florists", "wedding-djs"]

GUIDE_METROS = {
    "phoenix": dict(peak=[10, 11, 12, 1, 2, 3, 4],
        setting="Desert weddings here run on the calendar: the Sonoran sky and saguaro backdrops are the draw, and resort venues in Scottsdale and the foothills around Cave Creek and Carefree host much of the market.",
        weather="Summer highs routinely pass 105&deg;F, so outdoor ceremonies cluster from October to April; summer weddings move indoors or to early evening."),
    "denver": dict(peak=[5, 6, 7, 8, 9, 10],
        setting="Couples split between city venues in Denver and Boulder and mountain settings in the foothills around Evergreen and Idaho Springs, with Colorado Springs to the south.",
        weather="Summer afternoons bring frequent thunderstorms, so many ceremonies are set for late afternoon with an indoor fallback; mountain venues can see snow into May and from October."),
    "dallas-fort-worth": dict(peak=[3, 4, 5, 9, 10, 11],
        setting="The metroplex spreads from Dallas and Fort Worth out to Frisco, Grapevine, Denton and the ranch country beyond, so drive time between ceremony, reception and hotels is worth planning around.",
        weather="Spring and fall are the comfortable seasons; July and August heat pushes outdoor plans to after sunset, and spring storms make a rain plan essential."),
    "houston": dict(peak=[3, 4, 5, 10, 11, 12],
        setting="Weddings range from downtown and Memorial ballrooms to The Woodlands, Katy and the open country west toward Waller, with Galveston for beach ceremonies.",
        weather="Humidity and heat run from May through September and hurricane season peaks in August and September, so most outdoor weddings land in spring or late fall."),
    "austin": dict(peak=[3, 4, 5, 10, 11],
        setting="Austin couples choose between the city and the Hill Country to the west around Dripping Springs and Marble Falls, with Round Rock and Georgetown to the north.",
        weather="Spring wildflower season and October&ndash;November are the peak months; summer heat makes evening ceremonies the norm."),
    "san-antonio": dict(peak=[3, 4, 5, 10, 11, 12],
        setting="Venues run from the historic city center to the Hill Country around Boerne and the river towns of New Braunfels and Gruene.",
        weather="Spring and fall are the main seasons; summer heat keeps outdoor ceremonies to the evening."),
    "las-vegas": dict(peak=[3, 4, 5, 9, 10, 11],
        setting="Vegas weddings run from Strip chapels and resorts to desert and lake settings around Henderson, Summerlin and Boulder City, and many couples travel in for them.",
        weather="Summer highs regularly pass 105&deg;F, so outdoor ceremonies favour spring and fall; winter evenings get cold quickly after sunset."),
    "atlanta": dict(peak=[4, 5, 6, 9, 10, 11],
        setting="Couples marry in the city and the suburbs from Marietta to Alpharetta, and many head north into the north Georgia venue corridor around Canton for barns and mountain views.",
        weather="Spring and fall are the peak seasons; summer is hot and humid with afternoon storms, so a covered fallback matters."),
    "nashville": dict(peak=[4, 5, 6, 9, 10, 11],
        setting="Beyond the city itself, much of the venue market sits south in Franklin and Leiper's Fork, with more options east toward Lebanon and Murfreesboro.",
        weather="Spring and fall are busiest; summer is hot and humid, and spring brings frequent storms."),
    "chicago": dict(peak=[5, 6, 7, 8, 9, 10],
        setting="Weddings span downtown lofts and lakefront spaces, the North Shore from Evanston to Lake Forest, and the western and northwest suburbs from Naperville to Barrington.",
        weather="Outdoor season runs roughly May to October; winters are long and cold, which makes off-season dates easier to book and indoor venues the default."),
    "los-angeles": dict(peak=[4, 5, 6, 9, 10, 11],
        setting="The region covers beach and bluff settings from Malibu to the South Bay, Pasadena's gardens and estates, and inland options toward Santa Clarita and Pomona.",
        weather="Mild weather makes most of the year workable; inland heat peaks in late summer and early fall, while the coast stays cooler and can be overcast in May and June."),
    "san-diego": dict(peak=[4, 5, 6, 8, 9, 10],
        setting="Couples marry on the coast from La Jolla to Carlsbad, inland around Escondido, and in Temecula wine country to the north.",
        weather="The climate allows weddings year-round; coastal mornings in May and June are often overcast, and inland Temecula runs hotter in summer."),
    "miami": dict(peak=[11, 12, 1, 2, 3, 4],
        setting="The market runs along the coast from Miami and Coral Gables up through Fort Lauderdale, Boca Raton and West Palm Beach, with garden and estate venues south around Homestead and the Redland.",
        weather="The dry season from November to April is the peak; summer brings heat, daily rain and hurricane season from June to November."),
    "orlando": dict(peak=[1, 2, 3, 4, 10, 11, 12],
        setting="Weddings range from Winter Park and downtown Orlando to the resort corridor around Lake Buena Vista and the lakes near Clermont.",
        weather="Cooler, drier months from October to April are the peak; summer afternoons bring near-daily thunderstorms."),
    "tampa": dict(peak=[1, 2, 3, 4, 10, 11, 12],
        setting="Couples choose between Tampa, St. Petersburg and the Gulf beaches around Clearwater, with Sarasota to the south.",
        weather="Fall through spring is the main season; summer is hot with afternoon storms, and hurricane season runs June to November."),
    "charlotte": dict(peak=[4, 5, 6, 9, 10, 11],
        setting="Venues range from uptown Charlotte to Lake Norman and Huntersville to the north, Concord, and across the state line in Rock Hill.",
        weather="Spring and fall are peak; summers are hot and humid with afternoon storms."),
    "raleigh-durham": dict(peak=[4, 5, 6, 9, 10, 11],
        setting="The Triangle covers Raleigh, Durham, Chapel Hill and Cary, with farm and rural venues out around Pittsboro and Wake Forest.",
        weather="Spring and fall are the peak seasons; summer heat and humidity favour evening ceremonies."),
    "seattle": dict(peak=[6, 7, 8, 9],
        setting="Couples marry in the city, across the lake in Bellevue and the Eastside, in Woodinville wine country, and in the barn venues around Snohomish.",
        weather="July through September is the reliable dry window; the rest of the year is mild but often wet, so covered space is a must outside summer."),
    "salt-lake-city": dict(peak=[5, 6, 7, 8, 9, 10],
        setting="Weddings run from the city and the Wasatch Front, Ogden to Provo, up into the mountains around Park City.",
        weather="Summer and early fall are the main season; mountain venues see snow from late fall into spring."),
    "boston": dict(peak=[5, 6, 7, 8, 9, 10],
        setting="Couples marry in the city and Cambridge, on the North Shore around Salem, on the South Shore and Cape edge, around Worcester, and many travel to Newport.",
        weather="June through October is the main season, with fall foliage driving demand for September and October dates; winters are cold and snowy."),
    "new-york-city": dict(peak=[5, 6, 9, 10],
        setting="The market covers all five boroughs plus Long Island, Westchester, North Jersey, the Jersey Shore, and the Hudson Valley to the north.",
        weather="Late spring and fall are the most sought-after; July and August are hot and humid, and winter weddings are almost always indoors."),
    "philadelphia": dict(peak=[5, 6, 9, 10],
        setting="Couples marry in the city, along the Main Line, in Bucks County around New Hope, in South Jersey, and as far as Wilmington and Lancaster.",
        weather="Late spring and fall are peak; summers are hot and humid and winters cold."),
    "washington-dc": dict(peak=[4, 5, 6, 9, 10],
        setting="Weddings span the District, Arlington and Alexandria, the Maryland suburbs to Annapolis and Frederick, and Virginia wine and barn country around Leesburg.",
        weather="Spring and fall are the peak seasons; summers are hot and humid."),
    "pittsburgh": dict(peak=[5, 6, 7, 8, 9, 10],
        setting="Venues run from downtown and the Strip District to the North and South Hills, barns in the Allegheny Valley, and the Laurel Highlands to the southeast.",
        weather="Late spring through fall is the main season; winters are cold and grey."),
    "kansas-city": dict(peak=[4, 5, 6, 9, 10],
        setting="Couples marry on both sides of the state line, from Kansas City and Overland Park to Lee's Summit and Liberty, with Weston and Lawrence on the edges.",
        weather="Spring and fall are peak; summer is hot and stormy and winters are cold."),
    "detroit": dict(peak=[5, 6, 7, 8, 9, 10],
        setting="Weddings range from downtown Detroit to Royal Oak and Birmingham, Ann Arbor, the lake venues around Clarkston, and barns downriver toward Monroe.",
        weather="The outdoor season runs late spring to early fall; winters are long and cold."),
    "minneapolis": dict(peak=[6, 7, 8, 9],
        setting="The Twin Cities market includes Minneapolis and St. Paul, Lake Minnetonka, and the river town of Stillwater.",
        weather="June through September is the main season; winters are severe, so off-season weddings are indoors."),
    "portland": dict(peak=[6, 7, 8, 9],
        setting="Couples marry in the city and in Vancouver across the river, in Willamette Valley wine country around McMinnville, and in the Columbia River Gorge around Hood River.",
        weather="July through September is the dependable dry season; the rest of the year is mild and often rainy."),
    "charleston": dict(peak=[3, 4, 5, 10, 11],
        setting="Charleston is a destination wedding city: the historic district, Mount Pleasant, and plantation and island settings on Johns Island and West Ashley, with Beaufort and Myrtle Beach further along the coast.",
        weather="Spring and fall are peak; summer heat and humidity are intense and hurricane season runs June to November."),
    "indianapolis": dict(peak=[5, 6, 7, 8, 9, 10],
        setting="Weddings range from downtown Indianapolis to Carmel, Fishers and Noblesville to the north, and Zionsville and Greenwood around the edges.",
        weather="Late spring to early fall is the main season; winters are cold."),
}

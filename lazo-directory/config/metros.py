"""Lazo metro registry. Nationwide-ready: add a metro dict + set tranche; seeder & generator pick it up.
grid: search tiles as (lat, lng) centers; radius_m per tile. Denser grid = better coverage, more API calls.
Tranches: 1 = launch (PHX/DEN/DFW), 2 = TX cluster/LV/ATL/BNA, 3 = wave-2 top metros, 4 = wave-3 national tier,
5 = national fill. 7 = the 2026-09-21 nationwide fill (50 metros: skipped top-100 metros, the
Florida/Carolina coast, destination markets, one metro per remaining state). 6 = the 2026-09-16 gap pass: Inland Empire, Baltimore, Orange County, Providence,
Hartford-New Haven, Oklahoma City, Buffalo, Birmingham, Grand Rapids, plus the destination markets
Santa Barbara, Palm Springs, Asheville and Honolulu. NOTE: adding a metro MOVES any spillover vendors
already caught by a neighbouring grid (vendors are keyed by placeId globally), so their URLs change.
Seed only with the redirect layer in place or those URLs become orphaned duplicates.
Seed with --tranche N (includes all tranches <= N; checkpoints skip already-seeded metros)."""

METROS = [
    {
        "id": "phoenix", "name": "Phoenix", "state": "AZ", "tranche": 1,
        "display": "Phoenix, Arizona",
        "center": (33.4484, -112.0740),
        "radius_m": 24000,
        "grid": [
            (33.4484, -112.0740),  # Phoenix core
            (33.4942, -111.9261),  # Scottsdale
            (33.3062, -111.8413),  # Chandler
            (33.4152, -111.8315),  # Mesa
            (33.3528, -111.7890),  # Gilbert
            (33.4255, -111.9400),  # Tempe
            (33.5387, -112.1860),  # Glendale
            (33.6292, -112.3680),  # Peoria/Surprise
            (33.3703, -112.5838),  # Buckeye/Goodyear
            (33.8039, -111.9550),  # Cave Creek/Carefree
        ],
    },
    {
        "id": "denver", "name": "Denver", "state": "CO", "tranche": 1,
        "display": "Denver, Colorado",
        "center": (39.7392, -104.9903),
        "radius_m": 24000,
        "grid": [
            (39.7392, -104.9903),  # Denver core
            (39.5501, -105.7821),  # Mountain venues corridor (Evergreen/Idaho Springs)
            (40.0150, -105.2705),  # Boulder
            (39.6133, -105.0166),  # Littleton
            (39.5807, -104.8772),  # Centennial/Parker
            (39.9205, -105.0867),  # Broomfield/Westminster
            (39.7294, -104.8319),  # Aurora
            (40.4233, -104.7091),  # Greeley/north
            (38.8339, -104.8214),  # Colorado Springs (52 Eighty territory)
        ],
    },
    {
        "id": "dallas-fort-worth", "name": "Dallas-Fort Worth", "state": "TX", "tranche": 1,
        "display": "Dallas-Fort Worth, Texas",
        "center": (32.7767, -96.7970),
        "radius_m": 26000,
        "grid": [
            (32.7767, -96.7970),  # Dallas core
            (32.7555, -97.3308),  # Fort Worth
            (33.1507, -96.8236),  # Frisco
            (33.0198, -96.6989),  # Plano
            (32.9343, -97.0781),  # Grapevine/Southlake
            (32.7357, -97.1081),  # Arlington
            (33.2148, -97.1331),  # Denton
            (32.5639, -96.3083),  # Kaufman/east
            (32.5007, -97.1247),  # Mansfield/south
        ],
    },
    # ---- TRANCHE 2 ----
    {
        "id": "houston", "name": "Houston", "state": "TX", "tranche": 2,
        "display": "Houston, Texas",
        "center": (29.7604, -95.3698), "radius_m": 26000,
        "grid": [
            (29.7604, -95.3698),  # Houston core
            (29.7752, -95.5580),  # Memorial/Energy Corridor
            (29.5502, -95.0966),  # Clear Lake/Kemah
            (30.1658, -95.4613),  # The Woodlands
            (29.6911, -95.2091),  # Pasadena/east
            (29.5636, -95.2860),  # Pearland
            (29.7858, -95.8245),  # Katy
            (30.0333, -95.9772),  # Waller/west venues
            (29.3013, -94.7977),  # Galveston (beach weddings)
        ],
    },
    {
        "id": "austin", "name": "Austin", "state": "TX", "tranche": 2,
        "display": "Austin, Texas",
        "center": (30.2672, -97.7431), "radius_m": 24000,
        "grid": [
            (30.2672, -97.7431),  # Austin core
            (30.5083, -97.6789),  # Round Rock/Georgetown
            (30.1327, -97.6390),  # SE/airport corridor
            (30.2960, -98.0170),  # Hill Country west (Dripping Springs)
            (30.0844, -97.8531),  # Buda/Kyle
            (30.5788, -98.2730),  # Marble Falls/Burnet hill country
            (30.6410, -97.6780),  # Georgetown north
        ],
    },
    {
        "id": "san-antonio", "name": "San Antonio", "state": "TX", "tranche": 2,
        "display": "San Antonio, Texas",
        "center": (29.4241, -98.4936), "radius_m": 25000,
        "grid": [
            (29.4241, -98.4936),  # SA core
            (29.5866, -98.6199),  # NW/Helotes
            (29.6520, -98.4530),  # Stone Oak north
            (29.8833, -98.0867),  # New Braunfels/Gruene
            (29.9979, -98.9017),  # Boerne hill country
            (29.3500, -98.3200),  # SE
        ],
    },
    {
        "id": "las-vegas", "name": "Las Vegas", "state": "NV", "tranche": 2,
        "display": "Las Vegas, Nevada",
        "center": (36.1699, -115.1398), "radius_m": 22000,
        "grid": [
            (36.1699, -115.1398),  # Strip/core
            (36.0395, -114.9817),  # Henderson
            (36.1989, -115.2550),  # Summerlin
            (36.2400, -115.1175),  # North LV
            (35.9607, -114.8390),  # Boulder City/lake venues
        ],
    },
    {
        "id": "atlanta", "name": "Atlanta", "state": "GA", "tranche": 2,
        "display": "Atlanta, Georgia",
        "center": (33.7490, -84.3880), "radius_m": 26000,
        "grid": [
            (33.7490, -84.3880),  # ATL core
            (33.9526, -84.5499),  # Marietta/Kennesaw
            (34.0754, -84.2941),  # Alpharetta/Roswell
            (33.9605, -83.9880),  # Lawrenceville/Gwinnett
            (33.5404, -84.5738),  # Fayetteville/south
            (33.7900, -84.1600),  # Stone Mountain/Decatur east
            (34.2367, -84.4908),  # Canton/north GA venue corridor
        ],
    },
    {
        "id": "nashville", "name": "Nashville", "state": "TN", "tranche": 2,
        "display": "Nashville, Tennessee",
        "center": (36.1627, -86.7816), "radius_m": 24000,
        "grid": [
            (36.1627, -86.7816),  # Nashville core
            (35.9251, -86.8689),  # Franklin/Leiper's Fork (venue country)
            (36.0331, -86.7828),  # Brentwood
            (36.3067, -86.6200),  # Hendersonville/Gallatin
            (36.2081, -86.2911),  # Lebanon/Mt. Juliet
            (35.8456, -86.3903),  # Murfreesboro
        ],
    },
    # ---- TRANCHE 3 (wave 2) ----
    {
        "id": "chicago", "name": "Chicago", "state": "IL", "tranche": 3,
        "display": "Chicago, Illinois",
        "center": (41.8781, -87.6298),
        "radius_m": 26000,
        "grid": [
            (41.8781, -87.6298),  # Chicago core/Loop
            (42.0451, -87.6877),  # Evanston/North Shore
            (41.7508, -88.1535),  # Naperville
            (42.0334, -88.0834),  # Schaumburg
            (41.8328, -87.9289),  # Oak Brook/Hinsdale
            (41.6303, -87.8539),  # Orland Park/SW
            (42.2586, -87.8407),  # Lake Forest
            (41.5250, -88.0817),  # Joliet
            (42.1539, -88.1362),  # Barrington
        ],
    },
    {
        "id": "los-angeles", "name": "Los Angeles", "state": "CA", "tranche": 3,
        "display": "Los Angeles, California",
        "center": (34.0522, -118.2437),
        "radius_m": 26000,
        "grid": [
            (34.0522, -118.2437),  # DTLA
            (34.0195, -118.4912),  # Santa Monica/Westside
            (34.1478, -118.1445),  # Pasadena
            (33.7701, -118.1937),  # Long Beach
            (34.1808, -118.3090),  # Burbank/Glendale
            (34.0259, -118.7798),  # Malibu (destination corridor)
            (33.8358, -118.3406),  # Torrance/South Bay
            (34.3917, -118.5426),  # Santa Clarita
            (34.0551, -117.7500),  # Pomona/inland edge
        ],
    },
    {
        "id": "san-diego", "name": "San Diego", "state": "CA", "tranche": 3,
        "display": "San Diego, California",
        "center": (32.7157, -117.1611),
        "radius_m": 24000,
        "grid": [
            (32.7157, -117.1611),  # San Diego core
            (32.8328, -117.2713),  # La Jolla
            (33.1581, -117.3506),  # Carlsbad/North County coast
            (33.1192, -117.0864),  # Escondido
            (32.6401, -117.0842),  # Chula Vista/South Bay
            (33.4936, -117.1484),  # Temecula wine country (destination)
            (32.7948, -116.9625),  # El Cajon/East County
        ],
    },
    {
        "id": "miami", "name": "Miami", "state": "FL", "tranche": 3,
        "display": "Miami, Florida",
        "center": (25.7617, -80.1918),
        "radius_m": 26000,
        "grid": [
            (25.7617, -80.1918),  # Miami core
            (26.1224, -80.1373),  # Fort Lauderdale
            (26.3683, -80.1289),  # Boca Raton
            (26.7153, -80.0534),  # West Palm Beach
            (25.7215, -80.2684),  # Coral Gables
            (26.0112, -80.1495),  # Hollywood
            (25.4687, -80.4776),  # Homestead/Redland venues
        ],
    },
    {
        "id": "orlando", "name": "Orlando", "state": "FL", "tranche": 3,
        "display": "Orlando, Florida",
        "center": (28.5383, -81.3792),
        "radius_m": 24000,
        "grid": [
            (28.5383, -81.3792),  # Orlando core
            (28.2920, -81.4076),  # Kissimmee
            (28.6000, -81.3392),  # Winter Park
            (28.3772, -81.5707),  # Lake Buena Vista/resort corridor
            (28.8029, -81.2695),  # Sanford
            (28.5494, -81.7729),  # Clermont/lakes
        ],
    },
    {
        "id": "tampa", "name": "Tampa", "state": "FL", "tranche": 3,
        "display": "Tampa Bay, Florida",
        "center": (27.9506, -82.4572),
        "radius_m": 24000,
        "grid": [
            (27.9506, -82.4572),  # Tampa core
            (27.7676, -82.6403),  # St. Petersburg
            (27.9659, -82.8001),  # Clearwater/beaches
            (27.3364, -82.5307),  # Sarasota
            (28.0395, -81.9498),  # Lakeland
            (27.9378, -82.2859),  # Brandon
        ],
    },
    {
        "id": "charlotte", "name": "Charlotte", "state": "NC", "tranche": 3,
        "display": "Charlotte, North Carolina",
        "center": (35.2271, -80.8431),
        "radius_m": 24000,
        "grid": [
            (35.2271, -80.8431),  # Charlotte core
            (35.4088, -80.5795),  # Concord
            (35.2621, -81.1873),  # Gastonia
            (34.9249, -81.0251),  # Rock Hill SC
            (35.4107, -80.8428),  # Huntersville/Lake Norman
            (34.9854, -80.5495),  # Monroe
        ],
    },
    {
        "id": "raleigh-durham", "name": "Raleigh-Durham", "state": "NC", "tranche": 3,
        "display": "Raleigh-Durham, North Carolina",
        "center": (35.7796, -78.6382),
        "radius_m": 24000,
        "grid": [
            (35.7796, -78.6382),  # Raleigh
            (35.9940, -78.8986),  # Durham
            (35.9132, -79.0558),  # Chapel Hill
            (35.7915, -78.7811),  # Cary
            (35.9799, -78.5097),  # Wake Forest
            (35.7201, -79.1772),  # Pittsboro/rural venues
        ],
    },
    {
        "id": "seattle", "name": "Seattle", "state": "WA", "tranche": 3,
        "display": "Seattle, Washington",
        "center": (47.6062, -122.3321),
        "radius_m": 25000,
        "grid": [
            (47.6062, -122.3321),  # Seattle core
            (47.6101, -122.2015),  # Bellevue/Eastside
            (47.2529, -122.4443),  # Tacoma
            (47.9790, -122.2021),  # Everett
            (47.7543, -122.1635),  # Woodinville wine country (destination)
            (47.9129, -122.0982),  # Snohomish barn-venue belt
            (47.5301, -122.0326),  # Issaquah
        ],
    },
    {
        "id": "salt-lake-city", "name": "Salt Lake City", "state": "UT", "tranche": 3,
        "display": "Salt Lake City, Utah",
        "center": (40.7608, -111.8910),
        "radius_m": 24000,
        "grid": [
            (40.7608, -111.8910),  # SLC core
            (40.2338, -111.6585),  # Provo/Utah County
            (41.2230, -111.9738),  # Ogden
            (40.6461, -111.4980),  # Park City (destination)
            (40.5649, -111.8389),  # Sandy/Draper
            (40.3916, -111.8508),  # Lehi
        ],
    },
    # ---- TRANCHE 4 (wave 3) ----
    {
        "id": "new-york-city", "name": "New York City", "state": "NY", "tranche": 4,
        "display": "New York City, New York",
        "center": (40.7580, -73.9855),
        "radius_m": 26000,
        "grid": [
            (40.7580, -73.9855),  # Manhattan
            (40.6782, -73.9442),  # Brooklyn
            (40.7282, -73.7949),  # Queens
            (40.7259, -73.5143),  # Nassau/Long Island
            (40.8256, -73.2076),  # Suffolk/Hamptons edge
            (41.0340, -73.7629),  # Westchester
            (40.8259, -74.2090),  # North Jersey (Montclair/Newark)
            (40.2204, -74.0121),  # Jersey Shore (Asbury Park)
            (40.5795, -74.1502),  # Staten Island
            (41.4570, -74.0104),  # Hudson Valley edge (Newburgh)
        ],
    },
    {
        "id": "boston", "name": "Boston", "state": "MA", "tranche": 4,
        "display": "Boston, Massachusetts",
        "center": (42.3601, -71.0589),
        "radius_m": 25000,
        "grid": [
            (42.3601, -71.0589),  # Boston core
            (42.3736, -71.1097),  # Cambridge/Somerville
            (42.5195, -70.8967),  # North Shore (Salem)
            (41.9584, -70.6673),  # South Shore (Plymouth)
            (42.2626, -71.8023),  # Worcester
            (41.7590, -70.4939),  # Cape edge (Sandwich)
            (41.4901, -71.3128),  # Newport RI (destination)
            (42.7654, -71.4676),  # Nashua NH edge
        ],
    },
    {
        "id": "philadelphia", "name": "Philadelphia", "state": "PA", "tranche": 4,
        "display": "Philadelphia, Pennsylvania",
        "center": (39.9526, -75.1652),
        "radius_m": 25000,
        "grid": [
            (39.9526, -75.1652),  # Philadelphia core
            (40.0292, -75.3049),  # Main Line
            (40.3643, -74.9513),  # Bucks County (New Hope)
            (39.9268, -75.0246),  # South Jersey (Cherry Hill)
            (39.7391, -75.5398),  # Wilmington DE
            (40.0893, -75.3963),  # Valley Forge/King of Prussia
            (40.0379, -76.3055),  # Lancaster edge
        ],
    },
    {
        "id": "washington-dc", "name": "Washington DC", "state": "DC", "tranche": 4,
        "display": "Washington, D.C.",
        "center": (38.9072, -77.0369),
        "radius_m": 25000,
        "grid": [
            (38.9072, -77.0369),  # DC core
            (38.8048, -77.0469),  # Arlington/Alexandria
            (39.0840, -77.1528),  # Bethesda/Rockville
            (38.8462, -77.3064),  # Fairfax/Vienna
            (39.1157, -77.5636),  # Leesburg VA wine/barn country (destination)
            (38.9784, -76.4922),  # Annapolis
            (39.4143, -77.4105),  # Frederick MD
        ],
    },
    {
        "id": "san-francisco-bay", "name": "San Francisco Bay", "state": "CA", "tranche": 4,
        "display": "San Francisco Bay Area, California",
        "center": (37.7749, -122.4194),
        "radius_m": 25000,
        "grid": [
            (37.7749, -122.4194),  # San Francisco
            (37.8044, -122.2712),  # Oakland/Berkeley
            (37.3382, -121.8863),  # San Jose
            (37.4419, -122.1430),  # Peninsula (Palo Alto)
            (38.2975, -122.2869),  # Napa (destination)
            (38.4404, -122.7141),  # Sonoma/Santa Rosa (destination)
            (37.4636, -122.4286),  # Half Moon Bay coast
            (37.6819, -121.7680),  # Livermore wine valley
        ],
    },
    {
        "id": "portland", "name": "Portland", "state": "OR", "tranche": 4,
        "display": "Portland, Oregon",
        "center": (45.5152, -122.6784),
        "radius_m": 24000,
        "grid": [
            (45.5152, -122.6784),  # Portland core
            (45.6387, -122.6615),  # Vancouver WA
            (45.5229, -122.9898),  # Hillsboro
            (45.3573, -122.6068),  # Oregon City
            (45.2101, -123.1987),  # Willamette wine country (McMinnville, destination)
            (45.7054, -121.5215),  # Columbia Gorge (Hood River, destination)
        ],
    },
    {
        "id": "minneapolis", "name": "Minneapolis", "state": "MN", "tranche": 4,
        "display": "Minneapolis-St. Paul, Minnesota",
        "center": (44.9778, -93.2650),
        "radius_m": 24000,
        "grid": [
            (44.9778, -93.2650),  # Minneapolis core
            (44.9537, -93.0900),  # St. Paul
            (44.8408, -93.2983),  # Bloomington
            (45.0725, -93.4558),  # Maple Grove/NW
            (45.0566, -92.8088),  # Stillwater (wedding town)
            (44.9033, -93.5661),  # Lake Minnetonka/Excelsior
        ],
    },
    {
        "id": "st-louis", "name": "St. Louis", "state": "MO", "tranche": 4,
        "display": "St. Louis, Missouri",
        "center": (38.6270, -90.1994),
        "radius_m": 24000,
        "grid": [
            (38.6270, -90.1994),  # St. Louis core
            (38.6426, -90.3237),  # Clayton
            (38.7881, -90.4974),  # St. Charles
            (38.6631, -90.5771),  # Chesterfield
            (38.5201, -89.9840),  # Metro East (Belleville IL)
            (38.6534, -90.7890),  # Missouri wine country (Defiance)
        ],
    },
    {
        "id": "kansas-city", "name": "Kansas City", "state": "MO", "tranche": 4,
        "display": "Kansas City, Missouri",
        "center": (39.0997, -94.5786),
        "radius_m": 24000,
        "grid": [
            (39.0997, -94.5786),  # KC core
            (38.9822, -94.6708),  # Overland Park
            (38.9108, -94.3822),  # Lee's Summit
            (39.2461, -94.4191),  # Liberty
            (38.9717, -95.2353),  # Lawrence KS edge
            (39.4111, -94.9019),  # Weston (venue town)
        ],
    },
    {
        "id": "columbus", "name": "Columbus", "state": "OH", "tranche": 4,
        "display": "Columbus, Ohio",
        "center": (39.9612, -82.9988),
        "radius_m": 24000,
        "grid": [
            (39.9612, -82.9988),  # Columbus core
            (40.0992, -83.1141),  # Dublin
            (40.1262, -82.9291),  # Westerville
            (39.8814, -83.0930),  # Grove City
            (40.0681, -82.5196),  # Granville/Newark
            (40.2987, -83.0680),  # Delaware OH
        ],
    },
    {
        "id": "new-orleans", "name": "New Orleans", "state": "LA", "tranche": 4,
        "display": "New Orleans, Louisiana",
        "center": (29.9511, -90.0715),
        "radius_m": 24000,
        "grid": [
            (29.9511, -90.0715),  # French Quarter/core (destination capital)
            (29.9841, -90.1529),  # Metairie
            (30.4755, -90.1009),  # Northshore (Covington)
            (30.2752, -89.7812),  # Slidell
            (30.0002, -90.7057),  # River Road plantation corridor (destination)
        ],
    },
    {
        "id": "indianapolis", "name": "Indianapolis", "state": "IN", "tranche": 4,
        "display": "Indianapolis, Indiana",
        "center": (39.7684, -86.1581),
        "radius_m": 24000,
        "grid": [
            (39.7684, -86.1581),  # Indy core
            (39.9784, -86.1180),  # Carmel
            (39.9568, -86.0134),  # Fishers/Noblesville
            (39.6137, -86.1067),  # Greenwood
            (39.9509, -86.2619),  # Zionsville
            (39.7042, -86.3994),  # Avon/Plainfield
        ],
    },


    {
        "id": "sacramento", "name": "Sacramento", "state": "CA", "tranche": 5,
        "display": "Sacramento, California",
        "center": (38.5816, -121.4944), "radius_m": 24000,
        "grid": [
            (38.5816, -121.4944),  # Sacramento core
            (38.7521, -121.2880),  # Roseville/Rocklin
            (38.6668, -121.1461),  # Folsom/El Dorado Hills
            (38.7296, -120.7985),  # Apple Hill/Placerville venue belt
            (38.3488, -121.9670),  # Vacaville/Winters barns
            (39.0968, -120.0324),  # Tahoe edge (destination)
        ],
    },
    {
        "id": "jacksonville", "name": "Jacksonville", "state": "FL", "tranche": 5,
        "display": "Jacksonville, Florida",
        "center": (30.3322, -81.6557), "radius_m": 24000,
        "grid": [
            (30.3322, -81.6557),  # Jax core
            (30.2946, -81.3931),  # Jax Beach/Ponte Vedra
            (29.8946, -81.3145),  # St. Augustine (destination)
            (30.6697, -81.4626),  # Amelia Island (destination)
            (30.1588, -81.7787),  # Orange Park
        ],
    },
    {
        "id": "charleston", "name": "Charleston", "state": "SC", "tranche": 5,
        "display": "Charleston, South Carolina",
        "center": (32.7765, -79.9311), "radius_m": 24000,
        "grid": [
            (32.7765, -79.9311),  # Historic District (destination capital)
            (32.8323, -79.8284),  # Mount Pleasant
            (32.6913, -80.0620),  # Johns Island/plantation belt
            (32.7935, -80.0521),  # West Ashley plantations
            (33.6891, -78.8867),  # Myrtle Beach (destination)
            (32.4316, -80.6698),  # Beaufort/Sea Islands
        ],
    },
    {
        "id": "savannah", "name": "Savannah", "state": "GA", "tranche": 5,
        "display": "Savannah, Georgia",
        "center": (32.0809, -81.0912), "radius_m": 23000,
        "grid": [
            (32.0809, -81.0912),  # Historic District (destination capital)
            (32.0186, -80.8434),  # Tybee Island
            (31.9905, -81.2354),  # Richmond Hill
            (32.2163, -80.7526),  # Hilton Head SC (destination)
            (31.1499, -81.4915),  # Golden Isles/Jekyll (destination)
        ],
    },
    {
        "id": "detroit", "name": "Detroit", "state": "MI", "tranche": 5,
        "display": "Detroit, Michigan",
        "center": (42.3314, -83.0458), "radius_m": 25000,
        "grid": [
            (42.3314, -83.0458),  # Detroit core
            (42.4895, -83.1446),  # Royal Oak/Birmingham
            (42.5803, -83.0302),  # Rochester/Troy
            (42.2808, -83.7430),  # Ann Arbor
            (42.6875, -83.2341),  # Clarkston lake venues
            (42.0334, -83.0166),  # Downriver/Monroe barns
        ],
    },
    {
        "id": "pittsburgh", "name": "Pittsburgh", "state": "PA", "tranche": 5,
        "display": "Pittsburgh, Pennsylvania",
        "center": (40.4406, -79.9959), "radius_m": 24000,
        "grid": [
            (40.4406, -79.9959),  # Downtown/Strip
            (40.5513, -80.0180),  # North Hills
            (40.3573, -80.1103),  # South Hills
            (40.6162, -79.7331),  # Allegheny Valley barns
            (40.2884, -79.5839),  # Laurel Highlands venue belt
        ],
    },
    {
        "id": "cincinnati", "name": "Cincinnati", "state": "OH", "tranche": 5,
        "display": "Cincinnati, Ohio",
        "center": (39.1031, -84.5120), "radius_m": 24000,
        "grid": [
            (39.1031, -84.5120),  # OTR/Downtown
            (39.2145, -84.5495),  # North suburbs
            (39.0826, -84.5087),  # Covington/Newport KY
            (39.2450, -84.2633),  # Loveland/Milford barns
            (38.9530, -84.6483),  # Florence KY edge
        ],
    },
    {
        "id": "cleveland", "name": "Cleveland", "state": "OH", "tranche": 5,
        "display": "Cleveland, Ohio",
        "center": (41.4993, -81.6944), "radius_m": 24000,
        "grid": [
            (41.4993, -81.6944),  # Downtown/Flats
            (41.4820, -81.8004),  # Lakewood/West
            (41.5200, -81.5568),  # Cleveland Heights/East
            (41.3183, -81.4456),  # Cuyahoga Valley venues
            (41.2407, -82.6157),  # Sandusky/Cedar Point coast
        ],
    },
    {
        "id": "milwaukee", "name": "Milwaukee", "state": "WI", "tranche": 5,
        "display": "Milwaukee, Wisconsin",
        "center": (43.0389, -87.9065), "radius_m": 24000,
        "grid": [
            (43.0389, -87.9065),  # Third Ward/Downtown
            (43.0642, -88.1070),  # Waukesha/Lake Country
            (42.9975, -88.0450),  # West Allis
            (43.3172, -88.0126),  # Cedarburg (venue town)
            (42.7261, -87.7829),  # Racine/Kenosha edge
        ],
    },
    {
        "id": "richmond", "name": "Richmond", "state": "VA", "tranche": 5,
        "display": "Richmond, Virginia",
        "center": (37.5407, -77.4360), "radius_m": 24000,
        "grid": [
            (37.5407, -77.4360),  # Richmond core
            (37.6432, -77.5636),  # Glen Allen/Short Pump
            (37.3771, -77.5050),  # Chester/plantation river road
            (38.0293, -78.4767),  # Charlottesville wine country (destination)
            (37.2707, -76.7075),  # Williamsburg (destination)
        ],
    },
    {
        "id": "virginia-beach", "name": "Virginia Beach", "state": "VA", "tranche": 5,
        "display": "Virginia Beach, Virginia",
        "center": (36.8529, -75.9780), "radius_m": 24000,
        "grid": [
            (36.8529, -75.9780),  # Oceanfront
            (36.8468, -76.2852),  # Norfolk
            (36.7682, -76.2875),  # Chesapeake
            (37.0299, -76.3452),  # Hampton/Newport News
            (36.0946, -75.7118),  # Outer Banks NC edge (destination)
        ],
    },
    {
        "id": "louisville", "name": "Louisville", "state": "KY", "tranche": 5,
        "display": "Louisville, Kentucky",
        "center": (38.2527, -85.7585), "radius_m": 24000,
        "grid": [
            (38.2527, -85.7585),  # NuLu/Downtown
            (38.2735, -85.5741),  # East End/Middletown
            (38.1867, -85.7645),  # South/Churchill Downs
            (38.3396, -85.4569),  # Oldham County horse farms
            (37.9975, -85.7016),  # Bardstown bourbon belt (venue draw)
        ],
    },
    {
        "id": "memphis", "name": "Memphis", "state": "TN", "tranche": 5,
        "display": "Memphis, Tennessee",
        "center": (35.1495, -90.0490), "radius_m": 23000,
        "grid": [
            (35.1495, -90.0490),  # Downtown/Beale
            (35.1174, -89.9711),  # Midtown
            (35.2035, -89.7325),  # Lakeland/Arlington barns
            (34.9887, -89.9979),  # Southaven MS edge
            (35.0456, -89.6773),  # Collierville
        ],
    },
    {
        "id": "tucson", "name": "Tucson", "state": "AZ", "tranche": 5,
        "display": "Tucson, Arizona",
        "center": (32.2226, -110.9747), "radius_m": 24000,
        "grid": [
            (32.2226, -110.9747),  # Tucson core
            (32.3407, -111.0431),  # Oro Valley/Catalina foothills
            (32.1543, -110.7801),  # Saguaro East/Tanque Verde ranches
            (31.9573, -110.9823),  # Green Valley
            (32.4064, -110.9080),  # Catalina/SaddleBrooke
        ],
    },
    {
        "id": "inland-empire", "name": "Inland Empire", "state": "CA", "tranche": 6,
        "display": "Riverside-San Bernardino, California",
        "center": (33.9533, -117.3962), "radius_m": 24000,
        "grid": [
            (33.9533, -117.3962),  # Riverside core
            (34.1083, -117.2898),  # San Bernardino
            (34.0633, -117.6509),  # Ontario/Chino
            (34.1064, -117.5931),  # Rancho Cucamonga
            (33.8753, -117.5664),  # Corona
            (34.0556, -117.1825),  # Redlands
            (33.4936, -117.1484),  # Temecula wine country
            (33.7476, -116.9719),  # Hemet/San Jacinto
            (34.5362, -117.2928),  # Victorville/high desert
        ],
    },
    {
        "id": "baltimore", "name": "Baltimore", "state": "MD", "tranche": 6,
        "display": "Baltimore, Maryland",
        "center": (39.2904, -76.6122), "radius_m": 24000,
        "grid": [
            (39.2904, -76.6122),   # Inner Harbor/downtown
            (39.4015, -76.6019),   # Towson
            (39.2037, -76.8610),   # Columbia
            (38.9784, -76.4922),   # Annapolis waterfront
            (39.2673, -76.7983),   # Ellicott City
            (39.5359, -76.3483),   # Bel Air
            (39.5754, -76.9958),   # Westminster/Carroll County barns
        ],
    },
    {
        "id": "orange-county", "name": "Orange County", "state": "CA", "tranche": 6,
        "display": "Orange County, California",
        "center": (33.7175, -117.8311), "radius_m": 20000,
        "grid": [
            (33.6846, -117.8265),  # Irvine
            (33.8366, -117.9143),  # Anaheim
            (33.6189, -117.9298),  # Newport Beach
            (33.5427, -117.7854),  # Laguna Beach
            (33.6603, -117.9992),  # Huntington Beach
            (33.5017, -117.6625),  # San Juan Capistrano
            (33.8704, -117.9242),  # Fullerton
        ],
    },
    {
        "id": "providence", "name": "Providence", "state": "RI", "tranche": 6,
        "display": "Providence and Newport, Rhode Island",
        "center": (41.8240, -71.4128), "radius_m": 24000,
        "grid": [
            (41.8240, -71.4128),   # Providence core
            (41.4901, -71.3128),   # Newport mansions
            (41.7001, -71.4162),   # Warwick
            (41.7015, -71.1550),   # Fall River MA edge
            (41.4501, -71.4495),   # Narragansett
            (42.0029, -71.5148),   # Woonsocket
        ],
    },
    {
        "id": "hartford-new-haven", "name": "Hartford-New Haven", "state": "CT", "tranche": 6,
        "display": "Hartford and New Haven, Connecticut",
        "center": (41.6032, -72.7290), "radius_m": 24000,
        "grid": [
            (41.7658, -72.6734),   # Hartford
            (41.3083, -72.9279),   # New Haven
            (41.5582, -73.0515),   # Waterbury
            (41.5623, -72.6506),   # Middletown
            (41.7470, -73.1893),   # Litchfield Hills
            (41.3543, -71.9665),   # Mystic/shoreline
        ],
    },
    {
        "id": "oklahoma-city", "name": "Oklahoma City", "state": "OK", "tranche": 6,
        "display": "Oklahoma City, Oklahoma",
        "center": (35.4676, -97.5164), "radius_m": 24000,
        "grid": [
            (35.4676, -97.5164),   # OKC core
            (35.6528, -97.4781),   # Edmond
            (35.2226, -97.4395),   # Norman
            (35.3395, -97.4867),   # Moore
            (35.5067, -97.7625),   # Yukon/Mustang
            (35.8789, -97.4253),   # Guthrie
        ],
    },
    {
        "id": "buffalo", "name": "Buffalo", "state": "NY", "tranche": 6,
        "display": "Buffalo and Niagara, New York",
        "center": (42.8864, -78.8784), "radius_m": 24000,
        "grid": [
            (42.8864, -78.8784),   # Buffalo core
            (43.0962, -79.0377),   # Niagara Falls
            (42.9784, -78.7998),   # Amherst/Williamsville
            (42.7676, -78.7439),   # Orchard Park
            (42.7681, -78.6136),   # East Aurora
            (43.1706, -78.6903),   # Lockport
        ],
    },
    {
        "id": "birmingham", "name": "Birmingham", "state": "AL", "tranche": 6,
        "display": "Birmingham, Alabama",
        "center": (33.5186, -86.8104), "radius_m": 24000,
        "grid": [
            (33.5186, -86.8104),   # Birmingham core
            (33.4054, -86.8114),   # Hoover
            (33.4488, -86.7877),   # Vestavia Hills
            (33.6198, -86.6089),   # Trussville
            (33.4018, -86.9544),   # Bessemer
            (33.2098, -87.5692),   # Tuscaloosa
        ],
    },
    {
        "id": "grand-rapids", "name": "Grand Rapids", "state": "MI", "tranche": 6,
        "display": "Grand Rapids, Michigan",
        "center": (42.9634, -85.6681), "radius_m": 24000,
        "grid": [
            (42.9634, -85.6681),   # Grand Rapids core
            (42.7875, -86.1089),   # Holland
            (43.0631, -86.2284),   # Grand Haven lakeshore
            (42.6547, -86.2006),   # Saugatuck
            (43.1203, -85.5600),   # Rockford
            (42.2917, -85.5872),   # Kalamazoo
        ],
    },
    {
        "id": "santa-barbara", "name": "Santa Barbara", "state": "CA", "tranche": 6,
        "display": "Santa Barbara and the Santa Ynez Valley, California",
        "center": (34.4208, -119.6982), "radius_m": 24000,
        "grid": [
            (34.4208, -119.6982),  # Santa Barbara
            (34.4367, -119.6321),  # Montecito
            (34.5958, -120.1376),  # Solvang
            (34.6142, -120.0799),  # Santa Ynez wine country
            (34.2746, -119.2290),  # Ventura
            (34.4480, -119.2429),  # Ojai
        ],
    },
    {
        "id": "palm-springs", "name": "Palm Springs", "state": "CA", "tranche": 6,
        "display": "Palm Springs and the Coachella Valley, California",
        "center": (33.8303, -116.5453), "radius_m": 20000,
        "grid": [
            (33.8303, -116.5453),  # Palm Springs
            (33.7222, -116.3745),  # Palm Desert
            (33.6634, -116.3100),  # La Quinta
            (33.7397, -116.4128),  # Rancho Mirage
            (33.7206, -116.2156),  # Indio
            (34.1347, -116.3131),  # Joshua Tree
        ],
    },
    {
        "id": "asheville", "name": "Asheville", "state": "NC", "tranche": 6,
        "display": "Asheville and the Blue Ridge, North Carolina",
        "center": (35.5951, -82.5515), "radius_m": 24000,
        "grid": [
            (35.5951, -82.5515),   # Asheville core
            (35.3187, -82.4609),   # Hendersonville
            (35.6180, -82.3215),   # Black Mountain
            (35.4887, -82.9887),   # Waynesville
            (35.2334, -82.7343),   # Brevard
            (36.2168, -81.6746),   # Boone/high country
        ],
    },
    {
        "id": "honolulu", "name": "Honolulu", "state": "HI", "tranche": 6,
        "display": "Honolulu and Oahu, Hawaii",
        "center": (21.3099, -157.8581), "radius_m": 20000,
        "grid": [
            (21.3099, -157.8581),  # Honolulu core
            (21.2793, -157.8294),  # Waikiki
            (21.3369, -158.1220),  # Ko Olina
            (21.4022, -157.7394),  # Kailua
            (21.5928, -158.1033),  # Haleiwa/North Shore
            (21.4181, -157.8036),  # Kaneohe
        ],
    },

    # ---- tranche 7 (2026-09-21): nationwide fill, 50 metros. See add_metros7.py notes in README.
    {
        "id": 'rochester', "name": 'Rochester', "state": 'NY', "tranche": 7,
        "display": 'Rochester and the Finger Lakes, New York',
        "center": (43.1566, -77.6088), "radius_m": 22000,
        "grid": [
            (43.1566, -77.6088),  # Rochester core
            (43.0906, -77.5150),  # Pittsford
            (43.2123, -77.4300),  # Webster
            (42.8875, -77.2819),  # Canandaigua
            (43.1867, -77.8036),  # Spencerport/Brockport
            (42.9825, -77.4089),  # Victor
        ],
    },
    {
        "id": 'albany', "name": 'Albany', "state": 'NY', "tranche": 7,
        "display": 'Albany and Saratoga, New York',
        "center": (42.6526, -73.7562), "radius_m": 22000,
        "grid": [
            (42.6526, -73.7562),  # Albany core
            (43.0831, -73.7846),  # Saratoga Springs
            (42.7284, -73.6918),  # Troy
            (42.8142, -73.9396),  # Schenectady
            (42.8620, -73.7770),  # Clifton Park
            (43.4262, -73.7123),  # Lake George
        ],
    },
    {
        "id": 'syracuse', "name": 'Syracuse', "state": 'NY', "tranche": 7,
        "display": 'Syracuse, New York',
        "center": (43.0481, -76.1474), "radius_m": 22000,
        "grid": [
            (43.0481, -76.1474),  # Syracuse core
            (42.9470, -76.4291),  # Skaneateles
            (42.9317, -76.5661),  # Auburn
            (43.1587, -76.3327),  # Baldwinsville
            (43.0298, -76.0044),  # Fayetteville/Manlius
            (43.4553, -76.5105),  # Oswego
        ],
    },
    {
        "id": 'lehigh-valley', "name": 'Lehigh Valley', "state": 'PA', "tranche": 7,
        "display": 'Lehigh Valley: Allentown, Bethlehem and Easton, Pennsylvania',
        "center": (40.6084, -75.4902), "radius_m": 20000,
        "grid": [
            (40.6084, -75.4902),  # Allentown
            (40.6259, -75.3705),  # Bethlehem
            (40.6884, -75.2207),  # Easton
            (40.5393, -75.4966),  # Emmaus
            (40.5173, -75.7774),  # Kutztown
            (40.4418, -75.3416),  # Quakertown
        ],
    },
    {
        "id": 'tulsa', "name": 'Tulsa', "state": 'OK', "tranche": 7,
        "display": 'Tulsa, Oklahoma',
        "center": (36.1540, -95.9928), "radius_m": 22000,
        "grid": [
            (36.1540, -95.9928),  # Tulsa core
            (36.0526, -95.7909),  # Broken Arrow
            (36.2695, -95.8547),  # Owasso
            (36.0229, -95.9683),  # Jenks/Bixby
            (36.1398, -96.1089),  # Sand Springs
            (36.3126, -95.6161),  # Claremore
        ],
    },
    {
        "id": 'omaha', "name": 'Omaha', "state": 'NE', "tranche": 7,
        "display": 'Omaha and Lincoln, Nebraska',
        "center": (41.2565, -95.9345), "radius_m": 24000,
        "grid": [
            (41.2565, -95.9345),  # Omaha core
            (41.2619, -95.8608),  # Council Bluffs
            (41.1544, -96.0422),  # Papillion/Bellevue
            (41.2864, -96.2378),  # Elkhorn
            (41.1408, -96.2394),  # Gretna
            (40.8136, -96.7026),  # Lincoln
        ],
    },
    {
        "id": 'albuquerque', "name": 'Albuquerque', "state": 'NM', "tranche": 7,
        "display": 'Albuquerque and Santa Fe, New Mexico',
        "center": (35.0844, -106.6504), "radius_m": 24000,
        "grid": [
            (35.0844, -106.6504),  # Albuquerque core
            (35.2328, -106.6630),  # Rio Rancho
            (35.2378, -106.6067),  # Corrales
            (35.6870, -105.9378),  # Santa Fe
            (34.8062, -106.7334),  # Los Lunas
            (35.3000, -106.5500),  # Bernalillo/Placitas
        ],
    },
    {
        "id": 'el-paso', "name": 'El Paso', "state": 'TX', "tranche": 7,
        "display": 'El Paso, Texas and Las Cruces',
        "center": (31.7619, -106.4850), "radius_m": 24000,
        "grid": [
            (31.7619, -106.4850),  # El Paso core
            (31.7500, -106.3000),  # East El Paso
            (31.9000, -106.4300),  # Northeast El Paso
            (31.8700, -106.5900),  # Upper Valley
            (31.6928, -106.2069),  # Horizon City
            (32.3199, -106.7637),  # Las Cruces
        ],
    },
    {
        "id": 'fresno', "name": 'Fresno', "state": 'CA', "tranche": 7,
        "display": 'Fresno and the Central Valley, California',
        "center": (36.7378, -119.7871), "radius_m": 24000,
        "grid": [
            (36.7378, -119.7871),  # Fresno core
            (36.8252, -119.7029),  # Clovis
            (36.3302, -119.2921),  # Visalia
            (36.9613, -120.0607),  # Madera
            (36.3275, -119.6457),  # Hanford
            (36.7080, -119.5560),  # Sanger/Reedley
        ],
    },
    {
        "id": 'bakersfield', "name": 'Bakersfield', "state": 'CA', "tranche": 7,
        "display": 'Bakersfield, California',
        "center": (35.3733, -119.0187), "radius_m": 22000,
        "grid": [
            (35.3733, -119.0187),  # Bakersfield core
            (35.4100, -119.1100),  # Northwest Bakersfield
            (35.3200, -119.0900),  # Southwest Bakersfield
            (35.1322, -118.4490),  # Tehachapi
            (35.5005, -119.2718),  # Shafter
        ],
    },
    {
        "id": 'colorado-springs', "name": 'Colorado Springs', "state": 'CO', "tranche": 7,
        "display": 'Colorado Springs and Pueblo, Colorado',
        "center": (38.8339, -104.8214), "radius_m": 24000,
        "grid": [
            (38.8339, -104.8214),  # Colorado Springs core
            (39.0917, -104.8725),  # Monument
            (38.8597, -104.9172),  # Manitou Springs
            (38.6822, -104.7008),  # Fountain
            (38.2544, -104.6091),  # Pueblo
            (38.9939, -105.0569),  # Woodland Park
        ],
    },
    {
        "id": 'boise', "name": 'Boise', "state": 'ID', "tranche": 7,
        "display": 'Boise and the Treasure Valley, Idaho',
        "center": (43.6150, -116.2023), "radius_m": 24000,
        "grid": [
            (43.6150, -116.2023),  # Boise core
            (43.6121, -116.3915),  # Meridian
            (43.5407, -116.5635),  # Nampa
            (43.6955, -116.3540),  # Eagle
            (43.6629, -116.6874),  # Caldwell
            (43.6807, -114.3637),  # Sun Valley/Ketchum
        ],
    },
    {
        "id": 'des-moines', "name": 'Des Moines', "state": 'IA', "tranche": 7,
        "display": 'Des Moines, Iowa',
        "center": (41.5868, -93.6250), "radius_m": 22000,
        "grid": [
            (41.5868, -93.6250),  # Des Moines core
            (41.5772, -93.7113),  # West Des Moines
            (41.7318, -93.6001),  # Ankeny
            (42.0308, -93.6319),  # Ames
            (41.6444, -93.4647),  # Altoona
            (41.3581, -93.5574),  # Indianola
        ],
    },
    {
        "id": 'madison', "name": 'Madison', "state": 'WI', "tranche": 7,
        "display": 'Madison and the Dells, Wisconsin',
        "center": (43.0731, -89.4012), "radius_m": 22000,
        "grid": [
            (43.0731, -89.4012),  # Madison core
            (43.0972, -89.5043),  # Middleton
            (43.1836, -89.2137),  # Sun Prairie
            (42.9908, -89.5332),  # Verona/Fitchburg
            (43.6275, -89.7710),  # Wisconsin Dells
            (42.9170, -89.2179),  # Stoughton
        ],
    },
    {
        "id": 'knoxville', "name": 'Knoxville', "state": 'TN', "tranche": 7,
        "display": 'Knoxville, Tennessee',
        "center": (35.9606, -83.9207), "radius_m": 22000,
        "grid": [
            (35.9606, -83.9207),  # Knoxville core
            (35.8848, -84.1544),  # Farragut
            (35.7565, -83.9705),  # Maryville
            (36.0104, -84.2696),  # Oak Ridge
            (36.0334, -84.0308),  # Powell
            (35.7973, -84.2591),  # Lenoir City
        ],
    },
    {
        "id": 'greenville-sc', "name": 'Greenville', "state": 'SC', "tranche": 7,
        "display": 'Greenville and Spartanburg, South Carolina',
        "center": (34.8526, -82.3940), "radius_m": 22000,
        "grid": [
            (34.8526, -82.3940),  # Greenville core
            (34.9496, -81.9320),  # Spartanburg
            (34.5034, -82.6501),  # Anderson
            (34.9676, -82.4432),  # Travelers Rest
            (34.7371, -82.2543),  # Simpsonville
            (34.8298, -82.6015),  # Easley
        ],
    },
    {
        "id": 'columbia-sc', "name": 'Columbia', "state": 'SC', "tranche": 7,
        "display": 'Columbia, South Carolina',
        "center": (34.0007, -81.0348), "radius_m": 22000,
        "grid": [
            (34.0007, -81.0348),  # Columbia core
            (33.9815, -81.2362),  # Lexington
            (34.0859, -81.1832),  # Irmo
            (34.2143, -80.9740),  # Blythewood
            (34.2465, -80.6070),  # Camden
        ],
    },
    {
        "id": 'baton-rouge', "name": 'Baton Rouge', "state": 'LA', "tranche": 7,
        "display": 'Baton Rouge and Lafayette, Louisiana',
        "center": (30.4515, -91.1871), "radius_m": 24000,
        "grid": [
            (30.4515, -91.1871),  # Baton Rouge core
            (30.2380, -90.9201),  # Prairieville/Gonzales
            (30.4874, -90.9559),  # Denham Springs
            (30.6485, -91.1565),  # Zachary
            (30.7799, -91.3762),  # St. Francisville
            (30.2241, -92.0198),  # Lafayette
        ],
    },
    {
        "id": 'dayton', "name": 'Dayton', "state": 'OH', "tranche": 7,
        "display": 'Dayton and Springfield, Ohio',
        "center": (39.7589, -84.1916), "radius_m": 22000,
        "grid": [
            (39.7589, -84.1916),  # Dayton core
            (39.9242, -83.8088),  # Springfield
            (39.6284, -84.1594),  # Kettering/Centerville
            (39.7092, -84.0633),  # Beavercreek
            (40.0395, -84.2033),  # Troy/Tipp City
            (39.6428, -84.2866),  # Miamisburg
        ],
    },
    {
        "id": 'toledo', "name": 'Toledo', "state": 'OH', "tranche": 7,
        "display": 'Toledo, Ohio',
        "center": (41.6528, -83.5379), "radius_m": 22000,
        "grid": [
            (41.6528, -83.5379),  # Toledo core
            (41.5570, -83.6271),  # Perrysburg
            (41.7189, -83.7130),  # Sylvania
            (41.5628, -83.6538),  # Maumee
            (41.3748, -83.6513),  # Bowling Green
            (41.0442, -83.6499),  # Findlay
        ],
    },
    {
        "id": 'fort-myers-naples', "name": 'Fort Myers', "state": 'FL', "tranche": 7,
        "display": 'Fort Myers, Naples and the Gulf Coast, Florida',
        "center": (26.6406, -81.8723), "radius_m": 22000,
        "grid": [
            (26.6406, -81.8723),  # Fort Myers core
            (26.1420, -81.7948),  # Naples
            (26.5629, -81.9495),  # Cape Coral
            (26.3398, -81.7787),  # Bonita Springs/Estero
            (26.4489, -82.0227),  # Sanibel/Captiva
            (26.9298, -82.0454),  # Punta Gorda
        ],
    },
    {
        "id": 'sarasota', "name": 'Sarasota', "state": 'FL', "tranche": 7,
        "display": 'Sarasota and Bradenton, Florida',
        "center": (27.3364, -82.5307), "radius_m": 20000,
        "grid": [
            (27.3364, -82.5307),  # Sarasota core
            (27.4989, -82.5748),  # Bradenton
            (27.0998, -82.4543),  # Venice
            (27.4200, -82.4300),  # Lakewood Ranch
            (27.4127, -82.6592),  # Anna Maria/Longboat Key
            (27.2672, -82.5464),  # Siesta Key
        ],
    },
    {
        "id": 'daytona-beach', "name": 'Daytona Beach', "state": 'FL', "tranche": 7,
        "display": 'Daytona Beach and St. Augustine, Florida',
        "center": (29.2108, -81.0228), "radius_m": 22000,
        "grid": [
            (29.2108, -81.0228),  # Daytona Beach core
            (29.2858, -81.0559),  # Ormond Beach
            (29.0258, -80.9270),  # New Smyrna Beach
            (29.1383, -80.9956),  # Port Orange
            (29.9012, -81.3124),  # St. Augustine
            (29.0283, -81.3031),  # DeLand
        ],
    },
    {
        "id": 'key-west', "name": 'Key West', "state": 'FL', "tranche": 7,
        "display": 'Key West and the Florida Keys',
        "center": (24.5551, -81.7800), "radius_m": 20000,
        "grid": [
            (24.5551, -81.7800),  # Key West
            (24.7136, -81.0906),  # Marathon
            (24.9243, -80.6278),  # Islamorada
            (25.0865, -80.4473),  # Key Largo
            (24.6698, -81.3535),  # Big Pine Key
        ],
    },
    {
        "id": 'greensboro', "name": 'Greensboro', "state": 'NC', "tranche": 7,
        "display": 'Greensboro, Winston-Salem and High Point, North Carolina',
        "center": (36.0726, -79.7920), "radius_m": 22000,
        "grid": [
            (36.0726, -79.7920),  # Greensboro core
            (36.0999, -80.2442),  # Winston-Salem
            (35.9557, -80.0053),  # High Point
            (36.0957, -79.4378),  # Burlington
            (36.1199, -80.0737),  # Kernersville
            (35.7079, -79.8136),  # Asheboro
        ],
    },
    {
        "id": 'wilmington-nc', "name": 'Wilmington', "state": 'NC', "tranche": 7,
        "display": 'Wilmington and the Cape Fear Coast, North Carolina',
        "center": (34.2257, -77.9447), "radius_m": 20000,
        "grid": [
            (34.2257, -77.9447),  # Wilmington core
            (34.2085, -77.7964),  # Wrightsville Beach
            (34.0352, -77.8936),  # Carolina Beach
            (34.2563, -78.0447),  # Leland
            (33.9216, -78.0203),  # Southport/Oak Island
        ],
    },
    {
        "id": 'outer-banks', "name": 'Outer Banks', "state": 'NC', "tranche": 7,
        "display": 'The Outer Banks, North Carolina',
        "center": (36.0307, -75.6760), "radius_m": 20000,
        "grid": [
            (36.0307, -75.6760),  # Kill Devil Hills
            (35.9573, -75.6240),  # Nags Head
            (35.9082, -75.6757),  # Manteo
            (36.1690, -75.7549),  # Duck/Corolla
            (35.3521, -75.5058),  # Hatteras Island
        ],
    },
    {
        "id": 'napa-sonoma', "name": 'Napa', "state": 'CA', "tranche": 7,
        "display": 'Napa and Sonoma Wine Country, California',
        "center": (38.2975, -122.2869), "radius_m": 20000,
        "grid": [
            (38.2975, -122.2869),  # Napa
            (38.5052, -122.4697),  # St. Helena
            (38.5788, -122.5797),  # Calistoga
            (38.2919, -122.4580),  # Sonoma
            (38.6105, -122.8692),  # Healdsburg
            (38.4404, -122.7141),  # Santa Rosa
            (38.4016, -122.3608),  # Yountville
        ],
    },
    {
        "id": 'lake-tahoe-reno', "name": 'Lake Tahoe', "state": 'NV', "tranche": 7,
        "display": 'Lake Tahoe and Reno, Nevada and California',
        "center": (38.9399, -119.9772), "radius_m": 22000,
        "grid": [
            (38.9399, -119.9772),  # South Lake Tahoe
            (39.5296, -119.8138),  # Reno
            (39.2513, -119.9729),  # Incline Village
            (39.1677, -120.1452),  # Tahoe City
            (39.3280, -120.1833),  # Truckee
            (39.1638, -119.7674),  # Carson City
            (39.5349, -119.7527),  # Sparks
        ],
    },
    {
        "id": 'maui', "name": 'Maui', "state": 'HI', "tranche": 7,
        "display": 'Maui, Hawaii',
        "center": (20.8893, -156.4729), "radius_m": 20000,
        "grid": [
            (20.8893, -156.4729),  # Kahului
            (20.6903, -156.4419),  # Wailea/Kihei
            (20.8783, -156.6825),  # Lahaina/Kaanapali
            (20.9155, -156.3777),  # Paia/Haiku
            (20.9995, -156.6670),  # Kapalua
            (20.8570, -156.3131),  # Makawao/Upcountry
        ],
    },
    {
        "id": 'sedona', "name": 'Sedona', "state": 'AZ', "tranche": 7,
        "display": 'Sedona and Flagstaff, Arizona',
        "center": (34.8697, -111.7610), "radius_m": 22000,
        "grid": [
            (34.8697, -111.7610),  # Sedona
            (34.7808, -111.7625),  # Village of Oak Creek
            (34.7391, -112.0099),  # Cottonwood
            (35.1983, -111.6513),  # Flagstaff
            (34.5636, -111.8543),  # Camp Verde
            (34.5400, -112.4685),  # Prescott
        ],
    },
    {
        "id": 'monterey-big-sur', "name": 'Monterey', "state": 'CA', "tranche": 7,
        "display": 'Monterey, Carmel and Big Sur, California',
        "center": (36.6002, -121.8947), "radius_m": 20000,
        "grid": [
            (36.6002, -121.8947),  # Monterey
            (36.5552, -121.9233),  # Carmel
            (36.2704, -121.8081),  # Big Sur
            (36.6177, -121.9166),  # Pacific Grove
            (36.6777, -121.6555),  # Salinas
            (36.9741, -122.0308),  # Santa Cruz
        ],
    },
    {
        "id": 'aspen-vail', "name": 'Aspen', "state": 'CO', "tranche": 7,
        "display": 'Aspen, Vail and the Colorado Rockies',
        "center": (39.1911, -106.8175), "radius_m": 22000,
        "grid": [
            (39.1911, -106.8175),  # Aspen
            (39.6403, -106.3742),  # Vail
            (39.4817, -106.0384),  # Breckenridge
            (40.4850, -106.8317),  # Steamboat Springs
            (39.5505, -107.3248),  # Glenwood Springs
            (38.8697, -106.9878),  # Crested Butte
        ],
    },
    {
        "id": 'jackson-hole', "name": 'Jackson Hole', "state": 'WY', "tranche": 7,
        "display": 'Jackson Hole and the Tetons, Wyoming',
        "center": (43.4799, -110.7624), "radius_m": 20000,
        "grid": [
            (43.4799, -110.7624),  # Jackson
            (43.5875, -110.8277),  # Teton Village
            (43.5008, -110.8752),  # Wilson
            (43.7232, -111.1113),  # Driggs/Victor
            (43.1799, -111.0197),  # Alpine
        ],
    },
    {
        "id": 'cape-cod', "name": 'Cape Cod', "state": 'MA', "tranche": 7,
        "display": "Cape Cod, Nantucket and Martha's Vineyard, Massachusetts",
        "center": (41.6525, -70.2881), "radius_m": 20000,
        "grid": [
            (41.6525, -70.2881),  # Hyannis
            (41.5515, -70.6148),  # Falmouth
            (41.6821, -69.9597),  # Chatham
            (42.0584, -70.1787),  # Provincetown
            (41.2835, -70.0995),  # Nantucket
            (41.3890, -70.5134),  # Martha's Vineyard
            (41.9584, -70.6673),  # Plymouth
        ],
    },
    {
        "id": 'hudson-valley', "name": 'Hudson Valley', "state": 'NY', "tranche": 7,
        "display": 'The Hudson Valley and Catskills, New York',
        "center": (41.7004, -73.9210), "radius_m": 20000,
        "grid": [
            (41.7004, -73.9210),  # Poughkeepsie
            (41.9268, -73.9129),  # Rhinebeck
            (41.7476, -74.0868),  # New Paltz
            (41.5048, -73.9696),  # Beacon/Cold Spring
            (42.2529, -73.7910),  # Hudson
            (41.9270, -74.0001),  # Kingston/Woodstock
            (41.2565, -74.3599),  # Warwick
        ],
    },
    {
        "id": 'hamptons', "name": 'The Hamptons', "state": 'NY', "tranche": 7,
        "display": 'The Hamptons and North Fork, New York',
        "center": (40.8843, -72.3895), "radius_m": 18000,
        "grid": [
            (40.8843, -72.3895),  # Southampton
            (40.9634, -72.1848),  # East Hampton
            (41.0359, -71.9545),  # Montauk
            (40.9979, -72.2926),  # Sag Harbor
            (40.9170, -72.6620),  # Riverhead
            (41.1034, -72.3598),  # Greenport
        ],
    },
    {
        "id": 'poconos', "name": 'Poconos', "state": 'PA', "tranche": 7,
        "display": 'The Poconos, Pennsylvania',
        "center": (40.9868, -75.1946), "radius_m": 22000,
        "grid": [
            (40.9868, -75.1946),  # Stroudsburg
            (41.1220, -75.3646),  # Mount Pocono
            (41.4762, -75.1810),  # Hawley/Lake Wallenpaupack
            (40.8759, -75.7324),  # Jim Thorpe
            (41.3223, -74.8024),  # Milford
        ],
    },
    {
        "id": 'smoky-mountains', "name": 'Gatlinburg', "state": 'TN', "tranche": 7,
        "display": 'Gatlinburg, Pigeon Forge and the Smoky Mountains, Tennessee',
        "center": (35.7143, -83.5102), "radius_m": 18000,
        "grid": [
            (35.7143, -83.5102),  # Gatlinburg
            (35.7884, -83.5543),  # Pigeon Forge
            (35.8681, -83.5619),  # Sevierville
            (35.6751, -83.7538),  # Townsend
            (35.7480, -83.6600),  # Wears Valley
            (35.4315, -83.4490),  # Bryson City
        ],
    },
    {
        "id": 'anchorage', "name": 'Anchorage', "state": 'AK', "tranche": 7,
        "display": 'Anchorage, Alaska',
        "center": (61.2181, -149.9003), "radius_m": 22000,
        "grid": [
            (61.2181, -149.9003),  # Anchorage core
            (61.3214, -149.5678),  # Eagle River
            (61.5814, -149.4394),  # Wasilla/Palmer
            (60.9426, -149.1663),  # Girdwood
            (60.1042, -149.4422),  # Seward
        ],
    },
    {
        "id": 'little-rock', "name": 'Little Rock', "state": 'AR', "tranche": 7,
        "display": 'Little Rock and Hot Springs, Arkansas',
        "center": (34.7465, -92.2896), "radius_m": 22000,
        "grid": [
            (34.7465, -92.2896),  # Little Rock core
            (34.7695, -92.2671),  # North Little Rock
            (35.0887, -92.4421),  # Conway
            (34.5645, -92.5868),  # Benton/Bryant
            (34.5037, -93.0552),  # Hot Springs
            (34.9745, -92.0165),  # Cabot
        ],
    },
    {
        "id": 'wichita', "name": 'Wichita', "state": 'KS', "tranche": 7,
        "display": 'Wichita, Kansas',
        "center": (37.6872, -97.3301), "radius_m": 22000,
        "grid": [
            (37.6872, -97.3301),  # Wichita core
            (37.5456, -97.2689),  # Derby
            (37.7139, -97.1364),  # Andover
            (37.7780, -97.4670),  # Maize/West Wichita
            (38.0467, -97.3450),  # Newton
        ],
    },
    {
        "id": 'portland-maine', "name": 'Portland', "state": 'ME', "tranche": 7,
        "display": 'Portland and the Maine Coast',
        "center": (43.6591, -70.2568), "radius_m": 22000,
        "grid": [
            (43.6591, -70.2568),  # Portland core
            (43.3617, -70.4767),  # Kennebunkport
            (43.9145, -69.9653),  # Freeport/Brunswick
            (43.5781, -70.3220),  # Scarborough/Cape Elizabeth
            (44.2098, -69.0648),  # Camden/Rockland
            (44.3876, -68.2039),  # Bar Harbor
        ],
    },
    {
        "id": 'jackson-ms', "name": 'Jackson', "state": 'MS', "tranche": 7,
        "display": 'Jackson, Mississippi',
        "center": (32.2988, -90.1848), "radius_m": 22000,
        "grid": [
            (32.2988, -90.1848),  # Jackson core
            (32.4618, -90.1153),  # Madison/Ridgeland
            (32.2732, -89.9859),  # Brandon/Flowood
            (32.3415, -90.3218),  # Clinton
            (32.3526, -90.8779),  # Vicksburg
            (31.3271, -89.2903),  # Hattiesburg
        ],
    },
    {
        "id": 'billings', "name": 'Billings', "state": 'MT', "tranche": 7,
        "display": 'Billings, Bozeman and Montana',
        "center": (45.7833, -108.5007), "radius_m": 24000,
        "grid": [
            (45.7833, -108.5007),  # Billings core
            (45.6770, -111.0429),  # Bozeman
            (46.8721, -113.9940),  # Missoula
            (46.5891, -112.0391),  # Helena
            (45.1858, -109.2468),  # Red Lodge
            (45.2618, -111.3080),  # Big Sky
            (48.1920, -114.3168),  # Kalispell/Whitefish
        ],
    },
    {
        "id": 'fargo', "name": 'Fargo', "state": 'ND', "tranche": 7,
        "display": 'Fargo and Bismarck, North Dakota',
        "center": (46.8772, -96.7898), "radius_m": 22000,
        "grid": [
            (46.8772, -96.7898),  # Fargo core
            (46.8738, -96.7678),  # Moorhead
            (46.8750, -96.9003),  # West Fargo
            (47.9253, -97.0329),  # Grand Forks
            (46.8083, -100.7837),  # Bismarck
        ],
    },
    {
        "id": 'manchester-nh', "name": 'Manchester', "state": 'NH', "tranche": 7,
        "display": 'Manchester and the Lakes Region, New Hampshire',
        "center": (42.9956, -71.4548), "radius_m": 22000,
        "grid": [
            (42.9956, -71.4548),  # Manchester core
            (42.7654, -71.4676),  # Nashua
            (43.2081, -71.5376),  # Concord
            (43.0718, -70.7626),  # Portsmouth
            (43.6576, -71.5003),  # Lake Winnipesaukee/Meredith
            (44.0537, -71.1284),  # North Conway
        ],
    },
    {
        "id": 'sioux-falls', "name": 'Sioux Falls', "state": 'SD', "tranche": 7,
        "display": 'Sioux Falls and the Black Hills, South Dakota',
        "center": (43.5460, -96.7313), "radius_m": 22000,
        "grid": [
            (43.5460, -96.7313),  # Sioux Falls core
            (43.5947, -96.5717),  # Brandon
            (43.4314, -96.6973),  # Harrisburg/Tea
            (44.0805, -103.2310),  # Rapid City
            (44.3767, -103.7296),  # Spearfish/Deadwood
        ],
    },
    {
        "id": 'burlington-vt', "name": 'Burlington', "state": 'VT', "tranche": 7,
        "display": 'Burlington and Stowe, Vermont',
        "center": (44.4759, -73.2121), "radius_m": 22000,
        "grid": [
            (44.4759, -73.2121),  # Burlington core
            (44.4654, -72.6874),  # Stowe
            (44.3798, -73.2276),  # Shelburne
            (44.2601, -72.5754),  # Montpelier
            (43.6242, -72.5187),  # Woodstock
            (43.1637, -73.0723),  # Manchester
        ],
    },
    {
        "id": 'charleston-wv', "name": 'Charleston', "state": 'WV', "tranche": 7,
        "display": 'Charleston and the Greenbrier Valley, West Virginia',
        "center": (38.3498, -81.6326), "radius_m": 22000,
        "grid": [
            (38.3498, -81.6326),  # Charleston core
            (38.4192, -82.4452),  # Huntington
            (39.6295, -79.9559),  # Morgantown
            (37.8018, -80.4456),  # Lewisburg/Greenbrier
            (39.2667, -81.5615),  # Parkersburg
        ],
    },

]

BY_ID = {m["id"]: m for m in METROS}

def metros_for_tranche(t: int):
    return [m for m in METROS if m["tranche"] <= t]

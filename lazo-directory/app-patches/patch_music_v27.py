"""patch_music_v27.py - Music widget v2.7 (THE SET LIST)
Music_master_v26.txt -> Music_master_v27.txt. Anchor-asserted (exact counts).
  1. A Lazo starter set list: 266 well-known wedding songs in 26 sections by
     moment (ceremony, reception moments, cocktail hour and dinner, the dance
     floor by decade and genre) plus 12 commonly skipped songs offered as
     do-not-play suggestions. Title and artist only; clean-edit flags.
  2. A Set list tab: load the starter list or start blank (nothing is seeded
     until the couple taps), open a section, hear a song (looked up through
     /music/search on the first tap), remove (swipe or menu, with Undo), add
     from search or type one in, drag to reorder, move to another section,
     star a must play, use it for that section's moment, don't play, a note,
     skip a whole section, reset a section or everything to the Lazo list
     (the couple's own songs stay). "No line dances" starts that section off.
  3. A new moment, Aisle entrance, between the processional and recessional.
  4. The set list rides along everywhere the plan goes: copy/email text, the
     printable Music.html the DJ gets in the thread, and - when the couple has
     a wedding site - a live mirror at weddingSites/{slug}/playlist/setlist
     that the worker renders at meetlazo.com/w/{slug}/setlist (worker
     JC-LAZO-WORKER-1016-SETLIST). Rules unchanged: music/main is under
     couples/{cid}/{col}/{doc}; playlist/{doc} already allows the couple.
  5. A save refused by the rules now says to confirm the email (rules
     JC-LAZO-RULES-1016-021 make signedIn() require a verified email).
  python app-patches\\patch_music_v27.py
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "Music_master_v26.txt"
DST = HERE / "Music_master_v27.txt"
s = SRC.read_text(encoding="utf-8")


def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, f"anchor x{n} (want {count}): {old[:70]!r}"
    s = s.replace(old, new)


# ---------------------------------------------------------------- catalog
# key, label, group, the moment its rows can fill ('' = none), songs.
# 'Title|Artist', '|c' = ask the DJ for the clean edit.
SECTIONS = [
    ("processional", "Processional", "ceremony", "processional", [
        "Canon in D|Johann Pachelbel",
        "A Thousand Years|Christina Perri",
        "Married Life|Michael Giacchino",
        "Here Comes the Sun|The Beatles",
        "Air on the G String|J.S. Bach",
        "Jesu, Joy of Man's Desiring|J.S. Bach",
        "Clair de Lune|Claude Debussy",
        "River Flows in You|Yiruma",
        "Somewhere Over the Rainbow / What a Wonderful World|Israel Kamakawiwo'ole",
        "Turning Page|Sleeping At Last",
        "Marry Me|Train",
        "Bloom|The Paper Kites",
    ]),
    ("aisle", "Aisle entrance", "ceremony", "aisle", [
        "Bridal Chorus (Here Comes the Bride)|Richard Wagner",
        "Trumpet Voluntary|Jeremiah Clarke",
        "Arrival of the Queen of Sheba|G.F. Handel",
        "Ave Maria|Franz Schubert",
        "Can't Help Falling in Love|Elvis Presley",
        "Yellow|Coldplay",
        "Make You Feel My Love|Adele",
        "All of Me|John Legend",
    ]),
    ("recessional", "Recessional", "ceremony", "recessional", [
        "Wedding March|Felix Mendelssohn",
        "Ode to Joy|Ludwig van Beethoven",
        "Signed, Sealed, Delivered I'm Yours|Stevie Wonder",
        "You Are the Best Thing|Ray LaMontagne",
        "Marry You|Bruno Mars",
        "Happy|Pharrell Williams",
        "Love on Top|Beyonc\u00e9",
        "I'm a Believer|The Monkees",
        "Beautiful Day|U2",
        "Lovely Day|Bill Withers",
    ]),
    ("partyEntrance", "Wedding party entrance", "moments", "partyEntrance", [
        "Uptown Funk|Mark Ronson ft. Bruno Mars",
        "Can't Stop the Feeling!|Justin Timberlake",
        "Shut Up and Dance|Walk the Moon",
        "Turn Down for What|DJ Snake & Lil Jon|c",
        "Let's Get It Started|The Black Eyed Peas",
        "All I Do Is Win|DJ Khaled|c",
        "Party Rock Anthem|LMFAO",
        "Dynamite|Taio Cruz",
        "Levels|Avicii",
        "Pump It|The Black Eyed Peas",
    ]),
    ("grandEntrance", "Grand entrance", "moments", "entrance", [
        "Crazy in Love|Beyonc\u00e9 ft. Jay-Z|c",
        "Ain't No Mountain High Enough|Marvin Gaye & Tammi Terrell",
        "I Gotta Feeling|The Black Eyed Peas",
        "Don't Stop Me Now|Queen",
        "Higher Love|Kygo & Whitney Houston",
        "Good as Hell|Lizzo|c",
        "This Will Be (An Everlasting Love)|Natalie Cole",
        "Best Day of My Life|American Authors",
    ]),
    ("firstDance", "First dance", "moments", "firstDance", [
        "Perfect|Ed Sheeran",
        "Thinking Out Loud|Ed Sheeran",
        "At Last|Etta James",
        "Die With A Smile|Lady Gaga & Bruno Mars",
        "Lover|Taylor Swift",
        "Until I Found You|Stephen Sanchez",
        "Speechless|Dan + Shay",
        "10,000 Hours|Dan + Shay & Justin Bieber",
        "Tennessee Whiskey|Chris Stapleton",
        "Die a Happy Man|Thomas Rhett",
        "Wonderful Tonight|Eric Clapton",
        "The Way You Look Tonight|Frank Sinatra",
        "Unchained Melody|The Righteous Brothers",
        "Just the Way You Are|Bruno Mars",
        "I Get to Love You|Ruelle",
        "Better Together|Jack Johnson",
        "Lucky|Jason Mraz & Colbie Caillat",
        "Endless Love|Lionel Richie & Diana Ross",
        "Golden Hour|JVKE",
        "Bless the Broken Road|Rascal Flatts",
        "Amazed|Lonestar",
        "Say You Won't Let Go|James Arthur",
    ]),
    ("fatherDaughter", "Parent dance: father-daughter", "moments", "parentDance1", [
        "My Girl|The Temptations",
        "Butterfly Kisses|Bob Carlisle",
        "I Loved Her First|Heartland",
        "What a Wonderful World|Louis Armstrong",
        "My Little Girl|Tim McGraw",
        "Isn't She Lovely|Stevie Wonder",
        "Unforgettable|Nat King Cole & Natalie Cole",
        "Cinderella|Steven Curtis Chapman",
        "Dance with My Father|Luther Vandross",
        "Forever Young|Rod Stewart",
    ]),
    ("motherSon", "Parent dance: mother-son", "moments", "parentDance2", [
        "A Song for Mama|Boyz II Men",
        "Simple Man|Lynyrd Skynyrd",
        "You Raise Me Up|Josh Groban",
        "Wind Beneath My Wings|Bette Midler",
        "I Hope You Dance|Lee Ann Womack",
        "Because You Loved Me|Celine Dion",
        "Humble and Kind|Tim McGraw",
        "Landslide|Fleetwood Mac",
    ]),
    ("cake", "Cake cutting", "moments", "cake", [
        "Sugar|Maroon 5",
        "Pour Some Sugar on Me|Def Leppard",
        "Sugar, Sugar|The Archies",
        "How Sweet It Is (To Be Loved by You)|James Taylor",
        "Cake by the Ocean|DNCE",
        "I Want Candy|Bow Wow Wow",
        "Love and Marriage|Frank Sinatra",
        "Sweet Child O' Mine|Guns N' Roses",
    ]),
    ("bouquet", "Bouquet & garter", "moments", "bouquet", [
        "Single Ladies (Put a Ring on It)|Beyonc\u00e9",
        "Girls Just Want to Have Fun|Cyndi Lauper",
        "Wannabe|Spice Girls",
        "Man! I Feel Like a Woman!|Shania Twain",
        "Another One Bites the Dust|Queen",
        "Bad to the Bone|George Thorogood & The Destroyers",
        "Legs|ZZ Top",
        "The Stripper|David Rose",
    ]),
    ("lastDance", "Last dance", "moments", "lastDance", [
        "(I've Had) The Time of My Life|Bill Medley & Jennifer Warnes",
        "Closing Time|Semisonic",
        "Last Dance|Donna Summer",
        "Save the Last Dance for Me|The Drifters",
        "Piano Man|Billy Joel",
        "Bohemian Rhapsody|Queen",
        "New York, New York|Frank Sinatra",
        "Hey Jude|The Beatles",
        "American Pie|Don McLean",
        "Leave the Door Open|Silk Sonic",
    ]),
    ("sendOff", "Send-off", "moments", "sendOff", [
        "Mr. Blue Sky|Electric Light Orchestra",
        "Home|Edward Sharpe & The Magnetic Zeros",
        "Viva la Vida|Coldplay",
        "On the Road Again|Willie Nelson",
        "Life Is a Highway|Rascal Flatts",
        "Born to Run|Bruce Springsteen",
    ]),
    ("cocktail", "Cocktail hour", "dinner", "", [
        "Fly Me to the Moon|Frank Sinatra",
        "L-O-V-E|Nat King Cole",
        "Sway|Michael Bubl\u00e9",
        "Feeling Good|Michael Bubl\u00e9",
        "Put Your Records On|Corinne Bailey Rae",
        "Sunday Morning|Maroon 5",
        "Banana Pancakes|Jack Johnson",
        "Valerie|Mark Ronson ft. Amy Winehouse",
        "I'm Yours|Jason Mraz",
        "La Vie en Rose|Louis Armstrong",
        "Come Away with Me|Norah Jones",
        "Dreams|Fleetwood Mac",
        "Golden|Harry Styles",
        "Riptide|Vance Joy",
        "Ho Hey|The Lumineers",
        "Moon River|Andy Williams",
        "Coming Home|Leon Bridges",
        "Cheek to Cheek|Ella Fitzgerald & Louis Armstrong",
    ]),
    ("dinner", "Dinner", "dinner", "", [
        "Let's Stay Together|Al Green",
        "Something|The Beatles",
        "In My Life|The Beatles",
        "Your Song|Elton John",
        "Tiny Dancer|Elton John",
        "Into the Mystic|Van Morrison",
        "Bubbly|Colbie Caillat",
        "Everywhere|Fleetwood Mac",
        "Adorn|Miguel",
        "Best Part|Daniel Caesar ft. H.E.R.",
        "Ordinary People|John Legend",
        "Harvest Moon|Neil Young",
        "Can't Take My Eyes Off You|Frankie Valli",
        "Kiss Me|Sixpence None the Richer",
        "A Sunday Kind of Love|Etta James",
        "Stand by Me|Ben E. King",
    ]),
    ("motown", "Motown, soul & disco", "floor", "", [
        "September|Earth, Wind & Fire",
        "Let's Groove|Earth, Wind & Fire",
        "Shout|The Isley Brothers",
        "Superstition|Stevie Wonder",
        "Respect|Aretha Franklin",
        "Build Me Up Buttercup|The Foundations",
        "Brown Eyed Girl|Van Morrison",
        "Twist and Shout|The Beatles",
        "Sweet Caroline|Neil Diamond",
        "Dancing Queen|ABBA",
        "Le Freak|Chic",
        "Stayin' Alive|Bee Gees",
        "I Will Survive|Gloria Gaynor",
        "Celebration|Kool & The Gang",
    ]),
    ("eighties", "The 80s", "floor", "", [
        "I Wanna Dance with Somebody (Who Loves Me)|Whitney Houston",
        "Don't Stop Believin'|Journey",
        "Livin' on a Prayer|Bon Jovi",
        "Footloose|Kenny Loggins",
        "You Make My Dreams|Daryl Hall & John Oates",
        "Billie Jean|Michael Jackson",
        "Jump (For My Love)|The Pointer Sisters",
        "Love Shack|The B-52's",
        "Come On Eileen|Dexys Midnight Runners",
        "Take On Me|a-ha",
        "Walking on Sunshine|Katrina and the Waves",
        "Like a Prayer|Madonna",
    ]),
    ("nineties", "The 90s", "floor", "", [
        "No Diggity|Blackstreet ft. Dr. Dre|c",
        "Gonna Make You Sweat (Everybody Dance Now)|C+C Music Factory",
        "Everybody (Backstreet's Back)|Backstreet Boys",
        "I Want It That Way|Backstreet Boys",
        "Bye Bye Bye|*NSYNC",
        "Gettin' Jiggy wit It|Will Smith",
        "Poison|Bell Biv DeVoe",
        "Jump Around|House of Pain|c",
        "Return of the Mack|Mark Morrison",
        "This Is How We Do It|Montell Jordan",
        "Livin' la Vida Loca|Ricky Martin",
        "Baby Got Back|Sir Mix-a-Lot|c",
    ]),
    ("twoThousands", "The 2000s", "floor", "", [
        "Mr. Brightside|The Killers",
        "Hey Ya!|OutKast",
        "Yeah!|Usher ft. Lil Jon & Ludacris|c",
        "Hips Don't Lie|Shakira ft. Wyclef Jean",
        "Since U Been Gone|Kelly Clarkson",
        "Low|Flo Rida ft. T-Pain|c",
        "Toxic|Britney Spears",
        "Party in the U.S.A.|Miley Cyrus",
        "Hot in Herre|Nelly|c",
        "Umbrella|Rihanna ft. Jay-Z",
        "Just Dance|Lady Gaga ft. Colby O'Donis",
        "Love Story|Taylor Swift",
    ]),
    ("now", "2010s to now", "floor", "", [
        "Shake It Off|Taylor Swift",
        "Cruel Summer|Taylor Swift",
        "Blinding Lights|The Weeknd",
        "Levitating|Dua Lipa",
        "Don't Start Now|Dua Lipa",
        "24K Magic|Bruno Mars",
        "Treasure|Bruno Mars",
        "Get Lucky|Daft Punk ft. Pharrell Williams",
        "Timber|Pitbull ft. Ke$ha",
        "Wake Me Up|Avicii",
        "Watermelon Sugar|Harry Styles",
        "As It Was|Harry Styles",
        "Flowers|Miley Cyrus",
        "Espresso|Sabrina Carpenter",
        "HOT TO GO!|Chappell Roan",
        "APT.|ROS\u00c9 & Bruno Mars",
    ]),
    ("hiphop", "Hip-hop & R&B", "floor", "", [
        "Before I Let Go|Frankie Beverly & Maze",
        "Family Affair|Mary J. Blige",
        "Lose Control|Missy Elliott ft. Ciara & Fat Man Scoop|c",
        "Hypnotize|The Notorious B.I.G.|c",
        "Empire State of Mind|Jay-Z ft. Alicia Keys|c",
        "Rock Your Body|Justin Timberlake",
        "Boo'd Up|Ella Mai",
        "Kiss Me More|Doja Cat ft. SZA|c",
        "Juice|Lizzo|c",
        "Back That Azz Up|Juvenile|c",
    ]),
    ("country", "Country", "floor", "", [
        "Friends in Low Places|Garth Brooks",
        "Wagon Wheel|Darius Rucker",
        "Chicken Fried|Zac Brown Band",
        "Body Like a Back Road|Sam Hunt",
        "Fishin' in the Dark|Nitty Gritty Dirt Band",
        "Any Man of Mine|Shania Twain",
        "Neon Moon|Brooks & Dunn",
        "Fast Car|Luke Combs",
        "Save a Horse (Ride a Cowboy)|Big & Rich",
        "Texas Hold 'Em|Beyonc\u00e9",
    ]),
    ("latin", "Latin", "floor", "", [
        "Suavemente|Elvis Crespo",
        "Vivir Mi Vida|Marc Anthony",
        "La Bamba|Ritchie Valens",
        "Conga|Gloria Estefan & Miami Sound Machine",
        "Bidi Bidi Bom Bom|Selena",
        "Despacito|Luis Fonsi & Daddy Yankee",
        "Bailando|Enrique Iglesias ft. Descemer Bueno & Gente de Zona",
        "Gasolina|Daddy Yankee",
        "Danza Kuduro|Don Omar & Lucenzo",
        "Mi Gente|J Balvin & Willy William",
    ]),
    ("lineDances", "Line & group dances", "floor", "", [
        "Cupid Shuffle|Cupid",
        "Wobble|V.I.C.",
        "Electric Boogie (Electric Slide)|Marcia Griffiths",
        "Cha Cha Slide|DJ Casper",
        "Macarena (Bayside Boys Mix)|Los del R\u00edo",
        "Y.M.C.A.|Village People",
        "Copperhead Road|Steve Earle",
        "Boot Scootin' Boogie|Brooks & Dunn",
        "The Git Up|Blanco Brown",
        "Hava Nagila|Traditional",
    ]),
    ("slow", "Slow songs for the floor", "floor", "", [
        "Truly Madly Deeply|Savage Garden",
        "I Don't Want to Miss a Thing|Aerosmith",
        "Halo|Beyonc\u00e9",
        "Everything|Michael Bubl\u00e9",
        "Iris|Goo Goo Dolls",
        "Make It with You|Bread",
    ]),
    ("skipped", "Commonly skipped", "skip", "", [
        "The Chicken Dance|Traditional",
        "Cotton Eye Joe|Rednex",
        "Achy Breaky Heart|Billy Ray Cyrus",
        "The Hokey Pokey|Traditional",
        "Baby Shark|Pinkfong",
        "Gangnam Style|PSY",
        "Before He Cheats|Carrie Underwood",
        "thank u, next|Ariana Grande",
        "We Are Never Ever Getting Back Together|Taylor Swift",
        "Ex's & Oh's|Elle King",
        "Goodbye Earl|The Chicks",
        "Every Breath You Take|The Police",
    ]),
]

WANT = {"processional": 12, "aisle": 8, "recessional": 10, "partyEntrance": 10,
        "grandEntrance": 8, "firstDance": 22, "fatherDaughter": 10,
        "motherSon": 8, "cake": 8, "bouquet": 8, "lastDance": 10, "sendOff": 6,
        "cocktail": 18, "dinner": 16, "motown": 14, "eighties": 12,
        "nineties": 12, "twoThousands": 12, "now": 16, "hiphop": 10,
        "country": 10, "latin": 10, "lineDances": 10, "slow": 6, "skipped": 12}


def slug(t):
    # same as the widget's _slug (ASCII only; accents drop out on both sides)
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", t.lower()))


seen = {}
play = 0
for key, label, group, moment, songs in SECTIONS:
    assert len(songs) == WANT[key], f"{key}: {len(songs)} songs, want {WANT[key]}"
    for row in songs:
        p = row.split("|")
        assert len(p) in (2, 3) and p[0] and p[1], row
        assert len(p) == 2 or p[2] == "c", row
        assert '"' not in row, f"double quote breaks the r\"\" literal: {row}"
        sid = slug(p[0] + " " + p[1])
        assert sid not in seen, f"duplicate {row!r} (also in {seen[sid]})"
        seen[sid] = key
    if group != "skip":
        play += len(songs)
assert len(SECTIONS) == 25, len(SECTIONS)
assert play == 266, play
assert len(seen) == 278, len(seen)

GROUP_LABELS = {"ceremony": "The ceremony", "moments": "Reception moments",
                "dinner": "Cocktail hour & dinner", "floor": "The dance floor",
                "skip": "Do-not-play ideas"}

dart_sections = "\n".join(
    f"    <String>['{k}', '{l}', '{g}', '{m}'],"
    for k, l, g, m, _ in SECTIONS)
dart_songs = []
for k, _, _, _, songs in SECTIONS:
    dart_songs.append(f"    '{k}': <String>[")
    for row in songs:
        dart_songs.append(f'      r"{row}",')
    dart_songs.append("    ],")
dart_songs = "\n".join(dart_songs)
dart_groups = "\n".join(f"    '{k}': '{v}'," for k, v in GROUP_LABELS.items())

# ---------------------------------------------------------------- header
rep("// Build ID: JC-LAZO-MUSIC-0929-V25\n",
    "// Build ID: JC-LAZO-MUSIC-1016-V27\n")
rep("""// (v2.6: PHONES""",
    r"""// (v2.7: THE SET LIST - a Set list tab seeded on request from the Lazo
// starter list (266 wedding staples in 25 sections by moment and decade, plus
// 12 commonly skipped songs as do-not-play ideas): remove (swipe, Undo), add
// from search or typed in, drag to reorder, move between sections, star a
// must play, use for the section's moment, skip a section, reset a section
// or everything to the Lazo list. New moment: Aisle entrance. The list goes
// into the copy/email text and the DJ's Music.html, and with a wedding site
// is mirrored to weddingSites/{slug}/playlist/setlist for the live page at
// meetlazo.com/w/{slug}/setlist. Data: couples/{cid}/music/main.setlist.)
// (v2.6: PHONES""")

# ---------------------------------------------------------------- the section model
rep("""class _LazoMusicState extends State<LazoMusic> {
""", r"""// v2.7: one section of the set list. Songs are ordinary _Song rows; the
// starter ones carry ids 'lz:<slug>' so a reset can tell them from the
// couple's own picks (search ids, or 'typed:<ms>').
class _SetSection {
  _SetSection(
      {required this.key,
      required this.label,
      this.group = '',
      this.moment = '',
      this.off = false,
      this.skipList = false,
      List<_Song>? songs})
      : songs = songs ?? <_Song>[];
  final String key;
  String label;
  final String group;
  final String moment; // a moment key: rows offer "Use for ..."
  bool off; // "we're skipping this" - kept, and the DJ is told to skip it
  final bool skipList; // the do-not-play ideas, never played
  final List<_Song> songs;

  static Map<String, dynamic> songMap(_Song s) => <String, dynamic>{
        'id': s.id,
        'title': s.title,
        'artist': s.artist,
        if (s.album.isNotEmpty) 'album': s.album,
        if (s.art.isNotEmpty) 'art': s.art,
        if (s.preview.isNotEmpty) 'preview': s.preview,
        if (s.ms > 0) 'ms': s.ms,
        if (s.link.isNotEmpty) 'link': s.link,
        if (s.note.isNotEmpty) 'note': s.note,
        if (s.explicit) 'explicit': true,
      };

  Map<String, dynamic> toMap() => <String, dynamic>{
        'key': key,
        'label': label,
        'group': group,
        'moment': moment,
        'off': off,
        if (skipList) 'skipList': true,
        'songs': songs.map(songMap).toList(),
      };
}

class _LazoMusicState extends State<LazoMusic> {
""")

# ---------------------------------------------------------------- moments + catalog
rep("""    <String>['processional', 'Processional', 'Walking in'],
""", """    <String>['processional', 'Processional', 'Walking in'],
    <String>['aisle', 'Aisle entrance', 'The walk everyone stands for'],
""")

rep("""    'Read the room',
  ];
""", """    'Read the room',
  ];

  // v2.7: THE LAZO STARTER SET LIST. Generated by patch_music_v27.py, which
  // asserts the counts and that no song appears twice. Each section: key,
  // label, group, the moment its rows can fill ('' = none).
  static const String kSetBase = 'lazo-2026-10';
  static const String kSkipGroup = 'skip';
  static const List<List<String>> kSetSections = <List<String>>[
""" + dart_sections + """
  ];
  static const Map<String, String> kSetGroups = <String, String>{
""" + dart_groups + """
  };
  // 'Title|Artist', and '|c' when the DJ should play the clean edit.
  static const Map<String, List<String>> kStarterSongs =
      <String, List<String>>{
""" + dart_songs + """
  };
""")

# ---------------------------------------------------------------- state
rep("""  final List<String> _avoid = <String>[];
""", """  final List<String> _avoid = <String>[];
  // v2.7: the set list
  final List<_SetSection> _set = <_SetSection>[];
  final Set<String> _setOpen = <String>{};
  final Set<String> _resolving = <String>{}; // rows looking up a preview
  String _searchSet = ''; // a set-list section key: the next + files there
""")

# ---------------------------------------------------------------- load / save
rep("""    _notes = (d['notes'] ?? '').toString();
""", """    _loadSet(d['setlist']);
    _notes = (d['notes'] ?? '').toString();
""")

rep("""        'notes': _notes,
        'coupleUid': _cid,
""", """        'notes': _notes,
        if (_set.isNotEmpty) 'setlist': _setToMap(),
        'coupleUid': _cid,
""")

rep("""      _dirty = false;
    } catch (e) {
      _toast('Could not save: ' + _errText(e));
    }""", """      _dirty = false;
      _mirrorSet(); // v2.7: the DJ's live page, when there is a site
    } catch (e) {
      _toast('Could not save: ' + _errText(e));
    }""")

rep(r"""      return 'permission denied - the rules may need updating.';""",
    r"""      return 'permission denied - if you haven\u2019t confirmed your email yet, do that first and try again.';""")

# ---------------------------------------------------------------- player knows set rows
rep("""    return _juneSong.containsKey(_playingId) ? _juneSong[_playingId] : null;
""", """    for (final _SetSection x in _set) {
      for (final _Song s in x.songs) {
        if (s.id == _playingId) return s;
      }
    }
    return _juneSong.containsKey(_playingId) ? _juneSong[_playingId] : null;
""")

rep("""  Widget _playBtn(_Song s, {double size = 34}) {""",
    """  Widget _playBtn(_Song s, {double size = 34, VoidCallback? onTap}) {""")
rep("""      tick: _Tick.none, // _togglePlay ticks when playback actually changes
      onTap: () => _togglePlay(s),""",
    """      tick: _Tick.none, // _togglePlay ticks when playback actually changes
      onTap: onTap ?? (() => _togglePlay(s)),""")

# ---------------------------------------------------------------- search targets
rep("""    if (_searchFor.isNotEmpty) {
      final String key = _searchFor;
      setState(() {
        _searchFor = '';
        _tab = 0;
      });
      _setMoment(key, s);
      return;
    }""", """    if (_searchSet.isNotEmpty) {
      final String key = _searchSet;
      setState(() {
        _searchSet = '';
        _tab = 2;
      });
      _setAdd(key, s);
      return;
    }
    if (_searchFor.isNotEmpty) {
      final String key = _searchFor;
      setState(() {
        _searchFor = '';
        _tab = 0;
      });
      _setMoment(key, s);
      return;
    }""")

rep("""      _reqFor = d.id;
      _searchFor = '';
""", """      _reqFor = d.id;
      _searchFor = '';
      _searchSet = '';
""")

rep("""                          _searchFor = m[0];
                          _reqFor = '';
""", """                          _searchFor = m[0];
                          _reqFor = '';
                          _searchSet = '';
""")

rep("""    } else if (_searchFor.isNotEmpty) {
      title = 'Choose your ${_momentLabel(_searchFor).toLowerCase()}';
      sub = 'Tap + on a result to set it.';
    }
    final bool targeted = _reqFor.isNotEmpty || _searchFor.isNotEmpty;""",
    """    } else if (_searchFor.isNotEmpty) {
      title = 'Choose your ${_momentLabel(_searchFor).toLowerCase()}';
      sub = 'Tap + on a result to set it.';
    } else if (_searchSet.isNotEmpty) {
      title = 'Add to ${_setLabel(_searchSet)}';
      sub = 'Tap + on a result to add it to your set list.';
    }
    final bool targeted = _reqFor.isNotEmpty ||
        _searchFor.isNotEmpty ||
        _searchSet.isNotEmpty;""")

rep("""                            onPressed: _h(() => setState(() {
                                  _searchFor = '';
                                  _reqFor = '';
                                })),""", """                            onPressed: _h(() => setState(() {
                                  if (_searchSet.isNotEmpty) _tab = 2;
                                  _searchFor = '';
                                  _reqFor = '';
                                  _searchSet = '';
                                })),""")

# ---------------------------------------------------------------- layout: tabs
rep("""          Expanded(
              child: Padding(
                  padding: const EdgeInsets.all(14), child: _planPanel())),
        ]);
  }""", """          Expanded(
              child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Row(children: <Widget>[
                          _tabChip('Your plan', 0, badge: _newRequests),
                          const SizedBox(width: 6),
                          _tabChip('Set list', 2),
                        ]),
                        const SizedBox(height: 10),
                        Expanded(
                            child: _viewSwitch(_wideSet
                                ? KeyedSubtree(
                                    key: const ValueKey<String>('set'),
                                    child: _setPanel())
                                : KeyedSubtree(
                                    key: const ValueKey<String>('plan:root'),
                                    child: _planPanel()))),
                      ]))),
        ]);
  }

  // v2.7: on wide screens search is always on the left; the right side shows
  // the set list while it is open or while search is filling a section.
  bool get _wideSet => _tab == 2 || (_tab == 1 && _searchSet.isNotEmpty);""")

rep("""    final String searchLabel = _reqFor.isNotEmpty
        ? 'Pick the version'
        : _searchFor.isNotEmpty
            ? 'Choose: ${_momentLabel(_searchFor)}'
            : 'Find songs';""", """    final String searchLabel = _reqFor.isNotEmpty
        ? 'Pick the version'
        : _searchFor.isNotEmpty
            ? 'Choose: ${_momentLabel(_searchFor)}'
            : _searchSet.isNotEmpty
                ? 'Add to: ${_setLabel(_searchSet)}'
                : 'Find songs';""")

rep("""        child: Row(children: <Widget>[
          _tabChip('Your plan', 0, badge: _newRequests),
          const SizedBox(width: 6),
          _tabChip(searchLabel, 1),
        ]),""", """        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(children: <Widget>[
            _tabChip('Your plan', 0, badge: _newRequests),
            const SizedBox(width: 6),
            _tabChip('Set list', 2),
            const SizedBox(width: 6),
            _tabChip(searchLabel, 1),
          ]),
        ),""")

rep("""              child: _viewSwitch(_tab == 0
                  ? KeyedSubtree(
                      key: const ValueKey<String>('plan:root'),
                      child: _planPanel())
                  : KeyedSubtree(
                      key: const ValueKey<String>('search'),
                      child: _searchPanel())))),""", """              child: _viewSwitch(_tab == 0
                  ? KeyedSubtree(
                      key: const ValueKey<String>('plan:root'),
                      child: _planPanel())
                  : _tab == 2
                      ? KeyedSubtree(
                          key: const ValueKey<String>('set'),
                          child: _setPanel())
                      : KeyedSubtree(
                          key: const ValueKey<String>('search'),
                          child: _searchPanel())))),""")

# ---------------------------------------------------------------- send / print / copy
rep("""  bool get _hasAnything =>
      _moments.isNotEmpty || _must.isNotEmpty || _dont.isNotEmpty;""",
    """  bool get _hasAnything =>
      _moments.isNotEmpty ||
      _must.isNotEmpty ||
      _dont.isNotEmpty ||
      _setCount > 0;""")

rep(r"""    b.writeln('Planned on Lazo \u00b7 meetlazo.com');""",
    r"""    // v2.7: the set list last, so a capped thread message loses it first
    final List<_SetSection> play = _setPlayable;
    if (play.isNotEmpty) {
      b.writeln('SET LIST ($_setCount songs)');
      for (final _SetSection x in play) {
        if (x.off) {
          b.writeln('${x.label.toUpperCase()}: skip this section');
          continue;
        }
        b.writeln('${x.label.toUpperCase()} (${x.songs.length})');
        for (final _Song s in x.songs) {
          b.writeln(
              '- ${s.title} - ${s.artist}${_inList(_must, s) ? ' (must play)' : ''}${s.explicit ? ' (clean edit)' : ''}${s.note.isEmpty ? '' : ' (${s.note})'}');
        }
      }
      b.writeln('');
    }
    b.writeln('Planned on Lazo \u00b7 meetlazo.com');""")

rep("""    final String sub = <String>[
      if (_coupleLabel.isNotEmpty) _coupleLabel,""", r"""    // v2.7: the set list, compact - two columns of numbered titles
    final List<_SetSection> play = _setPlayable;
    if (play.isNotEmpty) {
      h.write('<h2>Set list ($_setCount songs)</h2>');
      for (final _SetSection x in play) {
        h.write(
            '<h3>${_esc(x.label)} ${x.off ? '<span class="skip">skip this section</span>' : '<span class="n">${x.songs.length}</span>'}</h3>');
        if (x.off) continue;
        h.write('<ol class="sl">');
        for (final _Song s in x.songs) {
          h.write(
              '<li><b>${_esc(s.title)}</b> <span class="a">${_esc(s.artist)}</span>${_inList(_must, s) ? ' <span class="must">\u2605 must play</span>' : ''}${s.explicit ? ' <span class="cl">clean edit</span>' : ''}${_isStarter(s) ? '' : ' <span class="y">their pick</span>'}${s.note.isEmpty ? '' : '<br><i>${_esc(s.note)}</i>'}</li>');
        }
        h.write('</ol>');
      }
    }
    final String sub = <String>[
      if (_coupleLabel.isNotEmpty) _coupleLabel,""")

rep("""        '.foot{margin-top:34px;color:#6B5F72;font-size:11px;font-family:Helvetica,Arial,sans-serif}'""",
    """        'h3{font-size:16px;font-weight:600;margin:16px 0 4px;color:#3D1C3B}h3 .n{color:#6B5F72;font-size:12px;font-family:Helvetica,Arial,sans-serif}'
        '.skip{color:#B04343;font-size:10.5px;font-family:Helvetica,Arial,sans-serif;text-transform:uppercase;letter-spacing:1px}'
        '.sl{font-family:Helvetica,Arial,sans-serif;font-size:13px;margin:0 0 6px;padding-left:24px;columns:2;column-gap:28px}.sl li{break-inside:avoid;padding:2px 0}.sl .a{color:#6B5F72}'
        '.must{color:#8A6A2F;font-size:11px;font-weight:700}.cl{background:#FFF4E5;color:#8A6A2F;font-size:10px;padding:1px 5px;border-radius:3px}.y{color:#2E8B6B;font-size:10px;text-transform:uppercase;letter-spacing:1px}@media(max-width:600px){.sl{columns:1}}'
        '.foot{margin-top:34px;color:#6B5F72;font-size:11px;font-family:Helvetica,Arial,sans-serif}'""")

rep(r"""        '${note.isEmpty ? 'Here\u2019s our music plan.' : note}\n\n${_summaryText()}';""",
    r"""        '${note.isEmpty ? 'Here\u2019s our music plan.' : note}${_siteSlug.isNotEmpty ? '\n\nLive list (always current): $_liveSetUrl' : ''}\n\n${_summaryText()}';""")

# ---------------------------------------------------------------- logic
rep("""  // ---------------- search ----------------
""", r"""  // ---------------- v2.7: the set list ----------------

  static String _slug(String t) => t
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'^-+|-+$'), '');

  static _Song _starterSong(String row) {
    final List<String> p = row.split('|');
    final String t = p[0];
    final String a = p.length > 1 ? p[1] : '';
    return _Song(
        id: 'lz:${_slug('$t $a')}',
        title: t,
        artist: a,
        explicit: p.length > 2 && p[2] == 'c');
  }

  static bool _isStarter(_Song s) => s.id.startsWith('lz:');

  static List<_Song> _starterFor(String key) =>
      (kStarterSongs[key] ?? const <String>[]).map(_starterSong).toList();

  static int get _starterPlayable {
    int n = 0;
    for (final List<String> d in kSetSections) {
      if (d[2] != kSkipGroup) n += (kStarterSongs[d[0]] ?? const <String>[]).length;
    }
    return n;
  }

  _SetSection _freshSection(List<String> d, {bool empty = false}) =>
      _SetSection(
          key: d[0],
          label: d[1],
          group: d[2],
          moment: d[3],
          skipList: d[2] == kSkipGroup,
          songs: empty ? <_Song>[] : _starterFor(d[0]));

  List<String> _sectionDef(String key) {
    for (final List<String> d in kSetSections) {
      if (d[0] == key) return d;
    }
    return const <String>[];
  }

  _SetSection? _section(String key) {
    for (final _SetSection x in _set) {
      if (x.key == key) return x;
    }
    return null;
  }

  String _setLabel(String key) => _section(key)?.label ?? key;

  // Songs the DJ will play: sections that aren't the skip list or switched off.
  int get _setCount => _set
      .where((_SetSection x) => !x.skipList && !x.off)
      .fold<int>(0, (int n, _SetSection x) => n + x.songs.length);

  List<_SetSection> get _setPlayable => _set
      .where((_SetSection x) => !x.skipList && x.songs.isNotEmpty)
      .toList();

  String get _liveSetUrl => 'https://meetlazo.com/w/$_siteSlug/setlist';

  void _loadSet(dynamic v) {
    _set.clear();
    if (v is! Map || v['sections'] is! List) return;
    for (final dynamic m in v['sections'] as List) {
      if (m is! Map) continue;
      final String key = (m['key'] ?? '').toString();
      if (key.isEmpty) continue;
      _set.add(_SetSection(
          key: key,
          label: (m['label'] ?? key).toString(),
          group: (m['group'] ?? '').toString(),
          moment: (m['moment'] ?? '').toString(),
          off: m['off'] == true,
          skipList: m['skipList'] == true,
          songs: _songList(m['songs'])));
    }
  }

  Map<String, dynamic> _setToMap() => <String, dynamic>{
        'base': kSetBase,
        'sections': _set.map((_SetSection x) => x.toMap()).toList(),
      };

  void _seedSet({bool blank = false}) {
    setState(() {
      _set
        ..clear()
        ..addAll(kSetSections
            .map((List<String> d) => _freshSection(d, empty: blank)));
      if (_vibe.contains('No line dances')) {
        _section('lineDances')?.off = true;
      }
      _setOpen.clear();
      if (!blank) _setOpen.add(_set.first.key);
    });
    _scheduleSave();
    _tick(_Tick.medium);
    _toast(blank
        ? 'A blank set list - add songs to any section.'
        : '$_setCount songs loaded. Now make it yours.');
  }

  static bool _sameSong(_Song a, _Song b) =>
      a.title.trim().toLowerCase() == b.title.trim().toLowerCase() &&
      a.artist.trim().toLowerCase() == b.artist.trim().toLowerCase();

  void _setAdd(String key, _Song s) {
    final _SetSection? x = _section(key);
    if (x == null) return;
    for (final _SetSection o in _set) {
      o.songs.removeWhere((_Song y) => y.id == s.id || _sameSong(y, s));
    }
    x.songs.add(s.copy());
    _setOpen.add(key);
    _scheduleSave();
    _tick(_Tick.medium);
    _toast('${s.title} \u2192 ${x.label} \u2713');
  }

  void _setRemove(_SetSection x, _Song s) {
    final int i = x.songs.indexWhere((_Song y) => y.id == s.id);
    if (i < 0) return;
    setState(() => x.songs.removeAt(i));
    _scheduleSave();
    _tick(_Tick.light);
    _toastUndo('Removed ${s.title}', () {
      if (x.songs.any((_Song y) => y.id == s.id)) return;
      setState(() => x.songs.insert(math.min(i, x.songs.length), s));
      _scheduleSave();
    });
  }

  void _setMove(_SetSection x, _Song s, String toKey) {
    final _SetSection? to = _section(toKey);
    if (to == null || to == x) return;
    setState(() {
      x.songs.removeWhere((_Song y) => y.id == s.id);
      to.songs.add(s);
      _setOpen.add(toKey);
    });
    _scheduleSave();
    _tick(_Tick.medium);
    _toast('${s.title} \u2192 ${to.label} \u2713');
  }

  void _setToggleMust(_Song s) {
    if (_inList(_must, s)) {
      setState(() => _must.removeWhere((_Song x) => x.id == s.id));
      _scheduleSave();
      _tick(_Tick.light);
      _toast('${s.title} is off the must-play list');
    } else {
      _addMust(s);
    }
  }

  void _setDont(_SetSection x, _Song s) {
    _addDont(s);
    if (!x.skipList) {
      setState(() => x.songs.removeWhere((_Song y) => y.id == s.id));
      _scheduleSave();
    }
  }

  // Starter songs come back in the Lazo order (keeping notes and looked-up
  // previews); starter songs that wandered to other sections come home; the
  // couple's own songs stay, at the bottom.
  void _resetSection(_SetSection x) {
    final List<_Song> starter = _starterFor(x.key);
    final Set<String> ids = starter.map((_Song s) => s.id).toSet();
    final Map<String, _Song> have = <String, _Song>{};
    for (final _SetSection o in _set) {
      for (final _Song s in o.songs) {
        if (ids.contains(s.id)) have[s.id] = s;
      }
      if (o != x) o.songs.removeWhere((_Song s) => ids.contains(s.id));
    }
    final List<_Song> extra =
        x.songs.where((_Song s) => !ids.contains(s.id)).toList();
    x.songs
      ..clear()
      ..addAll(starter.map((_Song s) => have[s.id] ?? s))
      ..addAll(extra);
  }

  void _setReset(_SetSection x) {
    if (_sectionDef(x.key).isEmpty) {
      _toast('This section is all yours - there is no Lazo list to go back to.');
      return;
    }
    setState(() => _resetSection(x));
    _scheduleSave();
    _tick(_Tick.medium);
    _toast('${x.label} is back to the Lazo list \u2713');
  }

  Future<void> _setResetAll() async {
    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => AlertDialog(
        backgroundColor: card,
        title: Text('Start over from the Lazo list?', style: _serif(size: 22)),
        content: const Text(
            'Every section goes back to the starter songs, in order. Songs you added yourself stay. Must plays and do-not-plays are not touched.',
            style: TextStyle(fontSize: 13, color: muted)),
        actions: <Widget>[
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Cancel', style: TextStyle(color: muted))),
          FilledButton(
              style: FilledButton.styleFrom(backgroundColor: plum),
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text('Reset')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    setState(() {
      final List<_SetSection> out = <_SetSection>[];
      for (final List<String> d in kSetSections) {
        out.add(_section(d[0]) ?? _freshSection(d, empty: true));
      }
      for (final _SetSection x in _set) {
        if (!out.contains(x)) out.add(x);
      }
      _set
        ..clear()
        ..addAll(out);
      for (final _SetSection x in _set) {
        if (_sectionDef(x.key).isNotEmpty) {
          x.off = false;
          _resetSection(x);
        }
      }
    });
    _scheduleSave();
    _tick(_Tick.medium);
    _toast('Back to the Lazo list \u2713');
  }

  // The first tap on a starter (or typed) song looks it up, keeps the clip
  // on the row, and plays it.
  Future<void> _playSet(_SetSection x, _Song s) async {
    if (s.preview.isNotEmpty) {
      await _togglePlay(s);
      return;
    }
    if (_resolving.contains(s.id)) return;
    setState(() => _resolving.add(s.id));
    _Song? hit;
    try {
      final List<_Song> rs = await _fetchSongs('${s.title} ${s.artist}');
      final String a =
          s.artist.toLowerCase().split(RegExp(r'[ &,]+')).first.trim();
      for (final _Song r in rs) {
        if (r.preview.isEmpty) continue;
        if (a.isEmpty || r.artist.toLowerCase().contains(a)) {
          hit = r;
          break;
        }
      }
      if (hit == null) {
        for (final _Song r in rs) {
          if (r.preview.isNotEmpty) {
            hit = r;
            break;
          }
        }
      }
    } catch (e) {
      debugPrint('LAZO music set lookup: ' + e.toString());
    }
    if (!mounted) return;
    setState(() => _resolving.remove(s.id));
    if (hit == null) {
      _toast('No preview found for ${s.title}.');
      return;
    }
    final _Song n = _Song(
        id: s.id,
        title: s.title,
        artist: s.artist,
        album: hit.album,
        art: hit.art,
        preview: hit.preview,
        ms: hit.ms,
        link: hit.link,
        note: s.note,
        explicit: s.explicit || hit.explicit);
    final int i = x.songs.indexWhere((_Song y) => y.id == s.id);
    if (i >= 0) x.songs[i] = n;
    _scheduleSave();
    await _togglePlay(n);
  }

  void _setSearch(_SetSection x) {
    setState(() {
      _searchSet = x.key;
      _searchFor = '';
      _reqFor = '';
      _tab = 1;
      _searchC.clear();
      _results = <_Song>[];
      _searchErr = '';
    });
  }

  Future<void> _setType(_SetSection x) async {
    final TextEditingController t = TextEditingController();
    final TextEditingController a = TextEditingController();
    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => AlertDialog(
        backgroundColor: card,
        title: Text('Add to ${x.label}', style: _serif(size: 22)),
        content: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
          TextField(
              controller: t,
              autofocus: true,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(labelText: 'Song')),
          TextField(
              controller: a,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(labelText: 'Artist'),
              onSubmitted: (_) => Navigator.of(ctx).pop(true)),
        ]),
        actions: <Widget>[
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Cancel', style: TextStyle(color: muted))),
          FilledButton(
              style: FilledButton.styleFrom(backgroundColor: plum),
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text('Add')),
        ],
      ),
    );
    final String title = t.text.trim();
    final String artist = a.text.trim();
    t.dispose();
    a.dispose();
    if (ok != true || title.isEmpty || !mounted) return;
    _setAdd(
        x.key,
        _Song(
            id: 'typed:${DateTime.now().millisecondsSinceEpoch}',
            title: title,
            artist: artist));
  }

  Future<void> _setMoveSheet(_SetSection x, _Song s) async {
    final String? to = await showDialog<String>(
      context: context,
      builder: (BuildContext ctx) => SimpleDialog(
        backgroundColor: card,
        title: Text('Move ${s.title} to\u2026', style: _serif(size: 20)),
        children: <Widget>[
          for (final _SetSection o in _set)
            if (o != x && !o.skipList)
              SimpleDialogOption(
                onPressed: () => Navigator.of(ctx).pop(o.key),
                child: Text(o.label,
                    style: const TextStyle(
                        color: plum, fontWeight: FontWeight.w700)),
              ),
        ],
      ),
    );
    if (to != null && mounted) _setMove(x, s, to);
  }

  Future<void> _copyLiveLink() async {
    await Clipboard.setData(ClipboardData(text: _liveSetUrl));
    _toast('DJ link copied \u2713');
  }

  // A live copy for the DJ's page (meetlazo.com/w/{slug}/setlist). The site
  // doc's playlist/{doc} is couple-written, worker-read (rules unchanged).
  // Notes stay out: they go to the DJ in the thread, not on a public page.
  Future<void> _mirrorSet() async {
    if (_siteSlug.isEmpty || !_hasAnything) return;
    Map<String, dynamic> lite(_Song s) => <String, dynamic>{
          't': s.title,
          'a': s.artist,
          if (s.explicit) 'c': true,
          if (_inList(_must, s)) 'm': true,
          if (!_isStarter(s) && s.id.isNotEmpty) 'y': true,
        };
    try {
      await FirebaseFirestore.instance
          .collection('weddingSites')
          .doc(_siteSlug)
          .collection('playlist')
          .doc('setlist')
          .set(<String, dynamic>{
        'names': _coupleLabel,
        'date': _weddingDate,
        'moments': <Map<String, dynamic>>[
          for (final List<String> m in _allMoments)
            if (_moments[m[0]] != null)
              <String, dynamic>{
                'label': m[1],
                if (_moments[m[0]]!.time.isNotEmpty)
                  'time': _fmtClock(_moments[m[0]]!.time),
                ...lite(_moments[m[0]]!),
              },
        ],
        'must': _must.map(lite).toList(),
        'dont': _dont.map(lite).toList(),
        'avoid': _avoid,
        'vibe': _vibe.toList(),
        'sections': <Map<String, dynamic>>[
          for (final _SetSection x in _set)
            if (!x.skipList && x.songs.isNotEmpty)
              <String, dynamic>{
                'label': x.label,
                'group': kSetGroups[x.group] ?? '',
                'off': x.off,
                'songs': x.songs.map(lite).toList(),
              },
        ],
        'updatedAt': DateTime.now().toUtc().toIso8601String(),
      });
    } catch (e) {
      debugPrint('LAZO music mirror: ' + e.toString());
    }
  }

  void _toastUndo(String message, VoidCallback undo) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).hideCurrentSnackBar();
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      backgroundColor: plumDeep,
      behavior: SnackBarBehavior.floating,
      duration: const Duration(seconds: 4),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      content: Text(message, style: const TextStyle(color: ivory)),
      action: SnackBarAction(
          label: 'Undo',
          textColor: gold,
          onPressed: () {
            _tick(_Tick.light);
            undo();
          }),
    ));
  }

  // ---------------- search ----------------
""")

# ---------------------------------------------------------------- UI
rep("""  Widget _sectionTitle(String t, String sub, {Widget? trailing}) {
""", r"""  // ---------------- v2.7: set list panel ----------------

  Widget _setPanel() {
    if (_set.isEmpty) {
      return ListView(
          padding: const EdgeInsets.only(bottom: 24),
          children: <Widget>[_setIntro()]);
    }
    final List<Widget> kids = <Widget>[
      _sectionTitle(
          'Your set list',
          '$_setCount songs for your DJ. Tap a section to open it; drag to reorder, swipe to remove.',
          trailing: _setMenu()),
      if (_siteSlug.isNotEmpty) _liveLinkCard(),
    ];
    String group = '\u0000';
    for (final _SetSection x in _set) {
      if (x.group != group) {
        group = x.group;
        kids.add(Padding(
          padding: const EdgeInsets.fromLTRB(4, 16, 4, 6),
          child: Text((kSetGroups[group] ?? 'Your sections').toUpperCase(),
              style: const TextStyle(
                  fontSize: 10.5,
                  letterSpacing: 2,
                  color: plum,
                  fontWeight: FontWeight.w700)),
        ));
      }
      kids.add(Padding(
          padding: const EdgeInsets.only(bottom: 8), child: _setCard(x)));
    }
    return ListView(padding: const EdgeInsets.only(bottom: 24), children: kids);
  }

  Widget _setIntro() {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 18),
      decoration: BoxDecoration(
          gradient: LinearGradient(
              colors: <Color>[gold.withOpacity(.22), card],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: goldLine)),
      child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Icon(Icons.queue_music_rounded, color: plum, size: 28),
            const SizedBox(height: 8),
            Text('Start from the Lazo wedding set list',
                style: _serif(size: 26)),
            const SizedBox(height: 6),
            Text(
                '$_starterPlayable songs the floor already knows, sorted by moment: the aisle, the entrances, first and parent dances, cocktail hour, dinner, and the dance floor by decade. Take out what isn\u2019t you, add your own, put them in order, and send it to your DJ.',
                style: const TextStyle(fontSize: 13, color: muted, height: 1.4)),
            const SizedBox(height: 14),
            Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
              FilledButton.icon(
                style: FilledButton.styleFrom(
                    backgroundColor: plum,
                    foregroundColor: ivory,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 18, vertical: 12)),
                onPressed: () => _seedSet(),
                icon: const Icon(Icons.library_music_rounded, size: 17),
                label: const Text('Load the starter list',
                    style: TextStyle(fontWeight: FontWeight.w800)),
              ),
              OutlinedButton(
                style: OutlinedButton.styleFrom(
                    foregroundColor: plum,
                    side: const BorderSide(color: goldLine),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 18, vertical: 12)),
                onPressed: () => _seedSet(blank: true),
                child: const Text('Start blank',
                    style: TextStyle(fontWeight: FontWeight.w700)),
              ),
            ]),
            const SizedBox(height: 10),
            const Text(
                'Your moments, must plays and do-not-plays stay exactly as they are.',
                style: TextStyle(fontSize: 11.5, color: muted)),
          ]),
    );
  }

  Widget _setMenu() {
    return PopupMenuButton<String>(
      tooltip: 'Set list options',
      icon: const Icon(Icons.more_horiz_rounded, color: plum),
      color: card,
      onSelected: (String v) {
        _tick(_Tick.select);
        if (v == 'open') {
          setState(() => _setOpen.addAll(_set.map((_SetSection x) => x.key)));
        } else if (v == 'close') {
          setState(_setOpen.clear);
        } else if (v == 'reset') {
          _setResetAll();
        } else if (v == 'link') {
          _copyLiveLink();
        }
      },
      itemBuilder: (BuildContext c) => <PopupMenuEntry<String>>[
        const PopupMenuItem<String>(value: 'open', child: Text('Open every section')),
        const PopupMenuItem<String>(value: 'close', child: Text('Close every section')),
        if (_siteSlug.isNotEmpty)
          const PopupMenuItem<String>(value: 'link', child: Text('Copy the DJ link')),
        const PopupMenuItem<String>(
            value: 'reset', child: Text('Reset everything to the Lazo list')),
      ],
    );
  }

  Widget _liveLinkCard() {
    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
      decoration: _panelDeco,
      child: Row(children: <Widget>[
        const Icon(Icons.link_rounded, color: plum, size: 18),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const Text('Live link for your DJ',
                    style: TextStyle(
                        color: ink, fontSize: 13, fontWeight: FontWeight.w800)),
                Text('meetlazo.com/w/$_siteSlug/setlist \u00b7 always current',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11.5, color: muted)),
              ]),
        ),
        TextButton(
            onPressed: _h(_copyLiveLink),
            child: const Text('Copy',
                style: TextStyle(color: plum, fontWeight: FontWeight.w800))),
      ]),
    );
  }

  Widget _pill(String t, Color c) => Container(
        margin: const EdgeInsets.only(left: 6),
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 1),
        decoration: BoxDecoration(
            color: c.withOpacity(.14), borderRadius: BorderRadius.circular(999)),
        child: Text(t,
            style: TextStyle(
                fontSize: 9.5, color: c, fontWeight: FontWeight.w800)),
      );

  Widget _setCard(_SetSection x) {
    final bool open = _setOpen.contains(x.key);
    final String peek =
        x.songs.take(3).map((_Song s) => s.title).join(' \u00b7 ');
    return Container(
      decoration: BoxDecoration(
          color: x.off ? ivory : card,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: goldLine)),
      clipBehavior: Clip.antiAlias,
      child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () {
                _tick(_Tick.select);
                setState(() =>
                    open ? _setOpen.remove(x.key) : _setOpen.add(x.key));
              },
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 10, 2, 10),
                child: Row(children: <Widget>[
                  Expanded(
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Row(children: <Widget>[
                            Flexible(
                                child: Text(x.label,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: _serif(
                                        size: 19,
                                        color: x.off ? muted : plum))),
                            _pill('${x.songs.length}', x.off ? muted : plum),
                            if (x.off) _pill('skipping', rose),
                          ]),
                          if (!open && peek.isNotEmpty)
                            Text(peek,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                    fontSize: 11.5, color: muted)),
                          if (!open && peek.isEmpty)
                            const Text('Empty - add a song',
                                style: TextStyle(fontSize: 11.5, color: muted)),
                          if (open && x.skipList)
                            const Text(
                                'Songs couples often ban. Tap Don\u2019t play on any you agree with.',
                                style: TextStyle(fontSize: 11.5, color: muted)),
                          if (open && x.off)
                            const Text(
                                'Your DJ will see this section marked skip.',
                                style: TextStyle(fontSize: 11.5, color: rose)),
                        ]),
                  ),
                  _sectionMenu(x),
                  Icon(
                      open
                          ? Icons.expand_less_rounded
                          : Icons.expand_more_rounded,
                      color: muted),
                  const SizedBox(width: 6),
                ]),
              ),
            ),
            if (open) ...<Widget>[
              if (x.songs.isNotEmpty) _setRows(x),
              Padding(
                padding: const EdgeInsets.fromLTRB(6, 2, 6, 6),
                child: Wrap(children: <Widget>[
                  TextButton.icon(
                      onPressed: _h(() => _setSearch(x)),
                      icon: const Icon(Icons.search_rounded,
                          color: plum, size: 16),
                      label: const Text('Find a song',
                          style: TextStyle(
                              color: plum,
                              fontSize: 12,
                              fontWeight: FontWeight.w800))),
                  TextButton.icon(
                      onPressed: _h(() => _setType(x)),
                      icon: const Icon(Icons.edit_rounded,
                          color: plum, size: 15),
                      label: const Text('Type one in',
                          style: TextStyle(
                              color: plum,
                              fontSize: 12,
                              fontWeight: FontWeight.w800))),
                ]),
              ),
            ],
          ]),
    );
  }

  Widget _sectionMenu(_SetSection x) {
    final bool canReset = _sectionDef(x.key).isNotEmpty;
    return PopupMenuButton<String>(
      tooltip: 'Section options',
      icon: const Icon(Icons.more_vert_rounded, color: muted, size: 19),
      color: card,
      onSelected: (String v) {
        _tick(_Tick.select);
        if (v == 'find') {
          _setSearch(x);
        } else if (v == 'type') {
          _setType(x);
        } else if (v == 'off') {
          setState(() => x.off = !x.off);
          _scheduleSave();
        } else if (v == 'reset') {
          _setReset(x);
        }
      },
      itemBuilder: (BuildContext c) => <PopupMenuEntry<String>>[
        const PopupMenuItem<String>(value: 'find', child: Text('Find a song')),
        const PopupMenuItem<String>(value: 'type', child: Text('Type one in')),
        if (!x.skipList)
          PopupMenuItem<String>(
              value: 'off',
              child: Text(x.off
                  ? 'Play this section again'
                  : 'We\u2019re skipping this')),
        if (canReset)
          const PopupMenuItem<String>(
              value: 'reset', child: Text('Reset to the Lazo list')),
      ],
    );
  }

  Widget _setRows(_SetSection x) {
    return ReorderableListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      buildDefaultDragHandles: false,
      itemCount: x.songs.length,
      onReorderStart: (int _) => _tick(_Tick.medium),
      proxyDecorator: (Widget child, int i, Animation<double> a) =>
          AnimatedBuilder(
        animation: a,
        builder: (BuildContext c, Widget? w) {
          final double t = Curves.easeOut.transform(a.value);
          return Transform.scale(
            scale: 1 + .02 * t,
            child: Material(
              color: card,
              elevation: 10 * t,
              shadowColor: plumDeep.withOpacity(.4),
              borderRadius: BorderRadius.circular(12),
              child: w,
            ),
          );
        },
        child: child,
      ),
      onReorder: (int a, int b) {
        _tick(_Tick.select);
        setState(() {
          if (b > a) b--;
          final _Song s = x.songs.removeAt(a);
          x.songs.insert(b, s);
        });
        _scheduleSave();
      },
      itemBuilder: (BuildContext c, int i) {
        final _Song s = x.songs[i];
        final Key k = ValueKey<String>('set:${x.key}:${s.id}');
        return Dismissible(
          key: k,
          direction: DismissDirection.endToStart,
          background: Container(
            alignment: Alignment.centerRight,
            padding: const EdgeInsets.only(right: 18),
            color: rose.withOpacity(.12),
            child: const Icon(Icons.delete_outline_rounded, color: rose),
          ),
          onDismissed: (DismissDirection _) => _setRemove(x, s),
          child: _setRow(x, s, i),
        );
      },
    );
  }

  Widget _setRow(_SetSection x, _Song s, int i) {
    final bool me = _playingId == s.id;
    final bool must = _inList(_must, s);
    final String where = _whereIs(s);
    final bool busy = _resolving.contains(s.id);
    return Container(
      padding: const EdgeInsets.fromLTRB(2, 6, 2, 6),
      decoration: BoxDecoration(
          color: me ? gold.withOpacity(.1) : Colors.transparent,
          border: Border(top: BorderSide(color: goldLine.withOpacity(.6)))),
      child: Row(children: <Widget>[
        ReorderableDragStartListener(
          index: i,
          child: const MouseRegion(
              cursor: SystemMouseCursors.grab,
              child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: 6, vertical: 6),
                  child: Icon(Icons.drag_indicator_rounded,
                      color: muted, size: 18))),
        ),
        Expanded(
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(children: <Widget>[
                  Flexible(
                      child: Text(s.title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                              color: x.off ? muted : ink,
                              fontSize: 13.5,
                              fontWeight: FontWeight.w700))),
                  if (s.explicit) _explicitTag(),
                  if (!_isStarter(s)) _pill('yours', amber),
                ]),
                Text(s.artist,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11.5, color: muted)),
                if (where.isNotEmpty && where != 'Must play')
                  Text(where,
                      style: TextStyle(
                          fontSize: 10.5,
                          color: where == 'Do not play' ? rose : vGreen,
                          fontWeight: FontWeight.w800)),
                if (s.note.isNotEmpty)
                  Text(s.note,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          fontSize: 11,
                          color: amber,
                          fontStyle: FontStyle.italic)),
              ]),
        ),
        busy
            ? const SizedBox(
                width: 30,
                height: 30,
                child: Padding(
                    padding: EdgeInsets.all(7),
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: plum)))
            : _playBtn(s, size: 30, onTap: () => _playSet(x, s)),
        if (x.skipList)
          TextButton(
              onPressed: where == 'Do not play'
                  ? null
                  : _h(() => _setDont(x, s), _Tick.none),
              child: Text(where == 'Do not play' ? 'Banned' : 'Don\u2019t play',
                  style: TextStyle(
                      color: where == 'Do not play' ? muted : rose,
                      fontSize: 12,
                      fontWeight: FontWeight.w800)))
        else
          IconButton(
              tooltip: must ? 'Must play - tap to undo' : 'Must play',
              onPressed: _h(() => _setToggleMust(s), _Tick.none),
              icon: Icon(must ? Icons.star_rounded : Icons.star_border_rounded,
                  color: must ? gold : muted, size: 21),
              visualDensity: VisualDensity.compact),
        _rowMenu(x, s),
      ]),
    );
  }

  Widget _rowMenu(_SetSection x, _Song s) {
    return PopupMenuButton<String>(
      tooltip: 'More',
      icon: const Icon(Icons.more_vert_rounded, color: muted, size: 18),
      color: card,
      padding: EdgeInsets.zero,
      onSelected: (String v) {
        _tick(_Tick.select);
        if (v == 'moment') {
          _setMoment(x.moment, s);
        } else if (v == 'file') {
          _searchSet = '';
          _fileSong(s);
        } else if (v == 'dont') {
          _setDont(x, s);
        } else if (v == 'move') {
          _setMoveSheet(x, s);
        } else if (v == 'note') {
          _editNote(s);
        } else if (v == 'remove') {
          _setRemove(x, s);
        }
      },
      itemBuilder: (BuildContext c) => <PopupMenuEntry<String>>[
        if (x.moment.isNotEmpty)
          PopupMenuItem<String>(
              value: 'moment',
              child: Text('Use for ${_momentLabel(x.moment)}')),
        const PopupMenuItem<String>(
            value: 'file', child: Text('Set as another moment\u2026')),
        if (!x.skipList)
          const PopupMenuItem<String>(value: 'move', child: Text('Move to\u2026')),
        const PopupMenuItem<String>(value: 'note', child: Text('Note for the DJ')),
        if (!x.skipList)
          const PopupMenuItem<String>(value: 'dont', child: Text('Don\u2019t play')),
        const PopupMenuItem<String>(value: 'remove', child: Text('Remove')),
      ],
    );
  }

  Widget _sectionTitle(String t, String sub, {Widget? trailing}) {
""")

DST.write_text(s, encoding="utf-8", newline="\n")
b = s.count("{") - s.count("}")
p = s.count("(") - s.count(")")
print(f"wrote {DST.name}: {len(s):,} chars; {play} songs to play + "
      f"{len(seen) - play} to skip in {len(SECTIONS)} sections; "
      f"brace balance {b}, paren balance {p}")

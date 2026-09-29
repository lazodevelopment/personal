"""_mock_now.py - JC-LAZO-WWS-0929-SHOTS
Builds _preview/sage-now.html for screenshots: the Sage preview on its wedding
day with the clock pinned to 5:40 pm (so the hour-by-hour list marks Now and
Next), reveal animations forced on, and mocked answers for the seat finder,
the guest wall, the forecast and a personal RSVP link. A ?shot=<selector>
query shifts that section to the top for a headless capture; ?seat=Rosa fills
the seat finder; ?lang=es picks a language.

  python wedding-websites\\_preview.py sage && python wedding-websites\\_mock_now.py
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SLUG = sys.argv[1] if len(sys.argv) > 1 else "sage"
src = (ROOT / "_preview" / f"{SLUG}.html").read_text(encoding="utf-8")
U = "https://images.unsplash.com/photo-"
tl = [{"time": "16:00", "label": "Guests arrive", "note": "Cold drinks on the porch", "dur": 30},
      {"time": "16:30", "label": "Ceremony", "note": "", "dur": 30},
      {"time": "17:15", "label": "Cocktail hour", "note": "Oysters, a string trio, the lawn", "dur": 75},
      {"time": "18:30", "label": "Dinner", "note": "", "dur": 90},
      {"time": "20:00", "label": "First dance, then everyone", "note": "", "dur": 150},
      {"time": "22:30", "label": "Send-off", "note": "Sparklers by the barn", "dur": 15}]
photos = [("1519741497674-611481863552", "Aunt Rosa", "first dance"), ("1522673607200-164d1b6ce486", "The Nguyens", ""),
          ("1511285560929-80b456fea0bc", "Table 7", "sparklers!"), ("1465495976277-4387d4b0b4c6", "Dev", ""),
          ("1460978812857-470ed1c77af0", "Priya", "the cake"), ("1529636798458-92182e662485", "Marco", "")]
wall = {"ok": True, "on": True, "hold": False, "count": len(photos), "photos": [
    {"id": f"0mum{i:011d}", "name": n, "caption": c, "at": "", "url": f"{U}{p}?auto=format&fit=crop&w=1200&q=74"}
    for i, (p, n, c) in enumerate(photos)]}
seating = {"fields": {
    "guests": {"arrayValue": {"values": [
        {"mapValue": {"fields": {"n": {"stringValue": nm}, "p": {"stringValue": ""}, "t": {"stringValue": t}, "s": {"integerValue": str(i)}}}}
        for i, (nm, t) in enumerate([("Rosa Alvarez", "Table 7"), ("Miguel Alvarez", "Table 7"), ("Dev Patel", "Table 7"),
                                     ("Priya Patel", "Table 7"), ("Hannah Nguyen", "Table 3"), ("Marco Rossi", "Table 3"), ("June Park", "Table 5")])]}},
    "tables": {"arrayValue": {"values": [
        {"mapValue": {"fields": {"n": {"stringValue": f"Table {k}"}, "x": {"doubleValue": x}, "y": {"doubleValue": y},
                                 "sh": {"stringValue": "round"}, "r": {"doubleValue": 0}, "s": {"integerValue": "8"}}}}
        for k, (x, y) in {1: (300, 300), 2: (600, 300), 3: (900, 300), 4: (1200, 300), 5: (300, 620), 6: (600, 620), 7: (900, 620), 8: (1200, 620)}.items()]}},
    "canvas": {"mapValue": {"fields": {"w": {"integerValue": "1500"}, "h": {"integerValue": "900"}}}}}}
weather = {"ok": True, "day": {"hi": 76, "lo": 58, "rain": 10, "code": 1, "sky": "mostly clear", "sunset": "18:12", "line": "Bring a layer for the evening."}}
invite = {"fields": {"name": {"stringValue": "Rosa Alvarez"}, "party": {"stringValue": "Rosa & Miguel Alvarez"}, "plusOnes": {"integerValue": "1"},
                     "meals": {"arrayValue": {"values": [{"stringValue": "Chicken"}, {"stringValue": "Salmon"}, {"stringValue": "Garden risotto"}]}}}}

clock = """<script>(function(){var R=Date;var d0=new R();var iso=d0.getFullYear()+"-"+String(d0.getMonth()+1).padStart(2,"0")+"-"+String(d0.getDate()).padStart(2,"0");var FIX=new R(iso+"T17:40:00").getTime();window.__ISO=iso;
function D(){if(arguments.length===0)return new R(FIX);return new (Function.prototype.bind.apply(R,[null].concat([].slice.call(arguments))))}
D.prototype=R.prototype;D.now=function(){return FIX};D.parse=R.parse;D.UTC=R.UTC;window.Date=D;})();</script>"""
mock = ("<script>(function(){var LS=window.LAZO_SITE;LS.dateIso=window.__ISO;LS.timeline=%s;var W=%s,S=%s,X=%s,I=%s;var f=window.fetch;"
        "window.fetch=function(u,o){var s=String(u);var j=function(b){return Promise.resolve(new Response(JSON.stringify(b),{status:200,headers:{'content-type':'application/json'}}))};"
        "if(s.indexOf('/photos')>0&&(!o||o.method!=='POST'))return j(W);if(s.indexOf('/seating/main')>0)return j(S);if(s.indexOf('/weather')>0)return j(X);if(s.indexOf('/invites/')>0)return j(I);return f.apply(this,arguments)};})();</script>"
        % (json.dumps(tl), json.dumps(wall), json.dumps(seating), json.dumps(weather), json.dumps(invite)))
css = "<style>.rv{opacity:1!important;transform:none!important;transition:none!important}.hero-full .hph{animation:none!important}[data-lzf]{opacity:1!important}</style>"
drive = """<script>window.addEventListener("load",function(){var q=new URLSearchParams(location.search);
 var seat=q.get("seat");if(seat){var i=document.getElementById("seatq");if(i){i.value=seat;i.dispatchEvent(new Event("input"))}}
 var lang=q.get("lang");if(lang){var sel=document.querySelector(".lzlang select");if(sel){sel.value=lang;sel.dispatchEvent(new Event("change"))}}
 var shot=q.get("shot");if(shot){setTimeout(function(){var el=document.querySelector(shot);if(el){var y=el.getBoundingClientRect().top+window.scrollY-(parseInt(q.get("off")||"40",10));document.body.style.marginTop=(-y)+"px";document.body.style.paddingTop="0";document.querySelectorAll(".lzlang,.junebtn,.lzsong,.lzplayer").forEach(function(n){n.style.display="none"})}},parseInt(q.get("delay")||"1800",10))}
});</script>"""
s = src.replace("<head>", "<head>\n" + clock, 1).replace("</head>", mock + "\n" + css + "\n" + drive + "\n</head>", 1)
out = ROOT / "_preview" / f"{SLUG}-now.html"
out.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {out.relative_to(ROOT)}")

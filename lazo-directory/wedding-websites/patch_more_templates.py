"""patch_more_templates.py - JC-LAZO-WWS-0929-MORE
More for the couple site, one tagged script + CSS, replaced on re-runs:
  1. THE WHOLE DAY IN A CALENDAR  under the hour-by-hour list: an .ics with
     every moment as its own event, and a Google Calendar link for the ceremony.
  2. THE WEEKEND  weddingSites.events [{name, dateIso, time, venueName,
     venueAddress, note, dress, rsvp}] as cards (mehndi, sangeet, welcome
     dinner, brunch...) with directions and add-to-calendar; events with rsvp
     add "Which will you join?" checkboxes to the RSVP form; the reply carries
     `events`.
  3. THE HOTEL  weddingSites.hotelAddress adds "Directions to the hotel" to the
     travel card.
  4. YOUR TABLE ON THE MAP  when seating/main carries the tables and canvas,
     the seat finder draws the room and marks the guest's table.
  5. THE HOLD  (in patch_photos_templates.py) an upload the couple must approve
     says so instead of appearing on the wall.

  python wedding-websites\\patch_more_templates.py            # base + 20
  python wedding-websites\\patch_more_templates.py sage tide  # some
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ["sage", "noir", "dune", "fete", "tide", "flora", "atelier", "verona", "shore", "summit",
        "ranch", "starlit", "frost", "harvest", "aquarelle", "prism", "meadow", "gilded", "marigold", "papel"]
TAG = "JC-LAZO-WWS-0929-MORE"

CSS = """
/* ---- JC-LAZO-WWS-0929-MORE: calendar, the weekend, the hotel, the table map ---- */
.tlcal{text-align:center;margin-top:18px}.tlcal a{margin:0 8px}
.evg{display:grid;gap:18px;margin-top:clamp(26px,3.4vw,42px)}
@media(min-width:760px){.evg{grid-template-columns:1fr 1fr}}
.ev{background:var(--panel);border:1px solid var(--line);padding:24px 24px 20px}
.ev .k{margin-bottom:6px}.ev h3{font-size:24px;margin-bottom:4px}.ev p{font-size:15px}.ev .dim{color:var(--mut);font-size:13.5px;margin-top:3px}
.ev .evl{margin-top:12px;display:flex;gap:16px;flex-wrap:wrap}.ev .evl a{font-size:12px;letter-spacing:.14em;text-transform:uppercase;text-decoration:none;border-bottom:1px solid currentColor;padding-bottom:2px;color:inherit;opacity:.85}
.evs{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.evs label{border:1px solid var(--line);padding:10px 12px;font-size:13px;cursor:pointer;display:inline-flex;gap:8px;align-items:center}
.evs label:has(input:checked){border-color:var(--acc);color:var(--acc)}
.seatmap{margin-top:12px;background:var(--bg);border:1px solid var(--line)}
.seatmap svg{width:100%;height:auto;display:block}
/* ---- /JC-LAZO-WWS-0929-MORE ---- */
"""

JS = r"""
<script>
/* JC-LAZO-WWS-0929-MORE: the day in a calendar, the weekend's events, the hotel, your table on the map */
(function(){
 var LS=window.LAZO_SITE;if(!LS||document.body.classList.contains("framed"))return;
 /* the LIVE block builds #tlx, .seatr and the travel card; whichever order the
    patches were applied in, this runs after it */
 if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",arguments.callee);return}
 var esc=function(t){return String(t||"").replace(/[<>&"]/g,function(c){return{"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"}[c]})};
 var iso=LS.dateIso||"",hasDate=/^\d{4}-\d{2}-\d{2}$/.test(iso);
 var hhmm=function(t){var m=/^(\d{1,2}):(\d{2})/.exec(t||"");if(!m)return null;return parseInt(m[1],10)*60+parseInt(m[2],10)};
 var parse12=function(t){var m=/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i.exec(t||"");if(!m)return null;var h=parseInt(m[1],10),mi=m[2]?parseInt(m[2],10):0;if(m[3]){var pm=m[3].toLowerCase()==="pm";if(pm&&h<12)h+=12;if(!pm&&h===12)h=0}return h*60+mi};
 var p2=function(n){return String(n).padStart(2,"0")};
 var stamp=function(d,mins){return d.replace(/-/g,"")+"T"+p2(Math.floor(mins/60)%24)+p2(mins%60)+"00"};
 var icsWrap=function(events){return ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Lazo//Wedding//EN"].concat(events).concat(["END:VCALENDAR"]).join("\r\n")};
 var vevent=function(uid,d,start,end,title,loc,desc){return ["BEGIN:VEVENT","UID:"+uid+"@meetlazo.com","DTSTAMP:"+new Date().toISOString().replace(/[-:]/g,"").replace(/\.\d+Z$/,"Z"),"DTSTART:"+stamp(d,start),"DTEND:"+stamp(d,end),"SUMMARY:"+String(title).replace(/,/g,"\\,"),"LOCATION:"+String(loc||"").replace(/,/g,"\\,"),"DESCRIPTION:"+String(desc||"").replace(/,/g,"\\,").replace(/\n/g,"\\n"),"END:VEVENT"].join("\r\n")};
 var dl=function(a,name,ics){a.href="data:text/calendar;charset=utf-8,"+encodeURIComponent(ics);a.download=name;a.className="addcal";};
 var gcal=function(title,d,start,end,loc){return "https://calendar.google.com/calendar/render?action=TEMPLATE&text="+encodeURIComponent(title)+"&dates="+stamp(d,start)+"/"+stamp(d,end)+"&location="+encodeURIComponent(loc||"")};
 var venue=[LS.venueName,LS.venueAddress].filter(Boolean).join(", ");

 /* ---- 1. the whole day in a calendar ---- */
 var tlx=document.getElementById("tlx");
 if(tlx&&hasDate&&LS.timeline&&LS.timeline.length){
  var evs=LS.timeline.filter(function(m){return m&&m.label&&hhmm(m.time)!==null}).map(function(m,i){var st=hhmm(m.time),en=st+(m.dur>0?m.dur:60);return vevent("lazo-"+(LS.slug||"w")+"-"+i,iso,st,Math.min(en,23*60+59),m.label,venue,m.note||"")});
  var wrap=document.createElement("p");wrap.className="tlcal";
  var a=document.createElement("a");dl(a,(LS.slug||"wedding")+"-day.ics",icsWrap(evs));a.textContent="Add the whole day to your calendar";wrap.appendChild(a);
  var cer=parse12(LS.ceremonyTime||"");if(cer!==null){var g=document.createElement("a");g.className="addcal";g.href=gcal((LS.names||"Wedding")+" \u2014 ceremony",iso,cer,Math.min(cer+300,23*60+59),venue);g.target="_blank";g.rel="noopener";g.textContent="Google Calendar";wrap.appendChild(g)}
  tlx.parentNode.insertBefore(wrap,tlx.nextSibling);
 }

 /* ---- 2. the weekend ---- */
 var events=(LS.events||[]).filter(function(e){return e&&e.name});
 if(events.length){
  var s=document.createElement("section");s.className="evsec";s.id="events";
  s.innerHTML='<div class="wrap"><div class="center"><p class="k">The weekend</p><h2 style="margin:0 auto">More than one day to celebrate.</h2></div><div class="evg"></div></div>';
  var grid=s.querySelector(".evg");
  events.forEach(function(e,i){
   var c=document.createElement("div");c.className="ev";
   var when=e.dateIso?new Date(e.dateIso+"T12:00:00").toLocaleDateString("en-US",{weekday:"long",month:"long",day:"numeric"}):"";
   c.innerHTML='<p class="k"></p><h3></h3><p></p><p class="dim"></p><div class="evl"></div>';
   c.querySelector(".k").textContent=when+(e.time?" \u00b7 "+e.time:"");
   c.querySelector("h3").textContent=e.name;
   c.querySelectorAll("p")[1].textContent=[e.venueName,e.venueAddress].filter(Boolean).join(", ");
   c.querySelector(".dim").textContent=[e.note,e.dress?"Dress: "+e.dress:""].filter(Boolean).join(" \u00b7 ");
   var links=c.querySelector(".evl");
   var loc=[e.venueName,e.venueAddress].filter(Boolean).join(", ");
   if(loc){var d=document.createElement("a");d.href="https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(loc);d.target="_blank";d.rel="noopener";d.textContent="Directions";links.appendChild(d)}
   if(e.dateIso){var st=parse12(e.time||"");if(st===null)st=18*60;var ca=document.createElement("a");dl(ca,(LS.slug||"wedding")+"-"+(i+1)+".ics",icsWrap([vevent("lazo-"+(LS.slug||"w")+"-ev"+i,e.dateIso,st,Math.min(st+180,23*60+59),e.name+" \u2014 "+(LS.names||""),loc,e.note||"")]));ca.textContent="Add to calendar";links.appendChild(ca)}
   grid.appendChild(c);
  });
  var day=document.querySelector(".dayg");day=day?day.closest("section"):null;
  var story=document.querySelector(".split");story=story?story.closest("section"):null;
  var anchor=day||document.getElementById("rsvpSec");
  if(anchor)anchor.parentNode.insertBefore(s,anchor);else if(story)story.parentNode.insertBefore(s,story.nextSibling);
  // RSVP: which events?
  var rform=document.getElementById("rform"),ask=events.filter(function(e){return e.rsvp});
  if(rform&&ask.length&&LS.rsvpOpen!==false){
   var box=document.createElement("div");box.className="evs";box.innerHTML='<span class="mealk">Which will you join?</span>';
   ask.forEach(function(e){var l=document.createElement("label");var cb=document.createElement("input");cb.type="checkbox";cb.name="ev";cb.value=e.name;cb.checked=true;var t=document.createElement("span");t.textContent=e.name;l.appendChild(cb);l.appendChild(t);box.appendChild(l)});
   var at=rform.querySelector(".plusrow")||rform.querySelector(".meals")||rform.querySelector("[data-song]")||rform.querySelector("textarea");
   rform.insertBefore(box,at);
   var _f=window.fetch;
   window.fetch=function(u,o){try{if(typeof u==="string"&&u.indexOf("/rsvps")>0&&o&&o.method==="POST"){var b=JSON.parse(o.body);var picked=[].slice.call(rform.querySelectorAll("input[name=ev]:checked")).map(function(c){return{stringValue:c.value.slice(0,80)}});b.fields.events={arrayValue:{values:picked}};o.body=JSON.stringify(b)}}catch(_){}return _f.apply(this,arguments)};
  }
 }

 /* ---- 3. the hotel ---- */
 if(LS.hotelAddress){
  var vens=document.querySelectorAll(".ven");var tv=vens[1];
  if(tv&&tv.style.display!=="none"){var h=document.createElement("a");h.className="addcal";h.href="https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(LS.hotelAddress);h.target="_blank";h.rel="noopener";h.textContent="Directions to the hotel";tv.appendChild(h)}
 }

 /* ---- 4. your table on the map ---- */
 var seatr=document.getElementById("seatr");
 if(seatr){
  var FSB="https://firestore.googleapis.com/v1/projects/lazo-513ec/databases/(default)/documents/weddingSites/"+encodeURIComponent(LS.slug)+"/seating/main";
  var roomP=null;
  var room=function(){if(roomP)return roomP;roomP=fetch(FSB).then(function(r){return r.json()}).then(function(j){var f=j&&j.fields;if(!f||!f.tables)return null;var num=function(v){return v?Number(v.doubleValue!=null?v.doubleValue:v.integerValue):0};var cv=(f.canvas&&f.canvas.mapValue&&f.canvas.mapValue.fields)||{};
   return{w:num(cv.w)||1600,h:num(cv.h)||1000,tables:((f.tables.arrayValue||{}).values||[]).map(function(v){var m=(v.mapValue||{}).fields||{};return{n:(m.n||{}).stringValue||"",x:num(m.x),y:num(m.y),sh:(m.sh||{}).stringValue||"round",r:num(m.r),s:num(m.s)||8}})}}).catch(function(){return null});return roomP};
  new MutationObserver(function(){
   var cards=seatr.querySelectorAll(".seatc");if(!cards.length)return;
   room().then(function(R){
    if(!R||!R.tables.length)return;
    cards.forEach(function(c){
     if(c.querySelector(".seatmap"))return;
     var t=(c.querySelector(".seatt")||{}).textContent||"";var tn=t.split(" \u00b7 ")[0].trim();if(!tn)return;
     var mine=R.tables.filter(function(x){return x.n===tn});if(!mine.length)return;
     var sv='<svg viewBox="0 0 '+R.w+' '+R.h+'" role="img" aria-label="Your table on the floor plan">';
     R.tables.forEach(function(x){var hit=x.n===tn;var fill=hit?"var(--acc)":"var(--line)";var lab=hit?"#fff":"var(--mut)";
      if(x.sh==="round")sv+='<circle cx="'+x.x+'" cy="'+x.y+'" r="42" fill="'+fill+'"/>';
      else{var w=x.sh==="rect"?110:x.sh==="king"||x.sh==="serp"?260:160,h2=x.sh==="rect"?60:50;sv+='<rect x="'+(x.x-w/2)+'" y="'+(x.y-h2/2)+'" width="'+w+'" height="'+h2+'" rx="10" fill="'+fill+'" transform="rotate('+(x.r||0)+' '+x.x+' '+x.y+')"/>'}
      sv+='<text x="'+x.x+'" y="'+(x.y+6)+'" text-anchor="middle" font-size="'+(hit?26:20)+'" font-weight="'+(hit?700:400)+'" fill="'+lab+'">'+esc(x.n.replace(/^Table\s+/i,""))+'</text>'});
     sv+='</svg>';
     var box=document.createElement("div");box.className="seatmap";box.innerHTML=sv;c.appendChild(box);
    });
   });
  }).observe(seatr,{childList:true});
 }
})();
</script>
"""


def strip(s):
    s = re.sub(rf"\n/\* ---- {TAG}:.*?/\* ---- /{TAG} ---- \*/\n", "\n", s, flags=re.S)
    s = re.sub(rf"\n<script>\n/\* {TAG}:.*?</script>\n", "\n", s, flags=re.S)
    return s


def patch(path):
    s = strip(path.read_text(encoding="utf-8"))
    k = s.find("</style>")
    if k < 0:
        raise SystemExit(f"{path}: no <style>")
    s = s[:k] + CSS + s[k:]
    k = s.rfind("</body>")
    s = s[:k] + JS + s[k:]
    path.write_text(s, encoding="utf-8", newline="\n")
    print(f"  {path.relative_to(ROOT)}: more ({len(s):,} bytes)")


if __name__ == "__main__":
    names = sys.argv[1:] or LIVE
    if not sys.argv[1:]:
        patch(ROOT / "_base.html")
    for n in names:
        p = ROOT / n / "index.html"
        if not p.exists():
            raise SystemExit(f"no template {n}")
        patch(p)

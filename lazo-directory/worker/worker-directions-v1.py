# JC-LAZO-WORKER-0913-DIRECTIONS-001
# Run from C:\Users\kurvh\lazo-directory\worker:   python worker-directions-v1.py
# Then:  npx wrangler deploy
#
# Every couple site at /w/{slug} gets tap-to-navigate on the venue, without
# touching the eight templates: the worker appends a small script before
# </body> that
#   - builds a directions link from window.LAZO_SITE.venueAddress (falling
#     back to venueName): Apple Maps on iPhone/iPad, the Android navigation
#     intent on Android, Google Maps everywhere else - each opens the phone's
#     own navigation app straight into directions
#   - finds the address wherever the template rendered it (it waits for the
#     template's own hydration), turns that element into a link, and drops a
#     "Get directions" pill right under it
#   - exposes window.lazoDirections() so a template can add its own button
# Requires PAY-001 (restore) already applied.
import io, sys, shutil

p = "src/index.js"
s = io.open(p, encoding="utf-8").read()
if "DIRECTIONS-001" in s:
    sys.exit("already patched")
if "PAY-001" not in s:
    sys.exit("run worker-restore-v1.py first")

old = '''  html = html.replace(/<title>[^<]*<\\/title>/, `<title>${esc(title)}</title>`);
  html = html.replace("</head>", og + inject + "\\n</head>");

  const headers = {
    "content-type": TYPES.html,
    "cache-control": "public, max-age=60, s-maxage=120",'''
new = '''  html = html.replace(/<title>[^<]*<\\/title>/, `<title>${esc(title)}</title>`);
  html = html.replace("</head>", og + inject + "\\n</head>");
  // DIRECTIONS-001: tap the venue, open the phone's navigation
  html = html.replace(/<\\/body>/i, DIRECTIONS_JS + "\\n</body>");

  const headers = {
    "content-type": TYPES.html,
    "cache-control": "public, max-age=60, s-maxage=120",'''
if old not in s:
    sys.exit("renderCoupleSite head/headers anchor not found")
s = s.replace(old, new, 1)

fn = r'''
// JC-LAZO-WORKER-0913-DIRECTIONS-001 --------------------------------------
const DIRECTIONS_JS = `<script>(function(){
var S=window.LAZO_SITE||{};var addr=(S.venueAddress||"").trim(),name=(S.venueName||"").trim();var q=addr||name;if(!q)return;
var ua=navigator.userAgent||"";var ios=/iPad|iPhone|iPod/.test(ua)||(navigator.platform==="MacIntel"&&navigator.maxTouchPoints>1);var android=/Android/i.test(ua);
var enc=encodeURIComponent(q);
var url=ios?"maps://?daddr="+enc+"&dirflg=d":android?"google.navigation:q="+enc:"https://www.google.com/maps/dir/?api=1&destination="+enc;
var web="https://www.google.com/maps/dir/?api=1&destination="+enc;
function go(e){if(e)e.preventDefault();var t=Date.now();window.location.href=url;
 if(ios||android){setTimeout(function(){if(Date.now()-t<1500&&!document.hidden)window.location.href=web;},1200);}}
window.lazoDirections=go;
var done=false;
function norm(t){return (t||"").replace(/\\s+/g," ").trim().toLowerCase();}
function findAddr(){var want=norm(addr||name);if(!want)return null;
 var walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null);var n,best=null;
 while((n=walker.nextNode())){var tx=norm(n.nodeValue);if(!tx||tx.length>200)continue;if(tx===want||(tx.indexOf(want)>=0&&tx.length<want.length+40)){best=n;break;}}
 if(!best&&addr&&name){var w2=norm(name);walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null);while((n=walker.nextNode())){var t2=norm(n.nodeValue);if(t2===w2){best=n;break;}}}
 return best?best.parentElement:null;}
function inject(){if(done)return;var el=findAddr();if(!el)return;if(el.closest("a"))el=el.closest("a");done=true;
 el.style.cursor="pointer";el.setAttribute("role","link");el.setAttribute("aria-label","Get directions to "+q);el.addEventListener("click",go);
 var css=getComputedStyle(el);
 var b=document.createElement("a");b.href=web;b.className="lazo-directions";b.setAttribute("aria-label","Get directions");
 b.innerHTML='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:6px"><path d="M12 2l9 9-9 9-9-9z"/><path d="M9.5 12.5h4l-1.5 1.5"/><path d="M13.5 12.5l-1.5-1.5"/></svg>Get directions';
 b.style.cssText="display:inline-flex;align-items:center;margin-top:10px;padding:8px 14px;border-radius:999px;font:600 13px/1 -apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif;letter-spacing:.2px;text-decoration:none;color:"+css.color+";border:1.5px solid currentColor;opacity:.92";
 b.addEventListener("click",go);
 var host=el.tagName==="A"?el:el;var block=host.closest("p,div,li,address,section")||host;
 if(block&&block!==host&&block.children.length<=3){block.appendChild(document.createElement("br"));block.appendChild(b);}else{host.insertAdjacentElement("afterend",b);}}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",inject);else inject();
var tries=0;var iv=setInterval(function(){inject();if(done||++tries>40)clearInterval(iv);},250);
if(window.MutationObserver){var mo=new MutationObserver(function(){inject();if(done)mo.disconnect();});mo.observe(document.documentElement,{childList:true,subtree:true,characterData:true});setTimeout(function(){mo.disconnect();},15000);}
})();</script>`;
'''
shutil.copy(p, p + ".bak-dir1")
io.open(p, "w", encoding="utf-8", newline="\n").write(s.rstrip() + "\n" + fn)
print("patched", p, "- now: npx wrangler deploy")

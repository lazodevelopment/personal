/* =====================================================================
   SITE CONFIG — everything you need to swap is right here.
   1. IMAGES: paste your Firebase Storage download URLs (leave "" to keep
      the styled placeholder). Keys map to data-img attributes in the page.
   2. FORMSPREE_ID: replace with your real Formspree form ID.
   3. PHONE / EMAIL / SOCIALS: fill in when ready.
===================================================================== */
/* ---- Firebase image helpers (danbren-media bucket, tokenless via rules) ---- */
const _FB = "https://firebasestorage.googleapis.com/v0/b/danbren-media.firebasestorage.app/o/";
const _ws = (name, params) => "https://images.weserv.nl/?url=" +
  encodeURIComponent(_FB + encodeURIComponent(name) + "?alt=media") + params;
const ES_IMG  = (n, w=1200) => !n ? "" : _ws("ESCOTT_WED (" + n + ").jpg", "&w=" + w + "&q=82&output=webp");
const ES_HERO = (n)         => !n ? "" : _ws("Elizabeth Scott Hero Image (" + n + ").jpg", "&w=1920&q=82&output=webp");
const ES_HEADSHOT           = "https://images.weserv.nl/?url=https%3A%2F%2Ffirebasestorage.googleapis.com%2Fv0%2Fb%2Fdanbren-media.firebasestorage.app%2Fo%2FElizabeth%2520Portrait.png%3Falt%3Dmedia%26token%3D5a55439d-9c31-4457-95fa-3f3df4994e7b&w=900&q=84&output=webp";

const CONFIG = {
  FORMSPREE_ID: "xojgqprg",   // e.g. "xabcwxyz"
  META_PIXEL_ID: "REPLACE_WITH_PIXEL_ID",
  GA4_ID: "G-2GWEJ459GV",                                   // e.g. "G-XXXXXXXXXX"       // Elizabeth Scott Meta Pixel
  PHONE: "",                                    // e.g. "(833) 321-7676"
  EMAIL: "info@elizabethscottweddings.com",
  SOCIALS: { instagram: "https://www.instagram.com/elizabethscottweddings", facebook: "https://www.facebook.com/elizabethscottweddings", linkedin: "https://www.linkedin.com/company/elizabethscottweddings", youtube: "" },
  IMAGES: {
    /* hero: pick 1-4 (the dedicated Elizabeth Scott Hero Images) */
    hero: ES_HERO(1),
    hero2: ES_HERO(2),
    hero3: ES_HERO(3),
    hero4: ES_HERO(4),
    about: ES_HEADSHOT,
    /* gallery picks: replace each 0 with a number 1-463 from ESCOTT_WED (N).jpg
       0 = keep the styled monogram placeholder for that slot */
    photography: ES_IMG(25),
    videography: ES_IMG(150),
    combo: ES_IMG(275),
    portfolio1: ES_IMG(10, 900),
    portfolio2: ES_IMG(85, 900),
    portfolio3: ES_IMG(160, 900),
    portfolio4: ES_IMG(235, 900),
    portfolio5: ES_IMG(310, 900),
    portfolio6: ES_IMG(385, 900)
  }
};

/* ---- apply images ---- */
Object.entries(CONFIG.IMAGES).forEach(([key,url])=>{
  if(!url) return;
  document.querySelectorAll(`img[data-img="${key}"]`).forEach(img=>{
    img.addEventListener("load",()=>{
      img.classList.add("loaded");
      const f=img.closest(".frame")||img.parentElement;
      if(f) f.classList.add("has-img");
    });
    img.src=url;
  });
});

/* ---- contact details ---- */
if(CONFIG.PHONE){
  document.querySelectorAll("[data-tel]").forEach(a=>{a.href="sms:"+CONFIG.PHONE.replace(/\D/g,"");a.textContent=a.classList.contains("btn")?"Text "+CONFIG.PHONE:CONFIG.PHONE;});
}
if(CONFIG.EMAIL){
  document.querySelectorAll("[data-email]").forEach(a=>{a.href="mailto:"+CONFIG.EMAIL;a.textContent=CONFIG.EMAIL;});
}
Object.entries(CONFIG.SOCIALS).forEach(([k,url])=>{
  if(url) document.querySelectorAll(`[data-social="${k}"]`).forEach(a=>a.href=url);
});
document.querySelectorAll("[data-social]").forEach(a=>{if(a.getAttribute("href")==="#")a.closest("li")?a.closest("li").style.display="none":a.style.display="none";});

/* ---- form ---- */
const form=document.getElementById("availabilityForm");
const note=document.getElementById("formNote");
if(form){
const fd=document.getElementById("f-date");if(fd)fd.min=new Date().toISOString().split("T")[0];
form.addEventListener("submit",async e=>{
  e.preventDefault();
  if(CONFIG.FORMSPREE_ID.startsWith("REPLACE")){
    note.textContent="⚠ Formspree ID not set yet — update CONFIG.FORMSPREE_ID at the top of the script.";return;
  }
  const btn=form.querySelector("button[type=submit]");btn.disabled=true;btn.style.opacity=".6";
  try{
    const res=await fetch("https://formspree.io/f/"+CONFIG.FORMSPREE_ID,{
      method:"POST",headers:{Accept:"application/json"},body:new FormData(form)});
    if(res.ok){window.location.href="/thank-you.html";return;}
    throw new Error();
  }catch(_){
    note.textContent="Something went wrong — please try again, or text us directly.";
    btn.disabled=false;btn.style.opacity="1";
  }
});
}

/* ---- Meta Pixel (fires only when an ID is set) ---- */
if(CONFIG.META_PIXEL_ID && !CONFIG.META_PIXEL_ID.startsWith("REPLACE")){
  !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
  n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
  n.push=n;n.loaded=!0;n.version="2.0";n.queue=[];t=b.createElement(e);t.async=!0;
  t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
  document,"script","https://connect.facebook.net/en_US/fbevents.js");
  fbq("init",CONFIG.META_PIXEL_ID);fbq("track","PageView");
}

/* ---- mobile nav ---- */
const burger=document.getElementById("burger"),links=document.getElementById("navLinks");
burger.addEventListener("click",()=>links.classList.toggle("open"));
links.querySelectorAll("a").forEach(a=>a.addEventListener("click",()=>links.classList.remove("open")));

/* ---- GA4 (fires only when an ID is set) ---- */
if(CONFIG.GA4_ID && CONFIG.GA4_ID.indexOf("G-")===0){
  var gs=document.createElement("script");gs.async=true;
  gs.src="https://www.googletagmanager.com/gtag/js?id="+CONFIG.GA4_ID;
  document.head.appendChild(gs);
  window.dataLayer=window.dataLayer||[];window.gtag=function(){dataLayer.push(arguments);};
  gtag("js",new Date());gtag("config",CONFIG.GA4_ID);
}

/* ---- lead attribution: ?city= param wins, chip on contact, hidden fields ---- */
(function(){try{
  var q=new URLSearchParams(location.search),pc=q.get("city"),pf=q.get("from");
  var ss=null;try{ss=window.sessionStorage;}catch(e){}
  if(ss&&!ss.getItem("es_landing")){try{ss.setItem("es_landing",location.pathname);ss.setItem("es_ref",document.referrer||"");}catch(e){}}
  if(pc&&ss){try{ss.setItem("es_city",pc);ss.setItem("es_city_url",pf||"");}catch(e){}}
  var city=pc||(ss&&ss.getItem("es_city"))||"",curl=pf||(ss&&ss.getItem("es_city_url"))||"";
  if(!form)return;
  function set(n,v){var el=form.querySelector('[name="'+n+'"]');if(el&&v)el.value=v;}
  set("City",city);set("City Page",curl);
  if(ss){set("Landing Page",ss.getItem("es_landing")||"");set("Referrer",ss.getItem("es_ref")||"");}
  if(city){var ch=document.getElementById("cityContext"),nm=document.getElementById("cityContextName");
    if(ch&&nm){nm.textContent=city;ch.style.display="block";}}
  var pkg=q.get("package");
  if(pkg){var sp=form.querySelector('[name="package"]');
    if(sp){for(var i=0;i<sp.options.length;i++){if(sp.options[i].value===pkg){sp.value=pkg;break;}}}}
}catch(e){}})();

/* ---- thank-you conversions ---- */
if(location.pathname.indexOf("/thank-you")===0){
  if(window.fbq)fbq("track","Lead");
  if(window.gtag)gtag("event","generate_lead",{currency:"USD",value:500});
}

/* ---- portfolio lightbox ---- */
(function(){
  var lb=document.getElementById("esLightbox"); if(!lb) return;
  var items=[].slice.call(document.querySelectorAll("[data-glb]"));
  var sources=items.map(function(el){return el.getAttribute("data-glb-full")||el.getAttribute("data-glb");});
  var img=lb.querySelector(".glb__img"),count=lb.querySelector(".glb__count"),cur=0;
  function show(i){cur=(i+sources.length)%sources.length;img.src=sources[cur];count.textContent=(cur+1)+" / "+sources.length;lb.classList.add("open");document.body.style.overflow="hidden";}
  function close(){lb.classList.remove("open");document.body.style.overflow="";}
  items.forEach(function(el,i){el.addEventListener("click",function(){show(i);});});
  lb.querySelector(".glb__close").addEventListener("click",close);
  lb.querySelector(".glb__prev").addEventListener("click",function(e){e.stopPropagation();show(cur-1);});
  lb.querySelector(".glb__next").addEventListener("click",function(e){e.stopPropagation();show(cur+1);});
  lb.addEventListener("click",function(e){if(e.target===lb)close();});
  document.addEventListener("keydown",function(e){if(!lb.classList.contains("open"))return;
    if(e.key==="Escape")close();if(e.key==="ArrowLeft")show(cur-1);if(e.key==="ArrowRight")show(cur+1);});
})();

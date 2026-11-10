"""The page: one self-contained HTML file (inline CSS, JS and SVG) with the collected data embedded as JSON. It loads
nothing from the network; a served page asks only its own /data.json, by a relative path."""
from __future__ import annotations

import base64
import json
from pathlib import Path

BRAIN = Path(__file__).resolve().parent / "brain.jpg"  # a glass brain, left lateral view, on #01071b

# the words of the page, both languages complete
TEXT = {
    "tr": {
        "title": "Living Runtime · Zihin paneli", "eyebrow": "LIVING RUNTIME", "h1": "Zihin paneli",
        "tagline": "Var olan zekâyı daha iyi kullanmak: 13 amaç, her sayı kendi dosyasından.",
        "prov": "Bu sayfadaki her sayı, yanında adı yazan dosyadan sayfa oluşturulurken okundu. Örnek ya da yer "
                "tutucu veri yok: kaynağı olmayan \"kaynak yok\", ölçülmeyen \"ölçülmedi\" görünür.",
        "generated": "Oluşturuldu", "heartbeat": "Son kanca etkinliği",
        "min_ago": "dakika önce", "health": "Sunucu", "up": "açık", "down": "kapalı", "blind": "Kör pencere",
        "blind_opens": "Açılış", "up_to": "şu tarihe kadar", "analogy": "Benzetme",
        "analogy_note": "Beyin bölgeleri bir benzetmedir: sistemi okumanın bir yolu, beyin hakkında bir iddia değil.",
        "pulse_note": "Halka atan düğüm: o amacın kör pencere dışındaki bir kaynağına son 24 saatte yeni kayıt düştü.",
        "part": "Bölüm", "aim": "Amaç", "yardstick": "Ölçüt", "last": "Son ölçüm", "measured_on": "Ölçüldüğü tarih",
        "evidence": "Kanıt", "live": "Canlı sayılar", "source": "Kaynak", "how": "Nasıl hesaplanır",
        "window": "Pencere", "status": "Durum", "scorecard": "Karne", "vitals": "Yaşamsal belirtiler",
        "sources": "Kaynaklar", "not_found": "Aranıp bulunamayanlar", "rows": "satır", "newest": "en yeni",
        "no_card": "bu makinede ölçülmedi", "none": "yok", "missing": "kaynak yok", "unmeasured_v": "ölçülmedi",
        "no_card_hint": "Karne dosyası yok: durum ölçülmeden yazılmaz. Kendi ölçümlerinizi bir karne dosyasına "
                        "yazınca burada görünür (plugins/mind/README.md).",
        "aims_h": "13 amaç", "all_aims": "Tüm amaçlar", "part_LR": "hafıza", "part_COL": "öz denetim",
        "part_scnc": "sebep bulma", "no_live": "Bu amacın kendiliğinden sayılan bir ölçüsü yok.",
        "file_page": "Dosya olarak açıldı: sayılar oluşturulma anındaki hâlidir, yenilenmez.", "served_page":
        "Sunucudan açıldı: sayılar dakikada bir yenilenir.", "card_from": "Karne dosyası", "lang": "English",
        "only_newest": "yalnız kalp atışı için okundu", "skipped": "dışarıda tutulan", "files": "dosya",
        "c_sessions": "Günlük aktif oturum", "c_compactions": "Günlük özetleme", "c_context":
        "Çağrı başına bağlam (ortanca)", "c_rules": "Günlük eklenen kural", "c_reminders": "Günlük kural hatırlatma",
        "c_claims": "Günlük yakalanan iddia", "c_preds": "Öngörü: tuttu / tutmadı",
        "c_streaks": "Günlük ikinci / üçüncü başarısızlık", "c_intent": "Günlük niyet bakışı / geri çevirme",
        "no_series": "bu kaynak için günlük dizi yok", "nojs":
        "Bu sayfa sayıları JavaScript ile çizer; veriler sayfaya gömülü JSON olarak duruyor.",
    },
    "en": {
        "title": "Living Runtime · Mind panel", "eyebrow": "LIVING RUNTIME", "h1": "Mind panel",
        "tagline": "Better use of the intelligence already there: 13 aims, every number from its own file.",
        "prov": "Every number on this page was read from the file named next to it when the page was made. There is "
                "no sample or placeholder data: a source that is not there shows as \"source missing\", a number "
                "never measured as \"not measured\".",
        "generated": "Generated", "heartbeat": "Last hook activity",
        "min_ago": "minutes ago", "health": "Server", "up": "up", "down": "down", "blind": "Blind window",
        "blind_opens": "Opens", "up_to": "up to", "analogy": "Analogy",
        "analogy_note": "The brain regions are an analogy: a way to read the system, not a claim about brains.",
        "pulse_note": "A pulsing node: a source of that aim outside the blind window got a new record in the last "
                      "24 hours.",
        "part": "Part", "aim": "Aim", "yardstick": "Yardstick", "last": "Last measurement", "measured_on":
        "Measured on", "evidence": "Evidence", "live": "Live numbers", "source": "Source", "how": "How it is computed",
        "window": "Window", "status": "Status", "scorecard": "Scorecard", "vitals": "Vital signs",
        "sources": "Sources", "not_found": "Looked for and not found", "rows": "rows", "newest": "newest",
        "no_card": "not measured on this machine", "none": "none", "missing": "source missing", "unmeasured_v":
        "not measured",
        "no_card_hint": "There is no scorecard file: a status is not written without a measurement. Your own "
                        "measurements appear here once you write them to a scorecard file (plugins/mind/README.md).",
        "aims_h": "The 13 aims", "all_aims": "All aims", "part_LR": "memory", "part_COL": "self-check",
        "part_scnc": "finding causes", "no_live": "This aim has no number that is counted automatically.",
        "file_page": "Opened as a file: the numbers are as of generation and do not refresh.", "served_page":
        "Served: the numbers refresh every minute.", "card_from": "Scorecard file", "lang": "Türkçe",
        "only_newest": "read for the heartbeat only", "skipped": "kept out", "files": "files",
        "c_sessions": "Sessions active per day", "c_compactions": "Compactions per day", "c_context":
        "Context per call (median)", "c_rules": "Rules added per day", "c_reminders": "Rule reminders per day",
        "c_claims": "Claims caught per day", "c_preds": "Predictions: held / missed",
        "c_streaks": "Second / third failures per day", "c_intent": "Intent looks / turned back per day",
        "no_series": "no daily series for this source", "nojs":
        "This page draws its numbers with JavaScript; the data sits in the page as embedded JSON.",
    },
}
STATUS = {
    "works": {"tr": "çalışıyor", "en": "works"}, "partial": {"tr": "kısmen", "en": "partial"},
    "fails": {"tr": "tutmuyor", "en": "fails"}, "unused": {"tr": "kullanılmıyor", "en": "unused"},
    "unclear": {"tr": "belirsiz", "en": "unclear"}, "unmeasured": {"tr": "ölçülmedi", "en": "not measured"},
}
LABELS = {
    "compactions": ("Özetlemeler", "Compactions"), "episodes": ("Saklanan izler", "Traces kept"),
    "recall_searches": ("Geçmiş aramaları", "Recall searches"),
    "sessions_on_record": ("Kayıttaki oturumlar", "Sessions on record"),
    "sessions_active": ("Etkin oturumlar", "Sessions active"),
    "rules": ("Bellekteki kurallar", "Rules in memory"), "rules_added": ("Eklenen kurallar", "Rules added"),
    "cue_reminders": ("Kural hatırlatmaları", "Rule reminders"), "cue_rules": ("Hatırlatılan kurallar",
                                                                             "Rules reminded"),
    "rules_with_cue": ("İpucu taşıyan kurallar", "Rules that carry a cue"),
    "sleep_passes": ("Uyku geçişleri", "Sleep passes"), "sleep_last": ("Son geçiş", "Last pass"),
    "candidates": ("Bekleyen adaylar", "Candidates waiting"),
    "context_median": ("Çağrı başına bağlam (ortanca)", "Median context per call"),
    "checks": ("Denetlenen turlar", "Turns checked"), "claims_caught": ("Yakalanan iddialar", "Claims caught"),
    "intent_looks": ("Niyet bakışları", "Intent looks"), "intent_turned_back": ("Geri çevrilen", "Turned back"),
    "intent_tokens": ("Niyet tokenları", "Intent tokens"),
    "pred_recorded": ("Kaydedilen öngörüler", "Predictions recorded"), "pred_held": ("Tutan", "Held"),
    "pred_missed": ("Tutmayan", "Missed"), "pred_uncompared": ("Karşılaştırılamayan", "Not comparable"),
    "pred_hit": ("Tutma oranı", "Share that held"),
    "guard_stopped": ("Durdurulan yasak yazmalar", "Forbidden writes stopped"),
    "secrets_stopped": ("Durdurulan anahtarlar", "Keys stopped"),
    "hypothesis_lines": ("Hipotez satırları", "Hypothesis lines"),
    "scnc_skill_calls": ("scnc beceri çağrıları", "scnc skill calls"),
    "streak2": ("İkinci başarısızlıklar", "Second failures"), "streak3": ("Üçüncü başarısızlıklar",
                                                                          "Third failures"),
    "streak_share": ("Üçüncüye giden pay", "Share going to a third"),
    "scnc_reminders": ("scnc hatırlatmaları", "scnc reminders"),
    "scnc_third_after": ("Hatırlatmadan sonra üçüncü", "Third failure after a reminder"),
}

UNITS = {
    "rows": ("satır", "rows"), "turns": ("tur", "turns"), "writes": ("yazma", "writes"), "commits": ("işlem",
                                                                                                "commits"),
    "reminders": ("hatırlatma", "reminders"), "rules": ("kural", "rules"), "streaks": ("seri", "streaks"),
    "looks": ("bakış", "looks"), "tokens": ("token", "tokens"), "predictions": ("öngörü", "predictions"),
    "files": ("dosya", "files"), "sessions": ("oturum", "sessions"), "passes": ("geçiş", "passes"),
    "candidates": ("aday", "candidates"), "lines": ("satır", "lines"), "bytes": ("bayt", "bytes"),
    "compactions": ("özetleme", "compactions"), "calls": ("çağrı", "calls"), "failures": ("başarısızlık",
                                                                                          "failures"),
    "searches": ("arama", "searches"), "minutes": ("dakika", "minutes"),
}

TEMPLATE = r"""<!doctype html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mind panel</title>
<style>
:root{--bg:#01071b;--bg2:#0b1430;--card:rgba(13,22,48,.78);--line:#1f2c57;--ink:#e6ecfb;--dim:#8f9dc2;
--lr:#38d6e0;--col:#f2b13c;--scnc:#a98bff;--works:#47d18c;--partial:#e8c547;--fails:#ff6b6b;--unused:#8791ab;
--unclear:#c3a6e6;--unmeasured:#66739a;--blind:#3b2f5e}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",
Roboto,"Helvetica Neue",Arial,sans-serif}
main{max-width:1240px;margin:0 auto;padding:20px 16px 48px}
a{color:var(--lr)}
.hero{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:flex-end;justify-content:space-between}
.eyebrow{font-size:.74rem;letter-spacing:.22em;color:var(--col);font-weight:600}
h1{font-size:clamp(1.7rem,4vw,2.5rem);line-height:1.1;margin:.15rem 0 .35rem;font-weight:650;letter-spacing:-.01em}
.tagline{margin:0;color:#b9c5e6;font-size:1.02rem;max-width:46rem}
.meta{display:flex;flex-wrap:wrap;gap:.35rem 1.1rem;align-items:center;color:var(--dim);font-size:.88rem}
.meta b{color:var(--ink);font-weight:500}
h2{font-size:.82rem;margin:2.2rem 0 .7rem;color:var(--dim);font-weight:600;letter-spacing:.14em;
text-transform:uppercase}
button{font:inherit;color:var(--ink);background:var(--bg2);border:1px solid var(--line);border-radius:8px;
padding:.3rem .7rem;cursor:pointer}
button:hover{border-color:#3a4c88}
button:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--lr);outline-offset:2px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 6px}
.chip{display:inline-flex;align-items:center;gap:.4rem;padding:.3rem .7rem;border-radius:999px;font-size:.9rem;
border:1px solid color-mix(in srgb,var(--c) 45%,transparent);background:color-mix(in srgb,var(--c) 12%,transparent);
color:var(--c)}
.chip b{font-size:1.05rem;color:var(--ink)}
.prov{margin:.3rem 0 0;color:var(--dim);font-size:.84rem;max-width:62rem}
.band{margin:14px 0 0;padding:.6rem .85rem;border:1px solid #5d4a99;border-radius:10px;
background:repeating-linear-gradient(135deg,#21193d 0 10px,#271e48 10px 20px);font-size:.92rem}
.grid{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(0,1fr);gap:18px;align-items:start;margin-top:18px}
@media (max-width:900px){.grid{grid-template-columns:minmax(0,1fr)}}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}
.panel.brainbox{background:var(--bg);border-color:transparent;padding:0}
svg{display:block;max-width:100%;height:auto}
.brain .cortex{fill:rgba(120,160,255,.05);stroke:#8fa7e6;stroke-opacity:.55;stroke-width:2}
.brain .sulcus{fill:none;stroke:#8fa7e6;stroke-opacity:.28;stroke-width:1.4;stroke-linecap:round}
.brain .inner{fill:rgba(140,170,255,.06);stroke:#9fb3ea;stroke-opacity:.32;stroke-width:1.2;stroke-dasharray:3 3}
.brain .cb{fill:rgba(120,160,255,.06);stroke:#8fa7e6;stroke-opacity:.5;stroke-width:1.6}
.brain .lbl{fill:var(--dim);font-size:10px;opacity:.75}
.tract{fill:none;stroke-width:1.6;stroke-opacity:.2}
.brain.painted .tract{stroke-width:2.4;stroke-opacity:.28;stroke-dasharray:2 7;stroke-linecap:round}
.node{cursor:pointer;outline:none}
.node .ring{stroke-width:2.5}
.node text{font-size:11px;font-weight:700;fill:#07102a;pointer-events:none}
.node.hollow text{fill:var(--ink)}
.node .selring{fill:none;stroke:#fff;stroke-width:2;opacity:0}
.node.sel .selring,.node:focus-visible .selring{opacity:.95}
.node:hover .ring{stroke-width:4}
.node .halo{transform-box:fill-box;transform-origin:center}
.node.pulse .halo{animation:pulse 2.6s ease-out infinite}
@keyframes pulse{0%{transform:scale(1);opacity:.7}100%{transform:scale(2);opacity:0}}
@media (prefers-reduced-motion:reduce){.node.pulse .halo{animation:none;opacity:.4}}
.brain.painted .node .ring{stroke-width:3.5}
.brain.painted .node:hover .ring{stroke-width:6}
.brain.painted .node text{font-size:21px}
.brain.painted .lead{fill:#e6ecfb;font-size:21px;font-weight:500;paint-order:stroke;stroke:#01071b;
stroke-width:6px;stroke-linejoin:round}
.notes{padding:2px 12px 12px;color:var(--dim);font-size:.8rem}
.notes p{margin:.15rem 0}
.group{margin:0 0 .9rem}
.group:last-of-type{margin-bottom:.2rem}
.group h3{margin:.1rem 0 .35rem;font-size:.95rem;font-weight:650;letter-spacing:.02em}
.group h3 span{color:var(--dim);font-weight:400;font-size:.85rem;margin-left:.3rem}
.group ul{list-style:none;margin:0;padding:0}
.aimbtn{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:.6rem;align-items:center;width:100%;
text-align:left;background:transparent;border:0;border-top:1px solid var(--line);border-radius:0;padding:.5rem .2rem}
.aimbtn:hover{background:rgba(255,255,255,.035)}
.aimbtn .n{display:inline-grid;place-items:center;width:1.7rem;height:1.7rem;border-radius:50%;border:2px solid;
font-size:.8rem;font-weight:700}
.aimbtn .a{font-size:.92rem;line-height:1.3}
.card .back{margin-bottom:.7rem;font-size:.85rem;color:var(--dim)}
.cardhead{display:flex;gap:.7rem;align-items:flex-start}
.cardhead .n{flex:none;display:inline-grid;place-items:center;width:2.3rem;height:2.3rem;border-radius:50%;
border:2.5px solid;font-weight:700;font-size:1.05rem}
.card h3{margin:.1rem 0 .2rem;font-size:1.12rem;line-height:1.3}
.card .sub{color:var(--dim);font-size:.88rem}
.card dl{margin:.7rem 0 .2rem}
.card dt{color:var(--dim);font-size:.74rem;letter-spacing:.08em;text-transform:uppercase;margin-top:.6rem}
.card dd{margin:.1rem 0 0}
.card h4{margin:1rem 0 .1rem;font-size:.74rem;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);
font-weight:600}
.live{border-top:1px solid var(--line);padding:.5rem 0}
.live .k{display:flex;flex-wrap:wrap;gap:.3rem;align-items:center;justify-content:space-between}
.live .v{font-size:1.25rem;font-weight:650}
.small{font-size:.8rem;color:var(--dim);overflow-wrap:anywhere}
.tag{display:inline-block;font-size:.72rem;padding:0 .45rem;border-radius:9px;border:1px solid var(--line);
color:var(--dim);vertical-align:middle;white-space:nowrap}
.tag.blind{border-color:#6c5bb0;color:#c9bcff}
.part-LR{color:var(--lr)}.part-COL{color:var(--col)}.part-scnc{color:var(--scnc)}
table{border-collapse:collapse;width:100%;font-size:.88rem}
th,td{text-align:left;vertical-align:top;padding:.5rem .5rem;border-bottom:1px solid var(--line)}
th{color:var(--dim);font-weight:500;font-size:.78rem;letter-spacing:.06em;text-transform:uppercase}
.tablewrap{overflow-x:auto}
.tablewrap table{min-width:720px}
.badge{display:inline-flex;align-items:center;gap:.3rem;white-space:nowrap;font-size:.86rem}
.charts{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
@media (max-width:400px){.charts{grid-template-columns:minmax(0,1fr)}}
.chart h4{margin:0 0 .3rem;font-size:.92rem;font-weight:500}
.chart .tot{font-size:.85rem;color:var(--dim)}
.axis{fill:var(--dim);font-size:9px}
tr.aimrow{cursor:pointer}
tr.aimrow:hover{background:rgba(255,255,255,.03)}
footer{margin-top:2.4rem;color:var(--dim);font-size:.8rem}
</style>
</head>
<body>
<main id="app">
<noscript><p>__NOJS__</p></noscript>
</main>
<script type="application/json" id="mind-data">__DATA__</script>
<script type="application/json" id="mind-text">__TEXT__</script>
<script>
(function(){
"use strict";
var DATA=JSON.parse(document.getElementById("mind-data").textContent);
var T=JSON.parse(document.getElementById("mind-text").textContent);
var SERVED=__SERVED__;
var LANG="__LANG__";
var SEL=null;
// node centres on the drawn outline (the fallback when the painted brain is not there)
var POS={dlpfc:[212,148],frontopolar:[124,228],ofc:[178,318],acc:[300,204],striatum:[358,264],
thalamus:[432,252],hippocampus:[392,332],temporal:[262,366],parietal:[548,140],tpj:[528,262],
cerebellum:[598,402],vta:[462,326],lc:[480,388]};
// node centres on the painted brain (1200 x 800), by region
var PAINTED={dlpfc:[406,195],hippocampus:[531,461],temporal:[414,469],striatum:[500,344],thalamus:[617,344],
cerebellum:[789,508],parietal:[789,195],acc:[438,258],tpj:[813,344],ofc:[313,367],frontopolar:[258,313],
lc:[652,484],vta:[648,426]};
// where each painted node's short label goes, pointing away from the inner structures: [dx, dy, anchor]
// (only the nodes on the cortex and cerebellum get one; the inner, gold structures stay uncovered)
var LEAD={dlpfc:[0,-36,"middle"],parietal:[0,-36,"middle"],frontopolar:[-34,7,"end"],ofc:[-34,7,"end"],
temporal:[-30,40,"end"],tpj:[34,7,"start"],cerebellum:[34,36,"start"]};
var BRAIN=T.brain||"";
var PART={LR:"var(--lr)",COL:"var(--col)",scnc:"var(--scnc)"};
var SHAPE={works:"✓",partial:"◐",fails:"✕",unused:"○",unclear:"?",unmeasured:"·"};
var ORDER=["works","partial","fails","unused","unclear","unmeasured"];
function t(k){return (T.ui[LANG]||{})[k]||k;}
function L(o){if(o==null)return "";if(typeof o==="string")return o;return o[LANG]||o.en||o.tr||"";}
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",
">":"&gt;",'"':"&quot;","'":"&#39;"}[c];});}
function num(v){if(v==null)return "—";if(typeof v!=="number")return esc(v);
return new Intl.NumberFormat(LANG==="tr"?"tr-TR":"en-US",{maximumFractionDigits:v<10&&v%1?3:1}).format(v);}
function when(iso,dateOnly){if(!iso)return "—";var d=new Date(iso);if(isNaN(d))return esc(iso);
var o=dateOnly?{year:"numeric",month:"short",day:"numeric"}:{year:"numeric",month:"short",day:"numeric",
hour:"2-digit",minute:"2-digit"};return d.toLocaleString(LANG==="tr"?"tr-TR":"en-GB",o);}
function label(k){var l=T.labels[k];return l?(LANG==="tr"?l[0]:l[1]):k;}
function stat(s){return (T.status[s]||{})[LANG]||s;}
function badge(s){return '<span class="badge" style="color:var(--'+s+')"><span aria-hidden="true">'+SHAPE[s]+
'</span>'+esc(stat(s))+'</span>';}
function value(m){
if(!m)return '<span class="small">'+t("missing")+'</span>';
if(m.status==="missing")return '<span class="small">'+t("missing")+'</span>';
if(m.status==="unmeasured"||m.value==null)return '<span class="small">'+t("unmeasured_v")+'</span>';
var v=m.value;
if(typeof v==="object"){var ks=Object.keys(v).sort(function(a,b){return v[b]-v[a];});
return ks.length?ks.slice(0,6).map(function(k){return esc(k)+": "+num(v[k]);}).join(" · "):t("none");}
if(m.unit==="time")return when(v);
if(m.unit==="state")return esc(t(v));
if(m.unit==="share")return (LANG==="tr"?"%":"")+num(Math.round(v*1000)/10)+(LANG==="tr"?"":"%");
var u=T.units[m.unit];return num(v)+' <span class="small">'+esc(u?(LANG==="tr"?u[0]:u[1]):m.unit)+'</span>';}
function blindTag(m){return m&&m.blind?'<span class="tag blind">'+t("blind")+", "+t("up_to")+" "+
when(DATA.blind.from,true)+'</span>':"";}
function sources(m){return (m.source||[]).map(esc).join("<br>");}
function pulsing(x){return x.live.some(function(k){var m=DATA.metrics[k];return m&&m.active_24h&&!m.blind;});}

function nodes(pos,r,lead){var a=DATA.aims,s="";
["LR","COL","scnc"].forEach(function(p){var ns=a.filter(function(x){return x.part===p;});
for(var i=1;i<ns.length;i++){var p0=pos[ns[i-1].region],p1=pos[ns[i].region],mx=(p0[0]+p1[0])/2,
my=(p0[1]+p1[1])/2-r*1.6;s+='<path class="tract" stroke="'+PART[p]+'" d="M'+p0[0]+' '+p0[1]+'Q'+mx+' '+my+' '+
p1[0]+' '+p1[1]+'"/>';}});
a.forEach(function(x){var p=pos[x.region],hollow=["unused","unmeasured","unclear"].indexOf(x.status)>=0,
fill=hollow?"#01071b":"var(--"+x.status+")",pulse=pulsing(x);
s+='<g class="node'+(hollow?" hollow":"")+(pulse?" pulse":"")+(SEL===x.id?" sel":"")+'" data-id="'+x.id+
'" tabindex="0" role="button" aria-label="'+x.id+". "+esc(L(x.aim))+", "+esc(stat(x.status))+'">';
s+='<title>'+x.id+". "+esc(L(x.aim))+" · "+esc(stat(x.status))+'</title>';
s+='<circle cx="'+p[0]+'" cy="'+p[1]+'" r="'+(r*1.55)+'" fill="transparent"/>';
s+='<circle class="halo" cx="'+p[0]+'" cy="'+p[1]+'" r="'+r+'" fill="none" stroke="'+PART[x.part]+'" '+
'stroke-width="2" stroke-opacity="'+(pulse?".7":"0")+'"/>';
s+='<circle class="selring" cx="'+p[0]+'" cy="'+p[1]+'" r="'+(r*1.32)+'"/>';
s+='<circle class="ring" cx="'+p[0]+'" cy="'+p[1]+'" r="'+r+'" fill="'+fill+'" stroke="'+PART[x.part]+'"'+
(x.status==="unmeasured"?' stroke-dasharray="2 4"':x.status==="unused"?' stroke-dasharray="7 4"':'')+'/>';
s+='<text x="'+p[0]+'" y="'+(p[1]+r*.33)+'" text-anchor="middle">'+x.id+'</text>';
if(lead&&lead[x.region]){var q=lead[x.region];s+='<text class="lead" x="'+(p[0]+q[0])+'" y="'+(p[1]+q[1])+
'" text-anchor="'+q[2]+'" aria-hidden="true">'+esc(stat(x.status))+'</text>';}
s+='</g>';});return s;}
function notes(){return '<div class="notes"><p>'+esc(t("analogy_note"))+'</p><p>'+esc(t("pulse_note"))+
'</p></div>';}
function brain(){
if(BRAIN)return '<svg class="brain painted" viewBox="0 0 1200 800" role="group" aria-label="'+esc(t("title"))+
'"><image href="'+BRAIN+'" x="0" y="0" width="1200" height="800"/>'+nodes(PAINTED,22,LEAD)+'</svg>'+notes();
var s='<svg class="brain" viewBox="60 40 680 480" role="group" aria-label="'+esc(t("title"))+'">';
s+='<defs><radialGradient id="glass" cx="45%" cy="40%" r="70%"><stop offset="0" stop-color="#2a3f7a" '+
'stop-opacity=".35"/><stop offset="1" stop-color="#0a1024" stop-opacity="0"/></radialGradient></defs>';
s+='<path class="cortex" fill="url(#glass)" d="M118 298C78 220 104 122 214 84C318 48 470 44 572 84C662 120 '+
'712 200 694 278C684 320 652 344 612 350L556 346C520 360 482 398 422 414C340 432 252 422 210 386C180 360 '+
'148 338 118 298Z"/>';
['M228 300C300 278 382 268 472 286','M424 58C412 120 392 182 382 262','M384 62C370 120 352 176 344 248',
'M466 66C452 124 434 184 424 262','M170 150C220 130 280 118 340 112','M150 220C200 200 260 190 330 186',
'M236 352C300 336 380 330 470 330','M520 92C560 130 600 170 640 230','M486 300C540 296 600 304 660 300',
'M610 350C626 320 650 296 690 282'].forEach(function(d){s+='<path class="sulcus" d="'+d+'"/>';});
s+='<path class="cb" d="M502 366C522 340 640 334 672 370C692 400 652 442 592 442C540 442 500 416 502 366Z"/>';
['M516 384C560 370 620 368 666 380','M520 402C566 392 624 392 664 400','M532 420C572 414 616 414 650 420']
.forEach(function(d){s+='<path class="sulcus" d="'+d+'"/>';});
s+='<path class="cb" d="M446 372C450 412 454 452 458 506L500 506C500 456 504 414 512 362Z"/>';
s+='<path class="inner" d="M252 236C290 170 482 156 548 222C520 196 470 182 400 184C330 186 280 206 252 236Z"/>';
s+='<path class="inner" d="M270 232C310 190 470 180 530 226"/>';
s+='<path class="inner" d="M330 226C340 200 402 194 442 214C472 234 480 270 470 300"/>';
s+='<ellipse class="inner" cx="360" cy="266" rx="36" ry="22"/>';
s+='<ellipse class="inner" cx="432" cy="254" rx="38" ry="24"/>';
s+='<path class="inner" d="M326 344C366 318 432 318 482 332C470 344 420 344 372 350Z"/>';
s+='<ellipse class="inner" cx="464" cy="328" rx="22" ry="17"/>';
s+='<ellipse class="inner" cx="480" cy="388" rx="25" ry="21"/>';
[["cingulate",360,176],["thalamus",432,232],["striatum",334,292],["hippocampus",300,354],["midbrain",492,318],
["pons",512,394],["cerebellum",640,432]].forEach(function(x){s+='<text class="lbl" x="'+x[1]+'" y="'+x[2]+
'">'+x[0]+'</text>';});
return s+nodes(POS,13,null)+'</svg>'+notes();}

function chips(){var c={};DATA.aims.forEach(function(x){c[x.status]=(c[x.status]||0)+1;});
return '<div class="chips">'+ORDER.filter(function(s){return c[s];}).map(function(s){
return '<span class="chip" style="--c:var(--'+s+')"><span aria-hidden="true">'+SHAPE[s]+'</span><b>'+c[s]+
'</b>'+esc(stat(s))+'</span>';}).join("")+'</div>';}

function overview(){var h='';
["LR","COL","scnc"].forEach(function(p){var ns=DATA.aims.filter(function(x){return x.part===p;});
h+='<section class="group"><h3 class="part-'+p+'">'+esc(p)+'<span>'+esc(t("part_"+p))+'</span></h3><ul>';
ns.forEach(function(x){h+='<li><button class="aimbtn" data-id="'+x.id+'"><span class="n" style="border-color:'+
PART[p]+'">'+x.id+'</span><span class="a">'+esc(L(x.aim))+'</span>'+badge(x.status)+'</button></li>';});
h+='</ul></section>';});
if(!DATA.scorecard)h+='<p class="small">'+esc(t("no_card_hint"))+'</p>';
return h;}

function card(){
var x=DATA.aims.filter(function(a){return a.id===SEL;})[0];
if(!x)return overview();
var h='<div class="card"><button id="closecard" class="back">← '+esc(t("all_aims"))+'</button>'+
'<div class="cardhead"><span class="n part-'+x.part+'">'+x.id+'</span><div><h3>'+esc(L(x.aim))+'</h3>'+
'<div class="sub"><span class="part-'+x.part+'">'+esc(x.part)+'</span> · '+esc(t("part_"+x.part))+' · '+
badge(x.status)+'</div></div></div><dl>';
h+='<dt>'+t("last")+'</dt><dd>'+(x.on_card?esc(L(x.measured)||L(x.status_text)||stat(x.status))+
(x.measured_on?' <span class="small">('+esc(x.measured_on)+')</span>':''):esc(t("no_card")))+'</dd>';
h+='<dt>'+t("yardstick")+'</dt><dd>'+esc(L(x.yardstick))+'</dd>';
h+='<dt>'+t("analogy")+'</dt><dd>'+esc(L(x.analogy))+'</dd>';
if(x.evidence)h+='<dt>'+t("evidence")+'</dt><dd class="small">'+esc(typeof x.evidence==="string"?x.evidence:
JSON.stringify(x.evidence))+'</dd>';
h+='</dl><h4>'+t("live")+'</h4>';
if(!x.live.length)h+='<p class="small">'+esc(t("no_live"))+'</p>';
x.live.forEach(function(k){var m=DATA.metrics[k];h+='<div class="live"><div class="k"><span>'+esc(label(k))+
'</span>'+blindTag(m)+'</div><div class="v">'+value(m)+'</div><div class="small">'+t("how")+': '+esc(L(m.how))+
'</div><div class="small">'+t("source")+': '+sources(m)+'</div>'+(m.as_of?'<div class="small">'+t("newest")+': '+
when(m.as_of)+'</div>':'')+'</div>';});
return h+'</div>';}

function table(){
var h='<div class="tablewrap"><table><thead><tr><th>#</th><th>'+t("part")+'</th><th>'+t("aim")+'</th><th>'+
t("status")+'</th><th>'+t("last")+'</th><th>'+t("live")+'</th></tr></thead><tbody>';
DATA.aims.forEach(function(x){h+='<tr class="aimrow" data-id="'+x.id+'"><td>'+x.id+'</td><td class="part-'+x.part+
'">'+esc(x.part)+'</td><td>'+esc(L(x.aim))+'</td><td>'+badge(x.status)+'</td><td>'+(x.on_card?
esc(L(x.measured)||L(x.status_text)||"")+(x.measured_on?' <span class="small">'+esc(x.measured_on)+'</span>':''):
'<span class="small">'+esc(t("no_card"))+'</span>')+'</td><td class="small">'+(x.live.length?x.live.map(
function(k){var m=DATA.metrics[k];return esc(label(k))+": "+value(m);}).join("<br>"):esc(t("unmeasured_v")))+
'</td></tr>';});
var c=DATA.scorecard;
h+='</tbody></table></div>';
if(DATA.blind&&DATA.blind.active)h+='<p class="small">'+esc(t("live"))+': '+esc(t("blind"))+", "+t("up_to")+" "+
when(DATA.blind.from,true)+'.</p>';
if(c&&c.path)h+='<p class="small">'+t("card_from")+': '+esc(c.path)+(c.as_of?' · '+esc(c.as_of):'')+'</p>';
return h;}

function days(from,to){var out=[],d=new Date(from+"T12:00:00"),e=new Date(to+"T12:00:00");
while(d<=e&&out.length<400){out.push(d.getFullYear()+"-"+("0"+(d.getMonth()+1)).slice(-2)+"-"+
("0"+d.getDate()).slice(-2));d.setDate(d.getDate()+1);}return out;}
function localDay(iso){var d=new Date(iso);return d.getFullYear()+"-"+("0"+(d.getMonth()+1)).slice(-2)+"-"+
("0"+d.getDate()).slice(-2);}
function chart(title,keys,colors){
var ms=keys.map(function(k){return DATA.metrics[k];});
var h='<div class="chart panel"><h4>'+esc(title)+'</h4>';
var have=ms.filter(function(m){return m&&m.series&&m.series.length;});
if(!have.length){var m0=ms[0];return h+'<p class="small">'+(m0&&m0.status==="missing"?t("missing"):
t("no_series"))+'</p><p class="small">'+t("source")+': '+(m0?sources(m0):"")+'</p></div>';}
var all=[];have.forEach(function(m){m.series.forEach(function(p){all.push(p[0]);});});all.sort();
var blind=ms.some(function(m){return m&&m.blind;});
var last=all[all.length-1];
if(blind)last=localDay(DATA.generated);
var ds=days(all[0],last),W=300,Hh=90,n=ds.length,bw=W/n,max=0,maps=have.map(function(m){var o={};
m.series.forEach(function(p){o[p[0]]=p[1];if(p[1]>max)max=p[1];});return o;});
var s='<svg viewBox="0 0 '+W+' '+(Hh+16)+'" role="img" aria-label="'+esc(title)+'">';
if(blind){var bi=ds.indexOf(localDay(DATA.blind.from));if(bi<0)bi=n;s+='<rect x="'+(bi*bw)+'" y="0" width="'+
Math.max(0,W-bi*bw)+'" height="'+Hh+'" fill="var(--blind)" opacity=".7"/><text class="axis" x="'+(Math.min(bi*bw,
W-40)+2)+'" y="10">'+esc(t("blind"))+'</text>';}
maps.forEach(function(o,j){var w=bw/maps.length;ds.forEach(function(d,i){var v=o[d];if(v==null||!max)return;
var y=Hh-v/max*(Hh-12);s+='<rect x="'+(i*bw+j*w+.3)+'" y="'+y+'" width="'+Math.max(.6,w-.6)+'" height="'+
(Hh-y)+'" fill="'+colors[j]+'"><title>'+d+": "+num(v)+'</title></rect>';});});
s+='<line x1="0" y1="'+Hh+'" x2="'+W+'" y2="'+Hh+'" stroke="var(--line)"/><text class="axis" x="0" y="'+(Hh+12)+
'">'+ds[0]+'</text><text class="axis" x="'+W+'" y="'+(Hh+12)+'" text-anchor="end">'+ds[n-1]+'</text>'+
'<text class="axis" x="2" y="20">'+num(max)+'</text></svg>';
h+=s+'<div class="tot">'+have.map(function(m,j){var k=keys[ms.indexOf(m)];return '<span style="color:'+colors[j]+
'">■</span> '+esc(label(k))+": "+value(m);}).join(" · ")+' '+blindTag(have[0])+'</div>';
var w0=have[0].window;h+='<div class="small">'+t("window")+': '+(w0?when(w0.from,true)+" → "+when(w0.to,true):
"—")+'</div><div class="small">'+t("source")+': '+sources(have[0])+'</div>';
return h+'</div>';}

function vitals(){return '<div class="charts">'+
chart(t("c_sessions"),["sessions_active"],["var(--lr)"])+chart(t("c_compactions"),["compactions"],["var(--lr)"])+
chart(t("c_context"),["context_median"],["var(--lr)"])+chart(t("c_rules"),["rules_added"],["var(--lr)"])+
chart(t("c_reminders"),["cue_reminders"],["var(--lr)"])+chart(t("c_claims"),["claims_caught"],["var(--col)"])+
chart(t("c_intent"),["intent_looks","intent_turned_back"],["var(--col)","var(--fails)"])+
chart(t("c_preds"),["pred_held","pred_missed"],["var(--works)","var(--fails)"])+
chart(t("c_streaks"),["streak2","streak3"],["var(--scnc)","var(--fails)"])+'</div>';}

function srcs(){var h='<div class="tablewrap"><table><thead><tr><th>'+t("source")+'</th><th>'+t("rows")+
'</th><th>'+t("newest")+'</th></tr></thead><tbody>';
DATA.sources.forEach(function(s){h+='<tr><td class="small">'+esc(s.path)+(s.skipped_outside?' ('+
s.skipped_outside+' '+t("files")+' '+t("skipped")+')':'')+'</td><td>'+(s.only_newest?'<span class="small">'+
t("only_newest")+'</span>':num(s.rows)+(s.kind==="transcripts"?" "+t("files"):""))+(s.blind?' <span class="tag '+
'blind">'+t("blind")+", "+t("up_to")+" "+when(DATA.blind.from,true)+'</span>':'')+'</td><td>'+(s.only_newest?"—":
s.blind&&s.kind==="transcripts"?t("blind"):when(s.newest))+'</td></tr>';});
h+='</tbody></table></div>';
h+='<h2>'+t("not_found")+'</h2>'+(DATA.missing.length?'<ul class="small">'+DATA.missing.map(function(p){
return '<li>'+esc(p)+'</li>';}).join("")+'</ul>':'<p class="small">'+t("none")+'</p>');return h;}

function render(){
var m=DATA.metrics,hb=m.heartbeat,h='<header><div class="hero"><div><div class="eyebrow">'+esc(t("eyebrow"))+
'</div><h1>'+esc(t("h1"))+'</h1><p class="tagline">'+esc(t("tagline"))+'</p></div><div class="meta"><span>'+
t("generated")+': <b>'+when(DATA.generated)+'</b></span><span>'+t("heartbeat")+': <b>'+(hb&&hb.status==="ok"?
num(hb.value)+" "+t("min_ago"):t("missing"))+'</b></span>';
if(m.health)h+='<span>'+t("health")+': <b style="color:var(--'+(m.health.value==="up"?"works":"fails")+')">'+
value(m.health)+'</b></span>';
h+='<button id="lang">'+esc(t("lang"))+'</button></div></div>'+chips()+'<p class="prov">'+esc(t("prov"))+' '+
esc(SERVED?t("served_page"):t("file_page"))+'</p>';
if(DATA.blind&&DATA.blind.active)h+='<div class="band" role="note"><b>'+t("blind")+'</b>: '+esc(L(DATA.blind.note))+
' '+t("blind_opens")+': <b>'+when(DATA.blind.until,true)+'</b>.</div>';
h+='</header><div class="grid"><div class="panel'+(BRAIN?' brainbox':'')+'">'+brain()+'</div><div class="panel" '+
'id="card" aria-live="polite">'+card()+'</div></div><h2>'+t("scorecard")+'</h2>'+table()+'<h2>'+t("vitals")+
'</h2>'+vitals()+'<h2>'+t("sources")+'</h2>'+srcs()+'<footer>Living Runtime · mind '+esc(T.version||"")+
'</footer>';
document.getElementById("app").innerHTML=h;document.documentElement.lang=LANG;document.title=t("title");
wire();}
function pick(id,from){SEL=id;render();var c=document.getElementById("card");
if(c&&c.scrollIntoView&&from!=="node")c.scrollIntoView({block:"nearest"});
var f=from==="node"?document.querySelector('.node[data-id="'+id+'"]'):document.getElementById("closecard");
if(f&&f.focus)f.focus({preventScroll:from==="node"});
if(from==="node"&&c&&c.getBoundingClientRect().top>window.innerHeight-80)c.scrollIntoView({block:"start"});}
function wire(){
Array.prototype.forEach.call(document.querySelectorAll(".node"),function(g){var id=+g.getAttribute("data-id");
g.addEventListener("click",function(){pick(id,"node");});g.addEventListener("keydown",function(e){
if(e.key==="Enter"||e.key===" "){e.preventDefault();pick(id,"node");}});});
Array.prototype.forEach.call(document.querySelectorAll("tr.aimrow,button.aimbtn"),function(r){
r.addEventListener("click",function(){pick(+r.getAttribute("data-id"),"list");});});
var c=document.getElementById("closecard");if(c)c.addEventListener("click",function(){SEL=null;render();});
document.getElementById("lang").addEventListener("click",function(){LANG=LANG==="tr"?"en":"tr";render();});}
render();
if(SERVED)setInterval(function(){fetch("data.json",{cache:"no-store"}).then(function(r){return r.json();})
.then(function(d){DATA=d;render();}).catch(function(){});},60000);
})();
</script>
</body>
</html>
"""


def _embed(obj) -> str:
    """JSON that is safe inside a <script> element."""
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&",
                                                                                                    "\\u0026")


def brain_uri(path: Path = BRAIN) -> str:
    """The painted brain as a data: URI (it travels inside the page; nothing is fetched), or "" when the file is not
    there, and the page draws its own outline instead."""
    try:
        return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return ""


def page(data: dict, lang: str = "en", served: bool = False, brain: Path = BRAIN) -> str:
    from . import __version__
    lang = lang if lang in TEXT else "en"
    text = {"ui": TEXT, "status": STATUS, "labels": {k: list(v) for k, v in LABELS.items()},
            "units": {k: list(v) for k, v in UNITS.items()}, "brain": brain_uri(brain), "version": __version__}
    html = TEMPLATE.replace("__NOJS__", TEXT[lang]["nojs"]).replace("__SERVED__", "true" if served else "false")
    html = html.replace("__LANG__", lang).replace("__TEXT__", _embed(text))
    return html.replace("__DATA__", _embed(data))

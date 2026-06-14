#!/usr/bin/env python3
"""Merge vsr_radar.html (dashboard) + vsr_topic_map.html (scatter) into a single
tabbed app: vsr_dashboard.html. Both standalone files are left untouched."""
import json

def grab(path, start_tok, end_tok):
    h = open(path, encoding="utf-8").read()
    s = h.index(start_tok) + len(start_tok)
    e = h.index(end_tok, s)
    return json.loads(h[s:e])

def main():
    radar = grab("vsr_radar.html", "const EMBEDDED = ", ";\n\nlet DB =")
    mapd  = grab("vsr_topic_map.html", "const D = ", ";\nconst cv=")
    EMB = {
        "papers": radar["papers"],
        "taxonomy": radar["taxonomy"],
        "lastRefresh": radar.get("lastRefresh"),
        "newIds": radar.get("newIds", []),
        "map": mapd,
    }
    blob = json.dumps(EMB, ensure_ascii=False).replace("</", "<\\/")
    open("vsr_dashboard.html", "w", encoding="utf-8").write(
        TEMPLATE.replace("/*__DATA__*/", "const EMBEDDED = " + blob + ";"))
    print(f"[ok] vsr_dashboard.html: {len(EMB['papers'])} papers, map={mapd['method']}")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vector Search Research Radar</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root{--bg:#0B0F14;--panel:#121821;--panel-2:#0F141B;--line:#1E2935;--text:#E6EDF3;--muted:#8B98A8;--muted-2:#5C6878;
    --cyan:#3FC9DE;--amber:#F2A93B;--hot:#FF6B5B;--green:#5BD68A;
    --sans:'Inter',system-ui,sans-serif;--display:'Space Grotesk',var(--sans);--mono:'JetBrains Mono',ui-monospace,monospace;}
  *{box-sizing:border-box;} html,body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);-webkit-font-smoothing:antialiased;}
  a{color:var(--cyan);text-decoration:none;} a:hover{text-decoration:underline;}
  button{font-family:var(--sans);cursor:pointer;border:none;background:none;color:inherit;}
  button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--cyan);outline-offset:2px;}
  .wrap{max-width:1180px;margin:0 auto;padding:26px 22px 70px;}
  header.top{display:flex;flex-wrap:wrap;align-items:flex-end;gap:18px;}
  .brand{flex:1 1 300px;min-width:260px;}
  .eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--cyan);margin:0 0 6px;}
  h1{font-family:var(--display);font-weight:700;font-size:clamp(24px,4.2vw,38px);line-height:1.02;margin:0;letter-spacing:-.015em;}
  h1 .dim{color:var(--muted-2);}
  .sub{margin:9px 0 0;color:var(--muted);font-size:13px;max-width:52ch;}
  .controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;}
  .ctl{display:flex;align-items:center;gap:7px;font-family:var(--mono);font-size:12px;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:8px 11px;}
  .ctl label{color:var(--muted-2);text-transform:uppercase;letter-spacing:.08em;font-size:10.5px;}
  select{font-family:var(--mono);font-size:12px;color:var(--text);background:transparent;border:none;cursor:pointer;}
  select option{background:var(--panel);color:var(--text);}
  .scan-btn{font-family:var(--display);font-weight:600;font-size:14px;color:#071017;background:linear-gradient(120deg,var(--cyan),#7be0ed);border-radius:9px;padding:11px 18px;display:flex;align-items:center;gap:9px;letter-spacing:.01em;box-shadow:0 0 0 1px rgba(63,201,222,.25);transition:transform .12s ease,filter .12s ease;}
  .scan-btn:hover{filter:brightness(1.06);} .scan-btn:active{transform:translateY(1px);}
  .scan-btn[disabled]{filter:grayscale(.5) brightness(.7);cursor:wait;}
  .scan-btn .rdot{width:8px;height:8px;border-radius:50%;background:#071017;}
  .scan-btn.busy .rdot{animation:blink .9s infinite;}
  @keyframes blink{50%{opacity:.25;}}
  .refresh-status{font-family:var(--mono);font-size:11px;color:var(--muted-2);align-self:center;}
  /* tabs */
  .tabs{display:flex;gap:4px;margin-top:20px;border-bottom:1px solid var(--line);}
  .tab{font-family:var(--display);font-weight:600;font-size:14px;letter-spacing:.02em;color:var(--muted-2);
    padding:11px 18px;border-bottom:2px solid transparent;margin-bottom:-1px;}
  .tab:hover{color:var(--text);}
  .tab.active{color:var(--text);border-bottom-color:var(--cyan);}
  .view{display:none;} .view.active{display:block;}
  /* statusbar */
  .statusbar{display:flex;flex-wrap:wrap;margin-top:20px;border:1px solid var(--line);border-radius:11px;overflow:hidden;background:var(--panel-2);}
  .stat{flex:1 1 130px;padding:13px 16px;border-right:1px solid var(--line);min-width:120px;}
  .stat:last-child{border-right:none;}
  .stat .k{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted-2);margin-bottom:5px;}
  .stat .v{font-family:var(--display);font-weight:600;font-size:21px;letter-spacing:-.01em;}
  .stat .v small{font-family:var(--mono);font-weight:400;font-size:12px;color:var(--muted);}
  .grid{display:grid;grid-template-columns:1.55fr 1fr;gap:22px;margin-top:22px;}
  @media(max-width:880px){.grid{grid-template-columns:1fr;}}
  .col-head{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:14px;}
  .col-head h2{font-family:var(--display);font-weight:600;font-size:15px;letter-spacing:.02em;margin:0;text-transform:uppercase;}
  .col-head .hint{font-family:var(--mono);font-size:11px;color:var(--muted-2);}
  .filterrow{display:flex;gap:9px;margin-bottom:14px;}
  .filterrow input{flex:1;background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:9px 12px;color:var(--text);font-family:var(--mono);font-size:12.5px;}
  .filterrow input::placeholder{color:var(--muted-2);}
  .toggle{display:flex;align-items:center;gap:7px;font-family:var(--mono);font-size:11.5px;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:0 12px;white-space:nowrap;}
  .toggle input{accent-color:var(--amber);}
  .clusters{display:flex;flex-direction:column;gap:7px;}
  .cluster{border:1px solid var(--line);border-radius:11px;background:var(--panel-2);overflow:hidden;transition:border-color .15s ease;}
  .cluster:hover{border-color:#2a3a4a;}
  .crow{display:grid;grid-template-columns:30px 1fr auto;gap:14px;align-items:center;padding:13px 15px;cursor:pointer;width:100%;text-align:left;}
  .rank{font-family:var(--mono);font-size:12px;color:var(--muted-2);font-weight:500;}
  .cmid{min-width:0;}
  .cname{font-family:var(--display);font-weight:600;font-size:14.5px;display:flex;align-items:center;gap:9px;}
  .delta{font-family:var(--mono);font-size:11px;font-weight:700;padding:1px 6px;border-radius:5px;}
  .delta.up{color:var(--hot);background:rgba(255,107,91,.12);}
  .delta.flat{color:var(--muted);background:rgba(139,152,168,.1);}
  .delta.down{color:var(--cyan);background:rgba(63,201,222,.1);}
  .terms{font-family:var(--mono);font-size:11px;color:var(--muted-2);margin-top:5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .track{position:relative;height:7px;border-radius:4px;background:var(--line);margin-top:9px;overflow:hidden;}
  .track .prior{position:absolute;top:0;left:0;height:100%;background:rgba(255,255,255,.07);border-radius:4px;}
  .track .recent{position:absolute;top:0;left:0;height:100%;border-radius:4px;transition:width .6s cubic-bezier(.2,.8,.2,1);}
  .cright{text-align:right;display:flex;flex-direction:column;align-items:flex-end;gap:2px;}
  .ccount{font-family:var(--display);font-weight:700;font-size:20px;line-height:1;}
  .csub{font-family:var(--mono);font-size:10px;color:var(--muted-2);letter-spacing:.06em;}
  .chev{color:var(--muted-2);font-size:11px;transition:transform .2s ease;font-family:var(--mono);}
  .cluster.open .chev{transform:rotate(90deg);}
  .papers{display:none;border-top:1px solid var(--line);padding:6px 15px 12px;}
  .cluster.open .papers{display:block;}
  .paper{padding:11px 0;border-bottom:1px dashed var(--line);}
  .paper:last-child{border-bottom:none;}
  .ptitle{font-size:13.5px;font-weight:500;line-height:1.35;}
  .ptitle .new,.fitem .new{display:inline-block;font-family:var(--mono);font-size:9px;font-weight:700;color:#071017;background:var(--amber);border-radius:4px;padding:1px 5px;margin-right:7px;letter-spacing:.08em;vertical-align:middle;}
  .pmeta{font-family:var(--mono);font-size:11px;color:var(--muted-2);margin-top:5px;display:flex;flex-wrap:wrap;gap:5px 12px;}
  .pmeta .cat{color:var(--cyan);}
  .pabs{font-size:12px;color:var(--muted);margin-top:6px;line-height:1.5;display:none;}
  .paper.exp .pabs{display:block;}
  .ptoggle{font-family:var(--mono);font-size:10.5px;color:var(--muted-2);margin-top:5px;text-transform:uppercase;letter-spacing:.08em;cursor:pointer;}
  .feed{display:flex;flex-direction:column;border:1px solid var(--line);border-radius:11px;background:var(--panel-2);overflow:hidden;}
  .fitem{padding:12px 15px;border-bottom:1px solid var(--line);}
  .fitem:last-child{border-bottom:none;}
  .fitem .ft{font-size:13px;font-weight:500;line-height:1.35;}
  .fitem .fm{font-family:var(--mono);font-size:10.5px;color:var(--muted-2);margin-top:5px;display:flex;flex-wrap:wrap;gap:4px 10px;}
  .fitem .fm .dot{color:var(--cyan);}
  .fitem .tag{font-family:var(--mono);font-size:9.5px;color:var(--amber);text-transform:uppercase;letter-spacing:.06em;}
  .empty{padding:38px 20px;text-align:center;color:var(--muted-2);border:1px dashed var(--line);border-radius:11px;font-size:13.5px;}
  .empty .big{font-family:var(--display);font-size:16px;color:var(--muted);margin-bottom:6px;}
  /* map */
  .mapnote{color:var(--muted);font-size:13px;margin:18px 0 0;max-width:64ch;} .mapnote b{color:var(--text);}
  .stage{display:grid;grid-template-columns:1fr 240px;gap:18px;margin-top:16px;}
  @media(max-width:820px){.stage{grid-template-columns:1fr;}}
  .canvaswrap{position:relative;border:1px solid var(--line);border-radius:14px;background:radial-gradient(120% 120% at 30% 20%, #10171F 0%, #0B0F14 60%);overflow:hidden;aspect-ratio:1.35;}
  canvas{display:block;width:100%;height:100%;cursor:crosshair;}
  .mhud{position:absolute;left:12px;top:12px;font-family:var(--mono);font-size:10.5px;color:var(--muted-2);letter-spacing:.08em;text-transform:uppercase;pointer-events:none;}
  .mhint{position:absolute;right:12px;bottom:10px;font-family:var(--mono);font-size:10px;color:var(--muted-2);pointer-events:none;}
  .tip{position:absolute;pointer-events:none;display:none;max-width:280px;background:#0E141Bdd;backdrop-filter:blur(4px);border:1px solid var(--line);border-radius:9px;padding:9px 11px;font-size:12px;line-height:1.4;z-index:5;box-shadow:0 8px 24px #0008;}
  .tip .tt{font-weight:600;font-size:12.5px;margin-bottom:4px;}
  .tip .tm{font-family:var(--mono);font-size:10px;color:var(--muted-2);display:flex;gap:8px;flex-wrap:wrap;}
  .tip .tc{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:5px;vertical-align:middle;}
  .legend{border:1px solid var(--line);border-radius:14px;background:var(--panel);padding:14px;align-self:start;}
  .legend h2{font-family:var(--display);font-size:13px;text-transform:uppercase;letter-spacing:.06em;margin:0 0 10px;}
  .leg{display:flex;align-items:center;gap:9px;padding:5px 0;cursor:pointer;font-size:12.5px;user-select:none;}
  .leg:hover{color:#fff;} .leg.off{opacity:.32;}
  .sw{width:11px;height:11px;border-radius:3px;flex:none;}
  .leg .ln{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .leg .lc{font-family:var(--mono);font-size:11px;color:var(--muted-2);}
  .legtools{display:flex;gap:8px;margin-top:12px;font-family:var(--mono);font-size:10.5px;}
  .legtools button{flex:1;background:#0E141B;border:1px solid var(--line);color:var(--muted);border-radius:7px;padding:6px;cursor:pointer;}
  .legtools button:hover{color:var(--text);border-color:#2a3a4a;}
  footer{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);font-family:var(--mono);font-size:11px;color:var(--muted-2);display:flex;flex-wrap:wrap;gap:6px 18px;justify-content:space-between;}
</style></head>
<body><div class="wrap">
  <header class="top">
    <div class="brand">
      <p class="eyebrow">arXiv snapshot &middot; vector search intelligence</p>
      <h1>Research Radar <span class="dim">/ VS</span></h1>
      <p class="sub">Recent arXiv submissions across vector search: ranked by momentum, mapped by similarity, new papers flagged.</p>
    </div>
    <div class="controls">
      <div class="ctl"><label for="window">window</label>
        <select id="window"><option value="30">30d</option><option value="90" selected>90d</option><option value="180">180d</option><option value="365">365d</option></select></div>
      <button class="scan-btn" id="refreshBtn"><span class="rdot"></span>Refresh</button>
      <span class="refresh-status" id="refreshStatus"></span>
    </div>
  </header>

  <div class="tabs">
    <button class="tab active" data-view="radar">Rising Topics</button>
    <button class="tab" data-view="map">Topic Map</button>
  </div>

  <!-- RADAR VIEW -->
  <div class="view active" id="view-radar">
    <div class="statusbar">
      <div class="stat"><div class="k">Snapshot</div><div class="v" id="stLast">&mdash;</div></div>
      <div class="stat"><div class="k">Papers in DB</div><div class="v" id="stCount">0</div></div>
      <div class="stat"><div class="k">New this run</div><div class="v" id="stNew">0</div></div>
      <div class="stat"><div class="k">Active topics</div><div class="v" id="stTopics">0</div></div>
      <div class="stat"><div class="k">Top mover</div><div class="v" id="stMover" style="font-size:14px;">&mdash;</div></div>
    </div>
    <div class="grid">
      <section>
        <div class="col-head"><h2>Rising Topics</h2><span class="hint">ranked by <span id="winLabel">90</span>d volume &middot; &#9650; vs prior period</span></div>
        <div class="filterrow"><input id="filter" type="text" placeholder="filter by keyword in title / abstract&hellip;" autocomplete="off"><label class="toggle"><input type="checkbox" id="newOnly"> new only</label></div>
        <div class="clusters" id="clusters"></div>
        <div class="empty" id="emptyClusters" style="display:none;"><div class="big">No data</div>Run the script to populate the radar.</div>
      </section>
      <section>
        <div class="col-head"><h2>Newest Drops</h2><span class="hint">most recent first</span></div>
        <div class="feed" id="feed"></div>
        <div class="empty" id="emptyFeed" style="display:none;margin-top:0;">No papers.</div>
      </section>
    </div>
  </div>

  <!-- MAP VIEW -->
  <div class="view" id="view-map">
    <p class="mapnote">Each dot is a paper, placed by text similarity (<b id="m1"></b>). Nearby dots discuss similar work; colour is the assigned topic. Hover for title, click to open on arXiv, toggle topics in the legend.</p>
    <div class="stage">
      <div class="canvaswrap">
        <canvas id="cv"></canvas>
        <div class="mhud" id="mhud"></div>
        <div class="mhint">scroll = zoom &middot; drag = pan &middot; click dot = open</div>
        <div class="tip" id="tip"></div>
      </div>
      <div class="legend"><h2>Topics</h2><div id="legend"></div>
        <div class="legtools"><button id="allOn">all</button><button id="reset">reset view</button></div></div>
    </div>
  </div>

  <footer><span>Source: arxiv.org &middot; clustering = keyword taxonomy &middot; map = TF-IDF\u2192SVD\u2192<span id="footm"></span></span><span id="dbnote"></span></footer>
</div>
<script>
"use strict";
/*__DATA__*/

/* ---------------- shared ---------------- */
let DB=(EMBEDDED.papers||[]).slice();
const TAXONOMY=EMBEDDED.taxonomy||[];
const newThisScan=new Set(EMBEDDED.newIds||[]);
const lastRefresh=EMBEDDED.lastRefresh||null;
const TAXMAP={};TAXONOMY.forEach(t=>TAXMAP[t.id]=t);
const $=id=>document.getElementById(id);
function daysAgo(n){const d=new Date();d.setDate(d.getDate()-n);return d;}
function within(iso,days){return new Date(iso)>=daysAgo(days);}
function fmtDate(iso){const d=new Date(iso);return d.toLocaleDateString(undefined,{month:"short",day:"numeric",year:"2-digit"});}
function esc(s){return (s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function heatColor(t){const c1=[63,201,222],c2=[242,169,59],c3=[255,107,91];let a,b,f;
  if(t<0.5){a=c1;b=c2;f=t/0.5;}else{a=c2;b=c3;f=(t-0.5)/0.5;}
  const m=i=>Math.round(a[i]+(b[i]-a[i])*f);return `rgb(${m(0)},${m(1)},${m(2)})`;}

/* ---------------- radar ---------------- */
function buildClusters(){
  const win=parseInt($("window").value,10);const filter=$("filter").value.trim().toLowerCase();const newOnly=$("newOnly").checked;
  const pass=p=>{if(newOnly&&!newThisScan.has(p.id))return false;if(filter&&!((p.title+" "+p.abstract).toLowerCase().includes(filter)))return false;return true;};
  const map={};TAXONOMY.forEach(t=>map[t.id]={def:t,recent:[],prior:[],all:[]});
  map["_other"]={def:{id:"_other",name:"Uncategorized / Adjacent",kw:[]},recent:[],prior:[],all:[]};
  for(const p of DB){if(!pass(p))continue;const b=map[p.cluster]||map["_other"];b.all.push(p);
    if(within(p.published,win))b.recent.push(p);else if(new Date(p.published)>=daysAgo(win*2))b.prior.push(p);}
  const arr=Object.values(map).filter(b=>b.all.length>0);
  arr.forEach(b=>{b.recentN=b.recent.length;b.priorN=b.prior.length;b.allN=b.all.length;b.delta=b.recentN-b.priorN;});
  arr.sort((a,b)=>b.recentN-a.recentN||b.allN-a.allN);return arr;}
function paperRow(p){return `<div class="paper"><div class="ptitle">${newThisScan.has(p.id)?'<span class="new">NEW</span>':""}<a href="${p.link}" target="_blank" rel="noopener">${esc(p.title)}</a></div>
  <div class="pmeta"><span>${fmtDate(p.published)}</span><span>${esc((p.authors||[]).slice(0,3).join(", "))}${p.authors&&p.authors.length>3?" +"+(p.authors.length-3):""}</span><span class="cat">${esc((p.categories||[]).slice(0,3).join(" \u00b7 "))}</span></div>
  <div class="pabs">${esc(p.abstract)}</div><div class="ptoggle">show abstract</div></div>`;}
function renderRadar(){
  $("stLast").innerHTML=lastRefresh?`<small>${new Date(lastRefresh).toLocaleString(undefined,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})}</small>`:"&mdash;";
  $("stCount").textContent=DB.length;$("stNew").textContent=newThisScan.size;$("winLabel").textContent=$("window").value;$("dbnote").textContent=DB.length+" papers cached";
  const clusters=buildClusters();const maxRecent=Math.max(1,...clusters.map(c=>c.recentN));
  $("stTopics").textContent=clusters.filter(c=>c.def.id!=="_other"&&c.recentN>0).length;
  const mover=clusters.filter(c=>c.def.id!=="_other").slice().sort((a,b)=>b.delta-a.delta)[0];
  $("stMover").innerHTML=mover&&mover.delta>0?esc(mover.def.name)+` <small style="color:var(--hot)">\u25b2${mover.delta}</small>`:"&mdash;";
  const host=$("clusters");$("emptyClusters").style.display=clusters.length?"none":"block";
  host.innerHTML=clusters.map((c,i)=>{
    const heat=c.recentN/maxRecent;const col=c.def.id==="_other"?"var(--muted-2)":heatColor(heat);
    const recentW=Math.max(3,Math.round(heat*100));const priorW=Math.min(100,Math.round((c.priorN/maxRecent)*100));
    let dcls="flat",dtxt="\u00b10";if(c.delta>0){dcls="up";dtxt="\u25b2"+c.delta;}else if(c.delta<0){dcls="down";dtxt="\u25bc"+Math.abs(c.delta);}
    const terms=(c.def.kw||[]).slice(0,6).join(" \u00b7 ")||"no fixed keywords";
    const recentPapers=c.recent.slice().sort((a,b)=>b.published.localeCompare(a.published));
    const olderPapers=c.all.slice().sort((a,b)=>b.published.localeCompare(a.published)).filter(p=>!recentPapers.includes(p));
    return `<div class="cluster" data-i="${i}"><button class="crow" aria-expanded="false"><span class="rank">${String(i+1).padStart(2,"0")}</span>
      <span class="cmid"><span class="cname">${esc(c.def.name)} <span class="delta ${dcls}">${dtxt}</span></span><span class="terms">${esc(terms)}</span>
      <span class="track"><span class="prior" style="width:${priorW}%"></span><span class="recent" style="width:${recentW}%;background:${col}"></span></span></span>
      <span class="cright"><span class="ccount" style="color:${col}">${c.recentN}</span><span class="csub">${c.allN} total <span class="chev">\u25b6</span></span></span></button>
      <div class="papers">${recentPapers.map(paperRow).join("")}${olderPapers.length?`<div class="show-all-toggle" style="padding:8px 0;cursor:pointer;color:var(--muted-2);font-size:12px">+ ${olderPapers.length} older papers</div><div class="older-papers" style="display:none">${olderPapers.map(paperRow).join("")}</div>`:""}</div></div>`;}).join("");
  host.querySelectorAll(".cluster").forEach(el=>{
    const btn=el.querySelector(".crow");btn.addEventListener("click",()=>{const o=el.classList.toggle("open");btn.setAttribute("aria-expanded",o?"true":"false");});
    const tog=el.querySelector(".show-all-toggle");if(tog){const older=el.querySelector(".older-papers");tog.addEventListener("click",e=>{e.stopPropagation();const x=older.style.display==="none";older.style.display=x?"block":"none";tog.textContent=x?"- hide older papers":"+ "+older.querySelectorAll(".paper").length+" older papers";});}
  });
  host.querySelectorAll(".paper").forEach(el=>{const tg=el.querySelector(".ptoggle");if(tg)tg.addEventListener("click",e=>{e.stopPropagation();const x=el.classList.toggle("exp");tg.textContent=x?"hide abstract":"show abstract";});});
  const feedHost=$("feed");
  const feed=DB.slice().filter(p=>{if($("newOnly").checked&&!newThisScan.has(p.id))return false;const f=$("filter").value.trim().toLowerCase();if(f&&!((p.title+" "+p.abstract).toLowerCase().includes(f)))return false;return true;}).sort((a,b)=>b.published.localeCompare(a.published)).slice(0,30);
  $("emptyFeed").style.display=feed.length?"none":"block";feedHost.style.display=feed.length?"flex":"none";
  feedHost.innerHTML=feed.map(p=>{const cl=TAXMAP[p.cluster];return `<div class="fitem"><div class="ft">${newThisScan.has(p.id)?'<span class="new">NEW</span>':""}<a href="${p.link}" target="_blank" rel="noopener">${esc(p.title)}</a></div>
    <div class="fm"><span class="dot">${fmtDate(p.published)}</span><span class="tag">${esc(cl?cl.name:"adjacent")}</span><span>${esc((p.categories||[]).slice(0,3).join(", "))}</span></div></div>`;}).join("");}
["window"].forEach(id=>$(id).addEventListener("change",renderRadar));
$("filter").addEventListener("input",renderRadar);$("newOnly").addEventListener("change",renderRadar);

/* ---------------- map ---------------- */
const D=EMBEDDED.map;const cv=$("cv"),ctx=cv.getContext('2d'),tip=$("tip");
const moff=new Set();let view={s:1,ox:0,oy:0},drag=null,W=0,Hh=0,mapInit=false;
$("m1").textContent=D.method+" on TF-IDF features";$("mhud").textContent=D.method+" \u00b7 "+D.total+" papers";$("footm").textContent=D.method;
function mresize(){const r=cv.getBoundingClientRect();if(!r.width)return;const dpr=devicePixelRatio||1;cv.width=r.width*dpr;cv.height=r.height*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);W=r.width;Hh=r.height;mdraw();}
function MP(p){const pad=34;const x=pad+p.x*(W-2*pad),y=pad+(1-p.y)*(Hh-2*pad);return [x*view.s+view.ox,y*view.s+view.oy];}
function mdraw(){ctx.clearRect(0,0,W,Hh);
  for(const pass of [0,1]){for(const p of D.points){const o=moff.has(p.c);if(pass===0&&!o)continue;if(pass===1&&o)continue;
    const [x,y]=MP(p);if(x<-20||x>W+20||y<-20||y>Hh+20)continue;const col=(D.legend.find(l=>l.id===p.c)||{}).color||'#4A5666';
    ctx.beginPath();ctx.arc(x,y,o?2:3.4,0,7);ctx.fillStyle=o?'rgba(74,86,102,.25)':col;ctx.globalAlpha=o?.5:.92;ctx.fill();}}
  ctx.globalAlpha=1;ctx.font="600 11px 'Space Grotesk',sans-serif";ctx.textAlign="center";
  for(const l of D.legend){if(l.id==="_other"||moff.has(l.id)||l.n<4)continue;const ps=D.points.filter(p=>p.c===l.id);
    let mx=0,my=0;for(const p of ps){const[a,b]=MP(p);mx+=a;my+=b;}mx/=ps.length;my/=ps.length;
    ctx.fillStyle="#0B0F14";ctx.globalAlpha=.55;const w=ctx.measureText(l.name).width+10;ctx.fillRect(mx-w/2,my-15,w,15);ctx.globalAlpha=1;
    ctx.fillStyle=l.color;ctx.fillText(l.name,mx,my-4);}}
function mnear(mx,my){let best=null,bd=14*14;for(const p of D.points){if(moff.has(p.c))continue;const[x,y]=MP(p);const d=(x-mx)*(x-mx)+(y-my)*(y-my);if(d<bd){bd=d;best=p;}}return best;}
cv.addEventListener('mousemove',e=>{const r=cv.getBoundingClientRect();const mx=e.clientX-r.left,my=e.clientY-r.top;
  if(drag){view.ox=drag.ox+(mx-drag.x);view.oy=drag.oy+(my-drag.y);mdraw();return;}
  const p=mnear(mx,my);if(p){const col=(D.legend.find(l=>l.id===p.c)||{});
    tip.innerHTML=`<div class="tt">${p.t.replace(/</g,'&lt;')}</div><div class="tm"><span><span class="tc" style="background:${col.color}"></span>${col.name}</span><span>${p.d}</span><span>${p.cat}</span></div>`;
    tip.style.display='block';let tx=mx+14,ty=my+14;if(tx>W-290)tx=mx-294;if(ty>Hh-80)ty=my-80;tip.style.left=tx+'px';tip.style.top=ty+'px';cv.style.cursor='pointer';}
  else{tip.style.display='none';cv.style.cursor='crosshair';}});
cv.addEventListener('mouseleave',()=>tip.style.display='none');
cv.addEventListener('mousedown',e=>{const r=cv.getBoundingClientRect();drag={x:e.clientX-r.left,y:e.clientY-r.top,ox:view.ox,oy:view.oy};});
window.addEventListener('mouseup',e=>{if(drag){const r=cv.getBoundingClientRect();const mx=e.clientX-r.left,my=e.clientY-r.top;if(Math.abs(mx-drag.x)<3&&Math.abs(my-drag.y)<3){const p=mnear(mx,my);if(p)window.open(p.u,'_blank');}}drag=null;});
cv.addEventListener('wheel',e=>{e.preventDefault();const r=cv.getBoundingClientRect();const mx=e.clientX-r.left,my=e.clientY-r.top;const f=e.deltaY<0?1.12:1/1.12;view.ox=mx-(mx-view.ox)*f;view.oy=my-(my-view.oy)*f;view.s*=f;mdraw();},{passive:false});
const lg=$("legend");
lg.innerHTML=D.legend.map(l=>`<div class="leg" data-id="${l.id}"><span class="sw" style="background:${l.color}"></span><span class="ln">${l.name}</span><span class="lc">${l.n}</span></div>`).join('');
lg.querySelectorAll('.leg').forEach(el=>el.addEventListener('click',()=>{const id=el.dataset.id;if(moff.has(id)){moff.delete(id);el.classList.remove('off');}else{moff.add(id);el.classList.add('off');}mdraw();}));
$("allOn").onclick=()=>{moff.clear();lg.querySelectorAll('.leg').forEach(e=>e.classList.remove('off'));mdraw();};
$("reset").onclick=()=>{view={s:1,ox:0,oy:0};mdraw();};

/* ---------------- tabs ---------------- */
document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('.view').forEach(x=>x.classList.remove('active'));
  t.classList.add('active');const v=t.dataset.view;$("view-"+v).classList.add('active');
  if(v==="map"){ if(!mapInit){mapInit=true;new ResizeObserver(mresize).observe(cv);} mresize(); }
}));

renderRadar();

/* ---------------- refresh (requires local server) ---------------- */
const rb=$("refreshBtn");
if(location.protocol==="file:"){
  $("refreshStatus").textContent="Open via serve.py to enable Refresh";
}
rb.addEventListener('click',async()=>{
  if(location.protocol==="file:"){
    $("refreshStatus").textContent="Refresh needs the server \u2014 run: python serve.py, then use the localhost tab";
    return;
  }
  rb.disabled=true;rb.classList.add('busy');$("refreshStatus").textContent="Refreshing\u2026 (this can take ~30\u201360s)";
  try{
    const r=await fetch('/refresh',{method:'POST'});
    const j=await r.json();
    if(j&&j.ok){$("refreshStatus").textContent="Updated \u2014 reloading\u2026";setTimeout(()=>location.reload(),400);}
    else{$("refreshStatus").textContent="Refresh failed \u2014 check the server window.";rb.disabled=false;rb.classList.remove('busy');}
  }catch(e){
    $("refreshStatus").textContent="Refresh service not running \u2014 start serve.py.";rb.disabled=false;rb.classList.remove('busy');
  }
});
</script></body></html>"""


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Topic map: project the vector-search paper corpus to 2D and render an
interactive scatter (dots = papers, colour = topic cluster).

Embedding: TF-IDF(title x2 + abstract) -> TruncatedSVD(50) -> t-SNE(2).
If umap-learn is importable it uses UMAP instead (set USE_UMAP). The method
actually used is printed on the plot so the label is never wrong.

To use TRUE UMAP locally:  pip install umap-learn  then run with --umap
"""
import json, re, sys, argparse
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.manifold import TSNE
from sklearn.preprocessing import normalize

SRC = "vsr_radar.html"
OUT = "vsr_topic_map.html"

# topic -> colour (distinct, tuned for dark bg). _other muted grey.
COLORS = {
    "rag":"#FF6B5B","quant":"#F2A93B","gpu":"#5BD68A","dense":"#3FC9DE",
    "graph":"#A98BFF","theory":"#E36FB0","scale":"#FFD24A","system":"#6FE0C8",
    "multimodal":"#FF9F6E","sparse":"#8FD14F","filter":"#5BA8FF","multivec":"#D98CFF",
    "stream":"#4FE3B0","mips":"#F26D9E","_other":"#4A5666","datamine":"#C9B037",
    "recsys":"#7AA2FF","hashing":"#E08CCB","privacy":"#9AD17B","general":"#6B7A8F",
}

def load_papers(path):
    h = open(path, encoding="utf-8").read()
    s = h.index("const EMBEDDED = ") + len("const EMBEDDED = ")
    e = h.index(";\n\nlet DB =")
    d = json.loads(h[s:e])
    return d["papers"], {t["id"]: t["name"] for t in d["taxonomy"]}

def embed(papers, use_umap):
    texts = [((p.get("title","")+" ")*2 + p.get("abstract","")) for p in papers]
    tfidf = TfidfVectorizer(stop_words="english", min_df=2, max_df=0.6,
                            sublinear_tf=True, ngram_range=(1,2)).fit_transform(texts)
    n = tfidf.shape[0]
    svd = TruncatedSVD(n_components=min(50, tfidf.shape[1]-1, n-1), random_state=42)
    X = normalize(svd.fit_transform(tfidf))
    method = "t-SNE"
    if use_umap:
        try:
            import umap
            xy = umap.UMAP(n_neighbors=15, min_dist=0.12, metric="cosine",
                           random_state=42).fit_transform(X)
            method = "UMAP"
            return xy, method
        except Exception as ex:
            print(f"[warn] UMAP unavailable ({ex}); using t-SNE", file=sys.stderr)
    perp = max(5, min(30, (n - 1)//3))
    xy = TSNE(n_components=2, perplexity=perp, init="pca",
              metric="cosine", random_state=42, max_iter=1000).fit_transform(X)
    return xy, method

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--umap", action="store_true", help="use UMAP if installed")
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    papers, names = load_papers(args.src)
    xy, method = embed(papers, args.umap)

    # normalise coords to 0..1
    xy = np.asarray(xy, float)
    mn, mx = xy.min(0), xy.max(0)
    span = np.where((mx-mn)==0, 1, mx-mn)
    norm = (xy - mn)/span

    # rising rank by count for legend ordering
    from collections import Counter
    cnt = Counter(p["cluster"] for p in papers)
    order = [c for c,_ in cnt.most_common()]

    pts = []
    for i,p in enumerate(papers):
        pts.append({
            "x": round(float(norm[i,0]),4), "y": round(float(norm[i,1]),4),
            "c": p["cluster"], "t": p["title"], "d": p["published"][:10],
            "u": p["link"], "cat": ", ".join(p.get("categories",[])[:3]),
        })
    legend = [{"id":c, "name": names.get(c,"Uncategorized/Adjacent"),
               "color": COLORS.get(c,"#4A5666"), "n": cnt[c]} for c in order]

    data = {"points": pts, "legend": legend, "method": method,
            "total": len(pts)}
    blob = json.dumps(data, ensure_ascii=False).replace("</","<\\/")
    out = TEMPLATE.replace("/*__DATA__*/", "const D = "+blob+";")
    open(args.out,"w",encoding="utf-8").write(out)
    print(f"[ok] method={method}, {len(pts)} points -> {args.out}")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vector Search Topic Map</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root{--bg:#0B0F14;--panel:#121821;--line:#1E2935;--text:#E6EDF3;--muted:#8B98A8;--muted-2:#5C6878;--cyan:#3FC9DE;
    --sans:'Inter',system-ui,sans-serif;--display:'Space Grotesk',var(--sans);--mono:'JetBrains Mono',monospace;}
  *{box-sizing:border-box;} html,body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);-webkit-font-smoothing:antialiased;}
  .wrap{max-width:1180px;margin:0 auto;padding:26px 22px 40px;}
  .eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--cyan);margin:0 0 6px;}
  h1{font-family:var(--display);font-weight:700;font-size:clamp(24px,4vw,36px);margin:0;letter-spacing:-.015em;}
  .sub{margin:9px 0 0;color:var(--muted);font-size:13px;max-width:62ch;}
  .sub b{color:var(--text);}
  .stage{display:grid;grid-template-columns:1fr 240px;gap:18px;margin-top:22px;}
  @media(max-width:820px){.stage{grid-template-columns:1fr;}}
  .canvaswrap{position:relative;border:1px solid var(--line);border-radius:14px;background:
    radial-gradient(120% 120% at 30% 20%, #10171F 0%, #0B0F14 60%);overflow:hidden;aspect-ratio:1.35;}
  canvas{display:block;width:100%;height:100%;cursor:crosshair;}
  .hud{position:absolute;left:12px;top:12px;font-family:var(--mono);font-size:10.5px;color:var(--muted-2);
    letter-spacing:.08em;text-transform:uppercase;pointer-events:none;}
  .hint{position:absolute;right:12px;bottom:10px;font-family:var(--mono);font-size:10px;color:var(--muted-2);pointer-events:none;}
  .tip{position:absolute;pointer-events:none;display:none;max-width:280px;background:#0E141Bdd;backdrop-filter:blur(4px);
    border:1px solid var(--line);border-radius:9px;padding:9px 11px;font-size:12px;line-height:1.4;z-index:5;box-shadow:0 8px 24px #0008;}
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
  footer{margin-top:20px;font-family:var(--mono);font-size:11px;color:var(--muted-2);}
</style></head>
<body><div class="wrap">
  <p class="eyebrow">arXiv corpus &middot; neighbour-embedding projection</p>
  <h1>Vector Search Topic Map</h1>
  <p class="sub">Each dot is a paper, placed by text similarity (<b id="m1"></b>). Nearby dots discuss similar work; colour is the assigned topic. Hover for the title, click to open on arXiv, toggle topics in the legend.</p>
  <div class="stage">
    <div class="canvaswrap">
      <canvas id="cv"></canvas>
      <div class="hud" id="hud"></div>
      <div class="hint">scroll = zoom &middot; drag = pan &middot; click dot = open</div>
      <div class="tip" id="tip"></div>
    </div>
    <div class="legend">
      <h2>Topics</h2>
      <div id="legend"></div>
      <div class="legtools"><button id="allOn">all</button><button id="reset">reset view</button></div>
    </div>
  </div>
  <footer id="foot"></footer>
</div>
<script>
"use strict";
/*__DATA__*/
const cv=document.getElementById('cv'),ctx=cv.getContext('2d');
const tip=document.getElementById('tip');
const off=new Set();
let view={s:1,ox:0,oy:0}; let drag=null;
document.getElementById('m1').textContent=D.method+" on TF-IDF features";
document.getElementById('hud').textContent=D.method+" \u00b7 "+D.total+" papers";
document.getElementById('foot').textContent="Projection: TF-IDF(title\u00d72 + abstract) \u2192 SVD(50) \u2192 "+D.method+"  \u00b7  "+D.total+" papers";

function resize(){const r=cv.getBoundingClientRect();const dpr=devicePixelRatio||1;
  cv.width=r.width*dpr;cv.height=r.height*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);W=r.width;Hh=r.height;draw();}
let W=0,Hh=0;
function P(p){const pad=34;
  const x=pad+(p.x)*(W-2*pad), y=pad+(1-p.y)*(Hh-2*pad);
  return [x*view.s+view.ox, y*view.s+view.oy];}

function draw(){
  ctx.clearRect(0,0,W,Hh);
  // dim dots first (off topics), then active for layering
  for(const pass of [0,1]){
    for(const p of D.points){
      const offt=off.has(p.c);
      if(pass===0 && !offt) continue;
      if(pass===1 && offt) continue;
      const [x,y]=P(p);
      if(x<-20||x>W+20||y<-20||y>Hh+20) continue;
      const col=(D.legend.find(l=>l.id===p.c)||{}).color||'#4A5666';
      ctx.beginPath();ctx.arc(x,y,offt?2:3.4,0,7);
      ctx.fillStyle=offt?'rgba(74,86,102,.25)':col;
      ctx.globalAlpha=offt?.5:.92;ctx.fill();
    }
  }
  ctx.globalAlpha=1;
  // centroid labels for active named topics with >=4 pts
  ctx.font="600 11px 'Space Grotesk',sans-serif";ctx.textAlign="center";
  for(const l of D.legend){
    if(l.id==="_other"||off.has(l.id)||l.n<4) continue;
    const ps=D.points.filter(p=>p.c===l.id);
    let mx=0,my=0;for(const p of ps){const[a,b]=P(p);mx+=a;my+=b;}
    mx/=ps.length;my/=ps.length;
    ctx.fillStyle="#0B0F14";ctx.globalAlpha=.55;
    const w=ctx.measureText(l.name).width+10;
    ctx.fillRect(mx-w/2,my-15,w,15);ctx.globalAlpha=1;
    ctx.fillStyle=l.color;ctx.fillText(l.name,mx,my-4);
  }
}

function nearest(mx,my){let best=null,bd=14*14;
  for(const p of D.points){if(off.has(p.c))continue;const[x,y]=P(p);
    const d=(x-mx)*(x-mx)+(y-my)*(y-my);if(d<bd){bd=d;best=p;}}return best;}

cv.addEventListener('mousemove',e=>{
  const r=cv.getBoundingClientRect();const mx=e.clientX-r.left,my=e.clientY-r.top;
  if(drag){view.ox=drag.ox+(mx-drag.x);view.oy=drag.oy+(my-drag.y);draw();return;}
  const p=nearest(mx,my);
  if(p){const col=(D.legend.find(l=>l.id===p.c)||{});
    tip.innerHTML=`<div class="tt">${p.t.replace(/</g,'&lt;')}</div><div class="tm"><span><span class="tc" style="background:${col.color}"></span>${col.name}</span><span>${p.d}</span><span>${p.cat}</span></div>`;
    tip.style.display='block';
    let tx=mx+14,ty=my+14;if(tx>W-290)tx=mx-294;if(ty>Hh-80)ty=my-80;
    tip.style.left=tx+'px';tip.style.top=ty+'px';cv.style.cursor='pointer';
  }else{tip.style.display='none';cv.style.cursor='crosshair';}
});
cv.addEventListener('mouseleave',()=>tip.style.display='none');
cv.addEventListener('mousedown',e=>{const r=cv.getBoundingClientRect();drag={x:e.clientX-r.left,y:e.clientY-r.top,ox:view.ox,oy:view.oy,moved:false};});
window.addEventListener('mouseup',e=>{
  if(drag){const r=cv.getBoundingClientRect();const mx=e.clientX-r.left,my=e.clientY-r.top;
    if(Math.abs(mx-drag.x)<3&&Math.abs(my-drag.y)<3){const p=nearest(mx,my);if(p)window.open(p.u,'_blank');}}
  drag=null;});
cv.addEventListener('wheel',e=>{e.preventDefault();const r=cv.getBoundingClientRect();
  const mx=e.clientX-r.left,my=e.clientY-r.top;const f=e.deltaY<0?1.12:1/1.12;
  view.ox=mx-(mx-view.ox)*f;view.oy=my-(my-view.oy)*f;view.s*=f;draw();},{passive:false});

// legend
const lg=document.getElementById('legend');
lg.innerHTML=D.legend.map(l=>`<div class="leg" data-id="${l.id}"><span class="sw" style="background:${l.color}"></span><span class="ln">${l.name}</span><span class="lc">${l.n}</span></div>`).join('');
lg.querySelectorAll('.leg').forEach(el=>el.addEventListener('click',()=>{
  const id=el.dataset.id;if(off.has(id)){off.delete(id);el.classList.remove('off');}else{off.add(id);el.classList.add('off');}draw();}));
document.getElementById('allOn').onclick=()=>{off.clear();lg.querySelectorAll('.leg').forEach(e=>e.classList.remove('off'));draw();};
document.getElementById('reset').onclick=()=>{view={s:1,ox:0,oy:0};draw();};

new ResizeObserver(resize).observe(cv);resize();
</script></body></html>"""

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Vector Search Research Radar — arXiv engine.

Fetches recent arXiv submissions across vector-search topics, clusters them by a
hand-built keyword taxonomy, tracks new papers across runs, and emits a
standalone interactive HTML dashboard.

Why server-side: arXiv's API sends no CORS headers, so a browser fetch is blocked.
This script does the fetch server-side (the way arXiv intends) and bakes the data
into the HTML, so the dashboard needs zero network access in the browser.

Zero dependencies (stdlib only). Respects HTTP(S)_PROXY env vars (corp networks).

Usage:
    python vsr_radar.py                 # fetch, cluster, write vsr_radar.html, open it
    python vsr_radar.py --depth 200     # pull up to 200 papers per query
    python vsr_radar.py --no-open       # don't auto-open browser
    python vsr_radar.py --selftest      # no network; render sample data (sanity check)

Refresh = re-run this script. The JSON cache (vsr_db.json) accumulates papers and
lets the dashboard flag what's NEW since your previous run.
"""
import argparse, json, os, re, sys, time, html, webbrowser
import urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# ----------------------------------------------------------------------------
# TAXONOMY — vector-search research buckets, split into two tiers.
#   METHOD = "how the index works" (what cuVS implements). Checked FIRST.
#   APP    = "where retrieval is used". Only used when no METHOD keyword hits.
# This method-first priority stops application terms (RAG/LLM/recsys) from
# swallowing method papers like "dense retrieval for RAG".
# Matching is word-boundary (see classify), so acronyms (rag, llm, lsh, ivf)
# are safe and won't false-match inside words (storage / average / codebook).
# Title hits weigh 3x abstract hits. Edit freely — single source of truth.
# ----------------------------------------------------------------------------
METHOD = [
    ("graph",    "Graph / Tree Indexes",          ["hnsw","navigable small world","proximity graph","graph-based","graph index","nsg","diskann","vamana","cagra","knn graph","greedy search graph","k-d tree","kd-tree","kd tree","ball tree","r-tree","cover tree","metric tree","metric space","reverse k-nearest","reverse nearest","skiplist","skip-list","skip list","query-adaptive","query-dependent"]),
    ("quant",    "Quantization & Compression",    ["product quantization","quantization","quantize","rabitq","scalar quantization","binary embedding","binary code","binary quantization","compression","codebook","residual quantization","opq","low-bit","subspace embedding"]),
    ("hashing",  "Hashing / LSH",                 ["locality-sensitive","locality sensitive","lsh","learning to hash","hash code","minhash","binary hashing"]),
    ("gpu",      "GPU / HW Acceleration",         ["gpu","cuda","cuvs","accelerat","fpga","simd","tensor core","hardware-aware","on-device","tpu","systolic","ray tracing"]),
    ("scale",    "Billion-Scale / Disk",          ["billion-scale","billion scale","disk-based","disk based","ssd","out-of-core","memory-efficient","web-scale","trillion","external memory","disk-oblivious","space efficiency","index storage"]),
    ("filter",   "Filtered Search",               ["filtered search","filtered ann","attribute filter","attribute filtering","predicate","metadata filter","constrained nearest","range filter","range filtering","label filter","filter-aware","filter-agnostic","arbitrary-filtered","aknn"]),
    ("dense",    "Dense / Learned Retrieval",     ["dense retrieval","dense passage","learned index","learned representation","contrastive","representation learning","two-tower","dual encoder","bi-encoder","embedding model","text embedding","retriever training","semantic search","frozen encoder"]),
    ("multivec", "Multi-Vector / Late Interaction",["colbert","late interaction","multi-vector","multi vector","token-level retrieval","maxsim","plaid","multiple query vectors"]),
    ("stream",   "Streaming / Dynamic Index",     ["streaming","incremental index","dynamic index","real-time index","fresh index","online update","mutable index","freshness","dynamic nearest"]),
    ("datamine", "Data Mining / Clustering",      ["data mining","clustering","cluster-based","clustering-based","k-means","kmeans","inverted file","ivf","ivfpq","ivf-pq","coarse quantizer","cluster centroid","balanced clustering","spherical k-means","cell-probe","voronoi","cluster pruning","agglomerative","spectral clustering","dbscan","partition-based","maximal clique","manifold"]),
    ("mips",     "MIPS / Inner-Product",          ["maximum inner product","inner product search","inner-product","mipsearch","reverse mips"]),
    ("sparse",   "Sparse / Lexical Hybrid",       ["sparse retrieval","splade","lexical","bm25","inverted index","learned sparse","term weighting","impact score"]),
    ("theory",   "Recall / Theory / Benchmarks",  ["recall guarantee","theoretical","provable","approximation guarantee","benchmark","lower bound","upper bound","worst-case","ann-benchmarks","performance bounds"]),
    ("system",   "Vector DB / Systems",           ["vector database","vector databases","vector db","vector store","vector dbms","serving system","distributed index","sharding","scalable retrieval system","query engine","milvus","weaviate","elasticsearch","opensearch","pinecone","qdrant","database system"]),
    ("structured","Structured Data & Tables",     ["structured data","tabular","relational","sql","table embedding","column embedding","schema","entity matching","record linkage","join","join ordering","query optimization","data integration","data lake","knowledge base completion","knowledge graph embedding","entity resolution","fuzzy join","semantic join","vector over relational","hybrid relational","structured retrieval","apache iceberg","iceberg","lakehouse","puffin"]),
]
APP = [
    ("rag",        "RAG / Retrieval Augmented",    ["retrieval-augmented","retrieval augmented","augmented generation","grounded generation","rag","generative retrieval","open-domain","question answering","in-context retrieval"]),
    ("llm",        "LLM / Agents",                ["llm","llms","large language model","language model","in-context","agent","agentic","llm-based","llm retrieval","llm-augmented","copilot","chatbot","instruction tuning","fine-tuning","prompt"]),
    ("recsys",     "Recommendation / RecSys",     ["recommendation","recommender","recsys","collaborative filtering","user-item","click-through","candidate generation","item retrieval","personalization"]),
    ("multimodal", "Multimodal / Cross-modal",    ["multimodal","cross-modal","cross modal","image retrieval","text-to-image","clip","video retrieval","audio","speech","vision","point cloud"]),
    ("privacy",    "Privacy / Security",          ["differential privacy","privacy-preserving","privacy preserving","federated","homomorphic","encrypted","secure retrieval","access-aware","authorized"]),
]
TAXONOMY = METHOD + APP   # combined list for rendering (legend + keyword display)

# Scope gate: a paper is in-scope for "vector search" if it mentions any of these.
# In-scope papers that match no specific bucket fall into GENERAL (a labeled
# catch-all). Out-of-scope papers (none of these terms) are dropped at scan time
# as search false-positives, rather than piling up as "uncategorized".
CORE_SCOPE = ["nearest neighbor","nearest-neighbor","vector search","vector retrieval",
    "similarity search","approximate nearest","ann","k-nn","knn","retrieval","retriever",
    "retrievers","embedding","embeddings","vector index","vector database","vector dbms",
    "maximum inner product","semantic","high-dimensional","metric space","similarity join",
    "top-k","passage","reranking","re-ranking","index"]
GENERAL = ("general", "General ANN (unspecified)", ["nearest neighbor","vector search","ann","similarity search","k-nn"])
TAXONOMY = TAXONOMY + [GENERAL]   # GENERAL shown in legend but NOT scored (assigned by fallback)

QUERIES = [
    'all:"vector search" OR all:"approximate nearest neighbor" OR all:"nearest neighbor search"',
    'all:"vector database" OR all:"HNSW" OR all:"DiskANN" OR all:"product quantization"',
    'all:"dense retrieval" OR all:"ColBERT"',
    'all:"maximum inner product search" OR all:"graph-based ANN" OR all:"billion-scale" OR all:"vector index"',
    'all:"structured data" OR all:"tabular" OR all:"semantic join" OR all:"fuzzy join" OR all:"table embedding"',
    'all:"cuvs" OR all:"faiss" OR all:"lucene"',
]

ARXIV = "https://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom"}
DELAY = 3.1          # arXiv etiquette: ~3s between requests
ABS_TRIM = 700
MAX_DB = 2000
CACHE = "vsr_db.json"
OUT = "vsr_radar.html"
UA = "vsr-radar/1.0 (research topic tracker; contact: local user)"


# ----------------------------------------------------------------------------
# fetch + parse
# ----------------------------------------------------------------------------
def fetch_query(q, depth):
    params = urllib.parse.urlencode({
        "search_query": q, "start": 0, "max_results": depth,
        "sortBy": "submittedDate", "sortOrder": "descending",
    })
    req = urllib.request.Request(ARXIV + "?" + params, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return parse_atom(r.read().decode("utf-8", "replace"))


def parse_atom(xml_text):
    out = []
    root = ET.fromstring(xml_text)
    for e in root.findall("a:entry", NS):
        def txt(tag):
            n = e.find("a:" + tag, NS)
            return " ".join(n.text.split()) if n is not None and n.text else ""
        raw_id = txt("id")
        # part after /abs/, strip trailing version (2401.01234v3 -> 2401.01234)
        pid = re.sub(r"v\d+$", "", raw_id.split("/abs/")[-1])
        authors = [a.find("a:name", NS).text.strip()
                   for a in e.findall("a:author", NS)
                   if a.find("a:name", NS) is not None]
        cats = [c.get("term") for c in e.findall("a:category", NS) if c.get("term")]
        abs_ = txt("summary")
        if len(abs_) > ABS_TRIM:
            abs_ = abs_[:ABS_TRIM] + "\u2026"
        out.append({
            "id": pid,
            "title": txt("title"),
            "abstract": abs_,
            "authors": authors,
            "published": txt("published"),
            "updated": txt("updated"),
            "categories": cats,
            "link": "https://arxiv.org/abs/" + pid,
        })
    return out


# ----------------------------------------------------------------------------
# clustering
# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------
# clustering — word-boundary matching, method-first priority
# ----------------------------------------------------------------------------
def _wb(k):
    # match k as a whole token; tolerant of hyphens/spaces inside k
    return re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])")

_METHOD_RX = [(cid, [_wb(k) for k in kws]) for cid, _n, kws in METHOD]
_APP_RX    = [(cid, [_wb(k) for k in kws]) for cid, _n, kws in APP]
_CORE_RX   = [_wb(k) for k in CORE_SCOPE]

def _best(title, abs, tier):
    best, best_score = None, 0
    for cid, rxs in tier:
        s = sum(3 * bool(r.search(title)) + 1 * bool(r.search(abs)) for r in rxs)
        if s > best_score:
            best_score, best = s, cid
    return best, best_score

def classify(p):
    title = (p.get("title") or "").lower()
    abs = (p.get("abstract") or "").lower()
    cid, score = _best(title, abs, _METHOD_RX)   # how the index works (cuVS lens)
    if score == 0:
        cid, score = _best(title, abs, _APP_RX)   # else application area
    if score > 0:
        p["cluster"], p["clusterScore"] = cid, score
    elif any(r.search(title) or r.search(abs) for r in _CORE_RX):
        p["cluster"], p["clusterScore"] = "general", 0   # in-scope, no sub-method
    else:
        p["cluster"], p["clusterScore"] = "_other", 0     # off-scope -> dropped at scan
    return p


# ----------------------------------------------------------------------------
# cache (persistence + new-paper diff)
# ----------------------------------------------------------------------------
def load_cache():
    if os.path.exists(CACHE):
        try:
            with open(CACHE, encoding="utf-8") as f:
                d = json.load(f)
            return d.get("papers", []), d.get("lastRefresh")
        except Exception:
            pass
    return [], None


def save_cache(papers, last_refresh):
    papers = sorted(papers, key=lambda p: p.get("published", ""), reverse=True)[:MAX_DB]
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump({"papers": papers, "lastRefresh": last_refresh}, f, ensure_ascii=False)
    return papers


# ----------------------------------------------------------------------------
# scan
# ----------------------------------------------------------------------------
def scan(depth, selftest=False):
    prior, _last = load_cache()
    for p in prior:
        classify(p)   # re-classify cached papers so taxonomy changes take effect immediately
    existing = {p["id"] for p in prior}
    merged = {p["id"]: p for p in prior}
    new_ids = []

    if selftest:
        sample = [
            {"id": "2406.00001", "title": "CAGRA: GPU graph-based ANN at scale",
             "abstract": "We present a GPU product quantization and graph index (HNSW-like) for billion-scale vector search using CUDA and cuVS.",
             "authors": ["A. Lee", "B. Kim", "C. Rao", "D. Singh"],
             "published": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
             "updated": "", "categories": ["cs.IR", "cs.DB"], "link": "https://arxiv.org/abs/2406.00001"},
            {"id": "2405.00002", "title": "Filtered DiskANN for hybrid metadata search",
             "abstract": "A filtered search method combining predicate filters with disk-based ANN and dense retrieval for RAG pipelines.",
             "authors": ["E. Wang"],
             "published": (datetime.now(timezone.utc) - timedelta(days=40)).isoformat(),
             "updated": "", "categories": ["cs.IR"], "link": "https://arxiv.org/abs/2405.00002"},
            {"id": "2312.00003", "title": "RaBitQ: binary quantization with recall guarantees",
             "abstract": "Scalar and binary quantization codebook achieving provable recall for maximum inner product search.",
             "authors": ["F. Chen", "G. Park"],
             "published": (datetime.now(timezone.utc) - timedelta(days=150)).isoformat(),
             "updated": "", "categories": ["cs.DS", "cs.IR"], "link": "https://arxiv.org/abs/2312.00003"},
        ]
        for p in sample:
            classify(p)
            if p["id"] not in existing:
                new_ids.append(p["id"])
            merged.setdefault(p["id"], p)
    else:
        errors = []
        for i, q in enumerate(QUERIES, 1):
            print(f"[scan] query {i}/{len(QUERIES)} (depth {depth})\u2026", flush=True)
            try:
                for p in fetch_query(q, depth):
                    classify(p)
                    if p["id"] not in existing:
                        new_ids.append(p["id"])
                    merged.setdefault(p["id"], p)
            except urllib.error.HTTPError as ex:
                errors.append(f"q{i} HTTP {ex.code}")
            except Exception as ex:
                errors.append(f"q{i} {ex}")
            if i < len(QUERIES):
                time.sleep(DELAY)
        if errors and len(errors) == len(QUERIES):
            print("[error] all queries failed:", "; ".join(errors), file=sys.stderr)
            print("        check network / proxy (set HTTPS_PROXY) and retry.", file=sys.stderr)
            sys.exit(1)
        if errors:
            print("[warn] partial:", "; ".join(errors), file=sys.stderr)

    papers = list(merged.values())
    papers = [p for p in papers if p.get("cluster") != "_other"]   # scope gate: drop off-topic
    last_refresh = datetime.now(timezone.utc).isoformat()
    papers = save_cache(papers, last_refresh)
    # only keep new_ids that survived the cap
    keep = {p["id"] for p in papers}
    new_ids = [i for i in new_ids if i in keep]
    return papers, new_ids, last_refresh


# ----------------------------------------------------------------------------
# render
# ----------------------------------------------------------------------------
def render_html(papers, new_ids, last_refresh):
    data = {
        "papers": papers,
        "newIds": new_ids,
        "lastRefresh": last_refresh,
        "taxonomy": [{"id": c, "name": n, "kw": k} for c, n, k in TAXONOMY],
    }
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("/*__DATA__*/", "const EMBEDDED = " + blob + ";")


# ----------------------------------------------------------------------------
# HTML template — data injected at /*__DATA__*/. All rendering is client-side
# over embedded data; no browser network calls.
# ----------------------------------------------------------------------------
TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vector Search Research Radar</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#0B0F14; --panel:#121821; --panel-2:#0F141B; --line:#1E2935;
    --text:#E6EDF3; --muted:#8B98A8; --muted-2:#5C6878;
    --cyan:#76b900; --amber:#F2A93B; --hot:#FF6B5B; --green:#5BD68A;
    --sans:'Inter',system-ui,sans-serif;
    --display:'Space Grotesk',var(--sans);
    --mono:'JetBrains Mono',ui-monospace,monospace;
  }
  *{box-sizing:border-box;}
  html,body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);-webkit-font-smoothing:antialiased;}
  a{color:var(--cyan);text-decoration:none;} a:hover{text-decoration:underline;}
  button{font-family:var(--sans);cursor:pointer;border:none;background:none;color:inherit;}
  button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--cyan);outline-offset:2px;}
  .wrap{max-width:1180px;margin:0 auto;padding:28px 22px 80px;}
  header.top{display:flex;flex-wrap:wrap;align-items:flex-end;gap:18px;border-bottom:1px solid var(--line);padding-bottom:18px;}
  .brand{flex:1 1 300px;min-width:260px;}
  .eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--cyan);margin:0 0 6px;}
  h1{font-family:var(--display);font-weight:700;font-size:clamp(26px,4.4vw,40px);line-height:1.02;margin:0;letter-spacing:-.015em;}
  h1 .dim{color:var(--muted-2);}
  .sub{margin:10px 0 0;color:var(--muted);font-size:13.5px;max-width:48ch;}
  .controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;}
  .ctl{display:flex;align-items:center;gap:7px;font-family:var(--mono);font-size:12px;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:8px 11px;}
  .ctl label{color:var(--muted-2);text-transform:uppercase;letter-spacing:.08em;font-size:10.5px;}
  select{font-family:var(--mono);font-size:12px;color:var(--text);background:transparent;border:none;cursor:pointer;}
  select option{background:var(--panel);color:var(--text);}
  .refresh-note{font-family:var(--mono);font-size:11px;color:var(--muted-2);background:var(--panel);border:1px dashed var(--line);border-radius:9px;padding:9px 13px;line-height:1.4;}
  .refresh-note code{color:var(--amber);}
  .statusbar{display:flex;flex-wrap:wrap;gap:0;margin-top:16px;border:1px solid var(--line);border-radius:11px;overflow:hidden;background:var(--panel-2);}
  .stat{flex:1 1 130px;padding:13px 16px;border-right:1px solid var(--line);min-width:120px;}
  .stat:last-child{border-right:none;}
  .stat .k{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted-2);margin-bottom:5px;}
  .stat .v{font-family:var(--display);font-weight:600;font-size:21px;letter-spacing:-.01em;}
  .stat .v small{font-family:var(--mono);font-weight:400;font-size:12px;color:var(--muted);}
  .grid{display:grid;grid-template-columns:1.55fr 1fr;gap:22px;margin-top:26px;}
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
  .delta.down{color:var(--cyan);background:rgba(118,179,0,.1);}
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
  footer{margin-top:40px;padding-top:16px;border-top:1px solid var(--line);font-family:var(--mono);font-size:11px;color:var(--muted-2);display:flex;flex-wrap:wrap;gap:6px 18px;justify-content:space-between;}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div class="brand">
      <p class="eyebrow">arXiv snapshot &middot; vector search intelligence</p>
      <h1>Research Radar <span class="dim">/ VS</span></h1>
      <p class="sub">Recent arXiv submissions across vector search, ranked by momentum within your selected window. New papers since the last run are flagged.</p>
    </div>
    <div class="controls">
      <div class="ctl">
        <label for="window">window</label>
        <select id="window">
          <option value="30">30d</option>
          <option value="90" selected>90d</option>
          <option value="180">180d</option>
          <option value="365">365d</option>
        </select>
      </div>
      <div class="refresh-note">refresh &rarr; re-run<br><code>python vsr_radar.py</code></div>
    </div>
  </header>

  <div class="statusbar">
    <div class="stat"><div class="k">Snapshot</div><div class="v" id="stLast">&mdash;</div></div>
    <div class="stat"><div class="k">Papers in DB</div><div class="v" id="stCount">0</div></div>
    <div class="stat"><div class="k">New this run</div><div class="v" id="stNew">0</div></div>
    <div class="stat"><div class="k">Active topics</div><div class="v" id="stTopics">0</div></div>
    <div class="stat"><div class="k">Top mover</div><div class="v" id="stMover" style="font-size:14px;">&mdash;</div></div>
  </div>

  <div class="grid">
    <section>
      <div class="col-head">
        <h2>Rising Topics</h2>
        <span class="hint">ranked by <span id="winLabel">90</span>d volume &middot; &#9650; vs prior period</span>
      </div>
      <div class="filterrow">
        <input id="filter" type="text" placeholder="filter by keyword in title / abstract&hellip;" autocomplete="off">
        <label class="toggle"><input type="checkbox" id="newOnly"> new only</label>
      </div>
      <div class="clusters" id="clusters"></div>
      <div class="empty" id="emptyClusters" style="display:none;"><div class="big">No data</div>Run the script to populate the radar.</div>
    </section>
    <section>
      <div class="col-head"><h2>Newest Drops</h2><span class="hint">most recent first</span></div>
      <div class="feed" id="feed"></div>
      <div class="empty" id="emptyFeed" style="display:none;margin-top:0;">No papers.</div>
    </section>
  </div>

  <footer>
    <span>Source: export.arxiv.org/api &middot; clustering = keyword taxonomy (transparent, not semantic)</span>
    <span id="dbnote"></span>
  </footer>
</div>

<script>
"use strict";
/*__DATA__*/

let DB = (EMBEDDED.papers||[]).slice();
const TAXONOMY = EMBEDDED.taxonomy||[];
const newThisScan = new Set(EMBEDDED.newIds||[]);
const lastRefresh = EMBEDDED.lastRefresh||null;
const TAXMAP = {}; TAXONOMY.forEach(t=>TAXMAP[t.id]=t);
const $ = id => document.getElementById(id);

function daysAgo(n){ const d=new Date(); d.setDate(d.getDate()-n); return d; }
function within(iso,days){ return new Date(iso) >= daysAgo(days); }
function fmtDate(iso){ const d=new Date(iso); return d.toLocaleDateString(undefined,{month:"short",day:"numeric",year:"2-digit"}); }
function esc(s){ return (s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
function heatColor(t){ const c1=[118,179,0],c2=[242,169,59],c3=[255,107,91]; let a,b,f;
  if(t<0.5){a=c1;b=c2;f=t/0.5;}else{a=c2;b=c3;f=(t-0.5)/0.5;}
  const m=i=>Math.round(a[i]+(b[i]-a[i])*f); return `rgb(${m(0)},${m(1)},${m(2)})`; }

function buildClusters(){
  const win=parseInt($("window").value,10);
  const filter=$("filter").value.trim().toLowerCase();
  const newOnly=$("newOnly").checked;
  const pass=p=>{
    if(newOnly && !newThisScan.has(p.id)) return false;
    if(filter && !((p.title+" "+p.abstract).toLowerCase().includes(filter))) return false;
    return true;
  };
  const map={};
  TAXONOMY.forEach(t=>map[t.id]={def:t,recent:[],prior:[],all:[]});
  map["_other"]={def:{id:"_other",name:"Uncategorized / Adjacent",kw:[]},recent:[],prior:[],all:[]};
  for(const p of DB){
    if(!pass(p)) continue;
    const b=map[p.cluster]||map["_other"];
    b.all.push(p);
    if(within(p.published,win)) b.recent.push(p);
    else if(new Date(p.published)>=daysAgo(win*2)) b.prior.push(p);
  }
  const arr=Object.values(map).filter(b=>b.all.length>0);
  arr.forEach(b=>{b.recentN=b.recent.length;b.priorN=b.prior.length;b.allN=b.all.length;b.delta=b.recentN-b.priorN;});
  arr.sort((a,b)=> b.recentN-a.recentN || b.allN-a.allN);
  return arr;
}

function paperRow(p){
  return `<div class="paper">
    <div class="ptitle">${newThisScan.has(p.id)?'<span class="new">NEW</span>':""}<a href="${p.link}" target="_blank" rel="noopener">${esc(p.title)}</a></div>
    <div class="pmeta"><span>${fmtDate(p.published)}</span>
      <span>${esc((p.authors||[]).slice(0,3).join(", "))}${p.authors&&p.authors.length>3?" +"+(p.authors.length-3):""}</span>
      <span class="cat">${esc((p.categories||[]).slice(0,3).join(" \u00b7 "))}</span></div>
    <div class="pabs">${esc(p.abstract)}</div>
    <div class="ptoggle">show abstract</div>
  </div>`;
}

function render(){
  $("stLast").innerHTML = lastRefresh ? `<small>${new Date(lastRefresh).toLocaleString(undefined,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})}</small>` : "&mdash;";
  $("stCount").textContent = DB.length;
  $("stNew").textContent = newThisScan.size;
  $("winLabel").textContent = $("window").value;
  $("dbnote").textContent = DB.length+" papers cached";

  const clusters=buildClusters();
  const maxRecent=Math.max(1,...clusters.map(c=>c.recentN));
  $("stTopics").textContent = clusters.filter(c=>c.def.id!=="_other"&&c.recentN>0).length;
  const mover=clusters.filter(c=>c.def.id!=="_other").slice().sort((a,b)=>b.delta-a.delta)[0];
  $("stMover").innerHTML = mover&&mover.delta>0 ? esc(mover.def.name)+` <small style="color:var(--hot)">\u25b2${mover.delta}</small>` : "&mdash;";

  const host=$("clusters");
  $("emptyClusters").style.display = clusters.length?"none":"block";
  host.innerHTML = clusters.map((c,i)=>{
    const heat=c.recentN/maxRecent;
    const col=c.def.id==="_other"?"var(--muted-2)":heatColor(heat);
    const recentW=Math.max(3,Math.round(heat*100));
    const priorW=Math.min(100,Math.round((c.priorN/maxRecent)*100));
    let dcls="flat",dtxt="\u00b10";
    if(c.delta>0){dcls="up";dtxt="\u25b2"+c.delta;} else if(c.delta<0){dcls="down";dtxt="\u25bc"+Math.abs(c.delta);}
    const terms=(c.def.kw||[]).slice(0,6).join(" \u00b7 ")||"no fixed keywords";
    const sorted=c.all.slice().sort((a,b)=>b.published.localeCompare(a.published));
    const recentPapers=c.recent.slice().sort((a,b)=>b.published.localeCompare(a.published));
    const olderPapers=sorted.filter(p=>!recentPapers.includes(p));
    const showAllId=`sa${i}`;
    return `<div class="cluster" data-i="${i}">
      <button class="crow" aria-expanded="false">
        <span class="rank">${String(i+1).padStart(2,"0")}</span>
        <span class="cmid">
          <span class="cname">${esc(c.def.name)} <span class="delta ${dcls}">${dtxt}</span></span>
          <span class="terms">${esc(terms)}</span>
          <span class="track"><span class="prior" style="width:${priorW}%"></span><span class="recent" style="width:${recentW}%;background:${col}"></span></span>
        </span>
        <span class="cright"><span class="ccount" style="color:${col}">${c.recentN}</span><span class="csub">${c.allN} total <span class="chev">\u25b6</span></span></span>
      </button>
      <div class="papers">${recentPapers.map(paperRow).join("")}${olderPapers.length?`<div class="show-all-toggle" id="${showAllId}" style="padding:8px 0;cursor:pointer;color:var(--muted-2);font-size:12px">+ ${olderPapers.length} older papers</div><div class="older-papers" id="op${i}" style="display:none">${olderPapers.map(paperRow).join("")}</div>`:""}</div>
    </div>`;
  }).join("");

  host.querySelectorAll(".cluster").forEach(el=>{
    const btn=el.querySelector(".crow");
    btn.addEventListener("click",()=>{const o=el.classList.toggle("open");btn.setAttribute("aria-expanded",o?"true":"false");});
    const tog=el.querySelector(".show-all-toggle");
    if(tog){
      const older=el.querySelector(".older-papers");
      tog.addEventListener("click",e=>{e.stopPropagation();const x=older.style.display==="none";older.style.display=x?"block":"none";tog.textContent=x?"- hide older papers":"+ "+older.querySelectorAll(".paper").length+" older papers";});
    }
  });
  host.querySelectorAll(".paper").forEach(el=>{
    const tg=el.querySelector(".ptoggle");
    if(tg) tg.addEventListener("click",e=>{e.stopPropagation();const x=el.classList.toggle("exp");tg.textContent=x?"hide abstract":"show abstract";});
  });

  const feedHost=$("feed");
  const feed=DB.slice().filter(p=>{
    if($("newOnly").checked&&!newThisScan.has(p.id)) return false;
    const f=$("filter").value.trim().toLowerCase();
    if(f&&!((p.title+" "+p.abstract).toLowerCase().includes(f))) return false;
    return true;
  }).sort((a,b)=>b.published.localeCompare(a.published)).slice(0,30);
  $("emptyFeed").style.display=feed.length?"none":"block";
  feedHost.style.display=feed.length?"flex":"none";
  feedHost.innerHTML=feed.map(p=>{
    const cl=TAXMAP[p.cluster];
    return `<div class="fitem"><div class="ft">${newThisScan.has(p.id)?'<span class="new">NEW</span>':""}<a href="${p.link}" target="_blank" rel="noopener">${esc(p.title)}</a></div>
      <div class="fm"><span class="dot">${fmtDate(p.published)}</span><span class="tag">${esc(cl?cl.name:"adjacent")}</span><span>${esc((p.categories||[]).slice(0,3).join(", "))}</span></div></div>`;
  }).join("");
}

["window"].forEach(id=>$(id).addEventListener("change",render));
$("filter").addEventListener("input",render);
$("newOnly").addEventListener("change",render);
render();
</script>
</body>
</html>"""


def main():
    ap = argparse.ArgumentParser(description="Vector Search Research Radar (arXiv).")
    ap.add_argument("--depth", type=int, default=150, help="max papers per query (default 150)")
    ap.add_argument("--out", default=OUT, help="output HTML path")
    ap.add_argument("--no-open", action="store_true", help="don't auto-open the HTML")
    ap.add_argument("--selftest", action="store_true", help="render sample data, no network")
    args = ap.parse_args()

    papers, new_ids, last_refresh = scan(args.depth, selftest=args.selftest)
    htmlout = render_html(papers, new_ids, last_refresh)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(htmlout)

    print(f"[ok] {len(papers)} papers in DB, {len(new_ids)} new this run.")
    print(f"[ok] wrote {args.out} and {CACHE}")
    if not args.no_open:
        try:
            webbrowser.open("file://" + os.path.abspath(args.out))
        except Exception:
            pass


if __name__ == "__main__":
    main()

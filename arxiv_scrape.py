#!/usr/bin/env python3
"""
arXiv search-page scraper — fallback fetch path for environments where the
export.arxiv.org API host is blocked but arxiv.org is reachable.
Reuses TAXONOMY / classify / TEMPLATE from vsr_radar.py.
"""
import re, time, json, html as H, urllib.request, urllib.parse, sys
from datetime import datetime, timezone
import vsr_radar as core

UA = "vsr-radar/1.0 (research topic tracker)"
SEARCH = "https://arxiv.org/search/"
PHRASES = [
    '"vector search"', '"approximate nearest neighbor"', '"nearest neighbor search"',
    '"vector database"', '"vector index"', '"semantic join"', '"table embedding"', '"fuzzy join"',
    '"product quantization"', '"maximum inner product search"',
]
PAGES_PER = 1          # 50 results/page
DELAY = 3.0

def fetch_page(phrase, start):
    qs = urllib.parse.urlencode({
        "searchtype": "all", "query": phrase, "start": start,
        "order": "-announced_date_first", "size": 50,
    })
    req = urllib.request.Request(SEARCH + "?" + qs, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")

def strip(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", H.unescape(s))).strip()

def parse(page):
    out = []
    blocks = page.split('class="arxiv-result"')[1:]
    for b in blocks:
        mid = re.search(r'/abs/(\d+\.\d+)', b)
        if not mid:
            continue
        pid = mid.group(1)
        mt = re.search(r'class="title is-5[^"]*">(.*?)</p>', b, re.S)
        title = strip(mt.group(1)) if mt else ""
        ma = re.search(r'class="authors">(.*?)</p>', b, re.S)
        authors = [strip(a) for a in re.findall(r'<a[^>]*>(.*?)</a>', ma.group(1))] if ma else []
        mab = re.search(r'class="abstract-full[^"]*"[^>]*>(.*?)</span>', b, re.S)
        abs = strip(mab.group(1)).replace("\u25b3 Less", "").strip() if mab else ""
        if abs.endswith("\u25bd More"):
            abs = abs[:-6].strip()
        if len(abs) > core.ABS_TRIM:
            abs = abs[:core.ABS_TRIM] + "\u2026"
        cats = re.findall(r'class="tag [^"]*"[^>]*>([a-zA-Z\-]+\.[a-zA-Z\-]+|[a-z\-]+ph)</span>', b)
        md = re.search(r'Submitted</span>\s*([0-9]{1,2}\s+\w+,\s+\d{4})', b)
        try:
            dt = datetime.strptime(md.group(1), "%d %B, %Y").replace(tzinfo=timezone.utc)
            pub = dt.isoformat()
        except Exception:
            pub = datetime.now(timezone.utc).isoformat()
        out.append({
            "id": pid, "title": title, "abstract": abs, "authors": authors,
            "published": pub, "updated": pub, "categories": cats[:5],
            "link": "https://arxiv.org/abs/" + pid,
        })
    return out

def run():
    merged = {}
    for i, ph in enumerate(PHRASES, 1):
        for pg in range(PAGES_PER):
            print(f"[scrape] {i}/{len(PHRASES)} {ph} page {pg+1}", flush=True)
            try:
                for p in parse(fetch_page(ph, pg * 50)):
                    core.classify(p)
                    merged.setdefault(p["id"], p)
            except Exception as ex:
                print("  warn:", ex, file=sys.stderr)
            time.sleep(DELAY)
    papers = sorted(merged.values(), key=lambda p: p["published"], reverse=True)
    papers = [p for p in papers if p.get("cluster") != "_other"]   # scope gate: drop off-topic
    last = datetime.now(timezone.utc).isoformat()
    htmlout = core.render_html(papers, [], last)  # first real snapshot: nothing flagged NEW
    with open("vsr_radar.html", "w", encoding="utf-8") as f:
        f.write(htmlout)
    print(f"[ok] {len(papers)} unique papers, wrote vsr_radar.html")
    # quick distribution
    from collections import Counter
    c = Counter(p["cluster"] for p in papers)
    name = {t[0]: t[1] for t in core.TAXONOMY}
    for cid, n in c.most_common():
        print(f"   {n:>3}  {name.get(cid, cid)}")

if __name__ == "__main__":
    run()

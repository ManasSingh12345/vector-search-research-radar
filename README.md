# Vector Search Research Radar

A self-contained dashboard that tracks **vector search** research on arXiv. It pulls recent papers, sorts topics by 90-day momentum, and plots every paper on a similarity map so you can see what's rising.

![two tabs: a ranked "Rising Topics" list and a "Topic Map" scatter]

- **Rising Topics** — papers grouped into ~18 topic buckets (graph indexes, quantization, GPU accel, RAG/LLM, recsys, hashing/LSH, …), ranked by how many landed in your time window vs the period before it.
- **Topic Map** — each dot is a paper, placed by text similarity (TF-IDF → t-SNE); hover for the title, click to open it on arXiv.
- **Refresh** — re-pulls arXiv and rebuilds everything with one click.

## Quick start

```bash
git clone https://github.com/<you>/vector-search-research-radar.git
cd vector-search-research-radar
pip install -r requirements.txt
python serve.py
```

This opens `http://localhost:8800/vsr_dashboard.html`. A prebuilt dashboard ships with the repo, so you see data immediately. Click **Refresh** to pull the latest papers.

> The Refresh button needs the local server (`serve.py`). Opening `vsr_dashboard.html` directly as a file shows the data but Refresh is disabled — that's expected, because a browser can't run Python on its own.

## How it works

```
arXiv  ──►  vsr_radar.py        fetch + keyword-classify papers  ──►  vsr_radar.html
            generate_topic_map.py   TF-IDF → SVD → t-SNE projection ──►  vsr_topic_map.html
            build_combined.py       merge into one tabbed dashboard ──►  vsr_dashboard.html
serve.py  serves the dashboard and runs the three steps above on Refresh
```

**Categorizing** is keyword-based and transparent (see `METHOD`/`APP` lists in `vsr_radar.py`). It's method-first: a paper is placed by *how the index works* (graph, quantization, GPU, …) before *where it's used* (RAG, recsys). Papers that mention vector search but no specific method go to "General ANN"; off-topic search false-positives are dropped.

## Notes

- **No API key needed.** Default fetch uses the arXiv API (`vsr_radar.py`). If your network blocks `export.arxiv.org`, switch the first step in `serve.py`'s `STEPS` to `arxiv_scrape.py` (scrapes `arxiv.org/search`, no API host needed).
- **Map projection** uses t-SNE by default. For UMAP: `pip install umap-learn`, then `python generate_topic_map.py --umap`.
- **Everything is local.** Data is cached in `vsr_db.json`; nothing is sent anywhere except read requests to arXiv.

## Files

| File | Role |
|------|------|
| `serve.py` | local server + Refresh endpoint (run this) |
| `vsr_radar.py` | fetch arXiv (API) + classify |
| `arxiv_scrape.py` | fetch via arxiv.org search (fallback) |
| `generate_topic_map.py` | build the similarity map |
| `build_combined.py` | merge radar + map into the dashboard |
| `vsr_dashboard.html` | the dashboard (prebuilt; regenerated on Refresh) |

## License

MIT

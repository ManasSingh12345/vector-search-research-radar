# Vector Search Research Radar

Tracks vector search research on arXiv — papers grouped by topic, ranked by 90-day momentum, plotted on a similarity map.

**Live dashboard:** https://manassingh12345.github.io/vector-search-research-radar/

[![Dashboard preview](https://image.thum.io/get/width/1280/crop/800/https://manassingh12345.github.io/vector-search-research-radar/)](https://manassingh12345.github.io/vector-search-research-radar/)

## Local setup

```bash
git clone https://github.com/ManasSingh12345/vector-search-research-radar.git
cd vector-search-research-radar
pip install -r requirements.txt
python serve.py
```

Opens `http://localhost:8800/vsr_dashboard.html`. Click **Refresh** to pull the latest papers.

## How it works

```
vsr_radar.py           fetch + classify papers      →  vsr_radar.html
generate_topic_map.py  TF-IDF → SVD → t-SNE         →  vsr_topic_map.html
build_combined.py      merge into tabbed dashboard   →  vsr_dashboard.html
```

`serve.py` runs the three steps above when you click Refresh.

## Data coverage

This is a **keyword-filtered subset of arXiv**, not a full index. Papers are fetched by searching for these exact phrases in the title, abstract, or body:
> "vector search", "approximate nearest neighbor", "nearest neighbor search", "vector database", "dense retrieval", "retrieval augmented generation", "product quantization", "maximum inner product search"

Papers that don't use this vocabulary are missed. Each daily run fetches ~50 results per phrase (~400 papers total), sorted by submission date. arXiv has a 2–3 day processing delay, so the most recent papers visible are typically from a few days ago — this is normal.

## Notes

- No API key needed. Falls back to `arxiv_scrape.py` if `export.arxiv.org` is blocked.
- UMAP instead of t-SNE: `pip install umap-learn` then `python generate_topic_map.py --umap`.
- All data is local (`vsr_db.json`); nothing is sent except read requests to arXiv.

## License

MIT

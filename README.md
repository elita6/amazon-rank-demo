# Amazon Category Intelligence — Demo

A multi-dimensional category scoring + action guidance system for Amazon marketplace selection.

This is a **public demo** of the full project, with data anonymized and content selectively disclosed.

🔗 **Live demo**: https://amazon-rank-demo-elita.streamlit.app/

---

## What this dashboard does

Turns Amazon category selection from gut-feel into an auditable, data-driven workflow:

- Crawls BS / NR / MS best-seller boards (700+ pages snapshot)
- Parses to SQLite (~70K ASIN-day records, ~20 categories, 5K+ brands)
- Scores 5 dimensions → composite opportunity score
- Ranks categories into 5 priority tiers + emits per-category signals
- Renders interactive dashboard + action playbooks

## Demo limitations

| Aspect | Full version | This demo |
|---|---|---|
| Categories | ~20 anonymized real Amazon verticals | 5 (renamed Category A ~ E) |
| Brands | 5K+ real names | `Brand_001` ~ `Brand_N` |
| ASINs | 15K+ real B0XXXXXXXX | `DEMO00001` ~ `DEMO0XXXX` |
| Price / review | actual values | ±5% noise |
| Action playbooks | Full per-tier + per-signal guidance | Structure disclosed, samples only |
| Dashboard pages | 6 (Category / Brand / ASIN flow / Cross-board / Scoring / Action) | 5 (Category / Brand / Cross-board / Scoring / Action) |
| Methodology docs | 4 docs (~3K lines) | Summary on landing page |

## Methodology core

**5 scoring dimensions** → composite opportunity score (0–1):
Market Attractiveness · Openness · New Product · Momentum · Stability

**Dual-layer weighting**:
- Layer 1 (within-dimension): fixed weights per indicator
- Layer 2 (across-dimension): business fixed weights (0.25 / 0.25 / 0.20 / 0.15 / 0.15)

**5 priority tiers** (composite-score percentiles):
High-potential / Higher / Balanced / Watch / Skip

**Category signals** (per-dimension percentiles, Strength ≥P75 / Constraint ≤P25) — 6 signals over 3 dimensions:
Top-quartile / Bottom-quartile demand · Open Market / Brand Barrier · Low / High volatility.
Momentum (directionally ambiguous) and New Product (sparse) are scored but excluded from signals.

## Tech stack

`Python` `Pandas` `NumPy` `SQLite` `Streamlit` `Plotly` `BeautifulSoup` ·
Multi-Criteria Decision Analysis (MCDA) · Pareto optimization

## Run locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app/产品概览.py
```

## License

[CC BY-NC 4.0](LICENSE) — Non-commercial use only, with attribution.

---

Built by **Elita Zheng** · 2026

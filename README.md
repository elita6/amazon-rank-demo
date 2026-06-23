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
- Diagnoses 13 business archetypes → maps to 5 strategies
- Renders 6-page interactive dashboard + action playbooks

## Demo limitations

| Aspect | Full version | This demo |
|---|---|---|
| Categories | ~20 anonymized real Amazon verticals | 5 (renamed Category A ~ E) |
| Brands | 5K+ real names | `Brand_001` ~ `Brand_N` |
| ASINs | 15K+ real B0XXXXXXXX | `DEMO00001` ~ `DEMO0XXXX` |
| Price / review | actual values | ±5% noise |
| Archetype playbooks | 13 complete (4 actions each) | 2 disclosed, 11 listed only |
| Dashboard pages | 6 (Category / Brand / ASIN flow / Cross-board / Scoring / Action) | 3 (Category / Scoring / Action) |
| Methodology docs | 4 docs (~3K lines) | Summary on landing page |

## Methodology core

**5 scoring dimensions**:
Market Size · Openness · New Product · Momentum · Stability

**Dual-layer weighting**:
- Layer 1 (within-dimension): Entropy weights — data-driven
- Layer 2 (across-dimension): Business fixed weights — judgment-anchored

**13 archetypes** → **5 strategies**:
Top Pick / Hidden Gem / Crowded / Watch / Avoid

## Tech stack

`Python` `Pandas` `NumPy` `SQLite` `Streamlit` `Plotly` `BeautifulSoup` ·
Information entropy · Multi-Criteria Decision Analysis (MCDA) · Pareto optimization

## Run locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app/产品概览.py
```

## License

[CC BY-NC 4.0](LICENSE) — Non-commercial use only, with attribution.

---

Built by **Elita Zheng** · 2026

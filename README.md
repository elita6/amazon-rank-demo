# Amazon Category Intelligence — Demo

A multi-dimensional category scoring + action guidance system for Amazon marketplace selection.

This is a **public demo** of the full project, with data anonymized and content selectively disclosed.

🔗 **Live demo**: https://amazon-rank-demo-elita.streamlit.app/

---

## What this dashboard does

Turns Amazon category selection from gut-feel into an auditable, data-driven workflow:

- Crawls BS / NR / MS best-seller boards (700+ pages snapshot)
- Parses to SQLite (~70K ASIN-day records, ~20 categories, 5K+ brands)
- Scores 3 base dimensions + a new-product bonus → composite opportunity score
- Ranks categories into 5 priority tiers + emits per-category signals
- Renders interactive dashboard + action playbooks

## Demo limitations

| Aspect | Full version | This demo |
|---|---|---|
| Categories | 19 real Amazon verticals | 18 (renamed Category A ~ R; 1 first-party-dominated category excluded) |
| Brands | 5K+ real names | `Brand_001` ~ `Brand_N` |
| ASINs | 15K+ real B0XXXXXXXX | `DEMO00001` ~ `DEMO0XXXX` |
| Price / review | actual values | ±5% noise |
| Action playbooks | Full per-tier + per-signal guidance | Structure disclosed, samples only |
| Dashboard pages | 5 (Category / Competitive Structure / Cross-board / Scoring / Action) | 5 (Category / Competitive Structure / Cross-board / Scoring / Action) |
| Methodology docs | 4 docs (~3K lines) | Summary on landing page |

## Methodology core

**Composite opportunity score = Base score (3 dimensions) + New-Product bonus**

**3 base dimensions** (base score, scaled 0–100):
Market Attractiveness · Openness · Stability

**Dual-layer weighting** (base score):
- Layer 1 (within-dimension): fixed weights per indicator
- Layer 2 (across-dimension): business fixed weights (0.40 / 0.35 / 0.25)

**New-Product bonus**: new products surging onto the Movers & Shakers board earn a tiered add-on (+0 / +3 / +6, with a minimum-event gate) — kept off the base ranking so a sparse signal can't dominate.

**5 priority tiers** (composite-score percentiles):
High-potential / Higher / Balanced / Watch / Skip

**Category signals** (per-dimension percentiles, Strength ≥P75 / Constraint ≤P25) — 6 signals over the 3 base dimensions:
Top-quartile / Bottom-quartile demand · Open Market / Brand Barrier · Low / High volatility.
New-product breakout is shown separately as a **New-Product Growth** tag (from the bonus), not folded into the dimension signals.

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

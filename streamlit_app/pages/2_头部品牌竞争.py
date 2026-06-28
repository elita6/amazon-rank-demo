# streamlit_app/pages/2_头部品牌竞争.py
# 更新日期：2026-06-28
# 用途：头部品牌竞争（Demo 版，对齐生产 v2）— 决策3。
#       核心 = 集中度 2×2（坑位集中度 × 需求集中度，CR3 双基准，归一化品牌）。
# 启动命令：streamlit run streamlit_app/产品概览.py
# 与生产 v2 差异：数据源 data/amazon.db → data/*.csv（connect_demo）；类目/品牌已匿名化。
# 主要改动：
#   - 2026-06-28：从生产 v2 pages/1_品牌竞争.py 移植（页名「品牌竞争」→「头部品牌竞争」；
#       CR3 双基准；热力图 + Top3 散点并排；Treemap 单类目下钻；全图 insight_box 数据驱动解读）

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "streamlit_app"))
from _styles import page_title, chart_title, insight_box
from _i18n import t
from _brands import normalize_brand, brand_breakdown
from _aggregate import distribution_insights, fmt_compact
from _demo_data import connect_demo

CAT_SHORT = {
    "Amazon Devices & Accessories": "AmazonDev", "Appliances": "Appliances",
    "Arts, Crafts & Sewing": "Arts", "Automotive": "Auto",
    "Beauty & Personal Care": "Beauty", "Camera & Photo Products": "Camera",
    "Cell Phones & Accessories": "Cell", "Clothing, Shoes & Jewelry": "Clothing",
    "Computers & Accessories": "Computers", "Electronics": "Electronics",
    "Health & Household": "Health", "Home & Kitchen": "Home",
    "Kitchen & Dining": "Kitchen", "Musical Instruments": "Musical",
    "Office Products": "Office", "Patio, Lawn & Garden": "Patio",
    "Pet Supplies": "Pet", "Sports & Outdoors": "Sports",
    "Tools & Home Improvement": "Tools",
}

# 高/低参考线（仅作热力深浅/散点参考，不做强制分类；两轴量纲不同，各取≈P70）
SHELF_HI, DEMAND_HI = 0.25, 0.35


@st.cache_data
def load_data():
    conn = connect_demo()
    asin = pd.read_sql(
        "SELECT category, list_type, date, asin, brand, price_low, review_count "
        "FROM asin_daily WHERE list_type='best_seller'", conn)
    summary = pd.read_sql("SELECT category, is_subcategory FROM category_summary", conn)
    sub = set(summary[summary["is_subcategory"] == 1]["category"])
    asin = asin[~asin["category"].isin(sub)].copy()
    uniq = pd.Series(asin["brand"].dropna().unique())
    bmap = dict(zip(uniq, uniq.map(normalize_brand)))
    asin["brand_norm"] = asin["brand"].map(bmap)
    return asin


@st.cache_data
def compute(asin):
    """每类目：per-brand 份额表 + 坑位/需求 CR3。"""
    recs, breakdowns = [], {}
    for cat, g in asin.groupby("category"):
        per, n = brand_breakdown(g)
        if per is None or n == 0:
            continue
        breakdowns[cat] = per
        # 同一组 top3：按 ASIN 数选出的前 3 品牌（per 已按 asin_count 降序）
        top3_per = per.head(3)
        shelf = top3_per["asin_count"].sum() / n          # Top3品牌份额(按ASIN)
        tot = per["review_sum"].sum()
        demand = top3_per["review_sum"].sum() / tot if tot > 0 else None  # 同组 review 占比
        top3 = "、".join(top3_per.index[:3])
        n_brand = len(per)
        recs.append({"category": cat, "n_asin": n, "n_brand": n_brand,
                     "asin_per_brand": round(n / n_brand, 2) if n_brand else None,
                     "shelf": round(shelf, 3),
                     "demand": round(demand, 3) if demand is not None else None,
                     "top3": top3})
    return pd.DataFrame(recs), breakdowns


# =======================================================================
page_title(t("头部品牌竞争", "Head-Brand Competition"))

asin = load_data()
df_cr, breakdowns = compute(asin)
df_cr = df_cr.dropna(subset=["shelf", "demand"]).reset_index(drop=True)
df_cr["短名"] = df_cr["category"].map(CAT_SHORT).fillna(df_cr["category"])

# ---------- 各类目集中度（热力，左）+ Top3 散点（右）并排 ----------
order = df_cr.sort_values("shelf", ascending=False).reset_index(drop=True)
num_cols = [   # 去掉 ASIN数量/品牌数量两列；ASIN/品牌 → 品牌密度
    (t("品牌密度", "Brand density"), "asin_per_brand", lambda v: f"{v:.1f}"),
    (t("Top3品牌份额(按ASIN)", "Top3 share (by ASIN)"), "shelf", lambda v: f"{v*100:.0f}%"),
    (t("评论占比", "Review share"), "demand", lambda v: f"{v*100:.0f}%"),
]
xlabels = [c[0] for c in num_cols]
norms = [(order[c[1]].min(), order[c[1]].max()) for c in num_cols]
ynames = order["category"].tolist()
z, text = [], []
for i in range(len(order)):
    zr, tr = [], []
    for j, (_, col, fmt) in enumerate(num_cols):
        v = order.loc[i, col]
        lo, hi = norms[j]
        zr.append((v - lo) / (hi - lo) if hi > lo else 0.5)
        tr.append(fmt(v))
    z.append(zr)
    text.append(tr)
fig_h = go.Figure(go.Heatmap(
    z=z, x=xlabels, y=ynames, text=text,
    texttemplate="%{text}", textfont=dict(size=11), colorscale="Blues",
    zmin=0, zmax=1, showscale=False, xgap=2, ygap=2, hoverinfo="skip"))
fig_h.update_layout(height=660, margin=dict(l=8, r=8, t=24, b=8),
                    yaxis=dict(autorange="reversed", automargin=True))
fig_h.update_xaxes(side="top", tickfont=dict(size=11))

# 解读占位数值（品牌密度 / Top3品牌份额(按ASIN) / 评论占比 列前 2-3 名）——热力图+散点合并解读用
def _top_pct(col, k=3):
    rows = order.nlargest(k, col)
    return "、".join(f"<b>{r['category']}</b> {r[col]*100:.0f}%" for _, r in rows.iterrows())
_sh_lo = order.nsmallest(2, "shelf")
_lo_s = "、".join(f"<b>{r['category']}</b> {r['shelf']*100:.0f}%" for _, r in _sh_lo.iterrows())
_apb3 = order.nlargest(3, "asin_per_brand")
_apb_s = "、".join(f"<b>{r['category']}</b> {r['asin_per_brand']:.1f}" for _, r in _apb3.iterrows())

# Top3 散点
fig = px.scatter(
    df_cr, x="shelf", y="demand", text="短名", hover_name="category",
    hover_data={"shelf": ":.0%", "demand": ":.0%", "短名": False, "top3": True},
    height=540,
    labels={"shelf": t("Top3品牌份额(按ASIN)", "Top3 share (by ASIN)"),
            "demand": t("评论占比", "Review share")})
fig.update_traces(marker=dict(size=13, color="#5b8fc4",
                              line=dict(width=1, color="white"), opacity=0.85),
                  textposition="top center", textfont=dict(size=9, color="#444"))
fig.add_vline(x=SHELF_HI, line_dash="dot", line_color="#ccc")
fig.add_hline(y=DEMAND_HI, line_dash="dot", line_color="#ccc")
xr = [df_cr["shelf"].min() - 0.03, df_cr["shelf"].max() + 0.07]
yr = [df_cr["demand"].min() - 0.03, df_cr["demand"].max() + 0.07]
fig.update_layout(xaxis=dict(range=xr, tickformat=".0%"),
                  yaxis=dict(range=yr, tickformat=".0%"),
                  showlegend=False, margin=dict(l=10, r=10, t=30, b=40))
_n = len(df_cr)
_above = int((df_cr["demand"] > df_cr["shelf"]).sum())
_rho = df_cr["shelf"].rank().corr(df_cr["demand"].rank())
_tr = df_cr.loc[(df_cr["shelf"] + df_cr["demand"]).idxmax()]   # 右上：两项都高
_bl = df_cr.loc[(df_cr["shelf"] + df_cr["demand"]).idxmin()]   # 左下：两项都低
_insight_items = [
    t(f"<b>Top3品牌份额(按ASIN)</b>最高的是 {_top_pct('shelf')}；最分散的 {_lo_s}——各类目头部 3 品牌占据的 ASIN 份额差距很大。",
      f"<b>Top3 share (by ASIN)</b> is highest in {_top_pct('shelf')}; most fragmented {_lo_s}—wide gap in the ASIN share held by the top 3 brands across categories."),
    t(f"<b>评论占比</b>最高的是 {_top_pct('demand')}——这几个类目的评论高度集中在头部 3 品牌手里。",
      f"<b>Review share</b> is highest in {_top_pct('demand')}—reviews here are heavily concentrated in the top 3 brands."),
    t(f"<b>品牌密度</b>（单品牌平均铺几款 ASIN）最高的是 {_apb_s}——这几个类目里头部品牌靠多个 SKU 占住榜单。",
      f"<b>Brand density</b> (ASINs per brand) is highest in {_apb_s}—here head brands hold the list with many SKUs each."),
    t(f"{_above}/{_n} 个类目<b>评论占比 > Top3品牌份额(按ASIN)</b>，且两者正相关（同向程度 {_rho:.0%}）：头部 3 品牌拿到的评论普遍比其 ASIN 份额还多，且份额越集中、评论通常也越集中。",
      f"{_above}/{_n} categories have <b>review share > Top3 share (by ASIN)</b>, and the two are positively correlated (rank agreement {_rho:.0%}): the top 3 brands' review share generally exceeds their ASIN share, and the more concentrated the share, the more concentrated the reviews."),
    t(f"右上角 <b>{_tr['category']}</b> 两项都最高、头部品牌最强势；左下角 <b>{_bl['category']}</b> 两项都最低、竞争最分散。",
      f"Top-right <b>{_tr['category']}</b> is highest on both—head brands dominate; bottom-left <b>{_bl['category']}</b> is lowest on both—the most fragmented."),
]

# 并排：左 热力(窄) / 右 散点(宽)
_hcol, _scol = st.columns([5, 6])
with _hcol:
    chart_title(t("各类目集中度", "Concentration by Category"))
    st.plotly_chart(fig_h, width="stretch")
    st.markdown(
        "<div style='font-size:0.70rem; color:#6b7280; line-height:1.7;'>"
        + t("注：", "Note:")
        + "<br>* "
        + t("Top3品牌份额(按ASIN) = 按 ASIN 数选出前 3 品牌，计算其 ASIN 数量占比；评论占比 = 这同 3 个品牌的评论数占比",
            "Top3 share (by ASIN) = pick the top 3 brands by ASIN count, their ASIN-count share; Review share = those same 3 brands' review share")
        + "<br>* "
        + t("品牌密度 = ASIN数 ÷ 品牌数（单品牌平均铺几款）",
            "Brand density = ASINs ÷ brands (avg SKUs per brand)")
        + "</div>",
        unsafe_allow_html=True)
with _scol:
    chart_title(t("Top3品牌：ASIN份额 × 评论占比", "Top3 brands: ASIN share × Review share"))
    st.plotly_chart(fig, width="stretch")
    insight_box(_insight_items)

st.divider()

# ---------- Treemap 单类目下钻（复用原页样式）----------
chart_title(t("Treemap：单类目内 Top15 品牌的 ASIN 占比（下钻）",
              "Treemap: ASIN share of Top 15 brands within a category (drill-down)"))
cats_sorted = df_cr.sort_values("demand", ascending=False)["category"].tolist()
sel = st.selectbox(t("选择类目", "Select category"), options=cats_sorted,
                   format_func=lambda c: CAT_SHORT.get(c, c), label_visibility="collapsed")
per = breakdowns.get(sel)
sub = per.head(15).reset_index().rename(columns={"index": "brand"})
if sub.empty:
    st.warning(t("该类目无品牌数据", "No brand data for this category"))
else:
    fig_tm = px.treemap(sub, path=["brand"], values="asin_count",
                        color="asin_count", color_continuous_scale="Oranges", height=460)
    fig_tm.update_traces(
        texttemplate="<b>%{label}</b><br>%{value} ASIN<br>%{percentRoot:.1%}",
        textfont=dict(size=12))
    fig_tm.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_tm, width="stretch")

    # 解读：选中类目 sel 内的品牌构成（per=全部品牌，sub=Top15，与 Treemap 同源）
    _tot = float(per["asin_count"].sum())
    _nb = len(per)
    _b1 = sub.iloc[0]
    _t3 = sub.head(3)["asin_count"].sum() / _tot if _tot > 0 else 0
    _t3names = "、".join(f"<b>{r['brand']}</b>" for _, r in sub.head(3).iterrows())
    _items_tm = [
        t(f"<b>{sel}</b> 共有 {_nb} 个品牌；第一名 <b>{_b1['brand']}</b> 独占 {int(_b1['asin_count'])} 个 ASIN（该类目 {_b1['asin_count']/_tot*100:.0f}%）。",
          f"<b>{sel}</b> has {_nb} brands; the leader <b>{_b1['brand']}</b> alone holds {int(_b1['asin_count'])} ASINs ({_b1['asin_count']/_tot*100:.0f}% of the category)."),
        t(f"前 3 品牌（{_t3names}）合计占 {_t3*100:.0f}% 的 ASIN。",
          f"The top 3 brands ({_t3names}) together hold {_t3*100:.0f}% of ASINs."),
    ]
    if len(sub) >= 2 and sub.iloc[1]["asin_count"] > 0:
        _b2 = sub.iloc[1]
        _items_tm.append(
            t(f"第一名的 ASIN 数是第二名 <b>{_b2['brand']}</b> 的 {_b1['asin_count']/_b2['asin_count']:.1f} 倍。",
              f"The leader has {_b1['asin_count']/_b2['asin_count']:.1f}× the ASINs of the runner-up <b>{_b2['brand']}</b>."))
    insight_box(_items_tm)

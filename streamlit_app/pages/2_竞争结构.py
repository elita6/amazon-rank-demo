# streamlit_app/pages/2_竞争结构.py
# 更新日期：2026-07-04
# Demo 适配：数据源 data/amazon.db → data/*.csv（_demo_data.connect_demo）；类目/品牌已匿名化；
#   黑名单类目在 demo 数据生成时已剔除，去掉 excluded_categories；CAT_SHORT 对 demo 类目无映射、自动回退。
# 原文件：v3/streamlit_app/pages/1_竞争结构.py
# 更新日期（原）：2026-07-03
# 用途：品牌竞争 —— 方案C 对照版（最终形态）。相对原版 1_品牌竞争.py 引入 openness 第三维
#       **NR_BS品牌占有率 occ = 1 − 新牌友好度 d**（高=老牌主导=壁垒高）：
#       左热力表加第 3 列，右散点点色按 occ 着色（去色条——左表该列即图例）；三列/点色全 Blues 同色系。
# 启动命令：streamlit run v2/streamlit_app/app.py
# 主要改动：
#   - 2026-07-03（方案C·散点上色）：load_data SQL 扩到 best_seller+new_release；compute 加 occ=1−d；
#       散点 color=occ + hover :.2f。
#   - 2026-07-03（方案C·最终形态）：左热力表由 2 列→3 列——新增 NR_BS品牌占有率(occ) 列，散点去掉
#       色条（update_coloraxes(showscale=False)），故表该列即散点点色图例。
#       左标题「各类目BS集中度」→「类目集中度」。**不恢复任何 st.dataframe 三面板。**
#   - 2026-07-03（配色统一）：occ 列与散点点色由 Oranges → Blues，三列 + 点色全蓝同色系。
#   - 2026-07-03（修错位）：热力表两 trace 合并回单个 go.Heatmap（3 列并入 num_cols），occ 的 None
#       在 z/text 循环里置 np.nan/""；单 trace 天然对齐，删掉 categoryarray/z_occ/text_occ。
#   - 2026-07-03（展示细化）：术语统一「NR_BS品牌占有率」；页标题→「品牌竞争」；列名/轴名→BS_Top3品牌份额/
#       BS_Top10商品份额/NR_BS品牌占有率；散点标题→「集中度象限图」+ 中位线说明；删右侧 footnote；
#       象限解读改为三指标结合（象限 + 占有率颜色叠加，标注各类目占有率%）。

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "streamlit_app"))
from _styles import page_title, chart_title, insight_box
from _i18n import t
from _brands import normalize_brand, brand_breakdown, brand_review_crn
from _aggregate import (distribution_insights, fmt_compact,
                        asin_review_crn, new_brand_demand_share)
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

# 决策11：参考线改为各轴中位数（见 compute 后），仅作散点参考、不做强制分类。


@st.cache_data
def load_data():
    conn = connect_demo()
    # 方案C：BS + NR 都取（NR 用于算「新牌友好度 d / 占有率」；BS 用于两条集中度腿，值不变）
    asin = pd.read_sql(
        "SELECT category, list_type, date, asin, brand, price_low, review_count "
        "FROM asin_daily WHERE list_type IN ('best_seller','new_release')", conn)
    summary = pd.read_sql("SELECT category, is_subcategory FROM category_summary", conn)
    conn.close()
    # 排除子类目（Demo 数据生成时已剔除黑名单类目）
    drop = set(summary[summary["is_subcategory"] == 1]["category"])
    asin = asin[~asin["category"].isin(drop)].copy()
    uniq = pd.Series(asin["brand"].dropna().unique())
    bmap = dict(zip(uniq, uniq.map(normalize_brand)))
    asin["brand_norm"] = asin["brand"].map(bmap)
    return asin


@st.cache_data
def compute(asin):
    """每类目：per-brand 份额表 + 坑位/需求 CR3。"""
    recs, breakdowns = [], {}
    for cat, g in asin.groupby("category"):
        # 两条集中度腿只在 BS 切片上算（与原页完全一致，NR 不参与，值不变）
        g_bs = g[g["list_type"] == "best_seller"]
        per, n = brand_breakdown(g_bs)
        if per is None or n == 0:
            continue
        breakdowns[cat] = per
        # 决策11 两轴（需求/评论口径，与评分引擎 openness 同一份函数）：
        brand_rev3 = brand_review_crn(g_bs)      # X：Top3 品牌(按评论) 评论占比
        asin_rev10 = asin_review_crn(g_bs)       # Y：Top10 ASIN(按评论) 评论占比
        # 方案C 上色维度：NR_BS品牌占有率 occ = 1 − d（d=新牌友好度，传该类目全 df 含 BS+NR）
        d = new_brand_demand_share(g)
        occ = round(1.0 - d, 4) if d is not None else None
        # Treemap 下钻仍按 ASIN 数展示品牌构成，故保留 top3(按ASIN) 名称串
        top3 = "、".join(per.head(3).index[:3])
        n_brand = len(per)
        recs.append({"category": cat, "n_asin": n, "n_brand": n_brand,
                     "brand_rev3": round(brand_rev3, 4) if brand_rev3 is not None else None,
                     "asin_rev10": round(asin_rev10, 4) if asin_rev10 is not None else None,
                     "occ": occ,
                     "top3": top3})
    return pd.DataFrame(recs), breakdowns


# =======================================================================
page_title(t("竞争结构", "Competitive Structure"))

asin = load_data()
df_cr, breakdowns = compute(asin)
df_cr = df_cr.dropna(subset=["brand_rev3", "asin_rev10"]).reset_index(drop=True)
df_cr["短名"] = df_cr["category"].map(CAT_SHORT).fillna(df_cr["category"])

# ---------- 各类目集中度（热力，左）+ 需求集中度散点（右）并排 ----------
# 方案C：单个 go.Heatmap，3 列 = BS_Top3品牌份额/BS_Top10商品份额 + NR_BS品牌占有率，全 Blues 同色系、对齐。
#   每列各自 min-max 归一（靠 norms）；占有率列 min-max 与散点 occ 蓝深浅大体一致。
order = df_cr.sort_values("brand_rev3", ascending=False).reset_index(drop=True)
num_cols = [   # 决策11：前两列 = 评分 openness 两腿；第三列 = NR_BS品牌占有率(occ)
    (t("BS_Top3品牌份额", "BS Top3 Brand Share"), "brand_rev3", lambda v: f"{v*100:.0f}%"),
    (t("BS_Top10商品份额", "BS Top10 Product Share"), "asin_rev10", lambda v: f"{v*100:.0f}%"),
    (t("NR_BS品牌占有率", "NR_BS Incumbent Share"), "occ", lambda v: f"{v*100:.0f}%"),
]
xlabels = [c[0] for c in num_cols]
norms = [(order[c[1]].min(), order[c[1]].max()) for c in num_cols]  # min/max 默认跳过 NaN
ynames = order["category"].tolist()
z, text = [], []
for i in range(len(order)):
    zr, tr = [], []
    for j, (_, col, fmt) in enumerate(num_cols):
        v = order.loc[i, col]
        lo, hi = norms[j]
        if pd.isna(v):                  # occ 可能为 None：空值格无色 + 文本留空，不报错
            zr.append(np.nan)
            tr.append("")
        else:
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

# 两项需求集中度（品牌 / 商品）合并解读取数：用组合排名给"最集中/最分散"。
#   两者秩相关仅 0.379、各带独立信息（品牌壁垒 vs 爆款壁垒），故一起给总体格局、
#   再单挑背离类目讲差异；相关/口径依据见 指标解释.md §二 / 改造依据.md 决策11。
# 参考线 = 各轴中位数；综合封闭度 = 品牌份额 / 商品份额 / 占有率 三项百分位均值
_xmed, _ymed = df_cr["brand_rev3"].median(), df_cr["asin_rev10"].median()
df_cr["_closed"] = df_cr[["brand_rev3", "asin_rev10", "occ"]].rank(pct=True).mean(axis=1)

_top = df_cr.nlargest(3, "_closed")
_bot = df_cr.nsmallest(3, "_closed")
_named = set(_top["短名"]) | set(_bot["短名"])   # 已在集中/分散点名的，背离里不重复


def _cnames(sub):
    names = [f"<b>{x}</b>" for x in sub["短名"]]
    return "、".join(names), ", ".join(names)


def _occ_rng(sub):
    o = sub["occ"].dropna()
    return f"{o.min()*100:.0f}~{o.max()*100:.0f}%" if len(o) else "—"


_top_cn, _top_en = _cnames(_top)
_bot_cn, _bot_en = _cnames(_bot)
_top_occ, _bot_occ = _occ_rng(_top), _occ_rng(_bot)
# 背离两组（median 切品牌/商品；排除已点名的 top/bot 避免重复）
_bd_brand = df_cr[(df_cr["brand_rev3"] >= _xmed) & (df_cr["asin_rev10"] < _ymed) & (~df_cr["短名"].isin(_named))]
_bd_prod = df_cr[(df_cr["brand_rev3"] < _xmed) & (df_cr["asin_rev10"] >= _ymed) & (~df_cr["短名"].isin(_named))]

# 集中度象限图：X=BS_Top3品牌份额、Y=BS_Top10商品份额、颜色=NR_BS品牌占有率(1−d)
_occ_label = t("NR_BS品牌占有率(深=老牌主导)", "NR_BS Incumbent Share (dark=incumbent-led)")
fig = px.scatter(
    df_cr, x="brand_rev3", y="asin_rev10", text="短名", hover_name="category",
    color="occ", color_continuous_scale="Blues",
    hover_data={"brand_rev3": ":.0%", "asin_rev10": ":.0%", "occ": ":.2f",
                "短名": False, "top3": True},
    height=540,
    labels={"brand_rev3": t("BS_Top3品牌份额", "BS Top3 Brand Share"),
            "asin_rev10": t("BS_Top10商品份额", "BS Top10 Product Share"),
            "occ": _occ_label})
fig.update_traces(marker=dict(size=13,
                              line=dict(width=1, color="white"), opacity=0.85),
                  textposition="top center", textfont=dict(size=9, color="#444"),
                  cliponaxis=False)   # 边缘点的文字不被坐标轴裁掉（修 Auto 等遮挡）
fig.update_coloraxes(showscale=False)   # 去掉色条：左表占有率列即图例，散点不另设
fig.add_vline(x=_xmed, line_dash="dot", line_color="#ccc")
fig.add_hline(y=_ymed, line_dash="dot", line_color="#ccc")
xr = [df_cr["brand_rev3"].min() - 0.05, df_cr["brand_rev3"].max() + 0.08]
yr = [df_cr["asin_rev10"].min() - 0.05, df_cr["asin_rev10"].max() + 0.09]
fig.update_layout(xaxis=dict(range=xr, tickformat=".0%"),
                  yaxis=dict(range=yr, tickformat=".0%"),
                  showlegend=False, margin=dict(l=16, r=16, t=30, b=46))
_n = len(df_cr)
# 集中/分散(带占有率补充) + 背离两组，自然表述（口径见坐标轴注）
_insight_items = [
    t(f"集中度较高：{_top_cn}——BS 头部品牌与商品都集中，且新品榜老牌也占一定份额（占有率 {_top_occ}），大牌仍在持续布局、占领新品生态。",
      f"More concentrated: {_top_en} — heads concentrated on both brand and product, and incumbents also hold a share of the new-release lane (incumbent share {_top_occ}), still extending into new products."),
    t(f"竞争较分散：{_bot_cn}——BS 头部分散，新品榜也基本是新牌（占有率仅 {_bot_occ}）。",
      f"More fragmented: {_bot_en} — dispersed heads, and the new-release lane is mostly newcomers (incumbent share only {_bot_occ})."),
]
if not _bd_brand.empty:
    _bc, _be = _cnames(_bd_brand)
    _insight_items.append(t(
        f"品牌集中但商品分散：{_bc}——大牌靠宽产品线占位，无单一爆款。",
        f"Brand-concentrated but product-fragmented: {_be} — big brands hold spots with wide lines, no single hero."))
if not _bd_prod.empty:
    _pc, _pe = _cnames(_bd_prod)
    _insight_items.append(t(
        f"商品集中但品牌分散：{_pc}——少数爆款 listing，无品牌垄断。",
        f"Product-concentrated but brand-fragmented: {_pe} — a few hero listings, no brand monopoly."))

# 并排：左 热力(窄) / 右 散点(宽)
_hcol, _scol = st.columns([5, 6])
with _hcol:
    chart_title(t("类目集中度", "Category Concentration"))
    st.plotly_chart(fig_h, width="stretch")
    st.markdown(
        "<div style='font-size:0.70rem; color:#6b7280; line-height:1.7;'>"
        + t("注：", "Note:")
        + "<br>* "
        + t("BS_Top3品牌份额 = 按评论排序前 3 品牌的评论占比（品牌壁垒）",
            "BS Top3 Brand Share = review share of the top 3 brands by reviews (brand barrier)")
        + "<br>* "
        + t("BS_Top10商品份额 = 按评论排序前 10 个商品(ASIN)的评论占比（爆款壁垒）",
            "BS Top10 Product Share = review share of the top 10 ASINs by reviews (hero-listing barrier)")
        + "<br>* "
        + t("NR_BS品牌占有率 = NR 榜上之前已出现在 BS 榜的品牌所占的 ASIN 数量比例",
            "NR_BS Incumbent Share = the ASIN-count share on the NR list held by brands already seen on the BS list")
        + "<br>* "
        + t("三列同为「高=壁垒高」；前两列按评论(销量代理)、占有率按 ASIN 坑位，均为 BS/NR 榜内相对比较，非全类目垄断度",
            "All three read high = high barrier; the first two use review share (sales proxy), incumbent share uses ASIN slots; relative within the BS/NR lists only, not full-category monopoly")
        + "</div>",
        unsafe_allow_html=True)
with _scol:
    chart_title(t("集中度象限图", "Concentration Quadrant"))
    st.markdown(
        "<div style='font-size:0.70rem; color:#6b7280; line-height:1.7;'>"
        + t("坐标轴：X = BS_Top3品牌份额中位数、Y = BS_Top10商品份额中位数<br>圆点颜色深浅：NR_BS品牌占有率高低，越深数值越高",
            "Axes: X = median of BS Top3 Brand Share, Y = median of BS Top10 Product Share<br>Dot shade: NR_BS Incumbent Share — darker = higher")
        + "</div>",
        unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch")
    insight_box(_insight_items)

st.divider()

# ---------- Treemap 单类目下钻（复用原页样式）----------
chart_title(t("单类目BS Top品牌ASIN占比",
              "Single-category BS top brands' ASIN share"))
cats_sorted = df_cr.sort_values("brand_rev3", ascending=False)["category"].tolist()
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


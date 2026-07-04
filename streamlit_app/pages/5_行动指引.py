# streamlit_app/pages/5_行动指引.py
# 更新日期：2026-07-04
# Demo 适配：数据源 data/amazon.db → data/*.csv（_demo_data.connect_demo）；类目/品牌/ASIN 已匿名化；
#   读 *_c 后缀评分列（由 demo CSV 提供）；Amazon 商品链接为 demo 占位（ASIN 已脱敏）。
# 原文件：v3/streamlit_app/pages/5_行动指引.py（方案C 对照版：3 维信号 + 新品Bonus）
# 更新日期（原）：2026-07-03
# 用途：行动指引页「方案C 对照版」— 复制自 5_行动指引.py，原页一字不动便于 A/B 对照。
#       方案C 口径：信号 3 维（market_size/openness/stability，读 *_c 列）+ 新品Bonus 单独成「新品成长」标签。
#       数据基于默认权重评分（不跟随综合评分页滑块）。
# 主要改动（相对原页，均为方案C 定制）：
#   - 2026-07-03（新建·方案C 对照版）：
#       ① 数据源改读 *_c 后缀列：composite_score_c / tier_c / positive_signals_c / risk_signal_c / bonus_c。
#       ② 优势/约束信号维度 = 3 维（market_size / openness / stability），读 positive_signals_c / risk_signal_c；
#          SIGNAL_LABELS 本就只含这 3 维（momentum/new_product 不参与信号），保持不动。
#       ③ 新品Bonus 单独作为「新品成长」标签展示（Strong / Medium / —，来自 bonus_c），
#          不并进三维的优势/约束信号里。
#       ④ 价位带参考、重点 ASIN 两模块读 asin_daily，与评分口径无关，保持原逻辑与 i18n 不动。
#   —— 原页 5_行动指引.py 与本页无关，保持不动。

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
from _i18n import t, get_lang
from _brands import normalize_brand   # 统一品牌口径（归一化去重）
from _demo_data import connect_demo


# price band 数据值（英文，qcut 标签）→ 显示名；分箱/排序仍用英文，仅渲染套用
BAND_ORDER = ["B1", "B2", "B3", "B4", "B5"]
BAND_LABELS = {
    "B1": t("低价格段", "Lowest"),
    "B2": t("中低价格段", "Lower"),
    "B3": t("中等价格段", "Mid"),
    "B4": t("中高价格段", "Upper"),
    "B5": t("高价格段", "Highest"),
}

# ---- Opportunity Signals（方案C：3 维信号，读 *_c 列）----
# Overall Rating(=Tier_c) 展示简称
TIER_LABEL = {
    "高潜机会类目": t("高潜机会", "Top"),     "较高机会类目": t("较高机会", "High"),
    "中性观察类目": t("中性观察", "Balanced"), "谨慎评估类目": t("谨慎评估", "Watch"),
    "暂不考虑类目": t("暂不考虑", "Skip"),
}
# 信号中英显示名（db 存英文；正向=优势/绿 chip，负向=约束/琥珀 chip）
# 方案C 仅 3 维参与信号（market_size / openness / stability）；momentum、new_product 不参与
SIGNAL_LABELS = {
    "Strong Demand":    t("需求居前", "Top-quartile demand"), "Open Market":     t("市场开放", "Open Market"),
    "Weak Demand":      t("需求居后", "Bottom-quartile demand"), "Brand Barrier":  t("品牌壁垒", "Brand Barrier"),
    "Stable Structure": t("波动较小", "Low volatility"), "Unstable Structure": t("波动较大", "High volatility"),
}
STRENGTH_BG, CONSTRAINT_BG = "#e8f6ef", "#fdece4"
STRENGTH_FG, CONSTRAINT_FG = "#1e8449", "#ba4a00"
# 新品成长（Bonus）单独标签配色 — 与优势/约束区分（蓝紫系）
BONUS_BG, BONUS_FG = "#eef2ff", "#4338ca"


def _sig_chips(s, bg, fg):
    """'Strong Demand + Open Market' → 彩色 chip；空→灰 —"""
    if s is None or (isinstance(s, float) and pd.isna(s)) or str(s).strip() in ("", "—", "None", "nan"):
        return "<span style='color:#c2c8cf;'>—</span>"
    return "".join(
        f"<span style='background:{bg}; color:{fg}; border-radius:10px; padding:2px 9px; "
        f"margin-right:5px; font-size:0.82rem; white-space:nowrap;'>{SIGNAL_LABELS.get(l, l)}</span>"
        for l in str(s).split(" + "))


def _bonus_chip(v):
    """新品Bonus 数值 → 「新品成长」chip：纯文字等级 较强 / 中等 / 无（不带数字）。
    阈值兼容当前 bonus_c 取值 6/3/0：>=6→较强 / >=2→中等 / else 无。"""
    try:
        v = float(v)
    except (TypeError, ValueError):
        v = 0.0
    if v >= 6:
        label = t("较强", "Strong")
    elif v >= 2:
        label = t("中等", "Medium")
    else:
        return "<span style='color:#c2c8cf;'>—</span>"
    return (f"<span style='background:{BONUS_BG}; color:{BONUS_FG}; border-radius:10px; "
            f"padding:2px 9px; margin-right:5px; font-size:0.82rem; white-space:nowrap;'>{label}</span>")


@st.cache_data
def load_categories():
    """从 db 读方案C（*_c）评分结果（默认权重，不跟随综合评分页滑块）"""
    conn = connect_demo()
    df = pd.read_sql(
        "SELECT category, composite_score_c, tier_c, "
        "positive_signals_c, risk_signal_c, bonus_c, "
        "score_market_size_c, score_openness_c, score_stability_c "
        "FROM category_summary "
        "WHERE COALESCE(is_subcategory,0)=0 "
        "  AND composite_score_c IS NOT NULL "
        "ORDER BY composite_score_c DESC",
        conn,
    )
    conn.close()
    return df


# ---- 品牌脏数据快补（方案A：决策3 盲点 + 解析垃圾）----
AMAZON_BRANDS = {normalize_brand(b) for b in (
    "Amazon", "Amazon Basics", "Blink", "Ring", "eero", "Fire", "Kindle", "Echo",
)}
BRAND_STOPWORDS = {
    "ft", "of", "to", "for", "the", "and", "with", "by", "in", "on", "at",
    "an", "x", "oz", "lb", "cm", "mm", "inch", "pcs", "pc", "pack", "set",
}


def _is_bad_brand(nb):
    """归一化品牌是否为解析垃圾（空 / 单字符 / 停用词）。"""
    return (not nb) or (len(nb) <= 1) or (nb in BRAND_STOPWORDS)


# ---------------------------------------------------------------
# 模块 1：重点 ASIN（全窗口去重池 + 品牌清洗）— 读 asin_daily，与评分口径无关，保持原逻辑
# ---------------------------------------------------------------


CLIMB_MIN = 15        # BS 榜内爬升达到此名次差才算"上升"


@st.cache_data
def compute_top_opportunity_asins(category, lang, top_n=10):
    """重点 ASIN（上升势头清单）：三路信号 + 关注理由。返回 (Top N 表, 已排除品牌分组列表)。
    信号：① 新品冲入畅销榜(NR→BS)；② BS 榜内排名爬升；③ MS→BS（飙升榜先现、后冲进 BS）。均剔 Amazon 自营。
    lang 仅用于缓存分桶（让 @st.cache_data 对中/英各缓存一份），使语言切换后 reason 文案重算。"""
    conn = connect_demo()
    rows = pd.read_sql(
        "SELECT date, list_type, rank, brand, asin, price_low, review_count, rate, "
        "product_url, pct_chg_sales_rank FROM asin_daily "
        "WHERE category=? AND brand IS NOT NULL",
        conn, params=(category,))
    conn.close()
    if rows.empty:
        return None, []
    rows["date"] = pd.to_datetime(rows["date"])
    rows["brand_norm"] = rows["brand"].map(normalize_brand)
    rows = rows.dropna(subset=["brand_norm"])
    rows = rows[~rows["brand_norm"].map(_is_bad_brand)].copy()    # 剔除解析垃圾/空品牌
    if rows.empty:
        return None, []
    bs = rows[rows["list_type"] == "best_seller"]
    nr = rows[rows["list_type"] == "new_release"]
    ms = rows[rows["list_type"] == "movers_shakers"]
    if bs.empty:
        return None, []
    rep = rows.groupby("brand_norm")["brand"].agg(lambda s: s.value_counts().index[0])
    blocked = set(AMAZON_BRANDS)
    amazon_present = sorted((rep[nb] for nb in blocked if nb in rep.index),
                            key=lambda x: (normalize_brand(x) != "amazon", x))
    excluded_groups = (["+".join(amazon_present)] if amazon_present else [])

    pool = rows[~rows["brand_norm"].isin(blocked)]
    if pool.empty:
        return None, excluded_groups
    latest = pool.sort_values("date").groupby("asin").tail(1).set_index("asin")   # 各 ASIN 最新快照

    sigs = []   # (asin, prio, score, reason_text)；prio 越小越优先
    # ① 新品冲入畅销榜：NR 首现日 严格早于 BS 首现日
    bs_first = bs.groupby("asin")["date"].min()
    nr_first = nr.groupby("asin")["date"].min()
    for a in bs_first.index.intersection(nr_first.index):
        if a in latest.index and (bs_first[a] - nr_first[a]).days > 0:
            sigs.append((a, 0, 0.0, t("🚀 NR榜冲进BS榜", "🚀 NR → BS")))
    # ② BS 榜内排名爬升（首现名次 − 最新名次 ≥ CLIMB_MIN）
    bs_pool = bs[~bs["brand_norm"].isin(blocked)]
    for a, g in bs_pool.groupby("asin"):
        if a not in latest.index:
            continue
        g = g.sort_values("date").dropna(subset=["rank"])
        if g["date"].nunique() < 2:
            continue
        r0, r1 = int(g["rank"].iloc[0]), int(g["rank"].iloc[-1])
        climb = r0 - r1
        if climb >= CLIMB_MIN:
            sigs.append((a, 1, float(climb),
                         t(f"⬆️ BS 榜内排名爬升{climb}名（{r0}→{r1}）",
                           f"⬆️ Climbed {climb} spots within BS ({r0}→{r1})")))
    # ③ MS→BS：MS 榜首现日 严格早于 BS 榜首现日（曾在飙升榜出现、之后冲进 BS）。与 ① 同构。
    ms_first = ms.groupby("asin")["date"].min()
    for a in bs_first.index.intersection(ms_first.index):
        if a in latest.index and (bs_first[a] - ms_first[a]).days > 0:
            sigs.append((a, 2, 0.0, t("📈 MS榜冲进BS榜", "📈 MS → BS")))
    if not sigs:
        return None, excluded_groups

    sdf = pd.DataFrame(sigs, columns=["asin", "prio", "score", "reason"])
    sdf = sdf.sort_values(["prio", "score"], ascending=[True, False])     # 高优先 + 大幅度在前
    agg = sdf.groupby("asin", sort=False).agg(
        prio=("prio", "min"),                     # 主信号（多信号取最高优先级）
        score=("score", "first"),                 # 已排序：first = 主信号里幅度最大
        reason=("reason", lambda s: " · ".join(s)),   # 多信号合并理由
    )
    nr_idx = list(agg[agg["prio"] == 0].sort_values("score", ascending=False).index)
    bs_idx = list(agg[agg["prio"] == 1].sort_values("score", ascending=False).index)
    ms_idx = list(agg[agg["prio"] == 2].sort_values("score", ascending=False).index)
    picks = nr_idx[:top_n]
    bi = mi = 0
    while len(picks) < top_n and (bi < len(bs_idx) or mi < len(ms_idx)):
        if mi < len(ms_idx):
            picks.append(ms_idx[mi]); mi += 1
        if len(picks) < top_n and bi < len(bs_idx):
            picks.append(bs_idx[bi]); bi += 1
    sel = agg.loc[picks].sort_values(["prio", "score"], ascending=[True, False])
    out = sel.join(
        latest[["brand", "price_low", "review_count", "rate", "product_url"]]).reset_index()
    return out, excluded_groups


# ---------------------------------------------------------------
# 模块 2：价位分布（三榜 BS/NR/MS 去重池，等比价位段；纯描述不判机会）— 读 asin_daily，保持原逻辑
# ---------------------------------------------------------------


@st.cache_data
def compute_price_distribution(category):
    """价位分布（三榜 BS/NR/MS 去重池，等比价位段）：返回各段 产品占比 + 销量占比 DataFrame 或 None。"""
    conn = connect_demo()
    rows = pd.read_sql(
        "SELECT date, asin, price_low, review_count FROM asin_daily "
        "WHERE category=? AND list_type IN ('best_seller','new_release','movers_shakers') "
        "  AND price_low IS NOT NULL AND price_low > 0 AND review_count IS NOT NULL",
        conn, params=(category,))
    conn.close()
    if rows.empty:
        return None
    rows["date"] = pd.to_datetime(rows["date"])
    snap = rows.sort_values("date").groupby("asin", as_index=False).tail(1).copy()
    n_total = len(snap)
    p_lo = float(snap["price_low"].quantile(0.05))
    p_hi = float(snap["price_low"].quantile(0.95))
    snap = snap[(snap["price_low"] >= p_lo) & (snap["price_low"] <= p_hi)].copy()
    n_excluded = n_total - len(snap)
    if len(snap) < 10:          # 去极值后样本过少则不分析
        return None
    lo, hi = float(snap["price_low"].min()), float(snap["price_low"].max())
    if not (hi > lo > 0):
        return None
    edges = np.geomspace(lo, hi, len(BAND_ORDER) + 1)
    edges[0] *= 0.9999
    edges[-1] *= 1.0001         # 容差，防最低/最高价产品落到区间外
    snap["band"] = pd.cut(snap["price_low"], bins=edges, labels=BAND_ORDER, include_lowest=True)
    snap = snap.dropna(subset=["band"])
    if snap.empty:
        return None
    grouped = snap.groupby("band", observed=True).agg(
        asin_count=("asin", "nunique"),
        price_min=("price_low", "min"),
        price_max=("price_low", "max"),
        review_sum=("review_count", "sum"),
    ).reset_index()
    ta, tr = grouped["asin_count"].sum(), grouped["review_sum"].sum()
    grouped["asin_pct"] = grouped["asin_count"] / ta if ta else 0       # ASIN 数量占比
    grouped["review_pct"] = grouped["review_sum"] / tr if tr else 0     # 评论占比
    grouped["price_range"] = grouped.apply(
        lambda r: f"${r['price_min']:.2f} ~ ${r['price_max']:.2f}", axis=1)
    out = grouped[["band", "price_range", "asin_pct", "review_pct"]]
    out.attrs["n_excluded"] = int(n_excluded)
    out.attrs["p_lo"] = p_lo
    out.attrs["p_hi"] = p_hi
    return out


# -----------------------------------------------------------------------
# 页面
# -----------------------------------------------------------------------
# set_page_config / inject_global_style / app_header 已统一由 app.py（st.navigation 入口）处理

st.markdown(
    """
    <style>
      /* "选择类目" selectbox 标签加粗 */
      [data-testid="stSelectbox"] > label,
      [data-testid="stSelectbox"] > label p {
          font-weight: 600 !important;
          color: #2c3e50 !important;
      }
      /* 摘要卡 metric value 字号 = page_title (1.35rem) */
      [data-testid="stMetric"] [data-testid="stMetricValue"],
      [data-testid="stMetric"] [data-testid="stMetricValue"] div {
          font-size: 1.35rem !important;
          font-weight: 600 !important;
      }
      /* 模块标题（chart_title）比 page_title 小 1 号 ≈ 1.15rem */
      .chart-title {
          font-size: 1.15rem !important;
          font-weight: 600 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

page_title(t("行动指引", "Action Playbook"))

df = load_categories()
if df.empty:
    st.error(t("db.category_summary 没有 *_c评分数据，请先运行 v3 评分引擎写入 *_c 列",
               "No Plan-C (*_c) scoring data in db.category_summary — run the v3 scoring engine first"))
    st.stop()

st.markdown(
    "<div style='color:#6b7280; font-size:0.85rem; margin: 4px 0 16px 0;'>"
    + t("选择一个类目，查看其优先级类型、优势/约束信号、新品成长、价格带参考，以及可切入的重点 ASIN。结果基于默认权重生成。",
        "Pick a category to see its priority type, strength/constraint signals, new-product growth, price-band reference, and entry-worthy ASINs. "
        "Results are based on the default weights.")
    + "</div>",
    unsafe_allow_html=True,
)

# 类目选择器
cats = df["category"].tolist()
selected = st.selectbox(t("🔍 选择类目", "🔍 Select category"), cats, key="action_guide_cat_c")
row = df[df["category"] == selected].iloc[0]

# 排名（按方案C 综合机会分在全部评分类目中的名次）
n_cats = len(df)
ranks = df["composite_score_c"].rank(ascending=False, method="min")
rank_pos = int(ranks[df["category"] == selected].iloc[0])

# 类目摘要卡（3 metric）：综合机会分 / 排名 / 综合优先级(Overall Rating=Tier_c)
c1, c2, c3 = st.columns(3)
c1.metric(t("综合机会分", "Composite Score"), f"{row['composite_score_c']:.1f}")
c2.metric(t("排名", "Rank"), f"#{rank_pos} / {n_cats}",
          help=t("按综合机会分在全部评分类目中的名次",
                 "Rank by opportunity score among all scored categories"))
c3.metric(t("优先级类型", "Priority Type"), TIER_LABEL.get(row["tier_c"], row["tier_c"]),
          help=t("综合分 5 档优先级（百分位）", "5-level priority tier by composite percentile"))

# Opportunity Signals：该类目相对优势/约束 chip（3 维）+ 新品成长（Bonus 单独标签）
st.markdown(
    "<div style='display:flex; gap:28px; align-items:center; flex-wrap:wrap; margin:12px 0 4px;'>"
    f"<div><span style='font-size:0.82rem; color:#6b7280; font-weight:600;'>"
    f"{t('优势信号', 'Top Strengths')}</span>&nbsp;&nbsp;"
    f"{_sig_chips(row['positive_signals_c'], STRENGTH_BG, STRENGTH_FG)}</div>"
    f"<div><span style='font-size:0.82rem; color:#6b7280; font-weight:600;'>"
    f"{t('约束信号', 'Key Constraint')}</span>&nbsp;&nbsp;"
    f"{_sig_chips(row['risk_signal_c'], CONSTRAINT_BG, CONSTRAINT_FG)}</div>"
    f"<div><span style='font-size:0.82rem; color:#6b7280; font-weight:600;'>"
    f"{t('新品成长', 'New-Product Growth')}</span>&nbsp;&nbsp;"
    f"{_bonus_chip(row['bonus_c'])}</div>"
    "</div>",
    unsafe_allow_html=True,
)
# 主因归因（修「档位与信号背离」可读性）：综合机会分主要由哪一维拉动（默认权重 0.40/0.35/0.25）
_dw_c = {"market_size": 0.40, "openness": 0.35, "stability": 0.25}   # = scoring_config_C.yaml 默认
_dim_name_c = {"market_size": t("市场吸引力", "Market Appeal"),
               "openness": t("市场开放度", "Market Openness"),
               "stability": t("结构稳定", "Structural Stability")}
_contrib_c = {d: (row[f"score_{d}_c"] or 0) * w for d, w in _dw_c.items()}
_main_c = max(_contrib_c, key=_contrib_c.get)
st.markdown(
    "<div style='font-size:0.78rem; color:#9ca3af; margin:2px 0 6px;'>"
    + t("综合机会分主要由", "Composite mainly driven by")
    + f"「<b>{_dim_name_c[_main_c]}</b>」" + t("拉动", "")
    + "</div>", unsafe_allow_html=True)
# 注：优势/约束信号 = 3 维（需求/开放度/结构稳定）相对事实；新品成长 = 新品Bonus（S/M/—），
#    单独成标签、不并入三维信号。口径说明见「指标解释」文档，页面不重复。
st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------
# 价位带参考（紧跟优势/约束信号）：仅作该类目价格带的参考，**不提供任何建议**。
# ---------------------------------------------------------------
chart_title(f"● {t('价位带参考', 'Price-Band Reference')} — {selected}")
st.caption(t(
    "把本类目**三榜去重产品**按价格分成 5个**等比价位段**（由低到高、每段约翻同样倍数、自适应各类目；已剔最高/最低各约 5% 极端价）",
    "This category's three-list deduplicated products split into 5 geometric price bands (low→high, adaptive; ~5% extreme prices removed)."))
bands = compute_price_distribution(selected)
if bands is None or bands.empty:
    st.warning(t("数据不足，无法展示价位带参考", "Not enough data for the price-band reference"))
else:
    lbl_a = t("ASIN数量占比", "ASIN share")
    lbl_r = t("评论数占比", "Review share")
    _range_map = dict(zip(bands["band"], bands["price_range"]))
    present = [b for b in BAND_ORDER if b in set(bands["band"])]
    _bv = bands.set_index("band")
    asin_v = [float(_bv.loc[b, "asin_pct"]) for b in present]
    rev_v = [float(_bv.loc[b, "review_pct"]) for b in present]
    BAND_SEQ = ["#dbeafe", "#93c5fd", "#60a5fa", "#3b82f6", "#1e40af"]
    BAND_TXT = ["#1f2937", "#1f2937", "#1f2937", "#ffffff", "#ffffff"]
    _idx = {b: i for i, b in enumerate(BAND_ORDER)}

    xL, xR, halfw = -0.30, 0.70, 0.34   # 条形整体左移（往图例方向靠）
    cumL = np.concatenate([[0.0], np.cumsum(asin_v)])
    cumR = np.concatenate([[0.0], np.cumsum(rev_v)])

    x_sw = -1.31   # 左侧色块 x（紧贴标签左缘）
    col_r = -0.80  # 标签右对齐边界（紧贴引导线，消除图例↔引导线空隙）
    fig = go.Figure()
    for i, b in enumerate(present):
        ci = _idx[b]
        fig.add_bar(
            x=[xL, xR], y=[asin_v[i], rev_v[i]], width=2 * halfw,
            marker=dict(color=BAND_SEQ[ci], line=dict(color="white", width=1)),
            text=[f"{asin_v[i]:.0%}", f"{rev_v[i]:.0%}"],
            textposition="inside", insidetextanchor="middle", textangle=0,
            constraintext="none", cliponaxis=False,
            textfont=dict(color=BAND_TXT[ci], size=12),
            hovertemplate=f"{BAND_LABELS[b]}: {_range_map.get(b, '')}<br>%{{y:.0%}}<extra></extra>",
            showlegend=False,
        )
    fig.update_layout(barmode="stack")

    for k in range(len(present) + 1):
        fig.add_scatter(
            x=[xL + halfw, xR - halfw], y=[cumL[k], cumR[k]],
            mode="lines", line=dict(color="#cbd5e1", width=1, dash="dot"),
            hoverinfo="skip", showlegend=False,
        )

    for i, b in enumerate(present):
        ci = _idx[b]
        yc = (cumL[i] + cumL[i + 1]) / 2
        fig.add_annotation(   # 图例色块
            x=x_sw, y=yc, xref="x", yref="y", text="■",
            showarrow=False, xanchor="left",
            font=dict(size=15, color=BAND_SEQ[ci]),
        )
        fig.add_annotation(   # 价位段名 + 价格范围（右对齐到 col_r，紧贴引导线）
            x=col_r, y=yc, xref="x", yref="y",
            text=f"{BAND_LABELS[b]}: {_range_map.get(b, '')}",
            showarrow=False, xanchor="right",
            font=dict(size=12, color="#374151"),
        )
        fig.add_scatter(   # 引导点线：标签右缘 → 左条边缘（无空隙）
            x=[col_r + 0.02, xL - halfw], y=[yc, yc],
            mode="lines", line=dict(color="#cbd5e1", width=1, dash="dot"),
            hoverinfo="skip", showlegend=False,
        )

    fig.update_xaxes(
        showgrid=False, zeroline=False, showline=False,
        tickmode="array", tickvals=[xL, xR], ticktext=[lbl_a, lbl_r],
        range=[x_sw - 0.08, xR + halfw + 0.06], tickfont=dict(size=13, color="#374151"),
    )
    fig.update_yaxes(visible=False, range=[-0.01, 1.03])
    fig.update_layout(
        height=470, bargap=0.0, plot_bgcolor="white",
        margin=dict(l=14, r=18, t=16, b=34),
    )
    st.plotly_chart(fig, width="stretch")

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------
# 模块 1：Top Opportunity ASINs
# ---------------------------------------------------------------
chart_title(f"● {t('重点 ASIN', 'Top ASINs to Watch')} — {selected}")
st.caption(t(
    "正在「上升」、值得关注的产品（已剔 Amazon 自营族）。三类上升信号平衡选取："
    "🚀 NR榜冲进BS榜 · ⬆️ BS榜内排名爬升 · 📈 MS榜冲进BS榜。",
    "Products on the rise (Amazon family excluded), balanced across three signals: "
    "🚀 NR → BS · ⬆️ climbing within BS · 📈 MS → BS."))
top_df, excluded_brands = compute_top_opportunity_asins(selected, get_lang(), top_n=10)
if excluded_brands:
    st.caption(t("注：已排除 Amazon 品牌族：", "Note: excluded Amazon family: ")
               + ", ".join(excluded_brands))
if top_df is None or top_df.empty:
    st.warning(t("窗口内没有符合三类上升信号的非头部 ASIN",
                 "No non-leader ASINs matched the three rising signals in this window"))
else:
    display = top_df[["reason", "brand", "asin", "price_low", "review_count", "rate", "product_url"]].copy()
    col_reason = t("关注理由", "Why watch")
    col_brand = t("品牌", "Brand")
    col_price = t("价格 ($)", "Price ($)")
    col_reviews = t("评论数", "Reviews")
    col_rating = t("评分", "Rating")
    col_link = t("Amazon 链接", "Amazon Link")
    display.columns = [col_reason, col_brand, "ASIN", col_price, col_reviews, col_rating, col_link]
    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        column_config={
            col_reason:   st.column_config.TextColumn(width="large",
                help=t("该 ASIN 入选的上升信号（可能多条）", "Rising signal(s) this ASIN matched")),
            col_price:    st.column_config.NumberColumn(format="$%.2f"),
            col_reviews:  st.column_config.NumberColumn(format="%d"),
            col_rating:   st.column_config.NumberColumn(format="%.1f"),
            col_link:     st.column_config.LinkColumn(display_text=t("🔗 打开", "🔗 Open")),
        },
    )

# 注：方案C 摘要 = 优先级(Tier_c) + 3 维优势/约束信号 + 新品成长(Bonus) 单独标签；
#    价位带参考 + 重点 ASIN 读 asin_daily、与评分口径无关，保持原逻辑。

# streamlit_app/pages/5_行动指引.py
# 更新日期：2026-06-29
# 用途：行动指引页（Demo 版，对齐生产 v2）— 单类目深度。
#       模块：摘要（优先级类型 + Opportunity Signals 优势/约束）→ 价位带参考（100% 堆积条）→ 重点 ASIN。
# 启动命令：streamlit run streamlit_app/产品概览.py
# 与生产 v2 差异：
#   - 数据源 data/amazon.db → data/*.csv（connect_demo）；类目/品牌/ASIN 已匿名化
#   - positive_signals / risk_signal：生产 v2 由评分引擎写入 db（CSV 无此两列）。Demo 在
#     load 时**用与 v2 评分引擎同一套百分位算法**（A/C/M/T 四维 P75→优势 / P25→约束，
#     优势取分值最高 2 个、约束取最严 1 个）从 5 维分现算，非造数据。
#   - 优先级类型(Tier)：从 composite_score 百分位重算（与综合评分页同口径）。
# 主要改动：
#   - 2026-06-29（信号体系同步生产 v2）：① 增长动能(momentum)退出优势/约束信号（方向歧义）——
#       SIG_DIMS 删 momentum 维（不再生成 High/Weak Momentum 信号）、SIGNAL_LABELS 同删两键。
#       ② 需求信号软化为「需求居前/需求居后」(Top/Bottom-quartile demand)。③ 结构稳定信号改
#       「波动较小/波动较大」(Low/High volatility)。均仅改显示名，内部英文键不变。
#   - 2026-06-29：关注理由列 + 重点 ASIN 说明措辞统一为简写——🚀NR榜新品冲进BS榜 /
#       ⬆️BS榜内排名爬升X名(r0→r1) / 📈MS榜排名飙升+X%（仅改展示字符串，信号逻辑/阈值不变）。
#   - 2026-06-29：修「关注理由」列语言切不动的缓存 bug——compute_top_opportunity_asins 加 lang
#       参数（仅用于 @st.cache_data 缓存分桶），调用处传 get_lang()，使中/英各缓存一份、切换后重算。
#   - 2026-06-28：从生产 v2 pages/5_行动指引.py 移植；信号/Tier 由 db 列改为现算（CSV 后端适配）。

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

# ---- Opportunity Signals ----
# Overall Rating(=Tier) 展示简称 + 徽章色
TIER_LABEL = {
    "高潜机会类目": t("高潜机会", "Top"),     "较高机会类目": t("较高机会", "High"),
    "中性观察类目": t("中性观察", "Balanced"), "谨慎评估类目": t("谨慎评估", "Watch"),
    "暂不考虑类目": t("暂不考虑", "Skip"),
}
# 信号中英显示名（db 英文键不变，仅改显示；正向=优势/绿 chip，负向=约束/琥珀 chip）
# momentum 不参与信号（方向歧义：高=有上升通道/也=赛道变挤），故无 High/Weak Momentum 映射
SIGNAL_LABELS = {
    "Strong Demand":    t("需求居前", "Top-quartile demand"), "Open Market":     t("市场开放", "Open Market"),
    "Weak Demand":      t("需求居后", "Bottom-quartile demand"), "Brand Barrier":  t("品牌壁垒", "Brand Barrier"),
    "Stable Structure": t("波动较小", "Low volatility"), "Unstable Structure": t("波动较大", "High volatility"),
}
STRENGTH_BG, CONSTRAINT_BG = "#e8f6ef", "#fdece4"
STRENGTH_FG, CONSTRAINT_FG = "#1e8449", "#ba4a00"

# ---- 信号 / Tier 现算配置（= 生产 v2 scoring_config.yaml opportunity_signals + tier_thresholds）----
# 注：momentum 不参与信号（= 生产 v2，方向歧义），故 SIG_DIMS 不含 momentum 维 → 不生成任何动能信号
SIG_DIMS = [
    {"key": "market_size", "col": "score_market_size", "positive": "Strong Demand",   "risk": "Weak Demand"},
    {"key": "openness",    "col": "score_openness",    "positive": "Open Market",      "risk": "Brand Barrier"},
    {"key": "stability",   "col": "score_stability",   "positive": "Stable Structure", "risk": "Unstable Structure"},
]
SIG_PCT_LOW, SIG_PCT_HIGH = 0.25, 0.75
SIG_MAX_POS, SIG_MAX_RISK = 2, 1
TIER_THRESHOLDS = [
    (0.80, "高潜机会类目"), (0.60, "较高机会类目"), (0.40, "中性观察类目"),
    (0.20, "谨慎评估类目"), (0.00, "暂不考虑类目"),
]


def assign_tier(scores: pd.Series) -> pd.Series:
    pct = scores.rank(pct=True)
    def to_tier(p):
        for thr, label in TIER_THRESHOLDS:
            if p >= thr:
                return label
        return TIER_THRESHOLDS[-1][1]
    return pct.apply(to_tier)


def compute_signals(df):
    """Opportunity Signals（百分位法，= 生产 v2 评分引擎 compute_signals 逐字复刻）。
    对 SIG_DIMS 每维（A/C/M/T，不含 new_product）在全部类目上算 P25/P75：
      ≥P75 → Positive 候选；≤P25 → Risk 候选。
    Positive 取分值最高 2 个；Risk 取分值最低（最严）1 个。无候选留空。
    """
    cutoffs = {}
    for d in SIG_DIMS:
        s = df[d["col"]]
        cutoffs[d["key"]] = (s.quantile(SIG_PCT_LOW), s.quantile(SIG_PCT_HIGH))
    pos_out, risk_out = [], []
    for _, row in df.iterrows():
        pos, risk = [], []
        for d in SIG_DIMS:
            v = row[d["col"]]
            lo, hi = cutoffs[d["key"]]
            if v >= hi:
                pos.append((v, d["positive"]))
            if v <= lo:
                risk.append((v, d["risk"]))
        pos_labels = [lab for _, lab in sorted(pos, reverse=True)[:SIG_MAX_POS]]
        risk_labels = [lab for _, lab in sorted(risk)[:SIG_MAX_RISK]]
        pos_out.append(" + ".join(pos_labels) if pos_labels else None)
        risk_out.append(" + ".join(risk_labels) if risk_labels else None)
    out = df.copy()
    out["positive_signals"] = pos_out
    out["risk_signal"] = risk_out
    return out


def _sig_chips(s, bg, fg):
    """'Strong Demand + Open Market' → 彩色 chip；空→灰 —"""
    if s is None or (isinstance(s, float) and pd.isna(s)) or str(s).strip() in ("", "—", "None", "nan"):
        return "<span style='color:#c2c8cf;'>—</span>"
    return "".join(
        f"<span style='background:{bg}; color:{fg}; border-radius:10px; padding:2px 9px; "
        f"margin-right:5px; font-size:0.82rem; white-space:nowrap;'>{SIGNAL_LABELS.get(l, l)}</span>"
        for l in str(s).split(" + "))


@st.cache_data
def load_categories():
    """从 category_summary 读评分；优先级类型(Tier) + Opportunity Signals 现算（CSV 后端无此列）。"""
    conn = connect_demo()
    df = pd.read_sql(
        "SELECT category, composite_score, "
        "score_market_size, score_openness, score_new_product, "
        "score_momentum, score_stability, est_monthly_gmv "
        "FROM category_summary "
        "WHERE COALESCE(is_subcategory,0)=0 "
        "  AND composite_score IS NOT NULL "
        "ORDER BY composite_score DESC",
        conn,
    )
    if df.empty:
        return df
    # 优先级类型(Tier)：与综合评分页同口径，从 composite_score 百分位重算（避免 CSV 旧 tier 名）
    df["tier"] = assign_tier(df["composite_score"])
    # Opportunity Signals：百分位法 P25/P75 现算（= 生产 v2 评分引擎算法，非造数据）
    df = compute_signals(df)
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
# 模块 1：重点 ASIN（全窗口去重池 + 品牌清洗）
# ---------------------------------------------------------------
CLIMB_MIN = 15        # BS 榜内爬升达到此名次差才算"上升"
MS_SURGE_CAP = 300    # MS 飙升率上限：> 此值多为排名重置脏数据，直接剔除不选
MS_TOP = 8            # MS 候选最多取这么多（按飙升幅度）


@st.cache_data
def compute_top_opportunity_asins(category, lang, top_n=10):
    """重点 ASIN（上升势头清单）：三路信号 + 关注理由。返回 (Top N 表, 已排除品牌分组列表)。
    lang 仅用于缓存分桶（让 @st.cache_data 对中/英各缓存一份），使语言切换后 reason 文案重算；
    函数体不直接使用它——reason 里的 t() 仍读全局 session，与调用时传入的 lang 一致。"""
    conn = connect_demo()
    rows = pd.read_sql(
        "SELECT date, list_type, rank, brand, asin, price_low, review_count, rate, "
        "product_url, pct_chg_sales_rank FROM asin_daily "
        "WHERE category=? AND brand IS NOT NULL",
        conn, params=(category,))
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
    # 排除集：仅 Amazon 第一方族（第三方进不去）。
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
            sigs.append((a, 0, 0.0, t("🚀 NR榜新品冲进BS榜", "🚀 NR new release → BS bestseller")))
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
    # ③ MS 飙升：每 ASIN 取最大提升率；剔除 >MS_SURGE_CAP 的，取真实值 Top
    ms_pool = ms[~ms["brand_norm"].isin(blocked)].dropna(subset=["pct_chg_sales_rank"])
    if not ms_pool.empty:
        ms_best = ms_pool.groupby("asin")["pct_chg_sales_rank"].max()
        ms_best = ms_best[(ms_best > 0) & (ms_best <= MS_SURGE_CAP)].sort_values(ascending=False).head(MS_TOP)
        for a, v in ms_best.items():
            if a in latest.index:
                sigs.append((a, 2, float(v), t(f"📈 MS榜排名飙升+{v:.0f}%", f"📈 MS rank surge +{v:.0f}%")))
    if not sigs:
        return None, excluded_groups

    sdf = pd.DataFrame(sigs, columns=["asin", "prio", "score", "reason"])
    sdf = sdf.sort_values(["prio", "score"], ascending=[True, False])     # 高优先 + 大幅度在前
    agg = sdf.groupby("asin", sort=False).agg(
        prio=("prio", "min"),                     # 主信号（多信号取最高优先级）
        score=("score", "first"),                 # 已排序：first = 主信号里幅度最大
        reason=("reason", lambda s: "\n".join(s)),   # 多信号合并理由：逐条换行展示
    )
    # 三信号「平衡」选取 top_n
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
    # 选取是平衡的；但显示按信号分组（新品冲榜 → BS爬升 → MS飙升），同组按幅度从大到小，不交叉
    sel = agg.loc[picks].sort_values(["prio", "score"], ascending=[True, False])
    out = sel.join(
        latest[["brand", "price_low", "review_count", "rate", "product_url"]]).reset_index()
    return out, excluded_groups


# ---------------------------------------------------------------
# 模块 2：价位分布（三榜 BS/NR/MS 去重池，等比价位段；纯描述不判机会）
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
    if rows.empty:
        return None
    rows["date"] = pd.to_datetime(rows["date"])
    snap = rows.sort_values("date").groupby("asin", as_index=False).tail(1).copy()
    # 分箱前两端去极值——剔除价格 < P5 与 > P95 的极端品
    n_total = len(snap)
    p_lo = float(snap["price_low"].quantile(0.05))
    p_hi = float(snap["price_low"].quantile(0.95))
    snap = snap[(snap["price_low"] >= p_lo) & (snap["price_low"] <= p_hi)].copy()
    n_excluded = n_total - len(snap)
    if len(snap) < 10:          # 去极值后样本过少则不分析
        return None
    # 等比(log 等宽)分箱：按「倍数」把价格切成 N 段
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
    out.attrs["n_excluded"] = int(n_excluded)   # 两端去极值剔除的极端品数（页面提示用）
    out.attrs["p_lo"] = p_lo
    out.attrs["p_hi"] = p_hi
    return out


# -----------------------------------------------------------------------
# 页面
# -----------------------------------------------------------------------
# 本页字号微调（覆盖 _styles.py 默认 chart_title 0.92rem / metric value 默认 ~2rem）
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
    st.error(t("category_summary 没有评分数据", "No scoring data in category_summary"))
    st.stop()

st.markdown(
    "<div style='color:#6b7280; font-size:0.85rem; margin: 4px 0 16px 0;'>"
    + t("选择一个类目，查看其优先级类型、优势/约束信号、价格带参考，以及可切入的重点 ASIN。结果基于默认权重生成。",
        "Pick a category to see its priority type, strength/constraint signals, price-band reference, and entry-worthy ASINs. "
        "Results are based on the default weights.")
    + "</div>",
    unsafe_allow_html=True,
)

# 类目选择器
cats = df["category"].tolist()
selected = st.selectbox(t("🔍 选择类目", "🔍 Select category"), cats, key="action_guide_cat")
row = df[df["category"] == selected].iloc[0]

# 排名（按综合机会分在全部评分类目中的名次，替代原 Tier 等级）
n_cats = len(df)
ranks = df["composite_score"].rank(ascending=False, method="min")
rank_pos = int(ranks[df["category"] == selected].iloc[0])

# 类目摘要卡（3 metric）：综合机会分 / 排名 / 综合优先级(Overall Rating=Tier)
c1, c2, c3 = st.columns(3)
c1.metric(t("综合机会分", "Composite Score"), f"{row['composite_score']:.3f}")
c2.metric(t("排名", "Rank"), f"#{rank_pos} / {n_cats}",
          help=t("按综合机会分在全部评分类目中的名次",
                 "Rank by opportunity score among all scored categories"))
c3.metric(t("优先级类型", "Priority Type"), TIER_LABEL.get(row["tier"], row["tier"]),
          help=t("综合分 5 档优先级（百分位）", "5-level priority tier by composite percentile"))

# Opportunity Signals：该类目相对优势/约束 chip（结构事实，不随评分页权重变）
st.markdown(
    "<div style='display:flex; gap:28px; align-items:center; flex-wrap:wrap; margin:12px 0 4px;'>"
    f"<div><span style='font-size:0.82rem; color:#6b7280; font-weight:600;'>"
    f"{t('优势信号', 'Top Strengths')}</span>&nbsp;&nbsp;"
    f"{_sig_chips(row['positive_signals'], STRENGTH_BG, STRENGTH_FG)}</div>"
    f"<div><span style='font-size:0.82rem; color:#6b7280; font-weight:600;'>"
    f"{t('约束信号', 'Key Constraint')}</span>&nbsp;&nbsp;"
    f"{_sig_chips(row['risk_signal'], CONSTRAINT_BG, CONSTRAINT_FG)}</div>"
    "</div>",
    unsafe_allow_html=True,
)
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
    # 段标签 = 价位段名 + 价格范围（如「低价段: $6.98 ~ $14.38」），随类目变；价位段名放左侧
    _range_map = dict(zip(bands["band"], bands["price_range"]))
    present = [b for b in BAND_ORDER if b in set(bands["band"])]
    _bv = bands.set_index("band")
    asin_v = [float(_bv.loc[b, "asin_pct"]) for b in present]
    rev_v = [float(_bv.loc[b, "review_pct"]) for b in present]
    # 配色：低→高 浅→深蓝；浅段深字、深段白字
    BAND_SEQ = ["#dbeafe", "#93c5fd", "#60a5fa", "#3b82f6", "#1e40af"]
    BAND_TXT = ["#1f2937", "#1f2937", "#1f2937", "#ffffff", "#ffffff"]
    _idx = {b: i for i, b in enumerate(BAND_ORDER)}

    xL, xR, halfw = -0.30, 0.70, 0.34   # 条形整体左移（往图例方向靠）
    cumL = np.concatenate([[0.0], np.cumsum(asin_v)])
    cumR = np.concatenate([[0.0], np.cumsum(rev_v)])

    x_sw = -1.31   # 左侧色块 x（紧贴标签左缘）
    col_r = -0.80  # 标签右对齐边界（紧贴引导线，消除图例↔引导线空隙）
    fig = go.Figure()
    # 两根 100% 堆积条（低价格段在最底→高价格段在最顶）；百分比直接标在各段内（不缩字、不转向）
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

    # 两条之间：各价位段边界用点线相连（看同一段在产品/需求两侧占比的此消彼长）
    for k in range(len(present) + 1):
        fig.add_scatter(
            x=[xL + halfw, xR - halfw], y=[cumL[k], cumR[k]],
            mode="lines", line=dict(color="#cbd5e1", width=1, dash="dot"),
            hoverinfo="skip", showlegend=False,
        )

    # 左侧图例列：色块（最左成列）+ 价位段名(价格范围)（右对齐）+ 引导点线 → 左条各段中心
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
    "🚀 NR榜新品冲进BS榜 · ⬆️ BS榜内排名爬升 · 📈 MS榜排名飙升。",
    "Products on the rise (Amazon family excluded), balanced across three signals: "
    "🚀 NR new release → BS bestseller · ⬆️ climbing within BS · 📈 MS rank surge."))
top_df, excluded_brands = compute_top_opportunity_asins(selected, get_lang(), top_n=10)
if excluded_brands:
    st.caption(t("注：已排除 Amazon 品牌族：", "Note: excluded Amazon family: ")
               + ", ".join(excluded_brands))
if top_df is None or top_df.empty:
    st.warning(t("窗口内没有符合三类上升信号的非头部 ASIN",
                 "No non-leader ASINs matched the three rising signals in this window"))
else:
    # 展示表：关注理由 + 基本信息（product_url 走 LinkColumn）
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

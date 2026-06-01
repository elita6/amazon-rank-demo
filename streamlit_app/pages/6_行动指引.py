# demo/streamlit_app/pages/2_行动指引.py
# 更新日期：2026-05-12
# 用途：Demo 版行动指引页（5 类目 + 5 strategy 全覆盖）
# 与生产版差异：
#   - 数据源 db → demo csv（in-memory sqlite）
#   - selectbox 只允许 Category A + Category E（反差最大：Top Pick vs Avoid）
#   - PLAYBOOK 公开 2 个 archetype + 11 个 locked 仅显示名字 + strategy badge

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from _styles import inject_global_style, app_header, page_title, chart_title
from _demo_data import connect_demo


# Demo 公开 2 个 archetype（对应 selectbox 可选的 2 类目：Category A + Category E）
PLAYBOOK = {
    "新兴机会": {
        "desc": "小盘但通道开放 + 新品空间足 — 早期机会",
        "actions": [
            "优先中低评论商品切入（≤200 评论 + ≥4.0 分）",
            "抢占供需缺口价格带（参考上方价格机会模块）",
            "快速测试新品（小批量 100-300 单试水）",
            "监控窗口是否继续打开（参考上方市场窗口模块）",
        ],
    },
    "低效开放市场": {
        "desc": "小盘 + 看似开放 + 新品空间小或不稳 — 弱势 / 噪声市场",
        "actions": [
            "市场开放但需求弱，谨慎进入",
            "仅做低成本测试（<$2k 试水预算）",
            "若数据噪声大（评论 / 销量异常波动），暂缓不动",
            "考虑放弃，时间投入到 Top Pick 类目",
        ],
    },
}

# 完整 13 archetype 概览（locked desc 留空，仅 unlocked 展示描述 —— 防源码侧泄露 5 维组合到业务标签的映射）
ALL_ARCHETYPES = [
    ("成熟优质市场",   "Top Pick",   "",                                       False),
    ("成长蓝海",       "Top Pick",   "",                                       False),
    ("新兴机会",       "Top Pick",   "小盘但通道开放 + 新品空间足",            True),
    ("高热红海",       "Crowded",    "",                                       False),
    ("高成长高波动",   "Hidden Gem", "",                                       False),
    ("新品潜力区",     "Watch",      "",                                       False),
    ("稳定现金流市场", "Watch",      "",                                       False),
    ("高门槛利基",     "Watch",      "",                                       False),
    ("稳态老品市场",   "Watch",      "",                                       False),
    ("大盘冷门",       "Avoid",      "",                                       False),
    ("低效开放市场",   "Avoid",      "小盘 + 看似开放 + 新品空间小或不稳",     True),
    ("冷门封闭",       "Avoid",      "",                                       False),
    ("待诊断",         "Avoid",      "",                                       False),
]


@st.cache_data
def load_categories():
    conn = connect_demo()
    df = pd.read_sql(
        "SELECT category, composite_score, tier, archetype, strategy_tag, "
        "score_market_size, score_openness, score_new_product, "
        "score_momentum, score_stability, est_monthly_gmv "
        "FROM category_summary "
        "WHERE COALESCE(is_subcategory,0)=0 "
        "  AND composite_score IS NOT NULL "
        "ORDER BY composite_score DESC",
        conn,
    )
    return df


@st.cache_data
def compute_top_opportunity_asins(category, top_n=5):
    conn = connect_demo()
    cr3 = pd.read_sql(
        "SELECT brand, COUNT(*) AS n FROM asin_daily "
        "WHERE category=? AND list_type='best_seller' AND brand IS NOT NULL "
        "GROUP BY brand ORDER BY n DESC LIMIT 3",
        conn, params=(category,))
    cr3_brands = set(cr3["brand"].tolist())

    latest_date = conn.execute(
        "SELECT MAX(date) FROM asin_daily WHERE category=? AND list_type='best_seller'",
        (category,)).fetchone()[0]
    if latest_date is None:
        return None, cr3_brands

    candidates = pd.read_sql(
        "SELECT rank, brand, asin, price_low, review_count, rate, product_url "
        "FROM asin_daily "
        "WHERE category=? AND list_type='best_seller' AND date=? AND brand IS NOT NULL",
        conn, params=(category, latest_date))

    if candidates.empty:
        return None, cr3_brands

    review_median = candidates["review_count"].median()
    cand = candidates[~candidates["brand"].isin(cr3_brands)].copy()
    if cand.empty:
        return None, cr3_brands

    cand["review_gap"] = (1 - cand["review_count"] / max(review_median, 1)).clip(0, 1)
    cand["rating_percentile"] = cand["rate"].rank(pct=True)

    cand = cand.sort_values(
        by=["review_gap", "rank", "rating_percentile"],
        ascending=[False, True, False],
    ).head(top_n).reset_index(drop=True)

    return cand, cr3_brands


@st.cache_data
def compute_price_gap(category):
    conn = connect_demo()
    latest_date = conn.execute(
        "SELECT MAX(date) FROM asin_daily WHERE category=? AND list_type='best_seller'",
        (category,)).fetchone()[0]
    if latest_date is None:
        return None
    df = pd.read_sql(
        "SELECT price_low, review_count FROM asin_daily "
        "WHERE category=? AND list_type='best_seller' AND date=? "
        "  AND price_low IS NOT NULL AND price_low > 0 "
        "  AND review_count IS NOT NULL",
        conn, params=(category, latest_date))

    if df.empty:
        return None

    df["log_price"] = np.log(df["price_low"])
    df["sales_heat"] = np.log1p(df["review_count"]) * df["price_low"]

    band_labels = ["Low", "Mass", "Premium", "High Premium"]
    try:
        df["band"] = pd.qcut(df["log_price"], q=4, labels=band_labels, duplicates="drop")
    except ValueError:
        return None

    grouped = df.groupby("band", observed=True).agg(
        asin_count=("price_low", "count"),
        price_min=("price_low", "min"),
        price_max=("price_low", "max"),
        total_heat=("sales_heat", "sum"),
    ).reset_index()

    total_asin = grouped["asin_count"].sum()
    total_heat = grouped["total_heat"].sum()
    grouped["supply_pct"] = grouped["asin_count"] / total_asin if total_asin else 0
    grouped["demand_pct"] = grouped["total_heat"] / total_heat if total_heat else 0
    grouped["gap"] = grouped["demand_pct"] - grouped["supply_pct"]
    grouped["price_range"] = grouped.apply(
        lambda r: f"${r['price_min']:.2f} ~ ${r['price_max']:.2f}", axis=1)

    return grouped[["band", "price_range", "asin_count", "supply_pct", "demand_pct", "gap"]]


# 业务校准的项目特定阈值（非通用配方；其他数据集需重新标定）
# 生产版本通过 28d 滚动窗口的指标 std × 系数动态计算
THRESHOLDS = {"CR3": 0.015, "HHI": 0.003, "Retention": 0.020}


@st.cache_data
def compute_market_window(category):
    conn = connect_demo()
    daily = pd.read_sql(
        "SELECT date, cr3, hhi FROM category_daily_metrics "
        "WHERE category=? AND list_type='best_seller' ORDER BY date",
        conn, params=(category,))
    asin = pd.read_sql(
        "SELECT date, brand FROM asin_daily "
        "WHERE category=? AND list_type='best_seller' AND brand IS NOT NULL",
        conn, params=(category,))

    if daily.empty or len(daily) < 10:
        return None, None, None, None

    brands_by_date = asin.groupby("date")["brand"].apply(lambda s: set(s.unique()))
    ret_rows = []
    dates_sorted = sorted(brands_by_date.index)
    for i in range(1, len(dates_sorted)):
        prev = brands_by_date[dates_sorted[i - 1]]
        curr = brands_by_date[dates_sorted[i]]
        if prev:
            ret_rows.append({"date": dates_sorted[i], "retention": len(curr & prev) / len(prev)})
    retention_df = pd.DataFrame(ret_rows)

    d = daily.sort_values("date").reset_index(drop=True)
    n = len(d)
    last7 = d.iloc[max(0, n - 7):n]
    prev7 = d.iloc[max(0, n - 14):max(0, n - 7)]

    cr3_delta = last7["cr3"].mean() - prev7["cr3"].mean()
    hhi_delta = last7["hhi"].mean() - prev7["hhi"].mean()

    if len(retention_df) >= 8:
        r = retention_df.sort_values("date").reset_index(drop=True)
        rn = len(r)
        retention_delta = (r.iloc[max(0, rn - 7):rn]["retention"].mean()
                           - r.iloc[max(0, rn - 14):max(0, rn - 7)]["retention"].mean())
    else:
        retention_delta = None

    def direction_and_score(name, delta):
        if delta is None:
            return "n/a", 0
        thr = THRESHOLDS[name]
        if delta <= -thr:
            return "opening", +1
        if delta >= thr:
            return "closing", -1
        return "stable", 0

    score = 0
    signals = []
    for name, val in [("CR3", cr3_delta), ("HHI", hhi_delta), ("Retention", retention_delta)]:
        dir_, sc = direction_and_score(name, val)
        signals.append({"name": name, "delta": val, "direction": dir_,
                        "threshold": THRESHOLDS[name], "contrib": sc})
        score += sc

    if score >= 2:
        state = "Opening"
    elif score <= -2:
        state = "Closing"
    else:
        state = "Stable"

    return state, signals, d, score


# -----------------------------------------------------------------------
# 页面
# -----------------------------------------------------------------------
st.set_page_config(page_title="行动指引 · Demo", layout="wide")
inject_global_style()
app_header()

st.markdown(
    "<div style='background:#fff7ed; border-left:4px solid #f59e0b; "
    "padding:8px 14px; margin: 4px 0 10px 0; border-radius:4px; font-size:0.85rem; color:#7c2d12;'>"
    "🎭 <b>Demo Mode</b> — 节选2类目展示 "
    "</div>",
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
      [data-testid="stSelectbox"] > label,
      [data-testid="stSelectbox"] > label p {
          font-weight: 600 !important;
          color: #2c3e50 !important;
      }
      [data-testid="stMetric"] [data-testid="stMetricValue"],
      [data-testid="stMetric"] [data-testid="stMetricValue"] div {
          font-size: 1.35rem !important;
          font-weight: 600 !important;
      }
      .chart-title {
          font-size: 1.15rem !important;
          font-weight: 600 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

page_title("行动指引")

df = load_categories()
if df.empty:
    st.error("demo/data/category_summary.csv 没有评分数据")
    st.stop()

st.markdown(
    "<div style='color:#6b7280; font-size:0.85rem; margin: 4px 0 16px 0;'>"
    "选择一个类目，查看其业务类型对应的打法建议。"
    "</div>",
    unsafe_allow_html=True,
)

# demo 限制只暴露 2 个类目（A=新兴机会/Top Pick，E=低效开放/Avoid），反差最大
ALLOWED_CATS = ["Category A", "Category E"]
cats = [c for c in df["category"].tolist() if c in ALLOWED_CATS]
selected = st.selectbox("🔍 选择类目", cats, key="action_guide_cat")
row = df[df["category"] == selected].iloc[0]
archetype = row["archetype"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("综合机会分", f"{row['composite_score']:.3f}")
c2.metric("等级", row["tier"])
c3.metric("业务类型", archetype)
c4.metric("策略建议", row["strategy_tag"])

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# 模块 1：重点 ASIN
chart_title(f"● 重点 ASIN — {selected}")
top_df, cr3_brands = compute_top_opportunity_asins(selected, top_n=5)
if cr3_brands:
    st.caption(f"注：已排除 CR3 头部品牌：{', '.join(sorted(cr3_brands))}")
if top_df is None or top_df.empty:
    st.warning("没有符合条件的候选 ASIN")
else:
    display = top_df.copy()
    display = display[["rank", "brand", "asin", "price_low", "review_count", "rate",
                       "review_gap", "rating_percentile", "product_url"]]
    display.columns = ["榜单排名", "品牌", "ASIN", "价格 ($)", "评论数", "评分",
                       "评论缺口", "评分百分位", "链接"]
    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        column_config={
            "价格 ($)":    st.column_config.NumberColumn(format="$%.2f"),
            "评论数":      st.column_config.NumberColumn(format="%d"),
            "评分":        st.column_config.NumberColumn(format="%.1f"),
            "评论缺口":    st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f",
                                                            help="评论数相对类目中位的缺口比例 — 越高表示成长空间越大"),
            "评分百分位":  st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f",
                                                            help="类目内 rating 的排名分位 — 越高表示产品质量越靠前"),
            "链接":        st.column_config.LinkColumn(display_text="🔗 demo"),
        },
    )

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# 模块 2：价格机会
chart_title(f"● 价格机会 — {selected}")
bands = compute_price_gap(selected)
if bands is None or bands.empty:
    st.warning("数据不足，无法分析价格带")
else:
    pg_col1, pg_col2 = st.columns([1.5, 1])
    with pg_col1:
        plot_df = bands.melt(
            id_vars=["band", "price_range"],
            value_vars=["supply_pct", "demand_pct"],
            var_name="metric", value_name="pct",
        )
        plot_df["metric"] = plot_df["metric"].map(
            {"supply_pct": "供给（ASIN 占比）", "demand_pct": "需求（sales_heat 占比）"})
        fig = px.bar(
            plot_df, x="band", y="pct", color="metric",
            barmode="group",
            color_discrete_map={"供给（ASIN 占比）": "#94a3b8", "需求（sales_heat 占比）": "#3498db"},
            height=300,
            labels={"band": "价格带", "pct": "占比"},
        )
        fig.update_layout(
            yaxis=dict(tickformat=".0%"),
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig, width="stretch")

    with pg_col2:
        display = bands.copy()
        display["supply_pct"] = display["supply_pct"].apply(lambda x: f"{x:.0%}")
        display["demand_pct"] = display["demand_pct"].apply(lambda x: f"{x:.0%}")
        display["gap"] = display["gap"].apply(lambda x: f"{x:+.1%}")
        display = display[["band", "price_range", "asin_count", "gap"]]
        display.columns = ["价格带", "价格范围", "ASIN 数", "Gap"]
        st.dataframe(display, hide_index=True, use_container_width=True)

    best = bands.loc[bands["gap"].idxmax()]
    if best["gap"] > 0:
        st.markdown(
            f"<div style='color:#27ae60; font-size:0.9rem; padding:8px 12px; "
            f"background:#f0fdf4; border-left:3px solid #27ae60; border-radius:4px; margin-top:8px;'>"
            f"🎯 <b>机会价格带</b>：{best['band']}（{best['price_range']}）"
            f" — gap = {best['gap']:+.1%}（需求 > 供给）"
            f"</div>",
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# 模块 3：市场窗口
chart_title(f"● 市场窗口 — {selected}")
state, signals, daily_df, score = compute_market_window(selected)
if state is None:
    st.warning("日度数据不足 14 天，无法计算市场窗口")
else:
    state_meta = {
        "Opening": {"label": "打开中", "color": "#27ae60", "icon": "↑", "desc": "窗口正在打开 — 头部松动/新品牌涌入"},
        "Stable":  {"label": "稳定",   "color": "#94a3b8", "icon": "→", "desc": "结构稳定 — 无显著变化"},
        "Closing": {"label": "关闭中", "color": "#e74c3c", "icon": "↓", "desc": "窗口正在关闭 — 头部固化/品牌固定"},
    }
    sm = state_meta[state]
    st.markdown(
        f"<div style='background:{sm['color']}; color:#fff; padding:10px 14px; "
        f"border-radius:6px; font-size:1.05rem; font-weight:600; margin-bottom:12px;'>"
        f"{sm['icon']} {sm['label']} <span style='font-weight:400; font-size:0.92rem;'>"
        f"(得分 {score:+d}) — {sm['desc']}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    sig_meta = {
        "opening": {"color": "#27ae60", "icon": "↓", "label": "opening"},
        "closing": {"color": "#e74c3c", "icon": "↑", "label": "closing"},
        "stable":  {"color": "#94a3b8", "icon": "—", "label": "stable"},
    }
    sig_cols = st.columns(3)
    for i, s in enumerate(signals):
        with sig_cols[i]:
            d = s["delta"]
            delta_txt = f"{d:+.3f}" if d is not None else "n/a"
            m = sig_meta.get(s["direction"], sig_meta["stable"])
            contrib = s.get("contrib", 0)
            contrib_txt = f"{contrib:+d}" if contrib else "0"
            st.markdown(
                f"<div style='border:1px solid #e6e9ee; border-radius:6px; padding:10px 14px; background:#fafbfd;'>"
                f"<div style='font-size:0.8rem; color:#6b7280;'>{s['name']} delta "
                f"(阈值 ±{s['threshold']:.3f})</div>"
                f"<div style='font-size:1.25rem; color:{m['color']}; font-weight:600; line-height:1.4;'>"
                f"{m['icon']} {delta_txt}</div>"
                f"<div style='font-size:0.75rem; color:#9ca3af;'>{m['label']} ({contrib_txt})</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# 模块 4：Playbook（公开 5 archetype）
pb = PLAYBOOK.get(archetype)
chart_title(f"● 打法建议 — {archetype}")
if pb is None:
    st.markdown(
        f"<div style='color:#475569; font-size:0.92rem; margin: 4px 0 14px 0; "
        f"padding:10px 14px; background:#f1f5f9; border-radius:6px; border-left:4px solid #94a3b8;'>"
        f"🔒 <b>{archetype}</b> — 该业务类型的完整 4 项行动建议在完整版可见"
        f"</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"<div style='color:#475569; font-size:0.92rem; margin: 4px 0 14px 0; "
        f"padding:10px 14px; background:#f1f5f9; border-radius:6px; border-left:4px solid #3498db;'>"
        f"<b>特征</b>：{pb['desc']}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("**具体行动项：**")
    for i, action in enumerate(pb["actions"], 1):
        st.markdown(f"{i}. {action}")

# 13 archetype 全集概览（5 unlocked + 8 locked）
st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
with st.expander("📋 13 业务类型完整框架（2 公开 / 11 加密 — 展开查看）", expanded=False):
    st.markdown(
        "<div style='color:#6b7280; font-size:0.8rem; margin-bottom:12px;'>"
        "demo 公开 2 个对应当前可选类目的业务类型打法；剩余 11 个仅展示名字 + 策略归属。"
        "</div>",
        unsafe_allow_html=True,
    )
    strategy_color = {
        "Top Pick":   "#27ae60",
        "Crowded":    "#e74c3c",
        "Hidden Gem": "#9b59b6",
        "Watch":      "#93A2D3",
        "Avoid":      "#8d949b",
    }
    for name, strat, desc, unlocked in ALL_ARCHETYPES:
        badge_color = strategy_color.get(strat, "#94a3b8")
        lock_icon = "✅" if unlocked else "🔒"
        lock_color = "#27ae60" if unlocked else "#94a3b8"
        # locked 仅展示名字 + strategy badge（不显示描述）
        desc_html = (
            f"<div style='color:#6b7280; font-size:0.82rem; margin-top:2px;'>{desc}</div>"
            if unlocked else ""
        )
        st.markdown(
            f"<div style='border:1px solid #e6e9ee; border-radius:6px; "
            f"padding:8px 12px; margin: 4px 0; background:#fafbfd;'>"
            f"<span style='color:{lock_color}; font-size:0.9rem;'>{lock_icon}</span>"
            f"&nbsp;<b style='color:#2c3e50;'>{name}</b>"
            f"&nbsp;<span style='display:inline-block; background:{badge_color}; "
            f"color:#fff; font-size:0.72rem; padding:1px 6px; border-radius:3px; margin-left:4px;'>{strat}</span>"
            f"{desc_html}"
            f"</div>",
            unsafe_allow_html=True,
        )

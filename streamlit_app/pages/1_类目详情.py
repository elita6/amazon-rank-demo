# demo/streamlit_app/类目详情.py
# 更新日期：2026-05-12
# 用途：Demo 版类目详情页（数据脱敏 + 5 类目）— streamlit entry
# 启动：streamlit run demo/streamlit_app/类目详情.py
# 与生产版差异：
#   - 数据源从 v1/data/amazon.db 改为 demo/data/*.csv（in-memory sqlite）
#   - 类目缩减为 5（Category A ~ E）— 覆盖 5 种 strategy
#   - 品牌/ASIN 已匿名化，价格/评论数 ±5% 扰动

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "streamlit_app"))
from _styles import inject_global_style, app_header, page_title, chart_title, chart_spacer
from _demo_data import connect_demo, market_heat_index


LIST_LABELS = {
    "all":            "综合（三榜合并）",
    "best_seller":    "BS",
    "new_release":    "NR",
    "movers_shakers": "MS",
}
LIST_OPTIONS_FULL = ["all", "best_seller", "new_release", "movers_shakers"]


@st.cache_data
def load_data():
    conn = connect_demo()
    asin = pd.read_sql(
        "SELECT category, list_type, date, asin, brand, price_low, rate, "
        "review_count, has_video FROM asin_daily",
        conn,
    )
    summary = pd.read_sql(
        "SELECT category, n_subcategories, est_monthly_gmv, "
        "avg_price_median, avg_review_median, is_subcategory "
        "FROM category_summary",
        conn,
    )
    return asin, summary


def filter_by_list(df, list_choice):
    if list_choice == "all":
        return df
    return df[df["list_type"] == list_choice]


def list_suffix(list_choice):
    return f"（{LIST_LABELS[list_choice]}）"


def list_radio(label, key, default="all", options=LIST_OPTIONS_FULL):
    return st.radio(
        label, options=options,
        format_func=lambda k: LIST_LABELS[k],
        index=options.index(default), horizontal=True, key=key,
        label_visibility="collapsed",
    )


# =======================================================================
# 页面
# =======================================================================
st.set_page_config(page_title="类目详情 · Demo", layout="wide", initial_sidebar_state="collapsed")
inject_global_style()
app_header()

# Demo banner
st.markdown(
    "<div style='background:#fff7ed; border-left:4px solid #f59e0b; "
    "padding:8px 14px; margin: 4px 0 10px 0; border-radius:4px; font-size:0.85rem; color:#7c2d12;'>"
    "🎭 <b>Demo Mode</b> — 节选5类目展示，品牌名/ASIN 已匿名化 ， 价格/评论数 ±5% 扰动 。 "
    "</div>",
    unsafe_allow_html=True,
)

page_title("类目详情")

asin, summary = load_data()

# 默认排除子类目
sub_set = set(summary[summary["is_subcategory"] == 1]["category"].tolist())
asin = asin[~asin["category"].isin(sub_set)]
summary = summary[summary["is_subcategory"] != 1].copy()
main_cats = summary["category"].tolist()

# KPI
_n_asin = asin["asin"].nunique()
_n_brand = asin["brand"].dropna().nunique()
_n_days = asin["date"].nunique()
_date_min = str(asin["date"].min())[:10]
_date_max = str(asin["date"].max())[:10]


def _kpi(col, label, value, value_size="1.7rem", value_color="#222", value_weight="400"):
    col.markdown(
        f"<div style='padding:8px 4px;'>"
        f"<div style='font-size:0.85rem; color:#6b7280; font-weight:600; margin-bottom:6px;'>{label}</div>"
        f"<div style='font-size:{value_size}; color:{value_color}; "
        f"font-weight:{value_weight}; line-height:1.2;'>{value}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


_kp1, _kp2, _kp3, _kp4 = st.columns(4)
_kpi(_kp1, "分析类目数",     f"{len(main_cats)}")
_kpi(_kp2, "ASIN 数(去重)",  f"{_n_asin:,}")
_kpi(_kp3, "品牌数(去重)",   f"{_n_brand:,}")
_kpi(_kp4, "数据时间范围",
     f"{_date_min} ~ {_date_max}"
     f"<div style='font-size:0.75rem; color:#9ca3af; margin-top:2px;'>({_n_days} 天)</div>",
     value_size="0.85rem", value_color="#36383b")

# 市场历史价值指数（BS 榜最近 1 天 Top 100，固定口径）
bs_full = asin[asin["list_type"] == "best_seller"]
if not bs_full.empty:
    market_heat = (
        bs_full.groupby("category")
        .apply(lambda g: market_heat_index(g))
        .dropna()
        .round(0)
    )
else:
    market_heat = pd.Series(dtype=float)


# =======================================================================
# 1.1 类目概览
# =======================================================================
with st.container(border=True):
    st.markdown("## 类目概览")

    if "cd_cats_inner" not in st.session_state:
        st.session_state.cd_cats_inner = list(main_cats)
    n_sel = len(st.session_state.cd_cats_inner)
    n_total = len(main_cats)

    def _cd_select_all():
        st.session_state.cd_cats_inner = list(main_cats)

    def _cd_clear_all():
        st.session_state.cd_cats_inner = []

    fc1, fc2 = st.columns([1, 4])
    with fc1:
        st.markdown("<div class='filter-label'>🔍 类目选择</div>", unsafe_allow_html=True)
        with st.popover(f"已选 {n_sel} / {n_total}", use_container_width=False):
            bcol1, bcol2 = st.columns(2)
            bcol1.button("✓ 全选", key="cd_btn_all", on_click=_cd_select_all, use_container_width=True)
            bcol2.button("✗ 全不选", key="cd_btn_none", on_click=_cd_clear_all, use_container_width=True)
            st.multiselect("勾选类目", options=main_cats,
                           key="cd_cats_inner", label_visibility="collapsed")
    with fc2:
        st.markdown("<div class='filter-label' style='visibility:hidden;'>·</div>", unsafe_allow_html=True)
        cd_list = list_radio("榜单", key="cd_list", default="all")
    cd_cats = st.session_state.cd_cats_inner or list(main_cats)

    asin_v = filter_by_list(asin, cd_list)
    asin_v = asin_v[asin_v["category"].isin(cd_cats)]
    summary_v = summary[summary["category"].isin(cd_cats)]
    suffix = list_suffix(cd_list)

    chart_title(f"● 类目汇总{suffix}")

    agg_view = (
        asin_v.groupby("category")
        .agg(
            records=("asin", "size"),
            days=("date", "nunique"),
            unique_asin=("asin", "nunique"),
            unique_brand=("brand", lambda s: s.dropna().nunique()),
            price_median=("price_low", "median"),
            review_median=("review_count", "median"),
            rate_mean=("rate", "mean"),
            has_video_pct=("has_video", "mean"),
        )
        .reset_index()
    )
    if "n_subcategories" in summary_v.columns:
        agg_view = agg_view.merge(
            summary_v[["category", "n_subcategories", "est_monthly_gmv"]],
            on="category", how="left",
        )

    agg_view["market_heat"] = agg_view["category"].map(market_heat)
    agg_view["has_video_pct"] = (agg_view["has_video_pct"] * 100).round(1)
    agg_view["price_median"] = agg_view["price_median"].round(2)
    agg_view["review_median"] = agg_view["review_median"].round(0)
    agg_view["rate_mean"] = agg_view["rate_mean"].round(2)
    agg_view["est_monthly_gmv_M"] = (agg_view["est_monthly_gmv"] / 1e6).round(2)

    ordered_cols = ["category", "records", "days", "unique_asin", "unique_brand",
                    "n_subcategories", "est_monthly_gmv_M", "market_heat",
                    "price_median", "review_median", "rate_mean", "has_video_pct"]
    ordered_cols = [c for c in ordered_cols if c in agg_view.columns]
    display = agg_view[ordered_cols].copy()

    rename_map = {
        "category":           "类目",
        "records":            "记录数",
        "days":               "样本天数",
        "unique_asin":        "唯一ASIN",
        "unique_brand":       "品牌数",
        "n_subcategories":    "子类数",
        "est_monthly_gmv_M":  "预估月销售额($M/月)",
        "market_heat":        "市场历史价值指数",
        "price_median":       "价格中位",
        "review_median":      "评论中位",
        "rate_mean":          "评分均值",
        "has_video_pct":      "有视频%",
    }
    display = display.rename(columns=rename_map)
    sort_col = "市场历史价值指数" if "市场历史价值指数" in display.columns else "唯一ASIN"
    display = display.sort_values(sort_col, ascending=False, na_position="last")

    column_config = {
        "类目":     st.column_config.TextColumn(width="medium"),
        "记录数":   st.column_config.NumberColumn(format="%d"),
        "样本天数": st.column_config.NumberColumn(format="%d"),
        "唯一ASIN": st.column_config.NumberColumn(format="%d"),
        "品牌数":   st.column_config.NumberColumn(format="%d"),
        "子类数":   st.column_config.NumberColumn(format="%d"),
    }
    if "预估月销售额($M/月)" in display.columns:
        m = display["预估月销售额($M/月)"].max()
        column_config["预估月销售额($M/月)"] = st.column_config.ProgressColumn(
            help="评论增量法估算的月化销售额（USD/月）— Σ_ASIN (review_delta ÷ 1.5% × 均价) × 30/天数。仅供类目间相对比较。",
            format="$%.1fM", min_value=0, max_value=float(m) if m else 1,
        )
    if "市场历史价值指数" in display.columns:
        m = display["市场历史价值指数"].max()
        column_config["市场历史价值指数"] = st.column_config.ProgressColumn(
            help="历史评论积累 × 价格的对数加权指数（无量纲）— Σ_top100_latest (log1p(review_count) × price_low)。"
                 "log1p 压平评论长尾；偏老品。与月销售额互补：双高=头部大盘 / 月销高+热度低=新兴上升。",
            format="%d", min_value=0, max_value=float(m) if m else 1,
        )
    if "价格中位" in display.columns:
        m = display["价格中位"].max()
        column_config["价格中位"] = st.column_config.ProgressColumn(
            format="$%.2f", min_value=0, max_value=float(m) if m else 1,
        )
    if "评论中位" in display.columns:
        m = display["评论中位"].max()
        column_config["评论中位"] = st.column_config.ProgressColumn(
            format="%d", min_value=0, max_value=float(m) if m else 1,
        )
    if "评分均值" in display.columns:
        column_config["评分均值"] = st.column_config.ProgressColumn(
            format="%.2f", min_value=0, max_value=5,
        )
    if "有视频%" in display.columns:
        column_config["有视频%"] = st.column_config.ProgressColumn(
            format="%.1f%%", min_value=0, max_value=100,
        )

    st.dataframe(display, hide_index=True, width="stretch",
                 column_config=column_config, height=260)
    st.markdown(
        "<div style='font-size: 0.70rem; color: #6b7280; line-height: 1.65; margin-top: 4px;'>"
        "注：预估月销售额($M/月)、市场历史价值指数均仅基于<b>BS榜</b>口径（不随榜单选择器变化）"
        "</div>",
        unsafe_allow_html=True,
    )


# =======================================================================
# 1.2 类目画像
# =======================================================================
st.markdown("## 类目画像")

# ----- 基础分布 -----
with st.container(border=True):
    st.markdown("**● 基础分布**")

    bd_list = list_radio("榜单", key="bd_list", default="best_seller")
    suffix_bd = list_suffix(bd_list)
    asin_bd = filter_by_list(asin, bd_list)
    asin_bd = asin_bd.dropna(subset=["price_low", "review_count"], how="all")

    if asin_bd.empty:
        st.warning("当前榜单无数据")
    else:
        bd_v = asin_bd.copy()
        bd_v["price_clip"] = bd_v.groupby("category")["price_low"].transform(
            lambda s: s.clip(upper=s.quantile(0.95)))
        bd_v["review_clip"] = bd_v.groupby("category")["review_count"].transform(
            lambda s: s.clip(upper=s.quantile(0.95)))

        chart_title(f"1. 价格分布{suffix_bd}")
        fig = px.box(bd_v.dropna(subset=["price_clip"]),
                     x="category", y="price_clip", height=380,
                     points=False, color="category")
        fig.update_traces(hovertemplate="%{x}<br>%{y:.2f} USD<extra></extra>")
        fig.update_layout(xaxis_tickangle=-30, xaxis_title=None,
                          yaxis_title="价格 (USD)", showlegend=False,
                          yaxis=dict(tickformat=".2f"),
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")

        chart_spacer()

        chart_title(f"2. 评论数分布{suffix_bd}")
        fig = px.box(bd_v.dropna(subset=["review_clip"]),
                     x="category", y="review_clip", height=380,
                     points=False, color="category")
        fig.update_traces(hovertemplate="%{x}<br>%{y:.0f}<extra></extra>")
        fig.update_layout(xaxis_tickangle=-30, xaxis_title=None,
                          yaxis_title="评论数", showlegend=False,
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")


# ----- 交叉分析 -----
with st.container(border=True):
    st.markdown("**● 交叉分析**")
    st.caption("注：基于 BS 榜口径（与页面榜单选择器无关）")

    chart_title("类目象限图（固定BS口径）")
    quad = summary[["category", "est_monthly_gmv", "avg_price_median"]].copy()
    quad["monthly_M"] = (quad["est_monthly_gmv"] / 1e6).round(2)
    quad["heat"] = quad["category"].map(market_heat)
    quad = quad.dropna(subset=["monthly_M", "heat"])

    if not quad.empty:
        fig = px.scatter(
            quad, x="monthly_M", y="heat",
            text="category",
            hover_name="category",
            hover_data={"monthly_M": ":.2f",
                        "heat": ":.0f",
                        "avg_price_median": ":.2f",
                        "category": False},
            height=480,
            labels={"monthly_M": "预估月销售额 ($M/月)",
                    "heat": "市场历史价值指数",
                    "avg_price_median": "价格中位 (USD)"},
        )
        fig.update_traces(
            marker=dict(size=14, color="#a8cfee",
                        line=dict(width=1, color="#5b8fc4"),
                        opacity=0.85),
            textposition="top center",
            textfont=dict(size=11, color="#444"),
        )
        mx = quad["monthly_M"].median()
        my = quad["heat"].median()
        fig.add_vline(x=mx, line_dash="dash", line_color="gray")
        fig.add_hline(y=my, line_dash="dash", line_color="gray")
        x_lo, x_hi = quad["monthly_M"].min(), quad["monthly_M"].max()
        y_lo, y_hi = quad["heat"].min(), quad["heat"].max()
        x_range = [max(0, x_lo - (x_hi - x_lo) * 0.12), x_hi + (x_hi - x_lo) * 0.15]
        y_range = [max(0, y_lo - (y_hi - y_lo) * 0.12), y_hi + (y_hi - y_lo) * 0.18]
        # 4 象限标签
        for x_anchor, x_pos, label, color in [
            (0.99, "right", "<b>头部大盘</b>",   "#c0392b"),
            (0.01, "left",  "<b>稳态成熟</b>",   "#2980b9"),
        ]:
            fig.add_annotation(xref="paper", yref="paper", x=x_anchor, y=1.0, yshift=14,
                               text=label, showarrow=False,
                               font=dict(size=11, color=color),
                               xanchor=x_pos, yanchor="bottom",
                               bgcolor="rgba(0,0,0,0)", borderpad=3)
        for x_anchor, x_pos, label, color in [
            (0.99, "right", "<b>新兴上升 ★</b>", "#27ae60"),
            (0.01, "left",  "<b>冷门小盘</b>",   "#7f8c8d"),
        ]:
            fig.add_annotation(xref="paper", yref="paper", x=x_anchor, y=0.0, yshift=-14,
                               text=label, showarrow=False,
                               font=dict(size=11, color=color),
                               xanchor=x_pos, yanchor="top",
                               bgcolor="rgba(0,0,0,0)", borderpad=3)
        fig.update_layout(
            xaxis=dict(range=x_range),
            yaxis=dict(range=y_range),
            margin=dict(l=10, r=10, t=50, b=50),
        )
        st.plotly_chart(fig, width="stretch")

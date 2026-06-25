# demo/streamlit_app/pages/跨榜联动.py
# 更新日期：2026-06-25
# 用途：Demo 版跨榜联动页（数据脱敏 + 5 类目）— BS/NR/MS 三榜联动，3 按钮切换
# 启动：streamlit run demo/streamlit_app/产品概览.py
# 与生产版差异：
#   - 数据源从 v1/data/amazon.db 改为 demo/data/*.csv（in-memory sqlite，connect_demo）
#   - 类目缩减为 5（Category A ~ E）；品牌/ASIN 已匿名化，价格/评论数 ±5% 扰动
#   - 流转漏斗 / NR·MS→BS 渗透 / MS 爆发强度 逻辑与生产版完全一致
# 主要改动：
#   - 2026-06-03：修复流转漏斗对比表 ImportError —— 改用手写 Blues rgba 色阶替换
#                 Styler.background_gradient(cmap=...)，去除对 matplotlib 的依赖
#                 （Streamlit Cloud requirements.txt 未含 matplotlib）
#   - 2026-06-23：UI 文案中英双语化（包 t()）+ 配合 st.navigation 入口清理 set_page_config/header
#   - 2026-06-25：同步生产版 — MS爆发强度类目排行条图改读法：末尾文字按头部倍数(P90÷中位)分白话档
#                （普涨<3× / 有黑马3–10× / 强爆发>10×），条色改按头部倍数渐变(YlOrRd, cmin/cmax=1/10)；
#                「尾部倍数」统一改称「头部倍数」；下钻漏斗阶段名「曾在源榜出现」→「入口」；
#                P90 KPI help 简化为「仅头部10%高于此值」

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "streamlit_app"))
from _styles import page_title, chart_title, conclusion, chart_spacer
from _i18n import t
from _demo_data import connect_demo


LIST_LABELS_3 = {"best_seller": "BS", "new_release": "NR", "movers_shakers": "MS"}

# 19 大类长名 → 短名（视角 6 上榜耗时象限图散点 label 用，避免重叠；hover 仍显完整名）
CAT_SHORT = {
    "Amazon Devices & Accessories": "Amazon Dev",
    "Appliances": "Appliances",
    "Arts, Crafts & Sewing": "Arts/Crafts",
    "Automotive": "Automotive",
    "Beauty & Personal Care": "Beauty",
    "Camera & Photo Products": "Camera",
    "Cell Phones & Accessories": "Cell Phones",
    "Clothing, Shoes & Jewelry": "Clothing",
    "Computers & Accessories": "Computers",
    "Electronics": "Electronics",
    "Health & Household": "Health",
    "Home & Kitchen": "Home",
    "Kitchen & Dining": "Kitchen",
    "Musical Instruments": "Musical",
    "Office Products": "Office",
    "Patio, Lawn & Garden": "Patio",
    "Pet Supplies": "Pet",
    "Sports & Outdoors": "Sports",
    "Tools & Home Improvement": "Tools",
}


@st.cache_data
def load_data():
    conn = connect_demo()
    asin = pd.read_sql(
        "SELECT category, list_type, date, asin, brand, rank, "
        "sales_rank, previous_sales_rank, pct_chg_sales_rank "
        "FROM asin_daily",
        conn,
    )
    summary = pd.read_sql(
        "SELECT category, is_subcategory FROM category_summary",
        conn,
    )
    conn.close()
    asin["date"] = pd.to_datetime(asin["date"])
    return asin, summary


def category_popover(key_prefix, cats, label=None):
    """同 ASIN 流动性 / 类目详情 popover 风格。"""
    if label is None:
        label = t("类目选择", "Category Filter")
    inner = f"{key_prefix}_cats_inner"
    if inner not in st.session_state:
        st.session_state[inner] = list(cats)
    n_sel, n_tot = len(st.session_state[inner]), len(cats)

    def _all():
        st.session_state[inner] = list(cats)

    def _none():
        st.session_state[inner] = []

    st.markdown(f"<div class='filter-label'>🔍 {label}</div>", unsafe_allow_html=True)
    with st.popover(t(f"已选 {n_sel} / {n_tot}", f"Selected {n_sel} / {n_tot}"),
                    use_container_width=False):
        b1, b2 = st.columns(2)
        b1.button(t("✓ 全选", "✓ Select All"), key=f"{key_prefix}_btn_all",
                  on_click=_all, use_container_width=True)
        b2.button(t("✗ 全不选", "✗ Clear"), key=f"{key_prefix}_btn_none",
                  on_click=_none, use_container_width=True)
        st.multiselect(t("勾选类目", "Select categories"), options=cats,
                       key=inner, label_visibility="collapsed")
    return st.session_state[inner] or list(cats)


def filter_label_spacer():
    st.markdown("<div class='filter-label' style='visibility:hidden;'>·</div>",
                unsafe_allow_html=True)


# =======================================================================
# 页面
# =======================================================================
page_title(t("跨榜联动", "Cross-List Linkage"))

# Demo banner
st.markdown(
    "<div style='background:#fff7ed; border-left:4px solid #f59e0b; "
    "padding:8px 14px; margin: 4px 0 10px 0; border-radius:4px; font-size:0.85rem; color:#7c2d12;'>"
    "🎭 <b>Demo Mode</b> — "
    + t("节选 5 类目展示，品牌名/ASIN 已匿名化，价格/评论数 ±5% 扰动。",
        "Showing 5 sample categories; brand names/ASINs anonymized, "
        "prices/review counts perturbed ±5%.")
    + "</div>",
    unsafe_allow_html=True,
)

asin_all, summary = load_data()

# 默认排除子类目
sub_set = set(summary[summary["is_subcategory"] == 1]["category"].tolist())
asin_all = asin_all[~asin_all["category"].isin(sub_set)]
summary = summary[summary["is_subcategory"] != 1].copy()
main_cats = sorted(asin_all["category"].unique().tolist())


# =======================================================================
# 4 按钮切换
# =======================================================================
S4_VIEWS = {
    "funnel":    t("流转漏斗", "Flow Funnel"),
    "lag_to_bs": t("NR/MS→BS渗透", "BS Penetration"),
    "ms_burst":  t("MS爆发强度", "MS Burst Intensity"),
}
if "s4_view" not in st.session_state:
    st.session_state.s4_view = "funnel"
# 兼容历史 session：旧 key（brand_dyn / penetration / overlap）残留时回退到默认
if st.session_state.s4_view not in S4_VIEWS:
    st.session_state.s4_view = "funnel"

bcols = st.columns([1, 1, 1, 3])
for col, (vk, vlabel) in zip(bcols[:3], S4_VIEWS.items()):
    is_active = (st.session_state.s4_view == vk)
    if col.button(vlabel, key=f"s4_btn_{vk}",
                  type="primary" if is_active else "secondary",
                  use_container_width=True):
        st.session_state.s4_view = vk
        st.rerun()

chart_spacer()
view = st.session_state.s4_view


# =======================================================================
# 视角 1：流转漏斗
# 注：原视角 1「三榜全景」已抽到 other/spare/overlap_view_260508.py 备用
#     （信噪比低 + 进过 BS% 是混淆指标；详见 spare 文件 header）。
# =======================================================================
if view == "funnel":
    with st.container(border=True):

        # 标题 + 源榜单 radio 同行（左标题 / 右 radio）— v3_src 必须先定义供下方计算用
        title_col, src_col = st.columns([3, 1])
        with src_col:
            v3_src = st.radio(
                t("源榜单", "Source list"), options=["new_release", "movers_shakers", "union"],
                format_func=lambda k: {"new_release": "NR",
                                        "movers_shakers": "MS",
                                        "union": "NR ∪ MS"}[k],
                horizontal=True, key="v3_src", label_visibility="collapsed",
            )

        def _funnel_stages(cat_df):
            if v3_src == "new_release":
                entry = set(cat_df[cat_df["list_type"] == "new_release"]["asin"].unique())
            elif v3_src == "movers_shakers":
                entry = set(cat_df[cat_df["list_type"] == "movers_shakers"]["asin"].unique())
            else:
                entry = set(cat_df[cat_df["list_type"].isin(
                    ["new_release", "movers_shakers"])]["asin"].unique())
            bs_df = cat_df[(cat_df["list_type"] == "best_seller")
                           & (cat_df["asin"].isin(entry))]
            return {
                "入口集":  len(entry),
                "进 BS":   bs_df["asin"].nunique(),
                "Top50":   bs_df[bs_df["rank"] <= 50]["asin"].nunique(),
                "Top10":   bs_df[bs_df["rank"] <= 10]["asin"].nunique(),
            }

        funnel_rows = []
        for cat in main_cats:
            r = _funnel_stages(asin_all[asin_all["category"] == cat])
            r["类目"] = cat
            r["入口→BS%"]     = round((r["进 BS"] / r["入口集"] * 100) if r["入口集"] else 0, 2)
            r["BS→Top50%"]    = round((r["Top50"] / r["进 BS"] * 100) if r["进 BS"] else 0, 2)
            r["Top50→Top10%"] = round((r["Top10"] / r["Top50"] * 100) if r["Top50"] else 0, 2)
            funnel_rows.append(r)
        cmp_df = (pd.DataFrame(funnel_rows)
                  [["类目", "入口集", "进 BS", "Top50", "Top10",
                    "入口→BS%", "BS→Top50%", "Top50→Top10%"]]
                  .sort_values("入口→BS%", ascending=False)
                  .reset_index(drop=True))

        src_label = {"new_release": "NR", "movers_shakers": "MS", "union": "NR∪MS"}[v3_src]
        with title_col:
            chart_title(t(f"● 类目对比表（按 入口→BS% 降序，入口={src_label}）",
                          f"● Category comparison (by Entry→BS% desc, entry={src_label})"))

        ret_cols = ["入口→BS%", "BS→Top50%", "Top50→Top10%"]
        ret_labels = {
            "入口→BS%":     t("入口→BS%", "Entry→BS%"),
            "BS→Top50%":    t("BS→Top50%", "BS→Top50%"),
            "Top50→Top10%": t("Top50→Top10%", "Top50→Top10%"),
        }
        ret_max = max(float(cmp_df[ret_cols].max().max() or 0), 10.0)

        # Blues 色阶（手写 rgba，避免依赖 matplotlib —— Streamlit Cloud 未装 matplotlib，
        # 原 .background_gradient(cmap="Blues") 会触发 ImportError）
        def _blue_grad(val, vmax=ret_max):
            if pd.isna(val) or vmax <= 0:
                return ""
            t = min(max(val / vmax, 0.0), 1.0)
            r = int(round(247 - t * (247 - 33)))
            g = int(round(251 - t * (251 - 113)))
            b = int(round(255 - t * (255 - 181)))
            txt = "#ffffff" if t > 0.55 else "#0f2943"
            return f"background-color: rgb({r},{g},{b}); color: {txt};"

        styler = cmp_df.style.map(_blue_grad, subset=ret_cols)
        column_config = {
            "类目":   st.column_config.TextColumn(t("类目", "Category"),
                                                 pinned=True, width="medium"),
            "入口集": st.column_config.NumberColumn(t("入口集", "Entry pool"),
                                                   format="%d", width="small"),
            "进 BS":  st.column_config.NumberColumn(t("进 BS", "Reached BS"),
                                                   format="%d", width="small"),
            "Top50":  st.column_config.NumberColumn("Top50", format="%d", width="small"),
            "Top10":  st.column_config.NumberColumn("Top10", format="%d", width="small"),
        }
        for c in ret_cols:
            column_config[c] = st.column_config.NumberColumn(
                ret_labels[c], format="%.2f%%",
                help=t(f"3 个留存率列共享色阶 max={ret_max:.2f}%（自适应数据峰值）",
                       f"3 retention columns share a color scale max={ret_max:.2f}% "
                       f"(auto-fit to data peak)"),
                width="small",
            )
        st.dataframe(
            styler, hide_index=True, width="stretch",
            height=min(560, 38 + 36 * len(cmp_df)),
            column_config=column_config,
        )

        chart_spacer()
        chart_title(t("● 类目下钻 funnel（选某类目看 4 阶段流转细节）",
                      "● Category drill-down funnel (pick a category to see 4-stage flow detail)"))
        drill_cat = st.selectbox(
            t("下钻类目", "Drill-down category"), options=cmp_df["类目"].tolist(),
            index=0, key="v3_funnel_drill_cat", label_visibility="collapsed",
        )
        drill_r = _funnel_stages(asin_all[asin_all["category"] == drill_cat])
        if drill_r["入口集"] == 0:
            st.warning(t(f"{drill_cat} 当前源榜入口集为空",
                         f"{drill_cat} has an empty entry pool for the current source list"))
        else:
            STAGES = [
                (t("入口", "Entry pool"),  drill_r["入口集"]),
                (t("后来进 BS", "Later reached BS"),     drill_r["进 BS"]),
                (t("进过 BS Top50", "Reached BS Top50"), drill_r["Top50"]),
                (t("进过 BS Top10", "Reached BS Top10"), drill_r["Top10"]),
            ]
            FUNNEL_COLORS = ["#5b8fc4", "#48a4d9", "#27ae60", "#e67e22"]
            fig = go.Figure(go.Funnel(
                y=[s[0] for s in STAGES],
                x=[s[1] for s in STAGES],
                textinfo="value+percent initial",
                marker=dict(color=FUNNEL_COLORS),
            ))
            fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width="stretch")



# =======================================================================
# 视角 3：MS爆发强度
# =======================================================================
elif view == "ms_burst":
    with st.container(border=True):
        st.markdown(t("**● MS爆发强度**", "**● MS Burst Intensity**"))

        df = asin_all[asin_all["list_type"] == "movers_shakers"].copy()
        df = df.dropna(subset=["pct_chg_sales_rank"])

        if df.empty:
            st.warning(t("无 MS 数据", "No MS data"))
        else:
            n_asin = df["asin"].nunique()
            med_pct = df["pct_chg_sales_rank"].median()
            p90_pct = df["pct_chg_sales_rank"].quantile(0.90)
            max_pct = df["pct_chg_sales_rank"].max()

            cs1, cs2, cs3, cs4 = st.columns(4)
            cs1.metric(t("MS 涉及 ASIN 数", "ASINs in MS"), f"{n_asin:,}")
            cs2.metric(t("中位 排名提升率", "Median Rank Gain"), f"{med_pct:,.0f}%",
                       help=t("该量定义：(上次排名 − 当日排名) / 上次排名 × 100%；"
                              "中位 = 典型 ASIN 一天内的排名跳升幅度",
                              "Defined as (previous rank − current rank) / previous rank "
                              "× 100%; median = typical single-day rank jump of an ASIN"))
            cs3.metric(t("P90 排名提升率", "P90 Rank Gain"), f"{p90_pct:,.0f}%",
                       help=t("90 分位 — 仅头部 10% 的 ASIN 提升率高于此值，尾部跳升更猛",
                              "90th percentile — only the top 10% of ASINs gain more than "
                              "this; the tail jumps even harder"))
            cs4.metric(t("单条最大", "Single max"), f"{max_pct:,.0f}%")

            chart_spacer()
            chart_title(t("● 类目 排名提升率排行（中位升序）",
                          "● Category rank-gain ranking (median asc)"))
            st.markdown(
                "<div style='font-size:0.70rem; color:#6b7280; font-weight:400; "
                "margin: -4px 0 8px 4px; line-height:1.3;'>"
                + t("倍数×=P90÷中位，普涨(<3×) / 有黑马(3–10×) / 强爆发(>10×) · 颜色越深=倍数越大",
                    "Ratio× = P90÷median; Broad rise (<3×) / Some breakouts (3–10×) / "
                    "Extreme burst (>10×) · darker = higher ratio")
                + "</div>",
                unsafe_allow_html=True,
            )
            df_pos = df[df["pct_chg_sales_rank"] > 0]
            cat_burst = (df_pos.groupby("category")
                         .agg(median_pct=("pct_chg_sales_rank", "median"),
                              p90_pct=("pct_chg_sales_rank", lambda s: s.quantile(0.90)),
                              n_asin=("asin", "nunique"))
                         .reset_index().sort_values("median_pct", ascending=True))
            cat_burst["ratio"] = (cat_burst["p90_pct"]
                                   / cat_burst["median_pct"].replace(0, np.nan))
            top5_burst = set(cat_burst.tail(5)["category"].tolist())

            # 头部倍数 → 分布形态档（白话），仅作文字标签；条色用倍数渐变（cmin/cmax 对齐档位界）
            BURST_LABEL = {
                "broad":   t("普涨", "Broad rise"),
                "some":    t("有黑马", "Some breakouts"),
                "extreme": t("强爆发", "Extreme burst"),
                "na":      "—",
            }
            def _burst_key(r):
                if pd.isna(r):
                    return "na"
                if r < 3:
                    return "broad"
                if r < 10:
                    return "some"
                return "extreme"
            cat_burst["band_label"] = cat_burst["ratio"].map(_burst_key).map(BURST_LABEL)

            fig1 = go.Figure(go.Bar(
                x=cat_burst["median_pct"], y=cat_burst["category"],
                orientation="h",
                marker=dict(
                    color=cat_burst["ratio"], colorscale="YlOrRd",
                    cmin=1, cmax=10,
                    colorbar=dict(title=t("头部倍数×", "Top ratio×"),
                                  thickness=12, x=1.04, xpad=6),
                    line=dict(color="white", width=0.5),
                ),
                customdata=cat_burst[["p90_pct", "ratio", "n_asin", "band_label"]].values,
                hovertemplate=t("%{y}<br>中位 %{x:,.0f}%"
                                "<br>分布形态：%{customdata[3]}"
                                "<br>P90 %{customdata[0]:,.0f}%"
                                "<br>头部倍数 %{customdata[1]:.1f}× (P90/中位)"
                                "<br>ASIN 数 %{customdata[2]:,.0f}<extra></extra>",
                                "%{y}<br>Median %{x:,.0f}%"
                                "<br>Shape: %{customdata[3]}"
                                "<br>P90 %{customdata[0]:,.0f}%"
                                "<br>Top ratio %{customdata[1]:.1f}× (P90/median)"
                                "<br>ASINs %{customdata[2]:,.0f}<extra></extra>"),
                text=[f"{v:,.0f}% · <b>{lab}</b>"
                      for v, lab in zip(cat_burst["median_pct"], cat_burst["band_label"])],
                textposition="outside",
                cliponaxis=False,
            ))
            fig1.update_layout(
                height=max(360, 26 * len(cat_burst)),
                xaxis_title=t("中位 排名提升率 (%)", "Median rank gain (%)"),
                yaxis_title=None,
                margin=dict(l=10, r=200, t=10, b=10),
            )
            st.plotly_chart(fig1, width="stretch")

            chart_spacer()
            chart_title(t("● 每日中位 排名提升率幅度 by 类目（平滑曲线；Top 5 高亮粗线，其余细线半透明）",
                          "● Daily median rank gain by category (smoothed; Top 5 bold, "
                          "others thin and semi-transparent)"))
            day_cat = (df.groupby(["date", "category"])
                       ["pct_chg_sales_rank"].median()
                       .reset_index().sort_values("date"))
            cat_rank = cat_burst.sort_values("median_pct", ascending=False)
            top5_cats = set(cat_rank.head(5)["category"].tolist())
            # 19 类目各给一种颜色（Dark24 调色板 24 色，绕够用）
            PALETTE = px.colors.qualitative.Dark24
            ordered_cats = cat_rank["category"].tolist()
            cat_color = {c: PALETTE[i % len(PALETTE)] for i, c in enumerate(ordered_cats)}

            fig2 = go.Figure()
            # 先画非 Top 5（细线+半透明，作为底层背景）
            for cat in ordered_cats:
                if cat in top5_cats:
                    continue
                sub = day_cat[day_cat["category"] == cat]
                fig2.add_trace(go.Scatter(
                    x=sub["date"], y=sub["pct_chg_sales_rank"],
                    name=cat, mode="lines",
                    line=dict(color=cat_color[cat], width=1.3,
                              shape="spline", smoothing=0.7),
                    opacity=0.55,
                    showlegend=False,
                    hovertemplate=("<b>" + cat + "</b><br>%{x|%Y-%m-%d}"
                                   + t("<br>中位 排名提升率 %{y:,.0f}%<extra></extra>",
                                       "<br>Median rank gain %{y:,.0f}%<extra></extra>")),
                ))
            # 再画 Top 5（粗线+markers，覆盖在上层）
            for cat in cat_rank.head(5)["category"]:
                sub = day_cat[day_cat["category"] == cat]
                fig2.add_trace(go.Scatter(
                    x=sub["date"], y=sub["pct_chg_sales_rank"],
                    name=cat, mode="lines+markers",
                    line=dict(color=cat_color[cat], width=2.8,
                              shape="spline", smoothing=0.7),
                    marker=dict(size=7),
                    hovertemplate=("<b>" + cat + "</b><br>%{x|%Y-%m-%d}"
                                   + t("<br>中位 排名提升率 %{y:,.0f}%<extra></extra>",
                                       "<br>Median rank gain %{y:,.0f}%<extra></extra>")),
                ))
            fig2.update_layout(
                height=480, margin=dict(l=10, r=10, t=10, b=80),
                xaxis_title=t("日期", "Date"),
                yaxis_title=t("中位 排名提升率 (%)", "Median rank gain (%)"),
                legend=dict(orientation="h", y=-0.20, x=0.5,
                            xanchor="center", yanchor="top"),
            )
            st.plotly_chart(fig2, width="stretch")

            chart_spacer()
            chart_title(t("● Top 20 爆发 ASIN（按单条最大 pct_chg 排序）",
                          "● Top 20 burst ASINs (by single-event max pct_chg)"))
            top_evt = (df.sort_values("pct_chg_sales_rank", ascending=False)
                       .drop_duplicates("asin").head(20).copy())
            bs_asins = set(asin_all[asin_all["list_type"] == "best_seller"]["asin"].unique())
            top_evt["进过BS"] = top_evt["asin"].apply(
                lambda a: "✓" if a in bs_asins else "—")
            show_evt = pd.DataFrame({
                "ASIN":     top_evt["asin"],
                t("品牌", "Brand"):     top_evt["brand"].fillna("—"),
                t("类目", "Category"):     top_evt["category"],
                t("事件日期", "Event date"): pd.to_datetime(top_evt["date"]).dt.strftime("%Y-%m-%d"),
                t("上次排名", "Previous rank"): top_evt["previous_sales_rank"].apply(
                    lambda v: f"{int(v):,}" if pd.notna(v) else "—"),
                t("当日排名", "Current rank"): top_evt["sales_rank"].apply(
                    lambda v: f"{int(v):,}" if pd.notna(v) else "—"),
                t("排名提升率", "Rank gain"): top_evt["pct_chg_sales_rank"].apply(lambda v: f"{v:,.0f}%"),
                t("进过 BS", "Reached BS"): top_evt["进过BS"],
            })
            st.dataframe(show_evt, hide_index=True, width="stretch",
                         height=min(560, 38 + 36 * len(show_evt)))



# =======================================================================
# 视角 2：NR/MS→BS 渗透情况（迁移自原 3_ASIN流动性.py 视角 1）
#         （原视角 5「品牌动态」已抽到 other/spare/brand_dyn_view_260508.py）
# =======================================================================
elif view == "lag_to_bs":
    with st.container(border=True):

        # ---- BS ASIN 全集（两源共享） ----
        bs_first = (asin_all[asin_all["list_type"] == "best_seller"]
                    .groupby(["asin", "category"])["date"].min()
                    .reset_index().rename(columns={"date": "d_bs"}))
        bs_count_s = bs_first.groupby("category").size()

        def _compute_valid(src):
            src_first = (asin_all[asin_all["list_type"] == src]
                         .groupby("asin")["date"].min()
                         .reset_index().rename(columns={"date": "d_src"}))
            j = bs_first.merge(src_first, on="asin", how="inner")
            j["lag_days"] = (j["d_bs"] - j["d_src"]).dt.days
            return j[j["lag_days"] >= 0]

        valid_nr = _compute_valid("new_release")
        valid_ms = _compute_valid("movers_shakers")

        # ============================================================
        # 类目对比图（柱形=渗透率；NR=深蓝 / MS=浅蓝；双源同图）
        # ============================================================
        chart_title(
            t("● 类目渗透率对比", "● Category penetration comparison")
        )

        rows = []
        for cat in main_cats:
            n_bs = int(bs_count_s.get(cat, 0))
            nr_sub = valid_nr[valid_nr["category"] == cat]
            ms_sub = valid_ms[valid_ms["category"] == cat]
            rows.append({
                "类目":      cat,
                "nr_median": float(nr_sub["lag_days"].median()) if len(nr_sub) else None,
                "ms_median": float(ms_sub["lag_days"].median()) if len(ms_sub) else None,
                "nr_rate":   round(len(nr_sub) / n_bs * 100, 1) if n_bs else 0.0,
                "ms_rate":   round(len(ms_sub) / n_bs * 100, 1) if n_bs else 0.0,
            })
        cmp_all = (pd.DataFrame(rows)
                   .sort_values("nr_rate", ascending=False, na_position="last")
                   .reset_index(drop=True))

        COLOR_NR = "#1f4e79"
        COLOR_MS = "#a8cfee"
        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Bar(
            x=cmp_all["类目"], y=cmp_all["nr_rate"],
            name=t("NR→BS 渗透率", "NR→BS penetration"), marker_color=COLOR_NR,
            hovertemplate=t("<b>%{x}</b><br>NR→BS 渗透率 %{y:.1f}%<extra></extra>",
                            "<b>%{x}</b><br>NR→BS penetration %{y:.1f}%<extra></extra>"),
        ))
        fig_cmp.add_trace(go.Bar(
            x=cmp_all["类目"], y=cmp_all["ms_rate"],
            name=t("MS→BS 渗透率", "MS→BS penetration"), marker_color=COLOR_MS,
            hovertemplate=t("<b>%{x}</b><br>MS→BS 渗透率 %{y:.1f}%<extra></extra>",
                            "<b>%{x}</b><br>MS→BS penetration %{y:.1f}%<extra></extra>"),
        ))
        fig_cmp.update_layout(
            barmode="group",
            height=520,
            xaxis=dict(tickangle=-30, title=None),
            yaxis=dict(title=t("渗透率（%）", "Penetration (%)"), ticksuffix="%"),
            margin=dict(l=10, r=10, t=20, b=130),
            legend=dict(orientation="h", y=-0.32, x=0.5,
                        xanchor="center", yanchor="top"),
        )
        st.plotly_chart(fig_cmp, width="stretch")

        chart_spacer()

        # ============================================================
        # 耗时分布 box plot（双源同图：NR / MS 并列；类目顺序与双源对比图一致）
        # ============================================================
        chart_title(
            t("● 类目上榜BS中位耗时分布",
              "● Distribution of median days-to-BS by category")
        )
        if valid_nr.empty and valid_ms.empty:
            st.warning(t("两源均无重叠 ASIN", "No overlapping ASINs in either source"))
        else:
            box_df = pd.concat([
                valid_nr.assign(src="NR→BS"),
                valid_ms.assign(src="MS→BS"),
            ], ignore_index=True)
            box_order = (cmp_all.sort_values("nr_median", na_position="last")
                         ["类目"].tolist())
            fig_box = px.box(
                box_df, x="category", y="lag_days", color="src",
                color_discrete_map={"NR→BS": COLOR_NR, "MS→BS": COLOR_MS},
                category_orders={"category": box_order,
                                 "src": ["NR→BS", "MS→BS"]},
                height=480,
                labels={"category": "", "lag_days": t("耗时（天）", "Days"),
                        "src": t("源", "Source")},
            )
            fig_box.update_layout(
                boxmode="group",
                margin=dict(l=10, r=10, t=10, b=120),
                xaxis=dict(tickangle=-30),
                legend=dict(orientation="h", y=-0.30, x=0.5,
                            xanchor="center", yanchor="top"),
            )
            st.plotly_chart(fig_box, width="stretch")

        chart_spacer()

        # ============================================================
        # 类目散点图（左 NR→BS / 右 MS→BS；不分象限，靠轴向方向直觉表达）
        # ============================================================
        chart_title(t("● 类目跨榜渗透率X中位耗时交叉图",
                      "● Category cross plot: cross-list penetration × median days-to-BS"))

        def _draw_quad(median_col, rate_col, color, src_label):
            quad = (cmp_all[["类目", median_col, rate_col]]
                    .rename(columns={median_col: "中位耗时(天)",
                                     rate_col: "渗透率"})
                    .dropna(subset=["中位耗时(天)"]))
            quad = quad[quad["渗透率"] > 0].reset_index(drop=True)
            zero_cats = [c for c in cmp_all["类目"]
                         if c not in quad["类目"].tolist()]
            if quad.empty:
                st.warning(t(f"{src_label} 无渗透 ASIN",
                             f"{src_label} has no penetrating ASINs"))
                return
            quad["类目短名"] = quad["类目"].map(CAT_SHORT).fillna(quad["类目"])
            x_min = float(quad["中位耗时(天)"].min())
            x_max = float(quad["中位耗时(天)"].max())
            x_pad = max((x_max - x_min) * 0.15, 0.8)
            y_max = float(quad["渗透率"].max())

            rng = np.random.RandomState(42)
            x_jit = max((x_max - x_min) * 0.025, 0.18)
            y_jit = max(y_max * 0.018, 0.20)
            quad["_x"] = quad["中位耗时(天)"] + rng.uniform(-x_jit, x_jit, len(quad))
            quad["_y"] = quad["渗透率"] + rng.uniform(-y_jit, y_jit, len(quad))
            # 默认按 cycle 分布 4 方位；对已知重叠类目按源单独 override
            default_pos = ["top center", "bottom center", "middle right", "middle left"]
            if src_label == "NR→BS":
                overrides = {
                    "Clothing, Shoes & Jewelry": "top center",
                    "Tools & Home Improvement": "bottom center",
                }
            elif src_label == "MS→BS":
                overrides = {
                    "Cell Phones & Accessories":  "top center",
                    "Home & Kitchen":             "middle left",
                    "Arts, Crafts & Sewing":      "bottom center",
                    "Clothing, Shoes & Jewelry":  "top right",
                    "Health & Household":         "bottom right",
                }
            else:
                overrides = {}
            text_positions = [
                overrides.get(cat, default_pos[i % 4])
                for i, cat in enumerate(quad["类目"])
            ]

            fig = px.scatter(
                quad, x="_x", y="_y", text="类目短名",
                custom_data=["类目", "中位耗时(天)", "渗透率"],
                height=480,
            )
            fig.update_xaxes(title_text=t("中位耗时（天）", "Median days-to-BS"),
                             showline=False, ticks="outside", ticklen=5,
                             showticklabels=True,
                             showgrid=False, zeroline=False)
            fig.update_yaxes(title_text=t("渗透率（%）", "Penetration (%)"),
                             showline=False, ticks="outside", ticklen=5,
                             showticklabels=True, ticksuffix="%",
                             showgrid=False, zeroline=False)
            fig.update_traces(
                textposition=text_positions,
                textfont=dict(size=11),
                marker=dict(size=10, color=color,
                            line=dict(width=1, color="white")),
                hovertemplate=t(
                    "<b>%{customdata[0]}</b><br>"
                    "中位耗时: %{customdata[1]:.1f} 天<br>"
                    "渗透率: %{customdata[2]:.1f}%<extra></extra>",
                    "<b>%{customdata[0]}</b><br>"
                    "Median days-to-BS: %{customdata[1]:.1f}<br>"
                    "Penetration: %{customdata[2]:.1f}%<extra></extra>"
                ),
            )
            # X 轴：底部水平箭头（向右）— axref/ayref 不接受 'paper'，用 'x domain'/'y domain'
            fig.add_annotation(
                xref="x domain", yref="y domain",
                x=1.0, y=0, ax=0, ay=0,
                axref="x domain", ayref="y domain",
                showarrow=True, arrowhead=2, arrowsize=1.4,
                arrowwidth=1.6, arrowcolor="#888",
            )
            # Y 轴：左侧垂直箭头（向上）
            fig.add_annotation(
                xref="x domain", yref="y domain",
                x=0, y=1.0, ax=0, ay=0,
                axref="x domain", ayref="y domain",
                showarrow=True, arrowhead=2, arrowsize=1.4,
                arrowwidth=1.6, arrowcolor="#888",
            )
            # 快 / 慢 标签（红色）— X 轴方向，沿底部水平排列在同一 y 上
            fig.add_annotation(xref="x domain", yref="y domain",
                               x=0.04, y=0.01, text=t("快", "Fast"), showarrow=False,
                               font=dict(size=12, color="#c0392b"),
                               xanchor="left", yanchor="bottom")
            fig.add_annotation(xref="x domain", yref="y domain",
                               x=0.99, y=0.01, text=t("慢", "Slow"), showarrow=False,
                               font=dict(size=12, color="#c0392b"),
                               xanchor="right", yanchor="bottom")
            # 难 / 易 标签（绿色）— Y 轴方向，沿左侧竖直排列在同一 x 上
            fig.add_annotation(xref="x domain", yref="y domain",
                               x=0.01, y=0.05, text=t("难", "Hard"), showarrow=False,
                               font=dict(size=12, color="#27ae60"),
                               xanchor="left", yanchor="bottom")
            fig.add_annotation(xref="x domain", yref="y domain",
                               x=0.01, y=0.99, text=t("易", "Easy"), showarrow=False,
                               font=dict(size=12, color="#27ae60"),
                               xanchor="left", yanchor="top")
            fig.update_layout(
                margin=dict(l=50, r=20, t=40, b=50),
                title=dict(text=f"<b>{src_label}</b>", x=0.5, xanchor="center",
                           font=dict(size=13)),
                xaxis=dict(range=[x_min - x_pad - x_jit,
                                  x_max + x_pad + x_jit]),
                yaxis=dict(range=[-y_max * 0.18, y_max * 1.30]),
            )
            st.plotly_chart(fig, width="stretch")
            if zero_cats:
                st.caption(t(f"无渗透类目（不进图）：{'、'.join(zero_cats)}",
                             f"Categories with no penetration (excluded): {', '.join(zero_cats)}"))

        col_l, col_r = st.columns(2)
        with col_l:
            _draw_quad("nr_median", "nr_rate", COLOR_NR, "NR→BS")
        with col_r:
            _draw_quad("ms_median", "ms_rate", COLOR_MS, "MS→BS")



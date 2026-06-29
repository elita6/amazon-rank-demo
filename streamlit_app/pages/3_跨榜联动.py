# streamlit_app/pages/3_跨榜联动.py
# 更新日期：2026-06-29
# 用途：BS / NR / MS 三榜联动分析（Demo 版，对齐生产 v2）。
#       两视角：① ASIN流动性（类目黏性 & 新品活跃表，含 BS 在榜率/满榜率/新增比例、
#       NR 流动率/→BS渗透、MS →BS渗透）；② MS爆发强度（排名提升率排行 + 每日曲线 + Top20）。
# 启动命令：streamlit run streamlit_app/产品概览.py
# 与生产 v2 差异：数据源 data/amazon.db → data/*.csv（connect_demo）；类目/品牌已匿名化。
# 主要改动：
#   - 2026-06-29（同步生产 v2 文案）：BS 在榜率注解后半句「越高说明典型 ASIN 几乎天天在榜、
#       榜单越固化」→「越高说明头部产品生命周期越长」（中英同步，口径不动）。
#   - 2026-06-28：从生产 v2 pages/2_跨榜联动.py 移植——独立「ASIN流动性」页删除，其
#       类目黏性表并入本页并扩列（在榜率/满榜率口径走 _aggregate；渗透率 nr_to_bs_penetration）。

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "streamlit_app"))
from _styles import page_title, chart_title, conclusion, chart_spacer, insight_box
from _i18n import t
from _aggregate import (winsor_mean, nr_to_bs_penetration, ms_burst_winsor,
                        on_list_occupancy, bs_new_asin_ratio, fmt_compact)
from _demo_data import connect_demo

LIST_LABELS_3 = {"best_seller": "BS", "new_release": "NR", "movers_shakers": "MS"}

# 19 大类长名 → 短名（散点 label 用，避免重叠；hover 仍显完整名）
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
    asin["date"] = pd.to_datetime(asin["date"])
    return asin, summary


def category_popover(key_prefix, cats, label=None):
    """同 类目详情 popover 风格。"""
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

asin_all, summary = load_data()

# 默认排除子类目
sub_set = set(summary[summary["is_subcategory"] == 1]["category"].tolist())
asin_all = asin_all[~asin_all["category"].isin(sub_set)]
summary = summary[summary["is_subcategory"] != 1].copy()
main_cats = sorted(asin_all["category"].unique().tolist())


# =======================================================================
# 2 按钮切换
# =======================================================================
S4_VIEWS = {
    "liquidity": t("ASIN流动性", "ASIN Liquidity"),
    "ms_burst":  t("MS爆发强度", "MS Burst Intensity"),
}
if "s4_view" not in st.session_state:
    st.session_state.s4_view = "liquidity"
# 兼容历史 session：旧 key 残留时回退到默认
if st.session_state.s4_view not in S4_VIEWS:
    st.session_state.s4_view = "liquidity"

bcols = st.columns([1, 1, 4])
for col, (vk, vlabel) in zip(bcols[:2], S4_VIEWS.items()):
    is_active = (st.session_state.s4_view == vk)
    if col.button(vlabel, key=f"s4_btn_{vk}",
                  type="primary" if is_active else "secondary",
                  use_container_width=True):
        st.session_state.s4_view = vk
        st.rerun()

chart_spacer()
view = st.session_state.s4_view


# =======================================================================
# 视角：MS爆发强度
# =======================================================================
if view == "ms_burst":
    with st.container(border=True):
        st.markdown(t("**● MS爆发强度**", "**● MS Burst Intensity**"))

        df = asin_all[asin_all["list_type"] == "movers_shakers"].copy()
        df = df.dropna(subset=["pct_chg_sales_rank"])

        if df.empty:
            st.warning(t("无 MS 数据", "No MS data"))
        else:
            n_asin = df["asin"].nunique()
            wm_pct = winsor_mean(df["pct_chg_sales_rank"])
            p90_pct = df["pct_chg_sales_rank"].quantile(0.90)
            max_pct = df["pct_chg_sales_rank"].max()

            cs1, cs2, cs3 = st.columns(3)
            cs1.metric(t("MS 涉及 ASIN 数", "ASINs in MS"), f"{n_asin:,}")
            cs2.metric(t("排名平均提升率", "Avg Rank Gain"), f"{wm_pct:,.0f}%",
                       help=t("(上次排名 − 当日排名) / 上次排名 × 100%",
                              "(previous rank − current rank) / previous rank × 100%"))
            cs3.metric(t("单条最大", "Single max"), f"{max_pct:,.0f}%")

            chart_spacer()
            chart_title(t("● 类目排名平均提升率排行",
                          "● Category avg rank-gain ranking"))
            df_pos = df[df["pct_chg_sales_rank"] > 0]
            # 排名平均提升率走共享函数 ms_burst_winsor（= winsor_mean(pct>0)），
            # 与评分引擎 momentum「MS排名平均提升率」同一份口径（展示=评分）。
            cat_burst = (df_pos.groupby("category")
                         .apply(lambda g: pd.Series({
                             "wmean_pct": ms_burst_winsor(g),
                             "p90_pct": g["pct_chg_sales_rank"].quantile(0.90),
                             "n_asin": g["asin"].nunique()}))
                         .reset_index().sort_values("wmean_pct", ascending=True))

            fig1 = go.Figure(go.Bar(
                x=cat_burst["wmean_pct"], y=cat_burst["category"],
                orientation="h",
                marker=dict(
                    color=cat_burst["wmean_pct"], colorscale="YlOrRd",
                    showscale=False,
                    line=dict(color="white", width=0.5),
                ),
                customdata=cat_burst[["p90_pct", "n_asin"]].values,
                hovertemplate=t("%{y}<br>平均提升率 %{x:,.0f}%"
                                "<br>P90 %{customdata[0]:,.0f}%"
                                "<br>ASIN 数 %{customdata[1]:,.0f}<extra></extra>",
                                "%{y}<br>Avg rank gain %{x:,.0f}%"
                                "<br>P90 %{customdata[0]:,.0f}%"
                                "<br>ASINs %{customdata[1]:,.0f}<extra></extra>"),
                text=[f"{v:,.0f}%" for v in cat_burst["wmean_pct"]],
                textposition="outside",
                cliponaxis=False,
            ))
            fig1.update_layout(
                height=max(360, 26 * len(cat_burst)),
                xaxis_title=None,
                yaxis_title=None,
                margin=dict(l=10, r=60, t=10, b=10),
            )
            st.plotly_chart(fig1, width="stretch")

            # 解读：cat_burst 即条图数据（wmean_pct=平均提升率, p90_pct, n_asin）。
            _cb = cat_burst.sort_values("wmean_pct", ascending=False).reset_index(drop=True)
            _nc = len(_cb)
            _hi, _lo = _cb.iloc[0], _cb.iloc[-1]
            _top3 = "、".join(f"<b>{r['category']}</b> {r['wmean_pct']:,.0f}%" for _, r in _cb.head(3).iterrows())
            _cb2 = _cb[_cb["wmean_pct"] > 0].copy()
            _items_b1 = [
                t(f"MS <b>排名平均提升率</b>最高的几个类目：{_top3}；最低的 <b>{_lo['category']}</b> 只 {_lo['wmean_pct']:,.0f}%。",
                  f"Highest MS <b>avg rank gain</b>: {_top3}; the lowest, <b>{_lo['category']}</b>, just {_lo['wmean_pct']:,.0f}%."),
                t(f"多数类目排名平均提升率落在 {_cb['wmean_pct'].quantile(0.25):,.0f}%–{_cb['wmean_pct'].quantile(0.75):,.0f}% 之间。",
                  f"Most categories' avg rank gain falls between {_cb['wmean_pct'].quantile(0.25):,.0f}% and {_cb['wmean_pct'].quantile(0.75):,.0f}%."),
            ]
            if not _cb2.empty:
                _cb2["_g"] = _cb2["p90_pct"] / _cb2["wmean_pct"]
                _g = _cb2.loc[_cb2["_g"].idxmax()]
                _items_b1.append(
                    t(f"<b>{_g['category']}</b> 少数爆款的提升率（前 10% 高位 {_g['p90_pct']:,.0f}%）是其平均（{_g['wmean_pct']:,.0f}%）的 {_g['_g']:.0f} 倍——爆发集中在个别单品。",
                      f"In <b>{_g['category']}</b> the top-10% products' gain ({_g['p90_pct']:,.0f}%) is {_g['_g']:.0f}× its average ({_g['wmean_pct']:,.0f}%)—bursts concentrate in a few items."))
            insight_box(_items_b1)

            chart_spacer()
            chart_title(t("● 每日排名平均提升率 by 类目",
                          "● Daily avg rank gain by category"))
            day_cat = (df.groupby(["date", "category"])
                       ["pct_chg_sales_rank"].apply(winsor_mean)
                       .reset_index().sort_values("date"))
            cat_rank = cat_burst.sort_values("wmean_pct", ascending=False)
            top5_cats = set(cat_rank.head(5)["category"].tolist())
            # 各类目各给一种颜色（Dark24 调色板 24 色，绕够用）
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
                                   + t("<br>去极值均值 排名提升率 %{y:,.0f}%<extra></extra>",
                                       "<br>Winsor. mean rank gain %{y:,.0f}%<extra></extra>")),
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
                                   + t("<br>去极值均值 排名提升率 %{y:,.0f}%<extra></extra>",
                                       "<br>Winsor. mean rank gain %{y:,.0f}%<extra></extra>")),
                ))
            fig2.update_layout(
                height=480, margin=dict(l=10, r=10, t=10, b=80),
                xaxis_title=t("日期", "Date"),
                yaxis_title=t("排名平均提升率 (%)", "Avg rank gain (%)"),
                legend=dict(orientation="h", y=-0.20, x=0.5,
                            xanchor="center", yanchor="top"),
            )
            st.plotly_chart(fig2, width="stretch")

            # 解读：day_cat 即每日每类目曲线数据。
            if not day_cat.empty:
                _pk = day_cat.loc[day_cat["pct_chg_sales_rank"].idxmax()]
                _items_b2 = [
                    t(f"图上最高点是 {pd.to_datetime(_pk['date']):%m-%d} 的 <b>{_pk['category']}</b>，当天排名平均提升率冲到 {_pk['pct_chg_sales_rank']:,.0f}%。",
                      f"The chart's peak point is <b>{_pk['category']}</b> on {pd.to_datetime(_pk['date']):%m-%d}, with avg rank gain spiking to {_pk['pct_chg_sales_rank']:,.0f}%."),
                ]
                # 每个 Top5 类目自己的单日高点落在哪天；看是否扎堆在同一天
                _top5 = cat_rank.head(5)["category"].tolist()
                _pk_days = []
                for _c in _top5:
                    _s = day_cat[day_cat["category"] == _c]
                    if not _s.empty:
                        _pk_days.append(_s.loc[_s["pct_chg_sales_rank"].idxmax(), "date"])
                if len(_pk_days) >= 3:
                    _vc = pd.Series(_pk_days).value_counts()
                    _mode_n, _mode_day = int(_vc.iloc[0]), pd.to_datetime(_vc.index[0])
                    if _mode_n >= 3:
                        _items_b2.append(t(
                            f"5 个高爆发类目里有 {_mode_n} 个的单日最高点都落在 {_mode_day:%m-%d}——更像全市场同步的爆发事件（如大促）。",
                            f"{_mode_n} of the 5 hottest categories peak on the same day, {_mode_day:%m-%d}—looks like a market-wide burst event (e.g., a sale)."))
                    else:
                        _items_b2.append(t(
                            f"5 个高爆发类目各自的单日最高点分散在不同日子——更像各类目内部的爆发，而非全市场同步。",
                            f"The 5 hottest categories peak on different days—looks like category-specific bursts rather than a market-wide event."))
                insight_box(_items_b2)

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

            # 解读：top_evt 即 Top20 表数据；首条挂 ASIN 直链（单品级极值）
            _e1 = top_evt.iloc[0]
            _nbs = int((top_evt["进过BS"] == "✓").sum())
            _ntop = len(top_evt)
            _ccat = top_evt["category"].value_counts()
            _cc_top = "、".join(f"<b>{c}</b> {int(v)} 个" for c, v in _ccat.head(3).items() if v > 1) or f"<b>{_ccat.index[0]}</b> {int(_ccat.iloc[0])} 个"
            _prev = f"#{int(_e1['previous_sales_rank']):,}" if pd.notna(_e1['previous_sales_rank']) else "—"
            _cur = f"#{int(_e1['sales_rank']):,}" if pd.notna(_e1['sales_rank']) else "—"
            _lk = f"https://www.amazon.com/dp/{_e1['asin']}"
            insight_box([
                t(f"最猛单品销售排名从 {_prev} 跳到 {_cur}（提升 {_e1['pct_chg_sales_rank']:,.0f}%），属 <b>{_e1['category']}</b>（<a href='{_lk}' target='_blank'>查看商品</a>）。",
                  f"The hottest item jumped in sales rank from {_prev} to {_cur} (+{_e1['pct_chg_sales_rank']:,.0f}%), in <b>{_e1['category']}</b> (<a href='{_lk}' target='_blank'>view product</a>)."),
                t(f"这 {_ntop} 个爆发单品里只有 {_nbs} 个进过 BS 榜——短期排名暴涨并不等于能挤进 BS 头部。",
                  f"Of these {_ntop} burst items only {_nbs} ever reached BS—a short-term rank spike doesn't mean breaking into the BS head."),
                t(f"爆发单品最多的类目：{_cc_top}——这 {_ntop} 个里有 {int(_ccat.head(3).sum())} 个来自它们。",
                  f"Categories with the most burst items: {_cc_top}—{int(_ccat.head(3).sum())} of the {_ntop} come from them."),
            ])



# =======================================================================
# 视角：ASIN 流动性（迁移自原独立 ASIN流动性页 类目黏性表）
#   BS：在榜率 + 满榜率（黏性）+ 新增ASIN比例（开放度补充参考）
#   NR：流动率（新品活跃）+ →BS渗透率
#   MS：→BS渗透率
#   on_list_occupancy / nr_to_bs_penetration / bs_new_asin_ratio 均走 _aggregate 共享函数。
# =======================================================================
elif view == "liquidity":
    with st.container(border=True):

        bs_all = asin_all[asin_all["list_type"] == "best_seller"]
        nr_all = asin_all[asin_all["list_type"] == "new_release"]

        def _full_rate(sub):
            """满榜率 = 在该类目实际采集天数里一直在榜的 ASIN 占比。"""
            if sub.empty:
                return None
            cat_days = sub["date"].nunique()
            life = sub.groupby("asin")["date"].nunique()
            if life.size == 0:
                return None
            return float((life == cat_days).sum()) / life.size * 100.0

        def _flow_rate(sub):
            """流动率 = 每日平均换手率 (新增+流失)/2/在榜数。"""
            if sub.empty:
                return None
            ds = sub.groupby("date")["asin"].apply(set).sort_index()
            prev, rates = None, []
            for d in ds.index:
                cur = ds[d]
                hc = len(cur)
                if prev is None:
                    prev = cur
                    continue
                rates.append((len(cur - prev) + len(prev - cur)) / 2 / hc * 100 if hc else 0.0)
                prev = cur
            return (sum(rates) / len(rates)) if rates else None

        rows_data = []
        for cat in main_cats:
            cat_df = asin_all[asin_all["category"] == cat]
            bs_c = bs_all[bs_all["category"] == cat]
            nr_c = nr_all[nr_all["category"] == cat]

            def _nz(v):   # None → np.nan，保证列为 float 可排序/格式化
                return np.nan if v is None else v
            rows_data.append([
                cat,
                _nz(on_list_occupancy(bs_c)),                        # BS 在榜率（评分用）
                _nz(_full_rate(bs_c)),                               # BS 满榜率（评分用）
                _nz(bs_new_asin_ratio(bs_c)),                        # BS 新增ASIN比例（开放度补充参考）
                _nz(_flow_rate(nr_c)),                               # NR 流动率（新品活跃）
                _nz(nr_to_bs_penetration(cat_df, "new_release")),    # NR→BS 渗透率
                _nz(nr_to_bs_penetration(cat_df, "movers_shakers")), # MS→BS 渗透率
            ])

        columns = pd.MultiIndex.from_tuples([
            ("", "类目"),
            ("BS", "在榜率"), ("BS", "满榜率"), ("BS", "新增比例"),
            ("NR", "流动率"), ("NR", "→BS渗透"),
            ("MS", "→BS渗透"),
        ])
        show = pd.DataFrame(rows_data, columns=columns)
        show = show.sort_values(("BS", "在榜率"),
                                ascending=False, na_position="last").reset_index(drop=True)

        # 各指标数据条比例尺：百分制(在榜/满榜/新增)直接 0–100；流动率/渗透率按自身峰值放大（渗透极小，
        # 不放大会看不出差异）。NR 与 MS 的「→BS渗透」共用同一峰值 → 两列可直接比。
        def _col_max(metric):
            vals = pd.concat([show[c].dropna() for c in show.columns if c[1] == metric],
                             ignore_index=True)
            return float(vals.max()) if not vals.empty else 0.0
        flow_max_pct = max(_col_max("流动率") * 1.1, 10.0)
        pen_max_pct = max(_col_max("→BS渗透") * 1.1, 1.0)

        chart_title(t(
            "● 类目ASIN流动性(按 BS 在榜率降序)",
            "● Category ASIN liquidity (by BS on-list desc)"))

        BORDER = "2px solid #aaa"
        SCALE = {"在榜率": 100.0, "满榜率": 100.0, "新增比例": 100.0,
                 "流动率": flow_max_pct, "→BS渗透": pen_max_pct}
        BAR_GRADIENTS = {
            "在榜率":   ("#cfe1f3", "#5b8fc4"),   # 浅蓝 → 深蓝
            "满榜率":   ("#cfeedc", "#27ae60"),   # 浅绿 → 深绿
            "新增比例": ("#e8dcf5", "#8e6bbf"),   # 浅紫 → 深紫
            "流动率":   ("#fbe1c4", "#e67e22"),   # 浅橙 → 深橙
            "→BS渗透":  ("#f8d2d2", "#c0392b"),   # 浅红 → 深红
        }
        METRIC_LABELS = {
            "在榜率":   t("在榜率", "On-list %"),
            "满榜率":   t("满榜率", "Full-list %"),
            "新增比例": t("新增比例", "New-ASIN %"),
            "流动率":   t("流动率", "Turnover %"),
            "→BS渗透":  t("→BS渗透率", "→BS pen."),
        }
        GROUPS = [
            ("BS", ["在榜率", "满榜率", "新增比例"]),
            ("NR", ["流动率", "→BS渗透"]),
            ("MS", ["→BS渗透"]),
        ]

        def _cell_html(val, metric, first_in_group):
            cls_extra = " group-start" if first_in_group else ""
            if pd.isna(val):
                return f'<td class="empty-cell{cls_extra}">—</td>'
            scale = SCALE[metric]
            pct = min(val / scale * 100, 100) if scale > 0 else 0
            light, dark = BAR_GRADIENTS[metric]
            bg = (f"background: linear-gradient(90deg, {dark} 0%, {light} {pct:.2f}%, "
                  f"transparent {pct:.2f}%);")
            return f'<td class="bar-cell{cls_extra}" style="{bg}">{val:.1f}%</td>'

        parts = ['<table class="lifespan-cmp">', "<thead>", "<tr>"]
        parts.append(
            '<th rowspan="2" class="corner-cell">'
            f'<span class="corner-top">{t("榜单", "List")}</span>'
            '<svg viewBox="0 0 100 100" preserveAspectRatio="none">'
            '<line x1="0" y1="0" x2="100" y2="100" stroke="#aaa" stroke-width="0.8"/>'
            "</svg>"
            f'<span class="corner-bot">{t("类目", "Category")}</span>'
            "</th>"
        )
        for grp, metrics in GROUPS:
            parts.append(f'<th colspan="{len(metrics)}" class="group-start">{grp}</th>')
        parts.append("</tr>")

        parts.append("<tr>")
        for grp, metrics in GROUPS:
            for i, m in enumerate(metrics):
                cls = "sub-h group-start" if i == 0 else "sub-h"
                parts.append(f'<th class="{cls}">{METRIC_LABELS[m]}</th>')
        parts.append("</tr></thead><tbody>")

        for _, row in show.iterrows():
            parts.append("<tr>")
            parts.append(f'<td class="cat-cell">{row[("", "类目")]}</td>')
            for grp, metrics in GROUPS:
                for i, m in enumerate(metrics):
                    parts.append(_cell_html(row[(grp, m)], m, first_in_group=(i == 0)))
            parts.append("</tr>")
        parts.append("</tbody></table>")

        css = f"""
<style>
.lifespan-cmp {{
    border-collapse: collapse; font-family: inherit; font-size: 13px;
    background: white; width: 100%; table-layout: auto;
}}
.lifespan-cmp thead th {{
    background-color: #f0f4f8; font-weight: 600; padding: 6px 10px;
    text-align: center; border-bottom: 1px solid #aaa; white-space: nowrap;
}}
.lifespan-cmp tbody td {{
    padding: 4px 10px; border-bottom: 1px solid #e8e8e8;
    text-align: right; font-variant-numeric: tabular-nums;
}}
.lifespan-cmp .group-start {{ border-left: {BORDER} !important; }}
.lifespan-cmp .corner-cell {{
    position: sticky; left: 0; z-index: 3;
    min-width: 107px; width: 107px; height: 56px;
    background-color: #f0f4f8; padding: 0 !important;
    border-right: 1px solid #d0d4dc;
}}
.lifespan-cmp .corner-cell svg {{
    position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;
}}
.lifespan-cmp .corner-top {{ position: absolute; top: 4px; right: 10px; font-weight: 600; font-size: 12px; }}
.lifespan-cmp .corner-bot {{ position: absolute; bottom: 4px; left: 10px; font-weight: 600; font-size: 12px; }}
.lifespan-cmp .cat-cell {{
    position: sticky; left: 0; z-index: 2; font-weight: 500;
    text-align: left !important; white-space: nowrap;
    background-color: white !important; border-right: 1px solid #d0d4dc;
}}
.lifespan-cmp .empty-cell {{ color: #aaa; text-align: center !important; }}
</style>
"""
        st.markdown(
            css + f'<div style="overflow-x: auto; max-width: 100%;">{"".join(parts)}</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div style='font-size:0.68rem; color:#6b7280; line-height:1.7; margin-top:6px;'>"
            + t("* BS 在榜率：该类目 BS ASIN 平均在榜天数 / 采集天数；越高说明头部产品生命周期越长",
                "* BS on-list %: avg BS ASIN days-on-list / sampled days; higher = the longer the head products' lifecycle")
            + "<br>"
            + t("* BS 满榜率：整段采集期天天在榜的常驻款占比；高在榜率 + 高满榜率 = 少数款霸榜，高在榜率 + 低满榜率 = 广泛轮动",
                "* BS full-list %: share always on every day; high on-list + high full-list = a few dominate, high on-list + low full-list = broad rotation")
            + "<br>"
            + t("* BS 新增比例：采集期内才首次上榜（非开窗第一天就在）的 ASIN 占比，越高说明头部越多「新面孔」",
                "* BS new-ASIN %: share of ASINs that first appeared after the window opened; higher = more newcomers in the head")
            + "<br>"
            + t("* NR 流动率：NR 榜每天平均有百分之几的 ASIN 被替换，越高说明新品更替越快、越活跃",
                "* NR turnover %: avg share of NR ASINs replaced per day; higher = faster new-product churn")
            + "<br>"
            + t("* →BS 渗透率：先在源榜（NR/MS）出现、之后又进 BS 的去重 ASIN ÷ 源榜去重 ASIN",
                "* →BS penetration: unique ASINs that appeared on the source list (NR/MS) first then reached BS ÷ unique source-list ASINs")
            + "</div>",
            unsafe_allow_html=True,
        )

        # 解读：从「类目特点」出发综合多指标给结论（哪类封闭、哪类开放），不逐列念数；
        #   类目名按数据动态选取（满榜率 top3 / 在榜率 bottom3 / NR 流动率 top3）。
        _on, _full_c = ("BS", "在榜率"), ("BS", "满榜率")
        _flow_c = ("NR", "流动率")

        def _cats(dfsub, k=3):
            return "、".join(f"<b>{r[('', '类目')]}</b>" for _, r in dfsub.head(k).iterrows())

        _closed = show.dropna(subset=[_full_c]).nlargest(3, _full_c)   # 较封闭：满榜率最高
        _open = show.dropna(subset=[_on]).nsmallest(3, _on)            # 较开放：在榜率最低
        _nr_top = show.dropna(subset=[_flow_c]).nlargest(3, _flow_c)   # 新品洗牌最快：NR 流动率最高

        _items = []
        if not _closed.empty:
            _items.append(
                t(f"{_cats(_closed)} 的 BS 头部较封闭，常驻款占着位子（满榜率最高、在榜率也居前），新上来的 ASIN 较少。",
                  f"{_cats(_closed)} have relatively closed BS heads—a permanent core holds the spots "
                  f"(highest full-list rate, also high on-list), with fewer newly-added ASINs."))
        if not _open.empty:
            _items.append(
                t(f"{_cats(_open)} BS 头部较为开放流动，在榜率与满榜率较低，新增 ASIN 占比较高。",
                  f"{_cats(_open)} have more open, fluid BS heads—lower on-list and full-list rates, "
                  f"with a higher share of newly-added ASINs."))
        if not _nr_top.empty:
            _items.append(
                t(f"单看新品端，{_cats(_nr_top)} 的 NR 新品池洗牌最快——上新最频繁、新品流动性最强。",
                  f"On the new-product side, {_cats(_nr_top)} churn their NR pool fastest—the most frequent, fluid launches."))
        _items.append(
            t("→BS 渗透率均较低，因为 13 天窗口下两周内冲进 BS 是稀有事件，仅作相对参考。",
              "→BS penetration is low across the board: within a 13-day window, breaking into BS in two weeks is rare—relative reference only."))
        insight_box(_items)

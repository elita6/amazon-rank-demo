# streamlit_app/pages/1_类目详情.py
# 更新日期：2026-06-28
# 用途：类目详情（Demo 版，对齐生产 v2）— 统一聚合口径后的描述性分析页。
#       结构：1.1 类目概览（表）+ 1.2 类目画像（基础分布 + 交叉分析）
# 启动命令：streamlit run streamlit_app/产品概览.py
# 与生产 v2 差异：
#   - 数据源从 data/amazon.db 改为 data/*.csv（_demo_data.connect_demo in-memory sqlite）
#   - 类目/品牌/ASIN 已匿名化（Category A~R / Brand_xxx）；CAT_SHORT/TEXT_POS 对 demo 类目无映射，
#     自动回退原名/默认方位，不影响逻辑
# 主要改动：
#   - 2026-06-28：从生产 v2 类目详情.py 移植（去「三榜合并」默认 BS；价格/评论 winsor_mean；
#       需求增量/存量指数；箱线图不去极值；品牌归一化去重；象限图；全图 insight_box 数据驱动解读）
#   - 2026-06-29：对齐生产 v2 本轮改动——
#       1) 汇总表「平均价格」前补「平均累计评论数」列（=最新一天快照 winsor 均值 latest_review_repr）；
#       2) 表注改「需求累积量指数=平均累计评论数×平均价格（评论按最新值）」+ 加「需求指标仅作大致参考」行；
#       3) 箱型图「评论数分布」→「累计评论数分布」，数据改每类目最新一天快照（与平均累计评论同口径），价格仍全窗口；
#       4) 象限图换轴 X=需求存量(体量)/Y=加速度(增量/存量)，去四象限名，中位虚线端点写方向词（快/慢/小/大），
#          解读改纯位置描述（体量多·增速快 等），图下加「存量/增速为近似代理、非真实销量」注。

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "streamlit_app"))
from _styles import page_title, chart_title, conclusion, chart_spacer, insight_box
from _i18n import t
from _aggregate import (winsor_mean, demand_increment_index, demand_stock_index,
                        latest_review_repr, distribution_insights, crosslink_neg,
                        fmt_compact)
from _brands import normalize_brand
from _demo_data import connect_demo

# 19 大类长名 → 短名（散点图 label 用，避免重叠；hover 仍显完整名）
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

# 去掉「三榜合并(all)」：三榜是三个不同总体，混池算代表值无干净业务含义。默认 BS。
LIST_LABELS = {
    "best_seller":     t("BS", "BS"),
    "new_release":     t("NR", "NR"),
    "movers_shakers":  t("MS", "MS"),
}
LIST_OPTIONS_FULL = ["best_seller", "new_release", "movers_shakers"]


@st.cache_data
def load_data():
    conn = connect_demo()
    asin = pd.read_sql(
        "SELECT category, list_type, date, asin, brand, price_low, rate, "
        "review_count, has_video FROM asin_daily",
        conn,
    )
    summary = pd.read_sql(
        "SELECT category, n_subcategories, is_subcategory FROM category_summary",
        conn,
    )
    # 品牌归一化（去重口径统一）：Sony/SONY/Sony Inc. 归为同一品牌。
    # 在去重值上算映射再回填，避免逐行重复 regex。
    uniq = pd.Series(asin["brand"].dropna().unique())
    bmap = dict(zip(uniq, uniq.map(normalize_brand)))
    asin["brand_norm"] = asin["brand"].map(bmap)
    return asin, summary


@st.cache_data
def compute_bs_metrics(asin):
    """需求增量指数 / 需求存量指数 均为 BS 单口径，与页面榜单选择器无关，预先按类目算好。"""
    bs = asin[asin["list_type"] == "best_seller"]
    empty = pd.Series(dtype=float)
    if bs.empty:
        return empty, empty
    increment = bs.groupby("category").apply(demand_increment_index).dropna().round(0)
    stock = bs.groupby("category").apply(demand_stock_index).dropna().round(0)
    return increment, stock


def filter_by_list(df, list_choice):
    return df[df["list_type"] == list_choice]


def list_suffix(list_choice):
    return t(f"（{LIST_LABELS[list_choice]}）", f" ({LIST_LABELS[list_choice]})")


def list_radio(label, key, default="best_seller", options=LIST_OPTIONS_FULL):
    return st.radio(
        label, options=options,
        format_func=lambda k: LIST_LABELS[k],
        index=options.index(default), horizontal=True, key=key,
        label_visibility="collapsed",
    )


# =======================================================================
# 页面
# =======================================================================
page_title(t("类目详情", "Category Detail"))

asin, summary = load_data()

# 默认排除子类目
sub_set = set(summary[summary["is_subcategory"] == 1]["category"].tolist())
asin = asin[~asin["category"].isin(sub_set)]
summary = summary[summary["is_subcategory"] != 1].copy()
main_cats = summary["category"].tolist()

# 需求增量指数(近期) / 需求存量指数(历史)（BS 单口径，预先算好）
increment_by_cat, stock_by_cat = compute_bs_metrics(asin)

# 数据摘要（页面顶部 KPI）
_n_asin = asin["asin"].nunique()
_n_brand = asin["brand_norm"].dropna().nunique()
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
_kpi(_kp1, t("分析类目数", "Categories analyzed"),      f"{len(main_cats)}")
_kpi(_kp2, t("ASIN 数(去重)", "ASINs (unique)"),   f"{_n_asin:,}")
_kpi(_kp3, t("品牌数(去重)", "Brands (unique)"),    f"{_n_brand:,}")
_kpi(_kp4, t("数据时间范围", "Date range"),
     f"{_date_min} ~ {_date_max}"
     f"<div style='font-size:0.75rem; color:#9ca3af; margin-top:2px;'>({_n_days} {t('天', 'days')})</div>",
     value_size="0.85rem", value_color="#36383b")


# =======================================================================
# 1.1 类目概览
# =======================================================================
with st.container(border=True):
    st.markdown(f"## {t('类目概览', 'Category Overview')}")

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
        st.markdown(f"<div class='filter-label'>🔍 {t('类目选择', 'Category Filter')}</div>",
                    unsafe_allow_html=True)
        with st.popover(f"{t('已选', 'Selected')} {n_sel} / {n_total}", use_container_width=False):
            bcol1, bcol2 = st.columns(2)
            bcol1.button(t("✓ 全选", "✓ Select All"), key="cd_btn_all",
                         on_click=_cd_select_all, use_container_width=True)
            bcol2.button(t("✗ 全不选", "✗ Clear"), key="cd_btn_none",
                         on_click=_cd_clear_all, use_container_width=True)
            st.multiselect(t("勾选类目", "Select categories"), options=main_cats,
                           key="cd_cats_inner", label_visibility="collapsed")
    with fc2:
        st.markdown("<div class='filter-label' style='visibility:hidden;'>·</div>",
                    unsafe_allow_html=True)
        cd_list = list_radio(t("榜单", "List"), key="cd_list", default="best_seller")
    cd_cats = st.session_state.cd_cats_inner or list(main_cats)
    is_bs = (cd_list == "best_seller")

    asin_v = filter_by_list(asin, cd_list)
    asin_v = asin_v[asin_v["category"].isin(cd_cats)]
    suffix = list_suffix(cd_list)

    chart_title(f"● {t('类目汇总', 'Category Summary')}{suffix}")

    # 价格/评论 = 决策1 缩尾均值（去极值后平均，替代旧中位数）
    agg_view = (
        asin_v.groupby("category")
        .agg(
            records=("asin", "size"),
            days=("date", "nunique"),
            unique_asin=("asin", "nunique"),
            unique_brand=("brand_norm", lambda s: s.dropna().nunique()),
            price_repr=("price_low", winsor_mean),
            rate_mean=("rate", winsor_mean),  # 决策1：评分也是数值水平型，统一走缩尾均值（有界变量，效果≈普通均值但口径一致）
            has_video_pct=("has_video", "mean"),
        )
        .reset_index()
    )
    agg_view = agg_view.merge(
        summary[["category", "n_subcategories"]], on="category", how="left",
    )

    # 平均累计评论数 = 需求存量指数的评论因子：取该类目最新一天快照、缩尾后求平均
    #   （累计型变量取最新值，非跨天平均；与下方注释「评论数按最新值取值」一致）
    agg_view["review_repr"] = agg_view["category"].map(
        asin_v.groupby("category").apply(latest_review_repr).round(0)
    )

    # 需求增量指数 / 需求存量指数：固定 BS 口径，仅 BS 视图显示
    if is_bs:
        agg_view["demand_increment"] = agg_view["category"].map(increment_by_cat)
        agg_view["demand_stock"] = agg_view["category"].map(stock_by_cat)

    agg_view["has_video_pct"] = (agg_view["has_video_pct"] * 100).round(1)
    agg_view["price_repr"] = agg_view["price_repr"].round(2)
    agg_view["rate_mean"] = agg_view["rate_mean"].round(2)

    ordered_cols = ["category", "records", "days", "unique_asin", "unique_brand",
                    "n_subcategories", "demand_increment", "demand_stock",
                    "review_repr", "price_repr", "rate_mean", "has_video_pct"]
    ordered_cols = [c for c in ordered_cols if c in agg_view.columns]
    display = agg_view[ordered_cols].copy()

    COL_CATEGORY      = t("类目", "Category")
    COL_RECORDS       = t("记录数", "Records")
    COL_DAYS          = t("样本天数", "Sample days")
    COL_UNIQUE_ASIN   = t("唯一ASIN", "Unique ASINs")
    COL_BRAND         = t("品牌数", "Brands")
    COL_SUBCAT        = t("子类数", "Subcategories")
    COL_INCREMENT     = t("需求增量指数(月均)", "Demand Increment (monthly)")
    COL_STOCK         = t("需求累积量指数", "Demand Stock")
    COL_REVIEW_REPR   = t("平均累计评论数", "Avg cumulative reviews")
    COL_PRICE_REPR    = t("平均价格", "Avg price")
    COL_RATE_MEAN     = t("平均评分", "Avg rating")
    COL_HAS_VIDEO     = t("有视频%", "Video %")

    rename_map = {
        "category":           COL_CATEGORY,
        "records":            COL_RECORDS,
        "days":               COL_DAYS,
        "unique_asin":        COL_UNIQUE_ASIN,
        "unique_brand":       COL_BRAND,
        "n_subcategories":    COL_SUBCAT,
        "demand_increment":   COL_INCREMENT,
        "demand_stock":       COL_STOCK,
        "review_repr":        COL_REVIEW_REPR,
        "price_repr":         COL_PRICE_REPR,
        "rate_mean":          COL_RATE_MEAN,
        "has_video_pct":      COL_HAS_VIDEO,
    }
    display = display.rename(columns=rename_map)
    sort_col = COL_STOCK if COL_STOCK in display.columns else COL_UNIQUE_ASIN
    display = display.sort_values(sort_col, ascending=False, na_position="last")

    column_config = {
        COL_CATEGORY:    st.column_config.TextColumn(width="medium", pinned=True),
        COL_RECORDS:     st.column_config.NumberColumn(format="%d"),
        COL_DAYS:        st.column_config.NumberColumn(format="%d"),
        COL_UNIQUE_ASIN: st.column_config.NumberColumn(format="%d"),
        COL_BRAND:       st.column_config.NumberColumn(
            format="%d",
            help=t(
                "归一化去重品牌数：转小写 + 去 ®™ + 合并连字符/点 + 剥离公司后缀(Inc/Ltd…) 后计数，"
                "故 Sony / SONY / Sony Inc. 算 1 个。纯规则、不做模糊匹配（不会误并 Sony 与 Sonos）。",
                "Normalized distinct brands: lowercased + ®™ removed + hyphens/dots merged + corporate "
                "suffixes (Inc/Ltd…) stripped before counting, so Sony / SONY / Sony Inc. count as 1. "
                "Rule-based only, no fuzzy matching (won't merge Sony and Sonos).",
            ),
        ),
        COL_SUBCAT:      st.column_config.NumberColumn(format="%d"),
    }
    if COL_INCREMENT in display.columns:
        m = display[COL_INCREMENT].max()
        column_config[COL_INCREMENT] = st.column_config.ProgressColumn(
            format="%d", min_value=0, max_value=float(m) if m else 1,
        )
    if COL_STOCK in display.columns:
        m = display[COL_STOCK].max()
        column_config[COL_STOCK] = st.column_config.ProgressColumn(
            format="%d", min_value=0, max_value=float(m) if m else 1,
        )
    if COL_REVIEW_REPR in display.columns:
        m = display[COL_REVIEW_REPR].max()
        column_config[COL_REVIEW_REPR] = st.column_config.ProgressColumn(
            format="%d", min_value=0, max_value=float(m) if m else 1,
            help=t(
                "该类目最新一天快照的累计评论数，P5/P95 缩尾后求平均（累计型取最新值，非跨天平均）。"
                "它 × 平均价格 = 需求累积量指数。",
                "Latest-day snapshot cumulative reviews, winsorized at P5/P95 then averaged "
                "(cumulative variable taken at its latest value). This × avg price = Demand Stock.",
            ),
        )
    if COL_PRICE_REPR in display.columns:
        m = display[COL_PRICE_REPR].max()
        column_config[COL_PRICE_REPR] = st.column_config.ProgressColumn(
            format="$%.2f", min_value=0, max_value=float(m) if m else 1,
        )
    if COL_RATE_MEAN in display.columns:
        column_config[COL_RATE_MEAN] = st.column_config.ProgressColumn(
            format="%.2f", min_value=0, max_value=5,
        )
    if COL_HAS_VIDEO in display.columns:
        column_config[COL_HAS_VIDEO] = st.column_config.ProgressColumn(
            format="%.1f%%", min_value=0, max_value=100,
        )

    st.dataframe(display, hide_index=True, width="stretch",
                 column_config=column_config, height=420)

    note = t(
        "• 注：极值按 P5/P95 缩尾处理<br>"
        "• 需求增量指数(月均)：评论增量 × 平均价格 / 统计天数 × 30<br>"
        "• 需求累积量指数：平均累计评论数 × 平均价格（其中评论数按最新值取值）<br>"
        "• 需求指标仅作大致参考、用于跨类目相对排序，非真实销量/GMV",
        "• Note: extremes winsorized at P5/P95<br>"
        "• Demand Increment (monthly): review increment × avg price / observed days × 30<br>"
        "• Demand Stock: avg cumulative reviews × avg price (reviews taken at their latest value)<br>"
        "• Demand metrics are a rough reference for cross-category relative ranking only — not real sales/GMV",
    )
    if not is_bs:
        note += t("<br>（NR/MS 视图下需求增量/累积量指数隐藏，为固定 BS 口径）",
                  "<br>(Demand Increment/Stock hidden under NR/MS — fixed BS basis)")
    st.markdown(
        "<div style='font-size: 0.70rem; color: #6b7280; line-height: 1.65; margin-top: 4px;'>"
        + note + "</div>",
        unsafe_allow_html=True,
    )

    # 解读：与汇总表同一份 agg_view 现算（当前榜单 + 类目筛选下），指标名沿用表头。
    _ov = []
    _join = lambda d, c: "、".join(f"<b>{r['category']}</b>" for _, r in d.iterrows())
    if "demand_stock" in agg_view.columns:
        _st = agg_view.dropna(subset=["demand_stock"])
        if len(_st) >= 2:
            _t3 = _st.nlargest(3, "demand_stock")
            _s_hi = _t3.iloc[0]
            _s_med = _st["demand_stock"].median()
            _ratio = _s_hi["demand_stock"] / _s_med if _s_med else None
            _ov.append(t(
                f"按<b>需求累积量指数</b>（历史累计需求），排在前列的依次是 {_join(_t3, 'category')}"
                + (f"；居首的 <b>{_s_hi['category']}</b> 约为中位类目的 {_ratio:.0f} 倍。" if _ratio else "。"),
                f"By <b>Demand Stock</b> (historical), the leaders are {_join(_t3, 'category')}"
                + (f"; the top one, <b>{_s_hi['category']}</b>, is ~{_ratio:.0f}× the median category." if _ratio else ".")))
            if "demand_increment" in agg_view.columns:
                _it = agg_view.dropna(subset=["demand_increment"])
                if not _it.empty:
                    _it3 = _it.nlargest(3, "demand_increment")
                    _i_hi = _it3.iloc[0]
                    _diff = (f"——和历史最大的 <b>{_s_hi['category']}</b> 不是同一个，近期最旺另有其人。"
                             if _i_hi["category"] != _s_hi["category"] else "——与历史最大的同为一个类目。")
                    _diff_en = (f"—not the same as the historical leader <b>{_s_hi['category']}</b>; the hottest-recently differs."
                                if _i_hi["category"] != _s_hi["category"] else "—same category as the historical leader.")
                    _ov.append(t(
                        f"按<b>需求增量指数(月均)</b>（近期需求），排在前列的是 {_join(_it3, 'category')}{_diff}",
                        f"By <b>Demand Increment (monthly)</b> (recent), the leaders are {_join(_it3, 'category')}{_diff_en}"))
    if "has_video_pct" in agg_view.columns and agg_view["has_video_pct"].notna().any():
        _hv = agg_view.dropna(subset=["has_video_pct"])
        _hi2 = _hv.nlargest(2, "has_video_pct")
        _lo2 = _hv.nsmallest(2, "has_video_pct")
        _hs = "、".join(f"<b>{r['category']}</b> {r['has_video_pct']:.0f}%" for _, r in _hi2.iterrows())
        _ls = "、".join(f"<b>{r['category']}</b> {r['has_video_pct']:.0f}%" for _, r in _lo2.iterrows())
        _ov.append(t(
            f"<b>有视频%</b> 最高的是 {_hs}；最低的是 {_ls}——主图带视频的普及度在类目间差距很大。",
            f"<b>Video %</b> highest: {_hs}; lowest: {_ls}—video adoption varies widely across categories."))
    if "rate_mean" in agg_view.columns and agg_view["rate_mean"].notna().any():
        _rm = agg_view["rate_mean"].dropna()
        _ov.append(t(
            f"各类目<b>平均评分</b>全落在 {_rm.min():.2f}–{_rm.max():.2f} 之间（极差仅 {(_rm.max()-_rm.min()):.2f} 分），整体偏高、彼此几乎拉不开差距。",
            f"<b>Avg rating</b> across all categories sits within {_rm.min():.2f}–{_rm.max():.2f} (range just {(_rm.max()-_rm.min()):.2f})—uniformly high, barely separable."))
    insight_box(_ov)

    csv_bytes = display.to_csv(index=False).encode("utf-8-sig")
    _, _, dl_col = st.columns([5, 3, 1])
    with dl_col:
        st.download_button(
            t("📥 下载 CSV", "📥 Download CSV"), csv_bytes,
            file_name="category_overview.csv", mime="text/csv",
            help=t("下载当前筛选下的横向汇总表", "Download the summary table under the current filter"),
        )


# =======================================================================
# 1.2 类目画像
# =======================================================================
st.markdown(f"## {t('类目画像', 'Category Profile')}")

# ----- 基础分布 -----
with st.container(border=True):
    st.markdown(f"**● {t('基础分布', 'Distributions')}**")

    bd_list = list_radio(t("榜单", "List"), key="bd_list", default="best_seller")
    suffix_bd = list_suffix(bd_list)
    asin_bd = filter_by_list(asin, bd_list)
    asin_bd = asin_bd.dropna(subset=["price_low", "review_count"], how="all")

    if asin_bd.empty:
        st.warning(t("当前榜单无数据", "No data for the current list"))
    else:
        # 决策1：分布图只汇总、不缩尾——展示全貌（缩尾是为算代表值，画分布要保留长尾）
        bd_v = asin_bd.copy()

        chart_title(f"1. {t('价格分布', 'Price Distribution')}{suffix_bd}")
        _pi = distribution_insights(bd_v, "category", "price_low")
        fig = px.box(bd_v.dropna(subset=["price_low"]),
                     x="category", y="price_low", height=380,
                     points=False, color="category")
        fig.update_traces(hovertemplate="%{x}<br>%{y:.2f} USD<extra></extra>")
        fig.update_layout(xaxis_tickangle=-30, xaxis_title=None,
                          yaxis_title=t("价格 (USD)", "Price (USD)"), showlegend=False,
                          yaxis=dict(tickformat=".2f"),
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")

        if _pi:
            _p = lambda v: fmt_compact(v, money=True)
            _items = [
                t(f"{_pi['n_skew']}/{_pi['n_cat']} 类目<b>平均价格都高于中位价</b>——少数高价产品把平均拉高了。",
                  f"In {_pi['n_skew']}/{_pi['n_cat']} categories the <b>average price is above the median</b>—a few high-priced products pull the average up."),
                t(f"多数类目<b>中位价</b> {_p(_pi['rep_p25'])}–{_p(_pi['rep_p75'])}；<b>{_pi['high_cat']}</b> 中位价最高（{_p(_pi['high_val'])}，{_pi['n_cat']} 类目第 1"
                  + (f"，约最便宜 {_pi['low_cat']}（{_p(_pi['low_val'])}）的 {_pi['ratio']:.0f} 倍）。" if _pi.get('ratio') else "）。"),
                  f"Most categories' <b>median price</b> {_p(_pi['rep_p25'])}–{_p(_pi['rep_p75'])}; <b>{_pi['high_cat']}</b> has the highest median ({_p(_pi['high_val'])}, #1 of {_pi['n_cat']}"
                  + (f", ~{_pi['ratio']:.0f}× the cheapest {_pi['low_cat']} ({_p(_pi['low_val'])}))." if _pi.get('ratio') else ").")),
                t(f"<b>{_pi['disp_high'][0]}/{_pi['disp_high'][1]}</b> 类目内价位最分散（平价到高端跨度大）；<b>{_pi['disp_low'][0]}/{_pi['disp_low'][1]}</b> 最集中。",
                  f"<b>{_pi['disp_high'][0]}/{_pi['disp_high'][1]}</b> span the widest internal price range; <b>{_pi['disp_low'][0]}/{_pi['disp_low'][1]}</b> are the most concentrated."),
            ]
            insight_box(_items)

        chart_spacer()

        chart_title(f"2. {t('累计评论数分布', 'Cumulative Review Count Distribution')}{suffix_bd}")
        # 累计评论是累计型变量：取每类目「最新一天」快照（每 ASIN 一个当前值），与汇总表
        #   「平均累计评论数」同口径——避免全窗口按在榜天数重复计数/加权同一 ASIN（伪重复）。
        _bd_rev = bd_v.dropna(subset=["review_count"])
        _bd_rev = _bd_rev[_bd_rev["date"] ==
                          _bd_rev.groupby("category")["date"].transform("max")]
        _ri = distribution_insights(_bd_rev, "category", "review_count", id_col="asin")
        fig = px.box(_bd_rev,
                     x="category", y="review_count", height=380,
                     points=False, color="category")
        fig.update_traces(hovertemplate="%{x}<br>%{y:.0f}<extra></extra>")
        fig.update_layout(xaxis_tickangle=-30, xaxis_title=None,
                          yaxis_title=t("累计评论数", "Cumulative review count"), showlegend=False,
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")

        if _ri:
            _deep = "、".join(f"<b>{c}</b>" for c, _ in _ri["top_reps"][:2])
            _deep_en = ", ".join(f"<b>{c}</b>" for c, _ in _ri["top_reps"][:2])
            # 单品评论极值 → 直链该 ASIN 的 Amazon 商品页（Demo 为匿名 ASIN，链接仅示意）
            _lk = (f"（<a href='https://www.amazon.com/dp/{_ri['tail_id']}' target='_blank'>{t('查看商品','view product')}</a>）"
                   if _ri.get("tail_id") else "")
            _items = [
                t(f"多数类目<b>典型产品(中位)评论</b> {fmt_compact(_ri['rep_p25'])}–{fmt_compact(_ri['rep_p75'])} 条；{_deep} 等典型最深（约 {fmt_compact(_ri['top_reps'][0][1])} 条）。",
                  f"Most categories' <b>typical (median) reviews</b> {fmt_compact(_ri['rep_p25'])}–{fmt_compact(_ri['rep_p75'])}; {_deep_en} are the deepest (~{fmt_compact(_ri['top_reps'][0][1])})."),
                t(f"<b>{_ri['tail_cat']}</b> 出现单品评论破 {fmt_compact(_ri['tail_val'])} 条{_lk}，头部口碑壁垒极高。",
                  f"<b>{_ri['tail_cat']}</b> has a single product exceeding {fmt_compact(_ri['tail_val'])} reviews{_lk}—a very high head barrier."),
            ]
            # 跨指标发现：价格图已在上方出现，符合阅读顺序；仅当数据支持反向关系才输出
            _cl = crosslink_neg(_pi["rep"], _ri["rep"]) if _pi else None
            if _cl:
                _rktxt = "评论数垫底（倒数第 1）" if _cl["b_rank"] == _cl["n"] else f"评论数靠后（第 {_cl['b_rank']}/{_cl['n']}）"
                _rktxt_en = "the fewest reviews" if _cl["b_rank"] == _cl["n"] else f"few reviews (#{_cl['b_rank']}/{_cl['n']})"
                _items.append(t(
                    f"越贵的类目评论反而越薄——<b>中位价最高</b>的 <b>{_cl['top_a_cat']}</b>，{_rktxt}。💡推测：高价品买的人少、评论攒得慢。",
                    f"Pricier categories tend to have fewer reviews—<b>{_cl['top_a_cat']}</b> (highest median price) has {_rktxt_en}. 💡Likely: high-priced items sell less often, so reviews accrue slower."))
            insight_box(_items)

        st.caption(t(
            "注：箱线图展示原始分布（不去极值）。价格用全窗口全部观测；累计评论取每类目最新一天快照"
            "（每 ASIN 一个当前值），与汇总表「平均累计评论数」同口径。",
            "Note: box plots show the raw distribution (no winsorizing). Price uses all observations across "
            "the full window; cumulative reviews use each category's latest-day snapshot (one current value "
            "per ASIN), matching the summary table's Avg cumulative reviews.",
        ))


# ----- 交叉分析 -----
with st.container(border=True):
    # ============================================================
    # 类目象限图（需求存量[体量] × 加速度[增速] 4 象限 — 固定 BS 口径）
    #   旧版用 增量×存量，两轴秩相关高（伪二维、信息冗余）；改为 存量×加速度后两轴近正交：
    #   X=体量大小、Y=增速快慢，各答一个问题。加速度=增量/存量=月增评论/累计评论
    #   （价格约掉、体量中性）。不设象限名；方向词写在两条轴的两端：
    #   X 轴(体量) 左小右大、Y 轴(增速) 下慢上快。
    # ============================================================
    chart_title(t("类目象限图（固定BS口径）", "Category Quadrant Chart (fixed BS basis)"))
    quad = pd.DataFrame({"category": main_cats})
    quad["inc"] = quad["category"].map(increment_by_cat)
    quad["stk"] = quad["category"].map(stock_by_cat)
    quad = quad.dropna(subset=["inc", "stk"])
    quad["size"] = quad["stk"]                   # X = 体量（需求存量指数）
    quad["speed"] = quad["inc"] / quad["stk"]    # Y = 增速（加速度 = 增量/存量）

    if not quad.empty:
        quad["类目短名"] = quad["category"].map(CAT_SHORT).fillna(quad["category"])
        # 19 类目逐个显式 override textposition（cycle 不可控，密集区会重叠）
        TEXT_POS = {
            "Pet Supplies":                 "middle left",
            "Home & Kitchen":               "top right",
            "Cell Phones & Accessories":    "bottom right",
            "Office Products":              "top left",
            "Electronics":                  "middle right",
            "Health & Household":           "bottom center",
            "Computers & Accessories":      "top center",
            "Sports & Outdoors":            "bottom right",
            "Amazon Devices & Accessories": "middle left",
            "Kitchen & Dining":             "top center",
            "Beauty & Personal Care":       "middle right",
            "Automotive":                   "middle right",
            "Tools & Home Improvement":     "top center",
            "Clothing, Shoes & Jewelry":    "bottom center",
            "Patio, Lawn & Garden":         "middle left",
            "Appliances":                   "top center",
            "Arts, Crafts & Sewing":        "bottom center",
            "Musical Instruments":          "top center",
            "Camera & Photo Products":      "middle right",
        }
        text_positions = [TEXT_POS.get(cat, "top center") for cat in quad["category"]]

        fig = px.scatter(
            quad, x="size", y="speed",
            text="类目短名",
            hover_name="category",
            hover_data={"size": ":.0f",
                        "speed": ":.4f",
                        "类目短名": False},
            height=520,
            labels={"size": t("需求存量指数（体量）", "Demand Stock (size)"),
                    "speed": t("增速＝加速度（增量/存量）", "Growth speed = Increment/Stock")},
        )
        fig.update_traces(
            marker=dict(size=12, color="#a8cfee",
                        line=dict(width=1, color="#5b8fc4"),
                        opacity=0.85),
            textposition=text_positions,
            textfont=dict(size=10, color="#444"),
        )
        mx = quad["size"].median()
        my = quad["speed"].median()
        fig.add_vline(x=mx, line_dash="dash", line_color="gray")
        fig.add_hline(y=my, line_dash="dash", line_color="gray")
        x_lo, x_hi = quad["size"].min(), quad["size"].max()
        y_lo, y_hi = quad["speed"].min(), quad["speed"].max()
        x_range = [max(0, x_lo - (x_hi - x_lo) * 0.10), x_hi + (x_hi - x_lo) * 0.12]
        y_range = [max(0, y_lo - (y_hi - y_lo) * 0.10), y_hi + (y_hi - y_lo) * 0.15]
        # 方向词写在两条中位虚线（十字）的端点：
        #   竖线(增速) 上端=快、下端=慢（x 对齐 mx）；横线(体量) 左端=小、右端=大（y 对齐 my）。
        _df = dict(size=14, color="#555")
        fig.add_annotation(xref="x", x=mx, yref="paper", y=1.0, yshift=16,
                           text=f"<b>{t('快', 'Fast')}</b>", showarrow=False,
                           font=_df, xanchor="center", yanchor="bottom")
        fig.add_annotation(xref="x", x=mx, yref="paper", y=0.0, yshift=-16,
                           text=f"<b>{t('慢', 'Slow')}</b>", showarrow=False,
                           font=_df, xanchor="center", yanchor="top")
        fig.add_annotation(xref="paper", x=0.0, xshift=-12, yref="y", y=my,
                           text=f"<b>{t('小', 'Small')}</b>", showarrow=False,
                           font=_df, xanchor="right", yanchor="middle")
        fig.add_annotation(xref="paper", x=1.0, xshift=12, yref="y", y=my,
                           text=f"<b>{t('大', 'Big')}</b>", showarrow=False,
                           font=_df, xanchor="left", yanchor="middle")
        fig.update_layout(
            xaxis=dict(range=x_range),
            yaxis=dict(range=y_range),
            margin=dict(l=52, r=34, t=44, b=56),
        )
        st.plotly_chart(fig, width="stretch")

        st.markdown(
            "<div style='font-size: 0.70rem; color: #6b7280; line-height: 1.65; margin-top: 4px;'>"
            + t(f"坐标轴=中位线（{len(quad)} 类目中间水平）",
                f"Axes split at the median ({len(quad)} categories' midpoint)")
            + "<br>"
            + t("需求存量、增速是近似代理，非真实销量/GMV，仅做大致参考",
                "Demand stock and growth speed are rough proxies, not real sales/GMV—rough reference only")
            + "</div>",
            unsafe_allow_html=True,
        )

        # 解读：与象限图同一份 quad + 同一中位虚线（mx=体量中位, my=增速中位）划象限。
        # 纯位置描述（体量 多/少 × 增速 快/慢）；剔除贴近中位线的类目（归属不稳），
        # 按"离两条线都远"(角落代表性 = 两轴归一偏离的较小者)取前 k。
        _xspan = (quad["size"].max() - quad["size"].min()) or 1
        _yspan = (quad["speed"].max() - quad["speed"].min()) or 1
        _NEAR = 0.08   # 距中位线 < 8% 轴跨度 视为"贴线"，不写进解读

        def _typical(d, k=3):
            if d.empty:
                return ""
            dd = d.assign(_dx=(d["size"] - mx).abs() / _xspan,
                          _dy=(d["speed"] - my).abs() / _yspan)
            dd = dd[(dd["_dx"] >= _NEAR) & (dd["_dy"] >= _NEAR)]   # 剔贴线
            if dd.empty:
                return ""
            dd = dd.assign(_corner=dd[["_dx", "_dy"]].min(axis=1))  # 离两线都远=典型
            dd = dd.sort_values("_corner", ascending=False)
            return "、".join(f"<b>{c}</b>" for c in dd["category"].head(k).tolist())

        _bigfast = quad[(quad["size"] > mx) & (quad["speed"] > my)]     # 右上 多·快
        _bigslow = quad[(quad["size"] > mx) & (quad["speed"] <= my)]    # 右下 多·慢
        _smallfast = quad[(quad["size"] <= mx) & (quad["speed"] > my)]  # 左上 少·快
        _smallslow = quad[(quad["size"] <= mx) & (quad["speed"] <= my)] # 左下 少·慢
        _q = []
        _bf = _typical(_bigfast)
        if _bf:
            _q.append(t(
                f"<b>体量多 · 增速快</b>（存量、增速都高于中位）：{_bf}。",
                f"<b>Many · Fast</b> (both stock and growth speed above the medians): {_bf}."))
        _sf = _typical(_smallfast)
        if _sf:
            _q.append(t(
                f"<b>体量少 · 增速快</b>（存量低于中位、增速高于中位）：{_sf}。",
                f"<b>Few · Fast</b> (stock below median, growth speed above): {_sf}."))
        _bs = _typical(_bigslow)
        if _bs:
            _q.append(t(
                f"<b>体量多 · 增速慢</b>（存量高于中位、增速低于中位）：{_bs}。",
                f"<b>Many · Slow</b> (stock above median, growth speed below): {_bs}."))
        _ss = _typical(_smallslow)
        if _ss:
            _q.append(t(
                f"<b>体量少 · 增速慢</b>（存量、增速都低于中位）：{_ss}。",
                f"<b>Few · Slow</b> (both stock and growth speed below the medians): {_ss}."))
        insight_box(_q)

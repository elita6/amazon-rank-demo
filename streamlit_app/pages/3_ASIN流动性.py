# demo/streamlit_app/pages/ASIN流动性.py
# 更新日期：2026-06-01
# 用途：Demo 版 ASIN 流动性页（数据脱敏 + 5 类目）— ASIN 在榜时间与流动（跨类目对比）
# 启动：streamlit run demo/streamlit_app/产品概览.py
# 与生产版差异：
#   - 数据源从 v1/data/amazon.db 改为 demo/data/*.csv（in-memory sqlite，connect_demo）
#   - 类目缩减为 5（Category A ~ E）；品牌/ASIN 已匿名化，价格/评论数 ±5% 扰动
#   - 三榜在榜时间/满榜率/流动率对比表 + box plot 逻辑与生产版完全一致

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "streamlit_app"))
from _styles import inject_global_style, app_header, page_title, chart_title, conclusion, chart_spacer
from _demo_data import connect_demo


LIST_LABELS_3 = {"best_seller": "BS", "new_release": "NR", "movers_shakers": "MS"}
LIST_OPTIONS_3 = ["best_seller", "new_release", "movers_shakers"]


@st.cache_data
def load_data():
    conn = connect_demo()
    asin = pd.read_sql(
        "SELECT category, list_type, date, asin, brand, rank, "
        "price_low, review_count FROM asin_daily",
        conn,
    )
    summary = pd.read_sql("SELECT category, is_subcategory FROM category_summary", conn)
    conn.close()
    asin["date"] = pd.to_datetime(asin["date"])
    return asin, summary


def list_radio_3(label, key, default="best_seller"):
    return st.radio(
        label, options=LIST_OPTIONS_3,
        format_func=lambda k: LIST_LABELS_3[k],
        index=LIST_OPTIONS_3.index(default), horizontal=True, key=key,
        label_visibility="collapsed",
    )


WINDOW_OPTIONS = [7, 14]


def window_radio(key, default=14):
    """时间窗口切换器：7d / 14d。窗口取自数据集 max(date) 倒数 N 天滑窗。"""
    return st.radio(
        "时间窗口", options=WINDOW_OPTIONS,
        format_func=lambda n: f"近 {n} 天",
        index=WINDOW_OPTIONS.index(default), horizontal=True, key=key,
        label_visibility="collapsed",
    )


# =======================================================================
# 页面
# =======================================================================
st.set_page_config(page_title="ASIN 流动性", layout="wide", initial_sidebar_state="collapsed")
inject_global_style()
app_header()
page_title("ASIN 流动性")

# Demo banner
st.markdown(
    "<div style='background:#fff7ed; border-left:4px solid #f59e0b; "
    "padding:8px 14px; margin: 4px 0 10px 0; border-radius:4px; font-size:0.85rem; color:#7c2d12;'>"
    "🎭 <b>Demo Mode</b> — 节选 5 类目展示，品牌名/ASIN 已匿名化，价格/评论数 ±5% 扰动。"
    "</div>",
    unsafe_allow_html=True,
)

asin_all, summary = load_data()

# 默认排除子类目（仅看大类目跨类对比）
sub_set = set(summary[summary["is_subcategory"] == 1]["category"].tolist())
asin_all = asin_all[~asin_all["category"].isin(sub_set)]


# =======================================================================
# 单视角：ASIN 在榜时间与流动（跨类目对比）
# =======================================================================
with st.container(border=True):

    # 表标题占位（按钮渲染后回填动态文案）
    table_title_slot = st.empty()

    # 表筛选：只留窗口（stacked：label 上 / radio 下）
    fc1, _ = st.columns([1, 4])
    with fc1:
        st.markdown("<div class='filter-label'>📅 时间窗口</div>", unsafe_allow_html=True)
        v3_window = window_radio(key="v3_window", default=14)

    end_date = asin_all["date"].max()
    start_date = end_date - pd.Timedelta(days=v3_window - 1)

    # ---- 三榜各自计算 ASIN 在榜时间 + 流动率 ----
    def _compute_one(lt: str):
        df_lt = asin_all[(asin_all["list_type"] == lt)
                         & (asin_all["date"] >= start_date)
                         & (asin_all["date"] <= end_date)]
        if df_lt.empty:
            return None
        actual = int(df_lt["date"].nunique())
        life_lt = (df_lt.groupby(["category", "asin"])
                   .agg(life_days=("date", "nunique"))
                   .reset_index())
        s = (life_lt.groupby("category")
             .agg(n=("asin", "nunique"),
                  median_life=("life_days", "median"),
                  full_n=("life_days", lambda x: int((x == actual).sum())))
             .reset_index())
        s["full_rate"] = s["full_n"] / s["n"] * 100  # ×100 修 format 显示

        # 流动率
        rows = []
        for cat, sub in df_lt.groupby("category"):
            ds = (sub.groupby("date")["asin"].apply(set)
                  .reset_index().sort_values("date").reset_index(drop=True))
            prev = None
            for _, r in ds.iterrows():
                hc = len(r["asin"])
                if prev is None:
                    prev = r["asin"]
                    continue
                new_n = len(r["asin"] - prev)
                lost_n = len(prev - r["asin"])
                prev = r["asin"]
                if hc > 0:
                    rows.append({"category": cat,
                                 "rate": (new_n + lost_n) / 2 / hc * 100})
        flow = (pd.DataFrame(rows).groupby("category")["rate"].mean()
                if rows else pd.Series(dtype=float))
        s["flow_rate"] = s["category"].map(flow)
        return {"summary": s, "life": life_lt, "actual": actual}

    results = {lt: _compute_one(lt) for lt in LIST_OPTIONS_3}

    if all(r is None for r in results.values()):
        with table_title_slot.container():
            chart_title("类目对比表")
        st.warning("当前筛选下无数据")
    else:
        # ---- 拼 MultiIndex 宽表（BS/NR/MS 分组表头）----
        all_cats = sorted(set().union(
            *[set(r["summary"]["category"]) for r in results.values() if r]
        ))
        rows_data = []
        for cat in all_cats:
            row = [cat]
            for lt in ["best_seller", "new_release", "movers_shakers"]:
                r = results.get(lt)
                if r is None:
                    mlife = full_rate = flow_rate = pd.NA
                else:
                    cs = r["summary"][r["summary"]["category"] == cat]
                    if cs.empty:
                        mlife = full_rate = flow_rate = pd.NA
                    else:
                        mlife = cs["median_life"].iloc[0]
                        full_rate = cs["full_rate"].iloc[0]
                        flow_rate = cs["flow_rate"].iloc[0]
                if lt == "movers_shakers":
                    row.extend([mlife, flow_rate])  # MS 不出满榜率
                else:
                    row.extend([mlife, full_rate, flow_rate])
            rows_data.append(row)

        columns = pd.MultiIndex.from_tuples([
            ("", "类目"),
            ("BS", "中位在榜时间(天)"), ("BS", "满榜率"), ("BS", "流动率"),
            ("NR", "中位在榜时间(天)"), ("NR", "满榜率"), ("NR", "流动率"),
            ("MS", "中位在榜时间(天)"), ("MS", "流动率"),
        ])
        show = pd.DataFrame(rows_data, columns=columns)
        show = show.sort_values(("BS", "中位在榜时间(天)"),
                                ascending=False, na_position="last").reset_index(drop=True)

        # ---- shared maxes 跨榜 ----
        actual_max = max(r["actual"] for r in results.values() if r)
        flow_cols = [c for c in show.columns if c[1] == "流动率"]
        flow_vals = pd.concat([show[c].dropna() for c in flow_cols if not show[c].isna().all()],
                              ignore_index=True)
        flow_max_pct = max(float(flow_vals.max() or 0) * 1.1, 10.0) if not flow_vals.empty else 10.0

        window_caption = (f"近 {v3_window} 天" if actual_max == v3_window
                          else f"近 {v3_window} 天 · 实采 {actual_max} 天")

        # ============================================================
        # 类目对比表（自定义 HTML：分组表头 + 对角斜线类目头 + 数据条 + 组间粗竖线）
        # 原因：streamlit st.dataframe(styler) 不渲染 Styler.bar 的 CSS gradient
        # ============================================================
        with table_title_slot.container():
            chart_title(f"● 类目对比表 — 按 BS在榜中位时间降序（{window_caption}）")

        # 数据条 + 表格 HTML 渲染（每指标用 浅→深 渐变填充）
        BAR_GRADIENTS = {
            "中位在榜时间(天)": ("#cfe1f3", "#5b8fc4"),  # 浅蓝 → 深蓝
            "满榜率": ("#cfeedc", "#27ae60"),        # 浅绿 → 深绿
            "流动率": ("#fbe1c4", "#e67e22"),        # 浅橙 → 深橙
        }
        BORDER = "2px solid #aaa"   # 与表格分隔线同色
        GROUPS = [
            ("BS", ["中位在榜时间(天)", "满榜率", "流动率"]),
            ("NR", ["中位在榜时间(天)", "满榜率", "流动率"]),
            ("MS", ["中位在榜时间(天)", "流动率"]),
        ]

        def _cell_html(val, metric, first_in_group):
            cls_extra = " group-start" if first_in_group else ""
            cls_narrow = " col-narrow" if metric == "中位在榜时间(天)" else ""
            if pd.isna(val):
                return f'<td class="empty-cell{cls_extra}{cls_narrow}">—</td>'
            if metric == "中位在榜时间(天)":
                pct = min(val / actual_max * 100, 100) if actual_max > 0 else 0
                text = f"{val:.0f}"
            elif metric == "满榜率":
                pct = min(val, 100)
                text = f"{val:.1f}%"
            else:  # 流动率
                pct = min(val / flow_max_pct * 100, 100) if flow_max_pct > 0 else 0
                text = f"{val:.1f}%"
            light, dark = BAR_GRADIENTS[metric]
            # 深→浅渐变：bar 左侧深色（强调起点）→ 右侧浅色 → 透明
            bg = (f"background: linear-gradient(90deg, {dark} 0%, {light} {pct:.2f}%, "
                  f"transparent {pct:.2f}%);")
            return f'<td class="bar-cell{cls_extra}{cls_narrow}" style="{bg}">{text}</td>'

        parts = ['<table class="lifespan-cmp">', "<thead>", "<tr>"]
        # 对角斜线角头：左上→右下 \ 形，右上=榜单、左下=类目
        parts.append(
            '<th rowspan="2" class="corner-cell">'
            '<span class="corner-top">榜单</span>'
            '<svg viewBox="0 0 100 100" preserveAspectRatio="none">'
            '<line x1="0" y1="0" x2="100" y2="100" stroke="#aaa" stroke-width="0.8"/>'
            "</svg>"
            '<span class="corner-bot">类目</span>'
            "</th>"
        )
        for grp, metrics in GROUPS:
            parts.append(f'<th colspan="{len(metrics)}" class="group-start">{grp}</th>')
        parts.append("</tr>")

        # 第二行表头：指标
        parts.append("<tr>")
        for grp, metrics in GROUPS:
            for i, m in enumerate(metrics):
                cls_list = ["sub-h"]
                if i == 0:
                    cls_list.append("group-start")
                if m == "中位在榜时间(天)":
                    cls_list.append("col-narrow")
                parts.append(f'<th class="{" ".join(cls_list)}">{m}</th>')
        parts.append("</tr></thead><tbody>")

        # 数据行
        for _, row in show.iterrows():
            parts.append("<tr>")
            cat = row[("", "类目")]
            parts.append(f'<td class="cat-cell">{cat}</td>')
            for grp, metrics in GROUPS:
                for i, m in enumerate(metrics):
                    val = row[(grp, m)]
                    parts.append(_cell_html(val, m, first_in_group=(i == 0)))
            parts.append("</tr>")
        parts.append("</tbody></table>")

        css = f"""
<style>
.lifespan-cmp {{
    border-collapse: collapse;
    font-family: inherit;
    font-size: 13px;
    background: white;
    width: 100%;
    table-layout: auto;
}}
.lifespan-cmp thead th {{
    background-color: #f0f4f8;
    font-weight: 600;
    padding: 6px 10px;
    text-align: center;
    border-bottom: 1px solid #aaa;
    white-space: nowrap;
}}
.lifespan-cmp tbody td {{
    padding: 4px 10px;
    border-bottom: 1px solid #e8e8e8;
    text-align: right;
    font-variant-numeric: tabular-nums;
}}
.lifespan-cmp .group-start {{
    border-left: {BORDER} !important;
}}
.lifespan-cmp .corner-cell {{
    position: relative;
    min-width: 107px;     /* 160 × 2/3 ≈ 107，缩小 1/3 */
    width: 107px;
    height: 56px;
    background-color: #f0f4f8;
    padding: 0 !important;
}}
.lifespan-cmp .corner-cell svg {{
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    pointer-events: none;
}}
.lifespan-cmp .corner-top {{
    position: absolute;
    top: 4px; right: 10px;
    font-weight: 600;
    font-size: 12px;
}}
.lifespan-cmp .corner-bot {{
    position: absolute;
    bottom: 4px; left: 10px;
    font-weight: 600;
    font-size: 12px;
}}
.lifespan-cmp .col-narrow {{
    min-width: 78px;
    width: 78px;
}}
.lifespan-cmp .cat-cell {{
    font-weight: 500;
    text-align: left !important;
    white-space: nowrap;
    background-color: white !important;
}}
.lifespan-cmp .empty-cell {{
    color: #aaa;
    text-align: center !important;
}}
</style>
"""
        st.markdown(
            css + f'<div style="overflow-x: auto; max-width: 100%;">{"".join(parts)}</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f"<div style='font-size:0.68rem; color:#6b7280; line-height:1.7; margin-top:6px;'>"
            f"* 中位在榜时间：ASIN在窗口期内出现天数的中位数<br>"
            f"* 满榜率：在窗口期内一直在榜的 ASIN 占比<br>"
            f"* 流动率：每天平均有百分之几的 ASIN 被替换，比率越高说明榜单新陈代谢越快"
            f"</div>",
            unsafe_allow_html=True,
        )

        chart_spacer()
        # ============================================================
        # box plot — 独立筛选（榜单 + 窗口），与表解耦
        # 视觉：纵向（X=类目 / Y=在榜时间，与 v6.0 原始版一致）
        # 布局：标题在前 → 按钮 → 图（用 st.empty 占位先 reserve 标题位）
        # ============================================================
        title_slot = st.empty()  # 标题占位（在按钮渲染后回填动态文案）

        # 筛选行（stacked：label 上 / radio 下）
        bf1, bf2, _ = st.columns([1, 1, 3])
        with bf1:
            st.markdown("<div class='filter-label'>📊 榜单</div>", unsafe_allow_html=True)
            v3_box_list = list_radio_3("榜单", key="v3_box_list", default="best_seller")
        with bf2:
            st.markdown("<div class='filter-label'>📅 时间窗口</div>", unsafe_allow_html=True)
            v3_box_window = window_radio(key="v3_box_window", default=14)

        start_date_box = end_date - pd.Timedelta(days=v3_box_window - 1)
        df_box = asin_all[(asin_all["list_type"] == v3_box_list)
                          & (asin_all["date"] >= start_date_box)
                          & (asin_all["date"] <= end_date)]
        if df_box.empty:
            with title_slot.container():
                chart_title("● 各榜单ASIN在榜时间分布|按类目")
            st.warning("box plot 当前筛选下无数据")
        else:
            box_actual = int(df_box["date"].nunique())
            life_box = (df_box.groupby(["category", "asin"])
                        .agg(life_days=("date", "nunique")).reset_index())
            cat_order_box = (life_box.groupby("category")["life_days"].median()
                             .sort_values(ascending=False).index.tolist())
            box_window_caption = (f"近 {v3_box_window} 天" if box_actual == v3_box_window
                                  else f"近 {v3_box_window} 天 · 实采 {box_actual} 天")

            with title_slot.container():
                chart_title(f"● 各榜单ASIN在榜时间分布|按类目（{LIST_LABELS_3[v3_box_list]} · {box_window_caption}）")
            fig = px.box(life_box, x="category", y="life_days",
                         category_orders={"category": cat_order_box},
                         labels={"category": "", "life_days": "在榜时间"},
                         height=480)
            fig.update_traces(marker_color="#5b8fc4", line_color="#5b8fc4",
                              fillcolor="#a8cfee")
            fig.update_layout(
                margin=dict(l=10, r=10, t=10, b=80),
                xaxis=dict(tickangle=-30),
                yaxis=dict(dtick=max(1, box_actual // 7),
                           range=[0, box_actual + 0.5]),
            )
            st.plotly_chart(fig, width="stretch")


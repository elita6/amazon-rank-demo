# demo/streamlit_app/pages/品牌竞争.py
# 更新日期：2026-06-01
# 用途：Demo 版品牌竞争页（数据脱敏 + 5 类目）— 3 按钮切换（赛道全景 / 价格结构 / 组合分析）
# 启动：streamlit run demo/streamlit_app/产品概览.py
# 与生产版差异：
#   - 数据源从 v1/data/amazon.db 改为 demo/data/*.csv（in-memory sqlite，connect_demo）
#   - 类目缩减为 5（Category A ~ E）；品牌/ASIN 已匿名化，价格/评论数 ±5% 扰动
#   - 分析逻辑（集中度/经营形态/二维诊断/Treemap）与生产版完全一致

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "streamlit_app"))
from _styles import inject_global_style, app_header, page_title, chart_title, conclusion, chart_spacer
from _demo_data import connect_demo


TAG_COLOR = {
    "Top Pick":    "#27ae60",   # 绿（成熟优质 / 成长蓝海 / 新兴机会）
    "Hidden Gem":  "#9b59b6",   # 紫（高成长高波动）
    "Crowded":     "#e74c3c",   # 红（高热红海 — 盘子大但封闭）
    "Watch":       "#93A2D3",   # 蓝灰（稳态老品 / 新品潜力区 / 稳定现金流 / 高门槛利基）
    "Avoid":       "#8d949b",   # 灰（大盘冷门 / 低效开放 / 冷门封闭）
    "Excluded":    "#cbd5e1",   # 浅灰（v2.6 黑名单类目，如 Amazon Devices）
    "Subcategory": "#bdc3c7",
}

# -----------------------------------------------------------------------
# 数据加载
# -----------------------------------------------------------------------
@st.cache_data
def load_data():
    conn = connect_demo()
    asin = pd.read_sql(
        "SELECT category, list_type, date, asin, brand, price_low, review_count "
        "FROM asin_daily",
        conn,
    )
    summary = pd.read_sql(
        "SELECT category, composite_score, strategy_tag, est_monthly_gmv, "
        "is_subcategory, asin_retention_14d, brand_retention_14d "
        "FROM category_summary",
        conn,
    )
    conn.close()
    return asin, summary


# -----------------------------------------------------------------------
# 辅助函数
# -----------------------------------------------------------------------
def gini(values):
    v = np.asarray([x for x in values if x > 0], dtype=float)
    if len(v) <= 1 or v.sum() == 0:
        return 0.0
    v = np.sort(v)
    n = len(v)
    cum = np.cumsum(v)
    return (2 * np.sum(np.arange(1, n + 1) * v) - (n + 1) * cum[-1]) / (n * cum[-1])


def topn_share(values, n=1):
    v = np.asarray([x for x in values if x > 0], dtype=float)
    if v.sum() == 0:
        return 0.0
    v = np.sort(v)[::-1]
    return float(v[:n].sum() / v.sum())


def hhi_index(values):
    v = np.asarray([x for x in values if x > 0], dtype=float)
    if v.sum() == 0:
        return 0.0
    s = v / v.sum()
    return float(np.sum(s ** 2))


def compute_cat_metrics(brand_weight_df, weight_col):
    """统一函数：从「类目-品牌-权重」表算每类目集中度指标。
    weight_col: 用 'asin_count' (按 ASIN 数) 或 'sales_heat' (review×price)
    """
    rows = []
    for cat, grp in brand_weight_df.groupby("category"):
        weights = grp[weight_col].values
        n_brand = len(weights[weights > 0])
        rows.append({
            "category":  cat,
            "n_brand":   n_brand,
            "n_asin":    int(grp["asin_count"].sum()) if "asin_count" in grp.columns else None,
            "depth":     grp["asin_count"].sum() / n_brand if n_brand and "asin_count" in grp.columns else 0,
            "top1_pct":  topn_share(weights, 1),
            "cr3":       topn_share(weights, 3),
            "cr5":       topn_share(weights, 5),
            "hhi":       hhi_index(weights),
            "gini":      gini(weights),
        })
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------
# 页面
# -----------------------------------------------------------------------
st.set_page_config(page_title="品牌竞争", layout="wide", initial_sidebar_state="collapsed")
inject_global_style()
app_header()
page_title("品牌竞争")

# Demo banner
st.markdown(
    "<div style='background:#fff7ed; border-left:4px solid #f59e0b; "
    "padding:8px 14px; margin: 4px 0 10px 0; border-radius:4px; font-size:0.85rem; color:#7c2d12;'>"
    "🎭 <b>Demo Mode</b> — 节选 5 类目展示，品牌名/ASIN 已匿名化，价格/评论数 ±5% 扰动。"
    "</div>",
    unsafe_allow_html=True,
)

asin, summary = load_data()

# 排除子类目 + 锁定 BS 榜
sub_set = set(summary[summary["is_subcategory"] == 1]["category"].tolist())
filt_asin = asin[(asin["list_type"] == "best_seller") & (~asin["category"].isin(sub_set))].copy()
summary_main = summary[summary["is_subcategory"] != 1].copy()

# 观察窗口期（用于标题 / caption 标识；当前数据 = 14 天）
N_DAYS = filt_asin["date"].nunique() if not filt_asin.empty else 0
WIN_BADGE = f"BS · {N_DAYS}d 窗口"

st.caption(f"注：基于 **BS 榜** · 大类目 ·")

# 「类目-品牌-权重」基础表（含两种权重列）
bs_clean = filt_asin.dropna(subset=["brand"]).copy()
bs_clean["sales_heat_per_asin"] = (
    bs_clean["review_count"].fillna(0) * bs_clean["price_low"].fillna(0)
)
brand_weight = (
    bs_clean.groupby(["category", "brand"])
      .agg(asin_count=("asin", "nunique"),
           sales_heat=("sales_heat_per_asin", "sum"))
      .reset_index()
)

# 预算两种口径下的 cat_metrics
cat_metrics_count = compute_cat_metrics(brand_weight, "asin_count").merge(
    summary_main[["category", "composite_score", "strategy_tag", "est_monthly_gmv"]],
    on="category", how="left",
).sort_values("n_asin", ascending=True)

cat_metrics_sales = compute_cat_metrics(brand_weight, "sales_heat").merge(
    summary_main[["category", "composite_score", "strategy_tag", "est_monthly_gmv"]],
    on="category", how="left",
).sort_values("n_asin", ascending=True)


# -----------------------------------------------------------------------
# 3 按钮切换
# -----------------------------------------------------------------------
S2_VIEWS = {
    "track_panorama":   "赛道全景",
    "price_structure":  "价格结构",
    "combo":            "组合分析",
}
if "s2_view" not in st.session_state:
    st.session_state.s2_view = "track_panorama"
# 兼容旧 session_state 值（含 v3.5 已废弃的 conc_detail / conc_trend）
if st.session_state.s2_view in {"players", "conc_overview", "conc_detail", "conc_trend"}:
    st.session_state.s2_view = "track_panorama"

bcols = st.columns([1, 1, 1, 3])
for col, (vk, vlabel) in zip(bcols[:3], S2_VIEWS.items()):
    is_active = (st.session_state.s2_view == vk)
    if col.button(vlabel, key=f"s2_btn_{vk}",
                  type="primary" if is_active else "secondary",
                  use_container_width=True):
        st.session_state.s2_view = vk
        st.rerun()

chart_spacer()
view = st.session_state.s2_view


# =======================================================================
# 视图 A：赛道全景（合并原 玩家结构 + 集中度全景 + Treemap 下钻）
# 布局：① ASIN/品牌 bar  ② 集中度热力矩阵  ③ 竞争形态简表  ④ Treemap
# =======================================================================
if view == "track_panorama":

    # --- A.1 竞争结构热力矩阵（双口径 + 头部卡位难度 + 一致性 + 方向差异 + 竞争结构） ---
    with st.container(border=True):
        chart_title("● 竞争结构简表")

        # 展示 3 个指标（CR3 + HHI + 基尼），算法仅用 HHI + 基尼
        cols_for_display = ["cr3", "hhi", "gini"]
        cols_for_algo = ["hhi", "gini"]
        label_map = {
            "cr3":  "CR3",
            "hhi":  "HHI",
            "gini": "基尼",
        }

        def _normalize(df, cols):
            """缩尾 (5-95 分位) + min-max 归一化，避免极值压扁档位区分"""
            n = df.copy()
            for c in cols:
                col = n[c]
                lo, hi = col.quantile(0.05), col.quantile(0.95)
                clipped = col.clip(lo, hi)
                rng = hi - lo
                n[c] = (clipped - lo) / rng if rng > 0 else 0
            return n

        def _barrier_level(s):
            # BS 口径下"挤进 Top 100 的相对难度"，低端用"偏松/较松"避免"极易"误导
            if s >= 0.8:  return (4, "极难", "🔴")
            if s >= 0.6:  return (3, "难",   "🟠")
            if s >= 0.4:  return (2, "中等", "🟡")
            if s >= 0.2:  return (1, "偏松", "🟡")
            return (0, "较松", "🟢")

        df_c = cat_metrics_count[["category"] + cols_for_display].set_index("category")
        nc = _normalize(df_c, cols_for_display)
        # 算法只用 HHI + 基尼
        nc["barrier_score"] = nc[cols_for_algo].mean(axis=1)
        nc["barrier"] = nc["barrier_score"].apply(_barrier_level)
        nc["b_idx"] = nc["barrier"].apply(lambda b: b[0])
        nc["b_label"] = nc["barrier"].apply(lambda b: f"{b[2]} {b[1]}")
        # 档位 + 数值（单行紧凑：🟢 易(0.24)）
        nc["b_label_full"] = nc.apply(
            lambda r: f"{r['barrier'][2]} {r['barrier'][1]}({r['barrier_score']:.2f})",
            axis=1,
        )

        df_s = cat_metrics_sales[["category"] + cols_for_display].set_index("category")
        ns = _normalize(df_s, cols_for_display)
        ns["barrier_score"] = ns[cols_for_algo].mean(axis=1)
        ns["barrier"] = ns["barrier_score"].apply(_barrier_level)
        ns["b_idx"] = ns["barrier"].apply(lambda b: b[0])
        ns["b_label"] = ns["barrier"].apply(lambda b: f"{b[2]} {b[1]}")
        ns["b_label_full"] = ns.apply(
            lambda r: f"{r['barrier'][2]} {r['barrier'][1]}({r['barrier_score']:.2f})",
            axis=1,
        )

        common = nc.index.intersection(ns.index)
        # 类目排序：按销售口径入场难度降序（保持赛道全景统一顺序）
        order = ns.loc[common].sort_values("barrier_score", ascending=False).index.tolist()

        # 品牌竞争 9 标签（3 段 avg × 3 段 diff；阈值见 v1/other/品牌诊断规则）：
        #   高壁垒 (avg ≥ 0.80)：     强垄断   / 强势矩阵卡位 / 强势爆款主导
        #   中壁垒 (0.50 ≤ avg < 0.80)：竞争均衡 / 中度矩阵卡位 / 爆款主导
        #   低壁垒 (avg < 0.50)：     竞争分散 / 偏矩阵竞争  / 偏爆款竞争
        # diff 列：|diff| ≤ 0.10 一致 ；diff > 0.10 数量偏 ；diff < -0.10 销售偏
        DIFF_BIG = 0.10
        AVG_HIGH = 0.80
        AVG_MID = 0.50

        def _competition_tag(count_score, sales_score):
            diff = count_score - sales_score
            avg = (count_score + sales_score) / 2
            if avg >= AVG_HIGH:
                if abs(diff) <= DIFF_BIG:  return ("强垄断", 0.85)
                if diff > 0:               return ("强势矩阵卡位", 0.75)
                return ("强势爆款主导", 0.75)
            if avg >= AVG_MID:
                if abs(diff) <= DIFF_BIG:  return ("竞争均衡", 0.50)
                if diff > 0:               return ("中度矩阵卡位", 0.55)
                return ("爆款主导", 0.55)
            if abs(diff) <= DIFF_BIG:      return ("竞争分散", 0.20)
            if diff > 0:                   return ("偏矩阵竞争", 0.30)
            return ("偏爆款竞争", 0.30)

        def _consistency_mark(c):
            # 0.90 阈值对齐 DIFF_BIG=0.10：✔=一致路径，～/✗=方向差异路径
            if c >= 0.90: return ("✔", "#27ae60")   # 绿
            if c >= 0.75: return ("～", "#888888")  # 灰
            return ("✗", "#e74c3c")                 # 红

        diff_score_values = []        # 诊断函数内部需要 diff 符号判定矩阵/爆款方向
        consistency_values = []
        consistency_marks = []        # 一致性符号
        consistency_colors = []       # 一致性符号颜色
        avg_values = []               # 综合卡位难度数值
        avg_labels = []               # 综合卡位难度（emoji + 档位 + 数值）
        diag_labels = []              # 9 标签竞争结构
        diag_scores = []              # 竞争结构背景色权重
        for cat in order:
            cs = nc.loc[cat, "barrier_score"]
            ss = ns.loc[cat, "barrier_score"]
            diff = cs - ss
            cons = 1 - abs(diff)
            avg = (cs + ss) / 2
            diff_score_values.append(diff)
            consistency_values.append(cons)
            avg_values.append(avg)
            lvl = _barrier_level(avg)   # (idx, label, emoji)
            avg_labels.append(f"{lvl[2]}{lvl[1]}({avg:.2f})")
            mark, color = _consistency_mark(cons)
            consistency_marks.append(mark)
            consistency_colors.append(color)
            tag, score = _competition_tag(cs, ss)
            diag_labels.append(tag)
            diag_scores.append(score)

        # 列布局（共 12 列）：
        #   0-3 数量段 (CR3/HHI/基尼/数量卡位难度) | 4-7 销售段 | 8 一致性 | 9 综合卡位难度 | 10-11 竞争结构(占2列宽)
        all_x = (
            [label_map[c] for c in cols_for_display]
            + ["数量卡位难度"]
            + [label_map[c] + " " for c in cols_for_display]
            + ["销售卡位难度 "]
            + ["一致性"]
            + ["综合卡位难度"]
            + [" ", "  "]
        )

        z_rows = []
        text_rows = []
        for i, cat in enumerate(order):
            row_z = (
                [nc.loc[cat, c] for c in cols_for_display]
                + [nc.loc[cat, "barrier_score"]]
                + [ns.loc[cat, c] for c in cols_for_display]
                + [ns.loc[cat, "barrier_score"]]
                + [0.05]                                    # 一致性列：最浅蓝底，符号由 add_annotation 渲染
                + [avg_values[i]]                           # 综合卡位难度列：与卡位难度同色阶
                + [diag_scores[i], diag_scores[i]]         # 竞争结构同色背景重复 2 列
            )
            row_t = (
                [f"{df_c.loc[cat, c]:.2f}" for c in cols_for_display]
                + [nc.loc[cat, "b_label_full"]]            # 档位 + 数值
                + [f"{df_s.loc[cat, c]:.2f}" for c in cols_for_display]
                + [ns.loc[cat, "b_label_full"]]            # 档位 + 数值
                + [""]                                      # 一致性符号由 add_annotation 渲染
                + [avg_labels[i]]                           # 综合卡位难度（emoji + 档位 + 数值）
                + ["", ""]                                  # 竞争结构文字由 add_annotation 渲染
            )
            z_rows.append(row_z)
            text_rows.append(row_t)

        fig = go.Figure(data=go.Heatmap(
            z=z_rows,
            x=all_x,
            y=order,
            text=text_rows,
            texttemplate="%{text}",
            textfont=dict(size=10),
            colorscale="Blues",
            showscale=False,
        ))
        # 列布局：数量段(0-3) / 销售段(4-7) / 一致性(8) / 方向差异(9) / 竞争结构(10-11 占 2 列)
        # 分隔线
        fig.add_vline(x=3.5, line_color="#666", line_width=2)
        fig.add_vline(x=7.5, line_color="#666", line_width=2)   # 数据区与诊断区
        fig.add_vline(x=9.5, line_color="#999", line_width=1)   # 数值派生与标签派生之间

        # 顶部分组标题
        fig.add_annotation(
            x=1.5, y=1.10, yref="paper", xref="x",
            text="<b>📊 数量口径 (按 ASIN 数)</b>", showarrow=False,
            font=dict(size=12, color="#1e3a5f"),
        )
        fig.add_annotation(
            x=5.5, y=1.10, yref="paper", xref="x",
            text="<b>💰 销售口径 (按 review×price)</b>", showarrow=False,
            font=dict(size=12, color="#1e3a5f"),
        )
        fig.add_annotation(
            x=10.5, y=1.10, yref="paper", xref="x",
            text="<b>🔍 二维诊断</b>", showarrow=False,
            font=dict(size=12, color="#1e3a5f"),
        )

        # 一致性列：白底 + 着色符号（✔绿/～灰/✗红）+ 数值
        for i, cat in enumerate(order):
            fig.add_annotation(
                x=8, y=cat, xref="x", yref="y",
                text=(
                    f"<b><span style='color:{consistency_colors[i]}'>{consistency_marks[i]}</span></b>"
                    f" <span style='color:#1a2940'>{consistency_values[i]:.2f}</span>"
                ),
                showarrow=False,
                font=dict(size=10),
                xanchor="center", yanchor="middle",
            )

        # 竞争结构 cell 文字：跨 2 列居中（x=10.5 是竞争结构 2 列中心）
        for i, cat in enumerate(order):
            text_color = "white" if diag_scores[i] >= 0.7 else "#1a2940"
            fig.add_annotation(
                x=10.5, y=cat,
                xref="x", yref="y",
                text=diag_labels[i], showarrow=False,
                font=dict(size=10, color=text_color),
                xanchor="center", yanchor="middle",
            )

        # 自定义 axis tick：8 个数据列 + 一致性(x=8) + 综合卡位难度(x=9) + 竞争结构(x=10.5 双列中心)
        tick_positions = list(range(10)) + [10.5]
        tick_labels = (
            [label_map[c] for c in cols_for_display]
            + ["数量卡位难度"]
            + [label_map[c] for c in cols_for_display]
            + ["销售卡位难度"]
            + ["一致性"]
            + ["综合卡位难度"]
            + ["竞争结构"]
        )

        fig.update_layout(
            height=max(520, 36 * len(order)),
            margin=dict(l=10, r=10, t=70, b=10),
            xaxis=dict(
                side="top",
                tickfont=dict(size=10),
                tickmode="array",
                tickvals=tick_positions,
                ticktext=tick_labels,
            ),
            yaxis=dict(tickfont=dict(size=10)),
        )
        st.plotly_chart(fig, width="stretch")

    chart_spacer()

    # --- A.2 二维象限：方向差异 × 综合卡位难度（9 区域） ---
    with st.container(border=True):
        chart_title("● 竞争结构图谱")

        # 9 标签色板：3 列（一致/数量偏/销售偏）× 3 行（高/中/低 壁垒）
        # 一致系：红/灰/绿；数量系：深橙/橙/浅橙；销售系：深紫/紫/浅紫
        TAG_COLOR_MAP = {
            "强垄断":       "#c0392b",
            "强势矩阵卡位": "#d35400",
            "强势爆款主导": "#6c3483",
            "竞争均衡":     "#7f8c8d",
            "中度矩阵卡位": "#f39c12",
            "爆款主导":     "#9b59b6",
            "竞争分散":     "#27ae60",
            "偏矩阵竞争":   "#f8c471",
            "偏爆款竞争":   "#bb8fce",
        }

        scatter_df = pd.DataFrame({
            "category": order,
            "diff":     diff_score_values,
            "avg":      avg_values,
            "tag":      diag_labels,
        })

        # 动态 x 范围
        x_max = max(0.5, max(abs(d) for d in diff_score_values) * 1.15)

        fig_q = go.Figure()

        # 9 区域半透明背景（layer="below"）
        # 每行从左到右：销售偏 / 一致 / 数量偏
        regions = [
            # 高壁垒行 (y ≥ 0.80)
            dict(x0=-x_max, x1=-0.10, y0=0.80, y1=1.00, color=TAG_COLOR_MAP["强势爆款主导"]),
            dict(x0=-0.10,  x1=0.10,  y0=0.80, y1=1.00, color=TAG_COLOR_MAP["强垄断"]),
            dict(x0=0.10,   x1=x_max, y0=0.80, y1=1.00, color=TAG_COLOR_MAP["强势矩阵卡位"]),
            # 中壁垒行 (0.50 ≤ y < 0.80)
            dict(x0=-x_max, x1=-0.10, y0=0.50, y1=0.80, color=TAG_COLOR_MAP["爆款主导"]),
            dict(x0=-0.10,  x1=0.10,  y0=0.50, y1=0.80, color=TAG_COLOR_MAP["竞争均衡"]),
            dict(x0=0.10,   x1=x_max, y0=0.50, y1=0.80, color=TAG_COLOR_MAP["中度矩阵卡位"]),
            # 低壁垒行 (y < 0.50)
            dict(x0=-x_max, x1=-0.10, y0=0.00, y1=0.50, color=TAG_COLOR_MAP["偏爆款竞争"]),
            dict(x0=-0.10,  x1=0.10,  y0=0.00, y1=0.50, color=TAG_COLOR_MAP["竞争分散"]),
            dict(x0=0.10,   x1=x_max, y0=0.00, y1=0.50, color=TAG_COLOR_MAP["偏矩阵竞争"]),
        ]
        for r in regions:
            fig_q.add_shape(
                type="rect", xref="x", yref="y",
                x0=r["x0"], x1=r["x1"], y0=r["y0"], y1=r["y1"],
                fillcolor=r["color"], line=dict(width=0),
                opacity=0.10, layer="below",
            )

        # 9 区域标签（贴各区域左下角，避开散点 text 默认位置「散点正上方」）
        region_labels = [
            # 高壁垒行
            dict(text="强势爆款主导", x=-x_max + 0.02, y=0.84, anchor="left",
                 color=TAG_COLOR_MAP["强势爆款主导"]),
            dict(text="强垄断",       x=-0.08,          y=0.84, anchor="left",
                 color=TAG_COLOR_MAP["强垄断"]),
            dict(text="强势矩阵卡位", x=0.12,           y=0.84, anchor="left",
                 color=TAG_COLOR_MAP["强势矩阵卡位"]),
            # 中壁垒行
            dict(text="爆款主导",     x=-x_max + 0.02, y=0.54, anchor="left",
                 color=TAG_COLOR_MAP["爆款主导"]),
            dict(text="竞争均衡",     x=-0.08,          y=0.54, anchor="left",
                 color=TAG_COLOR_MAP["竞争均衡"]),
            dict(text="中度矩阵卡位", x=0.12,           y=0.54, anchor="left",
                 color=TAG_COLOR_MAP["中度矩阵卡位"]),
            # 低壁垒行
            dict(text="偏爆款竞争",   x=-x_max + 0.02, y=0.04, anchor="left",
                 color=TAG_COLOR_MAP["偏爆款竞争"]),
            dict(text="竞争分散",     x=-0.08,          y=0.04, anchor="left",
                 color=TAG_COLOR_MAP["竞争分散"]),
            dict(text="偏矩阵竞争",   x=0.12,           y=0.04, anchor="left",
                 color=TAG_COLOR_MAP["偏矩阵竞争"]),
        ]
        for rl in region_labels:
            fig_q.add_annotation(
                x=rl["x"], y=rl["y"], xref="x", yref="y",
                text=f"<b>{rl['text']}</b>", showarrow=False,
                font=dict(size=12, color=rl["color"]),
                opacity=0.65,
                xanchor=rl["anchor"], yanchor="middle",
            )

        # 散点（每个标签一个 trace，便于 legend 区分）
        for tag, color in TAG_COLOR_MAP.items():
            sub = scatter_df[scatter_df["tag"] == tag]
            if sub.empty:
                continue
            tpos = ["bottom center" if y > 0.92 else "top center" for y in sub["avg"]]
            fig_q.add_trace(go.Scatter(
                x=sub["diff"], y=sub["avg"],
                mode="markers+text",
                marker=dict(size=14, color=color, line=dict(width=1.5, color="white")),
                text=sub["category"], textposition=tpos,
                textfont=dict(size=9, color="#1a2940"),
                name=tag,
                cliponaxis=False,
                hovertemplate="<b>%{text}</b><br>方向差异 %{x:+.2f}"
                              "<br>综合卡位难度 %{y:.2f}<extra></extra>",
            ))

        fig_q.update_layout(
            height=640,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(title="方向差异（数量 − 销售 barrier_score）",
                       range=[-x_max, x_max]),
            yaxis=dict(title="综合卡位难度（数量 + 销售 barrier_score 平均）",
                       range=[0, 1]),
            showlegend=False,
        )
        st.plotly_chart(fig_q, width="stretch")

    chart_spacer()

    # --- A.3 经营形态简表 ---
    with st.container(border=True):
        chart_title("● 运营形态简表")

        # 类目级聚合
        cat_heat = (brand_weight.groupby("category")["sales_heat"].sum()
                    .rename("sales_heat_total").reset_index())
        cm = cat_metrics_count[["category", "n_brand", "n_asin"]].merge(
            cat_heat, on="category", how="left"
        ).merge(
            summary_main[["category", "brand_retention_14d"]],
            on="category", how="left",
        )
        cm["depth1"] = cm["n_asin"] / cm["n_brand"].replace(0, np.nan)
        cm["depth2"] = cm["sales_heat_total"] / cm["n_brand"].replace(0, np.nan) / 1e6  # M
        cm["sales_heat_M"] = cm["sales_heat_total"] / 1e6
        cm = cm.set_index("category")

        # 深度归一化：缩尾 (5-95 分位) + min-max（与上方集中度算法统一，消除 Amazon Devices 极值的压扁效应）
        def _winsor_minmax(s, lo_q=0.05, hi_q=0.95):
            lo, hi = s.quantile(lo_q), s.quantile(hi_q)
            clipped = s.clip(lo, hi)
            return (clipped - lo) / (hi - lo + 1e-9)

        cm["d1_norm"] = _winsor_minmax(cm["depth1"])
        cm["d2_norm"] = _winsor_minmax(cm["depth2"])

        # 密度分档（5 档，BS 口径下"低端"用偏低/较低 软化）
        def _density_level(s_norm):
            if s_norm >= 0.8:  return (4, "极高", "🔴")
            if s_norm >= 0.6:  return (3, "高",   "🟠")
            if s_norm >= 0.4:  return (2, "中",   "🟡")
            if s_norm >= 0.2:  return (1, "偏低", "🟡")
            return (0, "较低", "🟢")

        cm["d1_level"] = cm["d1_norm"].apply(_density_level)
        cm["d2_level"] = cm["d2_norm"].apply(_density_level)
        cm["d1_idx"] = cm["d1_level"].apply(lambda x: x[0])
        cm["d2_idx"] = cm["d2_level"].apply(lambda x: x[0])
        # 档位文字格式：emoji + 档位 + (归一化数值)，与头部卡位难度对齐
        cm["d1_label"] = cm.apply(
            lambda r: f"{r['d1_level'][2]} {r['d1_level'][1]}({r['d1_norm']:.2f})", axis=1
        )
        cm["d2_label"] = cm.apply(
            lambda r: f"{r['d2_level'][2]} {r['d2_level'][1]}({r['d2_norm']:.2f})", axis=1
        )

        # 派生指标：方向差异、综合经营密度、一致性
        cm["d_diff_score"] = cm["d1_norm"] - cm["d2_norm"]
        cm["d_avg"] = (cm["d1_norm"] + cm["d2_norm"]) / 2
        cm["d_cons_val"] = 1 - cm["d_diff_score"].abs()
        # 综合经营密度档位文字（emoji + 档位 + 数值；无空格）
        cm["d_avg_label"] = cm["d_avg"].apply(
            lambda v: f"{_density_level(v)[2]}{_density_level(v)[1]}({v:.2f})"
        )

        def _consistency_mark(c):
            # 0.90 阈值对齐 D_DIFF_BIG=0.10：✔=一致路径，～/✗=方向差异路径
            if c >= 0.90: return ("✔", "#27ae60")
            if c >= 0.75: return ("～", "#888888")
            return ("✗", "#e74c3c")

        # 9 标签经营形态（3 段 avg × 3 段 diff；阈值见 v1/other/品牌诊断规则）：
        #   高强度 (avg ≥ 0.80)：     头部全能型 / 头部矩阵型 / 头部精品型
        #   中强度 (0.50 ≤ avg < 0.80)：中坚均衡型 / 中坚矩阵型 / 中坚精品型
        #   低强度 (avg < 0.50)：     长尾轻量型 / 长尾铺货型 / 长尾爆品型
        # 留存率后缀：retention ≥ 0.85 → 🎯稳定；retention < 0.70 → 🔄高流动；其他 → 无
        D_DIFF_BIG = 0.10
        D_AVG_HIGH = 0.80
        D_AVG_MID = 0.50

        def _management_tag(row):
            d1, d2 = row["d1_norm"], row["d2_norm"]
            diff = d1 - d2
            avg = (d1 + d2) / 2
            if avg >= D_AVG_HIGH:
                if abs(diff) <= D_DIFF_BIG:  base, score = "头部全能型", 0.85
                elif diff > 0:               base, score = "头部矩阵型", 0.75
                else:                        base, score = "头部精品型", 0.75
            elif avg >= D_AVG_MID:
                if abs(diff) <= D_DIFF_BIG:  base, score = "中坚均衡型", 0.50
                elif diff > 0:               base, score = "中坚矩阵型", 0.55
                else:                        base, score = "中坚精品型", 0.55
            else:
                if abs(diff) <= D_DIFF_BIG:  base, score = "长尾轻量型", 0.20
                elif diff > 0:               base, score = "长尾铺货型", 0.30
                else:                        base, score = "长尾爆品型", 0.30

            ret = row.get("brand_retention_14d")
            if pd.notna(ret) and ret >= 0.85:
                suffix = " 🎯稳定"
            elif pd.notna(ret) and ret < 0.70:
                suffix = " 🔄高流动"
            else:
                suffix = ""
            return (base + suffix, score)

        cm["d_cons"] = cm.apply(lambda r: _management_tag(r)[0], axis=1)
        cm["d_cons_score"] = cm.apply(lambda r: _management_tag(r)[1], axis=1)

        # 复用上面的类目顺序 order
        cm_ord = cm.loc[order]

        # 列设计（12 列，对齐 A.1 集中度热力矩阵的 一致性 + 综合派生 + 标签 结构）：
        # 0:ASIN数 1:品牌数 2:销售热度 3:头部数量密度 4:数量密度档 5:头部销售密度 6:销售密度档
        # 7:留存率 8:一致性（z=0.05+annotation） 9:综合经营密度 10-11:经营形态（双列宽）
        cols_simple = ["n_asin", "n_brand", "sales_heat_M",
                       "depth1", "d1_label",
                       "depth2", "d2_label",
                       "brand_retention_14d",
                       "_consistency_placeholder",            # 一致性列：z=0.05，符号由 add_annotation 渲染
                       "d_avg",                                # 综合经营密度
                       "d_cons_score", "d_cons_score"]        # 经营形态（双列同色）
        cm_ord_d = cm_ord["d_cons"].tolist()
        cm_ord_d_score = cm_ord["d_cons_score"].tolist()
        cm_ord_d1_idx = cm_ord["d1_idx"].tolist()
        cm_ord_d2_idx = cm_ord["d2_idx"].tolist()
        cm_ord_d_cons = cm_ord["d_cons_val"].tolist()
        cm_ord_d_avg_label = cm_ord["d_avg_label"].tolist()

        z_simple = []
        text_simple = []
        for i, cat in enumerate(order):
            row_z = []
            row_t = []
            for j, c in enumerate(cols_simple):
                if c == "_consistency_placeholder":
                    row_z.append(0.05)
                    row_t.append("")   # 一致性由 add_annotation 渲染
                    continue
                v = cm_ord.loc[cat, c]
                if c == "d_cons_score":
                    row_z.append(v)
                    row_t.append("")
                elif c == "d_avg":
                    row_z.append(v)
                    row_t.append(cm_ord_d_avg_label[i])
                elif c == "brand_retention_14d":
                    row_z.append(v if pd.notna(v) else 0)
                    row_t.append(f"{v:.0%}" if pd.notna(v) else "—")
                elif c == "d1_label":
                    row_z.append(cm_ord_d1_idx[i] / 4)
                    row_t.append(v)
                elif c == "d2_label":
                    row_z.append(cm_ord_d2_idx[i] / 4)
                    row_t.append(v)
                else:
                    series = cm_ord[c]
                    rng = series.max() - series.min()
                    norm = (v - series.min()) / rng if rng > 0 else 0
                    row_z.append(norm)
                    if c in ("n_asin", "n_brand"):
                        row_t.append(f"{int(v)}")
                    elif c == "sales_heat_M":
                        row_t.append(f"{v:.1f}")
                    else:
                        row_t.append(f"{v:.2f}")
            z_simple.append(row_z)
            text_simple.append(row_t)

        fig = go.Figure(data=go.Heatmap(
            z=z_simple,
            x=list(range(12)),
            y=order,
            text=text_simple,
            texttemplate="%{text}",
            textfont=dict(size=10),
            colorscale="Greens",
            showscale=False,
        ))

        # 列分隔线
        fig.add_vline(x=7.5, line_color="#666", line_width=2)   # 数据区与诊断区
        fig.add_vline(x=9.5, line_color="#999", line_width=1)   # 数值派生与标签派生之间

        # 一致性列：白底 + 着色符号（✔绿/～灰/✗红）+ 数值
        for i, cat in enumerate(order):
            cons = cm_ord_d_cons[i]
            mark, color = _consistency_mark(cons)
            fig.add_annotation(
                x=8, y=cat, xref="x", yref="y",
                text=(
                    f"<b><span style='color:{color}'>{mark}</span></b>"
                    f" <span style='color:#1a2940'>{cons:.2f}</span>"
                ),
                showarrow=False,
                font=dict(size=10),
                xanchor="center", yanchor="middle",
            )

        # 经营形态文字：跨 2 列居中（x=10.5 = 列 10/11 的中心）
        for i, cat in enumerate(order):
            text_color = "white" if cm_ord_d_score[i] >= 0.7 else "#1a2940"
            fig.add_annotation(
                x=10.5, y=cat,
                xref="x", yref="y",
                text=cm_ord_d[i], showarrow=False,
                font=dict(size=10, color=text_color),
                xanchor="center", yanchor="middle",
            )
        # tick：8 个原始列 + 一致性(x=8) + 综合经营密度(x=9) + 经营形态(x=10.5 双列中心)
        tick_positions = list(range(10)) + [10.5]
        tick_labels = ["ASIN 数量", "品牌数量", "销售热度(M)",
                       "ASIN/品牌", "数量密度",
                       "销售/品牌(M)", "销售密度",
                       "品牌留存率", "一致性", "品牌综合密度", "运营形态"]
        fig.update_layout(
            height=max(480, 32 * len(order)),
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(
                side="top", tickfont=dict(size=10),
                tickmode="array", tickangle=0,
                tickvals=tick_positions, ticktext=tick_labels,
            ),
            yaxis=dict(tickfont=dict(size=10)),
        )
        st.plotly_chart(fig, width="stretch")

    chart_spacer()

    # --- A.4 经营形态二维象限：方向差异 × 综合经营密度（9 区域 + size=留存） ---
    with st.container(border=True):
        chart_title("● 运营形态图谱")
        st.caption("气泡大小 = 品牌留存率")

        # 9 标签色板（与经营形态 9 标签对应；色系跟 A.2 一致）
        MGMT_COLOR_MAP = {
            "头部全能型": "#c0392b",
            "头部矩阵型": "#d35400",
            "头部精品型": "#6c3483",
            "中坚均衡型": "#7f8c8d",
            "中坚矩阵型": "#f39c12",
            "中坚精品型": "#9b59b6",
            "长尾轻量型": "#27ae60",
            "长尾铺货型": "#f8c471",
            "长尾爆品型": "#bb8fce",
        }

        # 散点数据：去掉留存后缀作为 tag（着色用 base，hover 显示完整带后缀）
        def _strip_suffix(s):
            return s.split(" 🎯")[0].split(" 🔄")[0]

        mgmt_scatter = pd.DataFrame({
            "category": cm_ord.index.tolist(),
            "diff":     cm_ord["d_diff_score"].tolist(),
            "avg":      cm_ord["d_avg"].tolist(),
            "ret":      cm_ord["brand_retention_14d"].fillna(0.5).tolist(),
            "tag_full": cm_ord["d_cons"].tolist(),
        })
        mgmt_scatter["tag"] = mgmt_scatter["tag_full"].apply(_strip_suffix)

        x_max_m = max(0.5, max(abs(d) for d in mgmt_scatter["diff"]) * 1.15) if not mgmt_scatter.empty else 0.5

        fig_m = go.Figure()

        # 9 区域半透明背景
        regions_m = [
            # 高强度行 (y ≥ 0.80)
            dict(x0=-x_max_m, x1=-0.10, y0=0.80, y1=1.00, color=MGMT_COLOR_MAP["头部精品型"]),
            dict(x0=-0.10,    x1=0.10,  y0=0.80, y1=1.00, color=MGMT_COLOR_MAP["头部全能型"]),
            dict(x0=0.10,     x1=x_max_m, y0=0.80, y1=1.00, color=MGMT_COLOR_MAP["头部矩阵型"]),
            # 中强度行 (0.50 ≤ y < 0.80)
            dict(x0=-x_max_m, x1=-0.10, y0=0.50, y1=0.80, color=MGMT_COLOR_MAP["中坚精品型"]),
            dict(x0=-0.10,    x1=0.10,  y0=0.50, y1=0.80, color=MGMT_COLOR_MAP["中坚均衡型"]),
            dict(x0=0.10,     x1=x_max_m, y0=0.50, y1=0.80, color=MGMT_COLOR_MAP["中坚矩阵型"]),
            # 低强度行 (y < 0.50)
            dict(x0=-x_max_m, x1=-0.10, y0=0.00, y1=0.50, color=MGMT_COLOR_MAP["长尾爆品型"]),
            dict(x0=-0.10,    x1=0.10,  y0=0.00, y1=0.50, color=MGMT_COLOR_MAP["长尾轻量型"]),
            dict(x0=0.10,     x1=x_max_m, y0=0.00, y1=0.50, color=MGMT_COLOR_MAP["长尾铺货型"]),
        ]
        for r in regions_m:
            fig_m.add_shape(
                type="rect", xref="x", yref="y",
                x0=r["x0"], x1=r["x1"], y0=r["y0"], y1=r["y1"],
                fillcolor=r["color"], line=dict(width=0),
                opacity=0.10, layer="below",
            )

        # 9 区域标签（贴各区域左下）
        region_labels_m = [
            dict(text="头部精品型", x=-x_max_m + 0.02, y=0.84, color=MGMT_COLOR_MAP["头部精品型"]),
            dict(text="头部全能型", x=-0.08,            y=0.84, color=MGMT_COLOR_MAP["头部全能型"]),
            dict(text="头部矩阵型", x=0.12,             y=0.84, color=MGMT_COLOR_MAP["头部矩阵型"]),
            dict(text="中坚精品型", x=-x_max_m + 0.02, y=0.54, color=MGMT_COLOR_MAP["中坚精品型"]),
            dict(text="中坚均衡型", x=-0.08,            y=0.54, color=MGMT_COLOR_MAP["中坚均衡型"]),
            dict(text="中坚矩阵型", x=0.12,             y=0.54, color=MGMT_COLOR_MAP["中坚矩阵型"]),
            dict(text="长尾爆品型", x=-x_max_m + 0.02, y=0.04, color=MGMT_COLOR_MAP["长尾爆品型"]),
            dict(text="长尾轻量型", x=-0.08,            y=0.04, color=MGMT_COLOR_MAP["长尾轻量型"]),
            dict(text="长尾铺货型", x=0.12,             y=0.04, color=MGMT_COLOR_MAP["长尾铺货型"]),
        ]
        for rl in region_labels_m:
            fig_m.add_annotation(
                x=rl["x"], y=rl["y"], xref="x", yref="y",
                text=f"<b>{rl['text']}</b>", showarrow=False,
                font=dict(size=12, color=rl["color"]),
                opacity=0.65,
                xanchor="left", yanchor="middle",
            )

        # 散点：marker size = retention 映射 12-30 px
        # ret ∈ [0, 1]，min_size = 12, max_size = 30
        for tag, color in MGMT_COLOR_MAP.items():
            sub = mgmt_scatter[mgmt_scatter["tag"] == tag]
            if sub.empty:
                continue
            tpos = ["bottom center" if y > 0.92 else "top center" for y in sub["avg"]]
            sizes = [12 + r * 18 for r in sub["ret"]]
            fig_m.add_trace(go.Scatter(
                x=sub["diff"], y=sub["avg"],
                mode="markers+text",
                marker=dict(size=sizes, color=color, line=dict(width=1.5, color="white"),
                            sizemode="diameter"),
                text=sub["category"], textposition=tpos,
                textfont=dict(size=9, color="#1a2940"),
                name=tag,
                cliponaxis=False,
                customdata=sub[["ret", "tag_full"]].values,
                hovertemplate="<b>%{text}</b><br>方向差异 %{x:+.2f}"
                              "<br>综合经营密度 %{y:.2f}"
                              "<br>留存率 %{customdata[0]:.0%}"
                              "<br>形态 %{customdata[1]}<extra></extra>",
            ))

        fig_m.update_layout(
            height=760,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis=dict(title="方向差异（数量 − 销售密度归一化）",
                       range=[-x_max_m, x_max_m]),
            yaxis=dict(title="综合经营密度（数量 + 销售密度归一化平均）",
                       range=[0, 1]),
            showlegend=False,
        )
        st.plotly_chart(fig_m, width="stretch")

    chart_spacer()

    # --- A.5 Treemap 单类目下钻 ---
    with st.container(border=True):
        chart_title("Treemap：单类目内 Top15 品牌的 ASIN 占比（下钻）")
        cat_pick = st.selectbox(
            "选择类目下钻",
            sorted(brand_weight["category"].unique()),
            index=0, key="tm_cat_panorama",
        )
        sub = (brand_weight[brand_weight["category"] == cat_pick]
               .sort_values("asin_count", ascending=False).head(15))
        if sub.empty:
            st.warning("该类目无品牌数据")
        else:
            fig = px.treemap(
                sub, path=["brand"], values="asin_count",
                color="asin_count", color_continuous_scale="Oranges",
                height=460,
            )
            fig.update_traces(
                texttemplate="<b>%{label}</b><br>%{value} ASIN<br>%{percentRoot:.1%}",
                textfont=dict(size=12),
            )
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width="stretch")


# =======================================================================
# 视图 B：价格结构 — 品牌价格带分布（箱线图）
# =======================================================================
elif view == "price_structure":
    with st.container(border=True):
        chart_title("品牌价格带分布（每类目下品牌均价的箱线）")

        brand_price = (
            filt_asin.dropna(subset=["brand", "price_low"])
              .groupby(["category", "brand"])["price_low"].median()
              .reset_index(name="brand_med_price")
        )
        if brand_price.empty:
            st.warning("无品牌价格数据")
        else:
            sorted_data = brand_price.sort_values("category")

            fig = px.box(
                sorted_data,
                x="brand_med_price", y="category", orientation="h",
                height=620, points="outliers", log_x=True,
                labels={"brand_med_price": "品牌均价 (USD, 对数轴)", "category": ""},
            )
            fig.update_traces(marker=dict(color="#3d6fa0"), line=dict(color="#1e3a5f"))
            # 完整次刻度：1, 2, 5, 10, 20, 50, 100, 200, 500, 1000
            tick_vals = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
            fig.update_layout(
                margin=dict(l=10, r=10, t=20, b=10),
                xaxis=dict(
                    tickmode="array",
                    tickvals=tick_vals,
                    ticktext=[f"${v}" for v in tick_vals],
                ),
            )
            st.plotly_chart(fig, width="stretch")



# =======================================================================
# 视图 C：组合分析 — 类目综合对照表（汇总赛道全景 + 价格结构）
# =======================================================================
elif view == "combo":

    # ===== 双口径集中度归一化（同 A.1 算法）=====
    def _winsor_minmax(df, cols):
        n = df.copy()
        for c in cols:
            col = n[c]
            lo, hi = col.quantile(0.05), col.quantile(0.95)
            clipped = col.clip(lo, hi)
            rng = hi - lo
            n[c] = (clipped - lo) / rng if rng > 0 else 0
        return n

    cols_algo = ["hhi", "gini"]
    df_c = cat_metrics_count[["category"] + cols_algo].set_index("category")
    df_s = cat_metrics_sales[["category"] + cols_algo].set_index("category")
    nc_combo = _winsor_minmax(df_c, cols_algo)
    ns_combo = _winsor_minmax(df_s, cols_algo)
    nc_combo["barrier"] = nc_combo[cols_algo].mean(axis=1)
    ns_combo["barrier"] = ns_combo[cols_algo].mean(axis=1)

    # ===== 标签映射（与 A.1 / A.3 同源）=====
    def _barrier_emoji(s):
        if s >= 0.8: return ("🔴", "极难")
        if s >= 0.6: return ("🟠", "难")
        if s >= 0.4: return ("🟡", "中等")
        if s >= 0.2: return ("🟡", "偏松")
        return ("🟢", "较松")

    def _density_emoji(s):
        if s >= 0.8: return ("🔴", "极高")
        if s >= 0.6: return ("🟠", "高")
        if s >= 0.4: return ("🟡", "中")
        if s >= 0.2: return ("🟡", "偏低")
        return ("🟢", "较低")

    def _competition_tag(cs, ss):
        diff = cs - ss
        avg = (cs + ss) / 2
        if avg >= 0.80:
            if abs(diff) <= 0.10: return "强垄断"
            return "强势矩阵卡位" if diff > 0 else "强势爆款主导"
        if avg >= 0.50:
            if abs(diff) <= 0.10: return "竞争均衡"
            return "中度矩阵卡位" if diff > 0 else "爆款主导"
        if abs(diff) <= 0.10: return "竞争分散"
        return "偏矩阵竞争" if diff > 0 else "偏爆款竞争"

    def _management_tag(d1, d2, ret):
        diff = d1 - d2
        avg = (d1 + d2) / 2
        if avg >= 0.80:
            if abs(diff) <= 0.10: base = "头部全能型"
            elif diff > 0:        base = "头部矩阵型"
            else:                 base = "头部精品型"
        elif avg >= 0.50:
            if abs(diff) <= 0.10: base = "中坚均衡型"
            elif diff > 0:        base = "中坚矩阵型"
            else:                 base = "中坚精品型"
        else:
            if abs(diff) <= 0.10: base = "长尾轻量型"
            elif diff > 0:        base = "长尾铺货型"
            else:                 base = "长尾爆品型"
        if pd.notna(ret) and ret >= 0.85:    suffix = " 🎯稳定"
        elif pd.notna(ret) and ret < 0.70:   suffix = " 🔄高流动"
        else:                                 suffix = ""
        return base + suffix

    # ===== 经营形态聚合（同 A.3）=====
    cat_heat = (brand_weight.groupby("category")["sales_heat"].sum()
                .rename("sales_heat_total").reset_index())
    cm_combo = cat_metrics_count[["category", "n_brand", "n_asin"]].merge(
        cat_heat, on="category", how="left"
    ).merge(
        summary_main[["category", "brand_retention_14d"]], on="category", how="left",
    )
    cm_combo["depth1"] = cm_combo["n_asin"] / cm_combo["n_brand"].replace(0, np.nan)
    cm_combo["depth2"] = cm_combo["sales_heat_total"] / cm_combo["n_brand"].replace(0, np.nan) / 1e6

    def _wm_series(s, lo_q=0.05, hi_q=0.95):
        lo, hi = s.quantile(lo_q), s.quantile(hi_q)
        clipped = s.clip(lo, hi)
        return (clipped - lo) / (hi - lo + 1e-9)

    cm_combo["d1_norm"] = _wm_series(cm_combo["depth1"])
    cm_combo["d2_norm"] = _wm_series(cm_combo["depth2"])
    cm_combo = cm_combo.set_index("category")

    # ===== 价格结构（来自价格结构视图算法）=====
    brand_price = (
        filt_asin.dropna(subset=["brand", "price_low"])
          .groupby(["category", "brand"])["price_low"].median()
          .reset_index(name="brand_med_price")
    )
    price_stats = brand_price.groupby("category")["brand_med_price"].agg(
        price_med="median",
        price_p25=lambda s: s.quantile(0.25),
        price_p75=lambda s: s.quantile(0.75),
    )

    # ===== 组合表 =====
    rows = []
    for cat in nc_combo.index.intersection(ns_combo.index):
        cs = nc_combo.loc[cat, "barrier"]
        ss = ns_combo.loc[cat, "barrier"]
        avg_b = (cs + ss) / 2
        b_emo, b_lvl = _barrier_emoji(avg_b)
        comp_tag = _competition_tag(cs, ss)

        if cat in cm_combo.index:
            d1 = cm_combo.loc[cat, "d1_norm"]
            d2 = cm_combo.loc[cat, "d2_norm"]
            ret = cm_combo.loc[cat, "brand_retention_14d"]
        else:
            d1 = d2 = ret = np.nan

        if pd.notna(d1) and pd.notna(d2):
            avg_d = (d1 + d2) / 2
            de_emo, de_lvl = _density_emoji(avg_d)
            mgmt_tag = _management_tag(d1, d2, ret)
            density_str = f"{de_emo}{de_lvl}({avg_d:.2f})"
        else:
            mgmt_tag = "—"
            density_str = "—"

        if cat in price_stats.index:
            pm = price_stats.loc[cat, "price_med"]
            piqr = price_stats.loc[cat, "price_p75"] - price_stats.loc[cat, "price_p25"]
            price_med_str = f"${pm:.0f}"
            price_iqr_str = f"${piqr:.0f}"
        else:
            price_med_str = "—"
            price_iqr_str = "—"

        rows.append({
            "类目":         cat,
            "综合卡位难度": f"{b_emo}{b_lvl}({avg_b:.2f})",
            "_avg_sort":    avg_b,
            "竞争结构":     comp_tag,
            "综合经营密度": density_str,
            "经营形态":     mgmt_tag,
            "价格中位":     price_med_str,
            "价格 IQR":     price_iqr_str,
            "留存率":       f"{ret:.0%}" if pd.notna(ret) else "—",
        })

    combo_df = (pd.DataFrame(rows)
                .sort_values("_avg_sort", ascending=False)
                .drop(columns=["_avg_sort"])
                .reset_index(drop=True))

    with st.container(border=True):
        chart_title(f"类目综合对照表（{len(combo_df)} 个类目，按综合卡位难度降序）")
        st.dataframe(
            combo_df,
            hide_index=True,
            width="stretch",
            height=min(600, 38 + 36 * len(combo_df)),
        )


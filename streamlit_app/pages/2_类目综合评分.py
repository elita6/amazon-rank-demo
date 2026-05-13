# demo/streamlit_app/pages/1_类目综合评分.py
# 更新日期：2026-05-12
# 用途：Demo 版综合评分页（5 类目 + 5 strategy 全覆盖）
# 与生产版差异：
#   - 数据源 db → demo csv（in-memory sqlite）
#   - 默认权重 yaml inline（不依赖 scoring_config.yaml）
#   - Top 10 → Top 5（数据子集只有 5 类目）

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from _styles import inject_global_style, app_header, page_title, chart_title
from _demo_data import connect_demo


DIM_COLS = [
    "score_market_size",
    "score_openness",
    "score_new_product",
    "score_momentum",
    "score_stability",
]
DIM_LABELS = {
    "score_market_size":  "市场规模 (S)",
    "score_openness":     "市场开放度 (C)",
    "score_new_product":  "新品空间 (N)",
    "score_momentum":     "增长动能 (M)",
    "score_stability":    "结构稳定 (T)",
}
DIM_TOOLTIPS = {
    "score_market_size":  "偏好成熟大盘市场",
    "score_openness":     "偏好更容易进入的市场",
    "score_new_product":  "偏好新品成长机会",
    "score_momentum":     "偏好趋势和短期爆发",
    "score_stability":    "偏好稳定低波动市场",
}

# 业务校准的项目特定参数（非通用配方；其他数据集需重新校准）
# Layer 2 业务默认权重 — 生产版本通过 entropy + 业务约束二层加权得来
DEFAULT_WEIGHTS = {
    "score_market_size": 0.25,
    "score_openness":    0.25,
    "score_new_product": 0.20,
    "score_momentum":    0.15,
    "score_stability":   0.15,
}

# 4 套业务预设（trial-and-error 校准结果）
PRESETS = {
    "保守型": {"score_market_size": 0.30, "score_openness": 0.20, "score_new_product": 0.10, "score_momentum": 0.10, "score_stability": 0.30},
    "增长型": {"score_market_size": 0.15, "score_openness": 0.20, "score_new_product": 0.25, "score_momentum": 0.25, "score_stability": 0.15},
    "爆发型": {"score_market_size": 0.15, "score_openness": 0.20, "score_new_product": 0.25, "score_momentum": 0.35, "score_stability": 0.05},
    "默认":   DEFAULT_WEIGHTS,
}
# Tooltip 仅展示业务定位，不暴露具体权重数字（保留拖动 slider 时的真实交互）
PRESET_HELP = {
    "保守型": "重规模 + 稳定，低风险长期投入",
    "增长型": "重新品 + 动能 + 开放度",
    "爆发型": "重短期动能 + 新品爆发",
    "默认":   "业务默认配置",
}

TAG_COLOR = {
    "Top Pick":   "#27ae60",
    "Hidden Gem": "#9b59b6",
    "Crowded":    "#e74c3c",
    "Watch":      "#93A2D3",
    "Avoid":      "#8d949b",
}
TAG_ORDER = ["Top Pick", "Hidden Gem", "Crowded", "Watch", "Avoid"]

TIER_THRESHOLDS = [
    (0.80, "高潜机会类目"),
    (0.60, "优先关注类目"),
    (0.40, "中性观察类目"),
    (0.20, "谨慎评估类目"),
    (0.00, "低优先级类目"),
]
FLAG_TOP_PCT = 0.90
FLAG_BOTTOM_PCT = 0.10


@st.cache_data
def load_scoring():
    conn = connect_demo()
    df = pd.read_sql(
        "SELECT category, "
        "score_market_size, score_openness, score_new_product, "
        "score_momentum, score_stability, "
        "composite_score, is_pareto, tier, flag, archetype, strategy_tag, "
        "days_observed, est_monthly_gmv "
        "FROM category_summary "
        "WHERE COALESCE(is_subcategory,0)=0 "
        "  AND composite_score IS NOT NULL",
        conn,
    )
    return df


def assign_tier(scores):
    pct = scores.rank(pct=True)
    def to_tier(p):
        for thr, label in TIER_THRESHOLDS:
            if p >= thr:
                return label
        return TIER_THRESHOLDS[-1][1]
    return pct.apply(to_tier)


def assign_flag(scores):
    pct = scores.rank(pct=True)
    def to_flag(p):
        if p >= FLAG_TOP_PCT:
            return "Top Opportunity"
        if p <= FLAG_BOTTOM_PCT:
            return "High Risk"
        return "—"
    return pct.apply(to_flag)


def recompute(df, weights):
    w = pd.Series(weights)
    s = w.sum()
    w = w / s if s > 0 else pd.Series([1.0 / len(DIM_COLS)] * len(DIM_COLS), index=DIM_COLS)
    score = (df[DIM_COLS] * w[DIM_COLS].values).sum(axis=1)
    out = df.copy()
    out["composite_score"] = score
    out["tier"] = assign_tier(score)
    out["flag"] = assign_flag(score)
    return out


# -----------------------------------------------------------------------
# 页面
# -----------------------------------------------------------------------
st.set_page_config(page_title="类目综合评分 · Demo", layout="wide")
inject_global_style()
app_header()

st.markdown(
    "<div style='background:#fff7ed; border-left:4px solid #f59e0b; "
    "padding:8px 14px; margin: 4px 0 10px 0; border-radius:4px; font-size:0.85rem; color:#7c2d12;'>"
    "🎭 <b>Demo Mode</b> — 节选5类目作为展示（覆盖 5 种 strategy）  · "
    "完整版含 18 类目"
    "</div>",
    unsafe_allow_html=True,
)

page_title("类目综合评分")

df = load_scoring()
if df.empty:
    st.error("demo/data/category_summary.csv 没有评分数据")
    st.stop()

if st.session_state.get("_demo_p1_v") != 1:
    for _k in list(st.session_state.keys()):
        if _k.startswith("w_") or _k == "active_preset":
            del st.session_state[_k]
    st.session_state["_demo_p1_v"] = 1

if st.session_state.get("active_preset"):
    _ap = st.session_state["active_preset"]
    _target = PRESETS.get(_ap)
    if _target:
        for _c, _v in _target.items():
            _cur = st.session_state.get(f"w_{_c}")
            if _cur is not None and abs(float(_cur) - float(_v)) > 1e-6:
                st.session_state["active_preset"] = None
                break

st.markdown(
    """
    <style>
      [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stButton"] button,
      [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stButton"] button p {
          font-size: 0.60rem !important;
      }
      [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stButton"] button {
          padding: 3px 8px !important;
          min-height: 0 !important;
          line-height: 1.4 !important;
          width: 100% !important;
          position: relative !important;
          overflow: visible !important;
      }
      [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stButton"] button[kind="primary"]::after {
          content: "×";
          position: absolute;
          top: -6px;
          right: -6px;
          width: 14px;
          height: 14px;
          line-height: 12px;
          border-radius: 50%;
          background: #ffffff;
          color: #475569;
          font-size: 11px;
          font-weight: 700;
          text-align: center;
          border: 1px solid #cbd5e1;
          box-shadow: 0 1px 2px rgba(0,0,0,0.15);
          box-sizing: border-box;
          pointer-events: none;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("策略偏好设置")
    st.markdown(
        '<div style="color:#9ca3af; font-size:0.7rem; margin-top:-6px; margin-bottom:14px; line-height:1.3;">'
        '调整决策偏好，动态重算综合机会分'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="font-size:0.85rem; font-weight:600; color:#2c3e50; margin: 4px 0 16px 0;">快速预设</div>',
        unsafe_allow_html=True,
    )
    pcols = st.columns(4)
    active_preset = st.session_state.get("active_preset")
    for i, pname in enumerate(PRESETS.keys()):
        is_active = (active_preset == pname)
        with pcols[i]:
            btn_type = "primary" if is_active else "secondary"
            tip = PRESET_HELP[pname] + ("（再次点击取消）" if is_active else "")
            if st.button(pname, key=f"preset_{pname}", type=btn_type,
                         help=tip, use_container_width=True):
                if is_active:
                    st.session_state["active_preset"] = None
                else:
                    st.session_state["active_preset"] = pname
                    for c, v in PRESETS[pname].items():
                        st.session_state[f"w_{c}"] = v
                st.rerun()

    st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)

    weights = {}
    for c in DIM_COLS:
        weights[c] = st.slider(
            DIM_LABELS[c],
            0.0, 1.0,
            float(DEFAULT_WEIGHTS.get(c, 0.2)),
            0.01,
            key=f"w_{c}",
            help=DIM_TOOLTIPS[c],
        )

ranked = recompute(df, weights).sort_values("composite_score", ascending=False)

# KPI
n_total = len(ranked)
n_high = int((ranked["tier"] == "高潜机会类目").sum())
avg_score = ranked["composite_score"].mean()
crowded_pct = (ranked["strategy_tag"] == "Crowded").sum() / n_total if n_total > 0 else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("分析类目数", f"{n_total}")
k2.metric("高潜机会数", f"{n_high}", help="综合机会分 percentile ≥ 0.80")
k3.metric("平均综合分", f"{avg_score:.2f}")
k4.metric("Crowded 占比", f"{crowded_pct:.0%}", help="盘子大但开放度低的红海类目占比")

# 上半区 3 panel
top1, top2, top3 = st.columns([1.1, 1.6, 1.3])

with top1:
    chart_title("● 策略标签占比")
    tag_cnt = (ranked["strategy_tag"].value_counts()
               .reindex(TAG_ORDER).fillna(0).astype(int).reset_index())
    tag_cnt.columns = ["tag", "n"]
    fig = px.bar(tag_cnt, x="n", y="tag", orientation="h", text="n",
                 color="tag", color_discrete_map=TAG_COLOR, height=420)
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, yaxis_title=None, xaxis_title="类目数",
                      yaxis=dict(categoryorder="array", categoryarray=TAG_ORDER[::-1]),
                      margin=dict(l=10, r=20, t=10, b=10))
    st.plotly_chart(fig, width="stretch")

with top2:
    chart_title("● 策略矩阵：综合机会分 × 结构稳定")
    st.markdown(
        "<div style='font-size:0.70rem; color:#6b7280; font-weight:400; "
        "margin: -4px 0 8px 4px; line-height:1.3;'>"
        "气泡 = log1p 月 GMV M"
        "</div>",
        unsafe_allow_html=True,
    )
    plot_df = ranked.copy()
    plot_df["est_monthly_gmv_m"] = plot_df["est_monthly_gmv"].fillna(0) / 1_000_000.0
    plot_df["bubble_size"] = np.log1p(plot_df["est_monthly_gmv_m"].clip(lower=0))
    fig = px.scatter(
        plot_df,
        x="composite_score", y="score_stability",
        size="bubble_size", color="strategy_tag",
        color_discrete_map=TAG_COLOR,
        hover_name="category",
        custom_data=["est_monthly_gmv_m"],
        size_max=36, height=420,
        labels={"composite_score": "综合机会分 Opportunity Score",
                "score_stability": "结构稳定 StabilityScore"},
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "综合机会分：%{x:.2f}<br>"
            "结构稳定：%{y:.2f}<br>"
            "预估月 GMV：%{customdata[0]:.1f} M USD<extra></extra>"
        )
    )
    fig.add_vline(x=0.6, line_dash="dash", line_color="gray")
    fig.add_hline(y=0.6, line_dash="dash", line_color="gray")
    fig.add_annotation(x=0.95, y=0.95, text="目标区 (高分+稳)",
                       showarrow=False, font=dict(color="gray", size=11))
    fig.update_layout(legend_title_text="策略标签",
                      margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")

with top3:
    chart_title("● Top 3 综合分类目 · 5 维画像")
    top3_df = ranked.head(3)
    radar_dims = DIM_COLS
    radar_labels = [DIM_LABELS[d].split(" ")[0] for d in radar_dims]
    fig = go.Figure()
    palette = ["#27ae60", "#3498db", "#e67e22"]
    for i, (_, row) in enumerate(top3_df.iterrows()):
        vals = [row[d] for d in radar_dims]
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=radar_labels + [radar_labels[0]],
            fill="toself",
            name=row["category"],
            line=dict(color=palette[i], width=2),
            opacity=0.55,
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 1], showticklabels=True, tickfont=dict(size=9))),
        showlegend=True, height=420,
        legend=dict(orientation="v", yanchor="top", y=1.05, xanchor="left", x=0.0, font=dict(size=10)),
        margin=dict(l=40, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, width="stretch")

# 下半区 Top 5 综合分柱
chart_title("● Top 5 机会类目：综合分数 + 数据置信度（观察天数/14）")

top5 = ranked.head(5).copy()
top5["confidence"] = top5["days_observed"] / 14.0

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(
    go.Bar(
        x=top5["category"], y=top5["composite_score"],
        marker=dict(color=[TAG_COLOR.get(t, "#bbbbbb") for t in top5["strategy_tag"]]),
        name="综合分", text=top5["composite_score"].round(2), textposition="outside",
    ),
    secondary_y=False,
)
fig.add_trace(
    go.Scatter(
        x=top5["category"], y=top5["confidence"],
        mode="lines+markers",
        name="数据置信度", line=dict(color="#c0392b", width=2),
        marker=dict(size=10, symbol="diamond"),
    ),
    secondary_y=True,
)
fig.update_layout(
    height=380, hovermode="x unified",
    xaxis_tickangle=-25,
    margin=dict(l=10, r=10, t=10, b=80),
    legend=dict(orientation="h", y=1.05),
)
fig.update_yaxes(title_text="综合分", secondary_y=False, range=[0, 1.15])
fig.update_yaxes(title_text="置信度 (days/14)", secondary_y=True, range=[0, 1.05])

st.plotly_chart(fig, width="stretch")

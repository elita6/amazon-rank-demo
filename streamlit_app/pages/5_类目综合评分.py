# demo/streamlit_app/pages/1_类目综合评分.py
# 更新日期：2026-06-24
# 用途：Demo 版综合评分页（5 类目 + 5 strategy 全覆盖）
# 与生产版差异：
#   - 数据源 db → demo csv（in-memory sqlite）
#   - 默认权重 yaml inline（不依赖 scoring_config.yaml）
#   - Top 10 → Top 5（数据子集只有 5 类目）
# 主要改动：
#   - 2026-06-23：UI 文案中英双语化（包 t()）+ 配合 st.navigation 入口清理 set_page_config/header
#   - 2026-06-24：同步生产版 — strategy_tag 加 TAG_LABELS 显示映射（优选/隐形机会/竞争拥挤/
#                观察/不建议）、KPI「Crowded 占比」→「竞争拥挤占比」、散点轴去掉硬拼英文；
#                内部颜色键/比较仍用英文

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
from _styles import page_title, chart_title
from _i18n import t
from _demo_data import connect_demo


DIM_COLS = [
    "score_market_size",
    "score_openness",
    "score_new_product",
    "score_momentum",
    "score_stability",
]
DIM_LABELS = {
    "score_market_size":  t("市场规模 (S)", "Market Size (S)"),
    "score_openness":     t("市场开放度 (C)", "Openness (C)"),
    "score_new_product":  t("新品空间 (N)", "New-Product Room (N)"),
    "score_momentum":     t("增长动能 (M)", "Momentum (M)"),
    "score_stability":    t("结构稳定 (T)", "Stability (T)"),
}
DIM_TOOLTIPS = {
    "score_market_size":  t("偏好成熟大盘市场", "Favor large, mature markets"),
    "score_openness":     t("偏好更容易进入的市场", "Favor markets that are easier to enter"),
    "score_new_product":  t("偏好新品成长机会", "Favor new-product growth opportunities"),
    "score_momentum":     t("偏好趋势和短期爆发", "Favor trend and short-term momentum"),
    "score_stability":    t("偏好稳定低波动市场", "Favor stable, low-volatility markets"),
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
# 展示用映射（PRESETS 的键必须保持中文用于 session_state / 查找，按钮显示走此表）
PRESET_LABELS = {
    "保守型": t("保守型", "Safe"),
    "增长型": t("增长型", "Growth"),
    "爆发型": t("爆发型", "Bold"),
    "默认":   t("默认", "Default"),
}
# Tooltip 仅展示业务定位，不暴露具体权重数字（保留拖动 slider 时的真实交互）
PRESET_HELP = {
    "保守型": t("重规模 + 稳定，低风险长期投入", "Emphasizes size + stability, low-risk long-term play"),
    "增长型": t("重新品 + 动能 + 开放度", "Emphasizes new products + momentum + openness"),
    "爆发型": t("重短期动能 + 新品爆发", "Emphasizes short-term momentum + new-product breakout"),
    "默认":   t("业务默认配置", "Business default configuration"),
}

TAG_COLOR = {
    "Top Pick":   "#27ae60",
    "Hidden Gem": "#9b59b6",
    "Crowded":    "#e74c3c",
    "Watch":      "#93A2D3",
    "Avoid":      "#8d949b",
}
TAG_ORDER = ["Top Pick", "Hidden Gem", "Crowded", "Watch", "Avoid"]
# strategy_tag 数据值（英文，存于 csv）→ 显示名；内部比较/颜色键仍用英文，仅渲染时套用
TAG_LABELS = {
    "Top Pick":   t("优选", "Top Pick"),
    "Hidden Gem": t("隐形机会", "Hidden Gem"),
    "Crowded":    t("竞争拥挤", "Crowded"),
    "Watch":      t("观察", "Watch"),
    "Avoid":      t("不建议", "Avoid"),
}
# 颜色映射的「显示名」版本（供 px 用显示名上色时复用 TAG_COLOR 口径）
TAG_COLOR_LABEL = {TAG_LABELS[k]: v for k, v in TAG_COLOR.items()}

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
st.markdown(
    "<div style='background:#fff7ed; border-left:4px solid #f59e0b; "
    "padding:8px 14px; margin: 4px 0 10px 0; border-radius:4px; font-size:0.85rem; color:#7c2d12;'>"
    "🎭 <b>Demo Mode</b> — "
    + t("节选5类目作为展示（覆盖 5 种 strategy）。",
        "Showing 5 sampled categories (covering 5 strategy types). ")
    + "</div>",
    unsafe_allow_html=True,
)

page_title(t("类目综合评分", "Composite Score"))

df = load_scoring()
if df.empty:
    st.error(t("demo/data/category_summary.csv 没有评分数据",
               "No scoring data in demo/data/category_summary.csv"))
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
    st.header(t("策略偏好设置", "Strategy Preferences"))
    st.markdown(
        '<div style="color:#9ca3af; font-size:0.7rem; margin-top:-6px; margin-bottom:14px; line-height:1.3;">'
        + t("调整决策偏好，动态重算综合机会分",
            "Adjust your decision preferences to dynamically recompute the opportunity score")
        + '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="font-size:0.85rem; font-weight:600; color:#2c3e50; margin: 4px 0 16px 0;">'
        + t("快速预设", "Quick Presets")
        + '</div>',
        unsafe_allow_html=True,
    )
    pcols = st.columns(4)
    active_preset = st.session_state.get("active_preset")
    for i, pname in enumerate(PRESETS.keys()):
        is_active = (active_preset == pname)
        with pcols[i]:
            btn_type = "primary" if is_active else "secondary"
            tip = PRESET_HELP[pname] + (t("（再次点击取消）", " (click again to deselect)") if is_active else "")
            if st.button(PRESET_LABELS[pname], key=f"preset_{pname}", type=btn_type,
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
k1.metric(t("分析类目数", "Categories analyzed"), f"{n_total}")
k2.metric(t("高潜机会数", "High-potential count"), f"{n_high}",
          help=t("综合机会分 percentile ≥ 0.80", "Opportunity score percentile ≥ 0.80"))
k3.metric(t("平均综合分", "Avg composite score"), f"{avg_score:.2f}")
k4.metric(t("竞争拥挤占比", "Crowded share"), f"{crowded_pct:.0%}",
          help=t("盘子大但开放度低的红海类目占比",
                 "Share of large but low-openness red-ocean categories"))

# 上半区 3 panel
top1, top2, top3 = st.columns([1.1, 1.6, 1.3])

with top1:
    chart_title(t("● 策略标签占比", "● Strategy Tag Mix"))
    tag_cnt = (ranked["strategy_tag"].value_counts()
               .reindex(TAG_ORDER).fillna(0).astype(int).reset_index())
    tag_cnt.columns = ["tag", "n"]
    tag_cnt["tag_label"] = tag_cnt["tag"].map(TAG_LABELS)
    fig = px.bar(tag_cnt, x="n", y="tag_label", orientation="h", text="n",
                 color="tag", color_discrete_map=TAG_COLOR, height=420)
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, yaxis_title=None, xaxis_title=t("类目数", "Categories"),
                      yaxis=dict(categoryorder="array",
                                 categoryarray=[TAG_LABELS[x] for x in TAG_ORDER[::-1]]),
                      margin=dict(l=10, r=20, t=10, b=10))
    st.plotly_chart(fig, width="stretch")

with top2:
    chart_title(t("● 策略矩阵：综合机会分 × 结构稳定", "● Strategy Matrix: Opportunity Score × Stability"))
    st.markdown(
        "<div style='font-size:0.70rem; color:#6b7280; font-weight:400; "
        "margin: -4px 0 8px 4px; line-height:1.3;'>"
        + t("气泡 = log1p 月 GMV M", "Bubble = log1p monthly GMV ($M)")
        + "</div>",
        unsafe_allow_html=True,
    )
    plot_df = ranked.copy()
    plot_df["est_monthly_gmv_m"] = plot_df["est_monthly_gmv"].fillna(0) / 1_000_000.0
    plot_df["bubble_size"] = np.log1p(plot_df["est_monthly_gmv_m"].clip(lower=0))
    plot_df["strategy_tag_label"] = plot_df["strategy_tag"].map(TAG_LABELS)
    fig = px.scatter(
        plot_df,
        x="composite_score", y="score_stability",
        size="bubble_size", color="strategy_tag_label",
        color_discrete_map=TAG_COLOR_LABEL,
        hover_name="category",
        custom_data=["est_monthly_gmv_m"],
        size_max=36, height=420,
        labels={"composite_score": t("综合机会分", "Opportunity Score"),
                "score_stability": t("结构稳定", "Stability Score")},
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            + t("综合机会分：", "Opportunity Score: ") + "%{x:.2f}<br>"
            + t("结构稳定：", "Stability: ") + "%{y:.2f}<br>"
            + t("预估月 GMV：", "Est. monthly GMV: ") + "%{customdata[0]:.1f} M USD<extra></extra>"
        )
    )
    fig.add_vline(x=0.6, line_dash="dash", line_color="gray")
    fig.add_hline(y=0.6, line_dash="dash", line_color="gray")
    fig.add_annotation(x=0.95, y=0.95, text=t("目标区 (高分+稳)", "Target zone (high score + stable)"),
                       showarrow=False, font=dict(color="gray", size=11))
    fig.update_layout(legend_title_text=t("策略标签", "Strategy Tag"),
                      margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")

with top3:
    chart_title(t("● Top 3 综合分类目 · 5 维画像", "● Top 3 Categories · 5-Factor Profile"))
    top3_df = ranked.head(3)
    radar_dims = DIM_COLS
    # 去掉末尾的 " (X)" 缩写后缀，中英文均适用（中文取前段，英文保留完整词组）
    radar_labels = [DIM_LABELS[d].rsplit(" (", 1)[0] for d in radar_dims]
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
chart_title(t("● Top 5 机会类目：综合分数 + 数据置信度（观察天数/14）",
              "● Top 5 Opportunity Categories: Composite Score + Data Confidence (days observed / 14)"))

top5 = ranked.head(5).copy()
top5["confidence"] = top5["days_observed"] / 14.0

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(
    go.Bar(
        x=top5["category"], y=top5["composite_score"],
        marker=dict(color=[TAG_COLOR.get(tag, "#bbbbbb") for tag in top5["strategy_tag"]]),
        name=t("综合分", "Composite Score"), text=top5["composite_score"].round(2), textposition="outside",
    ),
    secondary_y=False,
)
fig.add_trace(
    go.Scatter(
        x=top5["category"], y=top5["confidence"],
        mode="lines+markers",
        name=t("数据置信度", "Data Confidence"), line=dict(color="#c0392b", width=2),
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
fig.update_yaxes(title_text=t("综合分", "Composite Score"), secondary_y=False, range=[0, 1.15])
fig.update_yaxes(title_text=t("置信度 (days/14)", "Confidence (days/14)"), secondary_y=True, range=[0, 1.05])

st.plotly_chart(fig, width="stretch")

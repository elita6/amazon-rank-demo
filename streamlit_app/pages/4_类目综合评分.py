# streamlit_app/pages/4_类目综合评分.py
# 更新日期：2026-06-29
# 用途：类目综合评分（Demo 版，对齐生产 v2 布局）— 横向比较页。
#       上：优先级类型分布树状图（全宽）；下：左 Top10 机会类目横向条形 + 右 Top3 五维雷达。
#       侧边栏 4 个权重预设 + 5 维滑块，动态重算综合分 / 优先级类型(Tier) / Flag。
# 启动命令：streamlit run streamlit_app/产品概览.py
# 与生产 v2 差异：
#   - 数据源 data/amazon.db → data/*.csv（connect_demo）；类目已匿名化（Category A~E）
#   - 默认权重：生产 v2 从 config/scoring_config.yaml 读取；Demo 无 config 目录，直接内联
#     DEFAULT_WEIGHTS = A0.25 / C0.25 / N0.20 / M0.15 / T0.15（与 v2 dimension_weights 一致）
# 主要改动：
#   - 2026-06-29（文案同步生产 v2）：各维度「衡量什么」改为问句式——市场吸引力=有没有市场？/
#       市场开放度=能不能进入？/新品空间=新品能不能成长？/增长动能=有没有正在上升的产品？/
#       结构稳定=市场波动性大不大？（中英同步）。不动计算口径。
#   - 2026-06-28：从生产 v2 pages/4_类目综合评分.py 移植（树状图 + Top10 横向条形 + Top3 雷达；
#       各项评分说明 expander；权重预设 + 滑块动态重算）

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "streamlit_app"))
from _styles import page_title, chart_title, insight_box
from _i18n import t
from _demo_data import connect_demo

# 默认权重（= 生产 v2 config/scoring_config.yaml dimension_weights；Demo 内联，无 yaml 依赖）
DEFAULT_WEIGHTS = {
    "score_market_size": 0.25,
    "score_openness":    0.25,
    "score_new_product": 0.20,
    "score_momentum":    0.15,
    "score_stability":   0.15,
}

DIM_COLS = [
    "score_market_size",
    "score_openness",
    "score_new_product",
    "score_momentum",
    "score_stability",
]
DIM_LABELS = {
    "score_market_size":  t("市场吸引力 (A)", "Market Attractiveness (A)"),
    "score_openness":     t("市场开放度 (C)", "Openness (C)"),
    "score_new_product":  t("新品空间 (N)", "New-Product Room (N)"),
    "score_momentum":     t("增长动能 (M)", "Momentum (M)"),
    "score_stability":    t("结构稳定 (T)", "Stability (T)"),
}
DIM_TOOLTIPS = {
    "score_market_size":  t("偏好需求强、客单价高的吸引力市场", "Favor markets with strong demand and high price points"),
    "score_openness":     t("偏好更容易进入的市场", "Favor markets that are easier to enter"),
    "score_new_product":  t("偏好新品成长机会", "Favor new-product growth opportunities"),
    "score_momentum":     t("偏好趋势和短期爆发", "Favor trend and short-term momentum"),
    "score_stability":    t("偏好稳定低波动市场", "Favor stable, low-volatility markets"),
}
# 策略偏好预设；"默认" 用 DEFAULT_WEIGHTS 填入
PRESETS = {
    "保守型": {"score_market_size": 0.30, "score_openness": 0.20, "score_new_product": 0.10, "score_momentum": 0.10, "score_stability": 0.30},
    "增长型": {"score_market_size": 0.15, "score_openness": 0.20, "score_new_product": 0.25, "score_momentum": 0.25, "score_stability": 0.15},
    "爆发型": {"score_market_size": 0.15, "score_openness": 0.20, "score_new_product": 0.25, "score_momentum": 0.35, "score_stability": 0.05},
    "默认": None,  # 由 load_default_weights() 填入
}
PRESET_LABELS = {
    "保守型": t("保守型", "Safe"),
    "增长型": t("增长型", "Growth"),
    "爆发型": t("爆发型", "Bold"),
    "默认":   t("默认", "Default"),
}
PRESET_HELP = {
    "保守型": t("A 0.30 / T 0.30 / C 0.20 / N 0.10 / M 0.10 — 重吸引力 + 稳定，低风险长期投入",
               "A 0.30 / T 0.30 / C 0.20 / N 0.10 / M 0.10 — emphasizes attractiveness + stability, low-risk long-term play"),
    "增长型": t("N 0.25 / M 0.25 / C 0.20 / A 0.15 / T 0.15 — 重新品 + 动能 + 开放度",
               "N 0.25 / M 0.25 / C 0.20 / A 0.15 / T 0.15 — emphasizes new products + momentum + openness"),
    "爆发型": t("M 0.35 / N 0.25 / C 0.20 / A 0.15 / T 0.05 — 重短期动能 + 新品爆发",
               "M 0.35 / N 0.25 / C 0.20 / A 0.15 / T 0.05 — emphasizes short-term momentum + new-product breakout"),
    "默认":   t("A 0.25 / C 0.25 / N 0.20 / M 0.15 / T 0.15 — 业务默认",
               "A 0.25 / C 0.25 / N 0.20 / M 0.15 / T 0.15 — business default"),
}

# 优先级类型（=Tier，Overall Rating）：5 档配色 + 顺序 + 展示简称
TIER_COLOR = {
    "高潜机会类目": "#27ae60",  # 绿（最优）
    "较高机会类目": "#9b59b6",  # 紫
    "中性观察类目": "#93A2D3",  # 蓝灰
    "谨慎评估类目": "#e74c3c",  # 红（警示）
    "暂不考虑类目": "#8d949b",  # 灰（最不重要）
}
TIER_ORDER = ["高潜机会类目", "较高机会类目", "中性观察类目", "谨慎评估类目", "暂不考虑类目"]
TIER_LABEL = {  # 占比图/柱图展示用简称
    "高潜机会类目": t("高潜机会", "Top"),
    "较高机会类目": t("较高机会", "High"),
    "中性观察类目": t("中性观察", "Balanced"),
    "谨慎评估类目": t("谨慎评估", "Watch"),
    "暂不考虑类目": t("暂不考虑", "Skip"),
}

# Tier 阈值（= scoring_config.yaml tier_thresholds）
TIER_THRESHOLDS = [
    (0.80, "高潜机会类目"),
    (0.60, "较高机会类目"),
    (0.40, "中性观察类目"),
    (0.20, "谨慎评估类目"),
    (0.00, "暂不考虑类目"),
]
FLAG_TOP_PCT = 0.90
FLAG_BOTTOM_PCT = 0.10


@st.cache_data
def load_default_weights():
    """默认权重（= 生产 v2 dimension_weights，Demo 内联）"""
    return dict(DEFAULT_WEIGHTS)


@st.cache_data
def load_scoring():
    """从 category_summary 读评分。
    过滤：仅主类目（is_subcategory=0），且评分非 NULL。
    """
    conn = connect_demo()
    df = pd.read_sql(
        "SELECT category, "
        "score_market_size, score_openness, score_new_product, "
        "score_momentum, score_stability, "
        "composite_score, is_pareto, tier, flag, "
        "days_observed "
        "FROM category_summary "
        "WHERE COALESCE(is_subcategory,0)=0 "
        "  AND composite_score IS NOT NULL",
        conn,
    )
    if df.empty:
        return None, None
    return df, "category_summary"


def assign_tier(scores: pd.Series) -> pd.Series:
    pct = scores.rank(pct=True)
    def to_tier(p):
        for thr, label in TIER_THRESHOLDS:
            if p >= thr:
                return label
        return TIER_THRESHOLDS[-1][1]
    return pct.apply(to_tier)


def assign_flag(scores: pd.Series) -> pd.Series:
    pct = scores.rank(pct=True)
    def to_flag(p):
        if p >= FLAG_TOP_PCT:
            return "Top Opportunity"
        if p <= FLAG_BOTTOM_PCT:
            return "High Risk"
        return "—"
    return pct.apply(to_flag)


def recompute(df, weights):
    """按权重重算 composite_score + tier(=Overall Rating) + flag；保持原始分（不 min-max）。"""
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
page_title(t("类目综合评分", "Composite Score"))

df, source_name = load_scoring()
if df is None:
    st.error(t("category_summary 没有评分数据", "No scoring data in category_summary."))
    st.stop()

# 页面副标题
st.markdown(
    "<div style='color:#6b7280; font-size:0.85rem; margin: 4px 0 16px 0;'>"
    + t("注：Demo 数据已匿名化（Category A~E）",
        "Note: demo data is anonymized (Category A~E)")
    + "</div>",
    unsafe_allow_html=True,
)

# 各项评分「衡量什么」的直白说明（默认展开，只说衡量什么，不写计算公式/字段）
with st.expander(t("ℹ️ 各项评分衡量什么", "ℹ️ What each score measures"), expanded=True):
    st.markdown(
        "<div style='font-size:0.8rem; color:#4b5563; line-height:1.7;'>"
        + "<b>" + t("综合机会分", "Composite Score") + "</b> — "
        + t("基于市场吸引力、市场开放度、新品空间、增长动能、结构稳定 5 个维度构建评分模型，用来给类目排优先级，分越高越值得优先考虑。",
            "a scoring model built on five dimensions (market attractiveness, openness, new-product room, momentum, stability) to rank category priority; higher means more worth prioritizing.")
        + "<br><b>" + t("市场吸引力", "Market Attractiveness") + "</b> — "
        + t("有没有市场？", "Is there a market?")
        + "<br><b>" + t("市场开放度", "Openness") + "</b> — "
        + t("能不能进入？", "Can you get in?")
        + "<br><b>" + t("新品空间", "New-Product Room") + "</b> — "
        + t("新品能不能成长？", "Can new products grow?")
        + "<br><b>" + t("增长动能", "Momentum") + "</b> — "
        + t("有没有正在上升的产品？", "Are products on the rise?")
        + "<br><b>" + t("结构稳定", "Stability") + "</b> — "
        + t("市场波动性大不大？", "How volatile is the market?")
        + "</div>",
        unsafe_allow_html=True,
    )

default_w = load_default_weights()
PRESETS["默认"] = default_w  # 默认权重 → 最后一个 preset 按钮

# 防止 hot reload / 旧 session 残留导致按钮误高亮（bump 版本号时强制清 active + 所有 w_*）
if st.session_state.get("_page4b_v") != 1:
    for _k in list(st.session_state.keys()):
        if _k.startswith("w_") or _k == "active_preset":
            del st.session_state[_k]
    st.session_state["_page4b_v"] = 1

# 检测：如果 active preset 跟当前 weights 不再匹配（用户拖了 slider），自动取消激活
if st.session_state.get("active_preset"):
    _ap = st.session_state["active_preset"]
    _target = PRESETS.get(_ap)
    if _target:
        for _c, _v in _target.items():
            _cur = st.session_state.get(f"w_{_c}")
            if _cur is not None and abs(float(_cur) - float(_v)) > 1e-6:
                st.session_state["active_preset"] = None
                break

# 预设按钮字号 + active 按钮右上角 × badge（::after 伪元素，相对 button 定位绝对不会跑）
st.markdown(
    """
    <style>
      /* 4 个 preset 按钮字号 + 撑满 column */
      [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stButton"] button,
      [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stButton"] button p {
          font-size: 0.60rem !important;
      }
      [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stButton"] button {
          padding: 3px 8px !important;
          min-height: 0 !important;
          line-height: 1.4 !important;
          width: 100% !important;
          position: relative !important;   /* 让 ::after 锚到 button 自己 */
          overflow: visible !important;     /* 让 ::after 突出按钮边界 */
      }

      /* active 按钮（kind=primary）右上角 × badge — close badge 风格 */
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

# --- 侧边栏：模型权重设置 ---
with st.sidebar:
    st.header(t("模型权重设置", "Model Weight Settings"))
    st.markdown(
        '<div style="color:#9ca3af; font-size:0.7rem; margin-top:-6px; margin-bottom:14px; line-height:1.3;">'
        + t("调整权重偏好，动态计算类目综合机会分",
            "Adjust weight preferences to dynamically compute the category opportunity score")
        + '</div>',
        unsafe_allow_html=True,
    )

    # 4 个快速预设；激活态主按钮 primary 高亮 + X 浮到 column 右上角（CSS 绝对定位）
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
                    # 再次点击 active 按钮 = 取消激活
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
            float(default_w.get(c, 0.2)),
            0.01,
            key=f"w_{c}",
            help=DIM_TOOLTIPS[c],
        )
    total = sum(weights.values())
    st.metric(t("权重总和（自动归一化）", "Weight Sum (auto-normalized)"), f"{total:.2f}")

ranked = recompute(df, weights).sort_values("composite_score", ascending=False)

# -----------------------------------------------------------------------
# 派生量（n_total / avg_score 用于 Top10 基准虚线）
# -----------------------------------------------------------------------
n_total = len(ranked)
avg_score = ranked["composite_score"].mean()      # 全部类目综合分均分 → Top10 基准虚线

# =======================================================================
# 上方（全宽）：类目优先级类型分布树状图 — 总体类目分布（放大）
# =======================================================================
chart_title(t("● 类目优先级类型分布", "● Category Priority-Type Distribution"))
st.markdown(
    "<div style='font-size:0.70rem; color:#6b7280; font-weight:400; "
    "margin: -4px 0 8px 4px; line-height:1.3;'>"
    + t("外层=优先级类型（括号内为品类数）· 内层=品类 · 块大小∝综合分 · 悬停看精确值",
        "Outer = priority type (count in parens) · inner = category · "
        "tile size ∝ composite score · hover for exact value")
    + "</div>",
    unsafe_allow_html=True,
)
seg = ranked.copy()
# 按优先级顺序排序（高潜→较高→中性→谨慎→暂不考虑），配合 treemap sort=False
_ord = {tl: i for i, tl in enumerate(TIER_ORDER)}
seg = (seg.assign(_ord=seg["tier"].map(_ord))
          .sort_values("_ord", kind="stable")
          .drop(columns="_ord"))
seg["tier_label"] = seg["tier"].map(TIER_LABEL)
counts = seg["tier_label"].value_counts()
seg["tier_disp"] = seg["tier_label"].map(lambda x: f"{x} ({counts[x]})")

fig = px.treemap(
    seg,
    path=["tier_disp", "category"],     # 不要根节点「全部类目」→ 无背景块、无根标签
    values="composite_score",            # 块面积 ∝ 综合分（得分越高块越大）
    color="tier", color_discrete_map=TIER_COLOR,  # 颜色按优先级类型（全名键），稳定
    custom_data=["composite_score"],
    height=560,
)
fig.update_traces(
    sort=False,  # 保持数据顺序（按优先级 高潜→暂不考虑），不按数值重排
    texttemplate="%{label}",
    textfont=dict(size=13),
    insidetextfont=dict(color="white", size=13),       # 彩色块上统一白字
    marker=dict(line=dict(color="white", width=1.5)),  # 块间分隔线白
    hovertemplate=(
        "<b>%{label}</b><br>"
        + t("综合机会分：", "Opportunity Score: ") + "%{customdata[0]:.3f}<extra></extra>"
    ),
)
fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, width="stretch")

# =======================================================================
# 下方：左 = Top 10 机会类目排名（横向条形）；右 = Top 3 五维画像
# =======================================================================
bl, br = st.columns([1.4, 1])

with bl:
    chart_title(t("● Top 10 机会类目排名（综合分 · 条色=优先级类型）",
                  "● Top 10 Opportunity Categories (composite · bar color = priority type)"))
    top10 = ranked.head(10).copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=top10["category"], x=top10["composite_score"],
        orientation="h",
        marker=dict(color=[TIER_COLOR.get(tr, "#bbbbbb") for tr in top10["tier"]]),
        name=t("综合分", "Composite Score"),
        text=top10["composite_score"].round(2), textposition="outside",
        hovertemplate="<b>%{y}</b><br>" + t("综合分：", "Composite: ") + "%{x:.3f}<extra></extra>",
    ))
    # 全部类目综合分均分基准虚线（横向条形 → 竖虚线 x=均分）
    fig.add_vline(
        x=avg_score, line_dash="dash", line_color="#374151", line_width=1.5,
        annotation_text=t(f"均分 {avg_score:.2f}", f"avg {avg_score:.2f}"),
        annotation_position="top",
        annotation_font=dict(size=11, color="#374151"),
    )
    fig.update_layout(
        height=440, margin=dict(l=10, r=46, t=24, b=20),
        xaxis=dict(title=t("综合分", "Composite Score"), range=[0, 1]),   # 从 0 起，诚实
        yaxis=dict(autorange="reversed", automargin=True),                # 第 1 名在最上
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")

with br:
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
        showlegend=True, height=440,
        legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5, font=dict(size=10)),
        margin=dict(l=60, r=75, t=30, b=25),
    )
    st.plotly_chart(fig, width="stretch")

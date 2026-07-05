# streamlit_app/pages/4_类目综合评分.py
# 更新日期：2026-07-05
# Demo 适配：数据源 data/amazon.db → data/*.csv（_demo_data.connect_demo）；类目已匿名化；
#   无 config 目录 → 默认权重内联（A0.40/C0.35/T0.25），删 yaml 读取；读 *_c 后缀评分列（由 demo CSV 提供）。
# 原文件：v3/streamlit_app/pages/4_类目综合评分.py（方案C 对照版：3 维基础分 + 新品Bonus）
# 更新日期（原）：2026-07-03
# 用途：类目综合评分「方案C 对照版」— 复制自 4_类目综合评分.py，原页一字不动便于 A/B 对照。
#       方案C 评分口径：3 维基础分 + 新品Bonus（读 DB 的 *_c 后缀列）。
# 主要改动（相对原页，均为方案C 定制）：
#   - 2026-07-05（同步生产 v3）：① 权重滑块改百分比显示（40%，int 0~100 + format="%d%%"，key=wp_*_c）+
#       侧栏加「总和 X% ✔/❗」文字提示（三者之和不必=100，引擎按比例折算）；session 版本号 bump 到 7。
#       ② 类目得分表「优先级类型」列过 TIER_LABEL 映射，英文模式正确显示 Top/High/…（仅改显示文本、不影响取色）。
#       ③ 「新品成长分」英文 New-Product Growth → New-Product Growth Bonus（加分项语义更准）。
#   - 2026-07-03（精简版·聚焦得分表）：
#       ① 删「衡量什么」里的 S+8/M+4 文字标签；新品机会分只显示原始数字 0/3/6；维度说明改直白版。
#       ② 类目得分表（5 列）：类目|基础分|新品成长分|综合得分|优先级类型；综合得分 = 表内条形
#          （Styler linear-gradient 背景，长度∝得分、每行颜色=tier_c 色，与优先级色块同套 TIER_COLOR，
#          数值叠条上），优先级类型 = 纯 tier 色块；因 linear-gradient 用 styler.to_html()+st.markdown 渲染。
#          随权重实时重算 tier→条色/色块同步变；基础分+新品成长分=综合得分（自洽）。
#       ③ 删除树状图 / Top10 排名 / Top3 雷达三块旧图（及各自取数与布局），清理 np/px/go import。
#       ④ 侧栏删「权重总和」metric；「恢复默认」按钮 → 「默认」，样式对齐原页快速预设按钮（1/4 宽、小字号）。
#   - 2026-07-03（新建·方案C 对照版）：
#       ① 权重 UI 精简：删除「快速预设」多按钮 + PRESETS 多预设 + active_preset 追踪 + ×badge CSS；
#          只保留一个「恢复默认」按钮（重置回 scoring_config_v3.yaml dimension_weights，
#          市场吸引力0.40 / 市场开放度0.35 / 结构稳定0.25）。
#       ② 滑块 5 维 → 3 维（市场吸引力 / 市场开放度 / 结构稳定）。
#       ③ 数据源改读 *_c 后缀列（3 维分 + base_score_c + bonus_c + composite_score_c
#          + tier_c + positive_signals_c / risk_signal_c）。
#       ④ base + bonus 分开展示：新增「各类目 基础分 / 新品Bonus / 综合机会分」明细表。
#       ⑤ recompute：基础分 = 3 维分按滑块权重加权 ×100；综合机会分 = 基础分 + bonus_c
#          （bonus 固定、不随滑块变）；tier 按综合机会分百分位重算。
#       ⑥ Top3 画像雷达由 5 维 → 3 维（去 new_product / momentum）。
#   —— 原页 4_类目综合评分.py 的算法/数据源/侧边栏预设逻辑与本页无关，保持不动。

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "streamlit_app"))
from _styles import page_title, chart_title
from _i18n import t
from _demo_data import connect_demo

# 方案C 3 维（内部 *_c 列 → 展示名）
DIM_COLS = [
    "score_market_size_c",
    "score_openness_c",
    "score_stability_c",
]
DIM_LABELS = {
    "score_market_size_c": t("市场吸引力 (A)", "Market Attractiveness (A)"),
    "score_openness_c":    t("市场开放度 (C)", "Openness (C)"),
    "score_stability_c":   t("结构稳定 (T)", "Stability (T)"),
}
DIM_TOOLTIPS = {
    "score_market_size_c": t("偏好需求强、客单价高的吸引力市场", "Favor markets with strong demand and high price points"),
    "score_openness_c":    t("偏好更容易进入的市场", "Favor markets that are easier to enter"),
    "score_stability_c":   t("偏好稳定低波动市场", "Favor stable, low-volatility markets"),
}
# 默认权重（= scoring_config_v3.yaml dimension_weights；文件缺失时的兜底值）
DEFAULT_WEIGHTS_C = {
    "score_market_size_c": 0.40,
    "score_openness_c":    0.35,
    "score_stability_c":   0.25,
}

# 优先级类型（=Tier_c，Overall Rating）：5 档配色 + 顺序 + 展示简称（与原页一致）
TIER_COLOR = {
    "高潜机会类目": "#27ae60",  # 绿（最优）
    "较高机会类目": "#9b59b6",  # 紫
    "中性观察类目": "#93A2D3",  # 蓝灰
    "谨慎评估类目": "#e74c3c",  # 红（警示）
    "暂不考虑类目": "#8d949b",  # 灰（最不重要）
}
TIER_ORDER = ["高潜机会类目", "较高机会类目", "中性观察类目", "谨慎评估类目", "暂不考虑类目"]
TIER_LABEL = {
    "高潜机会类目": t("高潜机会", "Top"),
    "较高机会类目": t("较高机会", "High"),
    "中性观察类目": t("中性观察", "Balanced"),
    "谨慎评估类目": t("谨慎评估", "Watch"),
    "暂不考虑类目": t("暂不考虑", "Skip"),
}

# Tier 阈值（百分位，同 scoring_config tier_thresholds）
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
def load_default_weights_c():
    """默认权重（= scoring_config_v3.yaml dimension_weights；Demo 内联，无 yaml/config 依赖）
    市场吸引力 0.40 / 市场开放度 0.35 / 结构稳定 0.25。"""
    return dict(DEFAULT_WEIGHTS_C)


@st.cache_data
def load_scoring_c():
    """从 db.category_summary 读方案C 评分（*_c 后缀列，由方案C 引擎写入）。
    过滤：仅主类目（is_subcategory=0），且 composite_score_c 非 NULL（排除 Excluded）。"""
    conn = connect_demo()
    df = pd.read_sql(
        "SELECT category, "
        "score_market_size_c, score_openness_c, score_stability_c, "
        "base_score_c, nr_ms_pen_c, bonus_c, composite_score_c, "
        "tier_c, positive_signals_c, risk_signal_c "
        "FROM category_summary "
        "WHERE COALESCE(is_subcategory,0)=0 "
        "  AND composite_score_c IS NOT NULL",
        conn,
    )
    conn.close()
    if df.empty:
        return None, None
    return df, "db.category_summary (方案C · *_c)"


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
    """方案C 重算：基础分 = 3 维分按滑块权重加权 ×100；综合机会分 = 基础分 + bonus_c。
    bonus_c 固定（不随滑块变）；tier 按综合机会分百分位重算。
    positive_signals_c / risk_signal_c 是结构事实、不随权重变，静态来自 db。"""
    w = pd.Series(weights)
    s = w.sum()
    w = w / s if s > 0 else pd.Series([1.0 / len(DIM_COLS)] * len(DIM_COLS), index=DIM_COLS)
    base = (df[DIM_COLS] * w[DIM_COLS].values).sum(axis=1) * 100.0
    bonus = df["bonus_c"].fillna(0.0)
    out = df.copy()
    out["base_score_c"] = base
    out["composite_score_c"] = base + bonus
    out["tier_c"] = assign_tier(out["composite_score_c"])
    out["flag"] = assign_flag(out["composite_score_c"])
    return out


# -----------------------------------------------------------------------
# 页面
# -----------------------------------------------------------------------
page_title(t("类目综合评分", "Composite Score"))

df, source_name = load_scoring_c()
if df is None:
    st.error(t("db.category_summary 没有 *_c评分数据，请先运行 v3 评分引擎写入 *_c 列",
               "No Plan-C (*_c) scoring data in db.category_summary. Run the v3 scoring engine to write the *_c columns first."))
    st.stop()

# 各项评分「衡量什么」的直白说明（方案C：3 维基础分 + 新品Bonus）
with st.expander(t("ℹ️ 各项评分衡量什么", "ℹ️ What each score measures"), expanded=True):
    st.markdown(
        "<div style='font-size:0.8rem; color:#4b5563; line-height:1.7;'>"
        + "<b>" + t("综合得分", "Composite Score") + "</b> = "
        + t("基础分（市场吸引力 + 市场开放度 + 结构稳定）+ 新品成长分。",
            "base score (market attractiveness + openness + stability) + new-product growth bonus.")
        + "<br><b>" + t("市场吸引力", "Market Attractiveness") + "</b> — "
        + t("有没有市场？", "Is there a market?")
        + "<br><b>" + t("市场开放度", "Openness") + "</b> — "
        + t("能不能进入？", "Can you get in?")
        + "<br><b>" + t("结构稳定", "Stability") + "</b> — "
        + t("市场波动性大不大？", "How volatile is the market?")
        + "<br><b>" + t("新品成长", "New-Product Growth") + "</b> — "
        + t("有没有新品在爆发？这段时间新品卖爆、冲上飙升榜的类目，综合分会额外加分——冲得越猛，加得越多（最多 +6）。",
            "Any new products taking off? Categories with new products surging onto the Movers & Shakers list get extra points—the stronger the surge, the more (up to +6).")
        + "</div>",
        unsafe_allow_html=True,
    )

default_w = load_default_weights_c()

# 防止 hot reload / 旧 session 残留（bump 版本号时强制清旧权重键 w_/wp_ *_c + 自动维/移动记录）
if st.session_state.get("_page4c_v") != 7:
    for _k in list(st.session_state.keys()):
        if (_k.startswith("w_") or _k.startswith("wp_")) and _k.endswith("_c"):
            del st.session_state[_k]
    st.session_state.pop("auto_dim_c", None)
    st.session_state.pop("_last_moved_c", None)
    st.session_state["_page4c_v"] = 7

# 单个「默认」按钮字号 + 撑满 column（样式对齐原页快速预设按钮：1/4 宽、小字号）
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
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- 侧边栏：模型权重设置（方案C：3 维滑块 + 单个「默认」按钮）---
with st.sidebar:
    st.header(t("模型权重设置", "Model Weight Settings"))
    st.markdown(
        '<div style="color:#9ca3af; font-size:0.7rem; margin-top:-6px; margin-bottom:14px; line-height:1.3;">'
        + t("根据策略偏好调整维度权重",
            "Adjust dimension weights by strategy preference")
        + '</div>',
        unsafe_allow_html=True,
    )

    # 默认权重（整数百分比）：分数 ×100 四舍五入；A/C/T 默认 40/35/25，∑=100。
    _initpct = {c: int(round(float(default_w.get(c, 1.0 / len(DIM_COLS))) * 100)) for c in DIM_COLS}

    # 单个「默认」按钮：type 随「是否等于默认」变色（primary 蓝 / secondary 灰）。
    _is_default = all(int(st.session_state.get(f"wp_{c}", _initpct[c])) == _initpct[c] for c in DIM_COLS)
    pcols = st.columns(4)
    with pcols[3]:
        if st.button(t("默认", "Default"),
                     key="reset_weights_c",
                     type=("primary" if _is_default else "secondary"),
                     use_container_width=True,
                     help=t(f"重置为默认权重（A {_initpct['score_market_size_c']}% / C {_initpct['score_openness_c']}% / T {_initpct['score_stability_c']}%）",
                            f"Reset to default weights (A {_initpct['score_market_size_c']}% / C {_initpct['score_openness_c']}% / T {_initpct['score_stability_c']}%)")):
            for c in DIM_COLS:
                st.session_state[f"wp_{c}"] = int(_initpct[c])
            st.rerun()

    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

    # 总和指示器（渲染在滑块上方）：placeholder 先占位，滑块实例化后回填计算值。
    total_ph = st.empty()

    # 3 维滑块：百分比显示（40%），int 0~100 + format="%d%%"；完全独立、无回调/无联动。
    # 注：滑块「按住拖不动」是浏览器缩放≠100% 的已知问题（Ctrl+0 复位即可），与本参数无关。
    # 三者之和不必等于 100：引擎会自动按比例折算（归一化）；上方指示器仅作提示、不强制。
    _pct = {}
    for c in DIM_COLS:
        _pct[c] = st.slider(
            DIM_LABELS[c],
            0, 100,
            int(_initpct[c]),
            1,
            format="%d%%",
            key=f"wp_{c}",
            help=DIM_TOOLTIPS[c],
        )

    weights = {c: _pct[c] / 100.0 for c in DIM_COLS}

    _total = sum(_pct.values())
    if _total == 100:
        total_ph.markdown(
            '<div style="font-size:0.78rem; font-weight:600; color:#16a34a; margin-bottom:8px;">'
            + t("总和 100% ✔", "Total 100% ✔") + '</div>',
            unsafe_allow_html=True,
        )
    else:
        total_ph.markdown(
            '<div style="margin-bottom:8px;">'
            '<span style="font-size:0.78rem; font-weight:600; color:#d97706;">'
            + t(f"总和 {_total}% ❗", f"Total {_total}% ❗") + '</span>'
            '<div style="font-size:0.68rem; color:#d97706; margin-top:1px;">'
            + t("建议凑到 100%（未凑齐时系统会按比例自动折算）",
                "Aim for 100% (otherwise weights are auto-scaled proportionally)") + '</div></div>',
            unsafe_allow_html=True,
        )

ranked = recompute(df, weights).sort_values("composite_score_c", ascending=False)

col_cat = t("类目", "Category")
col_base = t("基础分", "Base Score")
col_bonus = t("新品成长分", "New-Product Growth Bonus")
col_comp = t("综合得分", "Composite Score")
col_tier = t("优先级类型", "Priority Type")
col_driver = t("主驱动因素", "Main Driver")

n_cat = len(ranked)
bonus_vals = ranked["bonus_c"].fillna(0.0)
comp_max = float(ranked["composite_score_c"].max()) if n_cat else 1.0

# =======================================================================
# 类目得分表（5 列）：类目 | 基础分 | 新品成长分 | 综合得分 | 优先级类型
#   综合得分列 = 表内条形：Styler linear-gradient 背景，长度∝得分、颜色=该行 tier_c 色
#   （与优先级色块同套 TIER_COLOR），数值(.1f)叠在条上；优先级类型列 = 纯 tier 色块。
#   linear-gradient 须 HTML 渲染（st.dataframe 不认），故 styler.to_html() + st.markdown。
#   按综合得分降序（ranked 已排）；随权重实时重算 → tier_c 变 → 条色/色块同步变。
# =======================================================================
chart_title(t("● 类目得分表", "● Category Score Table"))

# 主驱动因素 = 三维中「维度分 × 当前权重」贡献最大的那维（随滑块实时变）；带 icon 便于分辨
_DRV_ICON = {"score_market_size_c": "💵", "score_openness_c": "🔓", "score_stability_c": "⚓"}  # 绿钞/金锁/蓝锚，三色分明
_wser = pd.Series(weights)
_driver = (ranked[DIM_COLS].mul(_wser[DIM_COLS].values, axis=1)
           .idxmax(axis=1)
           .map(lambda d: f"{_DRV_ICON[d]} {DIM_LABELS[d].rsplit(' (', 1)[0]}"))
tbl = ranked.copy()
tbl["bonus_c"] = bonus_vals
tbl["_driver"] = _driver
tbl = tbl[["category", "base_score_c", "bonus_c", "composite_score_c", "tier_c", "_driver"]].copy()
tbl.columns = [col_cat, col_base, col_bonus, col_comp, col_tier, col_driver]


def _lighten(hex_color, factor=0.82):
    """向白色混合（factor = 白色占比）得浅色版：#27ae60 → 淡绿。"""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def _tier_bg(v):
    color = TIER_COLOR.get(v, "")
    if not color:
        return ""
    # 优先级类型单元格用对应 tier 的浅色版 + 深色文字（比满色柔和，仍可区分档位）
    return f"background-color:{_lighten(color)}; color:#1f2937; font-weight:600; text-align:center;"


def _comp_bar(row):
    """逐行：只给「综合得分」单元格设 linear-gradient 表内条形（颜色=该行 tier 色）。"""
    styles = ["" for _ in row.index]
    color = TIER_COLOR.get(row[col_tier], "#8d949b")
    pct = (row[col_comp] / comp_max * 100.0) if comp_max > 0 else 0.0
    pct = max(0.0, min(100.0, pct))
    styles[row.index.get_loc(col_comp)] = (
        f"background:linear-gradient(90deg, {color} {pct:.1f}%, #eef0f2 {pct:.1f}%);"
        " color:#1f2937; font-weight:600;"
    )
    return styles


styler = (
    tbl.style
    .format({col_base: "{:.1f}", col_bonus: "{:.0f}", col_comp: "{:.1f}",
             col_tier: lambda v: TIER_LABEL.get(v, v)})
    .apply(_comp_bar, axis=1)
    .map(_tier_bg, subset=[col_tier])
    .hide(axis="index")
    .set_table_attributes('class="score-table"')
)

st.markdown(
    """
    <style>
      table.score-table { border-collapse: collapse; width: 100%; font-size: 0.86rem; }
      table.score-table thead th {
          background: #f3f4f6; color: #374151; font-weight: 600;
          text-align: left; padding: 7px 12px; border-bottom: 2px solid #d1d5db;
      }
      table.score-table tbody td {
          padding: 6px 12px; border-bottom: 1px solid #eceef1; white-space: nowrap;
      }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(styler.to_html(), unsafe_allow_html=True)

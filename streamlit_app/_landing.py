# streamlit_app/_landing.py
# 更新日期：2026-06-28
# 用途：Demo 落地页正文（产品定位 + 数据流 + 5 页架构 + 方法论概览）
#       作为 st.navigation 的默认 page；入口路由器是同目录的 产品概览.py
# 启动：streamlit run streamlit_app/产品概览.py（经路由器加载本页）
# 主要改动：
#   - 2026-06-01：页面全部公开；卡片统一绿边框 + 可点箭头
#   - 2026-06-23：UI 文案中英双语化（包 t()）+ 配合 st.navigation 入口清理 set_page_config/header
#   - 2026-06-28：对齐生产 v2 — 6 页 → 5 页（「头部品牌竞争」改名 + 删除独立「ASIN 流动性」页，
#                 黏性表并入「跨榜联动」）；方法论卡片 archetype/strategy → Opportunity Signals +
#                 5 档优先级类型；页面描述同步 v2 新模块。
#   - 2026-06-29：对齐指标解释 §4.5 — 机会信号改为「市场吸引力/开放度/结构稳定」三维
#                 （动能/新品空间不参与信号），信号名 需求居前·居后 / 市场开放·品牌壁垒 /
#                 波动较小·较大；5 档英文 Top/High → High-potential/Higher；
#                 头部品牌竞争描述精简为「CR3 集中度+ 单类目品牌下钻」。

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from _styles import page_title
from _i18n import t


# 5 页 dashboard 架构（对齐生产 v2：头部品牌竞争 + 删除独立「ASIN 流动性」页，黏性表并入「跨榜联动」）
PAGES = [
    {
        "n": 1,
        "icon": "📊",
        "title": t("类目详情", "Category Detail"),
        "desc": t("类目层描述性分析：基本指标 + 基础分布 + 需求增量/存量象限图",
                  "Category-level descriptive analysis: key metrics + distributions + demand increment/stock quadrant"),
        "demo": True,
        "url": "/category-detail",
    },
    {
        "n": 2,
        "icon": "🏆",
        "title": t("头部品牌竞争", "Head-Brand Competition"),
        "desc": t("CR3 集中度+ 单类目品牌下钻",
                  "CR3 concentration + single-category brand drill-down"),
        "demo": True,
        "url": "/brand-competition",
    },
    {
        "n": 3,
        "icon": "🔄",
        "title": t("跨榜联动", "Cross-List Linkage"),
        "desc": t("ASIN 流动性（在榜率/满榜率/新增比例/→BS渗透）+ MS 爆发强度",
                  "ASIN liquidity (on-list / full-list / new-ASIN / →BS penetration) + MS burst intensity"),
        "demo": True,
        "url": "/cross-list",
    },
    {
        "n": 4,
        "icon": "🎯",
        "title": t("类目综合评分", "Composite Score"),
        "desc": t("评分系统：5 维模型 + 双层加权 + 权重偏好动态调整 + 优先级类型分布",
                  "Scoring system: 5-factor model + two-layer weighting + dynamic weight preferences + priority-type distribution"),
        "demo": True,
        "url": "/composite-score",
    },
    {
        "n": 5,
        "icon": "🧭",
        "title": t("行动指引", "Action Playbook"),
        "desc": t("单类目深度：优先级类型 + 优势/约束信号 + 价位带参考 + 重点 ASIN",
                  "Single-category deep dive: priority type + strength/constraint signals + price-band reference + top ASINs"),
        "demo": True,
        "url": "/action-playbook",
    },
]

DATA_FLOW = [
    ("📥", t("数据采集", "Data Collection"),   t("BS / NR / MS 榜单", "BS / NR / MS rankings")),
    ("💾", t("数据入库", "Data Ingestion"),   t("解析清洗 + 日度指标聚合", "Parsing & cleaning + daily metric aggregation")),
    ("⚖️", t("评分建模", "Scoring & Modeling"),   t("5 维评分 + 双层加权 + 优先级类型 + 优势/约束信号", "5-factor scoring + two-layer weighting + priority tiers + opportunity signals")),
    ("📈", "Dashboard",   t("可视化 + 行动指引", "Visualization + action playbook")),
]


# =======================================================================
# 页面
# =======================================================================
# Demo banner
st.markdown(
    "<div style='background:#fff7ed; border-left:4px solid #f59e0b; "
    "padding:8px 14px; margin: 4px 0 10px 0; border-radius:4px; font-size:0.85rem; color:#7c2d12;'>"
    "🎭 <b>Demo Mode</b> — "
    + t("类目/品牌/ASIN已匿名化。", "categories / brands / ASINs are anonymized.")
    + " </div>",
    unsafe_allow_html=True,
)

page_title(t("产品概览", "Product Overview"))

# ---------------------------------------------------------------
# 0. 一句话定位
# ---------------------------------------------------------------
st.markdown(
    "<div style='font-size:1.0rem; line-height:1.7; color:#2c3e50; "
    "padding: 8px 0 4px 0;'>"
    + t(
        "基于Amazon三类榜单（BS / NR / MS）的自动化采集 + 多维评分 + 行动指引系统 — "
        "建立 <b>可审计、可复算、可回放</b>的 <b>类目选品决策</b> 数据流程。",
        "An automated pipeline over Amazon's three rankings (BS / NR / MS): "
        "collection + multi-factor scoring + action playbook — building an "
        "<b>auditable, reproducible, replayable</b> data process for "
        "<b>category sourcing decisions</b>.",
    )
    + "</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------
# 1. 数据流（4 步）
# ---------------------------------------------------------------
st.markdown("## " + t("数据流", "Data Flow"))
flow_cols = st.columns(7)
flow_indices = [0, 2, 4, 6]
arrow_indices = [1, 3, 5]
for i, (icon, label, desc) in enumerate(DATA_FLOW):
    with flow_cols[flow_indices[i]]:
        st.markdown(
            f"<div style='background:#f1f5f9; border:1px solid #cbd5e1; "
            f"border-radius:8px; padding:14px 10px; text-align:center; min-height:120px;'>"
            f"<div style='font-size:1.8rem; line-height:1;'>{icon}</div>"
            f"<div style='font-size:0.95rem; font-weight:600; color:#2c3e50; margin-top:6px;'>{label}</div>"
            f"<div style='font-size:0.75rem; color:#6b7280; margin-top:4px; line-height:1.4;'>{desc}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
for ai in arrow_indices:
    with flow_cols[ai]:
        st.markdown(
            "<div style='text-align:center; font-size:1.6rem; color:#94a3b8; "
            "padding-top:38px;'>→</div>",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------
# 2. 6 页 Dashboard 架构
# ---------------------------------------------------------------
st.markdown("## " + t("Dashboard 5 页架构", "Dashboard — 5-Page Architecture"))

for row in range((len(PAGES) + 2) // 3):
    cols = st.columns(3)
    for i in range(3):
        idx = row * 3 + i
        if idx >= len(PAGES):
            continue
        p = PAGES[idx]
        with cols[i]:
            # 6 页均已开放：统一绿边框 + 右下角可点绿圆箭头
            arrow_html = (
                f"<a href='{p['url']}' target='_self' title='{t('打开', 'Open')} {p['title']}' "
                f"style='display:inline-flex; align-items:center; justify-content:center; "
                f"width:30px; height:30px; border-radius:50%; "
                f"background:#27ae60; color:#fff; font-size:1.05rem; font-weight:700; "
                f"text-decoration:none; line-height:1; "
                f"box-shadow:0 1px 3px rgba(39,174,96,0.35);'>→</a>"
            )
            st.markdown(
                f"<div style='background:#ffffff; border:1px solid #86efac; "
                f"border-radius:8px; padding:14px 16px; min-height:175px; "
                f"box-shadow:0 1px 2px rgba(0,0,0,0.04);'>"
                f"<div style='display:flex; align-items:baseline; gap:8px;'>"
                f"<span style='font-size:1.4rem;'>{p['icon']}</span>"
                f"<span style='font-size:0.78rem; color:#9ca3af;'>Page {p['n']}</span>"
                f"</div>"
                f"<div style='font-size:1.05rem; font-weight:600; color:#1a2940; margin-top:6px;'>{p['title']}</div>"
                f"<div style='font-size:0.82rem; color:#4b5563; margin-top:6px; line-height:1.55; min-height:48px;'>{p['desc']}</div>"
                f"<div style='display:flex; justify-content:flex-end; align-items:center; margin-top:14px;'>"
                f"{arrow_html}"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------
# 3. 方法论核心
# ---------------------------------------------------------------
st.markdown("## " + t("方法论核心", "Core Methodology"))

m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(
        "<div style='background:#f1f5f9; border-left:4px solid #3498db; "
        "border-radius:6px; padding:14px 16px; min-height:200px;'>"
        "<div style='font-size:1.0rem; font-weight:600; color:#1a2940; margin-bottom:8px;'>"
        + t("评分系统", "Scoring System") + "</div>"
        "<div style='font-size:0.85rem; color:#475569; line-height:1.7;'>"
        + t(
            "<b>5 维</b>：市场吸引力 / 开放度 / 新品空间 / 增长动能 / 结构稳定<br><br>"
            "<b>双层加权</b>：数据驱动+业务调整<br><br>"
            "<b>模型指标</b>：筛选 → 候选 → selected",
            "<b>5 factors</b>: Market Attractiveness / Openness / New-Product Room / Momentum / Stability<br><br>"
            "<b>Two-layer weighting</b>: data-driven + business adjustment<br><br>"
            "<b>Model metrics</b>: screened &rarr; candidate &rarr; selected",
        )
        + "</div></div>",
        unsafe_allow_html=True,
    )

with m2:
    st.markdown(
        "<div style='background:#fdf2f8; border-left:4px solid #c026d3; "
        "border-radius:6px; padding:14px 16px; min-height:200px;'>"
        "<div style='font-size:1.0rem; font-weight:600; color:#1a2940; margin-bottom:8px;'>"
        + t("Opportunity Signals", "Opportunity Signals") + "</div>"
        "<div style='font-size:0.85rem; color:#475569; line-height:1.7;'>"
        + t(
            "对 市场吸引力 / 开放度 / 结构稳定 三维做<b>百分位</b>切线"
            "（动能方向歧义、新品空间数据稀疏，<b>不参与信号</b>）<br><br>"
            "<b>优势信号</b>（≥P75）：需求居前 / 市场开放 / 波动较小<br><br>"
            "<b>约束信号</b>（≤P25）：需求居后 / 品牌壁垒 / 波动较大",
            "Percentile cutoffs over Market Attractiveness / Openness / Stability "
            "(Momentum is directionally ambiguous and New Product is sparse, so both are "
            "<b>excluded from signals</b>)<br><br>"
            "<b>Strengths</b> (&ge;P75): Top-quartile demand / Open Market / Low volatility<br><br>"
            "<b>Constraints</b> (&le;P25): Bottom-quartile demand / Brand Barrier / High volatility",
        )
        + "</div></div>",
        unsafe_allow_html=True,
    )

with m3:
    st.markdown(
        "<div style='background:#f0fdf4; border-left:4px solid #16a34a; "
        "border-radius:6px; padding:14px 16px; min-height:200px;'>"
        "<div style='font-size:1.0rem; font-weight:600; color:#1a2940; margin-bottom:8px;'>"
        + t("5 档优先级类型", "5 Priority Tiers") + "</div>"
        "<div style='font-size:0.85rem; color:#475569; line-height:1.7;'>"
        + t(
            "按综合机会分<b>百分位</b>分 5 档：<br>"
            "<b>高潜机会</b> — 推荐优先<br>"
            "<b>较高机会</b> — 重点关注<br>"
            "<b>中性观察</b> — 均衡待察<br>"
            "<b>谨慎评估</b> — 谨慎权衡<br>"
            "<b>暂不考虑</b> — 暂缓<br><br>",
            "5 tiers by composite-score <b>percentile</b>:<br>"
            "<b>High-potential</b> — prioritize<br>"
            "<b>Higher</b> — strong focus<br>"
            "<b>Balanced</b> — monitor<br>"
            "<b>Watch</b> — weigh carefully<br>"
            "<b>Skip</b> — defer<br><br>",
        )
        + "</div></div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------
# 4. 技术栈
# ---------------------------------------------------------------
st.markdown("## " + t("技术栈", "Tech Stack"))

CHIPS = [
    ("Python", "#3776AB"),
    ("Pandas", "#150458"),
    ("NumPy", "#013243"),
    ("SQLite", "#003B57"),
    ("Streamlit", "#FF4B4B"),
    ("Plotly", "#3F4F75"),
    ("BeautifulSoup", "#4B8BBE"),
    ("Information Entropy", "#6b7280"),
    ("Pareto Optimization", "#6b7280"),
    ("MCDA", "#6b7280"),
]
chip_html = " ".join(
    f"<span style='display:inline-block; background:{c}; color:#fff; "
    f"font-size:0.78rem; padding:3px 10px; border-radius:12px; margin: 3px 4px 3px 0;'>{name}</span>"
    for name, c in CHIPS
)
st.markdown(f"<div style='line-height:2.2;'>{chip_html}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Footer
# ---------------------------------------------------------------
st.markdown("<div style='height:30px;'></div>", unsafe_allow_html=True)
st.markdown(
    "<div style='border-top:1px solid #e2e8f0; padding-top:14px; "
    "font-size:0.78rem; color:#94a3b8; text-align:center;'>"
    "© Elita · 2026"
    "</div>",
    unsafe_allow_html=True,
)

# streamlit_app/_landing.py
# 更新日期：2026-06-23
# 用途：Demo 落地页正文（产品定位 + 数据流 + 6 页架构 + 方法论概览）
#       作为 st.navigation 的默认 page；入口路由器是同目录的 产品概览.py
# 启动：streamlit run streamlit_app/产品概览.py（经路由器加载本页）
# 主要改动：
#   - 2026-06-01：6 页全部公开（品牌竞争 / ASIN流动性 / 跨榜联动 解锁为 demo），
#                 Demo banner「公开 3/6」→「公开 6/6」；架构卡片去掉「✅ Demo 可访问 /
#                 🔒 完整版」图例与徽章（均已开放，徽章冗余），卡片统一绿边框 + 可点箭头
#   - 2026-06-23：UI 文案中英双语化（包 t()）+ 配合 st.navigation 入口清理 set_page_config/header

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from _styles import page_title
from _i18n import t


# 6 页 dashboard 架构
PAGES = [
    {
        "n": 1,
        "icon": "📊",
        "title": t("类目详情", "Category Detail"),
        "desc": t("类目层描述性分析：基本指标+基础分布 +交叉图",
                  "Category-level descriptive analysis: key metrics + distributions + cross plots"),
        "demo": True,
        "url": "/category-detail",
    },
    {
        "n": 2,
        "icon": "🏆",
        "title": t("品牌竞争", "Brand Competition"),
        "desc": t("品牌画像 + CR3 经营形态 + 集中度演变",
                  "Brand profiles + CR3 operating types + concentration trends"),
        "demo": True,
        "url": "/brand-competition",
    },
    {
        "n": 3,
        "icon": "🔁",
        "title": t("ASIN 流动性", "ASIN Liquidity"),
        "desc": t("Top 100 在榜时间分布 / 流入流出情况",
                  "Top 100 time-on-list distribution / inflow & outflow"),
        "demo": True,
        "url": "/asin-liquidity",
    },
    {
        "n": 4,
        "icon": "🔄",
        "title": t("跨榜联动", "Cross-List Linkage"),
        "desc": t("BS / NR / MS 三榜 ASIN 跨榜流转情况",
                  "ASIN flow across the BS / NR / MS rankings"),
        "demo": True,
        "url": "/cross-list",
    },
    {
        "n": 5,
        "icon": "🎯",
        "title": t("类目综合评分", "Composite Score"),
        "desc": t("评分系统：多维模型 + 双层加权 + 策略偏好动态调整",
                  "Scoring system: multi-factor model + two-layer weighting + dynamic strategy preferences"),
        "demo": True,
        "url": "/composite-score",
    },
    {
        "n": 6,
        "icon": "🧭",
        "title": t("行动指引", "Action Playbook"),
        "desc": t("单类目深度：重点 ASIN / 价格机会 / 市场窗口 / 打法建议",
                  "Single-category deep dive: top ASINs / price gaps / market window / playbook"),
        "demo": True,
        "url": "/action-playbook",
    },
]

DATA_FLOW = [
    ("📥", t("数据采集", "Data Collection"),   t("BS / NR / MS 榜单", "BS / NR / MS rankings")),
    ("💾", t("数据入库", "Data Ingestion"),   t("解析清洗 + 日度指标聚合", "Parsing & cleaning + daily metric aggregation")),
    ("⚖️", t("评分建模", "Scoring & Modeling"),   t("5 维评分 + 双层加权 + 业务类型诊断", "5-factor scoring + two-layer weighting + archetype diagnosis")),
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
st.markdown("## " + t("Dashboard 6 页架构", "Dashboard — 6-Page Architecture"))

for row in range(2):
    cols = st.columns(3)
    for i in range(3):
        p = PAGES[row * 3 + i]
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
            "<b>5 维</b>：市场规模 / 开放度 / 新品空间 / 增长动能 / 结构稳定<br><br>"
            "<b>双层加权</b>：数据驱动+业务调整<br><br>"
            "<b>模型指标</b>：筛选 → 候选 → selected",
            "<b>5 factors</b>: Market Size / Openness / New-Product Room / Momentum / Stability<br><br>"
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
        + t("业务类型诊断", "Archetype Diagnosis") + "</div>"
        "<div style='font-size:0.85rem; color:#475569; line-height:1.7;'>"
        + t(
            "5 维各分 <b>H / M / L</b>分层阈值<br><br>"
            "组合业务类型：<br>"
            "如「新兴机会」「高热红海」「高成长高波动」<br><br>"
            "<b>优先级匹配</b>：跨维度特征强的先命中，第一个命中即停",
            "Each of the 5 factors is split into <b>H / M / L</b> threshold tiers<br><br>"
            "Combined into archetypes:<br>"
            '"Emerging Opportunity", "Hot Red Ocean", "High-Growth High-Volatility"<br><br>'
            "<b>Priority matching</b>: archetypes with stronger cross-factor signals match first, stopping at the first hit",
        )
        + "</div></div>",
        unsafe_allow_html=True,
    )

with m3:
    st.markdown(
        "<div style='background:#f0fdf4; border-left:4px solid #16a34a; "
        "border-radius:6px; padding:14px 16px; min-height:200px;'>"
        "<div style='font-size:1.0rem; font-weight:600; color:#1a2940; margin-bottom:8px;'>"
        + t("5 类策略决策", "5 Strategy Decisions") + "</div>"
        "<div style='font-size:0.85rem; color:#475569; line-height:1.7;'>"
        + t(
            "<b>Top Pick</b> — 推荐主投<br>"
            "<b>Hidden Gem</b> — 择时进入<br>"
            "<b>Crowded</b> — niche 切入<br>"
            "<b>Watch</b> — 长线观察<br>"
            "<b>Avoid</b> — 慎入<br><br>",
            "<b>Top Pick</b> — recommended core bet<br>"
            "<b>Hidden Gem</b> — enter on timing<br>"
            "<b>Crowded</b> — niche entry<br>"
            "<b>Watch</b> — long-term monitor<br>"
            "<b>Avoid</b> — enter with caution<br><br>",
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

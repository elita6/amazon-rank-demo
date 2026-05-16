# demo/streamlit_app/产品概览.py
# 更新日期：2026-05-16
# 用途：Demo 入口页 — 产品定位 + 数据流 + 6 页架构 + 方法论概览
# 启动：streamlit run demo/streamlit_app/产品概览.py

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from _styles import inject_global_style, app_header, page_title


# 6 页 dashboard 架构
PAGES = [
    {
        "n": 1,
        "icon": "📊",
        "title": "类目详情",
        "desc": "类目层描述性分析：基本指标+基础分布 +交叉图",
        "demo": True,
        "url": "/类目详情",
    },
    {
        "n": 2,
        "icon": "🏆",
        "title": "品牌竞争",
        "desc": "品牌画像 + CR3 经营形态 + 集中度演变",
        "demo": False,
        "url": None,
    },
    {
        "n": 3,
        "icon": "🔁",
        "title": "ASIN 流动性",
        "desc": "Top 100 在榜时间分布 / 流入流出情况",
        "demo": False,
        "url": None,
    },
    {
        "n": 4,
        "icon": "🔄",
        "title": "跨榜联动",
        "desc": "BS / NR / MS 三榜 ASIN 跨榜流转情况",
        "demo": False,
        "url": None,
    },
    {
        "n": 5,
        "icon": "🎯",
        "title": "类目综合评分",
        "desc": "评分系统：多维模型 + 双层加权 + 策略偏好动态调整",
        "demo": True,
        "url": "/类目综合评分",
    },
    {
        "n": 6,
        "icon": "🧭",
        "title": "行动指引",
        "desc": "单类目深度：重点 ASIN / 价格机会 / 市场窗口 / 打法建议",
        "demo": True,
        "url": "/行动指引",
    },
]

DATA_FLOW = [
    ("📥", "数据采集",   "BS / NR / MS 榜单"),
    ("💾", "数据入库",   "解析清洗 + 日度指标聚合"),
    ("⚖️", "评分建模",   "5 维评分 + 双层加权 + 业务类型诊断"),
    ("📈", "Dashboard",   "可视化 + 行动指引"),
]


# =======================================================================
# 页面
# =======================================================================
st.set_page_config(page_title="产品概览 · Demo", layout="wide", initial_sidebar_state="expanded")
inject_global_style()
app_header()

# Demo banner
st.markdown(
    "<div style='background:#fff7ed; border-left:4px solid #f59e0b; "
    "padding:8px 14px; margin: 4px 0 10px 0; border-radius:4px; font-size:0.85rem; color:#7c2d12;'>"
    "🎭 <b>Demo Mode</b> — 公开 3 / 6 页 · 类目/品牌/ASIN已匿名化 · "
    "</div>",
    unsafe_allow_html=True,
)

page_title("产品概览")

# ---------------------------------------------------------------
# 0. 一句话定位
# ---------------------------------------------------------------
st.markdown(
    "<div style='font-size:1.0rem; line-height:1.7; color:#2c3e50; "
    "padding: 8px 0 4px 0;'>"
    "基于 Amazon 三类榜单（BS / NR / MS）的自动化采集 + 多维评分 + 行动指引系统 — "
    "把 <b>类目选品决策</b> 从经验拍板转为<b>可审计、可复算、可回放</b>的数据流程。"
    "</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------
# 1. 数据流（4 步）
# ---------------------------------------------------------------
st.markdown("## 数据流")
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
st.markdown("## Dashboard 6 页架构")
st.caption("✅ Demo 可访问 · 🔒 完整版")

for row in range(2):
    cols = st.columns(3)
    for i in range(3):
        p = PAGES[row * 3 + i]
        with cols[i]:
            badge_color = "#27ae60" if p["demo"] else "#94a3b8"
            badge_bg    = "#f0fdf4" if p["demo"] else "#f1f5f9"
            badge_text  = "✅ Demo 可访问" if p["demo"] else "🔒 完整版独享"
            border_color = "#86efac" if p["demo"] else "#e2e8f0"
            # 右侧箭头：demo 可点（绿圆 + <a>）/ locked 灰圆 <span>
            if p["demo"] and p["url"]:
                arrow_html = (
                    f"<a href='{p['url']}' target='_self' title='打开 {p['title']}' "
                    f"style='display:inline-flex; align-items:center; justify-content:center; "
                    f"width:30px; height:30px; border-radius:50%; "
                    f"background:#27ae60; color:#fff; font-size:1.05rem; font-weight:700; "
                    f"text-decoration:none; line-height:1; "
                    f"box-shadow:0 1px 3px rgba(39,174,96,0.35);'>→</a>"
                )
            else:
                arrow_html = (
                    "<span style='display:inline-flex; align-items:center; justify-content:center; "
                    "width:30px; height:30px; border-radius:50%; "
                    "background:#e2e8f0; color:#94a3b8; font-size:1.05rem; font-weight:700; "
                    "line-height:1;'>→</span>"
                )
            st.markdown(
                f"<div style='background:#ffffff; border:1px solid {border_color}; "
                f"border-radius:8px; padding:14px 16px; min-height:175px; "
                f"box-shadow:0 1px 2px rgba(0,0,0,0.04);'>"
                f"<div style='display:flex; align-items:baseline; gap:8px;'>"
                f"<span style='font-size:1.4rem;'>{p['icon']}</span>"
                f"<span style='font-size:0.78rem; color:#9ca3af;'>Page {p['n']}</span>"
                f"</div>"
                f"<div style='font-size:1.05rem; font-weight:600; color:#1a2940; margin-top:6px;'>{p['title']}</div>"
                f"<div style='font-size:0.82rem; color:#4b5563; margin-top:6px; line-height:1.55; min-height:48px;'>{p['desc']}</div>"
                f"<div style='display:flex; justify-content:space-between; align-items:center; margin-top:14px;'>"
                f"<span style='background:{badge_bg}; color:{badge_color}; "
                f"font-size:0.72rem; font-weight:600; padding:2px 8px; border-radius:3px; "
                f"border:1px solid {badge_color}33;'>{badge_text}</span>"
                f"{arrow_html}"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------
# 3. 方法论核心
# ---------------------------------------------------------------
st.markdown("## 方法论核心")

m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(
        "<div style='background:#f1f5f9; border-left:4px solid #3498db; "
        "border-radius:6px; padding:14px 16px; min-height:200px;'>"
        "<div style='font-size:1.0rem; font-weight:600; color:#1a2940; margin-bottom:8px;'>"
        "评分系统</div>"
        "<div style='font-size:0.85rem; color:#475569; line-height:1.7;'>"
        "<b>5 维</b>：市场规模 / 开放度 / 新品空间 / 增长动能 / 结构稳定<br><br>"
        "<b>双层加权</b>：数据驱动+业务调整<br><br>"
        "<b>模型指标</b>：筛选 → 候选 → selected"
        "</div></div>",
        unsafe_allow_html=True,
    )

with m2:
    st.markdown(
        "<div style='background:#fdf2f8; border-left:4px solid #c026d3; "
        "border-radius:6px; padding:14px 16px; min-height:200px;'>"
        "<div style='font-size:1.0rem; font-weight:600; color:#1a2940; margin-bottom:8px;'>"
        "业务类型诊断</div>"
        "<div style='font-size:0.85rem; color:#475569; line-height:1.7;'>"
        "5 维各分 <b>H / M / L</b>分层阈值<br><br>"
        "组合业务类型：<br>"
        "如「新兴机会」「高热红海」「高成长高波动」<br><br>"
        "<b>优先级匹配</b>：跨维度特征强的先命中，第一个命中即停"
        "</div></div>",
        unsafe_allow_html=True,
    )

with m3:
    st.markdown(
        "<div style='background:#f0fdf4; border-left:4px solid #16a34a; "
        "border-radius:6px; padding:14px 16px; min-height:200px;'>"
        "<div style='font-size:1.0rem; font-weight:600; color:#1a2940; margin-bottom:8px;'>"
        "5 类策略决策</div>"
        "<div style='font-size:0.85rem; color:#475569; line-height:1.7;'>"
        "<b>Top Pick</b> — 推荐主投<br>"
        "<b>Hidden Gem</b> — 择时进入<br>"
        "<b>Crowded</b> — niche 切入<br>"
        "<b>Watch</b> — 长线观察<br>"
        "<b>Avoid</b> — 慎入<br><br>"
        "策略由业务类型直接映射（不依赖阈值，避免分数漂移）"
        "</div></div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------
# 4. 技术栈
# ---------------------------------------------------------------
st.markdown("## 技术栈")

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

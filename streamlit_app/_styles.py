# v1/streamlit_app/_styles.py
# 更新日期：2026-05-01
# 用途：Streamlit 多看板共用的 CSS 样式 + 标题/卡片工具
# 调用：每个 page 顶部 from _styles import inject_global_style, app_header, page_title
# 主要改动：
#   - 2026-04-30 v2：H1 改深蓝渐变；H2 fit-content 竖线；H3 缩进+下划线
#   - 2026-05-01 v3：H2 竖线改 H1 渐变最深色（#1e3a5f）保持视觉一致；
#                新增 app_header（全局共享大标题「Amazon 类目机会评分系统」）；
#                筛选器标签字号上调 + 选项字号下调；
#                .info-card 项目符号样式（去下划线，加 • 圆点）
#   - 2026-05-01 v4：修主标题被截断（block-container padding-top 加大 + line-height）；
#                筛选器选中色覆盖红→蓝；下载按钮字号缩小到与表格一致；
#                新增 view-toggle 三按钮风格（蓝底白字 active / 浅边框 inactive）

import streamlit as st


# H1 渐变三色（深→浅），H2 竖线用最深的那个色保证视觉延续
DEEP_NAVY = "#1e3a5f"
H1_GRADIENT = f"linear-gradient(90deg, {DEEP_NAVY} 0%, #2d5a8c 60%, #3d6fa0 100%)"

ACCENT = "#3498db"
CARD_BG = "#fafbfd"
CARD_BORDER = "#e6e9ee"


def inject_global_style():
    """注入全局 CSS"""
    st.markdown(
        f"""
        <style>
          /* ============= 全局 App 大标题（每页共享） ============= */
          .app-header {{
            text-align: center;
            font-size: 1.6rem;
            font-weight: 700;
            color: #1a2940;
            letter-spacing: 1px;
            line-height: 1.5;
            padding: 14px 0 10px 0;
            margin-bottom: 6px;
            border-bottom: 1px solid #e0e6ee;
          }}
          .app-header .app-subtitle {{
            font-size: 0.78rem; font-weight: 400;
            color: #6b7280; letter-spacing: 0;
            margin-top: 4px;
            line-height: 1.4;
          }}

          /* ============= 当前页 H1（深蓝渐变 banner） ============= */
          .page-title-bar {{
            background: {H1_GRADIENT};
            padding: 12px 18px;
            border-radius: 6px;
            margin: 6px 0 14px 0;
            box-shadow: 0 2px 6px rgba(30,58,95,0.15);
          }}
          .page-title-bar h1 {{
            color: #ffffff !important;
            font-size: 1.35rem !important;
            margin: 0 0 4px 0 !important;
            font-weight: 600 !important;
          }}
          .page-title-bar .subtitle {{
            color: rgba(255,255,255,0.85);
            font-size: 0.85rem; line-height: 1.4;
          }}

          /* ============= H2 竖线（用 H1 最深色 ============= */
          h2 {{
            font-size: 1.15rem !important;
            margin: 0.9rem 0 0.4rem 0 !important;
            padding: 4px 16px 4px 12px !important;
            border-left: 8px solid {DEEP_NAVY};
            display: inline-block; width: auto;
            background: linear-gradient(90deg, {DEEP_NAVY}10 0%, transparent 100%);
            border-radius: 0 4px 4px 0;
          }}

          /* ============= H3 缩进对齐（去下划线，由卡片项目符号代替强调） ============= */
          h3 {{
            font-size: 1.0rem !important;
            margin: 0.6rem 0 0.4rem 20px !important;
            color: #2c3e50;
            font-weight: 600;
          }}

          /* ============= 容器 ============= */
          /* 顶部 padding 加大，避免 app-header 被 streamlit 顶栏挤压裁切 */
          .block-container {{ padding-top: 2.6rem !important; padding-bottom: 1rem !important; }}
          [data-testid="stVerticalBlockBorderWrapper"] {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER} !important;
            border-radius: 6px !important;
            padding: 14px !important;
          }}

          /* ============= 信息卡片（综合评估 / 维度冠军） ============= */
          .info-card {{
            background: #ffffff;
            border: 1px solid {CARD_BORDER};
            border-radius: 8px;
            padding: 14px 16px;
            margin-bottom: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            border-left: 4px solid {ACCENT};
          }}
          .info-card .card-title {{
            font-size: 0.95rem; font-weight: 600;
            color: #2c3e50; margin: 0 0 8px 0;
          }}
          .info-card .card-bullets {{
            list-style: none; padding-left: 0; margin: 4px 0 0 0;
          }}
          .info-card .card-bullets li {{
            font-size: 0.83rem; color: #555;
            line-height: 1.6; margin: 4px 0;
            padding-left: 14px; position: relative;
          }}
          .info-card .card-bullets li::before {{
            content: "•";
            color: {ACCENT};
            font-weight: bold;
            position: absolute;
            left: 2px;
          }}
          .info-card .card-bullets li b {{ color: #2c3e50; }}
          .info-card .card-cats {{
            font-size: 0.8rem; color: #1565c0;
            background: #e8f0fa; padding: 3px 7px;
            border-radius: 3px; margin: 2px 3px 2px 0;
            display: inline-block;
          }}
          .info-card .card-score {{
            font-size: 1.7rem; font-weight: 700;
            color: {ACCENT}; line-height: 1;
          }}

          /* ============= 数据规模 KPI（去边框） ============= */
          .kpi-row {{
            display: flex; justify-content: space-between;
            align-items: flex-start; gap: 12px;
            padding: 8px 0;
          }}
          .kpi-item {{
            flex: 1;
            padding: 8px 12px;
            min-width: 0;
          }}
          .kpi-item .kpi-label {{
            font-size: 0.85rem; color: #666; margin-bottom: 6px;
          }}
          .kpi-item .kpi-value {{
            font-size: 1.7rem; font-weight: 400;
            color: #222; line-height: 1.1;
          }}

          /* ============= 统计周期（去边框，纯文字） ============= */
          .period-box {{
            color: #666; font-size: 0.85rem;
            padding: 4px 0;
          }}

          /* ============= 筛选器（榜单 / 类目）样式 ============= */
          /* radio 标签字号上调，选项字号下调 */
          [data-testid="stRadio"] > label,
          [data-testid="stMultiSelect"] > label,
          [data-testid="stPopover"] > label {{
            font-size: 0.92rem !important;
            font-weight: 600 !important;
            color: #2c3e50 !important;
          }}
          [data-testid="stRadio"] div[role="radiogroup"] label p,
          [data-testid="stRadio"] div[role="radiogroup"] label {{
            font-size: 0.82rem !important;
          }}
          /* radio/checkbox/multiselect 选中色：完全交给 primaryColor (.streamlit/config.toml)
             自然控制 — 选中红圆环 → 蓝圆环，未选中保持默认（无色） */

          /* 自渲染的筛选器标签（如"🔍 类目选择"），字号同 radio 标签 */
          .filter-label {{
            font-size: 0.875rem;
            font-weight: 600;
            color: #262730;
            line-height: 1.6;
            margin: 8px 0 0.25rem 0;
            padding: 0;
          }}

          /* 类目 popover 按钮样式：椭圆胶囊 + 淡灰边框
             高度 ~26px（小巧），margin-top:4px 让按钮中心下移
             与 radio item (~32px) 圆环中心严格对齐 */
          [data-testid="stPopover"] > div > button,
          [data-testid="stPopover"] > button {{
            background: #fff !important;
            border: 1px solid #d0d4dc !important;
            color: #262730 !important;
            font-weight: 400 !important;
            border-radius: 999px !important;
            padding: 3px 14px !important;
            min-height: 0 !important;
            line-height: 1.4 !important;
            box-shadow: none !important;
            height: auto !important;
            margin-top: 4px !important;
          }}
          [data-testid="stPopover"] > div > button p,
          [data-testid="stPopover"] > button p {{
            font-size: 0.875rem !important;
            margin: 0 !important;
            line-height: 1.4 !important;
          }}
          [data-testid="stPopover"] > div > button:hover,
          [data-testid="stPopover"] > button:hover {{
            border-color: {DEEP_NAVY} !important;
            color: {DEEP_NAVY} !important;
          }}

          /* popover 内嵌的"全选/全不选"按钮：字号 0.875rem + 淡灰边 + 方角
             （选择器更具体，强制覆盖下方 .stButton 通用样式的 999px 圆角） */
          [data-testid="stPopover"] [data-testid="stButton"] button,
          [data-testid="stPopover"] .stButton button {{
            font-size: 0.875rem !important;
            padding: 4px 10px !important;
            border: 1px solid #d0d4dc !important;
            border-radius: 4px !important;
            background: #fff !important;
            color: #262730 !important;
            font-weight: 400 !important;
            min-height: 0 !important;
            line-height: 1.4 !important;
          }}
          [data-testid="stPopover"] [data-testid="stButton"] button p,
          [data-testid="stPopover"] .stButton button p {{
            font-size: 0.875rem !important;
            margin: 0 !important;
          }}

          /* ============= 下载 CSV 按钮（缩小到与表格记录相近） ============= */
          [data-testid="stDownloadButton"] button {{
            font-size: 0.78rem !important;
            padding: 2px 10px !important;
            min-height: 0 !important;
            line-height: 1.4 !important;
            border: 1px solid {CARD_BORDER} !important;
            color: #555 !important;
            background: #fafbfd !important;
          }}
          [data-testid="stDownloadButton"] button p {{
            font-size: 0.78rem !important;
            margin: 0 !important;
          }}
          [data-testid="stDownloadButton"] button:hover {{
            border-color: {DEEP_NAVY} !important;
            color: {DEEP_NAVY} !important;
          }}

          /* ============= view-toggle 三按钮（品牌竞争图表切换） =============
             字号 0.92rem（同 .chart-title）；高度 ~30px（同 H2 内边距）；
             active 蓝底白字 / inactive 白底淡灰边；圆角 999px（椭圆胶囊） */
          .stButton button[kind="primary"] {{
            background-color: {DEEP_NAVY} !important;
            color: #fff !important;
            border: 1px solid {DEEP_NAVY} !important;
            font-weight: 600 !important;
            font-size: 0.92rem !important;
            border-radius: 999px !important;
            padding: 4px 16px !important;
            min-height: 0 !important;
            line-height: 1.4 !important;
          }}
          .stButton button[kind="primary"] p {{
            font-size: 0.92rem !important;
            margin: 0 !important;
          }}
          .stButton button[kind="secondary"] {{
            background-color: #fff !important;
            color: #262730 !important;
            border: 1px solid #d0d4dc !important;
            font-weight: 500 !important;
            font-size: 0.92rem !important;
            border-radius: 999px !important;
            padding: 4px 16px !important;
            min-height: 0 !important;
            line-height: 1.4 !important;
          }}
          .stButton button[kind="secondary"] p {{
            font-size: 0.92rem !important;
            margin: 0 !important;
          }}
          .stButton button[kind="secondary"]:hover {{
            background-color: #eef4fb !important;
            border-color: {DEEP_NAVY} !important;
            color: {DEEP_NAVY} !important;
          }}

          /* ============= 通用 ============= */
          .conclusion-box {{
            background: #f6f8fa; border-left: 3px solid {ACCENT};
            padding: 8px 12px; border-radius: 4px; margin-top: 6px;
            font-size: 0.85rem; line-height: 1.5;
          }}
          .chart-title {{
            font-size: 0.92rem; font-weight: 600; color: #2c3e50;
            margin: 6px 0 4px 0; padding-left: 4px;
          }}
          .small-caption {{ color:#6b7280; font-size: 0.82rem; }}

          /* 区段内图表间距 */
          .chart-spacer {{ height: 24px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def app_header():
    """全局共享大标题（每页顶部都渲染）"""
    st.markdown(
        """
        <div class='app-header'>
          Amazon 类目机会评分系统 · Demo
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_title(title, caption=None):
    """渲染深蓝渐变 H1 banner（当前页主题）"""
    sub = f"<div class='subtitle'>{caption}</div>" if caption else ""
    st.markdown(
        f"<div class='page-title-bar'><h1>{title}</h1>{sub}</div>",
        unsafe_allow_html=True,
    )


def chart_title(text):
    st.markdown(f"<div class='chart-title'>{text}</div>", unsafe_allow_html=True)


def chart_spacer():
    """同模块内图表间距"""
    st.markdown("<div class='chart-spacer'></div>", unsafe_allow_html=True)


def conclusion(text):
    st.markdown(f"<div class='conclusion-box'>📌 {text}</div>", unsafe_allow_html=True)

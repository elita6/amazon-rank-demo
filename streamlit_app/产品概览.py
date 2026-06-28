# streamlit_app/产品概览.py
# 更新日期：2026-06-23
# 用途：Demo 多页应用统一入口（编程式 st.navigation 路由）
#       负责：set_page_config（全局唯一）→ 注入样式 → 侧边栏语言切换 → 全局大标题 → 导航
#       导航标题随语言中英切换；每个 page 设稳定 ASCII url_path（与语言无关，保证落地页卡片链接 + 书签稳定）
# 启动命令：streamlit run streamlit_app/产品概览.py
# 主要改动：
#   - 2026-06-23：新建路由器。把原 pages/ 目录自动导航（菜单名=文件名，无法翻译）替换为
#                st.navigation 编程式导航，使左侧菜单可随 _i18n 语言开关中英切换。
#                ⚠️ 本文件即 Streamlit Cloud 入口（Main file path 不可在控制台改，故让
#                入口文件名保持 产品概览.py）；落地页正文移到 _landing.py 作为默认 page。

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "streamlit_app"))
sys.path.insert(0, str(ROOT))

from _i18n import t, lang_toggle
from _styles import inject_global_style, app_header

# set_page_config 必须是第一个 st 命令，且全应用仅此一处
st.set_page_config(
    page_title="Amazon Category Opportunity Scorer · Demo",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_style()
lang_toggle()          # 侧边栏顶部 中文 | EN
app_header()           # 全局大标题（双语）

# 导航：标题用 t() 随语言切换；url_path 固定 ASCII 不随语言变（落地页卡片链接据此跳转）
# 对齐生产 v2：5 页 —「头部品牌竞争」改名 + 删除独立「ASIN 流动性」页（黏性表已并入「跨榜联动」）
pages = [
    st.Page("_landing.py",             title=t("产品概览",   "Product Overview"),  url_path="overview",         default=True),
    st.Page("pages/1_类目详情.py",       title=t("类目详情",   "Category Detail"),    url_path="category-detail"),
    st.Page("pages/2_头部品牌竞争.py",   title=t("头部品牌竞争", "Head-Brand Competition"),  url_path="brand-competition"),
    st.Page("pages/3_跨榜联动.py",       title=t("跨榜联动",   "Cross-List Linkage"), url_path="cross-list"),
    st.Page("pages/4_类目综合评分.py",   title=t("类目综合评分", "Composite Score"),    url_path="composite-score"),
    st.Page("pages/5_行动指引.py",       title=t("行动指引",   "Action Playbook"),    url_path="action-playbook"),
]

st.navigation(pages).run()

# streamlit_app/_i18n.py
# 更新日期：2026-06-23
# 用途：Demo 看板中英双语切换核心机制（与生产仓 v1/streamlit_app/_i18n.py 同一套）
#       调用方式：from _i18n import t, get_lang, lang_toggle
#       - t(zh, en)        渲染时按当前语言取值，f-string 两侧各传一份
#       - get_lang()       读当前语言（"zh" / "en"）
#       - lang_toggle()    侧边栏顶部 中文 | EN 切换按钮（每页都渲染）
# 主要改动：
#   - 2026-06-23：新建。配合 st.navigation 编程式导航，给公开 Demo 加中英切换。
#                语言存 st.session_state["_lang"]，并写回 query_params 以跨页/刷新持久化。

import streamlit as st

_LANG_KEY = "_lang"
_DEFAULT = "zh"          # 默认中文；若要公开 Demo 默认英文改这里
_SUPPORTED = ("zh", "en")


def get_lang():
    """读当前语言。优先 session_state，其次 URL query param ?lang=，最后默认。"""
    if _LANG_KEY not in st.session_state:
        qp = st.query_params.get("lang")
        st.session_state[_LANG_KEY] = qp if qp in _SUPPORTED else _DEFAULT
    return st.session_state[_LANG_KEY]


def t(zh, en):
    """就地双语：t('类目概览', 'Category Overview')。"""
    return en if get_lang() == "en" else zh


def lang_toggle():
    """侧边栏语言切换。切换后写回 query_params 并 rerun，保证全页同步刷新。"""
    cur = get_lang()
    choice = st.sidebar.radio(
        "Language",
        list(_SUPPORTED),
        format_func=lambda c: "中文" if c == "zh" else "EN",
        index=_SUPPORTED.index(cur),
        horizontal=True,
        key="_lang_radio",
        label_visibility="collapsed",
    )
    if choice != cur:
        st.session_state[_LANG_KEY] = choice
        st.query_params["lang"] = choice
        st.rerun()

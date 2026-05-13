# demo/streamlit_app/_demo_data.py
# 更新日期：2026-05-12
# 用途：把 demo/data/*.csv 加载到 in-memory sqlite，让原 streamlit 页面 sqlite 查询零修改可用
# 同时提供 inline 版 market_heat_index（避免依赖 core.analytics.indicators）

from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CSV_TABLES = ["asin_daily", "category_summary", "category_daily_metrics"]


class _DemoConn:
    """sqlite3.Connection 透传 wrapper —— close() 改为 no-op，保留 in-memory db 在 cache 中。"""
    def __init__(self, conn):
        self._conn = conn

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@st.cache_resource(show_spinner=False)
def _build_memory_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    for tbl in CSV_TABLES:
        csv_path = DATA_DIR / f"{tbl}.csv"
        df = pd.read_csv(csv_path)
        df.to_sql(tbl, conn, index=False, if_exists="replace")
    # 关键索引（加速 archetype 详情页查询）
    conn.execute("CREATE INDEX IF NOT EXISTS idx_asin_cat ON asin_daily(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_asin_cat_list_date ON asin_daily(category, list_type, date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_cat ON category_daily_metrics(category, list_type, date)")
    conn.commit()
    return conn


def connect_demo(_path_ignored=None):
    """页面里把 sqlite3.connect(DB_PATH) 改成 connect_demo() 即可。
    _path_ignored 保留位参兼容，让改动最小。
    """
    return _DemoConn(_build_memory_db())


def market_heat_index(df, top_n=100, review_col="review_count",
                     price_col="price_low", date_col="date"):
    """市场历史价值指数 — 最近一天 BS Top100 的 log1p(review) × price 求和。
    来源：core/analytics/indicators.py:market_heat_index（inline 版避免 import 依赖）"""
    if df is None or df.empty:
        return None
    if date_col not in df.columns or review_col not in df.columns:
        return None
    dfv = df.dropna(subset=[review_col, price_col])
    dfv = dfv[dfv[price_col] > 0]
    if dfv.empty:
        return None
    latest = dfv[date_col].max()
    snap = dfv[dfv[date_col] == latest]
    if "rank" in snap.columns:
        snap = snap.nsmallest(top_n, "rank")
    else:
        snap = snap.head(top_n)
    if snap.empty:
        return None
    heat = (np.log1p(snap[review_col]) * snap[price_col]).sum()
    return float(heat) if heat > 0 else None

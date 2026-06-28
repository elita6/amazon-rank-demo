# streamlit_app/_brands.py
# 更新日期：2026-06-28
# 用途：品牌名归一化（去重口径统一）。供 类目详情 品牌数 / 头部品牌竞争 CR3 等共用，
#       让 Sony / SONY / Sony Inc. 归为同一品牌。纯规则、不做模糊匹配（不会误并 Sony 和 Sonos）。
#       （Demo 版：与生产 v2/streamlit_app/_brands.py 同一份纯函数，无外部依赖，逐字移植。）
# 主要改动：
#   - 2026-06-28 从生产 v2 移植：normalize_brand / build_display_map / brand_breakdown / cr3_pair

import re

import pandas as pd

# 公司后缀（出现在末尾才剥离）。实测本库几乎不出现，保留以覆盖通用情况。
_CORP_SUFFIXES = {
    "inc", "llc", "ltd", "co", "corp", "corporation", "company",
    "gmbh", "limited", "incorporated", "plc", "kg", "ag",
}


def normalize_brand(name):
    """原始品牌名 → 归一化 key。

    规则（按序，纯字符串、无模糊匹配）：
      ① 转小写 + 去首尾空格
      ② 去 ®/™ 符号
      ③ 连字符/点/逗号/下划线/斜杠 → 空格，多空格合一
      ④ 末尾若是公司后缀词（Inc/LLC/Ltd/Co/Corp…）剥离一次
      ⑤ 去掉所有空格 = key（"uni ball"/"uni-ball" → "uniball"）
    返回 key 字符串；空/None → None。
    """
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return None
    s = str(name).lower().strip()
    if not s:
        return None
    s = re.sub(r"[®™]", "", s)
    s = re.sub(r"[\s\.,\-_/]+", " ", s).strip()
    parts = s.split(" ")
    if len(parts) > 1 and parts[-1] in _CORP_SUFFIXES:
        parts = parts[:-1]
    key = "".join(parts)
    return key or None


def build_display_map(brands):
    """归一化 key → 展示名：取该 key 下出现频次最高的原始拼写。

    用于品牌竞争页等需要显示「干净品牌名」的场景（key 本身是无空格小写、不适合展示）。
    """
    s = pd.Series(brands).dropna()
    df = pd.DataFrame({"raw": s.values})
    df["key"] = df["raw"].map(normalize_brand)
    df = df.dropna(subset=["key"])
    # 频次最高的原始拼写作为展示名（并列时取字典序最小，稳定）
    disp = (
        df.groupby("key")["raw"]
        .agg(lambda x: x.value_counts().sort_index().idxmax())
        .to_dict()
    )
    return disp


def brand_breakdown(df, asin_col="asin", date_col="date",
                    brand_col="brand_norm", review_col="review_count"):
    """决策3 · 窗口累计去重 ASIN → 每品牌的份额表。

    每个 ASIN 一票：取其归一化品牌的众数 + 最新累计评论（最新一天值）。
    返回 (per_brand, n_asin)：
      per_brand：index=品牌，列 [asin_count, review_sum]，按 asin_count 降序。
      n_asin：去重 ASIN 总数（有品牌的）。
    """
    g = df.dropna(subset=[brand_col])
    if g.empty:
        return None, 0
    pa = (g.sort_values(date_col).groupby(asin_col)
            .agg(brand=(brand_col, lambda s: s.mode().iloc[0]),
                 review=(review_col, "last")))
    n = len(pa)
    if n == 0:
        return None, 0
    per = (pa.groupby("brand")
             .agg(asin_count=("review", "size"), review_sum=("review", "sum"))
             .sort_values("asin_count", ascending=False))
    return per, n


def cr3_pair(df, **kw):
    """决策3 · 返回 (Top3品牌份额[按ASIN], 同组review占比)。

    **同一组 top3**：按 ASIN 数选出前 3 品牌，看它们的两个份额：
    - Top3品牌份额(按ASIN) = 这 3 个品牌 ASIN 数之和 / 去重 ASIN 总数（货架）。
    - 同组 review 占比     = 这同 3 个品牌评论和 / 全部评论和（需求）。
    差值（review占比 − 份额）：>0 货架老大也赢需求 / <0 占货架但需求被别家拿走（me-too）。
    """
    per, n = brand_breakdown(df, **kw)
    if per is None or n == 0:
        return None, None
    top3 = per.head(3)                      # per 已按 asin_count 降序 = 同一组
    shelf = top3["asin_count"].sum() / n
    tot = per["review_sum"].sum()
    demand = top3["review_sum"].sum() / tot if tot > 0 else None
    return round(float(shelf), 3), (round(float(demand), 3) if demand is not None else None)

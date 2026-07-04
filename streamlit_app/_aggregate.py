# streamlit_app/_aggregate.py
# 更新日期：2026-07-04
# 用途：新版页专用「统一聚合口径」实现（决策1 聚合契约）。
#       （Demo 版：与生产 v3/streamlit_app/_aggregate.py 同一份纯函数，仅依赖 pandas，逐字移植。
#        Demo 无 core 包、无 config/scoring_config.yaml、无 PyYAML —— 见下方 excluded_categories 说明。）
# 主要改动：
#   - 2026-06-28 从生产 v2 移植：winsor_mean / demand_increment_index / demand_stock_index /
#       nr_to_bs_penetration / on_list_occupancy / bs_new_asin_ratio / ms_burst_winsor /
#       distribution_insights / crosslink_neg / fmt_compact / latest_review_repr
#   - 2026-07-04 同步生产 v3（方案C 后端，追加不改旧）：
#       new_brand_demand_share（决策14 新牌友好度 d，openness 第三腿，按 ASIN 坑位·时序占有率）、
#       nr_ms_penetration（NR→MS 渗透率，方案C 新品 Bonus + 新品生态象限 Y 轴）、
#       asin_review_crn（决策11 商品需求集中度 CRn，竞争结构页 Y 轴）、
#       excluded_categories（展示层黑名单接口）。
#       ——Demo core-free/dep-free 适配：excluded_categories 不读 scoring_config.yaml（Demo 无 config
#         目录 / 无 PyYAML），直接返回空集；Demo 数据由生成器上游已剔除黑名单类目（当前 18 类，无自营）。

import pandas as pd

# 决策1 缩尾分位（与归一化层 winsor_quantiles 同口径）
WINSOR_LOW, WINSOR_HIGH = 0.05, 0.95


def winsor_mean(series, low=WINSOR_LOW, high=WINSOR_HIGH):
    """决策1 · 数值水平型字段代表值。

    ① 按行汇总（传入的已是某类目的产品-天观测池）
    ② 在池上算 P_low/P_high
    ③ 缩尾：<P_low 设为 P_low、>P_high 设为 P_high（不删行只封顶）
    ④ 求平均 = 该类目代表值
    """
    s = pd.Series(series).dropna()
    if s.empty:
        return None
    lo, hi = s.quantile(low), s.quantile(high)
    return float(s.clip(lo, hi).mean())


def excluded_categories(root=None):
    """展示层黑名单接口（Demo 版：恒返回空集）。

    生产 v3 版读 config/scoring_config.yaml 的 category_overrides.excluded_categories，
    保证「评分排除的类目，展示也不出现」。Demo 无 config 目录 / 无 PyYAML，且 Demo 数据由
    生成器（tools/prepare_demo_data）上游已把黑名单类目剔除（当前 18 类，均非自营），
    展示层再排除即为 no-op —— 故此处直接返回空集，避免引入 yaml/config 依赖（保持 core-free/dep-free）。
    签名保留 root 位参与生产一致，页面 import 与调用零改动。
    """
    return set()


def _per_asin_increments(df, asin_col="asin", date_col="date",
                         review_col="review_count"):
    """每个 ASIN 的评论增量 = max(末日评论 − 初日评论, 0)，只保留 >=2 天且 >0 的。"""
    out = []
    for _, a in df.dropna(subset=[review_col]).groupby(asin_col):
        aa = a.sort_values(date_col)
        if len(aa) >= 2:
            rd = aa[review_col].iloc[-1] - aa[review_col].iloc[0]
            if rd > 0:
                out.append(float(rd))
    return out


def latest_review_repr(df, date_col="date", review_col="review_count",
                       low=WINSOR_LOW, high=WINSOR_HIGH):
    """最新累计评论（去极值）= 取该类目**最新一天**的快照，review_count 缩尾后求均值。

    评论是累计型变量（只增不减），代表值取「最新一天」而非跨天平均——跨天平均会把
    历史低值混进来、且被在榜久的产品按行 tenure 加权拉高（实测比最新累计高约 11%）。
    （价格/评分是稳定水平值，仍用全窗口 winsor_mean；累计型才取最新快照。）
    """
    if df is None or df.empty or date_col not in df.columns:
        return None
    d = df.dropna(subset=[review_col])
    if d.empty:
        return None
    latest = d[date_col].max()
    snap = d[d[date_col] == latest]
    return winsor_mean(snap[review_col], low, high)


def asin_review_crn(df, n=10, asin_col="asin", date_col="date",
                    review_col="review_count"):
    """决策11 · 商品需求集中度 CRn = 按**评论降序**前 N 个 ASIN 的评论占比。

    每个 ASIN 取最新累计评论（评论只增不减，取 last；与 brand_breakdown 同口径），
    再取评论最高的 N 个占全类目评论和之比。粒度 = 单商品(Listing)，不涉及品牌。
    openness 商品腿 + 竞争结构页 Y 轴用它。评论是销量代理，销量到位即 review→sales 一处替换。
    默认 n=10：商品粒度细、Top3 覆盖面太窄（业内商品集中度惯例即 Top10，见 改造依据.md 决策11）。
    """
    if df is None or df.empty:
        return None
    d = df.dropna(subset=[review_col])
    if d.empty:
        return None
    pa = d.sort_values(date_col).groupby(asin_col)[review_col].last()
    pa = pa[pa > 0]
    tot = pa.sum()
    if tot <= 0 or len(pa) == 0:
        return None
    top = pa.sort_values(ascending=False).head(n).sum()
    return round(float(top / tot), 4)


def demand_increment_index(df, asin_col="asin", date_col="date",
                           review_col="review_count", price_col="price_low"):
    """需求增量指数(月均)（无量纲，仅排序）= 评论增量 × 平均价格 × 30/统计天数。

    评论增量 = clip→mean( 每 ASIN 的评论增量 )；平均价格 = winsor_mean(价格)。
    **月均化（× 30/统计天数）**：评论增量是流量、会随窗口变长而变大，÷统计天数×30 折算成
    「月度评论增速」后窗口不变、可跨期参考（不改变同一窗口下的跨类目排序，仅常数缩放）。
    size-neutral；不依赖任何第三方数据。
    """
    if df is None or df.empty:
        return None
    days = df[date_col].nunique()
    if days < 1:
        return None
    price_rep = winsor_mean(df[price_col])
    increments = _per_asin_increments(df, asin_col, date_col, review_col)
    if not increments or price_rep is None:
        return None
    inc_rep = winsor_mean(pd.Series(increments))
    if inc_rep is None:
        return None
    v = inc_rep * price_rep * 30.0 / days
    return float(v) if v > 0 else None


def demand_stock_index(df, date_col="date", review_col="review_count",
                       price_col="price_low"):
    """需求存量指数（无量纲，仅排序）= 历史累计需求 = 最新累计评论(去极值) × 均价(去极值)。

    即「表里『最新累计评论』列 × 『均价』列」（两列相乘，最新一天基准）。
    与需求增量指数对称：增量用「评论增量」、存量用「最新累计评论」，价格因子同为均价(去极值)。
    """
    if df is None or df.empty:
        return None
    price_rep = winsor_mean(df[price_col])
    stock_rep = latest_review_repr(df, date_col, review_col)
    if stock_rep is None or price_rep is None:
        return None
    v = stock_rep * price_rep
    return float(v) if v > 0 else None


# =============================================================================
# 跨榜 / 流动性 共享函数（原内联在 2b / 3b 页面，抽出供评分引擎复用）
# 单位：渗透率 / 在榜率 = 0–100 标量；ms_burst = 原始 pct（%）缩尾均值
# 约定：传入「单个类目」的行切片（cat_df），返回该类目标量；None 表示无可算数据
# =============================================================================

def nr_to_bs_penetration(cat_df, src, list_col="list_type", asin_col="asin",
                         date_col="date", bs_value="best_seller"):
    """源榜(src) → BS 渗透率(0–100)：源榜首现日**严格早于** BS 首现日(lag>0)的
    去重 ASIN 数 ÷ 该源榜去重 ASIN 池 × 100（取自 跨榜联动 NR/MS→BS 渗透）。

    cat_df = 某一个类目的全榜行（含 BS 与 src 两种 list_type）。
    严格在前：剔除同天(lag=0)与反向(lag<0)，13 天窗口下多数类目接近 0（已知稀疏）。
    分母 = 源榜去重 ASIN 数（= 新品/爆款冲榜能力），无源榜数据返回 None。
    """
    if cat_df is None or cat_df.empty:
        return None
    src_rows = cat_df[cat_df[list_col] == src]
    pool = src_rows[asin_col].nunique()
    if pool == 0:
        return None
    bs_first = (cat_df[cat_df[list_col] == bs_value]
                .groupby(asin_col)[date_col].min())
    src_first = src_rows.groupby(asin_col)[date_col].min()
    common = bs_first.index.intersection(src_first.index)
    if len(common) == 0:
        return 0.0
    lag = (bs_first.loc[common] - src_first.loc[common]).dt.days
    valid = int((lag > 0).sum())
    return float(valid) / pool * 100.0


def on_list_occupancy(cat_df, asin_col="asin", date_col="date"):
    """在榜率(0–100) = winsor_mean(每 ASIN 在榜去重天数) ÷ 该类目实际采集天数 × 100
    （取自 ASIN 流动性；一直在榜=100%、按各类目自身天数归一化、跨类目可比）。

    cat_df = 某一个类目某一榜单(通常 BS)的行切片。
    """
    if cat_df is None or cat_df.empty:
        return None
    cat_days = cat_df[date_col].nunique()
    if cat_days < 1:
        return None
    life = cat_df.groupby(asin_col)[date_col].nunique()
    mean_life = winsor_mean(life)
    if mean_life is None:
        return None
    return float(mean_life) / cat_days * 100.0


def bs_new_asin_ratio(cat_df, asin_col="asin", date_col="date"):
    """采集期内 BS 新增 ASIN 比例(0–100) = 首现日晚于该类目最早采集日的去重 ASIN 数
    ÷ BS 去重 ASIN 总数 × 100（开放度的**补充参考**：头部榜被多少「中途上来的新面孔」占据）。

    cat_df = 某一个类目的 BS 行切片。首现日 = 该 ASIN 在 BS 的最早出现日；
    «新增» = 首现日 > 该类目 BS 最早采集日（即不是开窗第一天就在榜的「老面孔」）。
    注：仅作展示参考，**不进评分**（与 openness 的 cr3 集中度正交，ρ≈0.09）。
    """
    if cat_df is None or cat_df.empty:
        return None
    total = cat_df[asin_col].nunique()
    if total == 0:
        return None
    first_seen = cat_df.groupby(asin_col)[date_col].min()
    start = cat_df[date_col].min()
    new_n = int((first_seen > start).sum())
    return float(new_n) / total * 100.0


def ms_burst_winsor(cat_df, col="pct_chg_sales_rank"):
    """MS 排名平均提升率 = winsor_mean(pct_chg_sales_rank 中 > 0 的值)
    （取自 跨榜联动 MS 爆发强度类目排行口径：先取正向提升再缩尾均值）。

    cat_df = 某一个类目的 MS 行切片（或已 >0 过滤的切片，幂等）。
    """
    if cat_df is None or len(cat_df) == 0 or col not in cat_df.columns:
        return None
    pos = pd.Series(cat_df[col]).dropna()
    pos = pos[pos > 0]
    if pos.empty:
        return None
    return winsor_mean(pos)


# =============================================================================
# 自动解读（数据驱动模板化）：用画图的同一份数据算关键事实，供 _styles.insight_box 渲染。
# 纯 pandas，无 streamlit；不依赖任何 AI。
# =============================================================================

def fmt_compact(v, money=False):
    """大数字紧凑格式：1.2M / 34k / 560；money=True 前缀 $。"""
    if v is None or pd.isna(v):
        return "—"
    v = float(v)
    pre = "$" if money else ""
    a = abs(v)
    if a >= 1e6:
        return f"{pre}{v/1e6:.1f}M"
    if a >= 1e3:
        return f"{pre}{v/1e3:.0f}k"
    if money:
        return f"{pre}{v:.0f}"
    return f"{v:.0f}"


def distribution_insights(df, cat_col, val_col, id_col=None):
    """一张「各类目分布箱线图」的关键事实 dict。

    **只解读箱线图本身体现的量**（平均值不画、不在此读，留给「类目汇总」解读）：
    代表水平 = **中位价（箱线图中线）**；形态 = 右偏与否（内部用 均值>中位 检测，多数低少数高）；
    分散 = **相对分散度 CV**（归一化，不用绝对 IQR——绝对值会被高价位类目天然放大）；极值 = max。
    id_col 给定时附极值所在记录的 id（如 asin，供"单品极值→直链"用）。返回 None 或 dict：
      rep            类目→中位价 Series（供跨指标复用）
      rep_p25/p75    多数类目中位价落在此区间
      high_cat/val   中位价最高的类目及其值（+ 排名第 1）
      low_cat/val    中位价最低的类目及其值 / ratio 最高÷最低 倍数
      top_reps       中位价前 3 (cat, val)
      n_skew         右偏（平均价格(去极值) > 中位价）的类目数
      disp_high / disp_low 相对最分散 / 最集中（按 CV）的 2 个类目
      tail_cat/val/id 单值极值（长尾）最高的类目、其 max、其记录 id
      n_cat          参与类目数
    """
    sub = df.dropna(subset=[val_col])
    g = sub.groupby(cat_col)[val_col]
    rep = g.median().dropna()             # 代表值 = 中位价（箱线图中线，图上可见）
    if rep.empty:
        return None
    idx = rep.index
    mean = g.mean().reindex(idx)          # 用于 CV
    avg = g.apply(winsor_mean).reindex(idx)   # 平均价格(去极值)：仅用于判「平均>中位」=右偏（不展示为区间）
    cv = (g.std() / mean).reindex(idx).dropna()       # 相对分散度（归一化，可跨价位比）
    mx = g.max().reindex(idx)
    lo = float(rep.min())
    tail_id = None
    if id_col is not None and not sub.empty:
        tail_id = str(sub.loc[sub[val_col].idxmax(), id_col])
    return {
        "rep": rep,
        "rep_p25": float(rep.quantile(0.25)), "rep_p75": float(rep.quantile(0.75)),
        "high_cat": str(rep.idxmax()), "high_val": float(rep.max()),
        "low_cat": str(rep.idxmin()), "low_val": lo,
        "ratio": (float(rep.max()) / lo) if lo > 0 else None,
        "top_reps": [(str(k), float(v)) for k, v in rep.sort_values(ascending=False).head(3).items()],
        # 分布形态：右偏 = 平均价格(去极值) > 中位价（多数低、少数高，上须拉长）
        "n_skew": int((avg > rep).sum()),
        # 相对最分散 / 最集中（按 CV，不用绝对 IQR——绝对值会被高价位类目天然放大）
        "disp_high": [str(x) for x in cv.sort_values(ascending=False).head(2).index],
        "disp_low": [str(x) for x in cv.sort_values().head(2).index],
        "tail_cat": str(mx.idxmax()), "tail_val": float(mx.max()),
        "tail_id": tail_id,
        "n_cat": int(rep.size),
    }


def new_brand_demand_share(cat_df, list_col="list_type", date_col="date",
                           asin_col="asin", brand_col="brand_norm", review_col="review_count"):
    """决策14/15/16 · 新牌友好度 d = 新牌在 NR 榜占的坑位比例(按 ASIN 数,openness 第三腿)。

    **时序口径(决策15)**:老品牌 = 在 BS 榜「首现不晚于」其 NR 首现的品牌(first_BS ≤ first_NR);
    在 NR 上**严格早于** BS 出现的品牌(= NR→BS 毕业新牌)算**新牌**。首日平局(first_BS==first_NR)算老牌。
    **决策16:改按 ASIN 坑位(原按评论)** —— d = 非老牌的 NR ASIN 数 ÷ NR 总 ASIN 数。
    按评论易被单个评论重的产品带偏、且把「占据」误读成「吃需求」;按坑位更贴
    「老牌占据新品榜」本意、更稳(重测 0.92 vs 0.89)。展示「NR_BS品牌占有率」= 1 − d = 老牌坑位占比。
    日期用 ISO 串比较即按时间序。review_col 保留仅为签名兼容,本口径不使用。"""
    nr = cat_df[cat_df[list_col] == "new_release"].dropna(subset=[brand_col])
    bs = cat_df[cat_df[list_col] == "best_seller"].dropna(subset=[brand_col])
    if nr.empty:
        return None
    nr_first = nr.groupby(brand_col)[date_col].min()
    bs_first = bs.groupby(brand_col)[date_col].min() if not bs.empty else None
    # 每个 NR ASIN 的归一化品牌(众数);按坑位=每个 ASIN 一票
    amap = nr.groupby(asin_col)[brand_col].agg(lambda s: s.mode().iloc[0])
    tot = len(amap)
    if tot == 0:
        return None

    def _is_incumbent(b):
        # 老牌:BS 有该品牌 且 BS 首现 ≤ NR 首现(平局算老牌;NR 严格早于 BS = 毕业新牌,不算)
        if bs_first is None or b not in bs_first.index or b not in nr_first.index:
            return False
        return bs_first[b] <= nr_first[b]

    new = sum(1 for b in amap.values if not _is_incumbent(b))
    return round(float(new / tot), 4)


def nr_ms_penetration(cat_df, list_col="list_type", asin_col="asin", return_count=False):
    """NR→MS 渗透率 = 同时在 NR 和 MS 榜的去重 ASIN ÷ NR 去重 ASIN。
    新品在飙升榜出现=新品冲销量势能。方案C 的新品Bonus + 新品生态象限 Y 轴。
    return_count=True 时返回 (渗透率, overlap_count) 供零事件过滤。"""
    nr = set(cat_df[cat_df[list_col] == "new_release"][asin_col].dropna().unique())
    ms = set(cat_df[cat_df[list_col] == "movers_shakers"][asin_col].dropna().unique())
    if not nr:
        return (None, 0) if return_count else None
    cnt = len(nr & ms)
    pen = round(cnt / len(nr), 4)
    return (pen, cnt) if return_count else pen


def crosslink_neg(rep_a, rep_b, min_n=5, thresh=-0.3):
    """两个「类目→代表值」序列的跨类目**反向**关系（rank+pearson=spearman，无 scipy）。

    用于"A 越高 B 越低"这类跨指标发现。关系不够强（rho > thresh）或样本太少则返回 None
    （不强行输出洞察）。返回 dict：rho、A 最高者 top_a_cat、它在 B 上的降序排名 b_rank（1=最高）、
    样本数 n —— 供"最 A 的类目 B 却垫底"这种可追溯结论用。
    """
    idx = rep_a.index.intersection(rep_b.index)
    if len(idx) < min_n:
        return None
    a, b = rep_a.reindex(idx), rep_b.reindex(idx)
    rho = a.rank().corr(b.rank(), method="pearson")
    if rho is None or rho > thresh:
        return None
    top_a = a.idxmax()
    return {"rho": float(rho), "top_a_cat": str(top_a),
            "b_rank": int(b.rank(ascending=False)[top_a]), "n": int(len(idx))}

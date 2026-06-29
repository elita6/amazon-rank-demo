# i18n 术语表（中英对照）

> 更新日期：2026-06-29
> 用途：看板中英双语切换（`_i18n.py` 的 `t(zh, en)`）的**英文口径单一来源**。
> 所有页面 `t()` 的英文一律引用此表，避免同词多译。生产版与 Demo 仓共用同一口径。

## 系统 / 导航

| 中文 | English |
|---|---|
| Amazon 类目机会评分系统 | Amazon Category Opportunity Scorer |
| 基于 BS / NR / MS 三类榜单 · 多维评分 + 优先级分档 + 行动指引 | Powered by BS / NR / MS rankings · Multi-factor scoring + priority tiers + playbook |
| 类目详情 | Category Detail |
| 品牌竞争 | Brand Competition |
| 跨榜联动 | Cross-List Linkage |
| ASIN 流动性 | ASIN Liquidity |
| 类目综合评分 | Composite Score |
| 行动指引 | Action Playbook |
| 产品概览（Demo 入口） | Product Overview |

## 榜单 / 筛选

| 中文 | English |
|---|---|
| 综合（三榜合并） | All Lists (Merged) |
| BS / NR / MS | BS / NR / MS |
| 榜单 | List |
| 类目 | Category |
| 类目选择 | Category Filter |
| 全选 / 全不选 | Select All / Clear |

## 核心指标

| 中文 | English |
|---|---|
| 综合评分 | Composite Score |
| 市场历史价值指数 | Market Heritage Value Index |
| 预估月销售额($M/月) | Est. Monthly GMV ($M/mo) |
| 预估市场规模($M) | Est. Market Size ($M) |
| ASIN 数(去重) | ASINs (unique) |
| 品牌数(去重) | Brands (unique) |
| 分析类目数 | Categories analyzed |
| 数据时间范围 | Date range |
| 评论数 / 评论中位 | Reviews / Median reviews |
| 评分 / 评分中位 | Rating / Median rating |
| 价格 / 价格中位 | Price / Median price |
| 子类目数 | Subcategories |

## 5 维评分

| 中文 | English |
|---|---|
| 市场吸引力 | Market Attractiveness |
| 开放度 | Openness |
| 新品空间 | New-Product Room |
| 动能 | Momentum |
| 稳定性 | Stability |
| 综合机会分 | Opportunity Score |
| 优先级类型（Overall Rating） | Priority Tier (Overall Rating) |

## 优先级类型（5 档，综合分百分位）

| 中文 | English |
|---|---|
| 高潜机会类目 | High-potential |
| 较高机会类目 | Higher |
| 中性观察类目 | Balanced |
| 谨慎评估类目 | Watch |
| 暂不考虑类目 | Skip |

## 机会信号（百分位，仅 3 维参与）

> 仅「市场吸引力 / 开放度 / 结构稳定」三维参与；动能（方向歧义）、新品空间（数据稀疏）不打信号。
> 维度分 ≥P75 → 优势信号；≤P25 → 约束信号。

| 中文 | English |
|---|---|
| 优势信号 / 约束信号 | Strength signal / Constraint signal |
| 需求居前 / 需求居后 | Top-quartile demand / Bottom-quartile demand |
| 市场开放 / 品牌壁垒 | Open Market / Brand Barrier |
| 波动较小 / 波动较大 | Low volatility / High volatility |

## 类目象限（体量 × 增速）

| 中文 | English |
|---|---|
| 体量（需求存量指数） | Size (Demand Stock) |
| 增速（加速度＝增量/存量） | Growth speed (Increment/Stock) |
| 多 / 少（体量轴） | Many / Few |
| 快 / 慢（增速轴） | Fast / Slow |

## 行动指引模块

| 中文 | English |
|---|---|
| 重点 ASIN | Top Opportunity ASINs |
| 价格机会 | Price Gap |
| 市场窗口 | Market Window |
| 打法建议 | Playbook |
| 打开中 / 稳定 / 关闭中 | Opening / Stable / Closing |
| 评论缺口 | Review Gap |
| 评分百分位 | Rating Percentile |

> 注：旧的「13 业务类型（Archetype）」与「Top Pick / Hidden Gem / Crowded / Watch / Avoid」策略组
> 已废弃，统一改为上方「5 档优先级类型 + 机会信号」框架（口径见主项目指标解释 §4.4 / §4.5）。

## 通用 UI

| 中文 | English |
|---|---|
| 概览 | Overview |
| 画像 | Profile |
| 基础分布 | Distributions |
| 交叉分析 | Cross Analysis |
| 数据库不存在 | Database not found |
| 暂无数据 / 当前筛选下无数据 | No data available / No data for the current filter |
| 下载 CSV | Download CSV |
| 天 | days |
| 万件 / 件 | × 10k units / units |
| 时间窗口 / 近 N 天 | Time Window / Last N days |
| 全选 / 全不选 / 已选 | Select All / Clear / Selected |

## 实施时各页新增译法（2026-06-23，并入单一来源）

> 翻译执行中各页新造、术语表原先未收录的关键译法，登记于此供 Demo 仓复用同一口径。

| 中文 | English |
|---|---|
| 中位在榜时间(天) | Median time on list (days) |
| 满榜率 | Full-list rate |
| 流动率 / 日均流动率 | Turnover rate |
| 类目对比表 | Category Comparison |
| 流转漏斗 | Flow Funnel |
| MS爆发强度 | MS Burst Intensity |
| 排名提升率 | Rank Gain |
| 尾部倍数 | Tail ratio |
| 入口集 / 进 BS / 入口→BS% | Entry pool / Reached BS / Entry→BS% |
| 渗透率 | Penetration |
| 策略偏好设置 / 快速预设 | Strategy Preferences / Quick Presets |
| 保守型 / 增长型 / 爆发型 / 默认 | Conservative / Growth / Aggressive / Default |
| 权重总和（自动归一化） | Weight Sum (auto-normalized) |
| 综合机会分 / 结构稳定 | Opportunity Score / Stability Score |
| 数据置信度 | Data Confidence |
| 卡位难度 / 经营密度 / 一致性 | Barrier / Operating Density / Consistency |
| 竞争结构 / 运营形态 | Competition Type / Operating Profile |
| 强垄断 / 矩阵卡位 / 爆款主导 / 竞争均衡 / 竞争分散 | Strong Monopoly / Matrix Lock-in / Hit-Driven / Balanced Competition / Fragmented Competition |
| 头部 / 中坚 / 长尾 | Leader / Mid-Tier / Long-Tail |
| 全能 / 矩阵 / 精品 / 均衡 / 轻量 / 铺货 / 爆品 | All-Rounder / Matrix / Boutique / Balanced / Light / Volume / Hit |
| 稳定 / 高流动（留存后缀） | Stable / High Churn |
| 价格带 / 机会价格带 | Price Band / Opportunity price band |
| 低价带 / 大众带 / 高端带 / 超高端带 | Low / Mass / Premium / High Premium |
| 缺口 | Gap |
| 打开中 / 关闭中 / 稳定（市场窗口信号） | opening / closing / stable |
| 供给（ASIN 占比）/ 需求（sales_heat 占比） | Supply (ASIN share) / Demand (sales-heat share) |
| 特征 / 具体行动项 | Profile / Action items |
| 得分 / 阈值 | score / threshold |

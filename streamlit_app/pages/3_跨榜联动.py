# streamlit_app/pages/3_跨榜联动.py
# 更新日期：2026-07-04
# Demo 适配：数据源 data/amazon.db → data/*.csv（_demo_data.connect_demo）；类目/品牌已匿名化；
#   黑名单类目在 demo 数据生成时已剔除，去掉 excluded_categories；CAT_SHORT 对 demo 类目无映射、自动回退。
# 原文件：v3/streamlit_app/pages/2_跨榜联动.py
# 更新日期（原）：2026-07-03
# 用途：BS / NR / MS 三榜联动分析【方案C 对照版】— 由 2_跨榜联动.py 复制而来，原页一字不动便于并排对照。
# 方案C 新增（仅本文件，不影响原页）：
#   - 2026-07-03：视角1 类目流动性表 NR 组新增「→MS渗透率」列（走 _aggregate.nr_ms_penetration，
#       口径 = NR∩MS 去重ASIN / NR 去重ASIN，与「→BS渗透」写法一致，独立比例尺 + 青色数据条）。
#       这是本对照版相对原页 2_跨榜联动.py 的唯一差异。
#       （注：曾试加「新品生态象限图」+ NR_BS品牌占位率着色，后因与本表信息重复删除、相关代码全部还原。）
# ---- 以下为继承自原页 2_跨榜联动.py 的历史改动记录（未改）----
# 主要改动：
#   - 2026-07-01：删除「类目排名平均提升率排行」条形图的第三条解读（「少数爆款前10%高位是
#       均值N倍——爆发集中在个别单品」）。该句用 p90_pct，但本图只画平均值条、P90 仅在 hover，
#       且「集中在个别单品」是类目内分布结论，本图撑不起（宁可不说不瞎说）；清理仅服务它的 _cb2。
#   - 2026-06-30：合并双视角为单页滚动——删除 ASIN流动性 / MS爆发强度 的 2 按钮切换
#       （S4_VIEWS / s4_view / 按钮逻辑全删），改为同页依次呈现：① ASIN流动性（结构概览，
#       原默认落地）在上 → ② MS爆发强度（MS 专项）在下，两块各自 st.container 包裹、中间 chart_spacer。
#   - 2026-06-30：① 删除「每日排名平均提升率 by 类目」spaghetti 图 + 其解读——指标最噪
#       （MS 提升率被起点深度主导 + 每日换一批 ASIN）、11 天窗口撑不起「同步爆发」结论、
#       与上方类目排行条形图信息冗余（低信噪比，同决策9 砍图思路）。② BS 在榜率注解修正：
#       「生命周期越长」措辞错误（生命周期=生产到退市）→「头部款在榜越持久（同批畅销品长期占榜、
#       轮换慢）」。③ Top20 解读删「只有 X 个进过 BS」废话句（_nbs 一并清理）。
#   - 2026-06-30：Top20 爆发 ASIN 表的 ASIN 列改 LinkColumn（显示 ASIN、点击跳商品页），
#       对应解读首条去掉行内「查看商品」直链（链接已并入表内）。
#   - 2026-06-29：文案修正——BS 在榜率注解「越高=榜单固化」改为「越高说明头部产品生命周期越长」
#       （中英同步，不动计算口径）。
#   - 2026-06-29：排除子类目时叠加排除评分黑名单类目（_aggregate.excluded_categories，
#       当前 Amazon Devices——自营/已 pass/常为极端值），展示与评分引擎口径一致。
#   - 2026-06-28（视角重构）：原「NR/MS→BS渗透」视角（双源渗透率柱形图）替换为「ASIN流动性」
#       视角——把 ASIN流动性页的「类目黏性 & 新品活跃」表迁入，并扩列：BS 加「新增ASIN比例」
#       （开放度补充参考，走 _aggregate.bs_new_asin_ratio，不进评分）、NR 加「→BS渗透率」、
#       MS 加「→BS渗透率」。渗透率并入表后原柱形图删除。按钮 s4_view key lag_to_bs→liquidity。
#       在榜率/满榜率/流动率/渗透率口径与 ASIN流动性原页一致（满榜率/流动率本地内联同公式）。
#   - 2026-06-28：两个视角的主要图表下方各加「📊 解读」框（_styles.insight_box，数据驱动、
#       非 AI）。MS爆发强度：类目排行 / 每日提升率 / Top20 爆发单品（首条挂 ASIN 直链）；
#       NR/MS→BS 渗透：渗透率柱图（稀疏事实 + 两路径对比）。
#   - 2026-06-28（解读复查加强）：① 类目排行/Top20 改列前 3 名（含区间），不只报第 1；
#       ② 每日提升率删"波动大"废话（MS 日间波动是榜单天性），改判 Top5 单日高点是否同一天
#       （同步=全市场事件 / 分散=类目内部）；③ 渗透率解读已删 MS>NR 那句榜单天性废话（保留）。
#   - 2026-06-27 b：NR/MS→BS 渗透率 与 MS 排名平均提升率(类目排行) 改为调用 _aggregate.py
#                共享函数 nr_to_bs_penetration / ms_burst_winsor，与评分引擎同一份口径
#                （展示=评分）。渗透率改按「类目」逐个算（源榜首现严格在前÷源榜池），
#                原全局 merge 写法删除（口径不变；个别 ASIN 跨类目时按本类目计更准确）。
#   - 2026-06-27：① 删除「流转漏斗」视角（入口→BS→Top50→Top10）——无序交集 + 13天窗口左截断
#                + 同天共现污染，MS→BS 47% 实为反向，流转不成立。② 删两个上榜耗时图（同样的病）。
#                ③ NR/MS→BS 渗透率改口径：源榜首现日 **严格早于** BS（lag>0，剔同天/反向）、
#                分母改 **源榜去重 ASIN 池**（= 新品冲榜能力，与评分 nr_bs_overlap_pct 对齐）。
#                ⚠️13天窗口下稀疏（多数类目≈0），加 caveat。视角 3→2（删 funnel，默认 lag_to_bs）。
#                注：评分引擎 list_overlap 仍是无序交集口径，属「展示≠评分」，待综合评分页统一。
#                ④ MS爆发强度：排名提升率 中位→缩尾均值（决策1，ρ=0.984）；KPI/类目排行/每日曲线全改。
#                顺势删「头部倍数 P90/中位 + 普涨/黑马/强爆发」档位——P90/缩尾均值≈2.0 全员无区分度。
#   - 2026-06-25：新建（基于 2_跨榜联动.py，原页不动）。MS爆发强度视角的类目排行条图改读法：
#                ① 末尾文字按头部倍数(=P90÷中位)分白话档：普涨<3× / 有黑马3–10× / 强爆发>10×；
#                   条色改为按头部倍数的渐变色（YlOrRd，cmin/cmax=1/10），带 colorbar
#                ② hover 含中位/分布形态/P90/头部倍数/ASIN 数；「尾部倍数」统一改称「头部倍数」
#                ③ 下钻漏斗阶段名「曾在源榜出现」→「入口」；P90 KPI help 简化为「仅头部10%高于此值」
#                其余视角原样
#   - 2026-05-05 v1：新建。5 按钮：重叠全景 / 渗透率 / 流转漏斗 / MS 爆发强度 / 品牌动态
#                重叠全景 = 类目堆叠条形 + 三榜 Venn 图（手画 3 圆）并列对比
#                渗透率   = NR→BS / MS→BS 4 象限散点 + 类目排行表（迁移自 1_数据全貌）
#                流转漏斗 = funnel vs sankey 对比；4 阶段（停 Top10）vs 5 阶段（加「连续 14 天 Top10」）
#                MS 爆发强度 = 类目排行 + 每日规模/平均爆发双轴 + Top 20 爆发 ASIN
#                品牌动态 = 新品力 × 爆款命中率散点（颜色=跨榜身份 1-3）+ Top 30 品牌表
#   - 2026-05-06 v1.1：重叠全景重做：删类目筛选 + 删 Venn 图 + 删 3 KPI 卡片；
#                堆叠图保留（看绝对量）；新增「类目占比表」承接原 Venn 信息——
#                按类目呈现 7 段全部占比 + 进过 BS% / 三榜全在% 两个 KPI 列，
#                占比列统一用 ProgressColumn 条形图（min=0, max=100，跨列同尺度）。
#   - 2026-05-07 v2：编号互换 — 本文件从 4_跨榜联动.py 改名为 3_跨榜联动.py
#                （DV.3 改用于「跨榜联动」、DV.4 改用于「ASIN 流动性」）。新增第 6
#                视角「上榜耗时」— 从原 3_ASIN流动性.py（现 4_ASIN流动性.py）的
#                「BS 上榜耗时」整段迁移过来（含 v4-v4.7 所有改动：类目对比表 + box
#                plot + 4 路径分类象限图 + jitter + 短名映射 + 4 标签按源榜动态切换
#                等）。session_state key `s4_view` 保持原样未改名。新加 import
#                plotly.express as px + CAT_SHORT 字典（迁移代码使用）。
#   - 2026-05-07 v2.1：视角 1 重叠全景三处调整：① 类目堆叠图改成百分比堆叠（每条
#                100% 归一化，消除类目大小差异，hover 仍显原始 ASIN 数）；② "三栖"
#                重命名为"三榜全在"（更直观，强调 NR ∩ MS ∩ BS 同时命中）；③ 类目
#                占比表「类目」首列固定（pinned=True） + 数值列 width=small 让横向
#                滚动条出现，便于浏览 10 列细分时类目名一直可见。
#   - 2026-05-07 v2.2：视角 1 视觉再调：① 堆叠图 legend 从 y=1.05（顶部）改到
#                y=-0.32（底部），margin t=10→20、b=10→130，height 440→520，
#                legend 不再遮挡图表；② 占比表 ProgressColumn max 自适应 — 6 段
#                细分列共享 max=数据峰值 (≥10%)、三榜全在% 列单独 max=数据峰值，
#                进过 BS% 保持 max=100%（语义清晰）；列宽 small→medium 让数据条
#                有足够长度看出区别（之前 max=100 + width=small 让 5%/10% 数据条
#                视觉差几乎不可见）。
#   - 2026-05-07 v2.3：占比表 ProgressColumn 数据条 → 热力图（Styler.background_
#                gradient）— 数据条对小占比（< 5%）几乎无视觉差，热力图用颜色深浅
#                完美区分。色阶分配：6 段细分用 Blues 共享 max=数据峰值；进过 BS%
#                用 Greens（max=100% 语义清晰）；三榜全在% 用 Reds（max=自适应，
#                突出强 ASIN）。column_config 改 NumberColumn + width=small。
#                依赖：matplotlib（pandas Styler.background_gradient 用 cmap 时硬依赖）。
#   - 2026-05-07 v2.4：小数位调整 — 数据 round(1)→round(2)；删 Styler.format
#                改用 column_config 的 NumberColumn format="%.2f%%" 显示 2 位小数 +
#                % 后缀（之前 Styler.format 与 NumberColumn 默认渲染冲突，导致小
#                数位显示混乱）。
#   - 2026-05-07 v2.5：热力图配色与堆叠图图例严格对齐 — 6 段细分各用堆叠图同款
#                段色（白→段色渐变），三榜全在% 用同款红，进过 BS% 是聚合 KPI 无
#                单段对应，保留 Greens 区分。改用 LinearSegmentedColormap 自定义
#                cmap（每段一个独立 cmap = ["#ffffff", SEG_COLORS[seg]]）。
#   - 2026-05-07 v3：流转漏斗（视角 3）按类目重构 — 之前是所有选中类目合并算
#                4/5 阶段，看不出类目差异。删除 4 张图（4 阶段 funnel/sankey +
#                5 阶段 funnel/sankey）+ 类目 popover + 5 阶段（连续 14 天 Top10）+
#                sankey 函数；改成「上：类目对比表（每行类目 × 4 阶段绝对量 +
#                3 个留存率 + Blues 热力图色阶共享 max）」+「下：selectbox 下钻
#                + 选中类目 funnel 4 阶段细节」。源榜单切换（NR / MS / NR∪MS）保留。
#   - 2026-05-07 v3.2：MS 爆发强度（视角 4）concept 修正 + box plot 替换条形图：
#                ① 命名「爆发幅度」→「排名提升率」（更精准 — pct_chg_sales_rank
#                语义是销售排名跳升率，不是销量涨幅，避免误读）；caption 加公式
#                + 直观示例（#500→#365 = 27%）；② 类目排行从「条形图（中位 + P90
#                colorscale）」改为「横向 box plot（log_x，每行类目完整分布：P25 /
#                中位 / P75 + 须 P10/P90 + 离群点）」— 单一视觉编码、信息密度高、
#                与 DV.3.6 上榜耗时 box plot 风格统一。
#   - 2026-05-07 v3.3：box plot 替换为 Violin（A）+ ECDF（C）双图 — MS 长尾分布
#                让 box plot 右侧离群点过多、视觉杂乱。改成：A 横向 violin（密度
#                形状，长尾自然变细，内嵌小 box）+ C 横向 ECDF（每类目一条累积分布
#                曲线，中位 Top 5 用 Dark24 高亮、其他半透明）。两图视角互补：
#                violin 看分布形状，ECDF 看累积比例 + 类目间横向对比。
#   - 2026-05-07 v3.4：violin plot 修复 — plotly violin + log_x 已知 bug：KDE 在
#                log 空间退化为几条横线。改为手动 np.log10 变换数据画线性 violin，
#                然后 X 轴 tickvals/ticktext 把 [0,1,2,3,4,5] 显示为 [1%, 10%,
#                100%, 1k%, 10k%, 100k%]，视觉等同 log 刻度但 KDE 正确。
#   - 2026-05-07 v3.5：回退 — Violin（A）+ ECDF（C）双图都不直观，回退到 v3.1 的
#                条形图（中位升序 + P90 colorscale）。Box plot / Violin / ECDF 各
#                有问题（box 离群多 / violin 长尾不显著 / ECDF 太抽象），条形图虽然
#                需要对照颜色和数值但商业分析师最熟。conclusion 加 4 种组合解读
#                （中位 × P90 矩阵：全员普涨 / 个别黑马 / 强爆发 / 平稳）。
#   - 2026-05-07 v3.6：条形图加「尾部倍数 = P90 / 中位」— 单一数字直接判断分布
#                形状，不再依赖颜色 + 数值的心算合并。条形末尾文本由 "27%" 改成
#                "27% · 2.2×"（中位% · 尾部倍数×）；hover 加单独一行；conclusion
#                加倍数解读（≈2 普涨 / 5-10 有黑马 / >20 极投机）。

#   - 2026-05-07 v3.1：MS 爆发强度（视角 4）三处调整：① 删除类目 popover（同其他
#                视角统一原则，全选无意义）；② 平均值 → 中位数 + 加 P90（避开
#                pct_chg_sales_rank 极值拉偏，1000%+ 极端事件常见）— 类目排行用
#                中位数，颜色用 P90 强度，全量 metric 4 张：ASIN 数 / 中位 / P90 /
#                单条最大；③ 每日 MS 规模 + 平均爆发双轴 → spaghetti plot：19 类目
#                每日中位 排名提升率折线，Top 5 整体跳升最强类目用对比色高亮（红/橙/绿/蓝/紫），
#                其余类目淡灰背景，便于看「Top 5 同步爆发 = 全市场事件 vs Top 5 高
#                其他低 = 类目内部事件」；④ Top 20 表加「上次排名」列（来自
#                previous_sales_rank 字段，配合「当日排名」直观看跳幅），load_data
#                SQL 加该字段。
#   - 2026-05-08 v2.7：删「品牌动态」视角（原视角 5）。理由：品牌粒度散点更适合
#                指定具体类目做竞品分析，大类目筛选场景下信噪比低。代码连同
#                依赖说明抽到 other/spare/brand_dyn_view_260508.py 备用。
#                S4_VIEWS 6→5 项；bcols [1×6, 2] → [1×5, 3]；bcols[:6] → [:5]。
#   - 2026-05-08 v2.8：删「渗透率」视角（与 BS 上榜耗时口径重合，类目通道开放度
#                的信息已在耗时分布 + 4 象限里覆盖）。按钮重排 + 重命名以求一致：
#                重叠全景 → 三榜全景 / 上榜耗时 → BS上榜耗时 / "MS 爆发强度" → "MS爆发强度"
#                （去空格避免 5 字符按钮折行变宽）。新顺序：三榜全景 / 流转漏斗 /
#                BS上榜耗时 / MS爆发强度。bcols [1×5, 3] → [1×4, 2]，按钮等宽不折行。
#   - 2026-05-08 v2.9：BS上榜耗时（视角 3）类目对比表 → 柱形+折线双轴图。原表
#                ProgressColumn 4 列在 19 行下视觉散乱、难比较两源。新图同图叠
#                NR / MS：柱形 = 中位耗时（左 Y）/ 折线 = 渗透率（右 Y）；NR=
#                深蓝 #1f4e79 / MS=浅蓝 #a8cfee。按 NR 中位耗时升序。视角结构由
#                「单源 radio → KPI → 表 → box → 象限」改为「双源对比图（无 radio）
#                → radio → KPI → box → 象限」，先跨源横向概览，再切单源深挖。
#   - 2026-05-08 v3.0：BS上榜耗时（视角 3）箱体图同步双源化。原单源 px.box（受
#                radio 控制）→ 双源同图 px.box(color="src")，每类目并列 NR / MS
#                两个箱（深蓝 / 浅蓝），类目顺序与双源对比图统一为 NR 中位耗时升
#                序。box plot 移出 radio 块到顶部「跨源横向概览」分区。radio 现
#                仅控制 KPI 与 4 象限图。
#   - 2026-05-08 v3.1：双源对比图收敛为「单一指标」— 删 中位耗时 柱形 + 折线
#                改 柱形（双轴变单轴）。原图 4 trace（2 柱 + 2 线）→ 2 柱（NR /
#                MS 渗透率），双 Y 轴 → 单 Y 轴（渗透率 %），排序 nr_median 升序
#                → nr_rate 降序（与新图主指标对齐）。耗时分布交给下方 box plot
#                呈现（box plot 独立排序仍为 nr_median 升序）。
#   - 2026-05-08 v3.2：视角改名「BS上榜耗时」→「NR/MS→BS渗透」（按钮）+「NR/MS
#                →BS 渗透情况」（section header）。4 象限分类图 → 双散点图（左
#                NR / 右 MS），删 radio + 阈值线 + 4 区标签 + 4 区解读 conclusion +
#                单源 cmp 中间表 + 3 KPI 卡。轴标签改方向提示 X「← 快 慢 →」/
#                Y「↓ 难 易 ↑」，靠视觉直觉表达「左上=友好 / 右下=门槛高」。
#                radio 彻底删除，整个视角无源切换，全图都是双源并列展示。
#   - 2026-05-08 v3.3：双散点图坐标轴改为箭头线形式 — 隐藏默认 X / Y 轴线、刻
#                度、刻度文字、网格、零线；改用 add_annotation(showarrow=True,
#                arrowhead=2) 画水平箭头（X 向右）+ 垂直箭头（Y 向上）。轴端标
#                注「快 / 慢」（X 轴）+「难 / 易」（Y 轴）。具体数值仅 hover 可
#                见，图本身是「方向直觉」纯视觉表达。
#   - 2026-05-08 v3.4：v3.3 的箭头线 + 方向标签 保留，但补回 axis title（中位
#                耗时（天）/ 渗透率（%））+ tick marks（ticks="outside" + ticklen=5）
#                + tick labels（值有量纲），让坐标轴除了方向直觉之外也能读出具
#                体数值。「快 / 慢 / 难 / 易」从 paper 边界外移至图内（贴 X 轴
#                箭头上方 / Y 轴箭头右侧），避免与 tick label 与 axis title 抢
#                margin 空间。修正 axref/ayref 不接受 'paper'（仅接受 'pixel'
#                或 'x/y domain'），箭头注解改用 'x domain' / 'y domain'。
#   - 2026-05-08 v3.5：双散点图 4 个方向标签换位 + 染色：「快 / 慢」对齐 X 轴
#                方向沿底部水平同一 y（0.01）摆放，红色 #c0392b；「难 / 易」对
#                齐 Y 轴方向沿左侧竖直同一 x（0.01）摆放，绿色 #27ae60。修复重
#                叠类目标签 — 按源单独 override textposition：左图 NR→BS（Clothing
#                top / Tools bottom）；右图 MS→BS（Cell top / Home left / Arts
#                bottom / Clothing top-right / Health bottom-right）。其余类目保
#                持 cycle 4 方位的默认行为。
#   - 2026-05-08 v3.6：删除「三榜全景」视角（信噪比偏低 + 进过 BS% 是混淆指
#                标 + 6 段细分与堆叠图重复），代码连同依赖说明抽到 other/spare/
#                overlap_view_260508.py 备用。S4_VIEWS 4→3 项；bcols [1×4, 2]
#                → [1×3, 3]，bcols[:4] → bcols[:3]；默认 view 从 "overlap" 改
#                为 "funnel"；session_state 兼容：旧 key（含 "overlap"）残留时
#                回退到 "funnel"。删 matplotlib LinearSegmentedColormap 导入
#                （仅原视角用）。视角章节注释重新编号：流转漏斗 = 1 / NR/MS→
#                BS渗透 = 2 / MS爆发强度 = 3。
#   - 2026-06-23：UI 文案中英双语化（包 t()）配合语言切换

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "streamlit_app"))
from _styles import page_title, chart_title, conclusion, chart_spacer, insight_box
from _i18n import t
from _aggregate import (winsor_mean, nr_to_bs_penetration, nr_ms_penetration,
                        ms_burst_winsor, on_list_occupancy, bs_new_asin_ratio,
                        fmt_compact)
from _demo_data import connect_demo

LIST_LABELS_3 = {"best_seller": "BS", "new_release": "NR", "movers_shakers": "MS"}

# 19 大类长名 → 短名（视角 6 上榜耗时象限图散点 label 用，避免重叠；hover 仍显完整名）
CAT_SHORT = {
    "Amazon Devices & Accessories": "Amazon Dev",
    "Appliances": "Appliances",
    "Arts, Crafts & Sewing": "Arts/Crafts",
    "Automotive": "Automotive",
    "Beauty & Personal Care": "Beauty",
    "Camera & Photo Products": "Camera",
    "Cell Phones & Accessories": "Cell Phones",
    "Clothing, Shoes & Jewelry": "Clothing",
    "Computers & Accessories": "Computers",
    "Electronics": "Electronics",
    "Health & Household": "Health",
    "Home & Kitchen": "Home",
    "Kitchen & Dining": "Kitchen",
    "Musical Instruments": "Musical",
    "Office Products": "Office",
    "Patio, Lawn & Garden": "Patio",
    "Pet Supplies": "Pet",
    "Sports & Outdoors": "Sports",
    "Tools & Home Improvement": "Tools",
}


@st.cache_data
def load_data():
    conn = connect_demo()
    asin = pd.read_sql(
        "SELECT category, list_type, date, asin, brand, rank, "
        "sales_rank, previous_sales_rank, pct_chg_sales_rank "
        "FROM asin_daily",
        conn,
    )
    summary = pd.read_sql(
        "SELECT category, is_subcategory FROM category_summary",
        conn,
    )
    conn.close()
    asin["date"] = pd.to_datetime(asin["date"])
    return asin, summary


def category_popover(key_prefix, cats, label=None):
    """同 ASIN 流动性 / 类目详情 popover 风格。"""
    if label is None:
        label = t("类目选择", "Category Filter")
    inner = f"{key_prefix}_cats_inner"
    if inner not in st.session_state:
        st.session_state[inner] = list(cats)
    n_sel, n_tot = len(st.session_state[inner]), len(cats)

    def _all():
        st.session_state[inner] = list(cats)

    def _none():
        st.session_state[inner] = []

    st.markdown(f"<div class='filter-label'>🔍 {label}</div>", unsafe_allow_html=True)
    with st.popover(t(f"已选 {n_sel} / {n_tot}", f"Selected {n_sel} / {n_tot}"),
                    use_container_width=False):
        b1, b2 = st.columns(2)
        b1.button(t("✓ 全选", "✓ Select All"), key=f"{key_prefix}_btn_all",
                  on_click=_all, use_container_width=True)
        b2.button(t("✗ 全不选", "✗ Clear"), key=f"{key_prefix}_btn_none",
                  on_click=_none, use_container_width=True)
        st.multiselect(t("勾选类目", "Select categories"), options=cats,
                       key=inner, label_visibility="collapsed")
    return st.session_state[inner] or list(cats)


def filter_label_spacer():
    st.markdown("<div class='filter-label' style='visibility:hidden;'>·</div>",
                unsafe_allow_html=True)


# =======================================================================
# 页面
# =======================================================================
page_title(t("跨榜联动", "Cross-List Linkage"))

asin_all, summary = load_data()

# 默认排除子类目（Demo 数据生成时已剔除黑名单类目）
drop_set = set(summary[summary["is_subcategory"] == 1]["category"].tolist())
asin_all = asin_all[~asin_all["category"].isin(drop_set)]
summary = summary[~summary["category"].isin(drop_set)].copy()
main_cats = sorted(asin_all["category"].unique().tolist())


# =======================================================================
# 视角 1：ASIN 流动性（迁移自原 3_ASIN流动性.py 类目黏性表）
#   BS：在榜率 + 满榜率（黏性，二者均进 stability 评分，算法不动）+ 新增ASIN比例（开放度补充参考）
#   NR：流动率（新品活跃）+ →BS渗透率
#   MS：→BS渗透率
#   渗透率并入表后，原「NR→BS / MS→BS 渗透率」柱形图删除。
#   on_list_occupancy / nr_to_bs_penetration / bs_new_asin_ratio 均走 _aggregate 共享函数。
# =======================================================================
with st.container(border=True):

    bs_all = asin_all[asin_all["list_type"] == "best_seller"]
    nr_all = asin_all[asin_all["list_type"] == "new_release"]

    def _full_rate(sub):
        """满榜率 = 在该类目实际采集天数里一直在榜的 ASIN 占比（与 ASIN流动性原页同口径）。"""
        if sub.empty:
            return None
        cat_days = sub["date"].nunique()
        life = sub.groupby("asin")["date"].nunique()
        if life.size == 0:
            return None
        return float((life == cat_days).sum()) / life.size * 100.0

    def _flow_rate(sub):
        """流动率 = 每日平均换手率 (新增+流失)/2/在榜数（与 ASIN流动性原页同口径）。"""
        if sub.empty:
            return None
        ds = sub.groupby("date")["asin"].apply(set).sort_index()
        prev, rates = None, []
        for d in ds.index:
            cur = ds[d]
            hc = len(cur)
            if prev is None:
                prev = cur
                continue
            rates.append((len(cur - prev) + len(prev - cur)) / 2 / hc * 100 if hc else 0.0)
            prev = cur
        return (sum(rates) / len(rates)) if rates else None

    rows_data = []
    for cat in main_cats:
        cat_df = asin_all[asin_all["category"] == cat]
        bs_c = bs_all[bs_all["category"] == cat]
        nr_c = nr_all[nr_all["category"] == cat]

        def _nz(v):   # None → np.nan，保证列为 float 可排序/格式化
            return np.nan if v is None else v

        def _pct(v):  # 0–1 比率 → 0–100 百分数，与其他渗透列同标度（方案C：nr_ms_penetration 返回比率）
            return np.nan if v is None else v * 100.0
        rows_data.append([
            cat,
            _nz(on_list_occupancy(bs_c)),                        # BS 在榜率（评分用）
            _nz(_full_rate(bs_c)),                               # BS 满榜率（评分用）
            _nz(bs_new_asin_ratio(bs_c)),                        # BS 新增ASIN比例（开放度补充参考）
            _nz(_flow_rate(nr_c)),                               # NR 流动率（新品活跃）
            _nz(nr_to_bs_penetration(cat_df, "new_release")),    # NR→BS 渗透率
            _pct(nr_ms_penetration(cat_df)),                     # NR→MS 渗透率（方案C 新增，比率→%）
            _nz(nr_to_bs_penetration(cat_df, "movers_shakers")), # MS→BS 渗透率
        ])

    columns = pd.MultiIndex.from_tuples([
        ("", "类目"),
        ("BS", "在榜率"), ("BS", "满榜率"), ("BS", "新增比例"),
        ("NR", "流动率"), ("NR", "→BS渗透"), ("NR", "→MS渗透"),
        ("MS", "→BS渗透"),
    ])
    show = pd.DataFrame(rows_data, columns=columns)
    show = show.sort_values(("BS", "在榜率"),
                            ascending=False, na_position="last").reset_index(drop=True)

    # 各指标数据条比例尺：百分制(在榜/满榜/新增)直接 0–100；流动率/渗透率按自身峰值放大（渗透极小，
    # 不放大会看不出差异）。NR 与 MS 的「→BS渗透」共用同一峰值 → 两列可直接比。
    def _col_max(metric):
        vals = pd.concat([show[c].dropna() for c in show.columns if c[1] == metric],
                         ignore_index=True)
        return float(vals.max()) if not vals.empty else 0.0
    flow_max_pct = max(_col_max("流动率") * 1.1, 10.0)
    pen_max_pct = max(_col_max("→BS渗透") * 1.1, 1.0)
    nrms_max_pct = max(_col_max("→MS渗透") * 1.1, 1.0)   # 方案C：NR→MS 独立比例尺（数值极小）

    chart_title(t(
        "● 类目ASIN流动性(按 BS 在榜率降序)",
        "● Category ASIN liquidity (by BS on-list desc)"))

    BORDER = "2px solid #aaa"
    SCALE = {"在榜率": 100.0, "满榜率": 100.0, "新增比例": 100.0,
             "流动率": flow_max_pct, "→BS渗透": pen_max_pct, "→MS渗透": nrms_max_pct}
    BAR_GRADIENTS = {
        "在榜率":   ("#cfe1f3", "#5b8fc4"),   # 浅蓝 → 深蓝
        "满榜率":   ("#cfeedc", "#27ae60"),   # 浅绿 → 深绿
        "新增比例": ("#e8dcf5", "#8e6bbf"),   # 浅紫 → 深紫
        "流动率":   ("#fbe1c4", "#e67e22"),   # 浅橙 → 深橙
        "→BS渗透":  ("#f8d2d2", "#c0392b"),   # 浅红 → 深红
        "→MS渗透":  ("#cdeeea", "#16a085"),   # 浅青 → 深青（方案C 新增）
    }
    METRIC_LABELS = {
        "在榜率":   t("在榜率", "On-list %"),
        "满榜率":   t("满榜率", "Full-list %"),
        "新增比例": t("新增比例", "New-ASIN %"),
        "流动率":   t("流动率", "Turnover %"),
        "→BS渗透":  t("→BS渗透率", "→BS pen."),
        "→MS渗透":  t("→MS渗透率", "→MS pen."),
    }
    GROUPS = [
        ("BS", ["在榜率", "满榜率", "新增比例"]),
        ("NR", ["流动率", "→BS渗透", "→MS渗透"]),
        ("MS", ["→BS渗透"]),
    ]

    def _cell_html(val, metric, first_in_group):
        cls_extra = " group-start" if first_in_group else ""
        if pd.isna(val):
            return f'<td class="empty-cell{cls_extra}">—</td>'
        scale = SCALE[metric]
        pct = min(val / scale * 100, 100) if scale > 0 else 0
        light, dark = BAR_GRADIENTS[metric]
        bg = (f"background: linear-gradient(90deg, {dark} 0%, {light} {pct:.2f}%, "
              f"transparent {pct:.2f}%);")
        return f'<td class="bar-cell{cls_extra}" style="{bg}">{val:.1f}%</td>'

    parts = ['<table class="lifespan-cmp">', "<thead>", "<tr>"]
    parts.append(
        '<th rowspan="2" class="corner-cell">'
        f'<span class="corner-top">{t("榜单", "List")}</span>'
        '<svg viewBox="0 0 100 100" preserveAspectRatio="none">'
        '<line x1="0" y1="0" x2="100" y2="100" stroke="#aaa" stroke-width="0.8"/>'
        "</svg>"
        f'<span class="corner-bot">{t("类目", "Category")}</span>'
        "</th>"
    )
    for grp, metrics in GROUPS:
        parts.append(f'<th colspan="{len(metrics)}" class="group-start">{grp}</th>')
    parts.append("</tr>")

    parts.append("<tr>")
    for grp, metrics in GROUPS:
        for i, m in enumerate(metrics):
            cls = "sub-h group-start" if i == 0 else "sub-h"
            parts.append(f'<th class="{cls}">{METRIC_LABELS[m]}</th>')
    parts.append("</tr></thead><tbody>")

    for _, row in show.iterrows():
        parts.append("<tr>")
        parts.append(f'<td class="cat-cell">{row[("", "类目")]}</td>')
        for grp, metrics in GROUPS:
            for i, m in enumerate(metrics):
                parts.append(_cell_html(row[(grp, m)], m, first_in_group=(i == 0)))
        parts.append("</tr>")
    parts.append("</tbody></table>")

    css = f"""
<style>
.lifespan-cmp {{
border-collapse: collapse; font-family: inherit; font-size: 13px;
background: white; width: 100%; table-layout: auto;
}}
.lifespan-cmp thead th {{
background-color: #f0f4f8; font-weight: 600; padding: 6px 10px;
text-align: center; border-bottom: 1px solid #aaa; white-space: nowrap;
}}
.lifespan-cmp tbody td {{
padding: 4px 10px; border-bottom: 1px solid #e8e8e8;
text-align: right; font-variant-numeric: tabular-nums;
}}
.lifespan-cmp .group-start {{ border-left: {BORDER} !important; }}
.lifespan-cmp .corner-cell {{
position: sticky; left: 0; z-index: 3;
min-width: 107px; width: 107px; height: 56px;
background-color: #f0f4f8; padding: 0 !important;
border-right: 1px solid #d0d4dc;
}}
.lifespan-cmp .corner-cell svg {{
position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;
}}
.lifespan-cmp .corner-top {{ position: absolute; top: 4px; right: 10px; font-weight: 600; font-size: 12px; }}
.lifespan-cmp .corner-bot {{ position: absolute; bottom: 4px; left: 10px; font-weight: 600; font-size: 12px; }}
.lifespan-cmp .cat-cell {{
position: sticky; left: 0; z-index: 2; font-weight: 500;
text-align: left !important; white-space: nowrap;
background-color: white !important; border-right: 1px solid #d0d4dc;
}}
.lifespan-cmp .empty-cell {{ color: #aaa; text-align: center !important; }}
</style>
"""
    st.markdown(
        css + f'<div style="overflow-x: auto; max-width: 100%;">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='font-size:0.68rem; color:#6b7280; line-height:1.7; margin-top:6px;'>"
        + t("* BS 在榜率：该类目 BS ASIN 平均在榜天数 / 采集天数；越高说明头部款在榜越持久（同一批畅销品长期占榜、轮换慢）",
            "* BS on-list %: avg BS ASIN days-on-list / sampled days; higher = bestsellers stay on the list longer (slower turnover at the head)")
        + "<br>"
        + t("* BS 满榜率：整段采集期天天在榜的常驻款占比；高在榜率 + 高满榜率 = 少数款霸榜，高在榜率 + 低满榜率 = 广泛轮动",
            "* BS full-list %: share always on every day; high on-list + high full-list = a few dominate, high on-list + low full-list = broad rotation")
        + "<br>"
        + t("* BS 新增比例：采集期内才首次上榜（非开窗第一天就在）的 ASIN 占比，越高说明头部越多「新面孔」",
            "* BS new-ASIN %: share of ASINs that first appeared after the window opened; higher = more newcomers in the head")
        + "<br>"
        + t("* NR 流动率：NR 榜每天平均有百分之几的 ASIN 被替换，越高说明新品更替越快、越活跃",
            "* NR turnover %: avg share of NR ASINs replaced per day; higher = faster new-product churn")
        + "<br>"
        + t("* →BS 渗透率：先在源榜（NR/MS）出现、之后又进 BS 的去重 ASIN ÷ 源榜去重 ASIN",
            "* →BS penetration: unique ASINs that appeared on the source list (NR/MS) first then reached BS ÷ unique source-list ASINs")
        + "<br>"
        + t("* NR→MS 渗透率：在 NR 与 MS 均出现过的去重 ASIN ÷ NR 去重 ASIN——新品被榜单识别为「飙升」的比例，越高说明新品越能冲起来（13 天窗口下多数类目≈0，仅相对参考）",
            "* NR→MS penetration: unique ASINs appearing on both NR and MS ÷ unique NR ASINs—share of new products the lists flag as movers; higher = new products break out more (near 0 for most categories in a 13-day window—relative reference only)")
        + "</div>",
        unsafe_allow_html=True,
    )

    # 解读：从「类目特点」出发综合多指标给结论（哪类封闭、哪类开放），不逐列念数；
    #   类目名按数据动态选取（满榜率 top3 / 在榜率 bottom3 / NR 流动率 top3）。
    _on, _full_c = ("BS", "在榜率"), ("BS", "满榜率")
    _flow_c = ("NR", "流动率")

    def _cats(dfsub, k=3):
        return "、".join(f"<b>{r[('', '类目')]}</b>" for _, r in dfsub.head(k).iterrows())

    _closed = show.dropna(subset=[_full_c]).nlargest(3, _full_c)   # 较封闭：满榜率最高
    _open = show.dropna(subset=[_on]).nsmallest(3, _on)            # 较开放：在榜率最低
    _nr_top = show.dropna(subset=[_flow_c]).nlargest(3, _flow_c)   # 新品洗牌最快：NR 流动率最高

    _items = []
    if not _closed.empty:
        _items.append(
            t(f"{_cats(_closed)} 的 BS 头部**榜位轮换慢**，常驻款占着位子（满榜率最高、在榜率也居前），新上来的 ASIN 较少。",
              f"{_cats(_closed)} have **slow BS-head turnover**—a permanent core holds the spots "
              f"(highest full-list rate, also high on-list), with fewer newly-added ASINs."))
    if not _open.empty:
        _items.append(
            t(f"{_cats(_open)} 的 BS 头部**榜位轮换快**，在榜率与满榜率较低、新增 ASIN 占比较高（此处指坑位换手快，与品牌集中度无关）。",
              f"{_cats(_open)} have **fast BS-head turnover**—lower on-list and full-list rates with a higher "
              f"share of newly-added ASINs (this is slot churn speed, not brand openness)."))
    if not _nr_top.empty:
        _items.append(
            t(f"单看新品端，{_cats(_nr_top)} 的 NR 新品池洗牌最快——上新最频繁、新品流动性最强。",
              f"On the new-product side, {_cats(_nr_top)} churn their NR pool fastest—the most frequent, fluid launches."))
    _items.append(
        t("→BS 渗透率均较低，因为 13 天窗口下两周内冲进 BS 是稀有事件，仅作相对参考。",
          "→BS penetration is low across the board: within a 13-day window, breaking into BS in two weeks is rare—relative reference only."))
    insight_box(_items)

chart_spacer()

# =======================================================================
# 视角 2：MS爆发强度
# =======================================================================
with st.container(border=True):
    st.markdown(t("**● MS爆发强度**", "**● MS Burst Intensity**"))

    df = asin_all[asin_all["list_type"] == "movers_shakers"].copy()
    df = df.dropna(subset=["pct_chg_sales_rank"])

    if df.empty:
        st.warning(t("无 MS 数据", "No MS data"))
    else:
        n_asin = df["asin"].nunique()
        wm_pct = winsor_mean(df["pct_chg_sales_rank"])
        p90_pct = df["pct_chg_sales_rank"].quantile(0.90)
        max_pct = df["pct_chg_sales_rank"].max()

        cs1, cs2, cs3 = st.columns(3)
        cs1.metric(t("MS 涉及 ASIN 数", "ASINs in MS"), f"{n_asin:,}")
        cs2.metric(t("排名平均提升率", "Avg Rank Gain"), f"{wm_pct:,.0f}%",
                   help=t("(上次排名 − 当日排名) / 上次排名 × 100%",
                          "(previous rank − current rank) / previous rank × 100%"))
        cs3.metric(t("单条最大", "Single max"), f"{max_pct:,.0f}%")

        chart_spacer()
        chart_title(t("● 类目排名平均提升率排行",
                      "● Category avg rank-gain ranking"))
        df_pos = df[df["pct_chg_sales_rank"] > 0]
        # 排名平均提升率走共享函数 ms_burst_winsor（= winsor_mean(pct>0)），
        # 与评分引擎 momentum「MS排名平均提升率」同一份口径（展示=评分）。
        cat_burst = (df_pos.groupby("category")
                     .apply(lambda g: pd.Series({
                         "wmean_pct": ms_burst_winsor(g),
                         "p90_pct": g["pct_chg_sales_rank"].quantile(0.90),
                         "n_asin": g["asin"].nunique()}))
                     .reset_index().sort_values("wmean_pct", ascending=True))

        fig1 = go.Figure(go.Bar(
            x=cat_burst["wmean_pct"], y=cat_burst["category"],
            orientation="h",
            marker=dict(
                color=cat_burst["wmean_pct"], colorscale="YlOrRd",
                showscale=False,
                line=dict(color="white", width=0.5),
            ),
            customdata=cat_burst[["p90_pct", "n_asin"]].values,
            hovertemplate=t("%{y}<br>平均提升率 %{x:,.0f}%"
                            "<br>P90 %{customdata[0]:,.0f}%"
                            "<br>ASIN 数 %{customdata[1]:,.0f}<extra></extra>",
                            "%{y}<br>Avg rank gain %{x:,.0f}%"
                            "<br>P90 %{customdata[0]:,.0f}%"
                            "<br>ASINs %{customdata[1]:,.0f}<extra></extra>"),
            text=[f"{v:,.0f}%" for v in cat_burst["wmean_pct"]],
            textposition="outside",
            cliponaxis=False,
        ))
        fig1.update_layout(
            height=max(360, 26 * len(cat_burst)),
            xaxis_title=None,
            yaxis_title=None,
            margin=dict(l=10, r=60, t=10, b=10),
        )
        st.plotly_chart(fig1, width="stretch")

        # 解读：cat_burst 即条图数据（wmean_pct=平均提升率, p90_pct, n_asin）。
        #   复查加强：列前 3 名 + 区间 + 断层，不只报第 1。
        _cb = cat_burst.sort_values("wmean_pct", ascending=False).reset_index(drop=True)
        _nc = len(_cb)
        _hi, _lo = _cb.iloc[0], _cb.iloc[-1]
        _top3 = "、".join(f"<b>{r['category']}</b> {r['wmean_pct']:,.0f}%" for _, r in _cb.head(3).iterrows())
        # 只保留条形图直接支撑的两条（最高/最低 + IQR 区间）。
        # 原第三条「少数爆款前10%是均值N倍/集中在个别单品」用 p90_pct，但本图只画平均值条、
        # P90 仅在 hover，且「集中在个别单品」属类目内分布结论——本图撑不起，删除（宁可不说不瞎说）。
        _items_b1 = [
            t(f"MS <b>排名平均提升率</b>最高的几个类目：{_top3}；最低的 <b>{_lo['category']}</b> 只 {_lo['wmean_pct']:,.0f}%。",
              f"Highest MS <b>avg rank gain</b>: {_top3}; the lowest, <b>{_lo['category']}</b>, just {_lo['wmean_pct']:,.0f}%."),
            t(f"多数类目排名平均提升率落在 {_cb['wmean_pct'].quantile(0.25):,.0f}%–{_cb['wmean_pct'].quantile(0.75):,.0f}% 之间。",
              f"Most categories' avg rank gain falls between {_cb['wmean_pct'].quantile(0.25):,.0f}% and {_cb['wmean_pct'].quantile(0.75):,.0f}%."),
        ]
        insight_box(_items_b1)

        chart_spacer()
        chart_title(t("● Top 20 爆发 ASIN（按单条最大 pct_chg 排序）",
                      "● Top 20 burst ASINs (by single-event max pct_chg)"))
        top_evt = (df.sort_values("pct_chg_sales_rank", ascending=False)
                   .drop_duplicates("asin").head(20).copy())
        bs_asins = set(asin_all[asin_all["list_type"] == "best_seller"]["asin"].unique())
        top_evt["进过BS"] = top_evt["asin"].apply(
            lambda a: "✓" if a in bs_asins else "—")
        show_evt = pd.DataFrame({
            "ASIN":     top_evt["asin"].apply(lambda a: f"https://www.amazon.com/dp/{a}"),
            t("品牌", "Brand"):     top_evt["brand"].fillna("—"),
            t("类目", "Category"):     top_evt["category"],
            t("事件日期", "Event date"): pd.to_datetime(top_evt["date"]).dt.strftime("%Y-%m-%d"),
            t("上次排名", "Previous rank"): top_evt["previous_sales_rank"].apply(
                lambda v: f"{int(v):,}" if pd.notna(v) else "—"),
            t("当日排名", "Current rank"): top_evt["sales_rank"].apply(
                lambda v: f"{int(v):,}" if pd.notna(v) else "—"),
            t("排名提升率", "Rank gain"): top_evt["pct_chg_sales_rank"].apply(lambda v: f"{v:,.0f}%"),
            t("进过 BS", "Reached BS"): top_evt["进过BS"],
        })
        st.dataframe(show_evt, hide_index=True, width="stretch",
                     height=min(560, 38 + 36 * len(show_evt)),
                     column_config={
                         "ASIN": st.column_config.LinkColumn(
                             "ASIN", display_text=r"/dp/(\w+)"),  # 显示 ASIN，点击跳商品页
                     })

        # 解读：top_evt 即 Top20 表数据；ASIN 直链已移到表内 ASIN 列，解读不再挂链接
        _e1 = top_evt.iloc[0]
        _ntop = len(top_evt)
        _ccat = top_evt["category"].value_counts()
        _cc_top = "、".join(f"<b>{c}</b> {int(v)} 个" for c, v in _ccat.head(3).items() if v > 1) or f"<b>{_ccat.index[0]}</b> {int(_ccat.iloc[0])} 个"
        _prev = f"#{int(_e1['previous_sales_rank']):,}" if pd.notna(_e1['previous_sales_rank']) else "—"
        _cur = f"#{int(_e1['sales_rank']):,}" if pd.notna(_e1['sales_rank']) else "—"
        insight_box([
            t(f"最猛单品销售排名从 {_prev} 跳到 {_cur}（提升 {_e1['pct_chg_sales_rank']:,.0f}%），属 <b>{_e1['category']}</b>。",
              f"The hottest item jumped in sales rank from {_prev} to {_cur} (+{_e1['pct_chg_sales_rank']:,.0f}%), in <b>{_e1['category']}</b>."),
            t(f"爆发单品最多的类目：{_cc_top}——这 {_ntop} 个里有 {int(_ccat.head(3).sum())} 个来自它们。",
              f"Categories with the most burst items: {_cc_top}—{int(_ccat.head(3).sum())} of the {_ntop} come from them."),
        ])

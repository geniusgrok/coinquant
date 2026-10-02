# Active alpha/beta mechanism round —2026-10-02

User approved all eight directions; spec/protocol/plan in research/alpha-beta-*. BTC-only, current consensus/incumbent baselines and original economics/native gates unchanged. Worktree pair /workspace/btc-alpha-beta-next/{spotquant,coinquant}; original mains remain unchanged. Progress ledger is this existing file; task briefs/reports/diffs are external /workspace/btc-alpha-beta-next/review.

Ruling: use mirrored external worktrees to preserve existing ../coinquant/../starquant paths without modifying market/FX inputs — cost if wrong: path repair, not economic changes.
Ruling: use existing PROJECT_STATE/HANDOFF rather than an additional SDD progress file to honor repository continuity rules — cost if wrong: manual reconstruction of task status; commits/reports remain retained.

| Preflight | Producer / consumer or constraint | Result |
|---|---|---|
| Task1 self | Coin four fixed mechanisms plus incumbent; real runner/audit, no default change | consistent |
| Task2 self | Spot six fixed variants plus consensus;20/80 core subpools and real ownership | consistent |
| Task3 self | actual raw curves/calibration, timestamp validation, no scaling | consistent |
| Task4 self | all48+10risk, conditional combos, Coin robustness, reviewed adoption | consistent |
| Task1/3 | Coin nested results + opportunity_ledger consumed by evaluator | fixed schema, preserve source/input hashes |
| Task2/3 | Spot flat results + opportunity_ledger consumed by evaluator | fixed schema, keep consensus baseline |
| Task1/4 | frozen Coin engine, later selected bridge equivalence | no core edits while financial worker active |
| Task2/4 | frozen Spot engine/core ledger, later selected bridge equivalence | no core edits while financial worker active |
| Task3/4 | deterministic calibration/combo output, completed inputs | false complete/native never promote |

Ruling: matched economic selection constraints compare identical stress scenes on unscaled actual accounts; separately rerun training-calibrated base accounts for achieved risk/alpha diagnosis — because the spec separates selection from risk-match claims; cost if wrong: add a risk-based adoption constraint before promotion.
Ruling: test the exact all-compatible eligible combination, never subsets; if that combination is rejected keep the best eligible singleton, ranking any accepted combo by the same worst-stress CAGR with singleton priority on ties — because an unevaluated or inferior combination cannot justify default replacement; cost if wrong: combination remains research-only.

Ruling: Coin trailing high excludes the 4h bar that overlaps actual entry; only bars opening at/after confirmed entry contribute high, with initial anchor at the actual fill — avoids a pre-entry wick becoming a stop under the completed-bar spec; cost if wrong: conservatively later tightening, fully disclosed before outcomes.

Task1: complete — source c2a01d1 + attribution fix31e8b1e; 359 offline checks,13focused and exact real three-session no-op monetary equality. Independent spec PASS/quality APPROVE at ../review/task1-fix1-review.md. Full-window/economic evidence remains Task4; production unchanged.
Task2: running /root/alpha_spot_implementation; BASEa3aed915 (Spot); requirements/report ../review/task2-brief.md /task2-report.md. Task3: pending; Task4: pending.
Ruling: core cold-start retains saved-checkpoint/entries_after/new-day and original execution gates, without a tactical SMA200 fresh-cross latch; original three tactical signals unchanged — permanent core otherwise gains an unregistered initial timing rule; cost if wrong: conservative comparison requires a separately registered variant, never post-outcome switching. Protocol clarified before any full new outcome.


--- Previous completed delivery ---

# Coinquant 当前状态（2026-10-01）

2026-10-01 第三轮入口：`evidence/third-round-20261001/RESULT.md`。
三个固定候选完成795次共同历史模型会话，完整现金核账通过。Coin默认
119.23%/44.11%，Star默认−3.68%/51.75%，半风险−1.27%/38.21%。
使用实际session/runner，snapshot桥接仍是简化代理，原生请求图、撮合和
30日证据未通过。共同模型下保留Coin合约、Spot现货，Star仅研究；不迁移
亏损候选、不晋升或退休运行器。Coin距150%目标差30.77个百分点，NOT_MET。
经济原件对应Coin源码00a6849、Star882b521，后续只读导出/核账工具不是
这个历史记录的源码身份。335项Coin离线检查通过。默认参数不改，新增
原生只读snapshot及Spot双账户并行采集；本轮无账户请求或交易，原生
NOT_QUALIFIED。以下前两轮及M10是其各自明确源码身份的历史记录。

2026-10-01 第二轮：`evidence/second-round-20261001/RESULT.md`。三个合约
固定候选有九项口径待对齐，因此不排名。五组逐请求/周期诊断精确复现 M10
成交前缀，费用造成的钱包与请求数量分歧已有事件证据；六项本机执行案例
通过。生产逻辑不改，没有新的完整六年测量，经济 NOT_MET、原生 NOT_QUALIFIED。

2026-10-01 首轮交付：`research.path_analysis` 与
`evidence/path-analysis-20261001/RESULT.md`。已归因 M10 费用、滑点、深度与
读取时延差异，并用当前源码复现两个三会话成交前缀。未发现可证明的生产
缺陷，默认风险和执行逻辑保留；没有新的完整六年经济测量。长期目标为
一个 BTC 合约项目与 Spotquant；Starquant 继续作为合约研究候选。

## 系统

Binance BTCUSDT U 本位永续，单账户、单向逐仓、交易所20×。手动启动一个有限会话（默认300秒、每5秒轮询），会话内反复“核对→决策→执行”，超时或中断后在120秒预算内收尾；没有后台进程。生产路径：`CLI → session.run → Campaign → Lifecycle → Binance`，持久化意图、成交、资金流水与每轮观察都在状态目录的 `intents.sqlite`。

默认模型 SX60＋DFII10：4小时 impulse-hold 多头主信号，风险尺度7.5（`coinquant.campaign.PRIMARY_RISK`；O1 曾降到6，R3 在测量器 M8 上按登记规则重选回7.5）；空仓且主信号无可执行多头时，DFII10 近值较第20个前值下降≥0.25个百分点触发3.6尺度宏观多头，整笔持仓止损损失≤入场权益3%。默认模型不开空。

默认 `run` 与 `status` 只读；`run --execute` 仅在显式 Demo 或专用小额主网试验参数满足时开放同一执行链。此入口不代表常规生产资格；资格 `NOT_QUALIFIED`。本轮未使用任何账户凭据、未发交易请求。

## 受控验证阶段（2026-09-28）

| 项目 | 工程状态 | 已验证 | 未验证与限制 |
|---|---|---|---|
| 未知订单恢复 | 移除时间＋一次 -2013 的不可逆拒绝，旧 `absent_at_ms` 原位重开核对 | 301 秒迟到查询、已成交加仓归属、明确本地拒绝的定向离线测试 | 交易所真实迟到查询及历史过期缺口 |
| 首次保护 | 终态原生订单复用，分别持久记录入场发送尝试、成交证明、止损发送尝试/接受/账户回读时点 | 1 秒每请求离线注入：首个止损发送 24→23 秒；失败减仓与重启局部测试 | Demo 实际时延、止损与开仓非原子窗口 |
| 受控入口 | 默认只读；显式 Demo 与主网试验共用 `session.run`/`Lifecycle`/Binance | 凭据隔离、写授权和 UID/资金门本地测试 | Demo UID、保护与订单接口原生语义 |
| 独占账户 | 固定 UID/环境/状态目录和本机锁；外部成交及持仓归属检查继续生效 | 状态作用域、外部同量重新开仓阻断的定向测试 | 跨机器并发不受本机锁保护，试验只支持一个独占客户端 |
| 原生闭环 | Demo 与主网配置和命令已给出；主网要求审查后的 Demo 证据且源码摘要匹配 | 未运行原生账户 | 实际成交、止盈止损、重启、退出及停进程后的保护触发全部待验证 |
| 资金边界 | 正值 `capital_limit_usdt` 为试验写入必选；专用小额主网账户由所有者隔离 | 参数门与现有数量/保证金预检定向测试 | 上限不是亏损保证；试验总额与停止条件待所有者确定 |

工程就绪：可由所有者准备 Demo 凭据和账户后先只读核对，再明确启动 Demo。Demo 原生验证：未运行。小额主网：入口默认关闭，Demo 证据及专用资金尚未提供。经济资格：仍为 `NOT_MET`；下面的 M10 是当前源码的测量，M9 与 P7/M7 对应更早源码。具体配置与命令见 README。

## 本轮附件复核与代码审查（2026-09-29）

- C1：旧完整止盈/止损仍核验有效且持仓归属已证明时，未完成的价格替换不再抢在模型退出之前阻断只减仓；持有时仍按原身份重试替换，未知入场余量或归属不明继续冻结。
- C2：钱包双读观察区间与初始资金锚点一起持久保存。晚发布、事件时间明确早于首次钱包观察的流水不重复计入后续变动；边界内同毫秒事件保持未知，不推测钱包与流水的原子顺序。旧状态没有初始区间证据，仍按旧保守逻辑处理，不自动重置余额差额。
- O1：每次有限会话完成一致 SQLite 备份、最近三份会话副本轮转，备份失败在报告中标注。拒绝其他机器近期写入者时不再先改写元数据。本地同盘副本需要所有者另行保存到别处才能抵御整盘丢失。
- 额外审查：假交易所、经济测量器与原生形状回放器中，正数但不足一毫秒的等待现在至少推进一毫秒，避免截止边界无限循环。受影响的离线测试覆盖此边界。

| 附件项 | 本轮核对与处理 |
|---|---|
| C1/C2 | 离线反例修复并加入正常、失败边界测试；旧资金锚点缺少可信时间证据时继续保守拒绝。 |
| C3 | 入场、补保证金与保护非原子；保留短路径和限时失败减仓，不宣称断网时零裸露窗口。 |
| C4 | 入场身份及成交关联无法证实时不接管等量仓位；可靠证据不可用时保留未知。 |
| C5 | 新保护被拒或未知时保留旧完整保护；证实归属的只减仓出口不再被替换挡住。 |
| C6 | `capital_limit_usdt` 是规模输入而非累计止损保险；配置、报告、说明一致。 |
| C7 | 单项目本机账户锁仍在；同 UID 跨项目共管不受支持，也不宣称跨机器/项目互斥。 |
| C8 | 新风险继续受身份、归属与资金审计门限制；已证实的保护和只减仓保留原有授权路径。 |
| O1 | 每次会话一致备份、有限轮转；失败在报告提示，同盘损坏仍需异地副本。 |
| O2 | 超出成交/流水保留期、状态丢失或旧锚点无法解释的差额仍须停止和人工核对；无自动重锚或通用归档导入。 |
| O3/O4 | 手动有限会话停止后不再作策略决策；DFII10 来源/时区不可用时相关新决策保守停止。 |
| R1/R2 | 默认仅做多；当前结果是 M10，M9/R3/P7 按各自源码身份保留。 |
| R3–R5 | 逐笔成交量只给 IOC 上界，分钟级止损没有完整跳空/深度回放，历史费用/档位/规则有固定代理；原始盘口/历史规则与逐笔输入缺失，不伪称已消除。 |
| R6/R7 | 历史结果对成本、时延、会话路径敏感，同窗口多轮研究不算前向样本；不事后改风险参数。 |
| R8/R9 | 历史 29 分钟标记价缺口沿用所有者接受的有界假设；FRED 人民币估值和 USDT 平价不代表可执行兑换。 |
| R10/R11 | M10 基准有 688 次观察超时、`execution_unresolved` 为 0；流水/日收盘不能补成停机期间连续权益或完整 MDD。 |
| S1–S5 | 只展开改动分支、保留既有终态归档与单一路径、单一短 CI；无性能热点证据时不引入新缓存或策略。 |

本轮执行源码摘要（`coinquant/*.py`）`37586959860c8f72db8cad09dbbaf6ced01802813807847910053ddeb54bed75`；经济源码摘要（受跟踪的 `coinquant/*.py` 与 `research/*.py`）`6504a24b18932e0d3dd3bfc5b73fc77dae89da546c069e4753e200bc3ec380f0`。323 项离线测试通过；真实账户接口、成交与时延均未运行。M10 已用这份 Python 和冻结输入重测，见 `evidence/remeasure-20260929-m10/RESULT.md`。

## 经济测量（测量器 M8，当前源码 M10）

`research.rebuild` 在 `research.session_exchange.SessionExchange` 上运行同一个 `session.run`/`Lifecycle`，冻结795个会话起点（`research/session_schedule.json`）；读请求占200 ms模拟时间（`--read-latency-ms`，0 复现旧 M7），写请求1000 ms。2020-01-01至2026-09-20（右端不含），人民币10,000元。下表是当前源码的 M10（经济源码摘要 `6504a24b…`，`git_head` `07d78ec`，风险7.5）。账户数字与旧 M9 相同。更早 R3 的 ¥2,794,265／131.26% 只对应 `evidence/robustness-20260929/m8/`。

| 场景 | 期末人民币 | 成本后 CAGR | 连续 MDD 包络 |
|---|---|---|---|
| 基准，风险 7.5 | 1,893,613 | 118.24% | 44.51% |
| 手续费 +50% | 2,406,523 | 126.17% | 44.79% |
| 出场滑点 ×2 | 2,118,221 | 121.92% | 44.87% |
| 深度取用 10% | 2,583,258 | 128.57% | 44.51% |
| 随机跳过 20% 会话 | 909,932 | 95.69% | 45.39% |
| 缺席序列 / 21 天空窗 | 1,893,613 | 118.24% | 44.51% |

MDD 达标，CAGR 未达150%目标；`economic_qualification` 为 `NOT_MET`。同一 R3 规则在 M10 的日历年区块上仍然选中 7.5，`PRIMARY_RISK` 不改。全窗口终值对风险不单调（6／6.5／7／7.5：¥1.70M／2.02M／2.21M／1.89M，7 最高），对读延迟敏感（风险6在100／200／400 ms：¥2.54M／1.70M／0.88M）。手续费 +50%、出场滑点 ×2 和深度取用 10% 的终值高于基准，随机跳过低于基准，都是路径结果，不是稳定估计；压力 MDD 最高 45.39%。基准观察超时 688 次，未决执行 0。2020-01-19 13:09–13:37 UTC 缺29分钟官方标记价而账户持仓；所有者2026-09-28接受以实测标记/成交偏离作边界（`path_complete=false`）。原件：`evidence/remeasure-20260929-m10/`；旧 M9 原件仍在 `evidence/remeasure-20260929/`。规则实现 `research/risk_select.py`。

审计发现（`evidence/robustness-20260929/RESULT.md`）：
- 历史 P7（¥5,228,630，153.86%）只在源码 `a6892b3`/`883d16a` 复现；后续生产修复改变每分钟请求权重使用，M7 上同一默认参数测得 ¥0.9–3.4M（O0）。M8 修复了该测量噪声（权重上限2000–1,000,000终值相同）；M7 的 O0／O1 数字作废，O1 的开发区块 MDD ≤40% 规则由所有者确认的 ≤45% R3 规则取代。
- 脉冲倍数、ATR 窗口、持有根数、止损回撤、止盈次幂各挪一档，全窗口 CAGR 降到40–102%（中位约91%），模型常数在尖峰上；没有单参数改动通过采纳规则，信号常数不变。
- 收益集中（M7、风险6）：风险6去掉最好3个月后 CAGR 38%；2024–2026三年分别 +44%、+1%、−9%。滚动1年窗口65%低于150%。

口径与各轮修正见 `research/redesign-PROTOCOL.md`，测量局限与旧 M7 结果见 `evidence/rebuild-20260927/RESULT.md`。

## 审计修复状态（C01–C13）

全部为离线代码与测试修复；真实账户行为未验证。范围限制：C08 没有外部归档/检查点导入入口（超期恢复仍返回未知）；C10 的部分场景沿用既有测试。详见 `evidence/audit-fixes-20260929/RESULT.md`。第二轮全项目审查（`evidence/full-review-20260929/RESULT.md`）又修复26项，并列出未改动的范围限制：入场未知意图与持仓并存时不自动保护、收入审计无重新锚定入口、条件单不存在不可证明、收入 `tranId` 去重未经真实样本核对、分钟级止损无跳空成交假设。此前同输入基准回归 REG2 为 ¥1,893,613／118.24%／MDD 包络44.51%，与 REG 逐字段相同（历史源码摘要 `ae7b3fd8…`）。同一组场景在当前源码上由 M10 重测，账户结果与 M9 相同，见 `evidence/remeasure-20260929-m10/RESULT.md`。

## 未完成

- 原生验证：真实成交后保护建立的时间窗口、重复 close-all 接受行为、超时/迟到成交、交易所断连、明确拒绝错误码与文档规定失败的503、-2013 查询与签名过期（recvWindow）后不再接受的语义、保证金历史结算、Demo 环境语义（`evidence/bounded-session-20260926/RESULT.md`）。先在 Demo（`environment: demo`）验证，再在单独授权的专用小额余额（`capital_limit_usdt`）上验证；需要指定账户和当次明确交易授权。
- 默认模型只做多，没有开空路径。
- 最近一次完成的历史测量没有找到同时满足 CAGR ≥150% 且 MDD <50% 又不落在参数尖峰上的配置；本次源码没有新的完整历史结果；没有前向证据，开发/检验划分不是干净的样本外。
- 超过成交历史（约3个月）与资金流水窗口（约88天未观察）后恢复只能返回未知；没有外部归档导入入口。实盘连续权益与 MDD 没有可核验的重建。
- Windows 等无系统时区库的环境需要 `tzdata`。

## 数据

行情 vision 文件在 `/data/coinquant-market`（`python -m research.session_market --root ...` 下载并校验），逐日 aggTrades 在 `/data/coinquant-prints`，缓存在 `/data/coinquant-prints-cache`；三者不入库，只在当前机器磁盘上。丢失后的下载、校验和缓存重建写在 `research/redesign-PROTOCOL.md` 的「行情输入恢复」。DEXCHUS、ALFRED DFII10、2019年12月预热行情、合约规则随仓库提交并按 SHA-256 校验。

## 仓库

只保留当前版本。旧 Bybit/反向合约实现、稀疏调用规格与抽签、历史候选研究及证据已于2026-09-28删除，需要时从 Git 历史 `3e9a696` 及以前取回。本轮删除无人引用的重复 `main.py` 入口，修正过时的只读注释与账户报告字段。旧 `absent_at_ms` 恢复仍保留：已有状态目录中的误拒订单可能迟到成交，必须按原身份核对，不能为了删兼容代码而跳过。

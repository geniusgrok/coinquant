# 第二轮全项目审查（2026-09-29）

状态：`NOT_QUALIFIED`，`economic_qualification` 仍为 `NOT_MET`。没有下单、账户或资金操作。

三组只读审查（适配器与安全层、生命周期与状态、研究测量器与文档）逐项读调用方后给出候选，下表是逐项处理结果。“已修复”均有离线调用链测试（`tests/test_full_review.py`、`tests/test_session_history.py`、`tests/test_rebuild_safety.py`、`tests/test_robustness.py`、`tests/test_acceptance.py`）；没有真实账户验证。

## 已修复

| 编号 | 问题 | 处理 |
|---|---|---|
| A1 | 已加仓持仓上，加仓/减仓订单被 `-2013` 证明不存在后仍因“账户非空仓”永远未知，`blocking()` 使模型退出停摆 | 减仓单在保留期内被证不存在即可退休（只会减仓）；加仓仅当持仓仍等于准备时记录的 `position_before_btc` 且无入场残单；入场仍要求空仓 |
| A3 | `http.client.HTTPException`（`IncompleteRead`、`BadStatusLine`）绕过 `Unknown` 直接抛出，中断周期与清理 | `_request`、`align_clock` 均按 `Unknown` 处理；DFII10 读取同样覆盖 |
| A4 | 写入门比所有权规则宽：订单 DELETE 不要求 `cq-`，减仓单不限类型 | 订单 DELETE 只接受 `symbol`+`origClientOrderId=cq-…`；减仓只接受 MARKET |
| A5 | 剩余不足时仍发写请求，几乎必然变成未知 | 写请求需至少 `MIN_WRITE_SECONDS=2` 秒，否则明确“未发送”（`ObservationDeadline`） |
| A6 | 时钟采样接受任意往返时延；`/time` 的 418/429 无冷却 | 往返超过1秒不采用；418/429 与其他请求共用冷却 |
| A7 | 保护与退出依赖全量 `exchangeInfo`，2 MB 上限 | 上限提高到 8 MB |
| A8 | 算法单撤单可能返回字符串 `"code":"200"`，被判未知 | 按字符串比较 |
| L1 | 恢复路径的两处兜底 `close()` 没有预留观察预算 | 两处先 `reserve(REDUCE_SECONDS)` |
| L2 | 信号恰好落入最终清理会中止 `finish()` | 清理内 `KeyboardInterrupt` 重试一次（之后的信号已被处理器忽略） |
| L3 | 清理前一次时钟采样失败就跳过整个验证 | 记录 `cleanup_clock` 错误并继续 `finish()` |
| L6 | 周期末尾未保护的收入审计失败会丢掉本周期已做的动作 | 审计失败记为 `income_audit: unresolved`，周期结果保留 |
| L7 | `main` 只捕获部分异常，其余成为裸 traceback | 捕获所有异常，报告 `unknown` 及 `error_type` |
| L8 | DFII10 单元格非数字（`InvalidOperation`）绕过 60 秒退避，每 5 秒重取 | 捕获 `ArithmeticError`、`csv.Error`、`zlib.error`、`EOFError`、`HTTPException` |
| L9 | 相对 `state_dir` 会在另一工作目录变成新的空状态 | 配置要求绝对路径或 `~` |
| L10 | 写入者主机声明只在打开时写一次，超过10分钟的会话失效 | 每次 `state.report` 刷新 |
| R1 | 保护替换重叠期仪表把“最后一条”止损当作生效止损，Binance 会先触发更保守的一条 | `_live()` 取先触发的那条（多头最高止损/最低止盈，空头相反），触发的算法单被标记完成 |
| R6 | 仪表接受立即触发的保护单；无仓位的 reduce-only 返回 200/EXPIRED | 返回原生 `-2021`、`-2022` 的 HTTP 400，生产分类器按 `Rejected` 处理 |
| R7 | 资金费结算缺官方标记价时，仪表用入场价当标记（编造输入） | 改为 `Unknown` |
| R8 | `risk_select.select` 的 `stress_ok` 参数从未使用，与协议文字不符 | 被否决的候选被剔除；缺失压力不否决 |
| R9 | 证据原件替换先改名后写入，崩溃后当前名消失 | 先硬链接保留原件，再一次 `os.replace` |
| R10 | 合约规则快照无摘要绑定 | `RULES_SHA256` 校验并写入 `market_identity.contract_rules_sha256` |
| R11 | 稳健性脚本复用任何已存在的临时结果 | 仅当记录的源码摘要与当前一致才复用 |
| R12 | 缺席序列没有固定摘要 | `ABSENCE_SHA256` 校验 |
| R13 | 仪表 kline 返回未结束分钟；`positionMargin` 忽略类型和余额 | 不返回未结束 K 线；类型≠1 或超过可用余额返回原生 400 |
| R14 | 验收测试是自证；文档里的数字未与证据文件核对 | `test_recorded_numbers_are_the_ones_in_their_evidence_files` 对照证据 JSON |
| R15 | CI 路径过滤含已删除的 `main.py`，遗漏示例配置；主分支连续推送互相取消 | `config*.json`；只对 PR 取消旧运行 |

## 范围限制与未验证项（没有改代码）

- 未证明父订单的入场未知意图与已有持仓并存时，保护与减仓不会自动执行：所有权规则要求入场成交经完整历史证明后才保护；`settle()` 因此保留“未知即阻断”。需要操作员按原订单身份查询后处理。
- 收入审计超过89天保留窗口，或钱包缺口长期未解释，会永久阻止新增风险，没有“空仓 + 操作员确认”的重新锚定入口；恢复需要人工。
- 算法（条件）单的“不存在”不可证明：超时未受理的保护单保持未知，最终由市价减仓兜底（保守，但会牺牲仓位）。
- 收入行以 `(incomeType, tranId)` 去重；若真实接口对多次成交重复 `tranId` 会保守阻断，需要真实样本核对。
- 仪表：有人值守时被分钟级官方标记触发的止损按触发价（加10 bp）成交，不含分钟内跳空；这偏乐观，属登记的测量假设，未改动，也未压力测量。
- 权重限制、`known_path=False` 后收盘 MDD 冻结、`AGENTS` 中的旧 P7 说明等沿用既有文档。

## 经济数字

回归 REG2（`REG2.json`，sha256 `ff3afcad528f219d9840c3e6bf64a169495442711534121db78427f95e4c0c66`）在相同冻结输入、相同测量器 M8、风险7.5上运行当前源码（`python_sources_sha256` `ae7b3fd8…`，干净提交 `ea29bbb`）：¥1,893,613，CAGR 118.24%，MDD 收盘43.60%／包络44.51%。与上一轮 REG 相比，除源码身份、`run_id`、新增的 `contract_rules_sha256` 外逐字段相同，说明 R1/R6/R7/R12/R13 的仪表修正在这段历史上没有改变任何成交（没有重叠止损被触发、没有立即触发的保护或无仓位减仓）。

R3（¥2,794,265／131.26%）只对应修复前的源码；`evidence/robustness-20260929/m8/` 的 44 份原件记录 `git_head=d1ca5c0`、`dirty=True`、源码摘要 `c5ef5b41…`（即 `d1ca5c0` 树加 `fbe3b31` 的 `research/session_exchange.py`，`PRIMARY_RISK` 当时为 6、7.5 由 `--knob`/`--primary-risk` 传入），并非干净的 `fbe3b31`。这些原件的 `execution_unresolved` 是旧定义（观察超时即计入，主序列721/795），当前定义只计未解决的意图、未验证的清理或无保护敞口，REG2 为 0，观察超时另计 `observation_timeouts=708`。

压力、风险网格（含七个日历年区块）和读延迟网格已在随后的 M9 里用当前源码重测，见 `evidence/remeasure-20260929/RESULT.md`。上文 REG2 的基准与 M9 基准逐字段相同。

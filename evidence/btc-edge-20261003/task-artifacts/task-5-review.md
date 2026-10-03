# Task 5 independent specification and code-quality review

SPEC: **FAIL** — T5-R1、T5-R2 为阻断项。

QUALITY: **CHANGES REQUIRED** — 修复最终财务审查证明的覆盖/一致性验证，以及实际日度账户重建的完整性缺口。

## 固定范围与独立性

- Spot review BASE `8c1be0fbfcc6a1c12d74450d29b5916bd10fa5dc`，HEAD `12fd6f13c2ea2bb29328a5a354153b9f044d7a2a`。
- 提供的完整 review package SHA256 `5da435677809730173ab73b81d94138cfb2d553237864d811450c45736275c9a`；implementation report SHA256 `28c2752de7494dd9ea9ed124cffe966c1182f71382c9135d6e3b988abd8a475e`，已实际核对。
- Coin 只读 HEAD `e9c2b4c5c962c3fa1dc62a25826745ad18d79f2b`。读取两仓 AGENTS、edge_spec/edge-PROTOCOL、Task 5 brief/review brief、完整新增实现/测试、复用统计/源证明/原始 meter helper、Task 3/4 producer interface/report。
- BASE..HEAD 还包括 root 的 PROJECT_STATE 派发元数据，不将其误归为实现者越界修改。审查期间可见 root 的工作区 PROJECT_STATE 更新；未发现本审查引入的源码变更。
- 本审查使用 code-review-skill；无子代理、源码修改、提交、Coin 测试、full financial producer、账户/凭据/设置/原生请求。没有重复报告中 22 focused/283 full 套件或八原始基准只读验证。下面三个纯计算 probe 用于具体新疑点；原始证据仅只读，变换仅在内存或临时证明目录。

## 阻断发现

### T5-R1 — P1 / blocking：最终财务 proof 接受失败重算与任意缺项内容

位置：`research/edge_assessment.py:743`，尤其 764–771；最终提升发生在 916–921 附近。

`verify_financial_review` 验证外层六类 `passed:true`、文件原字节 SHA、inventory SHA 和 reviewer 源树，但对于真正的 `recomputations` 只检查 dict/list 且非空。它不检查 account 是否存在、raw SHA 是否属于该账户、逐类覆盖是否完整、重算是否一致，甚至不拒绝显式 `matches:false`。现有测试 `test_financial_review_exact_preliminary_and_inventory_binding` 用 `{'case':'result'}` 即作为可接受证明，未覆盖该边界。

独立 probe：使用真实当前 clean committed assessor source（未 mock `verify_source`），构造含全部 68 个 required identity 的 synthetic completed preliminary/report，六类 artifact 的唯一记录均为：

```json
{"account":"NOT_AN_ACCOUNT","raw_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","matches":false}
```

全部外层/文件 SHA 都按其实际字节计算，调用原函数结果：

```text
FAILED_RECOMPUTATION_PROOF_ACCEPTED True
```

这是 final 验证器的直接 pure-function probe，未声称该 synthetic report 来自完整 `assess`。同一漏洞也适用于合法完成的 preliminary：将其六个 proof artifact 换成上述内容并正常绑定哈希，验证器没有额外的内容检查。`assess` 在验证返回后直接标记 `complete_reviewed`。哈希正确只证明这些失败/缺项内容没有改变，不能证明财务审查完成。这不等于要求通过每个候选的金融资格门槛；完整的“候选应被拒绝”重算必须可以通过审查。

最小修复：在新 assessor 中为六类证明增加小型、明确的记录 schema 和 expected coverage 派生函数；逐条验证身份、实际 raw/input/profile SHA、重复/缺失/额外项目、重算字段及明确的一致性状态。无定义 schema、null/unknown/failed/mismatch、显式 `matches:false` 或缺项一律不能取得 reviewed。保留候选的实际 eligible/rejected 结果，要求独立重算与该结果一致，而不是要求所有候选 eligible。必要覆盖至少为：

| 类别 | 由本次完成库存派生的必需范围 |
| --- | --- |
| source_and_inputs | 每个 original raw file 与全部 required account；实际项目/source/spec/protocol/FX/schedule/market/feature/consumed-file/offset 绑定，包括控制、负结果、calibrated、预算及适用组合 |
| original_accounting | 全部 required actual account 的初始/终端及完整日度账务、费用/funding/fills、连续 MDD 原始身份；不是仅 baseline |
| baseline_six_groups | 每项目四个 stress 的 accepted reference 六组，以及 actual scale1 unity 六组；绑定准确 reference/raw SHA 与每组一致性 |
| calibration_and_actual_risk | 两项目独立四个原始 profile 与四个 actual risk account，包括失败 singles；731 日训练、base raw、文档原字节、实际 unity，以及每个适用 combo 的 own base/profile/risk |
| adoption_gates | 全部 registered singles 和适用全组件 combo 的所有 gates、实际 risk bands、registered ranking/order 与 selected；负资格是可验证的正确结果 |
| actual_budget_aggregation | default 的三个固定 pairs，以及 selected 不同时的三个 pairs；准确账户/raw SHA、各自初始资本、日度 equity/exposure、账务与汇总指标 |

最终 proof 应绑定这些实际重算值/结果，包括预算汇总，不仅一个与重算内容无关系的 inventory 标签。仍应明确此自动验证不是签名、也不替代独立 reviewer 的工作。增加一次有效全覆盖 round trip，以及 failed consistency、缺一账户/预算/校准、错误 raw、重复记录、正确 rejection 的边界测试。

### T5-R2 — P1 / blocking：缺失日度证据被补成过期现金曲线并通过财务函数

位置：`research/edge_assessment.py:554`、`research/edge_assessment.py:597`，尤其 599–603；底层行为位于 `research/complete_assessment.py:89` 的 `canonical`。这是新模块需要补强的调用边界，无需改旧 helper。

`audit_daily` 只重算“保留下来的”快照。`original_curve` 随后只检查这些快照的排序、唯一性及窗口，然后调用 `canonical`。旧 canonical 在上一个快照 BTC 为 0 时可向后沿用现金；它不会扫描两快照间实际 fills/income。因此缺掉有持仓或已实现现金变化的日度记录时，两个校验一起仍能把过期平仓现金填到完整 2454 天。终端金额/CAGR正确和 continuous MDD 不低于合成 daily MDD 都不能揭露此问题。

最小 synthetic probe：CNY10000、FX10、起始USDT999，第一日买1BTC/10USDT、第二日卖出/20USDT，仅保留终端 cash1009/flat snapshot。`original_curve` 返回2454点，第一日和第二日均被填为 BTC0/equity999；正确首日BTC1，正确第二日cash1009。该 probe 未运行 producer。

另以实际 accepted Spot ATR base gzip 做只读证实：SHA `dc94a7b315ee8ea11cc7215cd8ff7c02a8ab94180499b2c4ebf7fe1448682323`，从 pinned `canonical-inventory.json` 解析路径，读原 row 后 deepcopy，仅将内存中的 `daily` 改为最后一条。使用实际原 FX/market 调用 `monetary_audit`、`original_curve`、`curve_metrics`，输出为：

```json
{
  "retained_original_daily": 2455,
  "probe_daily": 1,
  "terminal_money_audit": true,
  "canonical_days": 2454,
  "actual_original_days_with_BTC": 2450,
  "probe_days_with_BTC": 1,
  "financial_metrics_accepted": true,
  "probe_worst_day": -0.019857138917234285,
  "probe_es99": 0.010732390895437174,
  "probe_daily_mdd": 0.11851148237134723,
  "registered_mdd": "0.3641224868625986569325860059"
}
```

所有原件未写入。该变换后的基准本身会被外层 six-group equality 拦住；发现不声称修改基准可以通过最终评估。重要的是 singles、actual risk、组合及预算账户没有逐行 accepted reference，使用相同 `original_curve` 接受路径。丢失 daily 证据会改变训练 scale、2022+ volatility/beta、ES99/worst day/underwater、gross exposure 与预算汇总，违反 incomplete/unknown fail-closed。

最小修复：在新 `original_curve`/日度 audit 中沿原始 capture-clock 语义推进 fills/income，核对每个预期 UTC closing boundary 的真实现金/持仓状态。有真实持仓时必须有对应原始 mark/snapshot；允许 flat carry 的缺日只能是从已验证快照到该日持续为 flat 且没有未反映的现金变化，否则拒绝缺证据，不能假定过期快照仍代表账户。保留 Coin exact-midnight funding 及 before-same-stamp-fill convention，不用 tolerance 或 curve scaling 修补。增加“保留终端但丢失持仓日”和“日内已平仓却现金已变”的拒绝测试，同时保留确实无事件、始终 flat 的合法补齐测试。

## 其他已核查要求

- 独立 committed Python digest 和新 edge spec/protocol SHA 校验存在；current execution diff 只允许新增 Spot assessor 的明确路径差异。Spot canonical/旧 alpha 和 Coin original complete meter/new edge envelope 各自保留，未全局改旧 SPEC。Coin complete meter 原 inputs 本身没有 `spec_sha256`，不要求为它伪造旧 alpha spec 字段。
- 一层 exact-byte manifest、重复 identity、nested manifest、额外 inventory、JSON duplicate/nonfinite/overflow 和 exclusive writes 有明确拒绝路径。基础 `required_matrix` 为68，包含36 Spot、16 Coin、全部8 actual risk、2 offsets、6 baseline budgets；选中非基准/适用 combo 会追加要求。
- 全六组 equality、operating-only drift、旧 annotation 保留、固定新增 opportunity ledger 排除均可追踪。baseline 缺失和 unity mismatch 阻止最终完成。已保存错误证据不能代替所需完整账户。
- 各项目 calibration document 隔离，raw base bundle 精确绑定；731训练日期，统计前切片；scale0允许，无外层.01 floor；原始 unity scale1。实际 risk 使用实际账户，不在此模块按比例缩放曲线。完整实测 round trip 仍未完成。
- adoption 代码保留四 stress CAGR、项目 MDD、base improvement、带符号 arithmetic ES99/worst day/underwater、actual calibrated risk-only fallback；highest worst-stress CAGR/registered order 和 ALL eligible combo 逻辑可追踪。复用 `daily_metrics` 的风险收益为 arithmetic returns，不把 calendar log contribution 用作这些 gates。
- 固定真实资金账户身份与 CNY10000 pair 总额、5000/5000 neutral reference、daily joint MDD 标签、original account annualization、零 native/NOT_QUALIFIED 和污染披露均保留。预算使用 canonical 日度数据，因此仍受 T5-R2 影响。
- 现有测试重在 helper 边界；没有独立实际完成库存的 positive final round trip。T5-R1 的非空假证明和 T5-R2 的缺失日度证据未被覆盖。不能以套件 passed 代替这两项验证。

## 此任务不能验证的跨任务事项

Task 5 的实现审查不证明未来完整金融结果。仍需 root 按已登记命令完成、保留并独立审查 68+ 所有适用账户；全窗口新 baseline 与 accepted baseline 六组（包括 operating）；actual project calibration 文档与每条风险账户 journals/receipts；候选负结果、适用 combo 的全部组件/四 stress/own training/actual risk；当前和最终 selected 的真实固定预算账户；逐类完整独立 financial proof。22 focused/283 full 和已保留八基准/17不完整smoke证据作为既有测试记录读取，没有把 smoke 等同全窗口。

本次没有输出选优/采用/获利结论，没有改变 BTCUSDT、CNY10000、2020-01-01..2026-09-20 exclusive、原795 finite300s/5s sessions、FX/cost/funding/ownership、Spot no-topup/Coin no-short 或原目标 Spot>=100%/MDD<=30%、Coin>=150%/MDD<50%。Native cases0、actual account-days0、NOT_QUALIFIED；连续代理 MDD、历史污染及 prospective alpha 未证实的限制保持。

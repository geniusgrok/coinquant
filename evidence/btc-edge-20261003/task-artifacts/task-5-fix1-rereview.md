# Task 5 fix1 scoped independent re-review

SPEC: **FAIL** — fix 新引入的 T5-R3 必须修复。

QUALITY: **CHANGES REQUIRED** — 新 proof 重算使用了丢失原始精度的 MDD，可能拒绝正确的负结果。

| 原发现 | Scoped verdict |
| --- | --- |
| T5-R1：非空/failed/缺项 proof 可以通过 | **ADDRESSED** — 六类 typed records、精确覆盖/raw 绑定和逐值一致性替代了旧的非空检查；其新 gates 重算另有 T5-R3 |
| T5-R2：缺失持仓/现金变化 daily 被 stale-cash 补齐 | **ADDRESSED** — 新 audit 合并所有预期 UTC closing boundary，缺证据时逐个检查实际事件、现金及持仓 |

## 固定范围与证据

只审查 `12fd6f13c2ea2bb29328a5a354153b9f044d7a2a..73a0baf5702fce5bed23205c245aab53fad951b9` 的两条修复及新引入的重要问题；own commits 为 `0df61687f532b9762d33c43fed8dc006e41d7402`、`73a0baf5702fce5bed23205c245aab53fad951b9`。Coin HEAD 仍为 `e9c2b4c5c962c3fa1dc62a25826745ad18d79f2b`。未做另一次 whole-task review。

已读取原 `task-5-review.md`、fix brief/rereview brief、完整两文件 fix diff、report fix1 append、schema examples；核对实际 SHA：

- 完整 fix package：`0172a063910ce84394860389f309c93ff29ea1290481c9c240a98d9dfe48395c`。
- implementation report：`426fc530d3b15b06693d611d1b56e27060f16dacb7ff9fd86b977e5e290617e8`。
- 28 covering tests 日志：`dd9ba78662026fb34506a273eb9de4a0c8c34e39b12b5b93fd315752a68d6f60`；日志为 28 tests / OK / 28.691s。
- final-source verification receipt：`6a8bb8673e5c6634add3a70f15c4faffec1ec532c73b2bcc58d348864bbf1548`。
- schema examples：`9bb77ad185a40663e5871ef87a765dc2ea6baa6c576ad5e264aa9e63069f4fc3`。

没有重复这些测试或8基准/17pending只读验证。没有子代理、源码改动、提交、Coin tests/producer、完整财务 producer、原生/私有/账户操作，也没有修改 HOME/UID/锁。唯一新增独立 probe 是下面的纯计算边界探针；调用测试 fixture 构造数据，没有运行测试套件。只写本报告。

## 新 Important finding

### T5-R3 — P2 / Important：proof 用 float MDD 重算 exact Decimal gates，拒绝正确结果

新增位置：`research/edge_assessment.py:887`–`912`，特别是 `values()` 的 `mdd=a['continuous_mdd_from_account']`，以及 actual calibrated candidate/control MDD 的同类取值。

原有、仍正确的主 decision 路径是 `gate_values()` 读取 `account['row']['mdd']` 的完整原始 Decimal 字符串，再由 `adoption_gates()` 做精确阈值计算；risk-only fallback 同样使用 actual raw row MDD。新增 `review_expectations()` 改用 `metrics['continuous_mdd_from_account']`。后者由旧 `financial`/`attribution` 转为 float，是展示/统计值，不保留原始 Decimal 精度。

具体合法边界：baseline MDD 为 `"0.31"`，candidate MDD 为 `"0.30000000000000001"`，两者 CAGR 相同。正确的至少 `.01` MDD 改善门槛失败：`.30000000000000001 > .31-.01`。但 float 把 candidate 变为 `.3`，新增 proof 重算认为门槛通过。随后 line912 以 gate 不一致拒绝这个正确的 negative-candidate result。相同精度问题也可能影响 Coin strict `<.50` 或实际 calibrated risk-only MDD fallback。没有必要改变实际经济阈值或允许 tolerance。

独立 probe 使用 `complete_review_fixture()` 的68账户 completed synthetic report，在内存中将 Spot baseline及对照 stress MDD 设为`.31`，exit-confirm base raw gate input设为`.30000000000000001`；展示 metrics 按真实 `float(raw_mdd)` 路径赋值。各 single 的原始 decision 使用未修改的 `adoption_gates` 和上述 raw Decimal input 重算，保留正确拒绝、不选候选、原固定 inventory。然后直接调用新增 `review_expectations(report)`，输出：

```text
RAW_DECIMAL_BASE_IMPROVEMENT False
RAW_DECIMAL_ELIGIBLE False
CORRECT_NEGATIVE_PROOF_REJECTED review gates inconsistent with actual metrics
```

该探针没有运行 financial replay 或伪称真实 full-window 账户完成；它验证的是新 proof helper 与主 gates 的确定性不一致。现有完整 positive fixture 全为 flat MDD，不能覆盖原始 Decimal 到 float 的阈值损失。

最小修复：在剥离 raw row 前，为报告账户保留已绑定原始 raw SHA 的精确 gate inputs，至少完整精度原始 continuous MDD；unscaled stress 和 actual calibrated fallback 都使用同一份原始精度数据重算。更直接地保留 `gate_values(account)` 的审查输入，并单独保留 actual raw MDD，让主 decisions 和 proof comparison 共用这些值。纳入 inventory/proof 绑定并由独立 reviewer 从原始 raw核对。不要将主 gates 改成 float，也不要在 proof 加误差容忍掩盖阈值变化。加入此正确 negative outcome 的 proof roundtrip，以及 exact equality / just-fail 的 calibrated 与 Coin strict-MDD边界回归。

## 原发现修复的 scoped 核查

T5-R1 的原绕过已移除。新增 `review_expectations` 从完整适用 inventory 派生 source-account/raw、全部 original accounting、10个 baseline/unity六组、分项目 profile/actual-risk、全部 singles/适用combo/ranking，以及各固定预算 pair 的记录。`verify_financial_review` 拒绝未知/重复 identity、missing/extra记录、错误 raw、`matches:false`、不匹配类型/值和非有限数。正确 `eligible:false` 与 `matches:true` 分开表示，普通 negative outcome 可通过。cycle-free binding新增 account evidence、portfolios、input envelopes、calibration input documents/diagnostics、environment、combinations。实际 reviewer仍须独立重算，自动生成 expected records 不是独立财务证据。除 T5-R3 的新增精度不一致外，未发现原“任意非空内容可审核完成”的剩余路径。

T5-R2 的新路径会在每个缺失 UTC boundary 推进 fills/income，然后要求真实 qty与最后核验qty均为0、cash未变且事件游标没有前进，才允许carry。已验证的intraday flat snapshot可重新开始合法eventlesscarry。它仍使用 Spot原 capture stamps、Coin boundary减1ms的fill顺序及exact-midnight funding处理，没有修改旧 canonical/statistics helper或放宽数值/时间语义。新增测试覆盖missing held day、已flat但现金已变、真正无事件flat、核验过的intraday flat、Coin午夜funding与同stampfill。读取的最终干净源receipt显示8个accepted原基准通过、17smoke仍仅pending、accepted ATR原件的terminal-only内存变换被拒绝，reason为 `missing daily snapshot for held exposure or unreflected cash/fill events at 1578268800000`，原raw SHA保持`dc94a7b315ee8ea11cc7215cd8ff7c02a8ab94180499b2c4ebf7fe1448682323`。

## 范围外事项

没有新增其他 Critical/Important finding，也未将完整68+实测库存、实际profile回放、独立finance proof、采用决定或native qualification当作本次scoped修复应完成的任务。它们仍是root后续工作。此复审不改变任何BTC/economics/session/FX/cost/funding/ownership/no-topup/no-short/原目标约束；native cases0、actual account-days0、NOT_QUALIFIED和历史代理/污染限制保持。

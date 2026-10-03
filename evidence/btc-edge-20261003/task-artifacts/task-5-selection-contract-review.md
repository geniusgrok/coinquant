# Task 5 selection contract — narrow independent adjudication

**Verdict: 当前 combo 优先规则符合原 Task 5 实施 brief；未证实为实现偏离。冻结 spec/protocol 的简写存在影响最终选择的范围歧义，应在测量前明确记录解释。**

这不是一次新的全任务 SPEC/QUALITY 审查，也不撤销之前的 scoped 修复结论。没有代码缺陷 finding；以下 `T5-SC1` 是合同解释记录，不是已证实的 Critical/Important implementation bug。

## T5-SC1 — ranking 范围与 combo supersession 的解释

读取了两项目实际 frozen `edge_spec.json` 的 adoption/candidate_order/compatibility、实际 `edge-PROTOCOL.md` 的 Risk/adoption、原 `task-5-brief.md:25` 及当前 assessor 的三处选择逻辑。

冻结 spec 的原文是：

> ranking: highest worst-stress CAGR, then registered candidate order

> combination: all individually eligible compatible mechanisms, no subset search; all four stresses and actual calibrated base; adopt only own gates pass

协议把相同 ranking 句放在 adoption 段落，并要求组合重测后按自身 gates 采用，但没有显式说“组合必须胜过最佳 single 的 worst-stress CAGR”，也没有显式说“ranking 只适用于 singles”。两项目 `candidate_order` 都只枚举三个 singles，未给组合的全局并列次序。

仅从这两句简写出发，“adopt only own gates pass”表达必要条件，不能单凭它推出“只要门槛通过，就无条件优先组合”；同样也不能忽略组合阶段，把一个未明确登记的全局 single+combo 比较规则当成文本的唯一解读。

原实施 brief 则给出了更具体的两阶段说明：

> Rank eligible singles by highest worst-stress CAGR then registered order. Combine ALL individually eligible compatible components if>=2, in registered order, no subset/parameter search; own gates determine whether combo supersedes best eligible single, and singleton needs no duplicate combination replay.

此句在原 Task 5 dispatch 中已经存在，不是看到测量结果后的新解释。它明确限定第一步排名为 **singles**，然后以组合自己的 gates 决定是否 supersede 最佳 single。按这个任务合同执行，组合即使 worst-stress CAGR 低于最佳 single，也可在自身完整 gates 通过后替代它。当前实现因此有直接的预先给定依据，不应将其报告为已证明的作者偏离。

## 当前代码与确定性例子

- `research/edge_assessment.py:465` 的 `choose_singles` 只在三个 registered singles 中按最高 worst-stress CAGR/registered order选best，并返回全部eligible components。
- `assess():1136`–`1139` 在适用组合完整评估且 `outcome['eligible']` 为true时选combo，没有与best single重新比较CAGR。
- `review_expectations():932`–`933`核对同一个两阶段结果。它与主选择路径一致；该一致性本身并不能消除合同文字的歧义。

无需执行程序即可确定以下结果。假设 baseline 四stress CAGR均为50%；下面三个已评估对象所有其他原注册门槛都通过，第三个single被拒绝，唯一适用组合严格由前两个eligible singles组成：

| 对象 | worst-stress CAGR | own gates |
| --- | --- | --- |
| single A（registered order 1） | 60% | 通过 |
| single B（registered order 2） | 55% | 通过 |
| 固定 A+B combo | 52% | 通过 |

组合52%仍可满足相对baseline的所有CAGR门槛；这里只假设其余MDD/tails/underwater/实际risk等门槛也通过，未声称单靠这些CAGR数字就可建立资格。

原brief的两阶段规则及当前代码选 **A+B combo**。若改为“所有合格single与combo统一按worst-stress CAGR排名”，则选 **single A**。这说明两种解释差异影响selected、后续实际预算账户库存及最终采用结果，必须在看到新金融结果前定案；它不能说明哪种规则在经济上必然更好。

## 最小处理建议

若继续原 Task 5 brief 的两阶段解释，root应在测量前记录明确条款：“ranking适用于eligible singles；适用的ALL-components combo自身所有gates通过则替代best single，即使其worst-stress CAGR较低；否则保留best single；无需single重复组合回放。”按此解释，当前两处代码不需要修正。

Root在本次测量前裁定中确认采用这一原brief解释，不更改spec字节、gates或registered order。后续金融报告应同时展示best eligible single与适用combo的实际worst-stress CAGR、其余门槛结果和预先登记的两阶段选择规则；若选中的合格combo数值较低，明确显示这个差异，不能把combo描述为所有合格对象中最高worst-stress CAGR。此时实际结果尚未产生。

若root选择“最终所有eligible对象统一排名”，应明确把它作为本歧义的预先裁定/规则修订，而非声称既有文本已经唯一规定了该规则。届时主选择与proof检查都须同步按同一排名函数比较，并预先规定combo与single在worst-stress CAGR相等时的次序；相应预算适用库存按新selected派生。不得根据随后结果选择解释，也不得为获得更好结果搜索组件子集。若涉及更改frozen contract字节，必须按原source/spec冻结流程重新绑定后再测量；本报告不修改或授权绕过这些流程。

## 范围与证据身份

核对的Spot frozen spec SHA `af23d8afdce40c7cfc60387cc70e0332739a017c7b9a5460b9a5dbe9444b409f`，protocol SHA `c20446129708ef998ce9ab403ec6a14760b008cc00ad0ad49ea3488c2dc897bd`。本次只审查上述需求/代码关系；没有测试、producer、子代理、源码或合同修改，也没有实际金融结果/采用决定。示例为手工确定性的条件说明，不是金融实测。只写此独立报告。

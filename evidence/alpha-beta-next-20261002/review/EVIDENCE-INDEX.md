# BTC alpha/beta证据导航

本索引用于本轮最终归档。修复后的64项独立财务审查及五账户来源/采用审查均PASS，单独采用决定只批准开发默认。完成状态由原始命令回执、最终报告、独立审查和逐文件清单共同证明；文件存在或单一汇总表不表示通过。历史账户、共享执行路径证明、公开前向观察和真实账户资格分别记录。

## 财务原件

归档的`scratch/spot-singletons/accounts-manifest.json`绑定7个现货候选、每个4种压力场景，共28个完整账户。`scratch/perp-singletons-retry1.json.gz`保留5个合约候选的4种压力场景，共20个账户。JSON gzip是原始JSON的无损保留，不改写其中的测量来源、时间或财务字段。

现货实际风险原件为`scratch/risk-spot-project-early.json.gz`。合约首次五账户原件`scratch/risk-perp.json.gz`资金核验通过，但基准控制的两个会话操作轨迹不一致，不能进入通过集合。修复须使用原参数完整重放基准控制，先核对全部六组，再以明确派生的四账户无损投影和未改写的新基准原件组成一层SHA清单；正式通过项以修复后的最终报告为准。首次五账户及失败审核始终保留。注册风险清单仍为12项，包括两个比例1基线控制。训练只用2020–2021的731个实际USDT日收益；`spot-project-calibration.json`与`registered-calibration.json`分别保留各自原始SHA。已有持仓不追溯缩放，2022年后的新仓位按固定训练比例实际重跑。

四个`sensitivity-serial-retry1-incumbent-*.json.gz`分别测量CNY9900、CNY10100、原会话起点−60秒和+60秒。它们是固定的路径敏感性诊断，不能据此选最优本金或改写原CNY10000目标。只有一个现货机制通过组合门槛，复用已有账户；合约无新机制通过，不另造组合账户。

最终注册集合为48个原始场景、12个风险账户和4个敏感性账户。修复使用新的`scratch/registered-final-repaired.json`、`.csv`、`.md`与同名前缀的`.command.json`和`.run.log`，并对应`review/financial-audit-remaining-repaired-index.json`；它与未改变的`review/financial-audit-unscaled-index.json`分别核对剩余16项和48项。每项的候选、场景、阶段及原件SHA都必须精确对应。旧`registered-final.*`及旧剩余索引保留首次控制失败的事实，不能混入修复后的采用依据。文件名是定位方式，真实回执、完整核验和独立审查才是通过证明。

## 来源与共享执行路径

| 身份 | 已冻结测量版本 |
|---|---|
| 合约研究生产者 | acedaa43ca94223f24e2fe11851bbef74e032a69 |
| 现货研究生产者 | 8ca002522fbdce531dcfbbb783ff4d152a7fd66c |
| 独立评估实现 | 99fcf005d2cb15c13bb37322b65ab2863b19d65e |
| 现货共享ATR止损实现 | 0c52c812301de3712f3637a1ce1b1241de0c40f1 |

每个原始账户保留完整Git/Python/spec/protocol/市场/汇率/日程身份。后续文档提交或main合并不能冒充这些测量版本。旧基线原件仍在两仓库各自的`evidence/complete-delivery-20261001/`，保留原身份；它们不是新默认的测量账户。

`scratch/spot-canonical/canonical-inventory.json`另行绑定基础、费用、滑点、空窗和文件校准基础五个账户。它们走共享Model/session/Lifecycle路径，分别与冻结研究账户的财务、成交、日权益、归属、操作和其余原始字段六组对比。正式采用须再由最终报告、独立审查及专门来源桥共同支持；这五个账户不替代全局64项审计，也不计真实交易案例。

代码审查、实际风险比例核对、逐笔财务重建和五账户证明位于`review/`。`SPOT-RESULT.md`及`COIN-RESULT.md`记录各已完成阶段，其独立审查绑定原文SHA；最终采用决定独立于这些阶段记录。旧通用来源门保持严格，不能用自定义忽略项或重标来源接纳新执行代码。

## 原件定位与失败记录

`MANIFEST.json`把每个原始绝对路径映射到归档相对路径，并保存字节数和SHA。原始回执内部的绝对路径不被改写；在另一台机器复核时，通过该映射找到同字节原件。相对清单的子文件仍保留原目录关系。该归档是证据映射，并非含全部公开行情输入的独立回放包；完整复现还需要保留Git历史及说明中的公开市场/汇率输入。

原合约矩阵及并行探针在账户锁冲突后中断。旧日志、两个失败进度快照、重跑前缀观察、停机回执、撤回的并行审批和独立空锁检查保留为运行故障证据，不能作为完整财务账户。所有合约生产者随后严格串行；更换缓存目录不能隔离同一账户身份。

首次合约风险基准控制在会话31和38记录HTTP读取异常，轮询次数及错误记录不同。源码与离线探针支持公开成交ZIP补取HTTPError经历史适配器传播的机制，实际历史远端响应未留存，不能把具体URL或响应代码当成已证实原因。两次资金、成交和日权益均逐项相同，仍不得豁免操作轨迹门槛。源路径和无网络判别探针支持此机制，但原件没有保存远端HTTP状态或CHECKSUM/ZIP具体失败URL，不能追认历史响应代码。修复只重放失配控制，四个成功账户逐行无损保留；旧失败原件、严格检查失败日志、BLOCKED财务审核、根因补充及新派生证明分别归档。实际完整重放与无损来源核对未完成时，不存在修复通过或采用批准。

公开ZIP观察器只保留经官方CHECKSUM核对的原始公开归档。`scratch/public-print-vault/records/`、每次恢复回执和观察日志说明实际输入复用；ZIP/BIN缓存、账户State和巨大的已完成进度副本不入交付。已撤回的脚本与审批只用于故障历史，不能作为继续并行合约任务的授权。

## 指标边界

收益为成本后CNY CAGR；Spot按365.25天年化，Coin原注册账户按365.2425天。描述性日收益、波动率和回归另用365.25天。连续回撤是声明的Spot OHLC或Coin分钟/数量上界代理，未由第二执行引擎重放；日终回撤单列。2026年截至9月19日，为不完整年度。

风险匹配表示实际2022年后波动率不超过基线的1.05倍且BTC beta不超过基线+0.02，不能表述为风险精确相等。HAC7区间未校正此前策略选择；历史已被研究，不能证明未来alpha。现货新止损的最差CNY单日亏损增加，最长水下期未缩短，不能声称所有风险维度改善。

公开前向日记仅在规则冻结及审查通过后于实际UTC初始化，全现金、零观察、零交易、零实际账户日；它绑定冻结研究来源，不冒充新默认执行或真实账户。原100%/30%现货及150%/<50%合约目标不变。原生案例和实际账户日均为0，NOT_QUALIFIED。

`spot-native-atr-stop-zero-*`和`perp-native-incumbent-zero-*`保留绑定实际执行包的空原生模板及零案例检查，`native-zero-source-binding-proof.json`分开记录模板工具来源和两个目标执行包。空案例检查的退出码2是明确的未通过结果，不是原生资格通过。模板不含账户身份、凭据或真实事件。

复现命令、精确来源和串行条件见`REPRODUCE-registered.md`。图表使用最终实际账户指标，保留独立PNG/SVG和图表来源清单。


## 最终接受项与导出

- `review/final64-financial-review.md`及proof：接受准确48+12+4资金身份，绑定修复后的最终报告和新16索引。
- `scratch/spot-adoption-bridge.json`及实际命令回执：五共享账户机器等价证据；其false/pending原字段不改写。
- `review/spot-actual-adoption-bridge-review.md`及proof、`review/spot-actual-adoption-financial-review.md`及proof：实际来源与采用财务的两份独立PASS。
- `scratch/adoption-decision.json`：2026-10-02T17:17:58.192654UTC单独决定，共享现货ATR默认比例1，Coin原7.5/3.6；默认只读，无真实账户授权。
- `scratch/spot-forward-zero-init.json`和`perp-forward-zero-init.json`及各自command/run.log：实际初始化，immutable99/aced，全现金10000/BTC0/零观察/零案例/零账户日。
- `scratch/registered-diagnostics.csv`、provenance及verification：完整64行精确导出，不重算指标，小数比例单位。
- `scratch/figures/registered-risk-return.{png,svg}`及`actual-validation-risk.{png,svg}`：实际基础收益/连续代理回撤及2022+风险带；`figure-provenance.json`和`registered-figures.command.json`保留数据/图片/工具字节身份，正式PNG已借同字节预览逐张查看。
- `review/FINAL-RESULT.md`：最终开发选择、所有拒绝方向、四敏感性、实际alpha/beta及尾部/时序/原生边界；`SPOT-RESULT.md`/`COIN-RESULT.md`阶段原文不改写。

四个敏感性年化分别119.752564%、119.252162%、136.018640%、127.114524%，完整审查见`coin-four-sensitivity-financial-review.md`。原起点±60秒变化显著，不能解释为新默认或择优起点。所有目标仍NOT_MET，原生与实际账户日仍0。

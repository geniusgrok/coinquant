"""Write accepted delivery prose only; no source/economic/account changes."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path('/workspace/btc-alpha-beta-improve')
FIN = Path('/workspace/scratch/btc-alpha-beta-edge-20261003')
report_path = FIN / 'assessment/complete-final-input-path-fix1.json'
raw = report_path.read_bytes()
report = json.loads(raw)
assert report['status'] == 'complete_reviewed' and not any(report[k] for k in ('pending', 'blocking', 'rejected_files'))
assert report['selected'] == {'spot': 'crowding-interaction', 'perp': 'incumbent'}
report_sha = sha256(raw).hexdigest()
stamp = datetime.now(timezone.utc).isoformat()
result = f'''# BTC alpha/beta 完整交付（2026-10-03）

Spotquant 开发默认采用 **SMA30/40/50 + ATR 止损 + 登记的拥挤度交互**，默认规模1；Coinquant 保留 **SX60+DFII10、primary7.5/macro3.6**。两者仅关注 BTCUSDT，分别负责现货与合约。Starquant 仅保留历史研究/FX参考用途。

本轮71个注册原账户（Spot46/Coin25）及另外5个共享现货运行时账户全部完成，独立资金、收益、HAC7统计、风险、六组原字段及来源复核通过。最终报告 `complete-final-input-path-fix1.json` SHA256 `{report_sha}`，独立机器证明 SHA256 `50dc293c8225027f2bfa49508cdd058f2ccc4a44ebb4976f3b41b206d048aefc`。原始失败、负结果和更正回执全部保留。

## 结果及实际用途

| CNY10000、不追加的历史账户 | 成本后 CAGR | 原始连续代理 MDD | 全窗口 USDT BTC beta |
| --- | ---: | ---: | ---: |
| Spot ATR 基线 | 55.2180% | 36.4122% | 0.387101 |
| Spot 采用的交互 | 56.5981% | 36.4122% | 0.368539 |
| Coin 保留的原策略 | 119.2284% | 44.1051% | 0.275848 |

现货 CAGR 增加1.38008个百分点。2022+实际新订单风险账户 beta 从0.337669降至0.300300，年化日收益波动29.0681%降至27.3507%，累计USDT收益差为+14.9169个百分点（不是年化）。最差CNY日仍−15.8029%、水下期713天；ES99算术损失7.1885%降至7.1337%。全样本描述性回归算术年化截距30.1129%→31.6732%，不能与CAGR混用；2022+截距16.3777%的描述性HAC7区间包含0。原现货100%/≤30%、合约150%/<50%目标仍 **NOT_MET**。

**收益来源限制：** 登记的现货决策日志中689个报价不变、200个因缺失因果特征而阻止新开仓，实际三条件减半触发为0。因此观察到的改善来自这些路径上的缺失输入阻止开仓，不是减半分支盈利能力的实证。代码、必要分支检查和5个运行时账户证明实现与账本一致，不能证明未来alpha。

采用规则仅改变真正NEW BUY：已结算且因果可用funding>.0003、前一完整UTC日配对期货/现货成交收盘basis>.01、完整收盘不高于五日前，三项同时满足时支出减半一次。必需数据缺失时阻止该BUY；持仓数量、原ATR/已确认止损下限、退出/保护/归属、普通和安全SELL保留。无持仓补仓、再平衡、借币、现货杠杆或默认做空。当前交易与前向观察都使用同一谓词。

| 候选 | 结论 | 未通过的主要登记条件 |
| --- | --- | --- |
| Spot exit-confirm | 拒绝，研究保留 | 配对压力收益/回撤、收益改善、ES99、实际验证 |
| Spot stop-budget | 拒绝，研究保留 | 配对收益、改善、水下期、实际验证 |
| Spot crowding-interaction | 采用开发默认 | 全部登记门槛通过；缺失输入收益来源限制如上 |
| Coin quality-budget | 拒绝，研究保留 | 所有压力收益、改善、实际风险上界 |
| Coin cost-horizon | 拒绝，研究保留 | 三个压力收益、改善、实际风险上界 |
| Coin crowding-interaction | 拒绝，研究保留 | 改善及实际验证 |

只有一个现货单机制、零个合约单机制合格，没有适用的多机制组合。只用731个2020–2021 USDT收益观测训练；所有实际2022+风险账户均执行，规模只影响真正新订单，不改旧持仓或乘曲线。风险条件是波动≤基线1.05、beta≤基线+.02的上界，不是风险完全相同。

## 两个真实资金账户

CNY2500/7500、5000/5000、7500/2500均来自两侧分别实际注资的完整账户，总CNY10000，无转账/追加/再平衡。各自费用、资金费、最小订单、舍入及实际路径全部保留。

固定5000/5000中性参考的采用组合CNY CAGR为115.3293%、**日收盘联合MDD**24.6339%，beta0.306338、两侧收益相关0.373072。ATR基线组合CAGR115.4851%，因此本轮不能宣称中性组合收益也提高。另两种比例是稳健性证据，不按历史最高收益选资金比例。日收盘联合MDD不等于连续联合MDD，也不能替代任一项目的原风险目标。

## 来源与运行准备

原测量来源保持Spot74bd6e035e36531c517029077c1a9e2e5ec44516/Pythonf2d6c3e73c2acb7b328a7a0e2678bb95ceb77d8a17a46139abfe8b357befdbf6、Coin37061a7f588f97cc16852551cab6cd2e51acb920/Pythonba63895131db566e708a5c96cde4504beace39fa0bdd54881d039dd5b8ef4c50。5个现货共享账户来源609606d9c0e0ad8d3c3038b329c9c4ab6d1b9629/Pythonb81f1bfee086e875cbf8ff22a67b2cfdff419130a7918a6ce8754b2e9e2936c5，独立5案例证明SHA44bd6e504f7e33b3e702f9bfe28a8084f643f9dcf4ce1e94c1e376658939f8a0。之后文档/证据/合并HEAD只在保护字节和文件模式完全相等时作为元数据别名，不能重标原始测量。

现货执行规则为 `2026-10-03-atr-stop-crowding-interaction-v1`，Model格式仍5。旧规则、研究身份或不兼容耐久状态在Lifecycle恢复前拒绝，即使旧账户平仓也不能忽略。保留原SQLite/订单身份；不自动迁移、重置或以空目录推断账户已平。

两个手动前向影子账本以绑定独立证明的导出和真实当前FRED CSV/发布元数据初始化，CNY10000/BTC0/观测0，不回填历史。若无法取得新鲜公开市场数据，状态明确为 `fresh_public_market_pending`；首个真正新鲜观测只做预热，之后新的完整区间才可提议交易。已观察到Binance公开接口HTTP451，不绕过。Coin后续持仓区间的mark路径不确定仍阻止无法证明的模型成交，不能当作合格的多次原生交易证据。使用见 [当前运行与复现指南](edge-GUIDE.md)。

经济窗口2020-01-01至2026-09-20 UTC末端不含，795有限300秒/5秒轮询会话（现货登记空窗789），原费用/FX/资金费/延迟/保护边界不变。历史已经研究过，连续OHLC/分钟包络MDD为代理，29分钟缺失mark、USD/USDT平价估值、FRED周度基准、止损替换取消空档及原生保护限制仍保留。**native_cases=0、actual_account_days=0、NOT_QUALIFIED、prospective_alpha_proven=false**。收益未到天花板并不代表本轮负机制可以直接上线；后续收益证据需来自真正新的数据/来源约束。

完整原账户、成本/资金费、压力/风险/预算、源码档案、输入身份、首个存储失败/一次获准恢复、路径更正、独立审查和图表保留在 [本轮证据](../evidence/btc-edge-20261003/README.md)。已通过且未变的局部检查直接复用；最终每个仓库仅一次全量CI，无重复本机全量验证。CI与工程交付不授予私有账户、订单、资金、配置或实盘权限。
'''
guide = '''# 当前 BTC 策略、手动前向观察与复现

当前结果见 [edge-RESULT.md](edge-RESULT.md)，逐文件保留与恢复见 [证据包](../evidence/btc-edge-20261003/README.md)。历史指南及旧证据保持原来源身份；不能用当前执行代码代替冻结的旧生产者。

## 现货开发采用

当前规则2026-10-03-atr-stop-crowding-interaction-v1，SMA30/40/50、ATR14保护、默认规模1。拥挤度只约束真正NEW BUY，三项同时成立时减半一次；缺失只阻止该BUY，安全退出/止损不依赖这些数据。没有旧持仓补仓或自动资金再平衡。公开BTC fundingRate及配对现货/期货1d klines共用原始响应、SHA、请求/接收时钟和相同因果解析；不读未来历史特征文件，不请求私有期货账户。

funding结算+28800000ms才可用，自availability起age≥28800000ms即过期；basis使用closeTime+1的匹配UTC完成边界、完成+60000ms可用、当前UTC可用日期及最多一日年龄。响应接收须≤决策，且最多一分钟旧。不能用未完成K线或预测资金费率，也不能把缺失/非有限值变为0。详细说明 [canonical-crowding-GUIDE.md](canonical-crowding-GUIDE.md)。

旧规则/不兼容状态恢复前拒绝，包括平仓状态。Model格式5不代表执行策略版本兼容。保留旧State/SQLite/订单身份，只读核对或受控迁移需要额外真实账户证据；本交付未进行迁移，不创建空目录绕过拒绝。默认只读，run --execute仍阻止；工程工作不授予账户、订单、转账或设置权限。

## 手动前向影子账本

使用本轮保留的原始forward-binding导出，按清单无损还原gzip并核对原始SHA。不要用新导出来冒充本轮已审查的信任锚。Spot与Coin分别从各自干净的提交树运行；Coin读入导出时无需导入Spot或兄弟仓库。实际导出/初始化身份及原始FX配对响应在证据包forward/中。

```sh
python -m research.edge_forward init --diary /NEW/path/ledger.json \\
  --export /restored/forward-binding.json --export-sha PINNED_RAW_EXPORT_SHA \\
  --review-sha 50dc293c8225027f2bfa49508cdd058f2ccc4a44ebb4976f3b41b206d048aefc \\
  --defer-market-warmup
```

本轮已实际初始化的账本不能被这个示例重建覆盖；此命令是日后新观察记录的说明。初始化真实当前UTC/CNY10000/BTC0/事件0，真实FRED DEXCHUS CSV及发布Dataset元数据共同验证，无历史回填。周度FX基准不是可执行报价。市场pending不是已观察或已盈利。首个新鲜完整市场区间预热，之后真正新的区间才有提议；旧信号消耗、缺失/未知保护保持拒绝。Coin mark路径无法证实时保持未解决状态，不伪造成交。没有守护进程或保证自动收集。

```sh
python -m research.edge_forward observe --diary /existing/ledger.json \\
  --export /restored/forward-binding.json --export-sha PINNED_RAW_EXPORT_SHA \\
  --review-sha 50dc293c8225027f2bfa49508cdd058f2ccc4a44ebb4976f3b41b206d048aefc \\
  --url bars=OFFICIAL_CURRENT_BTC_BAR_URL --url depth=OFFICIAL_CURRENT_DEPTH_URL
```

具体所需公开类别以各仓库edge_forward.py CLI与当前指南所述为准：Spot另需futures_bars/crowding_funding，Coin需mark/funding/dfii配对公开证据，观察还保留FX。响应必须实际取得且时间/来源/哈希满足契约；HTTP失败留原始响应，不绕过地理限制。Observe是纯公开、显式模型成交影子账本，不是交易账户/原生成交。不要为了让事件数变大回填观察或反复刷新同一区间。

## 复现与检查

证据包MANIFEST映射原绝对路径、保留路径、字节数及SHA，gzip为明确的无损存储，原始JSON与原始压缩生产者SHA不同概念。保留原始Git历史及三个互异来源：原研究生产者、评估器、共享现货运行时；官方大规模市场档案按绑定CHECKSUM及原输入清单获取，包不复制14GB公共档案。额外2026-08-01 BTC aggTrades官方ZIP/CHECKSUM已单独保留。

复现经济研究是按冻结命令执行完整账户，不是日常启动前的检查。不要重新启动已经完成的实验队列。已通过且来源不变的检查直接复用，普通变更只运行受影响且必要的检查；完整离线CI仅最终提交一次。Coin共享UID的任何合成账户始终串行，不能改HOME或移除锁。

默认收益选择、软件CI、财务复核和原生资格分别保留真实状态。没有证明的原生案例/实际账户日为0，原收益目标未达，未来alpha未证明。
'''
for name in ('spotquant', 'coinquant'):
    repo = ROOT / name
    (repo/'research/edge-RESULT.md').write_text(result)
    (repo/'research/edge-GUIDE.md').write_text(guide)
    plan = repo/'research/edge-PLAN.md'
    text = plan.read_text()
    text = text.replace('- [ ]', '- [x]')
    text = text.replace('- [x] Write every result/rejection', '- [ ] Write every result/rejection')
    text += '\nFinancial/default/forward implementation closed after independent71+5 acceptance; final evidence packaging/whole-branch review/exact-head CI and normal merge remain the only integration work. User minimum-check policy: no repeated or optional tests; one final fullsuite per repository.\n'
    plan.write_text(text)
    state = repo/'PROJECT_STATE.md'
    text = state.read_text()
    a = text.index('Updated:'); b = text.index('\n', a)
    text = text[:a] + 'Updated: ' + stamp + text[b:]
    a = text.index('Latest resume point:'); b = text.index('\n\n', a)
    lead = f'Latest resume point: Independent financial review PASS all71 original accounts/all5 separate canonical Spot cases, machine proof50dc293c…; final report complete-final-input-path-fix1.json SHA{report_sha} complete_reviewed with no pending/blocking/rejected. Initial final attempt correctly rejected differing manifest paths and is retained; fixed invocation uses exact reviewed preliminary manifests and same public-print union, no account replay. Spot canonical609606 source integrated normally; Coin incumbent unchanged. Source/profile/economic identities remain distinct and preserved. Native0/days0/NOT_QUALIFIED/prospectivefalse, original targets NOT_MET. Next final clean-source bridge/export/actual cold initialization, charts and immutable evidence packet, then one final whole-branch review and one exact-head fullCI perrepo and normal PR integration. Passed scoped and71/5 financial work MUST NOT be repeated. Defaultread-only/no private actions.'
    text = text[:a] + lead + text[b:]
    text += f'\nProgress {stamp}: original71 and canonical5 independent acceptance complete; adopted Spot crowding development default after six-group proof, Coin retains incumbent. Actual journal689 unchanged/200 missing-feature blocked/zero halving events; observed gain does not validate halving profitability. Final source/report/forward metadata binding and normal integration proceed without optional/repeated tests.\n'
    state.write_text(text)
    hand = repo/'HANDOFF_PROMPT.md'
    text = hand.read_text()
    text += '\nCurrent round financial approval is complete; consult the latest PROJECT_STATE entry for actual final bindings and integration. Reuse completed71/5 calculations and passed scoped checks. The user requires no optional/repeated tests and one final fullsuite only. Old frozen Git/source/raw identities remain authoritative after metadata integration.\n'
    hand.write_text(text)
    readme = repo/'README.md'
    text = readme.read_text()
    if name == 'spotquant':
        boundary = text.index('第三轮接通')
        intro = '''# Spotquant

本轮完整交付 BTC alpha/beta 改造，开发默认为 **SMA30/40/50 + ATR止损 + 拥挤度交互**，现货只做多/现金，无借币和杠杆，规模1。原CNY10000历史成本后CAGR **56.60%**、连续OHLC代理MDD **36.41%**；ATR基线为55.22%/36.41%。实际2022+风险账户beta **0.3377→0.3003**。

观察到的改善来自缺失因果特征时阻止新开仓；本轮没有实际三条件减半事件，不能把结果当作减半分支未来盈利证据。原100%/≤30%目标仍 **NOT_MET**，原生案例/实际账户日0、**NOT_QUALIFIED**。旧规则耐久状态恢复前拒绝，无自动迁移/清空；默认只读。

71个原账户及5个共享现货账户独立复核通过，负结果与失败均保留。两个项目分别负责现货和合约，不选历史最佳资金比例；固定中性5/5组合115.33%/24.63%是日收盘联合指标，不能代替连续回撤目标。详见 [本轮结果](research/edge-RESULT.md)、[当前运行指南](research/edge-GUIDE.md)和 [完整证据](evidence/btc-edge-20261003/README.md)。

下方早期P4/共识/ATR及旧联合数字按各自冻结来源解释，不代表当前默认。上一轮完整证据仍保留在evidence/alpha-beta-next-20261002。

'''
    else:
        boundary = text.index('第三轮完成')
        intro = '''# Coinquant

本轮 BTC alpha/beta 完整交付后，开发默认保留 **SX60+DFII10、primary风险7.5/macro3.6、默认规模1**。三种新合约机制均完成压力及实际风险比较并按登记条件拒绝；完整负结果保留。交易所20倍是配置，不等于账户固定20倍敞口。

原CNY10000历史成本后 **119.23% CAGR / 44.11% 连续分钟包络代理MDD**，150%/<50%原目标仍 **NOT_MET**。这批机制失败不能证明收益已经到天花板。未来改进必须保留因果输入、真实新订单风险、成本及时序约束；不按历史启动时间或最优资金比例改默认。

71个原账户及5个共享现货账户独立复核通过。Coinquant负责合约、Spotquant负责现货；Starquant仅保留历史参考/FX。两个手动前向账本绑定实际来源与独立证明，不回填过去；原生案例/实际账户日仍0、**NOT_QUALIFIED**，默认只读。详见 [本轮结果](research/edge-RESULT.md)、[运行/复现指南](research/edge-GUIDE.md)和 [完整证据](evidence/btc-edge-20261003/README.md)。

下方早期轮次和M10数字按各自冻结测量来源解释。上一轮evidence/alpha-beta-next-20261002保持不可变。

'''
    readme.write_text(intro + text[boundary:])
    agents = repo/'AGENTS.md'
    text = agents.read_text()
    if name == 'spotquant':
        a=text.index('The current development default'); b=text.index('One manual session', a)
        text=text[:a]+'''The current development default is SMA30/40/50 plus ATR-stop and registered crowding-interaction, rule2026-10-03-atr-stop-crowding-interaction-v1, scale1. Only genuine NEW BUY changes: halve once when causal settled funding>.0003 AND prior completed UTC paired trade-close basis>.01 AND completed close<=five completed days earlier. Missing required causal features block only NEW BUY. Held quantities, no-topup, pooled90% free cash/whole-account ceiling, ordinary/safety exits, ATR14 clip(4*ATR/close,.10,.30), confirmed native stop floors and fill-owned peaks remain. Stored Model/follow catchup stays28%; no client stop amendment while stopped. Funding/basis public responses use the same causal/provenance parser as replay and paper; no future feature-file feed or private futures client.

Model format5 remains; old execution rule/research identity/incompatible durable state rejects before Lifecycle recovery even when flat. Preserve SQLite and order identities; no automatic migration/reset/new-directory inference. Current operation and reproduction: research/edge-GUIDE.md and canonical-crowding-GUIDE.md. Earlier adoption-GUIDE.md describes the immutable ATR-only historical delivery.

Complete71 financial accounts and5 separate canonical current-runtime accounts independently PASS. Original measured Spot74bd/Pythonf2d6 remains distinct from new canonical609606/Pythonb81f. Later metadata/evidence HEADs require exact protected byte/mode equality and preserve all original Git objects. Full current evidence: evidence/btc-edge-20261003; old alpha-beta-next-20261002 remains immutable. Default56.5981% cost-net CNY CAGR/36.4122% original continuousOHLC proxy MDD versus ATR55.2180%/36.4122%; 2022+actual USDTbeta.300300 versus.337669. Goals100%/<=30% remainNOT_MET. Nativecases0/accountdays0/NOT_QUALIFIED/prospectivefalse. Historical journals have689 unchanged/200 missing-feature-blocked proposals/zero actual halving events: observed benefit does not validate halving profitability. Whole-window/descriptive alpha, contaminated2022+ history and HAC7 are not prospective proof.

Only crowding passed all registered gates; exit-confirm/stop-budget rejected. Coin retains incumbent after three rejected singles; no multi-component combination applies. Actual731day2020–2021training only; scales affect new2022+orders, never held sizing or curves. Fixed three real budget pairs are diagnostics, neutral5000/5000 never historical best-allocation search; joint daily MDD cannot be continuous MDD. Actual paper ledgers are source-bound cold cash, with no backfill or invented observations/native days; fresh_public_market_pending remains truthful when official data is unavailable.

''' + text[b:]
    else:
        marker='## Latest complete BTC alpha/beta delivery (2026-10-02)'
        text=text.replace(marker,'''## Current complete BTC edge delivery (2026-10-03)

Complete71 registered original accounts and5 separately source-bound canonical Spot accounts independently PASS; evidence/btc-edge-20261003 retains all raw/negative/failure/proof identities. Coin quality-budget/cost-horizon/crowding all reject registered paired gates; quality/cost also fail actual risk upper bands. Default SX60+DFII10/primary7.5/macro3.6/scale1 remains unchanged,119.2284% cost-net CNY CAGR/44.1051% original continuous minute/envelope proxy MDD,150%/<50% goalsNOT_MET. Original producer37061/Pythonba638 remains distinct from later metadata/mergeHEADs. Preserve protected source modes/bytes and original Git objects; no schedule/start/capital optimization. Spot adopts crowding development change only after independent71+5 proof, with zero actual historical halving events and missing-input-blocking interpretation disclosed. Runtime repos remain separate and Coin forward reader is standalone.

Current result/operation: research/edge-RESULT.md and edge-GUIDE.md. Actual forward ledgers begin cold CNY10000/BTC0/events0 at realUTC, no backfill and no prospective/native claim. Coin later mark-path uncertainty stays unresolved rather than inventing fills. Nativecases0/accountdays0/NOT_QUALIFIED. User verification policy: reuse passed unchanged scoped/financial evidence; no optional/repeated tests, one final fullCI perrepo. All Coin account producers/tests sharingUID are strictly serial; never change HOME/UID/locks. Engineering work does not authorize private accounts/orders/transfers/settings.

## Previous complete BTC alpha/beta delivery (2026-10-02)''')
    agents.write_text(text)
spot=ROOT/'spotquant'
p=spot/'research/canonical-crowding-GUIDE.md'
text=p.read_text().replace('# Conditional canonical Spot crowding preparation','# Adopted canonical Spot crowding development rule')
text=text.replace('This isolated proposal is not final adoption or native qualification. Original financial review and five actual source-bound account comparisons are required before integration/export/initialization. The registered economics and edge specs remain unchanged. Main and the frozen original sources are separate.','Independent financial review of71 original accounts and all5 source-bound canonical comparisons passed. This development adoption does not establish native qualification. The registered economics/edge specs and original measured sources remain unchanged. Current result and operation are in edge-RESULT.md/edge-GUIDE.md; the full independent proof and source identities are retained in evidence/btc-edge-20261003.')
p.write_text(text)
p=spot/'research/adoption-GUIDE.md'
p.write_text('> Historical ATR-only adoption (2026-10-02), kept under its original source identity. Current runtime/commands are documented in [edge-GUIDE.md](edge-GUIDE.md) and [canonical-crowding-GUIDE.md](canonical-crowding-GUIDE.md). Do not run this old meter/old calibration against the new execution rule. Current minimum-check policy supersedes routine fullsuite repetition below.\n\n'+p.read_text())
print(json.dumps({'updated':stamp,'report_sha256':report_sha,'repositories':['spotquant','coinquant'],'protected_source_changes':0}))

# BTC 升级研究代码使用说明

先读 [升级结果](upgrade-RESULT.md)。三个新候选均被筛选拒绝，正式默认没有切换；历史研究源码及参数保留供下一项明确机制改造参考。普通使用仍按 [默认指南](edge-GUIDE.md)；不需要为了这轮报告重跑研究。

## 查看已完成的结果

`evidence/btc-upgrade-20261004/`保留spot-screen.json、perp-screen.json、spot-all-accepted-attribution.json、冻结规则、来源引用、真实操作起止回执及原失败日志。先查看文件，源码身份取各JSON原始source和Git对象，不把当前HEAD标成原生产者。旧71+5账本和财务证明继续留在evidence/btc-edge-20261003，未再次打包或测量。

两项目都保留同一份本轮简洁证据，以便独立查看结果。跨项目的诊断入口在Spot；Coin的事件筛选入口只读4h行情/资金费。运行只生成研究输出，不接触私有账户。

## 有新的具体问题时才执行

原窗口2020-01-01至2026-09-20（不含）、CNY10000、不加钱，规则upgrade-spec.json。以下为已有入口的复现说明，**本轮已经执行，默认不要再运行**。输出必须是全新文件；已有文件拒绝。工作区外需先按原证据恢复相同输入及原来源，不能随意换样本后比较旧基线。

Spot目录：

```sh
python3.13 -m research.upgrade_assessment \
  --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json \
  --out /NEW/path/spot-screen.json
```

该调用复用两个已接受原始压缩账户用于归因，然后只运行配对日线代理的三个固定模型。日线行情来自/tmp/spotquant-market/klines，PriorFX来自兄弟历史参考../starquant/data/usdcny_frankfurter.json；原账户路径及SHA在模块INPUTS，输入来源限制见证据input-references.json。

仅复用8个已接受crowding账户归因，不运行筛选：

```sh
python3.13 -m research.upgrade_assessment \
  --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json \
  --accepted-attribution /workspace/scratch/btc-alpha-beta-edge-20261003/assessment/complete-final-input-path-fix1.json \
  --out /NEW/path/all-accepted-attribution.json
```

--features仍是原CLI的必填参数，此归因模式不读取它。最终代码另加了接受报告的固定SHA守卫；保留输出仍是原7d0ed74来源，不重标也不重跑。

Coin目录：

```sh
python3.13 -m research.upgrade_perp --screen --out /NEW/path/perp-screen.json
```

加载/tmp/coinquant-market中已接受的4h及结算资金费，不读取整套分钟/逐笔行情，不运行完整账户。正收益筛选也不能直接采用；事件重叠、柱内时钟、资金费代理和执行约束需要完整账户验证。

## 研究适配及前向来源

Spot的model_for/Policy/configured/measure复用已有Model、ATR、Lifecycle与历史有限会话测量组件；仅是研究适配API，没有新增生产CLI或默认开关。Coin PullbackCampaign/variant复用原campaign、仓位归属和durable target路径，recovery历史随checkpoint保存，半风险仅用于新恢复主策略，已有主多单和持仓不替换。最终variant另外绑定候选名和新spec SHA。所有进程内patch离开上下文时恢复，普通运行时不导入这些候选。

本轮没有候选通过筛选，所以无需795会话、原资金/时间偏移矩阵、风险校准组合或原生测量。不得为实现“全部”而强行采用失败策略。新的候选若真有入围理由，先登记它将改变的采用决策、改变的依赖及耗时，再复用匹配旧基线，只测必要新路径。

原前向账本必须继续使用原已接受不可变消费源码：Spot f1383f1034e3f72df68bbda30793d22835e74557，Coin 762d75c22d19686dbd364a6b58b59dbc23340430，以及各自原export/review SHA。新增research文件改变全源码绑定，不要用本轮HEAD观察旧绑定账本，不初始化新目录绕过来源拒绝，不重建已存在账本。实际新鲜公开区间才可形成前向记录；本交付无新增观察或资格证据。原edge-GUIDE的命令示例须结合它写明的原干净提交树执行。

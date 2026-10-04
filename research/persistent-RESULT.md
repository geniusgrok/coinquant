# BTC 多次失败持续换向交付

本轮预登记并完成全部可用分支的实现、可作用普查、经济筛选和证据端点。生命周期之后继续研究新信息、机会生成、共同风险、执行损耗与新时期；没有因第一个候选失败停止。本轮没有通过账户入围门槛的新策略，因此独立账户准入器实际返回 NO_ACCOUNT_ENTRANT，两项目新增账户/会话均0，没有新的795批次或大库扫描。未改交易默认，收益目标仍未达成；收益天花板没有被证明。

## 交易问题与结果

| 项目 / 固定机制 | 独立事件 | 结论 | 经济诊断 |
| --- | ---: | --- | --- |
| spot / entry-chase | 6 | SUPPORT_PENDING | 避免的已结算净损益 -2680.375088735863754084544917 USDT |
| spot / entry-chase-soft | 6 | SUPPORT_PENDING | 避免的已结算净损益 -1340.187544367931877042272458 USDT |
| spot / repair-stall | 0 | SUPPORT_PENDING | 避免的已结算净损益 0 USDT |
| spot / repair-rebreak | 0 | SUPPORT_PENDING | 避免的已结算净损益 0 USDT |
| spot / state-trend | 33 | REJECT_MECHANISM | 事件代理平均净收益 -0.0005019987482324770732656930545 |
| spot / state-range | 1 | SUPPORT_PENDING | 事件代理平均净收益 0.018760321056641814418324208 |
| coin / macro-handoff | 1 | SUPPORT_PENDING | 新腿事件代理合计 -0.04975617197558136 |
| coin / macro-restart | 0 | SUPPORT_PENDING | 新腿事件代理合计 0 |
| coin / state-trend | 20 | REJECT_MECHANISM | 事件代理平均净收益 0.002165655264282824815994538540 |
| coin / state-range | 0 | SUPPORT_PENDING | 事件代理平均净收益 None |

追价的两个表达作用于相同6个批次，是一个信息家族，不能算12个独立机会。负的避免损益表示挡掉的是原盈利，轻量减仓只把金额减半；样本门槛不足且现有经济证据不利，继续保持待证，不试更宽阈值。repair两个不同失效条件均无可合法干预事件；Coingroup只有1次宏观向primary可见轮换，恢复重启0。机会不足与经济失败分开保存。

趋势/区间为新的机会生成函数，使用因果完成的多日价格结构，trend另需quote volume确认。固定原启动时刻重新检查信号，代理事件彼此不重叠。Spot33事件平均约-5.020bp，Coin20事件平均约+21.657bp但早/晚时期净效果不同时为正，两者拒绝。Range Spot仅1/Coin0，不因零机会放宽横盘定义。没有重新测量原core/SMA120/普通再入场/compression/qualitybudget/costhorizon/空头等已关闭研究。

这些是原 owned 现金篮子归因或事件代理，不是账户CAGR/MDD/alpha证明。归因包括实际BTC佣金及售出份额；风险止于每个份额实际退出，排除入场前/退出后整日低点。新事件代理扣固定费用/滑点，Coin另扣真实历史费率的资金费代理；双障碍保守先stop，部分入场柱路径省略、不确定；没有钱包、保证金、宏观竞争、成交深度或原生资格。所有已见历史都是开发数据。

## 研究执行入口

Spot persistent_spot复用当前ATR、crowding、资金池、归属和session/Lifecycle，原缺失输入拦截仍强制；实现追价两个表达、修复仓两个退出与新的机会生成研究适配。Coin persistent_perp复用单owned campaign、保护和session/Lifecycle，新的primary生成器及固定*.75新订单对照有来源绑定checkpoint。已持仓、已消费身份和原宏观优先级保留；quote volume为已验证完成K线的显式研究补充，未建立原生volume桥接。

Coin宏观轮换/重启本轮完成原日志可作用普查和事件假说；独立事件未入围，依据Ponytail及原登记门槛没有编写或启用闲置的实际轮换/重启交易执行器。以后若新证据入围，仍需先关旧仓、真实确认flat及无未决，再建立受原宏观承诺预算限制的新战役；不能重标旧持仓或清consumed制造收益。

独立账户入口只在已通过门槛时加载市场或初始化研究钱包；当前两次准入实际执行，均0账户。事件时钟决定最早季度，禁止按盈利选日期。当前支持Spot研究适配和Coin新primary生成器的有限比较，范围每项目最多1入围项、两季度/三独立账户、全局最多12账户；原启动子集、CNY10000、无追加、300/5、费用/保护/归属/存档审计不变。冷钱包不证明任何真实账户已flat；无合法checkpoint不能伪造沿用旧资金状态。筛选通过也不能自动采用默认或重跑795。

## 共同beta与执行

三个只读新增风险准入机制均实现：联合gross cap4、20日完成收益与已确认止损/费用的20%联合压力预算、两侧事前20日方向都负时gross cap2。必须有两个分别注资账户的当前所有权、保护、未决状态和时间；压力/方向另需因果输入时钟，缺失或未来值返回 BLOCK_UNKNOWN，不提交订单/转账，不改旧仓。JSON只是调用者提供的研究输入，不是独立账户证明。

原三组真实资金配对原样复用：5000/5000联合日收盘峰值5.8863，超过4的日收盘51天（2500/7500为71，7500/2500为24）。收盘超限不能当新BUY次数，涨价也可能增加gross；没有缩放曲线、挑历史最佳比例或虚构干预收益。三个新准入规则的完整账户价值和联合连续MDD仍待独立证明，未上线。

原线性佣金/IOC/资金费结论复用，合并碎片可证明节约0；新增有限公共book采集用于今后真实价差记录，没有maker队列或错失成交反事实就不改执行。新两侧book及OI请求均HTTP451，原响应保存；没有重试或绕过。

## 新信息和新时期

本轮有限8次公开请求：3次451、5次200（option summary加4个ticker）。四个真实BTC期权ticker提供实际delta/mark IV，两组附近30/90日期限、call/put，形成研究用近似25delta RR与期限比；不是DVOL替代、精确25delta插值或可执行IV。首个RR附近30天为-0.0093、期限比约0.91353；只有1个真正接收日，冻结的7日变化信号仍 WAIT_NEW_INTERVAL。OI来源不可用，去杠杆信息不能计算。

persistent_data.capture有限手动采集，无后台任务；evaluate验证原始SHA、单位、资产、maturity/delta、真实接收时钟，按每个UTC日首个有效receipt去重。未来receipt不能提前成为特征；历史今天下载不证明过去发布，接收时刻仅能作为之后研究的首次可用性。新观测不是旧纸账户观察，不回填/迁移/重绑旧ledger，不增加native/accountdays。账户日仍0。

首次qualification误将option-summary列表按ticker对象解析，原结果保留，仅修正summary为选择输入；四个ticker、派生数值及其他响应逐项复用，没有重新请求。accepted qualification-summary-fix1.json/recovery.json保留关系。

## 连续失败后如何执行

- NO_ACTION/样本不足：保留固定规则、记录待证，推进不同机制；新合法事件达到原门槛才重开。
- 真实经济负效果：关闭具体表达；同家族最多两种有经济含义表达用尽后换信息/机会生成。
- 只有较小敞口有效：与最简单统一降预算比较，beta价值与alpha分开；不以加杠杆冒充alpha。
- 信息有优势但执行损耗消除：只有记录支持的具体执行原因才改；没有盘口就进入有限采集。
- 数据/新时期缺失：其余分支继续，等待真正新receipt和新完成区间，不把时间参数、重复轮询或研究Git提交算新样本。

没有无限阈值网格、年度最优比例或启动时间优化。原Spot100%/<=30%、Coin150%/<50%目标与2020-01-01至2026-09-20排他窗口保持。新时期单列研究，不能移动原经济目标的时间窗。旧已批准消费者Spotf1383f1034e3f72df68bbda30793d22835e74557/Coin762d75c22d19686dbd364a6b58b59dbc23340430保持；工程不授权私人账户/订单/资金/设置。

## 来源与验证

规则先登记Spot a67e83d/Coin8f41eb9，补充具体对照/选择限制仍在结果前。第一次新筛选Spot1d6627a、persistent_routes.py原SHA见screen.json，耗时1.570942秒。后续只收紧未在该测量中调用的joint_admission输入时钟，原各项目结果不重算、不重标当前源码；无行为变化的新账户准入输出绑定各自真实source。原负结果、旧研究证据和Git对象保留。

最终软件每仓库一次；失败只补受影响项。本机与远端跳过CI分开记录；软件通过不证明盈利或原生资格。证据在evidence/btc-persistent-20261004，最终测试/正常PR回执补入同目录。

最终软件：Spot371项/11skip、compile和唯一fullsuite PASS，54.052秒；Coin471项/5skip唯一fullsuite1个新增fixture边界错误，compile PASS，7.183秒。原fixture把primary_consumed设为ORIGIN而真实契约严格要求>ORIGIN；仅改为第一根完成4h身份，失败的1项单独0.001秒PASS，接受PASS_COMPOSITE。原错误日志保留，没有第二次全量，没有研究/运行时修改或经济重算。tested HEAD Spot66f375003ae1995dcfbeda9790cb8158478e70b9、Coinfc41badcc86423e9787346189f0ad8f16b8f3287，目标恢复d783ae81e9893f2a6f011c705568a55d1ff4ef74；之后仅文档/证据。远端skip不算通过。

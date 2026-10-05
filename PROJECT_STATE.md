# BTC：2018—2019研究与核心替换实现完成，四候选拒绝

最新用户授权2026-10-05：“把2018年1月到2019年12月的数据用做研究，按你说的这些全部实施”。已补数据、实施Coin双向趋势和Spot底仓＋择时各2固定核心并完成预登记筛选。没有候选通过，0实际历史账户/0实际历史会话/0新795，原默认 SX60+DFII10 / primary7.5 / macro3.6 / scale1 继续保留。main策略/风控可改，但仍须满足replacement-spec明显改善及可比真实账户条件。

2018/2019现货各365/365日合格。2019已有缓存，复用；补2018及2017Sep-Dec预热，共32个成功ZIP/CHECKSUM GET。另2个2019合约4h/funding GET返回451，原失败保留、不重试。合计34GET/36351B/3.463秒，joined3306日packet一次校验后复用，无大库扫描。Coin2018-19仅最高1倍方向报价代理，不是不存在市场的资金费/清算/账户证明；价格end+60s与日线开盘成交、OHLC及2020+日开盘名义金额资金费仍为开发近似。2019缓存及反复用过的2020+不是新OOS。

Coin候选channel55/20＋3ATR及ma20/100＋3ATR，grosscap2/vol60%；共享已有Lifecycle/isolated/IOC/close-all与严格checkpoint，只有offline scope。原生形状fixture确认真实共享cycle开空且BUY TP/SL保护在清算前；这是软件，不是native案例。Spotbase25%＋tactical65%与defensive-base(close>MA100)；整体90%、ATR4clip10-30%、5%再平衡；同现金池、30/40组件分别拥有实际fill，不花未确认卖出款，scope恢复默认origin。代码在research/history_core.py，默认包及配置未改。

Coinchannel2018+10.7361%/MDD25.7369%、2019−14.1731%/22.1583%，两年压力−7.0293%失败。Coinma2018−18.3272%、2019+51.9031%，共同三段−18.4454/+40.3587/−36.6281%，且2019空头2个不足；screen保留SUPPORT_PENDING，assessment明确经济拒绝，不等待放宽数量。Spotbase2018−63.3726%/MDD71.1615%、2019+134.5257%；defensive-base2018−58.4730%/66.2285%、2019+138.6724%；都未通过2018MDD≤63.8897%的原门槛。这是开发报价/OHLC代理结果，不能与原完整CNY CAGR直接比较或当alpha/beta证明。每家族2表达已关闭，不调参救活或启动无入围依据的钱包矩阵。

首批74个低精度案例0.987秒；末端平仓错误引用区间外最后价格导致原现货收益异常，screen-original/源码/日志保留且无效。仅恢复30受影响案例0.688秒，44完整案例绑定复用；资金/区间外价格不影响终值的检查通过。3个必要新软件检查每仓；Coin一个报告字段断言错，只补该项。最终Python3.13编译/全量软件每仓一次：505/5skip PASS，7.425秒。软件PASS不是收益证明；提交skipCI避免重复全量，不说新的远端CI PASS。测量时精确源码与最终经济函数AST桥保留，不因HEAD变化重测。

详情research/history-RESULT.md、history-GUIDE.md、history-spec.json。全部数据/HTTP receipts/规格/原异常/恢复/producer/完整筛选/测试logs在Spotquant evidence/btc-history-2018-2019-20261005/research-artifacts.zip，archive.json绑定；Coin仅共享静态研究行情证据，运行账户独立。研究起始Coinmainca9419954de22b144de9c3472a0f14685b2fe5b4、Spotmaine814b3b9b7ef07947335eec7f8e01c135a2262ca。旧搜索结果和所有负证据保留。

下一次复用730日和原共同区间缓存；需要独立信息/新收益来源或退出机制的新家族，不再测本轮4失败核心。跨现货窗口/同步FX/成熟样本，矿工scope/UTC桶，期权成熟周期等旧pending继续按search-next状态。实际账户仅在信息/经济入围后，冻结源并串行同UID、独立资金时钟、复用适用原基线与解析cache；不要更改schedule/HOME/UID/锁或迁移reset旧状态。Coin119.2284%/44.1051%、Spot56.5981%/36.4122%完整原CNY代理指标与目标NOT_MET不变；native0/accountdays0/NOT_QUALIFIED。旧收益producer/forwardconsumer不改绑，不启后台或操作真实资金。

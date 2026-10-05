# BTC alpha/beta：独立机制搜索完成，候选未采用

2026-10-05用户指令“继续找吧”。目标仍是BTC Coinquant合约与Spotquant现货的alpha/beta改善。当前默认 SX60+DFII10 / primary7.5 / macro3.6 / scale1，恢复锚点 `113a792efc1531e1f00d5629f45e09756dce6e9c`。本轮未证明可采用的改善，运行策略、风险、配置、Python及测试未变。主策略/风控允许替换，但必须先满足 research/replacement-spec.json 的明显经济改善与可比实际账户条件；失败研究不安装默认。

新的平均quote成交额/笔数×收阳固定信息：Coin71独立七日标记通过信息筛选，原50真实初始成交中10受影响；Spot同表达拒绝。按每半首个受影响原机会时间选择2020Q2/2023Q4，各账户独立CNY10000。基线季度收益/MDD分别+29.1427%/34.5599%、+181.8225%/22.1154%。所有新入场过滤为−13.2920%/27.8354%、+187.2414%/22.1154%；macro-only为+12.7201%/26.1846%、+187.2414%/22.1154%。两行动表达均不通过原phase门槛，关闭家族。不把七日负收益归因直接当可删交易：真实机会随后成交，延迟损失趋势收益。

六个完整新钱包账审PASS，一个受阻钱包保留并仅该候选恢复。共7实例、178实际完成会话（171完整+7受阻），不是795；第二表达复用两基线57会话，不能重复计数。账户执行累计214.763秒、三批实际耗时215.119秒；阶段登记到回执507.026/171.433秒。0新795、0大库扫描。Coin冻结源 abfec606a235ae88bf5e691965435ab6c50d1fd1 / Python509f579454f814ae329e8e3fcd01a0599465cf75cc29a5ca29b25249b0c861c2，所有生产已结束。本交付只静态文档/档案，复用原软件502/5skip PASS，不跑全量、不将skipCI说成远端PASS。

Coinbase美元/USDT价格历史1723日均100%覆盖；192区间109收盘溢价事件的控制后前后半方向不同，两项目均拒绝。volume单位仍未合格，未使用。跨场所公开WS30秒/252成交确认Coinbase maker侧反转、Kraken WSv2 taker侧直接使用；共同窗口完整性及连续FX盘口仍缺，只有1真实UTC接收日、0成熟7日结果。矿工FeeTotNtv/IssTotNtv取得2485/2485日，新增官方定义补齐gross/burn但BTC专用范围及UTC桶起末仍pending；唯一固定表达已登记但NO_SCREEN，不放宽输入门槛。期权沿用2真实接收日、WAIT_NEW_INTERVAL。

最新完整结果 research/search-next-RESULT.md；原spec/producer、原HTTP/WS字节与receipt、全部负筛选、受阻/evaluator原失败及完整账户统一保存在Spotquant evidence/btc-search-next-20261005/search-artifacts.zip，archive.json绑定。前次 search-RESULT.md/search-artifacts.zip 保持。仅共享静态研究证据；运行资金/订单/时钟独立，旧收益producer和forward消费者不改绑。本轮开始Spotmain66b8a68756affbaeb8a0dcf0fbb9bbd3b95ff0ed。

下一次只补真实新数据/独立机制：跨现货连续窗口闭合+FX+成熟独立时期，矿工明确scope/bucket官方证据，或成熟期权/合格forced-selling。不要再测本轮两个入场过滤或收盘溢价，不启动后台重复采集，不优化schedule/阈值或原资金曲线。每家族最多2行动表达；输入/信息先合格，才注册必要真实钱包与简单恒定/减预算对照。原Coin119.2284%/44.1051%和Spot56.5981%/36.4122%完整代理指标与目标NOT_MET/native NOT_QUALIFIED不变；没有真实账户操作授权。

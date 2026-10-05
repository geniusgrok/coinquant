# BTC alpha/beta：本轮继续搜索完成

2026-10-05用户指令“那就继续找”。最新结果：**0新账户入围，未证明新alpha/beta改善；旧默认继续保留**。默认 SX60+DFII10 / primary7.5 / macro3.6 / scale1，经济恢复锚点 `113a792efc1531e1f00d5629f45e09756dce6e9c`；main可改策略/风控，但须先满足 research/replacement-spec.json 的明显经济改善与实际账户/压力条件。不得重复 target-core 的收益回落采用。

本轮完成：复用原完整账户成交投影归因；固定价格/主动卖压交互和 UTC 周末条件低成本筛选；第二个真实 UTC 期权接收日；一次跨现货公开数据资格探测。0新账户/0历史会话执行/0新795/0大库扫描/0软件测试/0私有操作。公开GET12次（期权5、跨现货7），全部成功，无旧451重试。

结论：卖压承接根表达0事件，原空闲会话另一表达2个负代理结果，买压耗尽否决0作用，均支持不足；周末減新风险方向被正成本收益及下侧结果拒绝，不能事后转成周末加杠杆。并行价格流量表达重叠完整披露，不算多个独立机制，后续先合并家族管理、最多两表达。Coin12零成交IOC仅3个初始且后来均入场；直接删macro已有完整失败压力证据，不能重测。Spot普通退出占负出售片段69.78%，但精确退出原因不足，未证明代码缺陷。

期权2真实接收日、七日结果未成熟，WAIT_NEW_INTERVAL；跨场所Coinbase盘口时间/美元换算可用，Kraken ticker缺venue事件时间，近期成交窗口不等且主动方向语义未绑定，PUBLIC_DATA_AVAILABLE_CROSS_VENUE_SIGNAL_NOT_QUALIFIED。此为新数据路径实质进展，不是可交易alpha。

详情 research/search-RESULT.md。全量原结果/失败/producer/公开原响应统一保存在 Spotquant evidence/btc-search-20261005/search-artifacts.zip；跨仓仅共享静态研究行情证据，不耦合运行账户。研究开始Coin main39ccfaf70f3aa8eb84d3650c2cf775d2f512c68e、Spot main5bcea8e19147145051c201db7ddffd8de82a0bfd；本交付只新增静态归档/报告/状态，运行与默认未变。复用上一交付Python3.13软件 502/5skip PASS，不重跑、不把skipCI说成远端PASS。恢复PR和原接受源码继续见 evidence/btc-replacement-20261005/GITHUB-INTEGRATION.json。

下一次：从本状态继续，不再重复旧筛选。取得真实新增且时钟/主动方向合格的跨现货固定时间窗，再登记单一需求迁移事件；期权等到真实七日结果成熟后评估。若信号仅FX/动量别名或在人工启动前消失，则转独立forced-selling/期权信息，不放宽门槛/优化启动时刻。入围后才比较独立钱包和恒定风险对照，旧收益生产者和前向consumer身份保持，不用新HEAD重绑旧账本。未达明显改善时不替换默认；不自动后台采集、不迁移/reset、不操作真实资金。

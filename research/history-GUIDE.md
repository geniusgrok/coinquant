# 2018—2019研究续接

先读PROJECT_STATE.md及research/history-RESULT.md。当前四个候选全不采用，不运行默认以外策略或重新测量本轮失败。

原字节证据统一在Spotquant evidence/btc-history-2018-2019-20261005/research-artifacts.zip。解压至 `/workspace/btc-history-2018-2019-20261005` 后读取 `spec.json`、`data-receipt.json`、`screen.json`、`assessment.json`、`software-checks.json`；`screen-original.json`是区间终值错误的失败原件，不可用于采用。Archive里面的 `screen-sources` 是测量时精确核心源码，不应覆盖当前main。

当前研究接口：

- Coin `research.history_core.Signals(bars, 'channel'|'ma', qualified_price_sha)`、`campaign_class(signals)`、`runtime(signals)`；共享现有session与资金/保护/恢复，runtime只接受offline venue。旧默认拒绝其checkpoint，不能重绑原账户状态。
- Spot `research.history_core.Signals(bars, 'base'|'defensive-base', qualified_price_sha)`、`decision(...)`、`runtime(signals)`；共享既有30/40/50所有权分配与P4执行，只有30/40组件使用，runtime只接受offline venue。2017预热origin仅在明确研究scope内设置，离开恢复2019默认origin。
- Spot `research.history_data` 已完成固定采集，已有data receipt时拒绝重跑。`research.history_screen` 已完成固定筛选，已有screen时拒绝新测量；`--recover-terminal`只供原区间外终值故障恢复，现已完成，不应重复调用。

这次没有实际历史账户入围，因此不启动history-spec.json里的季度钱包或完整795。进入新的实际账户阶段前必须有不同、合格的经济依赖和登记的未解决采用问题；保留原固定会话表、原资金/成本/FX、单独账户时钟。Coin账户及同UID测试串行，不改HOME/UID/锁，不删除持久状态；复用适用原基线和解析cache。

两次2019合约公开请求均451，原失败保存，不重试；不得用2018现货价格构造当时不存在的USDT合约资金费/清算证明。2018/2019表里的Coin结果只用于最高1倍方向报价代理，Spot为日线OHLC执行代理。全量软件本地505/401均已一次PASS，skipCI不等于远端通过；后续文档/报告/提交变化不重复测试或历史测量。

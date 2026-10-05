# BTC 生命周期、融资风险与独立信息：实施中
2026-10-05（Asia/Shanghai）。用户授权“按照你说的实施吧，务必达到目标”。目标仍为BTC两项目alpha/beta实质提升；实现功能不等于盈利证明，不承诺未测得的收益。采用遵循benefit-harm-policy，收益下降非单项否决。当前默认尚未替换，旧完成交付及测量身份保持。

本轮登记 /workspace/btc-lifecycle-20261005/spec.json 与 accounts-spec.json（基准spec SHA3b4836947865ec8a6d15f8791178e36746c779d20072c6853369f3e3199b6a0c）。路线：真实持仓获利回吐→确认亏损后的交易记忆→独立需求/事件；融资缓冲依赖真实隔离抵押/dated维护保证金/mark/已结资金费。不能使用模拟固定.005维持保证金率冒充历史档位。每家族最多2经济表达；失败换机制，原负结果保留。

正在并行实施新增研究模块，根任务负责冻结源码、实际钱包测量和整合。先支持筛选，无作用候选不跑钱包；如入围最多8候选钱包，另4独立现货hold25/cash基准（真实成交，独立资金；直接决策时钟不同，不作严格同会话alpha证明）。固定2020Q2/2023Q4沿用旧选定开发窗口，非新OOS；不移动资金/会话或缩放曲线。先复用4旧基线及风险×.75对照。不重跑795/大库校验，同CoinUID生产者/测试串行，实际scratch空间先查，全量软件最终各一次。

待办：完成新模块/因果支持筛选；只测有作用候选，评估实际净益处/失败替代；最终软件一次及普通FF发布；更新结果/来源归档。私有账户/订单/转账/配置、状态迁移/reset、旧forward消费者重绑、后台交易均未授权。新信息成熟/完整性缺口只阻塞对应路线。

前轮已完成：tradeoff-RESULT/GUIDE/roadmap；14独立钱包399被接受会话、旧6复用、7固定联合实际日线配对；没有足够默认采用净益处。共享归档在Spot evidence/btc-tradeoff-20261005/research-artifacts.zip，SHA b2957a708bc5f26d9998ab149f55d98786499e7009e12e5d410c7824e92675e6。前轮完整软件Coin510/5skip与Spot412/11skip PASS各一次，不使本轮新源码自动通过。

原完整代理目标仍NOT_MET：Coin119.2284% CAGR/44.1051% MDD；Spot56.5981%/36.4122%；native0/accountdays0/NOT_QUALIFIED。当前原默认Coin SX60+DFII10/primary7.5/macro3.6/scale1；Spot SMA30/40/50+ATR+crowding/scale1。旧producer/forward source不可标成新HEAD。

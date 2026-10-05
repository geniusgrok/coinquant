# BTC 综合取舍、策略替换与连续换路：本轮交付完成
2026-10-05（Asia/Shanghai）。最新任务“按照你说的全部做完/继续”已完成本轮可执行范围；alpha/beta显著提升及原经济目标仍未证明。读 research/tradeoff-RESULT.md、tradeoff-GUIDE.md、tradeoff-roadmap.json。后续新机制允许继续替换策略/风控；收益降低不是自动否决，不按指标数量或事后权重采用。原规格、失败与负结果不变。

已完成：旧6独立钱包综合重评；新增14冷启动钱包/399被接受有限会话（Coin6/171，Spot8/228），两个事前选定窗口2020Q2/2023Q4；真实simple-risk controls；7固定两仓组合、每个两窗口的独立资金实际日线求和。0新795、0大行情库扫描、不缩放曲线、不转账。完整UTC日线、财务审计、session时钟、原数据/资金/执行及来源比较通过。两个季度为开发选择窗口，非新的OOS或连续路径资格。

结果：宏观过滤Q2下行beta .3457→.3442，uniform75为.2770，水下62→83日；Q4收益较高但尾损/资金费恶化。通道多空Q4下行beta .0430→1.0945、ES5 2.91→5.52%，低MDD不能单独代表改善。已换成空头替代表达，两个季度约−5.1%、仅4/3fills，低beta主要伴随现金暴露，对冲支持薄。Spot防御Q2−3.96%/MDD16.81%，Q4+35.92%/12.85%；简单25%对照+8.11%/5.41%、+8.85%/4.11%。纯择时也已实际执行。候选保留研究，但尚未证明足够综合净益处，不改默认、不开没有采用价值的压力/795；这不是收益回落单项否决。

信息路线已落地有限研究提案：期权新风险/持仓减风险，吸收入场/七日衰减退出，跨场需求入场/风险，交割基差成本。输出0orders/0account_entrants，不是已安装的交易适配器或已验证alpha。7新公开GET/509935B；初次put delta−.19857严格BLOCK保留，仅该资格分支重新选择真实call.2542/put−.23606；IV34.83/35.65%对 causal BTCUSDT RMS43.60%为NO_EVENT。两真实绑定接收日、成熟outcomes0。新观测最早7日点2026-10-12 06:29:48.514UTC，不等于达到样本/控制资格。OI/强平/现货完整4h配对仍缺；真实cross-stream复用但共同窗口/新鲜连续USDT报价/成熟结果未具备；OKX BTC-USDT FUTURES返回code0/data[]，无合格USDT线性交割对，不用inverse/USDC替代。相同451/短流未重试。

恢复：Coin历史标识/终值导出、Spot预热起点/风险身份接入和临时目录满的原失败保留。5个无效Spot导出不接受错误complete标志；成功账户复用，仅失败部分恢复。删除闲置旧cache28个可再生bin/1688176928B，原ZIP、账户、SQLite、存档、锁保留；单钱包实际挂载200MB空间预检。有效账户循环累计140.221秒，不包含输入准备、失败、软件/采集/整合，也非并行实际交付耗时；399非全部执行调用总数。

最终Python3.13全量软件Coin510/5skip PASS、Spot412/11skip PASS，各一次，无失败补跑；测试执行合计约64.12秒。skipCI不宣称远端PASS。最终软件/路由source Coin9ae072874b20280fbfc9eb3e7f8be5d97c7a7d5e、Spot76a47ad1114e362d26587244ff8beb31b6074cbe；原账号producerCoin d83f396/028c3c4、Spot c189efa/2bc60ad，准确完整SHA在GUIDE/原件中。后续证据/文档HEAD不是producer。原评估器模块和结果保持，最终仅额外拒绝无效session，不重跑测量。

原完整代理目标仍NOT_MET：Coin119.2284% CAGR/44.1051% MDD，Spot56.5981%/36.4122%；native0/accountdays0/NOT_QUALIFIED。没有真实账户/订单/转账/凭据/设置、状态迁移/reset、后台、HOME/UID/锁绕过或旧forwardconsumer重绑。沿用原冻结消费者，不能从新HEAD读取旧日记。

下一轮：按tradeoff-roadmap.json的各失败路线换机会/信息来源，先取得真实因果成熟支持并和price/simple-risk controls比较，再登记最少实际钱包、费用/滑点/跨行情压力。只有最终可采用候选有未解决连续路径问题才预算一份新795，旧基线复用。不得重新调同通道长度、重跑这些同依赖季度、降低冻结信息门槛或事后挑资金/会话。必须先读当前状态/预算，Coin同UID所有生产者/软件严格串行；全量软件每完整交付最后一次。

本仓开发默认：Coin SX60+DFII10 / primary7.5 / macro3.6 / scale1。

归档为Spotquant单一共享原件 evidence/btc-tradeoff-20261005/research-artifacts.zip：3381135B / SHA256 b2957a708bc5f26d9998ab149f55d98786499e7009e12e5d410c7824e92675e6 / Gitblob 103f1a273dd3d64260af33cc088639ca93aa186b。完整原钱包、失败、输入、源码、软件日志及842个synthetic状态原件（原字节1022478244B）保留，状态打包一次并以XZ压缩，不复制大行情库；本仓archive.json引用同一原件。

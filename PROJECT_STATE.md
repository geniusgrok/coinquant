# BTC 改造：本轮交付完成

2026-10-05（Asia/Shanghai）。本文件为唯一当前任务状态。8 条策略路线、安全同账户恢复、来源绑定行情缓存和实际组合评估均已实施。16 个完整有限账户452会话；恢复证明2个独立账户24会话；唯一新完整账户795会话，原完整基线复用。

全路径新 `release-new-primary` 拒绝默认采用：净值195.18万→139.68万元，CAGR119.23%→108.58%，路径MDD44.11%→66.51%，日ES5 3.62%→5.49%，最长观测水下期319→729天。29新战役13正/16负，归属净现金流−11528.31USDT。收益、风险和恢复期综合退步，上涨beta变高不足以承担代价；原参考FAIL/负结果不改。两仓保留原默认：Coin SX60+DFII10风险7.5/3.6 scale1，Spot原crowding/ATR。

已存在的局部改善：2023Q1持仓冲击半减/全退收益分别+4.83/+9.76个百分点，MDD不变、ES近似不变，但仅1真实处理事件，保留实现与证据，未推广。剂量对照复现旧semivar98.53%增益，原改善主要来自仓位剂量。Spot新退出路线无增量或经济退步；半预算降低风险但明显牺牲财富，未证信息选择优势。完整/组合/有限结果详见research/progress-RESULT.md，路线见progress-roadmap.json。

历史合成账户金融执行源码Coin52ee50f，原e99恢复等价证明保持原身份；Spot各有限来源62f9d7d/1a9c7f7保留。795由4个有执行段接续，共5次启动（1次零会话setup失败），累计进程执行53.85分钟。原1800秒和原进程上限不满足，setup/storage例外另行登记并保留原声明/失败；没有重跑前段、基线或旧405。全终点后原财务审计一次PASS。完整历史、财务比较和软件检查分别计数。

软件全量每仓仅1次：Coin567项/5skip/原3测试问题，Spot452项/11skip/原1问题；仅测试夹具修复，Coin13项、Spot11项受影响补测各一次PASS，其余原通过证据复用。原FULLFAIL保留，金融源码未因补测修改；未声称remoteCI通过。两个恢复证明状态精确私有压缩保存；同账户最新State、核心快照、所有原来源保存，公开ZIP还原非链快照原字节。

独立alpha、有净好处的全路径beta提升尚未证明；Coin/Spot经济目标NOT_MET，native0/accountdays0/NOT_QUALIFIED。跨场新信息缺closed-boundary/freshFX仍PENDING，无后台采集或未来成熟承诺。下一决策先为持仓冲击退出取得其他固定regime的增量owned支持，失败则换新的独立信息/执行成本机制，不继续调已全路径失败的release阈值。不得自动再跑795、重扫大vault、重绑旧forward/源码或reset账户；CoinUID12000执行与同UID测试串行。

共享原件：Spot evidence/btc-progress-20261005/research-artifacts.zip，两仓同目录archive.json记录摘要；task/保留登记与失败，source/保留原源码，full-account/保留全部报告/快照，delivery/保留最终文档。正常FF推送，最后metadata/证据提交未改经济代码，不需再测。

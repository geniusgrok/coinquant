# Continue Pancakequant

继续 ychenracing/pancakequant 当前改造，全程中文，不重新立项或重复确认已有授权。
先核验远端 AGENTS.md、完整 PROJECT_STATE.md、本文件、实际 main/研究分支HEAD与Actions。
研究分支 research/on-demand-btc-20260920；最新已核验代码/数据3f79f2f53c3aaaf482e5a39850a5de8470f9ce90，
main c886b7c63c6455bd7c933269e32cd35a6fb3e09a未变。以远端实际状态为准，不使用.transfer覆盖代码。

最终仅Binance BTCUSDT，一个模型/适配器/配置，按需run_once，无daemon。
冻结CNY10000、2020-01-01至2026-09-20exclusive、CAGR>200%、连续完整账户MDD<20%、
交易所20x、原稀疏人工触发序列、真实成本/funding/保证金/强平/抵押风险。
不改目标、窗口或口径，不增加杠杆凑收益，不把proxy当native。无真实交易/划转/密钥/账户设置授权。
经济和必要交易安全未通过，不合并main；checkpoint/CI/数据齐备不是任务完成。

最新真实结果：Binance全窗口trade/mark各58896小时，funding7362次，完整性核验已通过。
月度mark缺216小时，由6段官方API原生响应补齐，无插值，不覆盖月度原件。
全部278档案原件和API补页已保全，恢复回执详见PROJECT_STATE.md，禁止重新全量下载。
临时采集CI已移除。新简单CI35568398097最后queued，读取实况；排队时继续独立工作。
早期1000次funding官方API的markPrice全部为空，原件已保存；精确估值缺口仍在，不得伪填。

默认CLI已切换Binance GET-only观察，旧Bybit不再经CLI调用。status对账并保存报告；
run额外读取120根完整4h行情后blocked，--execute在凭据/网络前拒绝。
无已验收生产alpha、完整写生命周期或真实testnet验证，不能称已完成自动交易迁移。
历史Bybit模块仍为研究保留。当前观察器是真实Binance只读API，没有测试网自动回退。

L1/L2账户代理和L3/L4原生预测诊断均已失败。L3/L4不是CAGR/MDD，不能据此声称账户收益。
不做相邻参数微调、不反转L4信号找漂亮结果。2024-end未用于经济调参。
下一步：完整Binance账户回放（资金费/历史规则/USDT估值诚实处理）、新的结构性alpha，
以及原生保护/部分成交/余单/未知结果/保证金的真实生命周期。独立TP/SL不证明原子入场保护。
继续同一研究分支及时提交并回读字节、hash、tree核验。任务尚未完成。

L5 preregistered at59a73abc4fa33d5443614b4313ad44cfc2321acb then measured and rejected: online Bayesian change-point drift,467development observations,364active,correlation-0.00601996,mean net-0.197441% vs constant-long+0.0710532%. Forecast diagnostics only,NOT_QUALIFIED,no2024+validation. Exact source/hypothesis/observations/result in evidence/l5-development-20260921/. No adjacent hazard/prior/cost-threshold tuning or signal reversal. The one targeted posterior-update/symmetry check passed.

L6 native channel-persistence account diagnostic measured. Corrected latest development CAGR2.43722%,conservative continuous MDD6.47025%,final CNY11011.13,22entries,21stops,1liquidation,468original invocations. It passes the preregistered positive-return/sub20%development screen but is nowhere near final CAGR>200%; NOT_QUALIFIED,2024+unused. Corrected funding ordering removes future within-hour mark influence on earlier opening checks; exact-hour funding uses opening mark. Entry/exit events and allinvocations match the initial run. Full old/corrected sources and traces are durable; receipts under evidence/l6-development-20260921/ and evidence/l6-corrected-development-20260921/. Initial attribution:22closedtrades,10winners,mean562.36holding hours,mean unweighted signed underlying trade return9.93%; these are not leveraged account returns. No channel/reward/risk/leverage parameters changed in correctness repair.

L7 persistent channel state measured: development CAGR4.86330%,conservative MDD11.36320%,72entries,2liquidations,468invocations; paired progression gate passed, final economic target still far away. Exact full originals Library libfile_5b982c646b348191a1e0d2c571db6002; receipt/result in evidence/l7-development-20260921/. L8 now preregistered in research/linear-l8-hypothesis.md: current-equity stop-risk reallocation at manual triggers, unchanged0.006risk/2xcap/20xsetting/channels/costs. research/native_channel_replay.py contains L8; older exact sources remain archived. Three targeted resize-accounting/state checks passed. Measure L8 once, preserve result; no2024+validation.

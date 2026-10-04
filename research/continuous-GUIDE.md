# 持续路线工具与决策入口

先读continuous-RESULT.md。六路线结果均已有不可变证据，正常查看无需重跑。continuous_routes.py以原账本、因果完成K线、公共响应和已接受真实资金配对为输入，按连续分支评估；每一分支有采用/淘汰/支持不足/数据不合格的状态，首项失败不会提前结束其他方向。

新增或不同依赖确实出现时，才使用新输出路径运行：

```sh
python3.13 -m research.continuous_routes \
  --spot-root /tmp/spotquant-market --coin-root /tmp/coinquant-market \
  --warmup /workspace/coinquant/evidence/binance-boundary-20260921/warmup-trade.json \
  --projections evidence/btc-flow-risk-20261004 \
  --public evidence/btc-continuous-20261004/public \
  --joint evidence/btc-continuous-20261004/joint-accepted-projection.json \
  --output /NEW/path/continuous-results.json
```

本轮接受的是原各分支结果加受影响风险修正；再次跑整条不是本轮待办，也不能冒充新样本。输出拒绝覆盖已有文件，固定gzip/父报告身份检查。风险篮子代理不缩放真实净值，原账户按原producer消费。

公开数据手动收集独立于账户日记，可选已完成UTC日，每次有限三来源、无重试、5秒超时、512KiB上限，留原字节/请求与接收UTC/状态/SHA：

```sh
python3.13 -m research.public_capture --date YYYY-MM-DD --out /NEW/public-evidence
```

未提供date默认昨日；未来/形成中的日期及已有目录拒绝。HTTP200只代表取到数据，不证明历史发布时刻、修订版本、期权偏斜或可交易alpha；这些回执始终UNQUALIFIED_RESEARCH_RECEIPT，不接入交易和旧纸账户。没有守护进程、账号凭据或自动再次测量。旧账本仍用原已批准不可变消费者。

Spot入围研究适配在continuous_account.py，候选只改真实新BUY的预算，原mandatory crowding安全、持仓、保护、费用、限制与订单身份继续经共享路径；Hook是研究规则，不能拿该cold状态当正式默认状态。本轮已完成两季度5新账户/1复用基线，实际治疗事件0。未来有真实新支持时，先固定有作用且不挑盈利的测量问题；不扩日期直到碰出收益、不改变启动计划、不从空目录推断账户无仓。Coin本轮没有入围执行候选，不写闲置执行改造。

完整原窗口/目标/资金/开始计划保持AGENTS约定；低成本代理只让候选入围，不能把相同净值、更低敞口、样本不足或HTTP页面直接标成通过。已失败的single-topup/成本退出/旧资金配对继续复用，不重复测。

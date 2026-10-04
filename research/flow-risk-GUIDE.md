# BTC 主动成交差异与持仓风险筛选

固定规则和采用门槛先登记在 flow-risk-spec.json。只做 BTCUSDT，复用已审查的完整账户原始日志与现有小型 K 线文件。先普查真正成交的独立机会；代理归因不能当作自融资反事实账户，不缩放净值曲线，不搜索参数或启动时间。只有入围项才编写执行改造、测有限账户，完整795重放须先说明新的决策价值和耗时。

Alpha：前一完整且可用 UTC 日，合约主动买占比为正而现货为非正时，否决新 BUY。Beta：会话内检查已持有风险相对当前预算/入场承诺是否超25%，只减不加；Coin 减仓必须降低持久化 requested，保留原生保护和身份。Spot 以 ATR 压力距离为预算代理，不冒充原生止损的损失保证。

缺新可选信息时沿用 incumbent，已有必要特征缺失保护保持。历史可用时刻只是保守假设；本轮不是前瞻验证。旧日志与旧前瞻消费者保留原有源码身份。本轮没有真实账户权限。

## 重现与消费

查看 flow-risk-RESULT.md 和 evidence/btc-flow-risk-20261004/screen-recovery2.json 即可使用本轮已验结论，不需再运行筛选。若数据/规则依赖实际变化，脚本可单次生成新的归因结果：

```sh
python3.13 -m research.flow_risk \
  --spot-root /tmp/spotquant-market \
  --coin-root /tmp/coinquant-market \
  --warmup /workspace/coinquant/evidence/binance-boundary-20260921/warmup-trade.json \
  --projections evidence/btc-flow-risk-20261004 \
  --output /tmp/new-flow-risk-screen.json
```

目录可替换为持有相同原始文件的路径；ZIP校验和、bar冲突/对齐/金额/完整天与父账本gzip固定哈希均检查。脚本无网络、账户、订单写入；只输出诊断JSON。错误只恢复受影响项目时，使用 --kind spot/coin --reuse-results 原JSON，另一项目结果带原源码与结果哈希保留，不能重标。历史60秒可用假设不是实测发布延迟；前瞻若恢复需在旧消费者或明确兼容版本中记录真实接收时刻。

下一步只有两种新的、不同依赖才有测量价值：新的可信信息/预先固定规则，或官方公共数据恢复后的真正前瞻积累。不能对本轮同一符号/门槛继续网格调参、重新挑启动日期或重复795。

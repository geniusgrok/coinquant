# Binance 执行能力：新增离线安全操作，生产仍只读

2026-09-21复核官方USDⓈ-M REST Trade规范：
https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade

新增coinquant/binance_safety.py，仅复用原BinanceReadOnly与durable State，
通过注入sender验证原生请求协议；没有接入生产网络writer或开启CLI执行。
默认authorization=False在任何写前拒绝。当前reader身份命名仍live，未伪造testnet兼容。

- 原生algo closePosition全仓SL后TP，MARK_PRICE且priceProtect=false；不混入quantity/reduceOnly，保留旧保护；要求无剩余入场单。部分已成交持仓使用全仓保护。
- 保护按stable ID先durable intent后发送；超时回读，已有intent不重新发送；单独ACK不能证明保护有效；最终账户回读核查持仓、保护及强平相对位置。
- 已记录所有权的普通入场单可撤单；查询终态及实际成交数量，撤单与全部成交竞争返回真实持仓，不推断零成交。条件入场仍不支持。
- reduce-only减仓需当前账户、数量规则和无剩余入场验证；未知终态不报告成功；不允许反向或未达到请求减仓量。
- 已有资金的模型目标逐仓保证金只允许增加，不提款；无client transaction ID的未知保证金写入保持pending并阻止新epoch重试，不用余额变化猜定成功。

离线定向验证通过：未授权零写入、部分持仓全仓保护、超时已接受后回读、
未知查询禁止重试、剩余入场阻止、撤单/成交竞争、reduce-only、未知保证金阻止重试、
保证金目标回读。总31项包含信号/既有账本/CLI等定向测试，不是31项原生账户验证。

仍未验证/完成：原生授权testnet生命周期、可写网络transport、原子入场与部分成交保护、
条件入场余单及子单竞争、状态完全丢失后的入场历史恢复、保证金超时的唯一事务归属、
保护更新与已触发子单竞争的完整闭环。保护价格/减仓数量过滤只是当前规则检查，
并不等于原生全生命周期合格。已有未知状态只能read-only恢复，不能自动补建风险。
没有调用真实账户或测试网交易API；没有资金划转/设置修改/密钥修改。

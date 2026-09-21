# Binance保护替换与恢复

目标仍为BTCUSDT、单向BOTH、逐仓20x。默认只读，生产--execute仍在读取凭据前阻止。
没有授权testnet账户，未执行任何交易或账户设置操作。

官方核验（2026-09-21）：
- [Trade API](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade)：条件单POST/GET/DELETE /fapi/v1/algoOrder；普通修改仅LIMIT。
- closePosition适用STOP_MARKET/TAKE_PROFIT_MARKET，不能同时传quantity或reduceOnly；不是普通限价改单语义。
- [错误语义](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/error-code)：超时可能已执行，订单冲突/数量/触发价格约束可能拒绝请求。
文档没有给出本账户必然接受两套全仓保护的保证；实现不把提交请求等同于并存成功。原生能力仍待验证。

## 实际调用链

replace_protection -> 绑定授权/账户/旧单durable ownership -> 固定replacement journal -> protect_existing安装并查询新SL/TP
-> 每撤一旧单前再次查询两新保护及账户 -> durable DELETE intent -> 父单与真实子单终态 -> 账户回读。
条件单若已触发，query_intent沿actualOrderId读取普通子单；CANCELED父单不能掩盖NEW/PARTIALLY_FILLED子单。
不使用取消全部订单接口，不在本地状态丢失时以相似ID猜测拥有权。

新保护被拒绝、超时未确认或一条腿缺失：不撤旧单；相同ID不重复提交，状态显示未解决。
旧单撤销超时：先查询，只有父单及子单都终态才继续；下一run恢复相同journal/ID。
两保护并存发生部分成交/仓位变化：停止下一写入，保留有效close-all保护。尚有入场余单则阻止替换。
原仓位已平：恢复流程只清理已拥有保护，绝不重建仓位。残余数量变化不会自动当成原数量继续替换。
未知的已拥有保护撤单不会阻止显式授权的reduce_existing风险移除；未知入场意图仍会阻止。
部分成交后可调用该reduce-only路径移除剩余风险，再恢复flat cleanup；本轮仅离线验证，没有执行账户操作。
本地状态丢失：旧单ownership无法证明时阻止写入，只读snapshot仍可观察真实仓位/保护；需恢复durable原件，不能假装成功接管。

CLI status/run已接入read-only取消意图恢复；即使没有pending订单，未完成replacement journal仍明确报告unknown。
旧journal完成后的重复调用不重新保护后来仓位；新请求不能覆盖未解决替换。
每一步有可恢复记录，但没有分布式事务或原子改单保证。

## 验证及缺口

离线覆盖新单拒绝、未知新单、撤单超时前后、真实重开SQLite恢复、父单取消/子单部分成交、
部分仓位变化、平仓清理、未授权写入、丢失ownership、修改未解决请求及授权风险移除。
35项相关定向用例分批通过，复用未变更验证；具体记录verification.json和原件日志。
仍缺目标账户原生并存许可、成交竞争/网络中断真实路径、订单限额及交易场景验证；不能用mock当原生证明。
模型与完整生产writer尚未整合，V2更新仍只能在run_once时发生，本轮未启用V2为生产模型。

保存后的接口复核发现并修复：单个DELETE /fapi/v1/algoOrder文档参数不包含symbol，
初版沿用了普通订单撤单的symbol字段。已从native请求移除，BTCUSDT范围改由原始durable保护intent及query_intent确认。
加入严格参数集合断言，受影响30项替换/安全/恢复检查通过；经济回放不受影响，不重复回测。
初版源码保留在已上传原件和af7095c，当前修正版本以Git最新提交为准，不能把先前mock通过当原生API合规证明。

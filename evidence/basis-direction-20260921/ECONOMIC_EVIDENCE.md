# 历史经济证据与实际影响

所有来源获取于2026-09-21，完整响应及哈希见原件economic-inputs。此表不生成伪造historical rules。

|项目|来源/适用日期|当前代理及缺口|L实际影响与下一步|
|---|---|---|---|
|手续费|Binance fee/futureFee页面；account API User Commission Rate|页面未给机器可读费率记录；当前账户费率也不能回填2020。旧0.075%沿历史研究代理，不是已核验Binance时间轴|每1bp固定数量189.57USDT；保留旧费率，补标准费率生效日及VIP/BNB/地域适用证据，再配对重算|
|tick/step/min/max/order count|已保存2026-09-21 exchangeInfo，官方market-data schema|tick0.10、step0.001、market max120、min notional50、ordinary orders200只是当前快照；强平fee1.25%不能冒充所有历史|已成交尺寸不触及当前max/min；旧保护价格按0.5代理取整仍影响时点，补历史变更时间戳，native条件单并存/限额仍未验证|
|风险档位/MMR|官方account/leverageBracket；含notionalFloor/Cap、maintMarginRatio、cum、账户notionalCoef|引擎统一0.5% MMR+0.075%关闭费，无历史完整档位。exchangeInfo maintMarginPercent不可拿来代替tier|L最高124336.89USDT、L0 40472.50；必须优先覆盖此名义范围，不能全用最低档。未取得有日期的cum/MMR前NOT_QUALIFIED|
|逐仓保证金/强平|当前引擎funded_target与Account；官方Leverage and Margin|在20x设置上模拟额外逐仓资金以保证stop与liq间有gap；原生转保证金/保护安装顺序未验证|分钟新回放无强平分类，但不证明安全；共享净目标必须报告所需额外margin，原生不可验证不得增加风险|
|funding率/mark|官方历史ZIP+GET/fapi/v1/fundingRate；仅46个持仓月份|4181条率一致，1897条有mark；更早记录mark为空。当前FAQ更新2026-03-06有15秒边界偏差，不证明2019起文字未变|L支付147次mark可核实，固定数量差1.49USDT；旧省略收入约24.45。保留旧代理，精确/区间/边界分开。方向筛选已采用不利边界|
|CNY/USD|Fed H10 / FRED DEXCHUS，日观察至2026-09-11，9/14发布|非连续可交易报价；日期值有发布延迟/修订可能。旧FX6.9762中间价与H10不是同一测量|四账本同口径参考重估，9/12–19不回填；不能给全窗新CAGR。先补最后区间及正式估值约定|
|USDT/USD|已有Kraken官方历史档案说明；本轮未获得连续原始序列|USDT=USD仍代理；不添加第二交易适配器|全余额均受脱锚影响，不能仅给持仓扣风险；需完整覆盖的估值源。假设0.95–1.05会使MDD上界升至1-(1-DD)*0.95/1.05，该为情景而非历史事实|
|分钟顺序|官方data.binance.vision trade/mark 2024-03-05、2021-01-02，CHECKSUM核验及重建|旧24日扩至26日，其余小时内未知仍留保守包络|四个全窗账户订单/CAGR/MDD完全一致。补关键风险日期没有产生alpha或消除其余小时不确定性|

来源：
- https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data
- https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account
- https://www.binance.com/en/fee/futureFee
- https://www.binance.com/en/support/faq/detail/360033525031
- https://www.binance.com/en/support/faq/detail/360033162192
- https://fred.stlouisfed.org/series/DEXCHUS

优先级：名义范围内历史tier/cum及USDT估值 > 账户费率条件 > 其他不影响这些候选的档案。
不能凭估值重标、去成本或缺失规则补当前值来达到验收。

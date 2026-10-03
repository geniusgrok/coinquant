# 当前 BTC 策略、手动前向观察与复现

当前结果见 [edge-RESULT.md](edge-RESULT.md)，逐文件保留与恢复见 [证据包](../evidence/btc-edge-20261003/README.md)。历史指南及旧证据保持原来源身份；不能用当前执行代码代替冻结的旧生产者。

## 现货开发采用

当前规则2026-10-03-atr-stop-crowding-interaction-v1，SMA30/40/50、ATR14保护、默认规模1。拥挤度只约束真正NEW BUY，三项同时成立时减半一次；缺失只阻止该BUY，安全退出/止损不依赖这些数据。没有旧持仓补仓或自动资金再平衡。公开BTC fundingRate及配对现货/期货1d klines共用原始响应、SHA、请求/接收时钟和相同因果解析；不读未来历史特征文件，不请求私有期货账户。

funding结算+28800000ms才可用，自availability起age≥28800000ms即过期；basis使用closeTime+1的匹配UTC完成边界、完成+60000ms可用、当前UTC可用日期及最多一日年龄。响应接收须≤决策，且最多一分钟旧。不能用未完成K线或预测资金费率，也不能把缺失/非有限值变为0。详细说明 [Spotquant现货规则细则](https://github.com/geniusgrok/spotquant/blob/main/research/canonical-crowding-GUIDE.md)。

旧规则/不兼容状态恢复前拒绝，包括平仓状态。Model格式5不代表执行策略版本兼容。保留旧State/SQLite/订单身份，只读核对或受控迁移需要额外真实账户证据；本交付未进行迁移，不创建空目录绕过拒绝。Spot的run --execute继续阻止；Coin受控Demo/小额试验入口仍须原授权和全部账户保护门，默认只读。工程工作不授予账户、订单、转账或设置权限。

## 手动前向影子账本

使用本轮保留的原始forward-binding导出，按清单无损还原gzip并核对原始SHA。不要用新导出来冒充本轮已审查的信任锚。Spot与Coin分别从各自干净的提交树运行；Coin读入导出时无需导入Spot或兄弟仓库。实际导出/初始化身份及原始FX配对响应在证据包forward/中。

```sh
python -m research.edge_forward init --diary /NEW/path/ledger.json \
  --export /restored/forward-binding.json --export-sha d2bc7eca7f2dfdb9a1049c41f1f80f10f603cedc8ab2f9d8bcb260897fab3b31 \
  --review-sha 50dc293c8225027f2bfa49508cdd058f2ccc4a44ebb4976f3b41b206d048aefc \
  --defer-market-warmup
```

本轮已实际初始化的账本不能被这个示例重建覆盖；此命令是日后新观察记录的说明。初始化真实当前UTC/CNY10000/BTC0/事件0，真实FRED DEXCHUS CSV及发布Dataset元数据共同验证，无历史回填。周度FX基准不是可执行报价。市场pending不是已观察或已盈利。首个新鲜完整市场区间预热，之后真正新的区间才有提议；旧信号消耗、缺失/未知保护保持拒绝。Coin mark路径无法证实时保持未解决状态，不伪造成交。没有守护进程或保证自动收集。

```sh
python -m research.edge_forward observe --diary /existing/ledger.json \
  --export /restored/forward-binding.json --export-sha d2bc7eca7f2dfdb9a1049c41f1f80f10f603cedc8ab2f9d8bcb260897fab3b31 \
  --review-sha 50dc293c8225027f2bfa49508cdd058f2ccc4a44ebb4976f3b41b206d048aefc \
  --url 'https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=4h&limit=150' \
  --url 'https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=1000' \
  --url 'https://fapi.binance.com/fapi/v1/aggTrades?symbol=BTCUSDT&limit=1000' \
  --url 'https://fapi.binance.com/fapi/v1/exchangeInfo' \
  --url 'https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT' \
  --url 'https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=100' \
  --url 'https://alfred.stlouisfed.org/series/downloaddata?seid=DFII10' \
  --url 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXCHUS'
```

--url参数接收实际官方URL，类别由URL识别，不使用category=URL语法。必须传入完整所需公开输入，含当前DEXCHUS FX配对证据。具体所需公开类别以各仓库edge_forward.py CLI与当前指南所述为准：Spot另需futures_bars/crowding_funding，Coin需mark/funding/dfii配对公开证据，观察还保留FX。响应必须实际取得且时间/来源/哈希满足契约；HTTP失败留原始响应，不绕过地理限制。Observe是纯公开、显式模型成交影子账本，不是交易账户/原生成交。不要为了让事件数变大回填观察或反复刷新同一区间。

## 复现与检查

证据包MANIFEST映射原绝对路径、保留路径、字节数及SHA，gzip为明确的无损存储，原始JSON与原始压缩生产者SHA不同概念。保留原始Git历史及三个互异来源：原研究生产者、评估器、共享现货运行时；官方大规模市场档案按绑定CHECKSUM及原输入清单获取，包不复制14GB公共档案。额外2026-08-01 BTC aggTrades官方ZIP/CHECKSUM已单独保留。

复现经济研究是按冻结命令执行完整账户，不是日常启动前的检查。不要重新启动已经完成的实验队列。已通过且来源不变的检查直接复用，普通变更只运行受影响且必要的检查；完整离线CI仅最终提交一次。Coin共享UID的任何合成账户始终串行，不能改HOME或移除锁。

默认收益选择、软件CI、财务复核和原生资格分别保留真实状态。没有证明的原生案例/实际账户日为0，原收益目标未达，未来alpha未证明。

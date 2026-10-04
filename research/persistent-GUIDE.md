# 持续失败换向操作入口

先读persistent-RESULT.md。当前所有可用分支已筛选，没有账户入围项；正常查看无需重算。下一轮必须来自新信息、真实新时期或不同机制，不重复旧候选。

有限手动公共观测：

```sh
python3.13 -m research.persistent_data capture --out /NEW/public
python3.13 -m research.persistent_data evaluate --history /NEW/public /OTHER/public --at-ms ACTUAL_UTC_MS --out /NEW/feature-decision.json
```

每次最多8请求（登记上限9），5秒超时、每响应2MiB、无重试/守护程序。标记IV和实际delta仅用于附近期限/近似25delta研究，需不同真实接收日及新完成区间；1日、DVOL或历史修订表都不能伪装七日信息。OI假说另需含completed_day_ms、available_ms、source_sha256、day_return、spot_taker_imbalance的完成日context，未来/不配日期不可用。始终accountdays0/orders0，旧ledger不接入这些文件。

只读两个账户的新增风险建议：

```sh
python3.13 -m research.persistent_admission --snapshots confirmed-input.json --proposal new-risk.json --rule gross-entry-cap --out /NEW/admission.json
```

snapshots.accounts必须恰为spot/coin两份，字段symbol=BTCUSDT、receipt_ms、owned/protected/pending、equity_usdt、gross_notional_usdt、stop_risk_usdt。freshness60秒；所有权或保护未知拒绝。压力/状态另需20个completed_returns和context.completed_through_ms/available_ms/source_sha256；状态还需每账户momentum20/momentum_available_ms。proposal明确symbol、BUY、gross_notional_usdt和stop_risk_usdt。这是调用者提供的研究数据，不能从新目录或布尔字段推断真实账户安全；输出从不发单/调仓/转账。

已有筛选结果的账户准入无需市场加载：

```sh
python3.13 -m research.persistent_account --kind spot --screen evidence/btc-persistent-20261004/screen.json --out /NEW/spot-screen
```

Coin对应--kind coin。当前返回NO_ACCOUNT_ENTRANT，0账户；不要为了“跑过账户”去改门槛。未来真正入围时需原market/FX/features/schedule；Coin再需原prints。最多两季度、40开始时刻/账户、每项目六账户/1800秒；Coin真实账户生产/测试仍strict serial，不改HOME/UID/锁。无checkpoint只做显式独立cold钱包，不能串成完整曲线或推断实盘flat。后续宏观轮换/重启若入围，需先补与原风险承诺及保护一致的执行桥接，不能直接清旧身份。

廉价诊断命令保留，仅用于新依赖或新问题：

```sh
python3.13 -m research.persistent_routes --spot-root /tmp/spotquant-market --coin-root /tmp/coinquant-market --warmup /workspace/coinquant/evidence/binance-boundary-20260921/warmup-trade.json --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --schedule /workspace/coinquant/research/session_schedule.json --output /NEW/screen.json
```

所有输出拒绝覆盖，源码/规则先冻结。事件代理不能自动采用；真正入围后的完整经济比较另明确未解决问题、相对旧证据的新依赖和预算。软件全量只在最终交付一次，失败仅受影响恢复。两个运行时保持独立，Starquant仅历史/FX参考。

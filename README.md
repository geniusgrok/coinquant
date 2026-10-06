# Coinquant

个人使用的 Binance BTCUSDT USDT 本位永续交易程序。当前策略为 SX60 + DFII10，风险参数为 7.5 / 3.6；使用单向、逐仓、20 倍杠杆账户。默认只读，手动启动有限会话，没有后台守护进程。项目仅使用 Python 3.13 标准库；系统需提供 `America/New_York` 时区数据。

## 配置与只读运行

```sh
cp config.example.json config.json
python3 -m coinquant status --config config.json
python3 -m coinquant run --config config.json
python3 -m coinquant snapshot --config config.json --out /tmp/coinquant-snapshot.json
```

先填写 `config.json` 的 `account_uid`，使用核验一致的 Binance UID；`state_dir` 使用该账户固定的绝对路径或 `~` 路径。配置不存凭据。

| 字段 | 用法 |
|---|---|
| `environment` | `live`（默认）或 `demo`，账户、凭据和状态分别隔离 |
| `session_seconds` | 会话时长 1～86400 秒，默认 300 |
| `poll_seconds` | 轮询间隔 1～60 秒，默认 5，不超过会话时长 |
| `capital_limit_usdt` | 可选正值十进制字符串，限制策略用于定仓的资金；不是亏损上限 |
| `max_stop_loss_fraction` | 可选入场资金基数到止损损失预算，十进制比例；须与下一项同时填写，未设置时保持原策略定仓 |
| `stop_slippage_fraction` | 上述预算采用的止损逆向滑点假设，十进制比例；预算还计入双边实际 taker 费率 |

主网凭据从 `COINQUANT_BINANCE_KEY`、`COINQUANT_BINANCE_SECRET` 读取，Demo 从 `COINQUANT_BINANCE_DEMO_KEY`、`COINQUANT_BINANCE_DEMO_SECRET` 读取。两套凭据互不回退。

`status` 读取一次账户和合约条件；`run` 在期限内观察、恢复订单状态、判断策略并输出预览。`snapshot` 导出新鲜只读账户 JSON，输出文件必须不存在。

## 有限交易试运行

```sh
cp config.demo.example.json demo.json
python3 -m coinquant run --config demo.json
python3 -m coinquant run --config demo.json --execute --trial demo --authorize-uid <DEMO_UID>
```

填写专用 Demo UID、固定状态目录和正值资金上限。执行需同时提供 `--execute`、匹配配置环境的 `--trial` 和匹配账户的 `--authorize-uid`；入口不会强造策略入场。

主网试运行使用 [config.live-trial.example.json](config.live-trial.example.json)，还需 `--trial live --demo-evidence <JSON>`。Demo 验收后用只读命令采集证据：

```sh
python3 -m coinquant demo-evidence --config demo.json --out demo-evidence.json \
  --entry-order-id <ENTRY> --stop-algo-id <STOP> --take-algo-id <TAKE> \
  --reduction-order-id <REDUCTION> --offline-trigger-order-id <TRIGGER>
```

命令核对 Demo 专用 UID、持久状态中的原始委托、交易所原生订单与成交，以及 SQLite 和观察归档中的会话报告；要求保护回读、部分减仓、停机后触发与再次启动核对。必需订单还须有当前源码版本 Demo 会话中的原身份与发送时间记录；新版安全恢复旧仓位，不会把旧版委托算作新版 Demo 验收。证据文件只保存在本地，主网入口会重新做只读 Demo 核对，单独填写订单 ID 不会通过。采集和核对都需要用户另行授权的 Demo 账户访问；当前仓库没有原生验收结果。

会话日志保留入场前盘口时间、买卖价、限价内可见量、请求与回读时间及原生成交量/价格；对账报告在交易所提供成交价时计算保护触发价到实际成交价的滑点。缺项保持缺项，不按零成本补值。这些观察用于后续校准旧回测代理，当前尚无真实样本。

执行先持久记录订单身份，成交后确认交易所托管的整仓止损和止盈。丢失回包时查询原身份；未解释的成交、资金或保护状态阻止新增风险。会话到期或中断后停止开仓，已开始的保护或减仓可能使用有限清理时间，确认的原生保护留在交易所。

## 账户状态

固定 `state_dir` 保存 `intents.sqlite`、`latest.json` 和执行锁；账户锁还保存在 `~/.local/state/coinquant/account-locks`。同一账户只使用一台机器、一个客户端。重启继续原订单身份；状态不匹配时只读核对，不删除数据库、不改 UID 或换空目录绕过。

启动时间可以不固定。每次运行都会重新核对实际持仓、原生保护与策略状态；报告中的 `next_required_review_at_ms` 标示下一根完整四小时 K 线的复核点，宏观数据或订单变化可能更早需要复核，程序不会自动唤醒。停止进程后只有交易所原生保护可能执行；七天到期、宏观数据变化和新信号均要等下一次人工运行。只读快照也不证明止损触发和重启执行已经验证。

持有仓位时，恢复对账依赖原 `state_dir/intents.sqlite` 中的订单身份、原生成交和历史覆盖记录，以及交易所可回读的订单、保护子单和从已核对边界至今连续的 BTCUSDT 成交。未覆盖的区间若超出最近约三个月的原生查询窗口，或子单终态、成交归属无法证实，程序会报告 `unknown` 并阻止新增风险；不会靠价格推断补齐。保留原状态目录，核对原环境与 UID、订单及子单身份、成交和当前仓位与保护状态，必要时人工处理敞口；不要换空目录、篡改覆盖记录或重发身份未明的订单。

`snapshot` 提供本账户的方向、BTC 名义金额、未保护名义金额及按现有止损触发价计算的价格距离损失。价格距离损失不含手续费、滑点或跳空，不能当亏损上界。SX60 和 DFII10 在本账户共用一个单向持仓；可选预算在每次原生入场及同一持仓追加前按新鲜账户余额、双边手续费和指定逆向滑点估算整仓到止损损失。它不保证跳空时不会超额，也不代表已有历史回测使用该预算。本项目独立运行，不要求与其他项目同步启动或合并账本。

## 当前完整回测

2026-10-06 对当前运行代码 `47837e3` 完成独立 1 万元账户的完整回测（2020-01-01 至 2026-09-20 UTC，末端不含，795 会话，不追加资金）。期末人民币权益 **1,951,753.81 元**，年化净收益 **119.23%**，人民币路径最大回撤代理 **44.11%**。

结果已计入模拟成交成本和换汇成本；历史价格与执行使用代理，历史窗口曾用于开发，不证明实盘或样本外 alpha。详细口径、权益图及数据见 [BACKTEST.md](BACKTEST.md)。

开发说明见 [AGENTS.md](AGENTS.md)，当前任务状态见 [PROJECT_STATE.md](PROJECT_STATE.md)。历史代码、研究和交付记录保存在 [archive/pre-slim-20261006](https://github.com/geniusgrok/coinquant/tree/archive/pre-slim-20261006) 分支。

项目供仓库所有者个人使用，公开可见不授予第三方使用许可，详见 [LICENSE](LICENSE)。

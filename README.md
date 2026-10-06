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

主网凭据从 `COINQUANT_BINANCE_KEY`、`COINQUANT_BINANCE_SECRET` 读取，Demo 从 `COINQUANT_BINANCE_DEMO_KEY`、`COINQUANT_BINANCE_DEMO_SECRET` 读取。两套凭据互不回退。

`status` 读取一次账户和合约条件；`run` 在期限内观察、恢复订单状态、判断策略并输出预览。`snapshot` 导出新鲜只读账户 JSON，输出文件必须不存在。

## 有限交易试运行

```sh
cp config.demo.example.json demo.json
python3 -m coinquant run --config demo.json
python3 -m coinquant run --config demo.json --execute --trial demo --authorize-uid <DEMO_UID>
```

填写专用 Demo UID、固定状态目录和正值资金上限。执行需同时提供 `--execute`、匹配配置环境的 `--trial` 和匹配账户的 `--authorize-uid`；入口不会强造策略入场。

小额主网试运行使用 [config.live-trial.example.json](config.live-trial.example.json)，还需 `--trial live --demo-evidence <JSON>`。该 JSON 必须匹配当前源码摘要，Demo 资金上限不低于本次上限，并包含 `demo_uid`、`entry_order_id`、`stop_algo_id`、`take_algo_id`、`reduction_order_id`、`offline_trigger_order_id` 六个真实原生身份及 `demo_capital_limit_usdt`。这是程序实际检查的交易入口条件；历史模拟不能替代原生回读。

执行先持久记录订单身份，成交后确认交易所托管的整仓止损和止盈。丢失回包时查询原身份；未解释的成交、资金或保护状态阻止新增风险。会话到期或中断后停止开仓，已开始的保护或减仓可能使用有限清理时间，确认的原生保护留在交易所。

## 账户状态

固定 `state_dir` 保存 `intents.sqlite`、`latest.json` 和执行锁；账户锁还保存在 `~/.local/state/coinquant/account-locks`。同一账户只使用一台机器、一个客户端。重启继续原订单身份；状态不匹配时只读核对，不删除数据库、不改 UID 或换空目录绕过。

停止进程后不会继续计算策略或修改保护。只读快照也不证明止损触发和重启执行已经验证。

## 当前完整回测

2026-10-06 对当前运行代码 `47837e3` 完成独立 1 万元账户的完整回测（2020-01-01 至 2026-09-20 UTC，末端不含，795 会话，不追加资金）。期末人民币权益 **1,951,753.81 元**，年化净收益 **119.23%**，人民币路径最大回撤代理 **44.11%**。

结果已计入模拟成交成本和换汇成本；历史价格与执行使用代理，历史窗口曾用于开发，不证明实盘或样本外 alpha。详细口径、权益图及数据见 [BACKTEST.md](BACKTEST.md)。

开发说明见 [AGENTS.md](AGENTS.md)，当前任务状态见 [PROJECT_STATE.md](PROJECT_STATE.md)。历史代码、研究和交付记录保存在 [archive/pre-slim-20261006](https://github.com/geniusgrok/coinquant/tree/archive/pre-slim-20261006) 分支。

项目供仓库所有者个人使用，公开可见不授予第三方使用许可，详见 [LICENSE](LICENSE)。

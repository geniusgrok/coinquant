# Coinquant

个人使用的 Binance BTCUSDT USDT 本位永续交易程序。当前 SX60 + DFII10 模型只做多，定仓乘数为 7.5 / 3.6；它们不是亏损比例上限。使用单向、逐仓、20 倍杠杆账户。默认只读，手动启动有限会话，默认 300 秒，没有定时唤醒或后台守护进程。当前尚未完成交易所原生执行验收。

## 安装与配置

使用 Python 3.13，程序仅依赖标准库；系统需提供 `America/New_York` 时区数据。取得代码并复制配置：

```sh
git clone https://github.com/geniusgrok/coinquant.git
cd coinquant
cp config.example.json config.json
```

先填写 `config.json` 的 `account_uid`，使用核验一致的 Binance UID；`state_dir` 使用该账户固定的绝对路径或 `~` 路径。配置不存凭据。

| 字段 | 用法 |
|---|---|
| `environment` | `live`（默认）或 `demo`，账户、凭据和状态分别隔离 |
| `session_seconds` | 会话时长 1～86400 秒，默认 300 |
| `poll_seconds` | 轮询间隔 1～60 秒，默认 5，不超过会话时长 |
| `capital_limit_usdt` | 可选正值十进制字符串，限制用于定仓的资金；未设置时使用钱包余额，不是亏损上限 |
| `max_stop_loss_fraction` | 默认 `".49"`，整轮到止损模型损失预算，基于已核实入场权益与资金上限的较小值；已成交部分计实际费用，未来部分采用当前 taker 费率 |
| `stop_slippage_fraction` | 默认 `".01"`，预算采用的止损逆向滑点假设，非实盘滑点上界；两项均为大于 0、小于 1 的十进制字符串 |

主网凭据从 `COINQUANT_BINANCE_KEY`、`COINQUANT_BINANCE_SECRET` 读取，Demo 从 `COINQUANT_BINANCE_DEMO_KEY`、`COINQUANT_BINANCE_DEMO_SECRET` 读取。两套凭据互不回退。

预算49%是在50%以下留一个百分点的模型余量，不是按回测收益择优，也不是连续账户回撤保证。需要更小的单次损失时显式降低它；收益会改变。两字段同时设为 null 时仍可读取、保护和退出已有敞口，但禁止新入场或追加。资金上限、20×设置和止损在强平前都不替代损失预算。

## 只读运行

```sh
python3.13 -m coinquant status --config config.json
python3.13 -m coinquant run --config config.json
python3.13 -m coinquant snapshot --config config.json --out /tmp/coinquant-snapshot.json
```

`status` 读取一次账户和合约条件；`run` 在期限内观察、恢复订单状态、判断策略并输出预览。`snapshot` 导出新鲜只读账户 JSON，输出文件必须不存在。只读命令仍会保存本地核对记录。

首次 `run` 从固定的 2019-12-01 UTC 起点重建完整四小时行情，逐页保存 checkpoint；有限会话内未完成时可再次人工运行继续。行情重建不会补造历史成交，冷启动不会追入已存在的信号。

## 有限交易试运行

以下命令中的尖括号占位符须换成专用账户 UID 和实际订单 ID。

```sh
cp config.demo.example.json demo.json
python3.13 -m coinquant run --config demo.json
python3.13 -m coinquant run --config demo.json --execute --trial demo --authorize-uid <DEMO_UID>
```

填写专用 Demo UID、固定状态目录和正值资金上限。执行需同时提供 `--execute`、与配置中显式 `environment` 一致的 `--trial` 和匹配账户的 `--authorize-uid`；入口不会强造策略入场。

主网试运行使用 [config.live-trial.example.json](config.live-trial.example.json)，还需 `--trial live --demo-evidence <JSON>`。Demo 验收后用只读命令采集证据：

```sh
python3.13 -m coinquant demo-evidence --config demo.json --out demo-evidence.json \
  --entry-order-id <ENTRY> --stop-algo-id <STOP> --take-algo-id <TAKE> \
  --reduction-order-id <REDUCTION> --offline-trigger-order-id <TRIGGER>
```

命令核对 Demo 专用 UID、持久状态中的原始委托、交易所原生订单与成交，以及 SQLite 和观察归档中的会话报告；要求保护回读、部分减仓、停机后触发与再次启动核对。必需订单须有当前源码版本 Demo 会话中的原身份与发送时间记录；恢复旧版仓位不会把旧版委托算作新版验收。证据只保存在本地，主网入口会重新做只读 Demo 核对，单独填写订单 ID 不会通过。Demo 证据资金上限须不低于主网试运行上限；采集和核对需要用户另行授权的 Demo 账户访问。

会话记录保留报价、请求与回读时间和实际成交；可回读成交价时计算保护触发滑点，缺项不按零成本补值。离线软件检查或只读快照不能证明真实委托、止损触发和重启执行已经通过验收。

执行先持久记录订单身份，成交后确认交易所托管的整仓止损和止盈。丢失回包时查询原身份；未解释的成交、资金或保护状态阻止新增风险。会话到期或中断后停止开仓，清理最多延续360秒，提前停止也按实际停止时间收紧总期限；确认的原生保护留在交易所。已证实终态部分减仓且新鲜成交归属证明残仓缩小时，可在总期限内使用新身份继续减仓；未知结果、零进展或预算耗尽不会无限重试。

## 状态、停机与恢复

固定 `state_dir` 保存 `intents.sqlite`、`latest.json`、观察归档和执行锁；账户锁还保存在 `~/.local/state/coinquant/account-locks`。同一账户只使用一台机器、一个客户端。重启继续原订单身份；保留原状态目录和观察归档，状态不匹配时只读核对，不删除数据库、不改 UID 或换空目录绕过。

当前模型状态协议为 v6，SQLite 状态协议为 1。字段布局、版本、校验值及现有恢复校验全部匹配的 checkpoint 可以原目录继续运行，不迁移数据库或重建 checkpoint。版本号同为 v6 也不足以证明兼容：缺少成交价或跟踪历史的旧布局仍在订单恢复和清理前拒绝，不补默认值、不清库重建。升级前停止会话、保留匹配旧版源码，并在进程停止后备份完整原状态目录。不兼容旧版的持仓、余单、未决意图或保护替换，须继续用匹配旧版和原目录核对、管理，或由账户所有者人工处理；平仓也不自动迁移未知布局。新版 `status` / `snapshot` 可只读观察当前仓位、订单及保护，仍会更新本地核对记录，不能证明完整历史成交归属。不得篡改版本或校验值、改 UID 或换空目录接管旧持仓。

启动时间可以不固定。每次运行都会重新核对实际持仓、原生保护与策略状态；报告中的 `next_required_review_at_ms` 标示下一根完整四小时 K 线的复核点，宏观数据或订单变化可能更早需要复核。`review_due_now` 表示已到复核点或需要人工处理，不是后台预约。SX60 默认在信号后七天退出。已记录成交价的多头若在该期限仍比成交价高出至少六个初始风险单位，则改为过去 14 天最低价的跟踪止损，且不低于成交价，原止盈不再作为退出。没有成交价记录时仍按七天退出。停止进程后只有交易所上已挂出的原生保护可能执行；跟踪止损、到期退出和宏观退出要等下一次人工运行，不等价于连续运行。

停止报告的 `native_protection_at_stop` 给出最后一次观察时间和保护腿：`flat` 为已观察平仓，`observed` 为当时两腿完整且止损在强平前，`incomplete` 为保护不足，`unverified` 为本次未能确认。它不保证之后保护不会触发或被撤。`pending_intents`、`unresolved_order_ids`、`protection_replacement_pending` 和 `execution_unresolved` 标示未决身份、未完替换及未解决执行；`pending_intents=0` 不证明残仓有保护。持仓且策略核对失败时另有 `strategy_review_required`。`manual_takeover_required=true` 时保留原目录，核对错误原因、交易所仓位、普通单与条件单，必要时由账户所有者处理敞口；它不要求盲目平仓，未知身份不得重发。明确配置或状态不支持会显示 `blocked`，订单或读回不明显示 `unknown`。运行时不要并发手工交易；停机后要手工重开仓，先核实并清理旧 closePosition 保护，否则旧腿可能平掉新手工仓。

持有仓位时，恢复对账依赖原 `state_dir/intents.sqlite` 中的订单身份、原生成交和历史覆盖记录，以及交易所可回读的订单、保护子单和从已核对边界至今连续的 BTCUSDT 成交。未覆盖的区间若超出最近约三个月的原生查询窗口，或子单终态、成交归属无法证实，程序会报告 `unknown` 并阻止新增风险；不会靠价格推断补齐。保留原状态目录，核对原环境与 UID、订单及子单身份、成交和当前仓位与保护状态，必要时人工处理敞口；不要换空目录、篡改覆盖记录或重发身份未明的订单。

历史 algo 查询缺失时，只以新鲜活动列表中逐字段匹配、尚未触发的 NEW 父单作为活动证据，不伪造终态。正常维护会在真实原生创建时间达到75天且仍小于90天时，沿现有先新后旧路径续期相同保护几何。停止跨过这个窗口后，超龄 NEW 仍可能保护仓位且可用于归属核对、退出；撤单或触发后若历史已不可回读，活动列表中的缺失不能证明终态，清理仍可能 `unknown`，需人工核实。超龄腿的破坏性替换不自动进行。

`snapshot` 的价格距离损失不含手续费、滑点或跳空，不能当亏损上界。SX60 和 DFII10 共用一个单向持仓；每次原生入场按新鲜已核实权益、双边手续费和指定逆向滑点估算整轮到止损损失，DFII10另有3%模型预算。原会话追加同时受冻结入场USDT预算和当前标记权益到止损预算限制，计入浮盈回吐，不因盈利放大冻结预算，也不借未实现利润付保证金。整轮预算累计所有已归属成交的实际USDT费用和已实现盈亏，部分减仓不会退还已付费用或抹掉已实现亏损；未来成交按当前费率估计，旧费用不从现金再次扣除。实际费用或盈亏证据缺失、费用资产不是USDT、预算未知或成交归属不完整时禁止追加，保护与退出继续按原有归属条件处理；超过新预算的已有仓不自动缩小。跳空、真实滑点、多笔累计亏损和停机期间浮盈回吐仍可能突破预算或连续DD目标。历史模拟不能证明实盘能力或未来收益。本项目独立运行，不要求与其他项目同步启动或合并账本。

报告将20×设置、`wallet_notional_ratio`（名义/钱包）和 `account_notional_leverage`（名义/同次标记权益）分别列出；非正分母返回 null，`equity_status` 明示非正权益，不把钱包当全账户权益。出现 `blocked` 或 `unknown` 时根据报告核对配置、原状态和交易所订单；无法确认的敞口需人工处理。若缺少 `America/New_York` 时区数据，安装系统时区数据库，或运行 `python3.13 -m pip install tzdata` 后再启动。

开发约定见 [AGENTS.md](AGENTS.md)。历史资料见 [archive/pre-slim-20261008](https://github.com/geniusgrok/coinquant/tree/archive/pre-slim-20261008)。

项目供仓库所有者个人使用，公开可见不授予第三方使用许可，详见 [LICENSE](LICENSE)。

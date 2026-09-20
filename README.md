# Pancakequant

个人使用、人工触发的 BTC 永续量化系统。一次运行先对账，再读取完整行情、计算目标、在明确授权下执行、回读保护和实际仓位，最后退出；不需要守护进程或下一次 AI 对话维持已挂出的交易所保护。

**当前改造仍在研究分支，尚未满足经济验收和真实接口验收，不是已验证可盈利的实盘发布。** `PROJECT_STATE.md` 记录当前证据与恢复入口。不得把离线测试或程序生成的订单计划当作真实成交。

## 当前实现

只有一条生产路径：`python -m pancakequant` → `cli` → `execution` → `Bybit`。`main.py` 调用同一 CLI，不保留旧机器人模式。标准库实现，没有生产第三方依赖。使用 Python 3.13。

生产适配目标是 **Bybit BTCUSD 反向永续、BTC 结算**，不是 BTCUSDT 线性合约。数量单位是美元合约，BTC 等值为数量 / 价格；反向合约盈亏为 `有符号数量 × (1 / 开仓价 - 1 / 当前价)`。**即使衍生品空仓，BTC 抵押资产也仍有人民币/美元价格风险。**

核心模型统一计算通道趋势、波动风险、仓位、保证金和止盈止损。只用已完成的四小时 K 线；回测复用同一模型。20 倍是交易所杠杆设置，不是要求账户开满 20 倍。程序核验单向、逐仓、20 倍，发现真实账户不匹配时阻止执行，不擅自切换模式。

已实现并有离线检查的路径：默认只读、账户与额度绑定、跨进程互斥、交易意图持久化、稳定客户端订单 ID、未知结果先查询、部分成交后回读并撤销余单、只减仓、全仓 TP/SL 原生设置/修改、停机保留保护、同根 K 线仍检查账户并修复保护。真实 API 兼容性仍待验证。

当前已实现两种增加风险的执行形态：需要立即处理的订单使用有界 IOC 限价；账户为空仓且模型给出未来触发价时，可留下 Bybit 原生 conditional FOK 入场单，并在母单上同时提交 Full/Market、MarkPrice 触发的 TP/SL。FOK 被当作“触发后要么整单成交、要么取消”的安全契约；如果真实回读出现部分 FOK 成交，系统记录安全故障并禁止继续增加风险。该路径已有离线竞态/恢复测试，但尚未用授权的 Bybit 私有 testnet 账户完成真实接口验收。普通条件入场可原生 amendment；保证金接口已封装，但模型驱动的端到端保证金调整仍未完成，因此不宣称该项已交付。

## 使用

在仓库根目录执行：

```sh
python -m pancakequant --help
cp config.example.json config.json
python -m pancakequant status --config config.json
python -m pancakequant run --config config.json
```

默认配置是测试网、空账户 UID、零交易额度。因此在没有正确配置密钥/账户时，命令返回 `blocked` 和退出码 2；不会自动回退到实盘。示例中的 `cp` 用于 POSIX shell，Windows 可直接复制该文件。\n\n`api_host` 默认留空：测试网使用 `api-testnet.bybit.com`，实盘使用 `api.bybit.com`。如果账户所属地区要求 Bybit 的地区域名，可显式填写官方域名；程序只接受内置官方 allowlist，并要求与 `testnet/live` 匹配，防止 API 密钥被发送到任意主机。程序不根据 IP 或地理位置自动猜测区域。

密钥仅通过环境变量读取：测试网为 `PANCAKEQUANT_TESTNET_KEY` / `PANCAKEQUANT_TESTNET_SECRET`；真实账户为 `PANCAKEQUANT_LIVE_KEY` / `PANCAKEQUANT_LIVE_SECRET`。配置中不保存密钥，不需要提现权限。账户配置只在合法可用、明确授权的账户上使用；本次改造未改变任何真实账户设置，也未进行真实交易。

将 `account_uid` 与交易所返回的 UID 对齐，设置一次性的最大授权名义敞口 `max_position_usd`。模型自动在风险、保证金、交易规格、流动性及授权上限内计算每次数量，不需要逐次手填仓位。每个账户/环境使用独立、持久化的 `state_dir`，不要同时在多台机器执行；本地锁不是分布式锁。

未来明确授权交易后，才使用：

```sh
python -m pancakequant run --config config.json --execute
```

`--execute` 与明确的环境、账户 UID、正数授权额度同时满足才允许写接口。有 API 密钥本身不会启用交易。当前版本未完成真实接口验收，不应据此直接投入真实资金。

标准输出是 JSON，标准错误是摘要；最新完整报告保存在状态目录的 `latest.json`。状态区分 `read_only`、`no_action`、`executed`、`partial`、`unknown` 和 `blocked`。后面三种状态返回非零退出码。`executed` 只代表已回读确认的操作，不代表收益保证。

## 退出后的保护与异常

增加风险的订单同时提交 Full 模式、MarkPrice 触发、Market 类型的 TP 和 SL。Bybit 官方文档说明全仓保护在母单部分或全部成交后生成；本实现还要求回读真实仓位和两侧条件单，不能仅凭仓位中的价格字段判断保护存在。修改使用原生双侧设置，不先撤旧保护。

程序正常退出和释放本地锁不撤销有效保护。只有经回读验证、空仓状态下的 conditional FOK 母单允许跨进程保留；普通 IOC/GTC 残余必须撤销并确认。FOK 触发后没有合法未成交余量可在止损后重新开仓；真实接口若违反这一契约则进入安全故障状态。保护无法确认时禁止增加风险，必要时尝试已授权的只减仓。网络断开或结果未知时不能保证成功平仓，报告会保留未知状态和恢复意图，不会把超时当作失败重发。

官方接口说明：
- https://bybit-exchange.github.io/docs/v5/order/create-order
- https://bybit-exchange.github.io/docs/v5/position/trading-stop
- https://www.bybit.com/en/help-center/article/How-to-Set-Up-and-Modify-TP-SL-Perpetual-Futures-Contracts

## 研究与回测

固定目标：人民币 10,000 元，2020-01-01 UTC 起，CAGR **大于 200%**、完整账户 MDD **小于 20%**。`research/spec.json` 固定窗口上限、成本假设和与行情无关的稀疏触发生成规则。当前上限为 2026-09-20 00:00 UTC，**尚未取得覆盖整个窗口的真实数据**，不能用这个时间声明数据已经齐备。

人民币统一采用 2019-12-31 人民银行美元中间价 6.9762 的固定换算口径，同时输出原始 BTC 权益和美元权益；不是对未来实际汇率的预测。手续费、历史保证金规则和资金费率必须由有来源的数据记录提供。价差、滑点、初始转换成本和流动性代理是提前披露的建模假设，不是已核验的每笔真实成交成本。

```sh
python -m pancakequant backtest --config config.json --manifest data/manifest.json --output results/base
python -m pancakequant backtest --config config.json --manifest data/manifest.json --output results/absence --stress-absence
```

缺失文件、时间缺口、散列不符、不同合约、缺失资金费率或窗口不符都会阻止回测，不自动生成替代行情。输出目录必须为空，避免覆盖原始结果。格式见 `research/DATA.md`。

回放只在预先生成的人工触发点重新决策；两次触发之间仅处理持有资产的估值、资金费率、保证金变化和原生退出。完整账户权益包含未实现盈亏与 BTC 抵押资产波动。分钟内同时触及多个价格时按不利顺序处理，并输出保守权益极值包络；这不是已知的逐笔市场路径。

当前回放输出是研究证据，`qualification` 保持 `NOT_QUALIFIED`。完整真实历史、隔离验证和真实接口检查尚未完成。不能把短小合成测试、旧恢复包或不同提交上的指标冒充当前代码的正式 CAGR/MDD。

## 检查与恢复

```sh
python -m unittest discover -s tests -v
```

只有一个短工作流，无覆盖率门槛、系统矩阵、定时交易和全历史优化。按改动风险运行定向检查，不要求每次重跑全部历史。

改造工作保存在 `research/on-demand-btc-20260920`。`.transfer` 是并行工作留下的历史恢复原件，不是另一条生产路径；不得将其盲目恢复覆盖当前代码。Git 保存旧实现历史，LICENSE 与原始证据保留。当前分支未经经济和安全验收不得覆盖 `main`。

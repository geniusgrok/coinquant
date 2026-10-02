# Spotquant

本轮完成 BTC alpha/beta 全机制比较，开发默认采用 **SMA30/40/50 共识仓位 + ATR自适应止损**。
CNY10000、不追加资金，2020-01-01 至 2026-09-20 UTC（末日不含），795次有限历史会话的
成本后年化为 **55.22%**、连续OHLC代理最大回撤为 **36.41%**；原共识为51.85%/41.21%。
年化提高3.37个百分点，连续代理回撤降低4.80个百分点。手续费、普通成交及止损滑点、
空窗四种场景均达到事先登记的配对门槛。其他现货机制保留完整拒绝结果。

原100%年化/不超过30%连续回撤目标仍为 **NOT_MET**。最差CNY单日收益由−14.48%
变为−15.80%，最长水下期仍为713天；改进没有覆盖每个风险维度。历史不是干净样本外，
原生交易案例和实际账户日均为0，**NOT_QUALIFIED**，主网写入继续禁止。

共享Model/session/Lifecycle路径另跑基础、费用、滑点、空窗和文件校准基础五个完整账户，
分别核对六组证据。训练比例仅用于离线诊断，默认仍为1。Model v5恢复前拒绝旧规则和
不兼容状态；保留原目录，不自动迁移或清空。现货只做多/现金，无借币、空头或杠杆。
详见 [本轮结果](evidence/alpha-beta-next-20261002/review/FINAL-RESULT.md)、
[逐文件证据](evidence/alpha-beta-next-20261002/MANIFEST.json)和
[运行时与状态说明](research/adoption-GUIDE.md)。

下方早期P4、共识及联合配置数字属于各自冻结历史来源；2026-10-01联合账户使用旧共识，
不代表新ATR止损默认与合约的联合收益。[历史完整交付](research/complete-delivery-GUIDE.md)
保留原账户。[本轮复现](evidence/alpha-beta-next-20261002/review/REPRODUCE-registered.md)
绑定原研究生产者、独立评估器和共享运行时来源，后续main不冒充已测量版本。

第三轮接通 P4 的 `session.run → Lifecycle → Binance Demo`，离线回放也走
同一会话。新增持久订单分仓归属、跨日恢复、原生只读导出和双账户并行采集。
使用命令和验收边界见 [第三轮结果](evidence/third-round-20261001/RESULT.md)。
该轮旧P4经济资格为NOT_MET，原生执行为NOT_QUALIFIED。

第二轮已完成同口径 [现金／买持／分批投入基线](evidence/baselines-20261001/RESULT.md)，
P4 的历史收益与回撤均优于两种持币基线。新增
[离线订单闭环、手动前向观察与两账户汇总](evidence/second-round-20261001/RESULT.md)。
日常只读观察：`python -m research.operations observe --refresh`。
执行资格与原收益目标仍未通过。

2026-10-01 首轮改造：已实现并完成 P5 简化规则对照，四个候选均被登记
门槛淘汰，P4 保留。运行 `python -m research.rebuild --simplify`；原件和
结论见 [P5](evidence/simplify-20261001/RESULT.md)。

本公开仓库仅用于托管 geniusgrok 的个人量化研究代码和实验记录，项目仅供仓库所有者本人使用。公开可见不代表开放授权、邀请贡献或实盘交易。未经权利人事先书面许可，不得擅自使用、复制、抄袭、修改、改编、传播其原创代码与研究内容，也不得冒名署名。详见 [LICENSE](LICENSE)。

**不得将本仓库作为实盘交易工具使用。** 策略、回测和收益数字仅为研究记录，不是投资建议、收益保证或可执行性证明。历史模拟不能证明真实撮合、余额、网络故障和保护单失效等风险已得到控制；任何擅自使用所产生的行为与损失由使用者自行承担。

研究对象是个人使用的 Binance **BTCUSDT 现货**。只做多或持有 USDT，不借币、不做空、不开合约、不用杠杆。手动启动一个有限会话，会话内持续读取真实行情与账户状态、重复判断，超时或 Ctrl-C 后退出；没有后台守护进程。

**主网写入继续禁止。** 所有者可显式启动有 UID 和资金上限的 Demo 验证。 `run --execute` 在读取配置、凭据和网络之前拒绝。当前共识+ATR止损默认没有达到两项目标，经济资格是 `NOT_MET`；原生交易资格是 `NOT_QUALIFIED`。

## 所有者本地研究

Python 3.13；项目运行仅使用标准库。

```sh
git clone https://github.com/geniusgrok/spotquant.git
cd spotquant
cp config.example.json config.json
python3 -m spotquant status --config config.json
python3 -m spotquant run --config config.json
```

仅供仓库所有者在授权账户上进行本地只读研究。在配置中填写所有者的 Binance `account_uid` 和固定 `state_dir`。实盘凭据只从 `SPOTQUANT_BINANCE_KEY`、`SPOTQUANT_BINANCE_SECRET` 环境变量读取，Demo 凭据只从 `SPOTQUANT_BINANCE_DEMO_KEY`、`SPOTQUANT_BINANCE_DEMO_SECRET` 读取，都不写入配置或仓库。`status` 单次观察；`run` 默认观察 300 秒，每 5 秒重新核对。配置项：

| 配置 | 含义 |
|---|---|
| `account_uid` | 必须与交易所核验的账户一致 |
| `state_dir` | 此账户持续使用的恢复目录 |
| `session_seconds` | 本次运行 1～86400 秒，默认 300 |
| `poll_seconds` | 轮询 1～60 秒，默认 5，不得超过会话时长 |
| `environment` | `live`（默认，`api.binance.com`）或 `demo`（`demo-api.binance.com`）。状态范围是 `binance:BTCUSDT:spot:{live\|demo}:{uid}` |
| `capital_limit_usdt` | 可选，十进制字符串。上限覆盖全账户持仓名义：从上限扣除保留持仓估值，再以当前真实usdt_free与剩余额度裁剪BUY。有SELL时本次BUY全部延后，不预支预计退出所得；共识提升只作用于真实新BUY。它不是亏损上限 |

Demo 与实盘共用一个适配器，默认只读。`run --execute` 在两种环境都被阻止。
所有者 Demo 使用单独的 [配置模板](config.demo.example.json) 和入口：

```sh
python -m spotquant demo-check --config demo.json
python -m spotquant demo-check --config demo.json --execute --authorize-uid <DEMO_UID>
python -m spotquant status --config demo.json
```

填写专用 Demo UID、固定状态目录和正值资金上限；凭据沿用上述 Demo 变量。
同一账户只允许一个客户端。冷启动仍等待新鲜穿越，验证入口不会强造入场。
停止时保留已确认的原生止损；进程关闭后不计算移动止损或模型退出。
现场成交、停机保护触发与重启都要以真实回读验收，离线回放不能代替。

首次运行从固定起点重建已完成的 UTC 日线，等待新鲜穿越；截断行情为未知。
执行入口在发送前持久记录订单身份及分仓权重；部分成交、多订单和等量分仓按
原生订单编号分配，不靠余额猜测。丢失回包后只查询原身份，查询不到不会重发。
跨日重启继续已准备的减仓，未发送的过期入场不会补买。未知市场余单、外部
委托/成交、转账或无法解释的余额变化阻止新增风险。止损更新先保存新意图，
确认旧单撤销后再挂新单；现货锁币使这段保护空窗无法假称原子操作。
不足数量步长的残币保留在账户和风险导出中。未通过数量/名义过滤的保护为
阻断，不记成已覆盖。没有持久分仓归属的旧只读跟随仍拒绝多订单和等量歧义。

固定状态目录的锁覆盖整个会话。同一账户只允许一台机器一个客户端；新空
目录不证明空账户，旧单 SMA 持仓不能直接接管。状态与成交不匹配时先只读
核对，不能删除 SQLite 或换空目录绕过。失败报告清除上一轮模型和持仓视图。
观察记录只保留最近 1000 行，订单意图持续保留。

`run --execute` 在访问凭据和网络之前拒绝。不要删除这个阻止来试单。

## 已实现的研究路径

`CLI → session.run/cycle → 共识模型/完成日线ATR止损 → 默认预览或显式 Demo Lifecycle → Binance → latest.json`。

- 当前默认保留SMA30/40/50、两根完成收盘、新鲜穿越、252日高点半价门、61%偏离、崩盘反转/修复交接和4%普通收盘退出。只有真实新BUY且至少两个实际看多分仓enter/hold时，才把该买单提升到至少90%可用现金；已有持仓不补足或重平衡。保护决策用十四个已完成真实波幅的ATR14，ATR14为最近十四个完成日线真实波幅的算术平均，距离为`clip(4×ATR14/完成收盘,10%,30%)`，以已归属成交后高点和确认原生保护下限为界，不放宽已经生效的止损；保护穿过当前标记价时走普通减仓，SELL优先于新BUY。持久模型与只读跟随的历史追赶仍保存28%规则，当前会话只调整决策副本；不会在停机期间修改原生保护。入场前高点不冒充持仓高点，部分卖出的剩余仓使用同一保护助手。完整规则和来源证明见本轮运行时说明；下方`research.rebuild`保留另一套历史日线账本。
- 预览买单是市价、按报价资产数量；预览卖单也是市价；预览保护是带 `stopPrice` 的 `STOP_LOSS`。默认预览不是委托；显式 Demo 执行才持久记录并提交。
- 冷启动和前向账本用同一种起点：已经看多的状态要等一次新鲜穿越，不是只跳过第一轮。同一天平掉的分仓不会在同一根已完成日线上再次入场。执行过的订单按持久权重归到分仓；没有归属的旧跟随遇到等量歧义仍为未知。观察失败不单独推进模型。名义金额不到 5 USDT 的分仓仍算持仓，三份加起来达到门槛时合成一张卖单。进程停着的时候不会继续改止损。

## 历史等份日线经济测量（不衡量当前默认共识仓位）

```sh
python3 -m unittest discover -s tests -v
python3 -m research.rebuild --suite --out /tmp/sleeves   # 完整证据集，写到仓库内需要干净的提交
python3 -m research.rebuild P4                            # 单个试验
python3 -m research.forward                               # 追加前向账本
```

测量窗口、成本、人民币估值、选参记录和 P4 的事先声明见 `research/PROTOCOL.md`。目标仍是成本后年化不低于 100%、连续最大回撤不超过 30%，没有降低，窗口没有移动。

历史日线试验 P4 在 P3 的规则上把单个 SMA(40) 换成 SMA 30、40、50 三个分仓；偏离、崩盘反转的距离取 P3 上“成交完全不变”的平台中心（1.61、跌 11% 涨 7%、修复交接 11%）；4% 收盘退出在 3.5%、4.0%、4.5% 三档都不使回撤变高，所以保留；只测了一次的波动率缩放没有同时满足回撤降一个点和年化至多降三个点，不采用。参数仍在整个窗口上选定，没有样本外结果。

| 场景 | 期末人民币 | 成本后 CAGR | 连续 MDD |
|---|---|---|---|
| P4 基准 `python3 -m research.rebuild P4` | 490,442 | 78.49% | 31.40% |
| 手续费 +50% | 470,645 | 77.40% | 31.81% |
| 出场滑点与止损滑点 ×2 | 480,484 | 77.95% | 31.61% |
| 随机跳过 20% 日开盘 | 429,610 | 75.01% | 32.63% |
| 21 天空窗 | 490,442 | 78.49% | 31.40% |
| P3 单个 SMA(40)，样本内上限 | 1,113,885 | 101.67% | 29.15% |
| ETHUSDT 冻结规则，三分仓 | 367,630 | 71.00% | 42.75% |
| ETHUSDT 冻结规则，单个 SMA(40) | 451,582 | 76.31% | 43.42% |

P4 两项目标都没有达到，经济资格是 `NOT_MET`。它比 P3 少约 23 个点年化，连续回撤多约 2.3 个点，换来的是对单个窗口的依赖更小，不是两项同时变好。P3 的证据文件原样保留。同样的常数下，单个 SMA 35、45、30、50 的年化只有 59.08%、94.83%、58.93%、70.37%（`evidence/sleeves-20260929/neighbors.json`），所以 101.67% 是样本内的上限。同一规则在 ETHUSDT 上仍是正收益，但回撤约 43%。`evidence/forward/forward.json` 是 2026-09-20 到 09-27 的回填，不是事先冻结后的样本。新的观察从 2026-09-29 起，写在 `evidence/forward/forward-20260929.json`。同一规则在 ETHUSDT 上仍是正收益，但回撤约 43%，不能据此说它不是比特币上的一次巧合。窗口结束时 P4 仍持有分仓 40 与 50。详见 [均线分仓重建](evidence/sleeves-20260929/RESULT.md) 和 [P3 重建结果](evidence/rebuild-20260928/RESULT.md)。原生资格是 `NOT_QUALIFIED`，历史收益不会因此放开主网下单。

行情 zip 不入库。日线放在测量器 `--market` 指向的目录（默认 `/tmp/spotquant-market/klines`）。ETHUSDT 检查放在 `--eth-market`（默认 `/tmp/spotquant-market/klines-eth`），前向账本额外读取 `/tmp/spotquant-market/forward`。DEXCHUS 原件在 `evidence/rebuild-20260928/inputs/`，加载时核对 SHA-256。

当前恢复入口：`AGENTS.md`、`PROJECT_STATE.md`、`HANDOFF_PROMPT.md`。

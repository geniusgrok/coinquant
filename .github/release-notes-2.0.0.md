# Coinquant 2.0.0 — 按需交易与资金保护

**个人使用的 Binance BTCUSDT USDT 本位永续交易程序：统一多头模型、按需有限会话、交易所原生保护和可核对的订单恢复。**

本次更新补充 `2.0.0` 固定源码的实际经济重测。Tag 仍指向 [`162ee7138952925ffafbc9b68be7c754c0c0a6c3`](https://github.com/geniusgrok/coinquant/tree/162ee7138952925ffafbc9b68be7c754c0c0a6c3)，包含已合并的 [PR #77](https://github.com/geniusgrok/coinquant/pull/77) 执行与恢复修复。重测与发布说明更新不改变这一代码身份。

**本轮结果状态：`两臂均完成 795/795，独立财务、完整路径回撤重算与状态审计全部通过`。当前版本成本后 CAGR 为 `27.6264%`，原模拟路径最大回撤代理为 `15.1634%`，日收盘最大回撤为 `12.1154%`。** 三项指标的来源和口径见下文。

## 一、特点与实际优势

| 特点 | 实现与作用 |
|---|---|
| 聚焦一套运行路径 | 一个 BTCUSDT 永续市场、一个单向持仓和 SX60 + DFII10 统一模型，减少多交易所、多策略切换与历史兼容分支。当前模型只做多，下跌脉冲不开空。 |
| 部署依赖少 | 当前运行代码使用 Python 3.13 标准库；部分系统需补纽约时区数据。无需 TA-Lib 或第三方数据库服务。 |
| 按需有限会话 | 用户手动启动，默认运行 300 秒、每 5 秒核对一次。模型进度与未决状态持久保存，可在下一次人工会话继续。 |
| 默认只读、执行入口明确 | 普通 `status`、`run`、`snapshot` 不发送交易写请求；执行需要显式环境、账户 UID 和授权参数。只读命令仍保存本地核对记录。 |
| 原生保护与恢复 | 成交后确认交易所托管的整仓止损和止盈。未知回包先按原订单身份查询；SQLite 保留成交归属、未决操作和保护替换阶段，支持中断后的核对与恢复。 |
| 资金约束可检查 | 用新鲜钱包、标记权益、费用、盘口和合约规则核算止损预算与保证金。报告分别展示原生保护、持仓风险、模型进度和未解决执行。 |

这些优势来自实现的聚焦、有限依赖和恢复机制。收益与风险表现按本次固定源码、指定输入和会话日程的测量结果单独报告。[运行说明](https://github.com/geniusgrok/coinquant/blob/162ee7138952925ffafbc9b68be7c754c0c0a6c3/README.md)

## 二、策略与定仓

### SX60：四小时上涨脉冲与盈利趋势延长

- 只使用已完成的 UTC 四小时 K 线。相对前收盘的上涨金额严格超过此前 `ATR(14) × 3` 时，形成多头机会。
- 初始止损为前收盘与信号收盘的中点；初始止盈采用 `信号收盘 × (信号收盘 / 初始止损)^20` 的幂次公式。
- 初始期限为信号起算 42 根四小时 K 线，即七天。到期时，若尚未成立适用退出条件、已有真实成交价，且已完成 K 线收盘至少高出成交价六个入场至初始止损风险单位，则延长持有。
- 延长后按此前 84 根四小时 K 线、即 14 日窗口的最低价跟踪止损，排除当前 K 线；止损不低于真实成交价，也不放松已接受的止损。原止盈会被替换。

### DFII10：真实收益率条件下的补充机会

- 使用 ALFRED 的美国十年期通胀保值国债收益率 `DFII10`。最新可得值相对此前第 20 个观察值下降至少 0.25 个百分点，即 25 bp 时，满足宏观条件。
- 历史 vintage 按纽约日期结束再延迟 48 小时判定可得性；超过七个自然日的旧观察失效。
- 无优先 SX60 入场机会时可形成宏观多头；已有且宏观条件仍有效的归属持仓优先继续管理。两种机会共用同一仓位。
- 初始止损取过去十个完整 UTC 日最低价；没有 SX60 的固定七日期限，宏观条件失效进入退出判断。

SX60 / DFII10 的定仓乘数分别为 **7.5 / 3.6**，结合最近 20 个日收益的均方根与当前 taker 费率计算目标，再受资金、损失预算、保证金、盘口和合约最小数量/步长约束。账户要求单资产、单向、BTCUSDT 逐仓 20×并关闭自动追加保证金；20×是交易所设置，实际名义敞口比例另行报告。

策略到期、跟踪止损和宏观退出在实际运行、补齐模型后处理。停机期间只有最后已接受的交易所原生保护可能执行；本地补读历史不会补造历史成交，新保护自交易所确认接受后生效。冷启动从固定的 `2019-12-01T00:00Z` 重建模型，并避免追入启动前已经存在的信号。

依据：[机会与延长规则](https://github.com/geniusgrok/coinquant/blob/162ee7138952925ffafbc9b68be7c754c0c0a6c3/coinquant/opportunities.py)、[统一模型、优先级与定仓](https://github.com/geniusgrok/coinquant/blob/162ee7138952925ffafbc9b68be7c754c0c0a6c3/coinquant/campaign.py)、[DFII10 可得性](https://github.com/geniusgrok/coinquant/blob/162ee7138952925ffafbc9b68be7c754c0c0a6c3/coinquant/dfii10.py)。

## 三、风险约束与本版修复

相较本次校准使用的 PR #74 源码，当前默认 `max_stop_loss_fraction` 从 **`.49` 调整为 `.10`**，且执行模型有 10% 硬上限；DFII10 另受 3% 模型止损预算约束。默认逆向止损滑点假设仍为 `.01`。

**当前逐仓保证金最多占可核实资金的 25%。** 资金基数取钱包、同次标记权益与配置资金上限中的较小值。新增敞口、持仓和恢复计划都要核对额度与强平缓冲；无法在预算内维持风险条件时，沿已有的仅减仓流程处理。

整轮风险核算计入实际手续费、已实现盈亏及已核实负向资金费；持久损失额度只收紧，部分减仓不会抹掉已付成本或补回冻结预算。PR #77 还修复了保护换腿中断恢复、历史保护覆盖、父子条件单归属、原生部分退出、发单前新鲜度及清理时外部重新开仓等边界。

10%、3% 和 25% 是不同层面的模型/执行约束。跳空、实际滑点、累计亏损、资金费和停机期间浮盈回吐仍会影响实际损失；这些比例不能换算成连续账户最大回撤保证。`capital_limit_usdt` 也不是最大可能亏损。

依据：[默认配置](https://github.com/geniusgrok/coinquant/blob/162ee7138952925ffafbc9b68be7c754c0c0a6c3/coinquant/config.py)、[风险和保证金上限](https://github.com/geniusgrok/coinquant/blob/162ee7138952925ffafbc9b68be7c754c0c0a6c3/coinquant/native_preview.py)、[保证金写入约束](https://github.com/geniusgrok/coinquant/blob/162ee7138952925ffafbc9b68be7c754c0c0a6c3/coinquant/binance_safety.py)、[PR #77](https://github.com/geniusgrok/coinquant/pull/77)。

## 四、本轮回测与历史校准

### 固定经济条件

| 项目 | 本轮登记 |
|---|---|
| 原窗口 | 2020-01-01 00:00 至 2026-09-20 00:00 UTC，终点排除，共 2454 天 |
| 本金与年化 | 初始 10,000 CNY，无外部追加资金；CAGR 使用 365.2425 天/年 |
| 会话日程 | 原 795 次人工启动会话，每次 300 秒、轮询 5 秒；读/写延迟 200 / 1000 毫秒 |
| 成本与资金费 | 每笔成交手续费 0.075%；计原官方资金费；进出换汇各扣 0.1%，使用观察日前已知汇率，USD/USDT 沿旧口径按平价估值 |
| 输入与模型 | 恢复并核对原行情、ALFRED vintage、warmup、合约规则及解析语义；各臂调用各自真实生产实现和默认 Config |
| 配对身份 | previous 为 `79a334b2d776be2dbe8756f3a616697f9403982e`；current 为 tag `2.0.0` 的 `162ee7138952925ffafbc9b68be7c754c0c0a6c3` |

两个版本在同一新 producer、恢复输入、成本和日程下运行各自连续钱包。风险参数保持各版本默认值，因此 `.49 → .10` 和当前 25% 保证金上限属于被测差异。重测没有将当前版本的风险调回旧值，也没有按收益阈值选择结果。

研究执行使用与恢复记录一致的 Python 3.12.14；项目面向用户的安装与软件检查说明仍为 Python 3.13。研究工具位于独立证据目录，主分支仍只保留运行实现、必要测试和使用说明。

### 完整配对结果

| 指标 | previous：PR #74 同源码重测 | current：2.0.0 |
|---|---:|---:|
| 实际完成会话 | 795 / 795 | 795 / 795 |
| 成本后人民币 CAGR | 167.9487% | 27.6264% |
| 全期日权益收益率 | 75,062.9002% | 414.9850% |
| 原模拟路径 MDD 代理 | 46.2720% | 15.1634% |
| 日收盘 MDD | 41.1043% | 12.1154% |
| 期末权益 / CNY | 7,516,290.02 | 51,498.50 |
| 净手续费 / USDT | 38,661.63 | 257.23 |
| 净支付资金费 / USDT | 75,628.89 | 282.66 |
| 成交记录条数 | 3079 | 142 |

当前相对本轮 previous 的 CAGR 变化为 **-140.3223个百分点**，路径 MDD 代理变化为 **-31.1085个百分点**，日收盘 MDD 变化为 **-28.9889个百分点**。这里只报告测得差异；详细的配置、成交、费用和状态差异见公开证据。

本轮比较包含两个完整版本的差异。除了默认止损预算从 `.49` 调整为 `.10`、逐仓保证金上限和持仓/恢复逻辑，2.0.0 还新增了发单前盘口一致性复核：关键价格、限价内深度、容量或报价所属模型时段不符合定仓计划时，该次入场不发送，后续轮询需重新取得有效观察。这些变化共同改变实际执行路径；本轮年化与回撤差值不能单独归因于某一个风险参数。见[最终盘口复核](https://github.com/geniusgrok/coinquant/blob/162ee7138952925ffafbc9b68be7c754c0c0a6c3/coinquant/native_preview.py#L389)。

财务与路径审计：**两臂全部通过；previous/current 分别核对 3,079/142 条成交、4,275/926 条收入，并对 2,544,832/1,763,276 个保留权益观测逐点重算路径回撤。见[独立审计](https://github.com/geniusgrok/coinquant/blob/d874ed0bef69d1b1ab8c32cf87eb2dc6791be486/evidence/2.0.0-remeasure-20261009/full-audit-summary.json)和[两臂状态审计](https://github.com/geniusgrok/coinquant/blob/d874ed0bef69d1b1ab8c32cf87eb2dc6791be486/evidence/2.0.0-remeasure-20261009/README.md#审计与完整性)**。期末持仓、保护、cleanup、pending、未解决执行及报告错误记录：**两臂期末均为 0 BTC、0 个活动保护，795 次会话均 cleanup verified、pending=0、execution_unresolved=false；130/81 个持仓会话终点的整仓原生保护和止损强平缓冲核对通过。previous/current 分别有 675/722 份报告保留错误、共 735/1,065 条保留记录；详见[报告错误统计](https://github.com/geniusgrok/coinquant/blob/d874ed0bef69d1b1ab8c32cf87eb2dc6791be486/evidence/2.0.0-remeasure-20261009/report-errors.json)**。资金费为正表示净支出、为负表示净收入。两臂保险扣费均为 **0 USDT**，已逐账本核对。

每份会话报告只保留最后 10 条错误，因此这些数值不是所有失败尝试或交易所拒单的总次数。当前版有 42 份报告保留发单前盘口一致性检查错误，共 296 条；部分会话后续仍成功成交。保留错误还包括期限耗尽、保护价格限制和观察不可得，cleanup 通过不能写成“没有错误”。

本地状态审计与模拟期末账本审计分别报告：当前本地 income coverage 截至 2026-09-18 00:05:02.4 UTC，`wallet_closure="collected"`、`closure=null`；全部 142 条模拟成交与 926 条收入恰好均已归档，未归档列表为空，但不据此把本地 coverage 延长至 9 月 20 日。完整模拟期末钱包与权益由独立财务审计核对。

分年收益与日收盘回撤如下。2020 从初始 10,000 CNY 计起，后续各年包含上年末权益；2026 截至 9 月 19 日日终，为 262 日部分年度收益。

| 年度 | previous 收益率 | 2.0.0 收益率 | previous 日收盘 MDD | 2.0.0 日收盘 MDD |
|---|---:|---:|---:|---:|
| 2020 | 5,545.0320% | 28.7629% | 24.2920% | 10.9669% |
| 2021 | 39.2062% | 23.9873% | 41.1043% | 5.4528% |
| 2022 | -18.0243% | 8.8300% | 26.9575% | 6.4711% |
| 2023 | 427.9402% | 126.4982% | 9.4226% | 7.8805% |
| 2024 | 71.0027% | 35.0296% | 18.9793% | 5.6877% |
| 2025 | 13.2998% | -4.0669% | 4.4199% | 4.6213% |
| 2026（262 日） | 14.0715% | 1.0220% | 8.3006% | 7.9780% |

日权益与日收盘回撤图使用 2454 个日终估值与初始本金；上图采用对数权益轴，下图为日收盘回撤，未绘制完整路径代理。[PNG](https://raw.githubusercontent.com/geniusgrok/coinquant/d874ed0bef69d1b1ab8c32cf87eb2dc6791be486/evidence/2.0.0-remeasure-20261009/equity-drawdown.png) / [SVG](https://raw.githubusercontent.com/geniusgrok/coinquant/d874ed0bef69d1b1ab8c32cf87eb2dc6791be486/evidence/2.0.0-remeasure-20261009/equity-drawdown.svg)。

![两版日权益与日收盘回撤](https://raw.githubusercontent.com/geniusgrok/coinquant/d874ed0bef69d1b1ab8c32cf87eb2dc6791be486/evidence/2.0.0-remeasure-20261009/equity-drawdown.png)

### 历史基线校准

此前 PR #72 / #74 的完整历史记录已经出现超过 150% 的年化结果。本次只保留 PR #74 最终测量作为校准锚点，早期沿革见 [PR #72](https://github.com/geniusgrok/coinquant/pull/72) 和 [PR #74](https://github.com/geniusgrok/coinquant/pull/74)。

| 同一 previous SHA 的指标 | PR #74 旧记录 | 本轮重测 | 本轮减旧记录 |
|---|---:|---:|---:|
| CAGR | 167.94868978615018% | 167.948689786150145…% | −3.4573137588980826 × 10⁻¹⁴个百分点 |
| 路径 MDD 代理 | 46.27197712514759% | 46.271977125147589…% | −5.3191679382 × 10⁻¹⁶个百分点 |

旧源码两项指标按四位小数展示时相同，未舍入差值如上表；不宣称旧、新 producer 字节相同。

本轮恢复了 PR #72 最小复现工具并做接口适配，使用新登记的 producer；PR #74 原 producer 程序未找回，因此不能冒用其身份。以上先列旧源码的实际校准差异，再解释本轮两臂比较的证据范围；未舍入值保留在机器结果中。

第一次尝试因压缩路径证据不完整，在 previous 478 / 795 时失败，原失败回执和账户状态保留，不产生经济结论。第二次只修改证据保存 I/O，生产源码、九个研究模块及经济条件保持登记值，两臂使用新身份从头执行。执行登记与失败诊断：**[测量协议](https://github.com/geniusgrok/coinquant/blob/d874ed0bef69d1b1ab8c32cf87eb2dc6791be486/evidence/2.0.0-remeasure-20261009/PROTOCOL.md)、[两次执行登记](https://github.com/geniusgrok/coinquant/blob/d874ed0bef69d1b1ab8c32cf87eb2dc6791be486/evidence/2.0.0-remeasure-20261009/ATTEMPTS.json)、[失败诊断](https://github.com/geniusgrok/coinquant/blob/d874ed0bef69d1b1ab8c32cf87eb2dc6791be486/evidence/2.0.0-remeasure-20261009/TRACE_FAILURE_DIAGNOSIS.json)**。

### 回撤与执行证据边界

本轮完整保留既有权益观测序列，并按这些观测逐点重算回撤，核对计数、顺序和滚动摘要；日收盘回撤另由 `financial.daily` 计算，`mdd_close` 仍是 close 观测代理。

路径代理沿用原研究的单层盘口/深度、IOC 逐笔量窗口、完整保护成交、固定维持保证金率、零额外退出滑点，以及缺失标记分钟的 hindsight bound。**配置中的 1% 是风险计算假设；模拟器额外退出滑点仍为零。** 后见边界分钟数为 **53 / 29**。原事件顺序中分别有 663 / 371 次时间戳倒退，审计原样保留并计数，没有为改善结果重新排序。

这是一段参与过开发的历史窗口、指定人工启动日程下的模拟证据。原生 Demo 执行验收状态为 **仍未完成；本次没有真实 Demo 或主网账户执行**。历史年化、模拟保护与路径复算不能替代真实连续交易所风险、资金容量或样本外表现的验证；人工启动间隔改变也会改变策略响应和结果。

完整证据包与机器指标：**[完整原始证据附件](https://github.com/geniusgrok/coinquant/releases/download/2.0.0/coinquant-2.0.0-remeasurement-evidence-20261009.tar.xz)**、**[未作展示舍入的机器指标](https://github.com/geniusgrok/coinquant/blob/d874ed0bef69d1b1ab8c32cf87eb2dc6791be486/evidence/2.0.0-remeasure-20261009/metrics.json)**、**[独立审计摘要](https://github.com/geniusgrok/coinquant/blob/d874ed0bef69d1b1ab8c32cf87eb2dc6791be486/evidence/2.0.0-remeasure-20261009/full-audit-summary.json)**。本轮 producer 为 `9b5ee3aea3a4f977b0b20c7b25e4a81ecdc5b7b188d9f26a3e119e03101f5413`；输入、spec、源码、回执、路径文件和工具身份由证据 manifest 绑定。

## 五、安装与使用

### 安装和只读核对

使用 Python 3.13，以下命令以 POSIX shell 为例：

```sh
git clone --branch 2.0.0 --depth 1 https://github.com/geniusgrok/coinquant.git
cd coinquant
cp config.example.json config.json
python3.13 -m coinquant --help
```

编辑 `config.json`，填写核验一致的 Binance UID，并将 `state_dir` 设为该账户固定的绝对路径或 `~` 路径。已有账户沿用兼容的原目录。默认会话 300 秒、轮询 5 秒，止损损失预算 `.10`、逆向滑点假设 `.01`。

凭据只从环境变量读取：主网使用 `COINQUANT_BINANCE_KEY` / `COINQUANT_BINANCE_SECRET`，Demo 使用 `COINQUANT_BINANCE_DEMO_KEY` / `COINQUANT_BINANCE_DEMO_SECRET`；两套互不回退，不将凭据写入配置或仓库。系统若缺 `America/New_York`，补装系统时区数据库或运行 `python3.13 -m pip install tzdata`。

```sh
python3.13 -m coinquant status --config config.json
python3.13 -m coinquant run --config config.json
python3.13 -m coinquant snapshot --config config.json --out coinquant-snapshot.json
```

`status` 核对一次账户与条件；普通 `run` 在期限内观察、恢复可核实状态并补齐模型；`snapshot` 输出新鲜只读 JSON，目标文件必须尚不存在。首次重建超过会话期限时，可再次人工运行从 checkpoint 继续。普通 `run` 不会维护交易所保护或完成策略退出。

### 有限 Demo 与主网试运行

```sh
cp config.demo.example.json demo.json
python3.13 -m coinquant run --config demo.json
python3.13 -m coinquant run --config demo.json --execute --trial demo --authorize-uid <DEMO_UID>
```

先填写专用 Demo UID、独立固定目录和正值 `capital_limit_usdt`，显式保留 `environment: "demo"`，并配置 Demo 凭据。示例金额 `"100"` 不保证满足当时最小可执行数量。程序核验单资产、单向、逐仓 20×等账户前提，不替用户调整账户设置，也不强造入场信号。

已发生的原生 Demo 执行用 `demo-evidence` 只读采集，需程序持久记录的入场、止损、止盈、减仓及停机触发原始客户端身份，并核对真实触发、子单、成交与同源码会话记录：

```sh
python3.13 -m coinquant demo-evidence --config demo.json --out demo-evidence.json \
  --entry-order-id <ENTRY_CLIENT_ID> --stop-algo-id <STOP_CLIENT_ALGO_ID> \
  --take-algo-id <TAKE_CLIENT_ALGO_ID> --reduction-order-id <REDUCTION_CLIENT_ID> \
  --offline-trigger-order-id <TRIGGER_CLIENT_ID>
```

取得同源码、匹配风险配置、资金上限足够的有效 Demo 证据，并获账户所有者授权后，复制主网试运行配置，填写主网专用 UID、固定状态目录、正值资金上限及主网凭据，先只读核对：

```sh
cp config.live-trial.example.json live-trial.json
python3.13 -m coinquant status --config live-trial.json
python3.13 -m coinquant run --config live-trial.json --execute \
  --trial live --authorize-uid <LIVE_UID> --demo-evidence demo-evidence.json
```

源码或执行配置变化后，不沿用不匹配的 Demo 证据。快照、软件检查或手填订单 ID 不能替代原生执行记录。

### 状态与升级

同一账户使用一台机器、一个客户端和固定状态目录，避免并发手工交易。停止会话后保留 `intents.sqlite`、观察归档及完整原目录；升级前核对状态布局与版本兼容性。不兼容状态继续用匹配旧版核对管理，或由账户所有者处理，不通过删库、改 UID、换空目录接管旧仓位。

会话结束可保留已确认的原生保护；停止报告仍需分别查看保护、持仓风险、未决执行及人工接管字段，`pending_intents=0` 本身不证明残仓有保护。完整操作、状态兼容与恢复要求见 [固定版本 README](https://github.com/geniusgrok/coinquant/blob/162ee7138952925ffafbc9b68be7c754c0c0a6c3/README.md) 和 [CLI](https://github.com/geniusgrok/coinquant/blob/162ee7138952925ffafbc9b68be7c754c0c0a6c3/coinquant/cli.py)。

项目供仓库所有者个人研究使用，公开可见不授予第三方使用许可，见 [LICENSE](https://github.com/geniusgrok/coinquant/blob/162ee7138952925ffafbc9b68be7c754c0c0a6c3/LICENSE)。

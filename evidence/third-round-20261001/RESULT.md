# BTC 合约共享会话账户 — 2026-10-01

三个固定候选完成全部 795 个有限会话，成交、持仓、已实现盈亏、手续费、
资金费及现金流水审计全部通过。共同历史模型下的基线支持保留 Coinquant
作为合约开发默认；没有策略晋升、原生资格升级或运行器退休。

| 固定候选 | 期末 CNY | 成本后 CAGR | 连续 MDD | 成交记录 | 未决会话 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Coinquant 默认 7.5 | 1,951,753.81 | 119.23% | 44.11% | 1,561 | 0 |
| Starquant 默认 0.048 | 7,772.36 | −3.68% | 51.75% | 49 | 0 |
| Starquant 半风险 0.024 | 9,174.88 | −1.27% | 38.21% | 41 | 0 |

每个账户独立从 CNY 10,000 起，无追加；2020-01-01 到 2026-09-20 UTC，
右端不含。不是把三个账户拼成一个组合。原件 [accounts.json](accounts.json)，
独立现金核账与决策 [assessment.json](assessment.json)。记录数包括部分成交，
不等于完整交易次数。Star 两候选各执行 39,734 个模型周期，12 个周期因
账户观察变化冻结，未决收尾为 0；这些不是实机性能或原生可用性证明。

## 对项目改造的作用

长期日常入口继续为 Coinquant 合约 + Spotquant 现货。Coinquant 原默认模型
及风险不变；Starquant 保留固定研究对照，不引入第三个日常交易服务。
其半风险账户降低回撤但仍亏损，不迁移到默认合约模型。不能把原连续回放
117.31% 当成这个有限手动启停场景的结果，也不能把本表当成原生收益预期。

Coinquant 距 150% CAGR 仍差 30.77 个百分点；本模型 MDD 在 50% 内，但经济
资格仍 NOT_MET，原生仍 NOT_QUALIFIED。本轮不新增选参。共同口径的成本/
时延压力晋升尚未开展；旧 M10 压力数字属于旧 FX/源码身份，不混入本表。
保留开发默认与开放交易资格是两件事。另一运行器正式退休仍需原生 Demo
闭环、状态迁移及人工操作负担的实际证据。

## 口径与验证边界

先登记 [第三轮协议](../../research/third-round-PROTOCOL.md)，再运行。调用
实际 `coinquant.session.run/Lifecycle` 与 `btc_perp.runner.run_cycle`，共享
官方交易/标记分钟、资金费、逐笔数量上界、795 次 300 秒/5 秒会话、读取
200ms/写入1000ms、0.00075手续费、双向各0.001兑换费，以及严格前一日
Frankfurter fixing。两模型按各自已有规则决定，Coin IOC 与 Star MARKET、
MARK_PRICE 与 CONTRACT_PRICE 保留差异；停机期间不发送客户端命令。

Star 的研究入口保留实际 Demo 门，使用发布的 USDT 5,000,000 名义上限；
并未删除生产守卫。市场和订单记录由离线适配器提供。Star snapshot 是
简化的历史桥接，不复现完整原生适配器请求图，不能据此认定实际读取时延、
手续费接口、原生部分 MARKET 或保护空窗已验证。没有真实历史订单簿或
队列优先级；市场单终态部分成交是离线假设。保证金档位及合约过滤用同一
研究代理，29 个缺失 mark 分钟沿用所有者已接受的事后边界，不是完整观察。
日线/分钟包络不能证明真正的价格路径。

共用历史库提供 2019-12 的小时预热；长窗口模型必须等待自己的窗口完整。
初始化指标峰值仍含父类固定 FX=6.9762 的现金点，首个决策前已切换共享
fixing；这是共同的指标代理，不是额外资金。原始保守包络按记录保留，不能
据此升级原生资格。各账户后续已记录峰值均高于这一初始化点。

Coin 经济源码 `00a6849f72cd6785d17f71db804564e9b82e998a`，Python SHA
`f2b451da2f6a452cb8a00c2b921a882d7ec6bd29003948f46f440b812768859a`；
Star 源码 `882b5212ed09a1c075e61399d30b50996691e24c`，Python SHA
`6331e9d2f36b8cba8406de5bf6863511626b12f6091ac174661fa3c5f1b0fcce`。
测量期间实际调用的执行/市场模块保持这些字节身份；后续核账、测试和只读
导出修正不是这个旧记录的源码版本。全部输入身份保存在原件中；恢复了
12 份缺失档案并校验冻结的 210 份分钟输入，见
[input-restoration.json](input-restoration.json)。逐笔文件按使用恢复、校验
官方 SHA，并仅轮转有本任务标记的 scratch cache。

真实 peer runner 的入场和两份原生形状保护通过集成探针；短仓、加仓、
部分成交与 CONTRACT_PRICE 适配边界测试通过。探针使用合成逐笔，见
[peer-entry-probe.json](peer-entry-probe.json)，不能代替原生账户。
最终完整 Coin 本地套件 335 项、compileall 和 diff check 通过。Star 完整
离线套件 323 项通过、10 项跳过；七类故障入口、ruff 和 mypy 通过。

## 重现与日常入口

在已安装 Starquant 锁定研究依赖的环境，从 Coinquant 根目录运行；生产
Coinquant 不依赖 peer。两个源码仓库须干净并使用记录的版本重现经济原件。
选择新输出文件，不覆盖旧记录：

```sh
python -m research.restore_comparison --market /tmp/coinquant-market
python -m research.unified_perp --star-repo ../starquant --market /tmp/coinquant-market --restore-prints --prints /tmp/btc-owned-print-cache --out /tmp/new-shared-accounts.json
python -m research.comparison_report /tmp/new-shared-accounts.json --star-repo ../starquant --market /tmp/coinquant-market --prints /tmp/btc-owned-print-cache --out /tmp/new-assessment.json
```

`--limit` 仅为 `/tmp` 诊断，不能排名。完整任务保留每次会话的实际结果；
异常退出保留未完成标记及 /tmp 进度，不把中断当成完整经济账户。

新增原生只读导出，无交易参数：

```sh
python -m coinquant snapshot --config demo.json --out /tmp/perp-fresh.json
```

UID、钱包观察区间及 mark 新鲜度受检查；权益只加一次浮盈亏，不再加保证金；
越过清算价的方向保留负距离。双账户并发采集、日期计数和 Spot 所有者 Demo
命令见 [Spotquant 第三轮](https://github.com/geniusgrok/spotquant/blob/codex/btc-first-round-20261001/evidence/third-round-20261001/RESULT.md)。
没有调用账户、使用凭据或下单；真实账户观察 0 天，原生/30日验收均待实际运行。

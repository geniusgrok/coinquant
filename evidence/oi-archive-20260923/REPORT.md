# BTCUSDT 永续持仓量：开发期官方原件与时间资格

前一轮仅检查少数 `.CHECKSUM`，由 2020-01-01 缺失推断整条输入不能用于从原起点计时的研究，结论过强。本轮从 **2020-01-01 至 2024-01-01（终点不含）**逐日取得 Binance USD-M `metrics/BTCUSDT` 的原始 ZIP 和 CHECKSUM，逐份验证提供方 SHA-256、CSV 字段、时间戳、重复及五分钟覆盖；脚本为 [`research/oi_archive_acquire.py`](https://github.com/geniusgrok/coinquant/blob/research/oi-causal-probe-20260923/research/oi_archive_acquire.py)。只访问公开行情原件，无账户或交易接口。原调查日志 `LOG_RUN_35882897104.txt`、`LOG_RUN_35883065863.txt` 保留作历史证据；那时没有下载 ZIP，此次改变了证据范围。

| 开发期 1,461 天 | 天数 | 处理 |
|---|---:|---|
| 2020-01-01 至 2020-08-31 CHECKSUM 404 | 244 | 保留原始账户起点和计时；这些日子无此输入时不能新开 OI 候选仓 |
| ZIP 与 CHECKSUM 相符、288 个唯一五分钟标签 | 1,140 | 只是**当前档案**完整，不自动等于当年决策时可见 |
| 校验相符但五分钟标签不全 | 68 | 所需观测缺刻则不可用；不能插值 |
| 校验相符但同一标签有冲突值或无效行 | 9 | 隔离，不在过滤时任意选一行 |

首个完整日为 **2020-09-01**。缺失的 244 天确实连续；其余日也并非全齐。2020–2023 各年完整日分别为 118、301、363、358；2021 年另有 63 个缺刻日。263 个日档含完全相同的重复行，完整日只在逐行完全一致时去重；2026-09-18 单日样本有乱序标签，因此任何读取都须按时间排序，而不是依赖 ZIP 行顺序。2020-09-01 例为 576 行、288 个唯一标签。原始字段含 `sum_open_interest`（BTC 合约数量）及 `sum_open_interest_value`（名义金额），后者受价格影响，不能把其上涨当成新增持仓。不要用其他币对、现货或别的交易所填充。

**点时可用性仍缺关键证据。** Binance 的[公开档案说明](https://github.com/binance/binance-public-data)说日档通常次日提供；其[历史持仓接口说明](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest-Statistics)给出五分钟统计与所报区间的结束时间，并限制接口的历史窗口。两者均不足以证明**本次下载的每个数值版本**在当年每次调用前已公开。HTTP `Last-Modified` 显示 2020 年可取的 122 个 ZIP 均于 2026 年修改，2021 年的 365 个 ZIP 中 334 个于 2026 年修改；这是修订风险的线索，不能反推它们直到 2026 年才首次公开，也不能反推旧值与现值相同。下载成功与文档中“通常次日”都不是逐日历史发布回执。五分钟 `create_time` 是观测标签，也不是下载发布时间。


## 在冻结调用时的必要时间筛查

`oi_time_eligibility.py` 固定三个原件 SHA，按每个调用前第 2、3 个完整 UTC 日档检查当前 ZIP 的 `Last-Modified` 是否均早于调用；先留出一天以上的日档生成时间。此条件**只是必要的保守筛查示例**，不是历史版本的发布证明，也不是为收益调过的可执行 OI 规则。开发 468 调用中，虽然 350 次有这两份当前完整日档（2020–2023 分别 38、85、119、108 次），只有 **43 次**两份当前文件修改时间均早于调用，全部在 2023 年；2020–2022 为 **0**。与 DC10 原价格跌幅≥10% 相交仅 `2023-08-23T09:00:00Z` 一次，该原账户的实际成交分段净额 **−4.624199 USDT**。43 次调用不是 43 笔交易；这一笔也不是 OI 策略的净损益。精确年别、事件身份和可复现源码见 `TIME_ELIGIBILITY.json` 与 `oi_time_eligibility.py`。它解释为何在现有原件下尚不能冻结有代表性的价格/OI配对开发净账户，不证明其他价格规则的 OI 无效。

因此 OI 当前处于**档案覆盖已核查、历史数值版本与发布时间资格未闭合**状态。可以设计从原始 2020-01-01 账户起点开始、早期空仓仍计入复利的统一模型，但尚不能以这些 2026 年回取值冻结可执行 OI 判别并声称因果合格，也没有候选、配对去 OI 控制或成本后账户；不能写作信号经济失败。若取得每个使用时段的历史快照或原始发布时间及修订对照，再先冻结完成观测、发布滞后、连续预热、过期/缺失、持仓时失效和相同价格规则的去 OI 对照，然后按原 468 调用净账户核验。不得按后段收益选择何年启用。

完整原件在研究分支 [`research/oi-causal-probe-20260923`](https://github.com/geniusgrok/coinquant/tree/research/oi-causal-probe-20260923/evidence/oi-archive-20260923/development-originals)，提交 `8ed8cbac49ec5c0c080be4ea4c6678e7367aaeda`：`MANIFEST.json` SHA-256 `abc9a7bde759f23598f31b7ea40e9f197be8efcb29cb1ac964058537c2f30bc6`；含全部 1,217 个实际 ZIP 与 CHECKSUM、及清单的 `OI_DEVELOPMENT_ORIGINALS.tar.gz` 为 **14,431,948 字节**、SHA-256 `a15d9d1dd28ac8901f5daa81fda9a58e86847ee0e29f77ba04d9f687f6b35196`。当前下载和提交的原始[Actions 运行](https://github.com/geniusgrok/coinquant/actions/runs/35892770477)及独立新检出[回读运行](https://github.com/geniusgrok/coinquant/actions/runs/35893521581)提供复核入口；后者重新核算整包 SHA-256、Git blob `0f0f5dd4be05d31e25967f77ebd32350cb261ba8`、包内清单及 1,217 对逐日 ZIP/CHECKSUM，全部通过。若资料后来更新，以清单逐日 SHA 为准，不将新值混入本次研究。研究分支仅保全原始档案，正式主线保留精简报告与诊断，不增生产路径。

从已核验 DC10 原件区分 2025 重叠价格事件、真实入场及开发期成本后账户，见 [`EVENT_NET_AUDIT.md`](../drawdown-reclaim-20260923/EVENT_NET_AUDIT.md)。七日未来毛价不能当可执行净优势；OI 尚无完成的增量净收益证据。正式最佳仍为 SX60 全窗 **102.626211% CAGR／39.885115% 连续 MDD**，距收益目标 47.373789 个百分点；生产 B36 和 `run --execute` 阻止不变。

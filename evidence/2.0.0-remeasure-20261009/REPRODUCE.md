# 查看与复核本轮结果

本目录属于独立研究证据分支。交易程序仍以 `2.0.0` tag 的源码为准；回放工具不会成为主分支的运行依赖。

本次执行身份以 `spec.json`、`tooling/tooling-registration-v2.json` 和最终回执为准。`BASE_INPUT_QUALIFICATION_INHERITED_V1.json`、`tooling/ADAPTATION_V1.md`、`tooling/tooling-registration-v1.json` 保留首次准备/执行的历史身份；`tooling/source-prepared.json` 是恢复的 PR #72 来源记录，它们都不冒称本次 producer。

## 结果与原件

- `metrics.json` 保留未四舍五入的 Decimal 结果，`RESULTS.md` 是对应表格。
- `full-audit-summary.json` 记录两臂的账本、成本、官方资金费、完整路径、会话收尾及来源核对。
- `state-audit-previous.json`、`state-audit-current.json` 是对已结束模拟账户的只读审计；它们区分本地已归档事件和终点无人观察的新事件。
- Release 附件中的 `coinquant-2.0.0-remeasurement-evidence-20261009.tar.xz` 保存完整回执、会话报告、生产调用计数、分段检查点、原始压缩权益路径及详细差异审计。附件不包含账户数据库或大型原始行情。
- `EVIDENCE_FILES.json`、`SHA256SUMS` 用于核对发布文件身份。压缩路径中的每个金额均为原字符串，没有抽样、改值或重新排序。

第一次执行在 478/795 次会话后因路径文件截断失败。`ATTEMPTS.json` 与 `TRACE_FAILURE_DIAGNOSIS.json` 保留这一事实及身份；该次失败结果不用于收益、回撤或后续续跑。第二次使用新 producer 和全新结果目录完成配对，经济输入与生产默认参数没有因此改变。

## 冻结条件

原窗口为 `[2020-01-01T00:00Z, 2026-09-20T00:00Z)`，2454 天。初始 10000 CNY，原 795 次会话、每次 300 秒，读写延迟、手续费、资金费和双边汇兑成本均按 `PROTOCOL.md` 登记。年化公式为：

```text
(期末 CNY / 10000) ** (365.2425 / 2454) - 1
```

权益路径最大回撤沿用原代理模型；日收盘回撤另用 `financial.daily` 的 2454 个日终值及初始 10000 计算。第一条标为 2019-12-31 的记录是窗口开盘边界，不能当作一个投资日或一个年度。2026 年只有 262 天，分年表中的收益未再年化。

两臂使用同一 producer 和经济合约，但保留各自真实默认风险。previous 是 PR #74 的 `79a334b2d776be2dbe8756f3a616697f9403982e`，current 是 `162ee7138952925ffafbc9b68be7c754c0c0a6c3`。不能把 current 的 10% 止损预算改回旧版 49% 后仍称为本次 2.0.0 默认测量。

## 恢复行情

`inputs/INPUT_MANIFEST.json` 保存 1164 个文件的精确公开地址、大小和 SHA-256；390 个 market ZIP、773 个逐笔 ZIP、1 个汇率文件合计约 14.31 GB。`inputs/sources/` 保存来源清单，`tooling/evidence/` 保存原 warmup、ALFRED vintage 与规则输入。

把 `inputs/` 复制到独立数据目录后，可在其中执行：

```bash
python restore_inputs_v2.py --groups all --workers 16
```

下载器拒绝与原登记不符的现有文件和新下载内容。已有原 `DOWNLOAD_RECEIPT.json` 是本次恢复的历史证据，应先保留；新的下载会产生自己的真实恢复回执。`build_parsed_cache.py` 只是可选的原解析器缓存，不是重测的前置条件。缓存包的校验范围另见发布的缓存清单与核验报告。

## 复核已保存的完整回放

本轮实际解释器为 Python 3.12.14，与恢复的 PR #72 研究工具记录一致。项目日常安装仍按主分支 README 使用 Python 3.13；不能据此把本次研究写成 Python 3.13 执行。

原回执绑定了真实绝对路径。要不改动原件地复核，可在新的隔离环境内恢复 `/workspace/scratch/4a60782c7dbc` 目录结构，或者将准备好的目录挂载到该位置：

```text
coinquant-remeasure-tooling-v2/       本目录 tooling/ 的原样副本
remeasure-inputs/                    本目录 inputs/ 及恢复的原始行情
coinquant-remeasure-2.0.0/previous/   固定 79a334b... 的 Git checkout
coinquant-remeasure-2.0.0/current/    固定 162ee71... 的 Git checkout
coinquant-remeasure-2.0.0-v2/         本目录的脚本、spec、来源清单和解出的回放原件
```

解包前核对附件 SHA；在隔离目录解包，不覆盖现有交易状态。固定两个 checkout 的实际生产文件必须与各自 `*-source-files.json` 完全相同。最终回执文件名由附件中的 `PROGRESS.json` 给出，不猜测分段数量。

恢复完成后，在 `coinquant-remeasure-2.0.0-v2/` 内，用 `PROGRESS.json` 中的两条 `receipt` 路径执行：

```bash
python independent_financial_audit.py \
  --main <previous 最终回执> --candidate <current 最终回执> \
  --main-spec spec.json --spec spec.json \
  --out local-verification.json --summary local-verification-summary.json
```

该脚本只读证据，不导入或启动生产策略。它重新核对全部路径序号和滚动 SHA、峰谷与回撤、成交费用、资金费、钱包和权益、订单归属、795 次实际调用及会话收尾。若完整证据或原始输入缺失，应得到失败，不能通过填零、删记录或改标志消除。

SQLite 原件按项目约定不提交；本次委托者另有模拟状态留存包。公开金融与路径审计不依赖公开数据库。要另做一轮完整运行，应建立新的登记和全新输出目录，由 `run_pair.py` 串行执行两臂；不要重置或迁移旧账户、覆盖本轮原件，或把不同 producer 的检查点接在一起。

## 模拟范围

完整审计证明这些冻结输入、生产路径和账本在本研究模型内一致。单层盘口、逐笔 IOC 数量窗口、完整保护成交、固定维持保证金、零额外退出滑点和缺失标记分钟的 hindsight bound 仍是旧研究假设。配置中的 1% 滑点用于风险定量，不能当作模拟撮合实际增加了 1% 退出滑点。结果不等同于真实交易所的连续执行、资金容量或样本外收益。

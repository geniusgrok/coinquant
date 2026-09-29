# Coinquant 接续入口（2026-09-29）

先核对实时 `geniusgrok/coinquant` main，再读 `AGENTS.md`、`PROJECT_STATE.md`、`evidence/remeasure-20260929/RESULT.md`（只对应历史源码摘要 `ae7b3fd8…` 的 M9 数字）、`evidence/full-review-20260929/RESULT.md`（含范围限制与未验证项）、`evidence/robustness-20260929/RESULT.md`、`evidence/rebuild-20260927/RESULT.md` 与 `research/redesign-PROTOCOL.md` 的 M9、M8、R3、O0、O1 部分。

当前默认：SX60＋DFII10，主信号风险7.5（历史 R3 规则选出；历史 M9 在其对应源码上同样选中 7.5；本轮未重新选择），宏观3.6。上次完整 M9 基准 ¥1,893,613／118.24% CAGR／44.51% MDD，只适用于旧源码摘要 `ae7b3fd8…`；当前源码已改资金/保护接线与研究虚拟时钟，**没有重测结果**。本环境缺 `/data/coinquant-market` 和 `/data/coinquant-prints`，`research.rebuild --limit 1` 在四小时行情加载处失败。拿到原始输入后，以冻结 795 会话时间表在新源码上运行已登记的基准、压力和日历年区块，记录新源码/输入摘要，不覆盖 M9 原件；待全部结果核对后再更新当前经济结论。`economic_qualification` 仍为 `NOT_MET`。旧 R3 的 131.26% 只对应 `evidence/robustness-20260929/m8/`；P7（153.86%）只对应 `a6892b3`。旧模型常数邻居与会话时序的敏感性见 `evidence/remeasure-20260929/RESULT.md` 与 `research/redesign-PROTOCOL.md`，不可当作当前测量。

规则：

- 默认只读；仓库所有者可按 README 显式启动受控 Demo，主网小额试验另需真实 Demo 闭环证据、专用小额资金和当次确认。代理未获授权代替所有者下单或修改账户设置。源码摘要不符则主网试验门拒绝。
- 不按压力结果或已知数据缺口调参；新的经济测量前先冻结会话时间表与试验登记（`research/redesign-trials.json`）。
- 完整试验：`python -m research.rebuild <名> [--primary-risk ...] [--fee ...] [--sequence ...] [--knob 名=值] [--from ... --until ...] [--uid N]`（`--knob` 是研究旋钮，默认值与生产一致；区块只是新账户稳健性测试，不写正式结果名；并行试验需要不同的 `--uid`，因为账户锁按 UID 加锁），结果写入 `evidence/rebuild-20260927/<名>.json` 并记录源码提交与输入摘要；`--limit` 部分运行写入 `/tmp/coinquant-partial`；部分或子窗口结果不能写入证据目录，同名证据需 `--overwrite`（原件以 `.superseded-<运行ID>` 保留），状态目录默认唯一且带所有权标记（无标记目录、符号链接、仍在运行的所有者一律拒绝）。
- 离线检查：`python -m unittest discover -s tests`。

当前工程阶段已实现未知订单恢复、受控入口、保护时序记录及试验配置。离线验证与剩余限制见 `PROJECT_STATE.md`；原生 Demo、专用小额主网与经济资格尚未完成。恢复时核对实时 main、仓库最新提交、`PROJECT_STATE.md` 和 README，再以同一账户状态目录从只读 `status` 开始；不得删除旧 SQLite 或把试验入口称为常规生产资格。

2026-09-29 早先审查（`COINQUANT` 修复清单 C01–C13）已进入 main；本轮附件 C1/C2 和状态备份、同类虚拟时钟问题的状态见 `PROJECT_STATE.md`。`收尾预算/execution_unresolved/资金流水放行门/保护替换`都是安全行为；恢复时必须先核对真实账户身份和持仓归属。历史收益原件按源码摘要阅读，不得归于新 main。

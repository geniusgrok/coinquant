# Coinquant 接续入口（2026-09-29）

先核对实时 `geniusgrok/coinquant` main，再读 `AGENTS.md`、`PROJECT_STATE.md`、`evidence/robustness-20260929/RESULT.md`、`evidence/rebuild-20260927/RESULT.md` 与 `research/redesign-PROTOCOL.md` 的 M8、R3、O0、O1 部分。

当前默认：SX60＋DFII10，主信号风险7.5（R3 在测量器 M8 上按登记规则选中；O1 曾降到6），宏观3.6；R3 基准 131.26% CAGR／44.51% MDD，压力 97.57–121.53%（手续费+50% 106.19%），MDD 最高44.87%，CAGR 未达150%目标；建立在所有者接受的2020-01-19标记价缺口边界上（`path_complete=false`）。M8 让读请求占200 ms模拟时间，消除了本地请求权重造成的路径依赖（O0）；历史 P7（153.86%）只对应源码 `a6892b3`。全窗口终值对风险不单调、对读延迟与手续费敏感，131.26%不是稳定估计；信号常数的单参数邻居只有40–102% CAGR（M7 上），即位于尖峰上。详见 `research/redesign-PROTOCOL.md` 与 `evidence/robustness-20260929/RESULT.md`。工具：`python -m research.robustness run|report`、`python -m research.risk_select`。

规则：

- 默认只读；仓库所有者可按 README 显式启动受控 Demo，主网小额试验另需真实 Demo 闭环证据、专用小额资金和当次确认。代理未获授权代替所有者下单或修改账户设置。源码摘要不符则主网试验门拒绝。
- 不按压力结果或已知数据缺口调参；新的经济测量前先冻结会话时间表与试验登记（`research/redesign-trials.json`）。
- 完整试验：`python -m research.rebuild <名> [--primary-risk ...] [--fee ...] [--sequence ...] [--knob 名=值] [--from ... --until ...] [--uid N]`（`--knob` 是研究旋钮，默认值与生产一致；区块只是新账户稳健性测试，不写正式结果名；并行试验需要不同的 `--uid`，因为账户锁按 UID 加锁），结果写入 `evidence/rebuild-20260927/<名>.json` 并记录源码提交与输入摘要；`--limit` 部分运行写入 `/tmp/coinquant-partial`。
- 离线检查：`python -m unittest discover -s tests`。

当前工程阶段已实现未知订单恢复、受控入口、保护时序记录及试验配置。离线验证与剩余限制见 `PROJECT_STATE.md`；原生 Demo、专用小额主网与经济资格尚未完成。恢复时核对实时 main、仓库最新提交、`PROJECT_STATE.md` 和 README，再以同一账户状态目录从只读 `status` 开始；不得删除旧 SQLite 或把试验入口称为常规生产资格。

# Coinquant 接续入口（2026-09-28）

先核对实时 `geniusgrok/coinquant` main，再读 `AGENTS.md`、`PROJECT_STATE.md`、`evidence/rebuild-20260927/RESULT.md` 与 `research/redesign-PROTOCOL.md` 的 M6 部分。

当前默认：SX60＋DFII10，主信号风险7.5，宏观3.6；P6 153.87% CAGR／44.73% MDD（与 M5 相同），建立在所有者接受的2020-01-19标记价缺口边界上（`path_complete=false`）。成本/滑点/深度压力 CAGR 148–149%，随机跳过20%会话 101%。

规则：

- 不打开 `run --execute`（实盘与 Demo 都阻止），不发真实或 Demo/Testnet 订单，不改账户设置。
- 不按压力结果或已知数据缺口调参；新的经济测量前先冻结会话时间表与试验登记（`research/redesign-trials.json`）。
- 完整试验：`python -m research.rebuild <名> [--primary-risk ...] [--fee ...] [--sequence ...]`，结果写入 `evidence/rebuild-20260927/<名>.json` 并记录源码提交与输入摘要；`--limit` 部分运行写入 `/tmp/coinquant-partial`。
- 离线检查：`python -m unittest discover -s tests`。

剩余工作：原生交易验收（见 `evidence/bounded-session-20260926/RESULT.md`），以及若要多空都能新开仓，需要一条经冻结协议验证的开空规则。

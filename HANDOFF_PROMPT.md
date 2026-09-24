# Coinquant 当前恢复入口（2026-09-24）

**最新工作**：先读取 `PROJECT_STATE.md` 顶部与 `evidence/downside-channel-20260924/{PROTOCOL,RESULT}.md`，并查询实时 main、研究分支 `research/downside-channel-20260924` 的 SHA、PR 和检查状态。该分支从 main `0ecd1a03058631d51b7b2d66aa97b11663ea1cf1` 起。下行通道空头在冻结 468 次开发调用的简化连续账户探针中 CAGR −34.747968%、保守 MDD 91.036954%、账本误差 0，按事前早停停止扩展；不是正式经济否决，也没有 795／压力／787。不可将通用回放器的“305 days only”字样视为本轮官方原件完备性声明。完整结果与验证边界在 `RESULT.md`，账户归档 SHA-256 `23c1b95d497ef54c1b870291e156aa2f5f9724d6095be29aa94156cf054dfcba`，重建用 `archive/reassemble.py`。

本轮需确认 `minutes/downside-minutes-{0,1,2,3}/data/futures/um` 的 301 份有效官方 ZIP 与 CHECKSUM、回执及两份拒绝原件都已在远端保存；仓库全局忽略 `data/`，临时 workflow 取数时必须显式 `git add -f`。最终 PR 移除该工作流后保留原件和回执。最佳已完成正式 SX60 仍 102.626211%／39.885115%，目标未达；不要复跑已经拒绝的空头机制或改动生产默认/执行阻止。

下文是上一次 C7 阶段的历史恢复说明，以本段实时状态为准。

仓库 `geniusgrok/coinquant`。恢复前读取实时 `main`、`AGENTS.md`、`PROJECT_STATE.md` 及 `evidence/c7-call-expiry-20260924/RESULT.md`，不得用历史 140/2/23 部分包覆盖新原件。当前任务从基线 main `242c8a2a03e7eafa537bd7c6bcc21fea23f53e22` 和研究分支 `research/minute-acceptance-20260924` 开始；远端 PR、最终 HEAD 以实时查询为准。

官方 1m 交易价/mark 的首批 16 日和 C7 另需 2020-11-26，合计 34 个 ZIP/CHECKSUM，已经在研究分支 `evidence/c7-call-expiry-20260924/minutes/` 逐文件回读核验。165 个独立事件已 **163 闭合/2 几何拒绝/0 未知**；原 23 个未知补数后全亏。C7 按原调用七天到期计划退出，在 468 开发账户的 2021-05-28 未知保护小时之前已有收盘回撤 58.012879%，超过 <50% 风险门，经济否决；不外推其 CAGR，不运行其正式/压力/缺席验收。SX60 同版控制完整 468 开发调用 CAGR 162.179152%、保守 MDD 37.209136%，与原原件一致。最佳完整正式 SX60 仍 102.626211%／39.885115%，≥150%/<50% 未达。B36 与 execute 阻止不变。

完整事件、C7 中断原件、SX60 对照原件放在 `evidence/c7-call-expiry-20260924/archive/` 确定性分片；按 `archive/MANIFEST.json` 用 `archive/reassemble.py` 校验重建。报告给出来源身份、风险点和复现。临时取数工作流完成原件保存后必须从待合并版本移除，保留官方原件、取数脚本及回执；合并前核验 PR、强制检查和远端 tree/ref。不要将已否决 C7 的中断前缀当成完整账户，不得因缺少 2021-05-28 后续分钟而忽略在此前已发生的硬性回撤失败。

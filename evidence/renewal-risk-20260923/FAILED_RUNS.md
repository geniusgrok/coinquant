# 失败运行原件索引

以下完整原件包 `COINQUANT_HR60_EVIDENCE_20260923.zip` 内的目录及旁路记录均保留；这些记录不作为候选绩效结果。

- `results/HR60-development-failed-01/`：首个开发尝试在执行时未导入 `gap_margin`，因 NameError 中止。保留调用参数、日志及完整 traceback。
- `results/HR60-development-failed-02/`：第二个开发尝试完成了账户回放，但 JSON 汇总不能序列化 `Decimal`，在完成验证前中止。保留全部可恢复账本及 traceback。
- `results/HR60-development-failed-03/`：完整 468 调用回放使用调用时冻结的减仓数量、T+60 执行；价格/标记在等待期间变化，执行后风险重验有 15 次违规。此运行被拒绝，后续版本改为 T+60 使用当时因果可见数据重新计算数量。其完整账户输出、输入身份、日志均保留。
- `results/HR60-development-superseded-04/`：合并前独立审查发现续持基数缺少 unresolved/子单闭合门禁，且不可行计划会中断回放。此完整通过候选已被门禁修正后的同一 HR60 回放替代，不作为最终绩效结果。
- `results/HR60-development-superseded-05/`：基数门禁已修复，但尚未显式要求 GAP 锚点必须是最后一笔确认子单；已由加严后的同一 HR60 回放替代。
- `results/HR60-development-retry-stale-01/`：`superseded-04` 的重复归档副本，不代表额外回放。
- `results/HR60-development-partial-streams-01/`：未闭合的流式文件片段，独立隔离且不参与验证；仅最终目录内通过 CRC、账本和风险审计的完整流用于结果。
- `results/HR60-full-window-failed-01/`：正式全窗首个账户尝试因实际入场所需分钟未包含在已验证的分钟覆盖中而中止，没有产生完整全窗账户。`FULL_WINDOW_INPUT_GAP.json` 进一步列出本地原件覆盖缺口。

只有 `results/HR60-development/` 是修正后通过 HR60 开发硬检查的账户；它不是正式全窗结果。

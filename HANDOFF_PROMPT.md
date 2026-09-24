# 最新接续入口（2026-09-24）

先读 `PROJECT_STATE.md` 顶部和 `evidence/unified-channel-20260924/CONTINUATION_RESULT.md`。PR #24、#25 已合并；UC4 3.6 在有效连续前缀的独立小时收盘回撤达到 54.6928008577%，按风险门拒绝，不再为了它补 2021-08-15 的分钟或报告部分账户 CAGR。UC4-PF55 完成 468 调用、CAGR54.8044%/保守 MDD44.9986%，按收益门拒绝，不做参数扫描和全窗。两份完整原件与官方新增分钟在上述报告标明，失败研究提交 4e957b3 可回读但不得将其切换为生产默认。后续市场机会筛查不支持直接镜像 UC4 空头，具体数字见报告，不能称净账户。正式目标未达；优先研究具备独立净收益机制的单一核心，验证真实稀疏调用和完整分片执行，避免重复 UC4/PF55。下方旧恢复命令及等待 PR #24 的文字属于历史状态。

# Coinquant 续接：UC4 证据纠正与 3.6 配对闭合

仓库 `geniusgrok/coinquant`，personal / geniusgrok。先读实时 main、AGENTS.md、PROJECT_STATE.md 顶部、PR #24 与 `evidence/unified-channel-20260924/REPORT.md`。写本入口时 main `6e6ae3f3b12c62e2c86dd227bf1f8844490cb267`，修复分支 `research/uc4-evidence-fix-20260924` 正在更新；远端提交和CI每次重核。生产B36、执行阻止保持，无实盘/Testnet授权。

## 已确认

1. 冻结 UC4 6.0 与 3.6 的旧 `minute_validation.hours` 都有361小时，却均**没有**2021-04-18 03:00 UTC。旧代码该小时使用整小时 OHLC。旧保守包络 76.154555%／57.588199% 不是「该分钟先强平」或「已证实真实回撤下限」。按旧 close 行重算 MDD 分别59.886072%／44.318401%；两条旧开发账户均在该小时停止，无开发CAGR。6.0 的已保存 close-only 代理路径独立超50%，3.6 尚未完成、无资格。
2. 官方交易价及mark 1m ZIP、CHECKSUM已取回，2021-04-18 03:00小时分别60根、精确重建旧小时OHLC，交易量差0。mark首跌破SL 57700于03:19 UTC，首跌破原强平边界于03:35 UTC。冻结代理模型应在03:19处理止损后停止旧仓位风险；不等于真实交易所保护成交资格。
3. 旧3.6部分账户中断以前5168个有仓小时，9个粗小时可能触发保护，含中断小时；详见 `COVERAGE_HOURS.json`。旧完整依赖含其中3天分钟，其他5天已通过研究分支官方取数；2021-01-26逐日mark缺失，使用官方月ZIP。研究入口增 `--coverage-hours`；UC4持仓粗小时可能触发SL/TP/强平时明确停机。定向新测试已加；PR #24曾有一次CI成功，新提交CI另核。
4. 原始失败包 `COINQUANT_UC4_DEVELOPMENT_RISK_REJECT_20260924.zip` 保持不变：Library `libfile_3bfa4d5d98e48191a5d280fc2830e3f2`，2,981,114字节、SHA256 `cad6b6b963a9b095f56268879d399d619e8c1477e829579f92100ad87bdc196d`；旧测量源码在包内 measured_source/risk-control。旧输入身份 `f1f1c7c9ddb985d4b034c307267283c76e1e987cfd737d7b22bfa801d4e657f2` 在本次补细化之前原样重建核对通过。现有报告纠错见同目录REPORT.md。

## 未完成和恢复顺序

本地执行环境在恢复数据后返回 `environment_offline`，**尚未运行新增分钟的3.6完整468调用**，也未完成9个新增小时的实际载入和全部重建，不能报告经济结果。研究分支的官方原件和小型改动已远端保存；旧依赖仍完整在Library。没有后台任务。

1. 恢复执行环境后，核验 PR #24最新HEAD/CI以及每个新增远端ZIP、CHECKSUM与本地字节/hash；分别验证压缩档存在、小时重建、载入、保护实际使用。若本次scratch还在，`/workspace/scratch/9bec34ab9b50/coinquant` 是旧本地checkout，先 `git fetch` 并正常快进到研究分支，不用旧本地文件覆盖远端。
2. 若要重建旧原件，Library `libfile_7579b3804a4c8191b16800c40c81d5df` 是184,635,190字节 M60 COMPLETE，内含 `dependencies/COINQUANT_BOUNDED_EXECUTION_20260922.zip` 与 `dependencies/COINQUANT_SUSTAINABLE_CAPITAL_EXIT_20260922.zip`；展开分别作为 `--bounded-originals`、`--sx60-originals`。M60 分钟依赖另有 `libfile_f238bff2ad6c819183809199ef661478`（开发分钟）、`libfile_b6057b4e31bc8191979c45b8060481da`（保护分钟）、`libfile_dec4645a5afc8191937b52f06c35abf8`（mark复核）、`libfile_6b23bff662d8819185867ef506e3be4a`（预热探针）。此会话scratch曾展开到 `../replay/bounded`、`../replay/sx60`、`../replay/m60-*`；如丢失，从原件按哈希恢复，不重跑旧策略代替。
3. 从仓库根目录运行固定3.6开发回放：`python -m research.channel_core_replay --bounded-originals ../replay/bounded --sx60-originals ../replay/sx60 --new-data ../replay/m60-development --new-data ../replay/m60-protection --new-data ../replay/m60-mark --new-data ../replay/m60-warmup --new-data evidence/unified-channel-20260924/minutes --coverage-hours evidence/unified-channel-20260924/COVERAGE_HOURS.json --risk-control-3.6 --output ../replay/UC4-risk-control-3.6-repaired`。每个输出路径新建，旧失败原件绝不覆盖。若发现新缺精度持仓小时，先收集并批量补原件；不能按旧CSV末行接续。6.0无需强行完成已独立代理风险失败的经济账户。
4. 分别检查逐分钟权益、保守包络、实际退出事件、费用/funding、资金与GAP、账本，不能把冻结止损填单假设冒充交易所成交。完整3.6开发双门通过才跑795全窗及后续压力/787缺席；失败则按收益与风险归因提出实质不同机制，保持150% CAGR/<50% MDD及原冻结协议。不扫描UC4新风险尺度。
5. 移除分支临时 `.github/workflows/uc4-minute-recovery.yml` 后，等待PR #24最后CI、正常合并main并核验ref、源码与官方原件回读。若环境始终离线，先完成可独立的报告/CI/PR整合，如实说明3.6仍未完成。

当期已完成最佳SX60为102.626211% CAGR／39.885115% MDD，目标≥150%／<50%仍未达到。不存在实盘执行或后台研究。

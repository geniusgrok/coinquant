# 证据与复现说明

## 先确认版本与统计口径

本次以 2.0.0 的 `162ee7138952925ffafbc9b68be7c754c0c0a6c3` 完整回执作为控制组；79a 历史版本只作背景。原 2×2 对照含控制组和前三个修复组，第四个修复组 combined-v3 单独报告追加冻结缓冲的增量效果。

| 修复组名称 | 公开不可变源码 | 本轮登记与状态目录 |
| --- | --- | --- |
| `margin-only` | `06206ac0c5383fb009df8bac20601cd9e2d9b004` | `replays/` 下最终通过 full795 的独立重试目录，以实际登记为准 |
| `book-v2-only` | `37bfc8a833d1ff3c0992842ce363758a47b1d06f` | `replays/book-v2-only/` |
| `combined-v2` | `3561728dab351d269b19b107fb4fbabb2ac1f674` | `replays/combined-v2/` |
| `combined-v3` | `230a61daade55d7d80de56f61aae24e660fb3a40` | `replays/combined-v3/` |

公开提交读回分别见 PUBLIC_SOURCE_VERIFICATION.json 与 PUBLIC_SOURCE_VERIFICATION_V3.json。v3 的公开 tree 为 `287fa361a36978fd782538433e7e82462c0587d8`；最终发行源码与实测 19 个生产模块的同一性另见 RELEASE_SOURCE_VERIFICATION.json。

RESULTS.json / RESULTS.md 与 figures/ 保留原 2×2 对照；FINAL_RESULTS.json / FINAL_RESULTS.md 与 figures-v3/ 增加第四组 v3，使用新的汇总和绘图脚本，不能覆盖原文件。ROOT_CAUSE.md 解释原因；PROTOCOL.md、BOOK_GUARD_AMENDMENT_V2.md、FROZEN_BUFFER_AMENDMENT_V3.md 分别保留原协议及两次补充。v3 补充是在查看 v2 完整结果后提出，其 SHA-256 `040729b29351abcf2a87244ba66f385eefbb2db33c5601cd80a31198d0bba9f4` 已冻结并写入 v3 registration / spec，不能倒称为在 v2 测量前登记。

v3 的 `incremental_base` 固定绑定 combined-v2 的源码、spec 和完整回执；其中 v2 receipt SHA-256 为 `6b1fe9dd901e933928e4148df614ff67ad94a3910fa502dfe41a17047846fc0b`。`FINAL_RESULTS.json` 的 `incremental_comparisons.combined-v3_minus_combined-v2` 只比较两份各自完整、审计通过的结果，并再次核对两者与同一 2.0.0 控制组的经济输入和策略一致。原交互项仍为 `combined-v2 − margin-only − book-v2-only + control`；v3 不替换原 2×2 中的任何一格。CAGR 和回撤差值是该固定历史路径上的描述性差异，不能相加推演成通用收益贡献。

原 margin-only 中断回放只有 788 条会话报告，无末段完整回执，原样保留且不计入完整结果，见 ONE_SEGMENT_LAUNCHER.md。`margin-only-rerun-001` 使用新的独立状态，登记的 case 仍是 `margin-only`，源码和经济设置保持一致；它不是把原中断分段拼接到重试上。这次重试也未完成：segment002 / checkpoint 的内存游标与日程为 711，但已绑定相同 SHA 的磁盘 reports / production-calls 均只有 709 条，缺少 2023-11-17 20:00Z 和 2024-09-17 08:00Z。segment003 在恢复阶段按原检查拒绝，实际没有执行新会话，不能因先前 `can_resume=true` 便将它计作完整结果。缺失记录的具体宿主或存储原因尚未证实；禁止补造日志、截断报告或回滚账户来通过恢复检查。

两次失败分别保留各自目录中的 `INTERRUPTION_20261010.json`、已完成分段、日志、检查点与私有模拟状态；其中重试文件实际名为 `replays/margin-only-rerun-001/INTERRUPTION_20261010.json`，SHA-256 `1c88fff48a13576cecbe8b461e7ee3d6f04f3d9ec4eca5e114b78740f08b274c`。若继续重试，须再建新目录和登记，最终 margin-only 结果只能采用该次完整、独立审计通过的原件。三个 v1 冒烟及测试失败记录也保留，不与完整 v2 / v3 结果混用。

## 需要哪些原件

本次发布附件保存新增实验的分段回执、原始权益路径 gzip、报告、调用记录、检查点、source maps、spec、命令、独立审计、汇总与绘图脚本。账户数据库和完整观察归档另作账户状态备份，不放入 Git 或公开附件；公开逐笔账本和会话证据足以独立重算所报告的金融数字。

原始控制组和 79a 历史背景的完整公开原件仍在 2.0.0 附件：

- 名称：`coinquant-2.0.0-remeasurement-evidence-20261009.tar.xz`
- 字节数：67,465,568
- SHA-256：`3b2ebd1078c373c8b09fd152b82bc70c6722b77853909b726633d5b4498f73d3`
- 下载：https://github.com/geniusgrok/coinquant/releases/download/2.0.0/coinquant-2.0.0-remeasurement-evidence-20261009.tar.xz
- 对应证据提交：`d874ed0bef69d1b1ab8c32cf87eb2dc6791be486`

原行情、逐笔与 FX 共 1164 个文件、约 14.31 GB，不重复塞入发布附件。原 INPUT_MANIFEST.json 中保存下载来源、大小和 SHA；本轮 DOWNLOAD_RECEIPT.json 对全部原件重新下载/校验，CACHE_MANIFEST.json 与 CACHE_VALIDATION.json 对 773 个原 parser 缓存独立核验。缓存不改变经济数据；不能把旧缓存清单冒充本轮实际下载或验证。本次验证保留新旧两份证明。

## 只读核验

下载附件后先核对其字节数与 SHA-256，再解压。逐文件清单绑定包内的公开证据。所有已有 spec、receipt、audit、path-trace 都作为不可变原件保留，不能直接改路径字段来迁就当前机器。

恢复到回执记载的目录结构时，可以使用独立 financial auditor、原 repair_results.py 及新增 repair_results_v2.py 复算。换目录开展新复测时，应复制记录并生成新的 spec / source binding，以新的目录和输出身份登记；不要编辑原回执或拼接不同 source / spec 的检查点。

两个汇总脚本都先核验旧发布指标的 22 个字段逐值一致。原 repair_results.py 接收原三个修复组，继续生成 RESULTS.json / RESULTS.md；新 repair_results_v2.py 的最终输出要求四个明确的 `--case`，生成 FINAL_RESULTS.json / FINAL_RESULTS.md。每个 `--case` 依次提供名称、REGISTRATION.json、完整 receipt、配对 full-audit-summary.json 和公开 commit URL；只允许 full795、金融与路径审计通过的结果，且 URL 必须是该组登记的完整提交身份。

最终汇总传入实际通过 full795 的 margin-only 重试登记及完整回执，`--case` 名称仍为 `margin-only`；当前两个失败目录均不得使用。各组末段编号以实际完整回执为准，不能预设 segment002 或 segment003 即表示完成。先将 `CQ_MARGIN_CASE_DIR` 设为最终完整重试的登记目录，将以下四个 `CQ_*_RECEIPT` 变量设为各自真实、已审计的完整回执路径，再执行；此命令仅汇总本地证据，不启动账户回放：

```sh
python diagnosis/repair_results_v2.py \
  --case margin-only "${CQ_MARGIN_CASE_DIR:?set the accepted full795 margin case directory}/REGISTRATION.json" \
    "${CQ_MARGIN_RECEIPT:?set the audited complete margin receipt path}" \
    "${CQ_MARGIN_CASE_DIR}/full-audit-summary.json" \
    https://github.com/geniusgrok/coinquant/commit/06206ac0c5383fb009df8bac20601cd9e2d9b004 \
  --case book-v2-only diagnosis/replays/book-v2-only/REGISTRATION.json \
    "${CQ_BOOK_RECEIPT:?set the audited complete book receipt path}" \
    diagnosis/replays/book-v2-only/full-audit-summary.json \
    https://github.com/geniusgrok/coinquant/commit/37bfc8a833d1ff3c0992842ce363758a47b1d06f \
  --case combined-v2 diagnosis/replays/combined-v2/REGISTRATION.json \
    "${CQ_V2_RECEIPT:?set the audited complete v2 receipt path}" \
    diagnosis/replays/combined-v2/full-audit-summary.json \
    https://github.com/geniusgrok/coinquant/commit/3561728dab351d269b19b107fb4fbabb2ac1f674 \
  --case combined-v3 diagnosis/replays/combined-v3/REGISTRATION.json \
    "${CQ_V3_RECEIPT:?set the audited complete v3 receipt path}" \
    diagnosis/replays/combined-v3/full-audit-summary.json \
    https://github.com/geniusgrok/coinquant/commit/230a61daade55d7d80de56f61aae24e660fb3a40 \
  --out diagnosis/FINAL_RESULTS.json --markdown diagnosis/FINAL_RESULTS.md
```

REPAIR_RESULTS_VERIFICATION.json 保留原汇总对真实 smoke、错 head 和退役 v1 名称的拒绝证明。repair-results-v2-preflight-verification.json 保留 v3 公开冻结前的占位拒绝和计算函数保持证明；其中的占位值及脚本 SHA 属于当时状态，不冒充填入公开 v3 head 后的最终执行验证。最终结果各自绑定实际使用的脚本字节。脚本核对 URL 的具体提交身份，在线 GitHub 可达性由独立公开提交读回记录证明。

原 2×2 与新增 v3 的绘图分别使用：

```sh
python diagnosis/plot_repair_results.py --results diagnosis/RESULTS.json --out-dir diagnosis/figures
python diagnosis/plot_repair_results_v2.py --results diagnosis/FINAL_RESULTS.json --out-dir diagnosis/figures-v3
```

原绘图读取四份回执；v3 绘图读取控制组及四个修复组的五份回执，并以不同标签保留 v2 与 v3。若相同原件的本地路径不同，可重复传入 `--receipt ARM PATH`，其中 ARM 为 `control_2_0_0`、`margin-only`、`book-v2-only`、`combined-v2` 或新增的 `combined-v3`；SHA 和字节数仍须与对应 RESULTS / FINAL_RESULTS 完全一致。绘图只使用 `financial.daily`，精确复核期末权益、CAGR 和日末回撤后才输出。日末图不使用盘中路径 MDD 或高频 close-observation MDD 替代。原 figures/ 与新 figures-v3/ 均保留，并保存各自输入身份和图表校验记录。

## 再运行经济实验

只使用不可变公共源码和原 v2 producer；driver SHA 为 `9b5ee3aea3a4f977b0b20c7b25e4a81ecdc5b7b188d9f26a3e119e03101f5413`。原 parser、九个研究模块、warmup、宏观 vintage、规则、日程、费用和 FX 均已绑定。原 run_pair.py 保留；本轮实际逐段启动用 run_one_segment.py，每次仍执行原定最多 540 秒的完整 driver 段落，FULL_COMMANDS.jsonl 记录每次真实命令与 launcher SHA。

每组单独新建模拟账户状态，离线 UID 12000 及正常账户锁保持原样，组间串行。开始前先对原最早六会话进行源码对应的 smoke 与独立审计；v3 必须使用新源码对应的 smoke，不能把 v2 冒烟当作 v3 通过。仅路径元数据改变的保证金重试复用了相同不可变源码的已通过 smoke，单独保存 SMOKE_REUSE.json。每段结束后保留实际 SQLite、报告前缀、路径证据和检查点，以该次登记和原回执恢复；`can_resume=true` 的安全分段仍须全部恢复检查通过，才能续下一段。不存在完整安全回执时，不截断报告或回滚账户来制造可恢复状态；已前进的中断状态保留，另行登记重跑。

该研究运行器不是实盘验收入口。默认生产 run 不内置“一键复现这些历史收益”的研究框架。原生 Demo/主网访问与历史模拟分开；公开数据和离线执行不能证明真实成交或未来收益。

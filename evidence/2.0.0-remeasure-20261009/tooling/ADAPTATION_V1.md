# 2.0.0 默认运行时配对重测：离线工具适配

本目录是独立的研究工具，生产仓库与两个运行时目录只读。这里的验证证明接口兼容、记账一致和断点续接一致；没有启动 795 次完整历史回放，也不包含新的年化或回撤结论。

## 来源与固定身份

以已恢复的 PR72 最小复现包为基础，原 driver SHA-256 为 `24883a9cc315ad3a23002809749fe52d8b49c9a6d10fb02d853d2bb4a0458be2`。未冒充仍未恢复的 PR74 producer。运行 Python 3.12.14，与恢复包记录一致。

| 身份 | 固定值 |
| --- | --- |
| 新运行器版本 | `coinquant-default-runtime-paired-replay-v1` |
| 新 driver SHA-256 | `43b855b5df5803168b02e2e925394cfaaa8c5e07a76034fd804f81c35f40d370` |
| previous 运行时 | `79a334b2d776be2dbe8756f3a616697f9403982e` |
| current 运行时 | `162ee7138952925ffafbc9b68be7c754c0c0a6c3` |
| previous 运行时与工具组合指纹 | `6d58018010102265d786dca32cc7e13b413df18e43560dfab21d37cc1abb8468` |
| current 运行时与工具组合指纹 | `35038c0bab5d520f3fed6d6b66437ef1dfecaee159315ec497ee6410927bfc53` |
| 原 795 次日程 SHA-256 | `c21b4fcfe3cb12fb062bb01d3c3591aa0ee8c65db9e9afde3c26b1bcdc2ac28e` |

每个运行时的 19 个生产 Python 文件均已通过 `current_source(spec)` 与独立冻结文件清单逐项核对。代码身份、研究模块身份、登记说明、日程和输入身份继续进入每段回执与 checkpoint 的绑定。

## 改动

1. **显式登记运行时和原生默认风险。** `CQR_RUNTIME_ROOT`、`CQR_RUNTIME_SHA` 必须与 `runtime_roots`、`runtime_heads` 中恰好一个 arm 对应。生产源码必须与该 arm 的 `source_files_by_arm` 相等。`risk_by_arm` 只接受 `capital_limit_usdt`、`max_stop_loss_fraction`、`stop_slippage_fraction` 三个字段，构造的 `Config` 必须等于该生产源码直接构造的默认 `Config`。previous 使用 `null/.49/.01`，current 使用 `null/.10/.01`。reader 绑定同一个 Config 的损失与滑点参数。
2. **让逐笔成交报告反映已经发生的记账。** `_apply_close` 返回原有钱包与收入账刚记录的 realized PnL；`_trade` 同步写 `commissionAsset=USDT`、`commission`、`realizedPnl`。完整平仓重置入场价前保留本次 PnL。开仓 PnL 为零。没有再次扣费或增加新的账户现金流。
3. **提供条件单原生归属所需字段。** 创建条件单时写入 `algoType=CONDITIONAL` 和当时模拟时钟的 `createTime`，后续查询保留原始创建时间。父子单 ID、原触发和全平路径沿用恢复版本。
4. **保留嵌套请求的传输身份。** 生产请求在必要时会通过嵌套 GET 对时，研究器的 `_inflight` 在 `finally` 恢复前层身份；生产请求检查和对时本身正常执行。
5. **升级 checkpoint 版本。** `default-runtime-research-exchange-checkpoint-v2` 显式登记 reader 的 `loss_fraction`、`slip_fraction`。沿用原 SQLite、正常状态锁和账户锁、归档文件身份、订单对象索引、`_path_audit` 与连续 session journal。旧版本检查点不能冒充新版本检查点。
6. **保留同一观测序列。** 根代理增加的 `complete_perp.PATH_TRACE` 只在原 `_record` 完成后输出一行，字段为 `[seq, stamp_ms, kind, equity_cny, known_path, q, entry, wallet, margin, fx]`。金额为字符串，不额外取得行情或生成 mark 值。driver 在 start 构造 venue 前连接流，在 resume 恢复完成后连接流，因此恢复 constructor 的临时初始点不会混入路径。

`session_market.py`、`data_loader.py`、`dfii10_history.py`、`unified_perp.py`、`comparison_report.py` 与恢复包保持原始字节。价格、撮合、手续费率、读写延迟、模拟时钟推进、资金费时间、缺口规则均未因本次适配而调参。策略通过选定生产模块直接运行。

## 分段路径与回执

每段独占创建 `scratch/path-traces/segment-NNN.jsonl.gz`，不覆盖已有文件。关闭后 driver 流式检查连续序号，按原四字段 `[stamp_ms, kind, equity_cny, known_path]` 重算 rolling hash，并与未改变的 `_path_audit` 边界比较。

`path_trace` 包含 `path`、`bytes`、`sha256`、`first_sequence`、`last_sequence`、`points`、`sequence_before`、`sequence_after`、`rolling_before`、`rolling_after`、`trace_rolling_after`、`verified`、`segment_failed`。安全停机后没有新增观测的段可以有 `points=0`、首末序号为 `null`。失败段保留现有文件并标记失败，不允许继续。

恢复前校验上一段路径文件的 SHA、字节数，以及其结束计数/rolling hash 与恢复 checkpoint 中的边界一致。完整独立审计由父目录审计器承担。保留路径能重新计算原模拟观测的回撤，不会把 OHLC 极值顺序、print/mark 代理和 hindsight 缺口界限升级成真实逐笔交易所路径。

## 最小验证

`test_compat.py` 使用小型合成 CSV ZIP，通过原 `TradePrints` 解析器、真实 `Market`/`PriorFX` 和所选生产模块验证五类行为：

| 类别 | 验证结果 |
| --- | --- |
| 长、短 IOC 分段入场、追加、部分减仓和全平 | 逐笔费用/PnL 与钱包和收入账闭合 |
| 条件单创建、触发、父子归属及终态归档 | 生产公共读取路径通过，创建时间稳定，子单成本闭合 |
| 实际 60 秒虚拟生产会话 | 入场、原生整仓止损/止盈、cleanup verified、pending 0；reader 风险错配在 I/O 前拒绝 |
| 原 checkpoint JSON 往返及继续 120 秒 | 重新生成快照相等，全部恢复字段与未中断实例相等 |
| checkpoint 依赖和持久状态篡改 | 拒绝错误摘要、改动日程、观察归档和 SQLite |

previous 与 current 两臂均已验证通过。当前臂首轮有一个测试报告字段读取错误，修正测试断言后定向复验通过；没有为通过测试改变生产默认值或研究算法。

`test_trace.py` 另验证初始点、实际短会话、driver checkpoint/restore、分段路径序号与 rolling hash 续接、与未中断路径审计完全相等、旧文件不覆盖，以及篡改路径拒绝恢复。两臂均通过。

所有涉及 `State` 的测试保留正常 HOME 和锁，使用合成 UID `12017` 与独立临时目录；完整研究仍登记 UID `12000`，由根任务串行运行，不能通过修改 HOME 并行使用该账户身份。

重验示例（在本目录执行，current 臂）：

```bash
CQR_RUNTIME_ROOT=/workspace/scratch/4a60782c7dbc/coinquant-remeasure-2.0.0/current \
CQR_RUNTIME_SHA=162ee7138952925ffafbc9b68be7c754c0c0a6c3 \
PYTHONPATH=/workspace/scratch/4a60782c7dbc/coinquant-remeasure-2.0.0/current:/workspace/scratch/4a60782c7dbc/coinquant-remeasure-tooling \
python -m unittest -v test_compat test_trace
```

previous 臂改为对应 `previous` 路径和固定 `79a334b...` SHA。经济研究的输入恢复、spec、首次六次 smoke、完整 795 次原窗口运行、独立财务与路径审计、年化/日收盘指标和 GitHub 更新由根任务完成。历史 CAGR 的年长口径是 365.2425 天。

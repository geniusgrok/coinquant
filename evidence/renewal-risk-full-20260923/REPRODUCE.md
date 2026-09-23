# 复现与原件

从本次合并源码恢复，按 originals.json 下载并校验完整依赖；解包只恢复数据，不覆盖当前源码。

- `bounded`：旧 bounded execution 包，内含 `inputs/`、`old-controls/`、`evidence/`。
- `sx60`：旧 sustainable capital exit 包，内含 `exit-minutes/`。
- `h60`：H60 完整开发原件，内含 `results/H60-development/`。
- `new-data`：保存的 M60 development/protection minute、mark recheck、warmup probe 原件，分别解包到不同子目录以保留各自 RECEIPT。
- `full-minutes`：本轮 390 份新官方分钟档案包。

在仓库根目录执行以下命令。`OUTPUT` 必须是不存在的新目录，绝不能覆盖已完成账户；只有要独立复核时才运行，不是下一轮默认必跑动作。

```bash
python -m research.renewal_risk_replay \
  --bounded-originals "$BOUNDED" --sx60-originals "$SX60" \
  --h60-originals "$H60" --new-data "$NEW_DATA" \
  --new-data "$FULL_MINUTES" --full-window --output "$OUTPUT"
```

本次配对 SX60 对照直接复用 HR60 `prepared_inputs(..., full=True)` 返回的相同输入，调用 `research.conditional_hold_replay.run_account(..., control=True, full=True)`；不是 H60 重跑。保存的两个 invocation 文件 input_identity 相同，均有 795 调用；原协议摘要不变。

只有输入准备发生修改。账户引擎、资金与风险公式等测量源码字节与已保存最终 HR60 开发相同。完整账户包保留两次调用、权益/决策/订单/执行轨迹、独立审计和测量源码。minute 包保留 ZIP、官方 CHECKSUM、每日下载审计与输入重建核验。

测量属于冻结代理成本和固定 CNY/USD 估值口径。完整历史动态汇率、USDT折价、费率/风险档位和原生交易所闭环尚未资格通过。

Git 中较大的 COVERAGE_PLAN.json 与 INPUT_PREFLIGHT.json 使用无损 `.json.gz` 保存；解压后与完整账户包中的原文件逐字节一致。EVIDENCE_MANIFEST.json 描述完整账户包内容，不是 Git 目录清单。

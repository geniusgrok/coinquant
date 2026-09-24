# 只读账本筛查复现

先按 `NET_EDGE_INPUTS.json` 核对三个完整原件的长度和 SHA-256，再从 `COINQUANT_M60_COMPLETE_20260923.zip` 的 `dependencies/COINQUANT_SUSTAINABLE_CAPITAL_EXIT_20260922.zip` 解出 `results/accounts/SX60-development` 与 `results/accounts/SX60-full`；从 PF55 和 RR 原件各自的 `replay/UC4-PF55-development-r01`、`replay/UC4-RR-development-r17` 解出有效账户。中断的 `.partial` 不用于本次分析。SX60 单文件与内层 `MANIFEST.json` 核对，RR 的 `result.json`、`equity.csv.gz` 与 `../recoverable-risk-20260924/ORIGINALS.json` 核对。把四个账户目录置于独立临时目录，不要把市场 ZIP 或原账户复制到源码仓库。

```bash
python3 evidence/net-edge-screen-20260924/screen.py \
  /path/to/SX60-development /path/to/SX60-full \
  /path/to/UC4-PF55-development-r01 /path/to/UC4-RR-development-r17 \
  > /path/to/NET_EDGE_SCREEN.json
sha256sum /path/to/NET_EDGE_SCREEN.json
```

复现脚本只读取已有连续账户的已成交与实际平仓记录；其输出哈希在 `NET_EDGE_INPUTS.json` 的 `derived_json_sha256`。输入路径只影响 `account` 的目录名，四个目录请使用上述固定名称。脚本对每个账户校验平仓净额与初末权益误差不超过 `1e-15` USDT。没有独立事件交易模拟，没有新策略回放、资金复用或账户重置。

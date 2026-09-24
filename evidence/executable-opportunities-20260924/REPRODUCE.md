# 复现独立事件研究

前提是从 `NET_EDGE_INPUTS.json` 指定的完整 Library 原件按 SHA-256 核验并解开：

- `libfile_7579b3804a4c8191b16800c40c81d5df`：`COINQUANT_M60_COMPLETE_20260923.zip`，184635190 字节，SHA-256 `ca1dab14d2501a31d2122bc22d3001c34392033a6e9de786a6727886b13c5a1e`；其中的 `dependencies/COINQUANT_BOUNDED_EXECUTION_20260922.zip` 解到 `bounded`，`dependencies/COINQUANT_SUSTAINABLE_CAPITAL_EXIT_20260922.zip` 解到 `sx60`。
- `libfile_025da54ab3a8819185df560eb62f5e5a`：`UC4_PF55_DEVELOPMENT_REJECT_20260924.zip`，4197340 字节，SHA-256 `769e3517cdbbedf6581ac313224285f63e8ca215099bce3fc633fe72c014c4ad`，解到 `pf55`。
- `libfile_9f4c5e3529d481919b25437d394e2f4b`：`COINQUANT_RR_DEVELOPMENT_REJECT_20260924.zip`，36488329 字节，SHA-256 `c769a815543f4c52c58b46fca0cf9dcdf2b54f5ede12dd44cbf23e051f7f885e`，解到 `rr`。

保留输入目录结构。必须校验 `NET_EDGE_INPUTS.json` 的账户文件长度和摘要；使用完整有效账户 `SX60-development`、`UC4-PF55-development-r01`、`UC4-RR-development-r17`，不要取 `.partial`。已有官方 1m 档和 CHECKSUM 可以从 bounded 原件、sx60 的 `exit-minutes`、RR 的 `evidence/recoverable-risk-20260924/minutes`、仓库 `evidence/unified-channel-20260924/minutes` 读取；新档案以 `--minute-root` 增加，并保留来源及 SHA。

在本仓库根目录运行，`../inputs` 为解出的工作目录；命令中的最后一个 `--minute-root` 指向新增的官方分钟档（若存在）：

```bash
python3 -m research.executable_opportunities \
  --bounded ../inputs/bounded --sx60 ../inputs/sx60 \
  --pf55 ../inputs/pf55 --rr ../inputs/rr \
  --minute-root ../inputs/bounded/inputs \
  --minute-root ../inputs/sx60/exit-minutes \
  --minute-root ../inputs/rr/evidence/recoverable-risk-20260924/minutes \
  --minute-root evidence/unified-channel-20260924/minutes \
  --minute-root ../inputs/new-official-minutes \
  --output ../out/executable-events
python3 evidence/executable-opportunities-20260924/summarize.py ../out/executable-events
```

当前保存的第一次有效执行没有 `new-official-minutes`。运行前确保 `--output` 不存在，程序拒绝覆盖。其有效原件在研究证据包中，`EVENTS.jsonl` 的 SHA-256 为 `5aa6a8291c6df1ca0ef040132071a37314fddabc3b96174873f37581de2ac91f`；复现如新增分钟档，应给新结果独立目录与新的证据身份，不能冒充相同输出摘要。`MISSING_MINUTES.json` 是**第一轮**依赖，不保证补齐后不会出现新的保护小时。软件环境 Python 3.13，研究代理限定在历史快照与离线回放。

Git 研究分支为完整保全将两个文本原件分成确定性小块。运行 `python3 evidence/executable-opportunities-20260924/reassemble.py ../restored-events`，脚本逐块核对偏移、长度及 SHA-256，再核对总长度和原件 SHA-256；完整的 ZIP 恢复包也单独保存原件。不得把任一块当作可独立解读的交易文件。

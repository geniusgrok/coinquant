# 开发账户恢复

从 `ORIGINALS.json` 核对旧基础依赖与本轮完整原件的字节数、SHA-256。解压本轮原件至独立目录；其中 `replay/UC4-RR-development-r17/` 是完整有效账户，`r02` 至 `r16` 是未通过分钟覆盖的中断轨迹；不得从任一部分CSV续算。14个新增官方日档、CHECKSUM及收据在原件的 `evidence/recoverable-risk-20260924/minutes/`，不必将市场二进制文件长期复制到源码仓库。

将原 M60 依赖包内的 `COINQUANT_BOUNDED_EXECUTION_20260922.zip`、`COINQUANT_SUSTAINABLE_CAPITAL_EXIT_20260922.zip` 分别展开为 `bounded`、`sx60`；再展开四份 M60 分钟包为 `m60-development`、`m60-protection`、`m60-mark`、`m60-warmup`。使用仓库中 `evidence/unified-channel-20260924/minutes` 及本轮原件中新增分钟目录。只在冻结源码树 `d49546d33e5def59f8891a08359ee8494092718f` 上跑同样的 468 次调用：

```bash
python3 -m research.channel_core_replay \
  --bounded-originals ../replay/bounded --sx60-originals ../replay/sx60 \
  --new-data ../replay/m60-development --new-data ../replay/m60-protection \
  --new-data ../replay/m60-mark --new-data ../replay/m60-warmup \
  --new-data evidence/unified-channel-20260924/minutes \
  --new-data ../RR-original/evidence/recoverable-risk-20260924/minutes \
  --coverage-hours evidence/recoverable-risk-20260924/COVERAGE_HOURS.json \
  --recoverable-risk --output ../replay/UC4-RR-development-fresh
```

核对原件中的 `r17.invocation.json` 输入身份、协议摘要、源码身份，以及 `result.json`、`equity.csv.gz`、账本和风险审计。上述命令只运行离线经济代理，不连接交易账户。Python 版本与历史 Binance 数量规则快照仍应作为代理限制记录；不把代理账户当成生产交易资格。

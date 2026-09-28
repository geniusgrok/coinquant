# Coinquant 当前状态（2026-09-28）

## 系统

Binance BTCUSDT U 本位永续，单账户、单向逐仓、交易所20×。手动启动一个有限会话（默认300秒、每5秒轮询），会话内反复“核对→决策→执行”，超时或中断后在120秒预算内收尾；没有后台进程。生产路径：`CLI → session.run → Campaign → Lifecycle → Binance`，持久化意图、成交、资金流水与每轮观察都在状态目录的 `intents.sqlite`。

默认模型 SX60＋DFII10：4小时 impulse-hold 多头主信号，风险尺度7.5（`coinquant.campaign.PRIMARY_RISK`）；空仓且主信号无可执行多头时，DFII10 近值较第20个前值下降≥0.25个百分点触发3.6尺度宏观多头，整笔持仓止损损失≤入场权益3%。默认模型不开空。

`run --execute` 在凭据和网络访问前拒绝；资格 `NOT_QUALIFIED`。

## 经济测量（测量器 M7）

`python -m research.rebuild P7` 在 `research.session_exchange.SessionExchange` 上运行同一个 `session.run`/`Lifecycle`，冻结795个会话起点（`research/session_schedule.json`）。2020-01-01至2026-09-20（右端不含），人民币10,000元：

| 场景 | 期末人民币 | CAGR | 连续 MDD |
|---|---|---|---|
| 基准 P7 | 5,228,630 | 153.86% | 44.73% |
| 手续费 +50% | 4,563,859 | 148.77% | 45.00% |
| 出场滑点 ×2 | 4,629,101 | 149.30% | 45.09% |
| 深度取用 10% | 4,475,825 | 148.05% | 44.73% |
| 随机跳过 20% 会话 | 1,092,311 | 101.08% | 44.68% |
| 缺席序列 / 21 天空窗 | 5,228,630 | 153.86% | 44.73% |

2020-01-19 13:09–13:37 UTC 缺29分钟官方标记价而账户持仓；所有者2026-09-28接受以实测标记/成交偏离作边界（`path_complete=false`）。`economic_qualification` 为 `NOT_MET`：基准达标，三项成本压力略低于150%。M7 与 M6 的 MDD 相同；少读的保护路径释放了本地请求权重，使部分补单提前，终值低0.04%。每份原件记录源码提交（`a6892b3`）、输入文件摘要、资金费流水与每日权益。口径与各轮修正见 `research/redesign-PROTOCOL.md`，结果与测量局限见 `evidence/rebuild-20260927/RESULT.md`。

## 未完成

- 原生验证：真实成交后保护建立的时间窗口、重复 close-all 接受行为、超时/迟到成交、交易所断连、明确拒绝错误码与文档规定失败的503、-2013 查询与签名过期（recvWindow）后不再接受的语义、保证金历史结算、Demo 环境语义（`evidence/bounded-session-20260926/RESULT.md`）。先在 Demo（`environment: demo`）验证，再在单独授权的专用小额余额（`capital_limit_usdt`）上验证；需要指定账户和当次明确交易授权。
- 默认模型只做多，没有开空路径。
- 成本、滑点、深度压力下 CAGR 比150%低0.7–2.0个百分点；没有前向证据。
- 超过成交历史（约3个月）与资金流水窗口（约88天未观察）后恢复只能返回未知；没有外部归档导入入口。实盘连续权益与 MDD 没有可核验的重建。
- Windows 等无系统时区库的环境需要 `tzdata`。

## 数据

行情 vision 文件在 `/data/coinquant-market`（`python -m research.session_market --root ...` 下载并校验），逐日 aggTrades 在 `/data/coinquant-prints`，缓存在 `/data/coinquant-prints-cache`；三者不入库。DEXCHUS、ALFRED DFII10、2019年12月预热行情、合约规则随仓库提交并按 SHA-256 校验。

## 仓库

只保留当前版本。旧 Bybit/反向合约实现、稀疏调用规格与抽签、历史候选研究及证据已于2026-09-28删除，需要时从 Git 历史 `3e9a696` 及以前取回。

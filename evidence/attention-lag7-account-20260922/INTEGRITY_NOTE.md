# 运行完整性说明

- C0、C1、C2_lag7 和 L3.6 的发布版 `orders.csv.gz`、`equity.csv.gz`、`decisions.csv.gz` 均已通过 gzip CRC；四个账户的独立现金账本最大误差均为 0 USDT。
- L3.6 的三条**发布版**流与已核验 `payoff-baseline` 的解压 SHA-256 完全一致：orders `aee6c514ffad9794f6df771d5f4a2d09d89a3f1343165eb2035176069771b111`，equity `f498acc2f4e3f845b9e9074d13af326a09b0f9f4ee971e6ea62f8b80206f8a40`，decisions `4c0986cc566ac6f9857f9849a8343253f787e1e23802c4f3d3caf56c0b318658`。
- L3.6 目录还保留了三个未发布的 `.partial` 残留：orders/decisions 为零字节（SHA-256 均为 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`），equity 为 558,559 bytes（SHA-256 `85be91c414ad2d09a4de477a33b54a6372b8f15e22237250a25c1c422ce8108a`）且 gzip CRC 失败。它们不参与任何指标、审计或上述等价性判断，也不覆盖发布版。
- 同一源码、同一缓存输入在临时隔离目录中完整重放一次没有生成 `.partial` 残留；当前未能把残留归因到可重复的账户逻辑缺陷。因此不以它为由改经济规则或重跑/调参。残留保留作诊断证据，而 C2 已在无关的 CAGR/MDD 条件上失败。

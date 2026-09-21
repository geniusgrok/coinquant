# Pancakequant

个人使用、按需运行的 Binance BTCUSDT U 本位永续项目，不运行守护进程。
**改造未完成，当前入口仅支持账户观察，不能自动交易，也没有通过经济验收的生产模型。**

## 当前可用功能

`python -m pancakequant` 和 `main.py` 使用同一 Binance 入口。`status` 读取并核验
账户 UID、单向/单资产/逐仓 20x 配置、余额、持仓、普通订单、条件订单与近期成交，
进行有界一致性检查，再保存报告并退出。不会修改账户设置。

适配器固定使用 Binance 官方 API 主机、GET 请求与签名；拒绝重定向。超时、冲突或
截断结果不会被解释为空账户。订单恢复组件可按稳定客户端 ID 查询母单及实际子单，
但尚未接入完整写操作恢复。近期成交不等于完整历史。

当前 `run` 完成同样的账户观察后报告 `blocked`，原因是没有已验收模型与交易生命周期。
`run --execute` 在读取凭据和调用网络前直接拒绝。旧 Bybit 不再由默认 CLI 实例化，
旧配置也不能触发旧交易所。旧模块暂为历史研究和离线回放保留，不代表继续支持它交易。

## 使用

Python 3.13，标准库，无生产第三方依赖。

```sh
cp config.example.json config.json
python -m pancakequant status --config config.json
```

填写 Binance `account_uid` 和持久化的 `state_dir`。凭据仅从
`PANCAKEQUANT_BINANCE_KEY`、`PANCAKEQUANT_BINANCE_SECRET` 读取，不写入配置。
当前观察器连接真实 Binance 只读 API；**没有测试网自动回退或真实交易能力**。
本任务未读取真实账户，未使用真实凭据，未进行交易或修改账户设置。

同一账户只在一台机器上运行。状态目录绑定 Binance、BTCUSDT 与 UID，并有本地互斥锁。
标准输出为 JSON，标准错误为摘要；成功观察后报告保存为状态目录下 `latest.json`。
`blocked`、`unknown` 等状态退出码为 2，不把报告生成当作交易成功。

## 研究状态

冻结目标：人民币 10,000 元，2020-01-01 UTC 至 2026-09-20 exclusive，
CAGR > 200%，完整账户连续 MDD < 20%，交易所杠杆固定 20x，原冻结稀疏人工触发序列。
真实成本、资金费、保证金、强平和 USDT 估值风险必须纳入。当前 `NOT_QUALIFIED`。

已保全 274 份通过检查的 Binance 原生档案，另 4 份月度 mark 档案报告小时缺口，
正在保全异常原件并定位缺失数据。完整历史规则与 USDT 估值仍未闭合。
L1/L2 账户代理实验和 L3/L4 原生开发区预测检验均失败，不能据此宣称盈利。
2024 至终点尚未用于经济模型调参；预测检验不是账户 CAGR/MDD。

研究模块及准确源码、输入身份、失败证据保存在 `research/`、`evidence/`。
旧 inverse 回放不再是当前 CLI 的 `backtest` 命令；它不能作为 Binance 回测入口。
`PROJECT_STATE.md` 是当前恢复入口，`HANDOFF_PROMPT.md` 提供续接约束。

当前分支 `research/on-demand-btc-20260920` 未经经济与必要交易安全验收不得合并 main。
完整历史证据和 Git 历史保留；不使用旧 `.transfer` 恢复包覆盖当前代码。

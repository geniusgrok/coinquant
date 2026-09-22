# Pancakequant

个人使用、按需运行的 Binance BTCUSDT U 本位永续项目。用户主动触发一次运行，完成后退出，不依赖常驻守护进程。

**main 是开发与集成主线，不代表实盘资格。当前执行入口仍阻止写操作，没有通过全部经济与原生安全验收的生产模型。**

## 开发主线与正式目标

2026-09-22 用户明确授权把研究成果合并 main，后续从实时 main 继续开发。此授权取代旧的“经济达标前不得合并 main”，不降低收益目标，也不授权真实交易、Testnet 写入或账户设置变动。历史研究分支及原件保留。

正式目标：初始人民币10,000元，无追加；2020-01-01T00:00:00Z 至 2026-09-20T00:00:00Z，终点不含；成本后 CAGR >=150%，完整账户连续 MDD <50%。仅 Binance BTCUSDT 永续，交易所杠杆固定20x，不等于始终20倍账户敞口。正式验收沿用原冻结稀疏人工调用，并计入费用、滑点、spread、funding、保证金、强平与人民币/USDT估值。

## 当前入口

`python -m pancakequant` 与 `main.py` 共用 Binance 入口。`status` 只读核验账户身份、单向/单资产/逐仓20x配置、余额、持仓、普通与条件订单及成交，然后保存报告退出；不会修改账户设置。

`run` 在观察账户后恢复共享 Campaign 检查点，补齐已完成行情，核对成交归属并生成研究模型与资金数量预览。缺失历史、未知归属、未决订单或未确认保护会阻止新风险；预览不等于成交。

`run --execute` 在访问凭据和网络前直接拒绝。合并 main 不会解除这个阻止，也不会自动将 SX60 替换为默认模型。现有3.6参考/默认路径保持不变。旧 Bybit/OKX 材料仅为历史研究，不会由默认入口切换执行。

## 使用与离线检查

Python 3.13。生产观察路径使用标准库；离线研究依赖见 `requirements-research.txt`。

```sh
cp config.example.json config.json
python -m pancakequant status --config config.json
python -m pancakequant run --config config.json
```

配置填写明确的 Binance `account_uid` 和持久化 `state_dir`。凭据只从 `PANCAKEQUANT_BINANCE_KEY` 与 `PANCAKEQUANT_BINANCE_SECRET` 环境变量读取，不写入仓库或配置。上述命令会访问真实 Binance 只读接口；没有测试网自动回退。

同一账户只在一台机器运行。状态目录绑定交易所、标的与UID并使用本地锁；输出JSON和摘要，报告保存到状态目录 `latest.json`。`blocked`/`unknown` 等返回退出码2，不能把生成报告当作交易成功。

```sh
python -m pip install -r requirements-research.txt
python -m compileall -q pancakequant research tests
python -m unittest discover -s tests -v
```

CI只运行轻量离线检查，不运行经济优化或交易。日常改动采用风险驱动的必要验证，不要求每次重复全套测试和历史账户。

## 当前研究结果与边界

完整历史窗口已经多次使用，不是独立未见数据。下面是保存的历史代理结果，本次源码发布与主线迁移没有重新运行经济账户。

| 完整窗口 | 成本后CAGR | 连续MDD包络 | 期末人民币 |
|---|---:|---:|---:|
| B36，五分钟入场参照 |74.9749%|31.9766%|429,053.61|
| SX60，资金约束与计划退出分片 |102.6262%|39.8851%|1,149,830.31|
| SX60，联合压力 |99.7502%|39.6555%|1,044,528.34|

SX60保留为改进后的研究候选，不是生产启用结果。原件对应的新资金/退出源码已在 `79e18895935de9525d9b78355a87448491f5a6d8` 恢复发布，固定经济源码哈希与Library原件一致。资金修复使用共享 Account/sizing；计划退出研究复用原时间线，不另建交易账本。

已有持仓路径的跳空缓冲核验通过，不意味着任意离线时长安全：21日同率静态持仓预算压力仍有不足。历史费率/风险档位、完整人民币与USDT估值、盘口冲击、原生部分成交/撤单未知/迟到成交与重启恢复仍存在证据缺口。同步回放保护不能替代真实交易所验证。150%收益目标尚未完成。

## 源码、证据与恢复

`pancakequant/` 为共享组件与只读入口；`research/` 为研究驱动；`tests/` 为离线检查；`evidence/` 保存协议、选择、报告及原件恢复索引。完整大型二进制原件在Library持久保存，不宣称全部已成为Git对象。

先读 `AGENTS.md`、`PROJECT_STATE.md`、`HANDOFF_PROMPT.md` 和 `evidence/sustainable-capital-exit-20260922/originals.json`。源码恢复与字节核验见同目录 `SOURCE_RESTORATION.json`、`SOURCE_READBACK.json`。旧报告中“源码未发布”是当时状态，已由恢复提交解决；原经济结果没有改写。

不要用旧 `.transfer` 或任何历史源码快照覆盖当前 main。恢复数据与恢复代码分别核对。后续以实际 main HEAD 为准，保留失败实验，不重复已经完成的等价研究。

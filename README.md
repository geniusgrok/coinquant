# Coinquant

个人使用的 Binance BTCUSDT U 本位永续系统，交易所设置20×，单向逐仓、单账户。手动启动一个有限会话，会话内持续读取真实行情与账户状态、重复判断，超时或 Ctrl-C 后退出；没有后台守护进程。

**当前是工程集成版本。命令行仍禁止真实交易写入：原生交易所接入验证与经济验收均未完成。离线验证通过不等于生产资格。**

## 使用

Python 3.13；生产运行仅使用标准库。

```sh
git clone https://github.com/geniusgrok/coinquant.git
cd coinquant
cp config.example.json config.json
python -m coinquant status --config config.json
python -m coinquant run --config config.json
```

在配置中填写自己的 Binance `account_uid` 和固定 `state_dir`。凭据只从 `COINQUANT_BINANCE_KEY`、`COINQUANT_BINANCE_SECRET` 环境变量读取，不写入配置或仓库。`status` 单次观察；`run` 默认观察300秒，每5秒重新核对，输出和状态目录的 `latest.json` 标明结果。配置只包含四项：

| 配置 | 含义 |
|---|---|
| `account_uid` | 必须与交易所核验的账户一致 |
| `state_dir` | 此账户持续使用的恢复目录 |
| `session_seconds` | 本次运行1～86400秒，默认300 |
| `poll_seconds` | 轮询1～60秒，默认5，不得超过会话时长 |

首次运行会从固定历史起点重建已完成4小时行情；网络不足以完成重建时返回未知，不用短历史冒充完整模型。已存在的仓位必须有可核验的本系统成交归属；禁止把新空目录当作空账户证明。同一账户只允许一台机器运行，本地锁覆盖整个会话。

`run --execute` 在访问凭据和网络之前拒绝；本轮没有实盘或 Testnet 订单，也没有修改账户设置。不要删除这个阻止来试单。

## 已实现的工程路径

`CLI → session → Campaign/资金预检 → Lifecycle → Binance → 持久化意图与原生回读`。

- 当前会话只使用已有4小时 impulse-hold规则、3.6风险尺度，多空沿同一规则和账户路径运行；无候选选择开关。这是工程接线，不是新的合格经济模型。
- 逐轮核对普通订单、条件订单、成交、持仓、钱包和实际保护。状态不明不增加风险，不把请求回执当成交。
- 入场使用有价格上限/下限的限价IOC；未成交时下一轮按新状态重新定价。已有自有普通挂单先撤销并核对终态，随后才可能重新挂单；不会盲目修改未明订单。条件入场与外部订单不在可管理范围，发现后停止新风险并报告。
- 部分成交按实际仓位设置交易所全仓止损/止盈，不按请求数量假设成交。不在持仓中重复加仓；机会失效时只减仓退出。
- 保护调整先建立并回读新保护，再逐一撤旧；未知结果保留恢复记录。保护无法建立时尝试已授权的减仓，并如实报告无法确认的结果。
- 正常结束和 Ctrl-C 后使用最多120秒收尾预算，禁止新入场，清理自有入场余单，核验实际持仓保护。持仓保护保留在交易所。强杀、断电和断网不可能保证收尾成功，下一次启动必须恢复核对。

网络写入与保护建立不具原子性。原生成交后保护间隙、重复close-all接受行为、真实撮合与迟到成交仍待受控原生验证；详见 [工程验收记录](evidence/bounded-session-20260926/RESULT.md)。

## 必要验证与回放

```sh
python -m pip install -r requirements-research.txt
python -m unittest discover -s tests -v
python -m research.session_replay TAPE.json --state-dir NEW_REPLAY_DIRECTORY
```

接口事件回放使用**同一个生产会话、决策和执行器**，在每个请求精确匹配后才释放对应响应。它验证调用时序与状态恢复，不是CAGR/MDD账户或历史成交模拟。测试不访问交易账户；CI只有一个Python 3.13离线任务、10分钟上限。

历史多候选经济回放保留在 `research/`，旧Bybit执行/配置/反向账户实现隔离在 `research/legacy/`，生产入口不会导入。已有大型研究原件及恢复脚本不删除；旧证据绑定原源码，不冒充本次工程版本的新结果。

## 尚未完成的交付门

正式经济目标不变：2020-01-01 00:00 UTC至2026-09-20 00:00 UTC，右端不含；人民币10,000元、不追加；成本后CAGR≥150%、完整连续账户MDD<50%，纳入实际时序、费用、资金费、保证金、强平及人民币/USDT估值。本轮不运行经济验收，不改变旧冻结调用序列。

旧稀疏回放与新的有限会话运行方式不同，历史固定汇率/成本与成交代理不能直接作为新路径的验收证据。原生工程资格和经济资格分别取得后才能启用生产。

当前恢复入口：`AGENTS.md`、`PROJECT_STATE.md`、`HANDOFF_PROMPT.md`。

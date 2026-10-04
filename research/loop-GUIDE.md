# BTC收益与联合风险决策闭环

两套独立运行系统仍为Spotquant现货长仓/现金与Coinquant默认长仓合约；本轮全部为有限研究和只读方案。没有私人账户调用、下单、转账、默认策略晋升。登记规则在任何新筛选前提交于loop-spec.json。

## 已实现的完整路径

五信息族先按实际接收时钟资格检查，再匹配真实可作用BUY和成熟成交篮子。Spot按卖出袖套所有权FIFO扣除真实BTC/USDT佣金，未售余量按实际出售比例计成本；Coin按完整平仓campaign归集真实盈亏、佣金和资金费。独立区间、覆盖、两半样本、同期BTC、前20日动量/RMS及Coin真实可用DFII10控制均满足时才允许`ACCOUNT_ENTRANT`。条件通过也只表示允许比较独立账户，不能把现金归因相加当作候选净值。

原nine_alpha.screen增加可选的真实成熟账户入口；不提供账户时保留原资格筛选。`loop_alpha`提供未来成熟账户manifest入口，重新核对成交/收入/外汇/期末钱包和固定资金，不接受调用者的PASS代替计算。Coin的nine_perp变体只记录模型已经读取的真实DFII10，不增加请求；主信号未读取宏观值时控制仍缺失。

三个后备alpha分别实施：两日持续现货主导价格发现（新机会与完全镜像的原BUY75%两种表达）；已提前实际接收的CPI日历后下跌修复；原有限会话IOC失败/部分成交的20秒限价再核对余量方案。七日价格筛选扣登记费用，但不模拟盘口或证明实际收益。没有队列证据不能用K线触价制造maker成交。

三个后备beta分别实施：因果共同净值高水位的10%触发/5%恢复回撤刹车（新Coin预算半额、已持Coin确认目标及requested上限）；近30日期权绝对IV预测下一七日风险，只有两半预测损失均优于已知20日RMS才准入；真实止损价格/数量与同钟深度、跳价相对已有10%gap/1%资金费准备金的缺口检查。风险计划无订单权限，不会扩大仓位；未知所有权、时钟、保护或盘口阻止新增风险。

六个原真实账户对不再重跑。共同UTC收盘、共同分钟估值和保守分钟路径包络均由原成交/收入重建，期末Spot现金/BTC、Coin数量/权益必须一致。Spot仍是原high-before-low日线路径，Coin是原官方mark分钟；持仓时缺失mark则上界未知。新接收的两个Spot一分钟月只做原固定成交的估值敏感性，不代表这些成交会在真实价格下发生，也不代表原生连续MDD。

## 本轮操作

复现使用冻结producer或相同受保护Python字节，不能把后来merge HEAD说成原producer。所有输出使用新路径，原失败/负结果不覆盖。仅第一次需要解析小行情；相同原始ZIP/校验文件元数据、解析依赖和解析结果hash匹配时复用缓存。原14.8GB逐笔库不扫描/复制。

```sh
python3.13 -m research.loop_data --out /workspace/btc-decision-loop-20261004/artifacts/public
python3.13 -m research.loop_routes \
  --joint evidence/btc-nine-20261004/joint \
  --spot-market /tmp/spotquant-market --coin-market /tmp/coinquant-market \
  --fx /workspace/starquant/data/usdcny_frankfurter.json \
  --schedule /workspace/coinquant/research/session_schedule.json \
  --cache /workspace/btc-decision-loop-20261004/artifacts/market.json.gz \
  --public /workspace/btc-decision-loop-20261004/artifacts/public \
  --receipt-history evidence/btc-nine-20261004/public \
  --inherited evidence/btc-persistent-20261004/public \
  --etf evidence/btc-continuous-20261004/public \
  --at-ms ACTUAL_RECEIPT_CLOCK --out NEW_SCREEN_PATH
python3.13 -m research.loop_accounts --screen NEW_SCREEN_PATH \
  --schedule /workspace/coinquant/research/session_schedule.json --out NEW_PLAN_PATH
```

交付已经保留本轮接收和筛选结果；不要为了复现又下载/重测。公开请求严格5次上限/每次5秒，不重试或换主机。本轮最多24个新独立钱包、每候选最多2窗口/每钱包40个原启动、总账户1800秒；零入围时账户进程/新会话/795重放均为零。

`loop_accounts`只选择实际合格事件各原登记时代最早季度，不按利润挑窗口。三组baseline/uniform25/candidate都必须是真实独立钱包；通过`--account-manifest`接收SHA绑定原始gzip，核对资金和成交，重新计算会话观察回撤/实际买入变化并执行原登记风险财富门槛。两个窗口缺一、重复或无实际改变均不能通过。不能把研究方案当成已经运行的账户；具体新机制只有入围后才启用原有限会话适配并生产账户。

## 后续真正有新证据时

成熟收益入口：`python3.13 -m research.loop_alpha --manifest ACCOUNT_MANIFEST --spot-market ... --coin-market ... --cache NEW_OR_APPLICABLE_CACHE --history RECEIPT_FOLDERS --inherited OPTION_RECEIPT_FOLDERS --etf ETF_FOLDER --at-ms ACTUAL_CLOCK --out NEW_RESULT`。manifest为`{"spec_sha256":"登记hash","accounts":[{"file":"原始配对gzip相对路径","sha256":"原始hash"}]}`，保留真实producer/period，最多12对，不覆盖本轮固定输入。

只读方案入口：`python3.13 -m research.loop_admission --route drawdown|implied|protection|execution --input PACKET --out NEW_PLAN`。JSON的now_ms不得来自未来。drawdown输入两个独立accounts、已知known_closes、可选旧state与requested_btc；返回新state由调用者持久保存，不能重置高水位。implied输入iv/prior_rms/available_ms，只计算不扩仓因子，不能绕过预测门槛。protection输入accounts/books，每个stop需confirmed/symbol/SELL/receipt_ms/stop_price_usdt/quantity_btc，book需available_ms/executable_bid_btc/confirmed_jump_fraction。execution需原300秒session_start_ms/deadline_ms、已确认account、book bid/ask/available_ms、实际trade_tape/queue_receipt两个hash及同钟queue_evidence；引用存在仅支持方案，不证明maker成交。

失败路线持续为：成熟信息→独立跨市场机制→外生事件→记录到的执行损失；联合实际回撤→隐含未来风险→保护执行缺口。每条记录不同失败原因和可恢复条件。原门槛不降低、负结果不删除；已有数据相同不重复跑。积累新接收数据与七日成熟期需要真实时间，不能一次命令造出。今天的日历/期权不能倒填2020–2026经济窗口；以后新增forward时期单独登记/报告，不拿它补原历史门槛。没有当前合格数据的执行适配不会提前写成能盈利或已验证的策略。

旧forward账本仅由原批准consumer读取：Spot f1383f1034e3f72df68bbda30793d22835e74557，Coin 762d75c22d19686dbd364a6b58b59dbc23340430。本轮新source不能消费、重绑、迁移或清空旧状态。原九路线结果与旧账户producer不变，新的估值诊断不追改旧登记PASS。全量软件检查最终每仓库一次；发现失败只恢复受影响部分。

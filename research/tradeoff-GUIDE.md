# BTC 本轮复现与后续入口

先读 `tradeoff-RESULT.md` 和 `benefit-harm-policy.md`。绩效按综合净益处判断；账本、资金/订单归属、保护及因果性仍是必要底线。原历史门槛原样保留，新重评不改称原门槛通过。

原账户 producer：Coin Q2uniform75 为 `d83f396802b249d47276b3c90f979746e28d2b57`，其余5个为 `028c3c4c79aac7e4384e5628c58023acce43f1bb`；Spot两个有效默认为 `c189efa579714397bcab51c57f5872cd3ebd114d`，其余6个为 `2bc60ad8b251d47bc6f66646fbc28a29d794ded9`。综合评估使用 Spot `2bc60ad…` 的原模块，最终只增加无效 session 拒绝检查；原模块、输出及桥接说明均保留。最终软件/路由源码 Coin `9ae072874b20280fbfc9eb3e7f8be5d97c7a7d5e`、Spot `76a47ad1114e362d26587244ff8beb31b6074cbe`。后续文档/归档提交不是测量 producer。

查看归档中的 `task/spec.json`、`task/delivery.json`、`task/assessment-new-wallets.json`、`task/assessment-reused-six-wallets.json` 和 `task/route-qualification.json`。原输入/源码/失败/钱包分别在 inputs、sources、reused-wallets、task；全部本轮 synthetic状态原件在 `synthetic-state.tar.xz`，逐文件绑定见 `task/synthetic-state-manifest.json`。派生行情缓存仅记录链接/来源，不重复复制大行情库。先校验 archive.json 的长度/SHA，再按实际需要读取具体原件，不自动重新扫描所有数据或执行账户。

已接受结果直接复用。确需复现某个失败或实际依赖改变的钱包时，在其冻结源码检查出干净工作树，将 spec 中原数据路径对应到相同原件，选一个新的输出和 synthetic scratch：

```sh
python3.13 -m research.tradeoff_accounts --spec /path/to/spec.json \
  --policy channel-short --begin 2020-04-01 \
  --out /path/to/new-result.json --scratch /path/to/new-synthetic-account
```

该命令只是已登记历史账户，不授权真实账户/订单。scratch 是独立融资的历史 venue 状态，不能用于推断任何私有账户为空、替换持久生产状态或迁移旧规则。CNY10000、初始现金/FX、冻结会话子集和执行条件不能调整。Coin同UID串行，不改 HOME/UID、不删锁，不复用已经失败的内存 venue 冒充检查点恢复。

综合评估器在 Spotquant `research/tradeoff_assessment.py`：小的 manifest 显式给出来源SHA、市场/资金/时钟/执行条件、完整 UTC 日线及基准，命令 `python3.13 -m research.tradeoff_assessment --manifest … --out …`。不同条件拒绝比较，不缩放曲线；用途和可接受代价须事前登记。只有日线匹配不能升级为连续/native风险。

两仓均有有限信息提案入口 `python3.13 -m research.tradeoff_routes --packet … --out …`。输入是真实原件派生且注明接收时刻的研究上下文，不是经认证的私有账户；输出始终0订单、0账户资格。期权需同期限20–40日、真实±.20–.30delta、因果BTCUSDT RMS；跨场需已完成共同窗口、两个实际 signed-flow来源及≤1秒USDT/USD转换报价。已持仓减风险还需新鲜、已归属、已保护、无待定订单和确实可减数量。七日事件退出只根据已归属的确认成交时钟，不根据事后价格触碰。

不要再次执行归档 capture 脚本覆盖原目录。只有回答新的未解决输入问题才登记一次有限新采集，先写请求/容量预算；原451和无资格原件保留。新公开观测只从实际接收时刻可用，不补写历史发布或旧 forward日记。手动有限采集不等于常驻采集服务，也不启动交易。

本轮完整软件结果在 task/software：各仓各一次最终全量，无失败补跑。新财务源码才使相应经济结果失效，文档/分支/提交身份变化不构成795重放理由。下一轮只对有采用价值的新机制测量；先登记它要解决的决策、未解决依赖、预算和压力场景。连续方向见 `tradeoff-roadmap.json`，当前任务进度仅由 PROJECT_STATE.md/HANDOFF_PROMPT.md维护。

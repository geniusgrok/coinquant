# Continue Pancakequant — active task, not a new project

全过程中文。继续用户已经授权的改造，不重复请求权限，不把排队、候选失败、
checkpoint、CI 通过或数据采集成功当成任务完成。

先从 GitHub 读取研究分支最新 AGENTS.md、完整 PROJECT_STATE.md 和本文件；
核验 main、研究分支实际 HEAD 与最新 Actions。不要依赖旧容器或用 .transfer
覆盖现有代码。仓库 ychenracing/pancakequant，研究分支
research/on-demand-btc-20260920。以远端实际状态为准。

最新用户明确选择：**只支持 Binance**。目标 BTCUSDT U 本位永续，一个统一模型，
一个适配器、一套配置，偶尔人工/Agent 触发 run_once。保留旧交易所研究证据，
不再研发 OKX，也不保留多交易所生产兼容层。当前 Bybit 生产路径尚未完成替换，
不得声称已经支持 Binance 自动交易。

冻结验收：初始人民币 10000，2020-01-01 UTC 至 2026-09-20 exclusive，
CAGR > 200%，完整账户连续 MDD < 20%，交易所固定 20x，原稀疏不规则人工触发序列，
真实成本/funding/保证金/强平/抵押资产风险。不降低指标、不改口径或窗口、不提高
杠杆凑收益、不把 proxy 当 native。没有真实交易、划转、密钥或真实账户设置授权。
未满足经济与必要交易安全验收，不合并 main。

下一步直接执行：

1. 检查数据运行 35564939199（源 1ae46b54f21040b2e6f5b85e3390d805b0a3a8dc，
   job 106224786844）。它只采集 research/binance-acquisition-request.json 中
   203 个缺失公开档案。最后看到 queued，不能假定仍排队。完成后获取原始 artifact，
   验证校验和并持久保存。与已保存的 75 个档案合并，不重复下载。
2. 已有 75 个原件（26 trade 月、24 mark 月、25 funding 月），不是三条连续序列：
   2021-07 mark 缺失，2022-02 trade 已有。缺口已在补采清单中。恢复入口
   evidence/binance-partial-originals.json。采集中断后的物理清单才权威。
   本地原件已存 Library，完整回执/校验和在 PROJECT_STATE.md。
3. 完整数据就绪后运行 research/audit_binance.py；September funding tail 和
   December 2019 trade/funding 预热已在 evidence/binance-boundary-20260921/。
   预热 mark 只从 Dec 23 开始，不能填造更早 mark。保留 funding 毫秒偏移。
4. 按 research/linear-l3-hypothesis.md 运行一次 L3 的 2020-2023 因果预测筛选，
   使用 linear_forecast.py。L3 已事前登记但尚未测量；不缩短开发窗口来代替。
   这是单模型四天预测诊断，不是账户 CAGR。失败按登记拒绝，不调邻近参数。
   通过后才制定可执行账户候选并完整回放。2024-终点不得用于调参；边界只做数据核验。
5. 同时推进 Binance 统一生产迁移。research/binance_readonly.py 已有只读签名/UID/
   模式检查与 USDT 账户解码；8 项相关定向测试通过，未调用真实私有 API。
   仍须完成一致性对账、历史恢复和真实 Binance 保护生命周期。官方 close-all TP/SL
   并不等于原子入场/部分成交保护；禁止用普通独立止损单冒充已经证明的原子保护。
6. 继续历史规则与 USDT 风险核验。当前资料仍不能支持完整 native qualification。
   必要 testnet 交易验证需要明确授权账户；当前不要操作真实账户或请求无关权限。
7. Binance 必要原件保存后，移除同一轻量 workflow 的临时采集/upload 步骤。
   保持一个 Python 环境、一个 10 分钟 job，不跑全历史优化 CI。

已失败的方向不要重做：inverse H3/H4/M1、提高风险/有效杠杆、stop-first 上界；
L1（开发 proxy CAGR 0.58%、MDD 1.36%，极少参与）和 L2（-1.10%、15.97%，
297 次入场、244 次 stop、5 次强平）也已拒绝。旧 inverse 收益几乎全是 BTC beta。

八个分钟歧义已经完成精化：强平 8→2，CAGR 43.92→44.12%，MDD 仍77.05%。
源数据、完整原始轨迹、被拒绝候选和准确源码都已持久保存，详见 PROJECT_STATE.md
及各 originals receipt。不要再把分钟数据当 blocker 或主要经济研究方向。

最晚已核验 main 为 c886b7c63c6455bd7c933269e32cd35a6fb3e09a，未被本任务修改。
研究分支实际 HEAD 要重新查询。原生 Git 读可用，写用已授权 GitHub connector。
提交有意义成果后读取远端字节/hash/tree 核验，避免覆盖并行变化；原件禁止通过
模型输出巨量 base64/JSON。使用 Library 或已验证分块保存。排队期间继续独立工作；
临时提交可用 [skip ci] 避免取消必要采集运行。任务仍未完成，继续实施。

最新补充：x64 采集 job 长时间排队后，已将同一个 job 改投 GitHub 官方
ubuntu-24.04-arm pool，10 分钟上限和 203 个文件请求不变。优先查询最新
Acquire missing Binance public archives 提交对应的 run；35564939199 会被
分支 concurrency 取代。不要重复启动同一池的盲目重试。Binance snapshot
现已实现两次观察一致性比较和有界 race 重读；L3 增加完整输入 hash 身份记录。

重要新增：2021-07 mark 的原采集错误是 `ValueError: hour gap`，不是单纯
网络丢文件。75 个 verified 记录都有对应原件；此前“多声称一个文件”的描述
不正确，最新 PROJECT_STATE.md 已纠正。采集器改为先保存校验和一致的原件，
再做语义检查，失败仍失败。下次补采必须使用该修正代码，以定位真实缺失小时，
然后找官方原生补页/停机证据，禁止插值或伪造完整性。

当前保留的采集 run 是 35566270075（a92066e1d1f1fc86b286faf4298e3db23226af43）。
它使用修复前采集器，可能会拒绝 July mark 但仍保存其他 202 个档案。不要为了
一个失败原件取消/重开整批采集；先保存实际结果，再用修正采集器只请求未解决文件。
L3 仅依赖完整 2020-2023 trade/funding，可在该输入齐备后独立测量；完整账户回放
仍必须解决 mark 缺口，不得把预测诊断冒充经济验收。

## Latest measured update: native Binance L3 rejection

Run 35566270075 completed: 117 offline tests passed; acquisition failed semantic validation for four mark months (2021-07, 2022-10, 2023-02, 2026-06), while 199 other archives passed. Exact original artifact is durable; see evidence/binance-remainder-result-20260921.json. There are now 274 verified formal archives. The next acquisition request contains only the four failed originals, using the corrected raw-before-semantic-check collector.

L3 development screen is now measured and rejected: 437 overlapping four-day observations, correlation -0.0161721, direction accuracy 49.1991%, mean directional net -0.434740% versus constant-long +0.0884211%. These are forecast diagnostics, not account CAGR/MDD. Progression gate failed. Exact source, hypothesis, input identities and observations are in evidence/l3-development-20260921/. No 2024+ economic validation was used. Do not tune adjacent L3 parameters. Continue a different causal structural hypothesis and complete Binance data/safety work. Status remains NOT_QUALIFIED; production Binance migration remains incomplete; main must not merge.

L4 was preregistered at a6712e6263be0bfbb91e89a92350870cb8af7603 and also rejected: 466 overlapping development observations, correlation 0.0259375, mean directional net -0.332363% versus constant-long +0.0672466%. No validation used. Exact evidence is in evidence/l4-development-20260921/. Do not reverse its sign or tune its lookback following failure. Four-file native mark capture run 35567111349 was queued at last check. Latest full local suite: 118 tests passed.

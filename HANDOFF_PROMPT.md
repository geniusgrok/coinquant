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
2. 已有 75 个原件覆盖 2020-01 至 2022-01，恢复入口
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

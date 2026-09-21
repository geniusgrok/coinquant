# 2026-09-21 最新：D3事件配对与V1/V2

当前完整报告：evidence/impulse-age-20260921/REPORT.md；原件收据originals.json。
D3原件不变，继续基线。开发配对确认空头延迟损耗，独立仅多头/空头对照已完成。
V1拒绝兑现后入场失败；V2一次确认失效边界完整窗口稀疏49.65%CAGR/34.64%MDD包络，仍NOT_QUALIFIED。
V2小幅增益集中少数事件，不提高风险，不合并main。2024+继续标记已使用。
新增主动成交量信息检查已完成开发覆盖及小样本描述，未实现过滤器，未查看2024+流向。
流向逐事件影响与时间稳定性已检查：空头优势去掉最佳事件或取2022–23即反转，暂不实现过滤器；见flow-stability.json。
执行下一条：新保护确认后撤旧保护的durable生命周期及离线竞争验证；无testnet不得声称原生通过。
21项定向检查及V2未来扰动通过。当前无后台研究进程。经济、证据和生产整合未完成。
复现入口research/replay_impulse_age.py，诊断research/impulse_event_diagnosis.py，research/impulse_flow_diagnosis.py。

---

最新追加先读evidence/impulse-risk-20260921/REPORT.md及登记/验证/原件清单。
D3（D2模型risk_scale2.4）完整窗稀疏47.93%CAGR、34.50%MDD、¥138,871.75；
4h50.10%/35.58%。比L29代理口径改善但仍NOT_QUALIFIED，禁止合并main。
F小时冲击开发稀疏4.64%/33.78%，拒绝继续周期/阈值搜索。D3看了已用2024+并启发F。
复现用research.measure_mechanisms --mechanism impulse_hold --risk-scale 2.4，配native/output；
完整窗另加--full-window。新原件依赖A–E归档，完整保留所有失败与精确实测版本。
任务未完成；下一机制须提升收益来源，不能机械增加风险。执行安全未原生验证，生产只读。

继续同一任务ychenracing/pancakequant，研究分支research/on-demand-btc-20260920。
先读取远端最新AGENTS.md、完整PROJECT_STATE.md、本文件，再核验HEAD/main/Actions/本地差异。
最新研究入口evidence/mechanisms-20260921/REPORT.md及candidate-register.json、sources.json、
verification.json、EXECUTION_STATUS.md、originals.json。依清单恢复全部原始包并逐项校验，
不得用旧.transfer覆盖远端。L29完整基线35.77% CAGR/54.79% MDD保持，不合并main。
本轮实际实现A收缩突破、B扫点收回、C冲击回补、D冲击延续、D2保留持仓、E持久状态。
A/B/C无成本后优势；D2开发4h33.86%/18.22%、稀疏27.78%/16.62%；完整冻结窗口
4h21.58%/18.22%、稀疏20.48%/16.62%，期末人民币34,964.35，不达150%目标。
E仅开发小增收益却恶化回撤，未看全窗。D2全窗已看并启发E，2024+不独立。
所有结果NOT_QUALIFIED；当前规则/费用流动性代理、funding不利边界、固定FX及USDT=USD
不支持正式验收。不要放大无优势信号或跑无依据网格。依据归因提出下一明确经济假设。
信号在pancakequant/opportunities.py，统一引擎persistent_hold_replay；研究默认每4h或冻结
sparse。固定入场数量，离线仅原生保护，无虚构本地跟踪或定时退出。
Binance safety模块已做保护、撤单竞争、减仓、保证金未知写入阻止的离线验证，未接
生产writer，未做原生testnet验证。保持默认只读；没有真实交易/划转/账户设置授权。
下一条可执行：读D2完整逐年/多空/持仓/回撤归因，冻结新机制假设后开发检验；
并按EXECUTION_STATUS补尚未完成的原生执行迁移。原件归档和保存是checkpoint，不是完成。

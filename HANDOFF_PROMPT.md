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

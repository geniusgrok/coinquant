# 当前状态：basis方向检验完成，经济证据补强，仍NOT_QUALIFIED

仓库ychenracing/pancakequant；唯一研究分支research/on-demand-btc-20260920。
本轮恢复d6539ebc12e08f3cf62791ed737b02229a5cbe2f；main c886b7c63c6455bd7c933269e32cd35a6fb3e09a，未改main。
计算前协议e55abcc，首轮信息代码/结果fd8e1be；后续保存请重新读实际HEAD，不把入口当最新。
先读AGENTS、本文件及evidence/basis-direction-20260921/REPORT.md、ECONOMIC_EVIDENCE.md、PROTOCOL.md、originals.json。
旧方向报告和D3/V2/L完整证据保留evidence/direction-risk-20260921/，不覆盖旧代理结果。

## 有效目标/授权
10000人民币、无追加；2020-01-01T00:00:00Z至2026-09-20T00:00:00Z exclusive；
净CAGR>=150%、完整连续MDD<50%；Binance BTCUSDT、20x交易所设置、原冻结稀疏序列。
研究频率不能替代正式验收。授权自主研究修改/同分支提交推送；无真实交易/划转/密钥/安全配置授权。
未达经济及必要安全验收不得合并main；生产默认只读，无授权testnet账户。

## 新证据
旧basis只做0.37%成本量级计数，没有预测未来方向，旧“2机会”不能否定B问题。
本轮连续24h VWAP价差+变化，7日后下一稀疏调用退出，控制价格趋势/波动/D3冲击，
2020–21训练，2022–23按月只用成熟标签+7日embargo；两种机制事前登记。
452有效标签、157非重叠样本、80个顺序评估；延续较控制-0.2960个百分点/样本，
反转零方向增益，预测误差均未改善。特征不是完全重复价格，但没有稳定成本后新优势。
INFORMATION_SCREEN_NOT_ACCOUNT。未生成统一账户候选，不做阈值/预算搜索，不用2024+选型。
首轮结果和15秒funding边界修正结果都保存；因果、异常、未来标签及资金费检查4项通过。

46个持仓月份官方funding响应4181条，1897条含mark，费率与原档案一致。
L稀疏147次支付可核实mark，固定数量减少1.49USDT；省略30笔非边界收入约24.45USDT；
不足解释收益缺口，不能冒充重算账户或alpha。L0及4h也同口径审计。
FRED H10 CNY/USD至2026-09-11，四账本参考重估；末段不填，USDT/USD仍缺，不输出新全窗CAGR。
L最高名义124336.89USDT，历史MMR/tier/cum缺口必须优先；现行规则不能倒灌。

## 完整配对分钟回放
补2024-03-05、2021-01-02 trade/mark分钟，官方校验及重建一致。原24日扩至26日。
L/L0各4h/稀疏四个完整账户，订单解压后逐字节相同，CAGR/MDD/期末不变。
L稀疏67.0921%/32.0241%，314775.82元；4h65.0208%/40.2210%。
L0稀疏48.3265%/23.6710%，141379.98元；4h44.0065%/28.4504%。
L仍较优代理基线，增益来自方向/预算，非新信号；D3/V2保留，盈利集中度风险未解除。

## 生产及安全
订单/保护源码本轮未改。稳定ID/durable intent/未知先对账/子单竞争/重启清理全部保留。
本轮再验CLI5项及信息4项共9项通过；原生并存、部分成交/取消竞争/资金转入顺序仍未验证。
CLI只有120根完成4h行情，研究使用完整机会/已消费campaign/日波动状态；
不可把短窗重新初始化当作研究一致。下一工程是共享可恢复模型状态与净目标，不能绕过写入阻止。

## 下一步与恢复
1. 按新originals.json核验恢复完整原件；旧native依赖沿direction-risk/basis-originals，不重采历史、不覆盖源码。
2. 复现信息：python -m research.basis_direction --native NATIVE --spot SPOT --output NEW。
3. 复现分钟账户：python -m research.economic_refinement --native NATIVE --output NEW --candidate L（及L0）。
4. 优先补L名义范围的历史风险档位、cum及连续USDT估值；保守代理继续NOT_QUALIFIED。
5. 下一不同信息机制已说明为美元实际利率变化驱动跨资产需求，先核验DFII10发布日期/修订与历史可得性；
   尚未测量，不能用现行回溯修订序列冒充当时可得。若缺时点证据，先推进独立经济/共享状态工程。

总目标未完成：CAGR差82.9079个百分点，规则/估值/研究生产一致性/原生安全均有缺口。
没有后台任务；CI通过、文件保存及本轮研究完成不代表正式合格。

## 保存后的CI修复
经济证据提交e4b525c的CI仅失败于新研究检查未安装numpy，其余192项通过。
新增requirements-research.txt固定numpy==2.3.5，并在原唯一10分钟CI中安装；生产无numpy导入。
复现研究前执行python -m pip install -r requirements-research.txt。经济源码及结果不变，原件仍有效。
最新CI结果需按当前HEAD核验，不把旧失败或旧成功误作最新状态。

# 当前状态：方向风险配置改善，仍NOT_QUALIFIED

仓库ychenracing/pancakequant，研究分支research/on-demand-btc-20260920。
本轮恢复入口5232f598a1fde7bbb9b3bb85e04b28082a7fd215；main核验c886b7c63c6455bd7c933269e32cd35a6fb3e09a。
先核验实际远端HEAD及本地差异，不用旧恢复包覆盖代码。当前报告evidence/direction-risk-20260921/REPORT.md、
PROTOCOL.md、candidate-register.json、各候选JSON、EXECUTION_STATUS.md、verification.json、originals.json。

## 不变目标与权限
人民币10000，无追加；2020-01-01T00:00:00Z至2026-09-20T00:00:00Z exclusive；
成本后CAGR>=150%，完整连续账户MDD<50%；Binance BTCUSDT，单向逐仓20x设置；原冻结稀疏序列。
研究4h不能替代正式稀疏验收。授权研究提交推送，不授权真实资金/账户配置/密钥操作。
所有结果仍代理NOT_QUALIFIED，禁止合并main。生产默认只读，无授权testnet账户，无账户操作。

## 最新成果
保留D3/V2原始数据与源码。复用long2.4/short2.4开发，不重跑。
事前H(long2.4/short1.2)开发稀疏66.39%CAGR/22.07%MDD包络；L(long3.6/short0)89.57%/24.25%。
L是一次50%预算增加，不按历史MDD反推；开发后冻结，未继续放大。
完整L稀疏67.0921%/32.0241%，人民币314775.82；4h65.0208%/40.2210%。
完整L0(long2.4)稀疏48.3265%/23.6710%，用于隔离方向/预算；4h44.0065%/28.4504%。
D3完整47.93%/34.50%、V2 49.65%/34.64%继续比较。L主要增益来自预算，不是新信号。
L完整稀疏前三净现金占62.01%，正常88.91%；2022稀疏负收益，不能隐瞒。2024+已反复使用。

资金费承接/拥挤消退机制已继续筛选：过去7日funding符号，额外滞后1小时，原稀疏至少7日非重叠持有。
开发13多头均值-1.46%，148空头-1.77%，不推进账户策略、不搜索阈值。
此为INFORMATION_SCREEN_NOT_ACCOUNT，未模拟保证金/保护/强平，不得当账户绩效。

保护替换已实际实现：新pair真实回读后逐单撤旧，durable journal/取消intent、子单终态、重启与flat cleanup。
不假设API必然允许并存；拒绝/未知时旧保护保留。部分成交暂停，允许授权reduce-only移除剩余风险。
丢失ownership阻止写入，只读观察可用。CLI已回读取消意图并显示未完成replacement状态。
35项相关定向检查分批通过，六组账户时间/事件/价格/funding率一致，全部实测源码哈希核验。
默认CLI --execute仍阻止，mock不等于原生验证。

## 恢复与下一步
复现：python -m research.direction_risk --native NATIVE --output NEW --candidate L --full-window。
开发H/L省略full-window。原件包含完整逐笔、权益、输入身份、测量源码、失败日志和全部结果；依赖链到上一轮原始行情。
读取originals.json回读核验档案后只恢复缺失数据，不重采完整历史。当前Git包含源码及小报告，档案包含大型原件。
下一具体工程：核验snapshot对子订单剩余风险的识别，补历史经济规则/动态FX与USDT估值的来源可用性；
取得明确授权testnet后才验证原生并存/部分成交/取消竞争，无账户时继续离线独立工作。
下一收益研究必须是不同经济信息机制；不继续预算阶梯、年龄/流量/funding阈值搜索，不承诺必然达到150%。
项目尚未完成：收益、历史经济证据、研究生产一致性及原生安全资格都未过；没有后台继续工作的承诺。

## 历史证据入口
impulse-age-20260921保留V1失败/V2/事件配对/流向失败；impulse-risk-20260921保留D3/F；
mechanisms-20260921保留A/B/C/D/D2/E；return-capture-20260921保留L29。
原件依赖链由各originals.json给出；历史完整内容和过去交接仍可通过Git原提交读取。

# 数据契约、文献与来源状态

协议c0fd62b7360eecd4385ed28600f16d1e5a42f4aa先于替代源计数获取及所有新经济输出。

## 原论文：已读取全文，不是摘要复述

Liu & Tsyvinski，August2018，NBER Working Paper24877。原始PDF HTTP200，653165字节，SHA256 c59ede546d32c6c2d5215cf7600c6f8642406083fc37952b27d6ee5fa9f364f2；原件及pdftotext在证据包raw/nber_pdf.*。
https://www.nber.org/system/files/working_papers/w24877/w24877.pdf

第2节：BTC价格样本2011-01-01至2018-05-31，CoinDesk；Ripple2013-08-04起、Ethereum2015-08-07起，同一终点。Google搜索数据由Google下载。
第4.2节、表19–22：搜索词Bitcoin的当周量减去前四周均值，并标准化；周度预测1至7周，BTC显著关系出现在未来第1、2周。表22用前两年定分组边界。该设定不提供本项目的发布日志、实时vintage、永续资金费/保护路径或成本后账户证据。
全文相关部分未给出足以重建每次下载的地区、类别、搜索渠道、主题ID、采样版本、请求区间和发布时刻；不自行声称这些已确认。这里只借用四周偏离的假设形状，不复刻论文分位交易。

## Google三条路径分别核查

|路径|本轮实得与覆盖|结论|
|---|---|---|
|官方API|官方页面HTTP200，仍申请制Alpha；文档滚动五年，发布说明具体为1800天、截至两日前。未获访问权限，没有发起申请或伪造API调用。|2026执行时不能覆盖2020及预热；一致尺度仍非绝对搜索计数。无数据载荷。|
|公开网站|Bitcoin搜索词、全球、默认全类别/Web Search、UTC；请求2019-11-01至2020-02-01返回429，原错误HTML保留。|实际取得0条。未改变地区/关键词绕过限流，未取得类别/渠道的响应确认。当前全历史0–100也不等于历史可得值。|
|历史归档|恢复仓库/原件没有关注度数据。找到并读取GoogleTrendArchive作者论文，归档2024-11-28至2026-01-03的Trending Now事件，非固定Bitcoin搜索指数。|与本轮开发期及数据产品不符，未下载大归档。有限检索未找到合格2020+逐期vintage，不宣称全球不存在。|

官方API：https://developers.google.com/search/apis/trends
发布说明：https://developers.google.com/search/blog/2025/07/trends-api
FAQ：https://support.google.com/trends/answer/4365533
归档作者原文：https://arxiv.org/html/2603.21871v1

FAQ确认抽样、按请求时间/地区归一到0–100、低量可能显示0；0不等于确切无搜索。长于30日范围用UTC。重采样、噪声、舍入、修订和拼接风险不因线性尺度变换消失。没有Google计数进入模型。

## 唯一替代源：Wikimedia AQS

预登记en.wikipedia.org / Bitcoin / all-access / user / daily；全球英文页面访问，无国家筛选，非搜索主题、非独立人数，不合并重定向、其他词条或语言。用户分类不保证全为真实投资者。响应project=en.wikipedia、article=Bitcoin、agent=user、granularity=daily均检查。
端点：https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia.org/all-access/user/Bitcoin/daily/{startYYYYMMDD00}/{endYYYYMMDD00}

跨年探测2019/2020/2023各7天全部HTTP200。之后五个按年请求实得2019-11-01至2023-12-31（包含终日）1522个日计数，无缺日、重复日或显式零。没有取得2024+数据，不把文档自2015年可用当作本轮完整窗已取得。
值是日页面访问计数，不做逐请求0–100归一或锚点拼接。周为Monday00:00UTC至次Monday00:00 exclusive；必须七日完整，且前四周完整，才有A=本周总量−前四周总量均值。日缺失/404视为unknown，不能填0。未完周期不能分摊到周期内部。

三种时间严格区分：
- period_end：活动周的排他终点。
- available_at：本次所有周均null；没有逐期历史快照或首次发布时间证据。
- raw/*.json的retrieved_at：2026-09-22本次HTTP获取发起时间，非历史发布时点；响应原字节、headers、请求范围与SHA256同时保留。

用于探索的assumed_available_at=period_end+48h；这是明确假设，不是已证实的历史发布时间。最新到期周缺失即拒绝，不回退旧周；超过7日陈旧拒绝。额外7日滞后仅预登记诊断。
官方说明常在几个小时内加载，但异常可24小时以上；缺失与真零可能无法区分。当前接口没有逐条vintage字段，不能靠48h或9日滞后恢复历史版本。
https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/documentation/troubleshooting.html
https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/concepts/page-views.html

官方数据问题记录：2020-04-29新增automated分类、2020-07-01调整Android消费定义、2020-08-24修复mobile定义（问题从2020-05-18起）；2021-06-04至2022-01下旬日志流量丢失，两个阶段平均2.80%/4.34%。这些是平台总体记录，不是Bitcoin误差估计，未用它们补值、删除亏损或乘系数纠偏。
https://wikitech.wikimedia.org/wiki/Analytics/Data_Lake/Traffic/Pageview_hourly

分类：RETROSPECTIVE_PROXY，可复现当前下载版本；正式历史可得性UNVERIFIED。不得将代理负结果扩大为所有关注度无alpha；Google路径是数据/可验证性阻塞，替代路径是已完成的受限探索筛选。

## 查重与恢复

现货主动成交延续控制的是成交方向，不等于阅读关注；旧basis/funding是市场结构变量。固定入场持有、T追踪、B0/B1标签替换没有检验本次外部访问计数。它们的失败仍保留，不重跑。
原payoff包53179721字节及SHA256与远端回执一致，6179个manifest成员全核验。原三份研究源码、报告和摘要与f1e2496远端Git blob一致；最新state/handoff及回执另从远端恢复。
标签SHA256 03c4ba9c6ef54260175e72b86dd35888b826c16c9900420146ded8d6c7b9e329；468个t与原invocations完全一致，标签路径未重生成。共享Account来自coinquant.linear_account，funded_target来自coinquant.linear_sizing；本轮未改资金、保护和执行模块。
补充SAVED_PREDICTION_REVIEW.md及ZIP均取得，作为事后诊断复用；本轮独立核验C1与原B1预测完全一致，不宣称重新执行其所有统计或测试。

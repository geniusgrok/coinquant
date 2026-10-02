# Coin 完整合约候选结果

BTCUSDT USDT结算永续，单向逐仓、交易所20倍；原持仓/资金/保护/未知订单门保留。CNY10000、不追加资金，2020-01-01至2026-09-20 UTC（末日不含），每账户795次有限历史模型会话，五候选×四压力场景全部完成。这里只总结完成的20组原账户；实际校准与扰动结论另见完整最终报告。

| 候选 | 基础成本后CNY CAGR | 连续分钟/包络代理MDD | 最差压力场景CAGR | 采用结果 |
|---|---:|---:|---:|---|
| 原SX60+DFII10 | 119.2284% | 44.1051% | 104.7730% | 保留基线 |
| 新鲜触发/追价门 | 20.6489% | 47.7723% | 18.0023% | 基础年化大幅下降，回撤增加 |
| ATR主仓移动止损 | 99.9177% | 48.5204% | 74.6681% | 基础年化下降，回撤增加；压力场景不通过 |
| 低波动压缩突破 | 34.0937% | 87.0373% | 29.7417% | 基础回撤87.04%，超过50%上限 |
| 每根4h棒最多一次确认加仓 | 94.6777% | 44.0980% | 84.4491% | 基础年化下降24.55个百分点，回撤只降低约0.0071个百分点 |

所有四个新合约候选都未通过预先登记的配对压力门槛。原模型保留，primary风险尺度7.5、macro3.6不变；没有新默认参数、组合或资本最优点。新候选没有使收益更高，不构成收益达到天花板的证明。原150%年化/连续回撤小于50%目标保持，所有20组均为NOT_MET。

## 完整四场景结果

场景为原base、手续费×1.5、读取400ms、触发滑点。手续费/延迟变化会改变之后的实际订单路径，不能把较高手续费账户的较高最终收益解释为收费更有利。

| 候选 | 场景 | CNY CAGR | 连续代理MDD |
|---|---|---:|---:|
| incumbent | base | 119.2284% | 44.1051% |
| incumbent | fees-x1.5 | 128.5405% | 44.3849% |
| incumbent | read-400ms | 104.7730% | 44.4119% |
| incumbent | trigger-slip | 124.9365% | 44.6470% |
| fresh-entry | base | 20.6489% | 47.7723% |
| fresh-entry | fees-x1.5 | 19.9623% | 48.7951% |
| fresh-entry | read-400ms | 18.0023% | 47.9894% |
| fresh-entry | trigger-slip | 19.8391% | 49.5723% |
| atr-trail | base | 99.9177% | 48.5204% |
| atr-trail | fees-x1.5 | 96.9093% | 48.9643% |
| atr-trail | read-400ms | 74.6681% | 48.5078% |
| atr-trail | trigger-slip | 96.6967% | 49.1227% |
| compression-breakout | base | 34.0937% | 87.0373% |
| compression-breakout | fees-x1.5 | 29.7951% | 88.3112% |
| compression-breakout | read-400ms | 34.4124% | 83.4426% |
| compression-breakout | trigger-slip | 29.7417% | 88.7686% |
| single-topup | base | 94.6777% | 44.0980% |
| single-topup | fees-x1.5 | 93.5860% | 44.3735% |
| single-topup | read-400ms | 84.4491% | 44.4023% |
| single-topup | trigger-slip | 93.8272% | 44.6416% |

## 独立核对与来源

独立Decimal40资金和公共资金费/先前完成mark核对重建15320笔成交、17068次资金费结算，所有20组均795会话，资金费、佣金、持仓差为0，最大货币算术残差5.26e-21 CNY。END边界不计入资金费。独立NumPy OLS/HAC7统计与不可变99评估器比较最大差8.88e-16；原四场景financial/fills/daily/ownership/operating/remaining_original_fields六组与批准的原基线完全相等。

实际原件/workspace/scratch/alpha-beta-next/perp-singletons-retry1.json.gz SHA bf1d167979f4bb3d15925f0bcaf5337bd1cc0a17523628b3af0599875dc5a7c1，来源acedaa43ca94223f24e2fe11851bbef74e032a69/Pythona6e3f30f02208ff7e604b6181c5d8fa7000fe7e30dbc3276fbcc93ffbb0ad227。不可变评估器99fcf005d2cb15c13bb37322b65ab2863b19d65e；其CSV/JSON/Markdown保留完整beta、成本、归属、因果诊断、年度集中度和回撤口径。不得将后续main提交冒充已测量来源。

可移植归档中的相同原件位于evidence根目录下的对应子路径；原始文件字节及raw SHA保持不变，本文路径更正不改写或重标原始财务回执。

全局12比例文档SHA ed8c99295e71386a7cef300f7d101ea941e5a7a0147bc9038012d6cc58e23821，独立确认等于已完成Spot7加Coin5，731个2020–2021实际USDT日收益训练。压缩突破比例0.7997705584944133，其余Coin比例1；仅2022年后的新资金使用固定比例，已有持仓不能倒缩。比例并非收益曲线缩放，后续完整实际账户才用于风险判定。Coin登记CAGR年长365.2425，日统计/HAC年化365.25，分别标记。

独立阶段依据为coin-unscaled20-financial-review.md、coin-unscaled20-financial-proof.json和financial-audit-perp-singletons.json。连续分钟/包络代理路径未被第二个引擎重放；16组明确包含事后可见的路径边界，原29个缺失mark分钟的已接受界限保留。研究过的历史不是干净样本外，HAC不能纠正策略选择偏差。原生案例0、实际账户日0，NOT_QUALIFIED。未使用私有账户、凭据、订单、转账或账户设置。

SHA绑定：

- registered-unscaled.json: 1784600db17f99b09a7dfedb74d3376c33379b8ad804a127f63259a88a10820c
- coin-unscaled20-financial-review.md: d883288747caf17b37dccd9dbc20c8a2bdd698c7992c398514740a3c6b71076f
- coin-unscaled20-financial-proof.json: 979cf8d362f7d9a7c4557827e753fd292d2cf17c2bac9c9eccd2ceb195453a4f
- financial-audit-perp-singletons.json: 051fade57cea7f85e33b799a7302da3d3c2f9adfae490f1161bcdf30a3ba0555

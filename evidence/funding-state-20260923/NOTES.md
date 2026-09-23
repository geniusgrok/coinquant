# 完成资金费状态与已执行净账户：只读下一机制筛查

OI 当前原件的历史版本/发布时间没有闭合，见 `../oi-archive-20260923/REPORT.md` 和 `TIME_ELIGIBILITY.json`。随后只读检查另一个**已保存的独立输入**：在 SX60 全窗 30 个真实成交母单、DC10 开发 29 个已平仓分段的**首笔成交前**，读取三次已发生的 8 小时资金费结算率，按 24h 三值之和正或非正分组，归集该笔实际已实现的成本后钱包净额。具体代码、所有年份分组见 `realized_state_audit.py` 和 `REALIZED_STATE.json`。没有添加到生产模型、没有资金费信号候选、没有筛选交易的新账户。

| 既有路径／首成交前 24h 资金费符号 | 笔数 | 实际净盈利笔数 | 实际钱包净额 USDT |
|---|---:|---:|---:|
| SX60 全窗：正 | 27 | 20 | +167,986.28 |
| SX60 全窗：非正 | 3 | 1 | −4,596.43 |
| DC10 开发：正 | 23 | 7 | −682.81 |
| DC10 开发：非正 | 6 | 3 | −1.15 |

分组内钱包净额**属于原账户路径**，组合资金和后续成交会因任何过滤改变；上表不能直接相减得到新模型净增益或 CAGR。SX60 的 2025 年三笔中，正资金费组两笔已赚 +20,149.38 USDT，非正组仅一笔 +70.68 USDT；单用符号过滤无法解释如何扩大当年独立机会或填补正式 150% 年化差额。DC10 非正组虽比正组少亏，但跨 2020–2022 的六笔合计仍微亏，原 DC10 价格核心完整开发账户已经失败。两个模型的分组不是独立样本，且分组高度不平衡；没有足够可归因净优势冻结并昂贵地重跑账户。它只否定**以这份证据立即晋级简单资金费符号过滤**，不永久排除资金费所有机制。

原数据使用已验证全窗官方月度资金费 ZIP/CHECKSUM **80 对**，逐份再验供应方 SHA 与 8h 单位，取 `calc_time` **严格早于**首笔成交的最近 24h 三次结算，不采用未来资金费；有序 ZIP 哈希清单的 SHA-256 为 `ded3fb7414b58f2bd995b753c574c51b4e54021074dcab6bf18071bc1283b569`。原月度包索引和逐日修复收据在 `evidence/sustainable-capital-exit-20260922/originals.json`；恢复基础输入包 `libfile_54a5fcf3af5c8191af73244b14ef6ec5`，SHA-256 `854fba74875a4e7bc07a9b709edf82b377d7157a01d8d73db42db44aa41095c1`。SX60 全窗原账户包 `libfile_0f102b0356a48191b1b5d2865074ad0b`，SHA-256 `d18021568ef10c5c091b1dc5488372a1d87e8b8bc0baadb5f0fe288df68956ab`；已核验的 30 笔逐笔净额 `../sx60-confirmed-risk-20260923/CAMPAIGNS.json` SHA-256 `e150a05e257b3813ed874f3dc3d62d1e170c3344687db34c540d9d1c422f4df5`。DC10 原账户 `libfile_f323126832c08191b6b81999e03e435c`，SHA-256 `2ed9b042cd7000d9b3bece516ef8b47ffbf7c975d6f598faa7c3d29038442621`。复现：`python3 evidence/funding-state-20260923/realized_state_audit.py /path/to/full/native/monthly/fundingRate/BTCUSDT evidence/sx60-confirmed-risk-20260923/CAMPAIGNS.json /path/to/COINQUANT_DC10_DEVELOPMENT_REJECT_20260923.zip`。

正式最优仍是原 SX60 **102.626211% CAGR／39.885115% MDD**。下一候选需要新的可观察状态在稀疏调用下增加**独立且可成交**的净机会，而不只是选择原路径已经发生的赢家。任何未来版本先冻结规则、用相同价格和资金路径配对控制再跑 468 开发；后段已反复看过。

# 固定空头研究入口

固定方案、结果前门槛在structure-spec.json，原件见evidence/btc-structure-20261004。当前四窗已全部拒绝，无新增短仓，**不要再跑同一筛选或完整795**。默认人工有限会话操作继续按edge-GUIDE.md，仍无默认短仓或后台守护进程。

仅在另一个事先登记、有具体决策用途的任务需要时运行：

```sh
python3.13 -m research.structure_screen   --market /path/to/original-perp-market   --prints /path/to/verified-original-public-vault   --fx /path/to/original-usdcny.json   --out /NEW/screen-output
```

--baseline-summary和--baseline-summary-sha支持**只恢复变更的候选**。必须提供完整旧summary的实际SHA；旧生产者为祖先、生产执行/基线依赖、原spec/FX/市场/日程相同，基线逐文件SHA与开始时刻匹配，账户保持原身份。修正结果中的coin/window-*.gz路径相对证据根目录，不是新生产账户。没有恢复私有持仓或建立空账户的语义。

源码在经济测量前冻结。每窗独立资金与时钟，不拼CAGR；原trade_print/分钟标记包络仍是历史代理，不是原生执行。月缓存只在单调用内共享，三日print缓存只读原ZIP/校验响应，临时链接/二进制只清理自己的scratch，无整库14GB复扫。900秒筛选预算在窗口边界检查，修正调用扣除首次测量时间；账户/软件测试共享UID的任务始终串行，不改变HOME/锁。窗口风险失败立即停止；只有入围者才登记完整测量的区别、预算和决策问题，复用匹配旧基线，不扩大网格。

未来空头是否有效需要真实新增信号与实际成交样本；不能降低门槛或放弃多头优先来使历史结果变好。当前公开市场HTTP451，前向继续pending；旧账本使用762d75c22d19686dbd364a6b58b59dbc23340430消费者，不重置、迁移、重绑或回填。工程授权不包括交易、账户设置、凭据、转账或原生开仓。

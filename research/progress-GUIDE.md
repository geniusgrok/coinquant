# BTC 改造结果使用说明

先读本项目 `PROJECT_STATE.md`、`research/progress-RESULT.md` 和 `research/progress-spec.json`，以最终默认版本与原始结果身份为准。8 条路线均有可执行实现；未采用候选及失败回执也保留。有限阶段已完成 16 账户/452 历史会话，恢复证明另为 2 账户/24 会话；唯一完整历史账户已完成795个不同会话，分段属于同一个账户；完整结果拒绝新信息核心默认采用。复用已完成、依赖相同的结果，不因文档或提交身份变化重跑账户。

## 有限策略入口

在对应 Coinquant 或 Spotquant 仓库根目录运行 `research.progress_accounts`。例如 Coin 已登记的 2020Q2 新 primary：

```sh
python3.13 -m research.progress_accounts \
  --spec research/progress-spec.json \
  --policy release-new-primary --begin 2020-04-01 \
  --out /ABS/NEW/result.json --scratch /ABS/NEW/synthetic-account
```

这是复现入口，不是要求再次测量。只选 spec 登记的策略、窗口和费用情景；输出与账户目录必须独立。Coin UID 12000 账户、同 UID 测试严格串行，遵循原账户锁。共享的只有不可变行情；资金、持仓、订单、模型及虚拟时钟均独立。不要用账户曲线缩放代替真实账户。

Coin spec 的可选 `shared_parsed_cache` 与 `shared_parsed_cache_max_bytes` 控制 progress 专用缓存，默认上限 128,000,000 字节。命中来源绑定的只读 gzip；缺失、容量不足或发布 IO 失败回到原 loader，仅影响处理成本。实际 binary 命中一致性是工程证据，不是全账户提速测量；不同策略账户耗时也不能直接归因为缓存。账户 SQLite 不能放入共享缓存，也不能为清磁盘删除持久状态。

## 完整路径与安全恢复

共享 evidence ZIP 的实际成员 `task/full-continuation.py` 是本轮注册完整路径的可复现入口。先解压并保留 `task/` 内 driver 与 helper 的相对位置；归档中的 `task/full-spec.json`、`full-segment-1.json`、`full-segment-2.json` 及后续 tail 登记和回执保留原始执行身份。完整账户已闭合，以下只说明原入口，不要求再次启动。它只处理登记候选，不自动重跑旧控制或整个矩阵：

```sh
cd /workspace/coinquant
python3.13 "$evidence_root/task/full-continuation.py" \
  --mode start --spec "$full_spec" --scratch "$account_dir" --out "$segment1"
python3.13 "$evidence_root/task/full-continuation.py" \
  --mode resume --spec "$full_spec" --scratch "$account_dir" \
  --previous "$segment1" --checkpoint "$checkpoint_file" --out "$segment2"
```

恢复要求原报告、checkpoint、同一原 SQLite 目录及源码/输入/策略/配置/UID 摘要全部匹配；只接受完整清理且无未解决执行意图的安全会话边界。持仓必须保有确认的原生止损、止盈及账户归属保护。执行期间冻结源码。

未知 crash 后先保留失败回执与原状态。若 SQLite 已在下一会话推进，旧 snapshot 会被拒绝；禁止改绑定摘要、回退数据库、reset、改 HOME/UID 或绕锁来假装续跑。更换源码后也不能重绑旧状态继续。旧 405 会话没有安全 venue checkpoint，不具备恢复资格。原 e99 源码的两个独立账户、各 12 会话等价证明只能证明其原始依赖。

## 保存和归档

保存每个原始 JSON、journal、spec、源码身份、输入摘要、checkpoint、失败/负结果及账本；新增结果另取文件名，不覆盖旧回执。共享 ZIP 成员使用实际 `task/`，保留 driver 与 helper 的原目录关系及文件摘要。共享 evidence：[https://github.com/geniusgrok/spotquant/blob/main/evidence/btc-progress-20261005/research-artifacts.zip](https://github.com/geniusgrok/spotquant/blob/main/evidence/btc-progress-20261005/research-artifacts.zip)。

仅在合成账户进程正常闭合后归档完整 state 目录，包含原 SQLite 与仍存在的附属文件，另存原路径映射；例如以下只生成压缩包，不删除或重置原状态：

```sh
tar -czf "$archive_dir/coin-synthetic-state.tgz" -C "$account_dir" state
sha256sum "$archive_dir/coin-synthetic-state.tgz" > "$archive_dir/coin-synthetic-state.tgz.sha256"
```

恢复运行仍使用原 state 目录；归档本身不是跨源码迁移或可恢复资格证明。最终全量软件检查每仓库集中一次；金融账户、数据处理与软件测试分别记录。最高权限授权的是工程和研究改造，不能据此使用 private API、真实下单、修改真实 settings 或自动实盘交易。

本轮完整路径已经闭合并拒绝默认采用，无须再运行上述复现命令。原入口只支持原两段上限，后来的 `budget-tail.py`、`budget-tail-recovery.py` 与 `storage-tail.py` 各自绑定具体真实登记/停点，不是通用重试入口；原 `can_resume=false` 和进程限制保留。只有对应安全停点与原同一 SQLite 尚匹配时，独立登记的执行器才获得相应恢复资格，不能直接修改旧收据来续跑。

2026 单日再生二进制可达约291MB。本轮存储恢复在已验证安全会话末释放关闭句柄的 private binary，保留原 owning arrays、gzip、ZIP、账户 State 和时钟；原 loader 和输入校验不变。中间非链快照精确压缩保留，关键302/520/722原件保留，ZIP按原路径映射复原所有原 JSON 字节。该操作用于腾出工作空间，不证明策略收益或整账户提速。

下一项有用研究先为持仓冲击退出寻找其他固定 regime 的真实已归属处理支持；无支持就不启账户。旧信息阈值全路径负结果直接复用。Spot 的退出原因和独立信息路线须有新的真实处理与成熟数据支持，数据 closed boundary / fresh FX 不足继续 PENDING，不承诺后台采集或未来收益。

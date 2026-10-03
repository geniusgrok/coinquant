# Task 6 controller preparation — independent scoped review

SPEC: **FAIL**.

QUALITY: **CHANGES REQUIRED** — T6-C1、T6-C2、T6-C3 应在首次真实队列启动前修复。

## 范围与已核对证据

本次仅审查外部 `prepare-source-freeze.py`、`run-registered-phase.py`、固定 registry、guard preparation receipt 及报告指定的 loader/market/vault preflight 接口；不是 whole-branch review 或 substantive financial review。读取了 task-6-controller-brief/report 和完整 review package；package SHA 为 `14d619b7a0f162b0bf5a280b7ae2b0c898af1e72b3e9d5af55a832091d1c5b21`。

报告列出的五个文件均实际复核 SHA 匹配，其中 freeze helper `742f6b895cf18e691a64d1819099e6cdf15eda26babb04e4ef0fcd2fbb417af8`，runner `57ce768b53b4277031d82f344506c7d4f3b8db569f350762f52cfa0944756a2a`，registry `e58114f25f316d237860d2d6e6859d48614a57d69065524f6c256140c575fbfa`，guard receipt `1528c95988d7463da606265686137596ef2d3c9cf99eb047c4bfc846c11a4090`。旧 runner 作为未使用原件保留，未改写。

静态检查 registry 的50个 job：labels与outputs均唯一，`--out`实际argv与declared output一致；账户数为Spot36/Coin16 unscaled、Spot4/Coin4 risk、Coin2 offsets、Spot3/Coin3 baseline budgets，共68。固定 argv 的不可变 registry SHA 有检查。真实 source freeze 和完整 financial queue 尚未启动。

读取原有四条 synthetic guard 检查及 public loader/preflight receipts，没有重跑它们，也未重复哈希整个14GB vault。下述新 probe 仅针对具体缺口，全部在临时目录；进程 probe 的 Popen 被 fake object替换，**未创建任何真实子进程**。无源码/registry/原件修改、提交、子代理、Coin tests/producer、账户/原生/私有请求、HOME/UID/锁改动；只持久写本审查报告。

## Findings

### T6-C1 — P1 / blocking：非guard启动/回执异常会遗弃已启动任务，缺少真实完成诊断

位置：`run-registered-phase.py:82`–`107` 与 `114`–`132`。

启动循环只捕获 `guard()` 的异常。其后已有output/progress（92–93）、已有invocation receipt（98–99）、mkdir/open/write/Popen失败均直接退出main。若第一个Spot子进程已经启动，第二个job遇这些条件，退出时没有drain/wait/finally，不会为已启动任务生成finish，也不会正确持久记录未启动任务。finish阶段的文件读取、输出哈希或exclusive写入异常同样可跳出对其他active进程的收尾。单纯guard失败虽会等待active，但其自身失败与pending列表只打印stdout，没有独立持久phase failure receipt。

最小隔离probe：临时registry只有两个Spot synthetic jobs，第二个output预先存在；第一个Popen返回仍运行的fake process。只为隔离该启动分支将guard替换为no-op；没有实际账户程序或真实子进程。结果：

```text
LAUNCH_FAILURE_ESCAPES existing output/progress: <temporary>/two.json
ACTIVE_POLLS 0 ACTIVE_WAITS 0 FIRST_FINISH_EXISTS False FIRST_LOG_CLOSED False
```

这违反 failure停止新任务、account for已启动进程、保留真实finish诊断及pending清单的要求。已有output不是可以忽略的异常输入，brief明确不能假设它不存在。

最小修复要求：将整个launch与completion bookkeeping纳入统一失败状态和收尾路径，而不仅guard；所有已启动进程必须被跟踪并drain/reap，日志关闭，生成实际exit/guard/output诊断。启动尚未成功的job也应有独占、可复核的失败/未启动状态；持久phase结果记录pending labels与错误，不得伪造未启动进程的exit code或成功financial状态。显式处理无法写回执的错误并返回失败；不得因为收尾出错再次启动或自动重跑。用隔离fake/harmless-process覆盖已有output、Popen失败以及一个active时的receipt写入失败。

### T6-C2 — P1 / blocking：actual vault与后续risk校准输入未纳入不可变原字节守卫

位置：`prepare-source-freeze.py:59`–`63`、`93`–`116`；`run-registered-phase.py:46`–`58`。

freeze把历史 `vault-before-task4.json` 文件本身加入bound_files，但没有展开其中的实际vault ZIP/CHECKSUM到bound_files，也没有登记vault的实际file-set。`original_market_vault`与`public_vault_preflight`只是输出metadata；runner.guard不读取或验证它们。唯一bound_trees是 `/tmp/spotquant-market/klines` 与 `/tmp/coinquant-market`，不是Coin实际恢复print使用的 `/workspace/scratch/alpha-beta-next/public-print-vault`。

Coin `VerifiedPrints` 的当前ZIP与CHECKSUM一致性检查，不能替代冻结旧身份：若ZIP及CHECKSUM一起改变，二者仍可互相一致，且controller前后guard仍只核对未变的旧清单JSON。这里只读了该现有接口，没有做Coin运行或重审其实现。

此外，registry五个risk命令实际引用 `/workspace/scratch/btc-alpha-beta-edge-20261003/assessment/{spot,perp}-calibration.json`。freeze helper没有把这些后生成的文件纳入绑定，runner也没有risk phase输入receipt。源/argv不变而同一路径profile原字节变化，controller仍会接受。producer自己保留profile SHA、最终assessor复核，不能替代“启动前及结束后固定实际输入”的controller要求。

最小隔离guard probe按当前结构构造freeze：bound_files仅列历史vault JSON，job argv列临时calibration path。修改临时actual ZIP、同步修改CHECKSUM，并修改calibration JSON；mock source_at保持同一synthetic identity后，原guard结果：

```text
CHANGED_ACTUAL_VAULT_AND_CALIBRATION_GUARD_ACCEPTED True
```

这个probe只是验证当前结构遗漏的输入不被检查，未修改真实vault/校准文件，也未执行任何producer。

最小修复要求：freeze须将Coin实际可消费的原始vault ZIP/CHECKSUM字节及精确file-set绑定到已验证preflight，guard在job前后检查这些实际对象，而非只哈希历史清单。初次source freeze不应伪造尚未存在的derived calibration；应提供明确、独占、不可变的**逐phase derived-input binding**，在risk开始前绑定实际原始assessor exports及其完整原字节SHA、父source/input freeze身份，并在每个risk job前后验证。项目profiles保持隔离，不能通过重新冻结source或替换父输入解除守卫；禁止重写profile原件或以路径存在代替身份。需要针对实际vault增加/移除/变更以及profile同路径替换的最小隔离检查。

### T6-C3 — P2 / Important：并发上限仅属于单个runner实例，不能保证全队列Coin串行

位置：`run-registered-phase.py:74`–`82`、`105`–`106`。

`max_running`和`active`是每次main的本地变量，没有controller级跨进程reservation/互斥。两个runner分别执行 `--kind perp --phase unscaled` 与 `--kind perp --phase budgets` 时，各自都可启动一个Coin进程。两phase使用不同output/start/log路径，因此exclusive receipt不会阻止重叠；多个Spot phase也可超出总计2进程。没有做真实或Coin并发probe，该结论直接来自独立main状态及registry的不交叠输出路径。

这是调度守卫缺口，不是要求绕过或修改账户锁。root人工按约定顺序启动可以避免触发，但当前helper本身不能兑现“all Coin invocations serialized”及phase failure期间不启动另一批的约束。

最小修复要求：在controller/task-owned路径实现所有实例共享的项目/phase执行reservation，最简单可让每项目一次仅有一个runner，内部Spot最多2、Coin最多1。已有或未知owner必须fail closed；reservation必须覆盖所有active子进程的实际生命周期，包括T6-C1的收尾，不因controller异常提前释放。不要修改HOME、UID或账户锁，不要自动删除未知/仍活跃的reservation。用无账户fake/harmless-process验证不同phase的第二runner在首次Popen前被拒绝，以及第一runner完全收尾后才允许后续phase。

## 正常路径与限制

对已经列入freeze的source和input，runner在job前后比较source identity、目录file-set及实际文件SHA；freeze helper要求clean committed tree并逐tracked research/runtime文件比较Git object，所选reviews、helpers、registry和new spec/protocol因此可被纳入字节绑定。正常已启动进程的非零exit、post-guard失败或无output会阻止后续启动并等待剩余active；本次发现集中在未覆盖的异常路径、遗漏的实际输入及跨实例并发边界。

start/log/finish正常路径使用exclusive写入，保留command、source/freeze/controller SHA及时间、exit、log/output SHA，没有自动retry或原生交易入口。它们是execution receipts，不是financial acceptance。四条已有synthetic guard checks没有覆盖本报告三个缺口。

本任务不验收实际完整68+账户、独立财务重算、条件combo/selected-budget后来适用的具体金融结果或最终广泛审查。冻结source跨全部phase及finance review的root操作约束仍必须遵守；本报告没有授权运行queue、重新选择时点/参数、改源/price/input、交易或native qualification。所有原经济目标、历史代理/污染限制和zero-native状态保持。

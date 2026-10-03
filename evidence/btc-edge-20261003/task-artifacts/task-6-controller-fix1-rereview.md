# Task 6 controller fix1 — scoped independent re-review

SPEC: **FAIL**.

QUALITY: **CHANGES REQUIRED** — T6-C1仍有可复现的controlled-signal收尾缺口；新增T6-C4接受显式失败的审计状态。

| 原发现 | 状态 | 范围 |
| --- | --- | --- |
| T6-C1 | **NOT ADDRESSED** | 普通launch/receipt失败路径已修复，但failure drain期间的首个SIGTERM仍会遗弃活跃child并缺失真实finish结果 |
| T6-C2 | **ADDRESSED** | actual vault/file-set及逐phase原始校准文件的字节绑定已加入；新增phase资格判断另有T6-C4 |
| T6-C3 | **ADDRESSED** | 固定项目reservation跨runner互斥、传给child的flock descriptor及unknown-owner fail-closed已加入 |

## 固定审查范围和证据

仅审查原T6-C1/C2/C3修复及fix新引入的Important问题；未重新审查旧producer/assessor或未变更的旧测试。读取了原controller review、fix1报告、完整root package以及三个helper和amended测试接口。

实际核对身份：

- Report：`5eff803f0e82865dac23bc128be1f88f3b18fe17f4d97c2f95e74abd33218375`。
- Root package：`c9880f31afe08ddc6cc95cd747fc0079ba1f4e4ee5f377c9a7ef479cd1ef3af2`。
- `prepare-source-freeze.py`：`3a78d0bb2c158cc0a5dc723ab149cb42b0f6456b416dd41fe6bd040cb876c2cf`。
- `run-registered-phase.py`：`628d549a8e485e5fe9db8384613db46dc828a035a7e1fc60cde1b9dbcd791bd7`。
- `bind-phase-inputs.py`：`3169ffc501ec2a82ec4eaf02d20f877e01d1e243e59512462676c3d9f16e7e12`。
- 原registry保持 `e58114f25f316d237860d2d6e6859d48614a57d69065524f6c256140c575fbfa`。

`task-6-controller-fix1-file-manifest.json` 的141项逐项检查了实际文件size/SHA，零不匹配。读取最终22项isolated tests的OK日志及对应测试范围，没有重跑原套件。审查前后helper字节未改变；并行forward实现的HEAD变化不作为本次外部helper身份。

没有编辑helper、worktree源码、registry或原件，没有commit、子代理、真实freeze/phase binding/queue、vault扫描/修改、Coin suite/producer或账户/原生/私有操作。新增探针仅临时无害Python child和纯函数fixture，无HOME/UID/账户锁变更。控制器锁仅在临时目录；复制的证据不含锁文件。原始失败证据保持，新证据单独保留。

## T6-C1 remaining — P1 / blocking：首个信号在failure drain的wait中仍会打断收尾

位置：`run-registered-phase.py:143`–`148`、`178`–`186`、`240`–`246`、`253`–`263`。

当第二个job启动失败后，`errors`非空使主循环直接调用第一个child的`finish()`，其中`process.wait()`可能等待很久。此时仍启用会raise的`interrupted()` handler；只有进入最外层finally时才忽略SIGTERM/SIGINT。如果首个SIGTERM在这个wait期间到达，handler抛RuntimeError，`finish`的`except BaseException`将它记为wait失败，却继续关闭日志、提前做post-guard/output hash，并写`state:unknown/exit_code:null/reaped:false`。随后主循环无条件`active.remove(entry)`。最终finally已没有该child，controller返回而child继续运行，真实退出结果和完成后输出哈希不再被记录。

当前inherited reservation仍保持占用，且不写reaped release，所以这**不是**Coin并发绕过，也没有伪造exit0；但它没有兑现已处理SIGTERM期间“drain/reap所有已启动children并保存真实finish”的T6-C1要求。SIGKILL/机器故障的不可恢复限制不能用于豁免正常处理的SIGTERM。

独立无害probe：temp目录，Spot第一job只是Python sleep0.6s后写`done`，第二job的output预先存在以触发已知failure drain；Popen成功后0.1s发送SIGTERM给该隔离probe控制器自身。job guards替换为no-op只隔离生命周期分支，没有生产source检查、账户程序或真实output path。当前helper输出：

```text
controller_exit: 2
elapsed_seconds: approximately 0.10
child_still_running: true
all_children_reaped: false
recorded_state: unknown
recorded_exit_code: null
recorded_reaped: false
```

Reviewer随后实际wait该child，确认`exit0`、输出`done`；没有遗留活跃process。新保留的probe results与逐job/phase/fallback/owner回执能看到controller早退以及reviewer cleanup后的真实结果。现有22测试覆盖signal during Popen，但未覆盖这个signal during failure-wait窗口。

最小修复：所有failure/shutdown drain在进入第一个阻塞wait前就进入不会raise中断收尾的信号状态，或让handler只记录deferred shutdown并确保被中断wait可继续reap。未reap的child不能仅因wait收到已处理信号就移出active；finish/output/post-guard应在真实结束后记录。保留首个错误和后续信号，不改未知owner/继承锁策略，不伪造成功，也不覆盖第一次失败回执。新增一个failure drain期间首个SIGTERM/SIGINT的最小隔离测试，断言run_jobs返回前child真实结束、actual exit与完整输出hash已保存。

## T6-C4 — P2 / Important / fix-new：phase eligibility 接受 `monetary_audit.passed:false`

位置：`bind-phase-inputs.py:50`–`57` 的 `validate_report()`。

新helper要求“complete audited account”，但其审计判断是 `bool(account.get('monetary_audit'))`。任何非空字典，包括`{'passed': False}`、`{'passed': None}`或根本无passed的字典，都满足这个条件。它同时验证status/reasons、source字符串身份和raw原字节SHA，却不检查报告内显式审计失败与complete状态的矛盾。现有positive synthetic fixture使用`{'synthetic': True}`，因此也未覆盖实际schema的passed边界。

独立pure-function probe用实际assessor接口取得52个原unscaled identity，创建对应临时raw bytes和正确SHA，project/source/contracts声明与synthetic freeze一致；全部account标为complete/reasons空，但全部`monetary_audit={'passed':False}`。原`validate_report()`结果：

```text
EXPLICIT_FAILED_AUDITS 52
PHASE_BOUND_RAW_COUNT 52
```

该probe只证实**自动phase资格校验**接受显式失败状态，不声称当前已冻结assessor会自然生成这种矛盾报告，也不把matching source字段/raw hash等同于实际由该source执行的证明。当前真实assessor的complete货币审计应产生`passed:true`；binding helper应直接拒绝与这个接口矛盾的输入，不能把字节一致性或未来独立finance review当作豁免。

最小修复：要求`monetary_audit`是预期字典且`monetary_audit.get('passed') is True`，拒绝missing/null/false以及1、字符串等非布尔值；保持完整52账户和report中全部已存在账户的检查、负候选结果、后续pending inventory和原字节/source绑定语义不变。这只核验审计一致性，无需在controller复制完整金融重算。修正positive fixture为真实的passed布尔接口，增加上述failure/unknown/type边界。该要求不能变成“所有候选eligible”：正确审计过但策略门槛不合格的账户仍必须保留。

## 已关闭的修复路径

T6-C2：freeze解析现有vault snapshot的实际`path/size/sha256`字段，核验actual files并将Coin vault全部对象和精确all-file tree纳入guard；parent freeze anchor禁止正常重新冻结；新phase helper将父freeze、实际report、report命令指定的原始export、registered production profile与所有report raw账户绑定，production/export必须原字节相等，runner在每个risk job前后复核phase file及bound bytes。原history-manifest-only遗漏及未绑定profile路径问题已修复。T6-C4是其新增语义资格判断的问题，不否定这些字节绑定改进。

T6-C3：固定ART下每项目一个reservation，跨phase实例争用同一flock；正常内部Spot上限2/Coin上限1；child继承fd，parent不显式LOCK_UN；durable owner缺少匹配all_children_reaped release时继续failclosed。读取的隔离检查包括different-phase拒绝、已完成释放、unknown-owner及parent退出后的继承锁。T6-C1 probe中未reap时没有错误释放reservation，也印证该防线保持。

普通已有output、Popen/receipt/hash/guard失败的共同收尾及durable fallback比原版本完整。新conditional registry沿固定entrypoint、ALL-eligible组合和完整stress/risk/budget matrix限制，没有修改原50job registry。本次不扩展到实际组合结果或重新判定选择合同。

## 保留的独立探针证据

- 可读复现脚本：`task-6-controller-fix1-rereview-probe.py`。
- 证据目录：`task-6-controller-fix1-rereview-probes/`，15项逐文件manifest，临时路径仅表示synthetic产物，不能用作真实phase输入。
- `probe-results.json` SHA：`b26a84142088386521391f0a2b46df8a6b11020195fa2909cd8a92599c6aa320`。
- `manifest.json` SHA：`5a3ef6ebc727d7cdb26f426e0531efa2cd696ebf097e2b047373661857781947`。
- 保留stdout、job start/finish/not-started、phase finish、fallback诊断、owner证据以及failed-audit synthetic report；不含实际controller锁或任何真实账户材料。

## 限制

未运行真实freeze/队列、profile production binding、vault全量hash或独立金融审查。本次通过项是helper修复的scoped工程结论；完整68+financial inventory、实测收益/采用决定和最终广泛审查仍属后续root工作。不得因这两项剩余问题自动reroll、删锁、改HOME/UID或绕过冻结条件。当前尚未启动真实financial queue，因此应在首次启动前完成修复并保留本轮first-attempt证据。

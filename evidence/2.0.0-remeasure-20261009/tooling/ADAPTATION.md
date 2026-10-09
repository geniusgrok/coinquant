# v2 证据保存修复

本轮最终 producer 为 `9b5ee3aea3a4f977b0b20c7b25e4a81ecdc5b7b188d9f26a3e119e03101f5413`。生产源码、全部九个 research 模块、价格、费用、匹配、日程与风险值相对第一次配对完全不变，只有 driver 的路径保存 I/O 改变。

第一次配对在 previous 478/795 的第二段发现 gzip 路径内容截断，缺 147543 个原观测点。原失败不续接，也不改为通过。事实、未能证明的底层原因与新执行登记见父目录 `ATTEMPTS.json`、`PROTOCOL.md` 及 `TRACE_FAILURE_DIAGNOSIS.json`。

新版每段 gzip 先写入 `SpooledTemporaryFile`，内存上限 64 MiB，超限转匿名临时 FD；关闭 gzip 后才独占写 `.publishing`、fsync 文件、原子链接到最终名、核对路径与发布 FD 的设备/节点/长度，并 fsync 目录。最终仍通过原有完整 gzip、逐点序号/数量和 rolling hash 读回门槛，任何冲突或不完整均失败。

定向验证：内存与实际 spill 解码相等；模拟长期打开的具名文件被替换能重现旧的 close 成功但路径 EOF；冲突最终路径保持原件并拒绝；两臂实际合成短会话、checkpoint 续接和路径篡改拒绝保持通过。两臂各 6 次原历史会话与独立财务/路径审计再次通过。完整795结果以最终回执和独立审计为准。

`ADAPTATION_V1.md` 和 `tooling-registration-v1.json` 是第一次 producer 的历史登记，保留原字节，不代表 v2 身份。它们详述从 PR72 工具恢复到第一版适配的经过。

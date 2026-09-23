# R10 原件重建

从原件索引中的完整三个依赖包恢复（不要用历史源码覆盖当前代码）：bounded 的 `inputs/development` 与 `old-controls/development`，PIR1 的 `raw/post-impulse-restart-20260923/{development-entry-minutes,MINUTE_REQUEST.development.json,mark-repair}`，归属纠错的 `input-supplements/sx60/exit-minutes`。先核验包与成员 checksum。

在本研究提交的源树执行以下等价 Python 调用，输出到不存在的新目录：

```python
from pathlib import Path
from decimal import Decimal as D
from research.bounded_execution_replay import prepare
from research.sustainable_replay import exit_minutes, run_account
b, p, c = (Path('bounded'), Path('pir/raw/post-impulse-restart-20260923'),
           Path('correction/input-supplements/sx60/exit-minutes'))
x = prepare(b/'inputs/development', b/'old-controls/development',
            p/'development-entry-minutes', p/'MINUTE_REQUEST.development.json', p/'mark-repair')
y = exit_minutes(c, x)
assert y[-1] == '9b036837f4eb462d672524f9b032adc7a9a9ba85cce071b33b268ab658747645'
run_account(b/'inputs/development', Path('R10-development'), y, 'SX60',
            stop_risk_share=D('.10'),
            research_protocol='evidence/stop-risk-core-20260923/PROTOCOL.md')
```

结果目录包括完整 `equity.csv.gz`、`orders.csv.gz`、`decisions.csv.gz`、`execution.jsonl`、所有资金与账本审计和测量源码。相邻的 `R10-development.invocation.json` 冻结配置和输入；原件包及依赖索引另见 `ORIGINALS.json`。

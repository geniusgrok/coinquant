# Pancakequant Repository Instructions

Repository: `ychenracing/pancakequant`

This file defines repository-level engineering rules. Account-level instructions define general collaboration principles. Current explicit task authorization overrides historical work, but does not override security requirements, repository protection, or safety boundaries.

## 1. Project Scope

Pancakequant is a cryptocurrency quantitative trading system derived from an algorithmic trading framework. The repository may contain strategy research, backtesting, paper trading, exchange integration, and execution-related components.

Maintain a clear separation between:

- research and production execution;
- backtest, paper trading, testnet, and live environments;
- strategy logic, risk controls, execution infrastructure, and exchange adapters.

Do not assume backtest performance represents live performance.

## 2. Engineering Principles

- Understand the real call path before changing code.
- Prefer existing abstractions over duplicate implementations.
- Fix root causes instead of adding temporary patches.
- Avoid unnecessary refactors and compatibility layers.
- Keep changes integrated into the current architecture.
- Do not add permanent switches or dead code for one-off experiments.

Use minimal sufficient validation. Do not require full test suites or full historical runs for every small change unless the modified area affects critical behavior.

## 3. Trading Safety

Changes affecting trading behavior require special care.

Preserve:

- order idempotency;
- position consistency;
- account state consistency;
- exchange synchronization;
- error handling during network failures;
- safe handling of unknown execution states.

Never:

- hard-code credentials;
- expose API keys;
- bypass risk controls only to improve historical results;
- treat failed or partial execution as successful.

Real-money trading actions require explicit authorization.

## 4. Quantitative Validation

When evaluating strategies, distinguish:

- backtest results;
- paper trading results;
- testnet results;
- live trading results.

Consider:

- fees;
- slippage;
- turnover;
- drawdown;
- robustness;
- execution feasibility;
- overfitting risk.

Preserve evidence identity including source revision, configuration, data range, and important parameters.

## 5. Recovery and Handoff

For long tasks preserve:

- code state;
- important evidence;
- branch and commit information;
- next recovery steps.

Do not create duplicate state systems when an existing recovery entry exists.

A checkpoint or handoff is not completion. Completion requires satisfying the current task objective and reporting remaining risks honestly.

## 6. Git Operations

Prefer normal Git operations. When large files or artifacts are involved:

- avoid transferring huge content through model context;
- prefer streaming or chunked transfer;
- preserve original artifacts when required;
- verify remote state after writes.

Do not claim completion without verifying the resulting repository state.

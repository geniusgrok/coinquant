# Binance durable-intent read-only recovery

The default CLI now checks pending Binance-native intents after UID-bound account observation, validates returned order scope/type/quantity/protection fields, and refreshes the account after recovery queries. Terminal cancellations with partial execution retain the executed amount; an active child keeps a canceled conditional parent unresolved. Missing/expired history, invalid fills, payload mismatches and legacy intent kinds stay pending. No resubmission, order write or credential/account change occurs.

Source checked2026-09-21: https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade — Query Algo Order, Query Order, New Algo Order and Modify Isolated Position Margin. Conditional parent and actual child are separate; closePosition conditional orders do not establish atomic entry plus protection. Documentation is not testnet evidence.

Verified offline: terminal partial-fill cancellation, active child after parent cancel, inconsistent filled quantity, payload mismatch, missing history, unsupported legacy intents, UID-first observation and post-recovery refresh. This implements a recovery component, not a completed production write lifecycle.

Still unresolved: entry-to-protection race/crash safety, parent residual, protection replacement races, isolated margin write recovery and native testnet lifecycle. The CLI execution gate stays closed. No account was contacted.

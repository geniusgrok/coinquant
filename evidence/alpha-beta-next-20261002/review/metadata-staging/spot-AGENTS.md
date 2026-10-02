# Spotquant engineering rules

Repository: geniusgrok/spotquant. Use the personal / geniusgrok GitHub connection.

## Current mandate

One manually triggered Binance BTCUSDT spot system. Long or USDT cash; no borrow, short, futures or leverage. Two runtime repositories remain separate: Spotquant spot, Coinquant perpetual; Starquant historical reference/FX only.

The current development default is SMA30/40/50 consensus plus the registered `atr-stop`, rule `2026-10-02-atr-stop`. Genuine entries, two completed closes, fresh cross, historical high-price/repair/ordinary exits and pooled90%-free-cash genuine NEW BUY rule remain. Held positions are never topped up/rebalanced. The shared session uses completed ATR14 (arithmetic mean of the last fourteen completed true ranges) decision protection `clip(4*ATR14/completed_close,.10,.30)`, confirmed allocated native stop floors and actual fill-based peaks; stops never loosen. Through-mark protection reduces normally; exits take priority and BUY uses free cash plus the remaining whole-account capital ceiling. Stored Model/follow catch-up remains28%; no stop amendment while stopped. Default sizing scale1; risk calibration exists only in verified offline replay, not live configuration.

Model version5 persists fourteen timestamped completed true ranges. Old rule/checkpoint, missing/malformed durable state, research wrappers and incompatible pending allocations reject before Lifecycle recovery even when flat. Do not discard SQLite, create an empty directory to imply flatness, or infer migration. See research/adoption-GUIDE.md.

Frozen shared runtime0c52c812301de3712f3637a1ce1b1241de0c40f1 / Python619570fb7baa586f28ad5de2a440d7752a536cc8f8ce7e357264612e65801537 was separately replayed in five complete canonical cases and compared in all six evidence groups with frozen research8ca. Immutable assessor99 binds those cases to the reviewed final64 inventory and a separate adoption decision. Later metadata/merge HEADs do not relabel raw measurement identities. Full financial and exact-source evidence is in evidence/alpha-beta-next-20261002/; default selection does not establish native qualification.

Economic window2020-01-01T00:00:00Z through2026-09-20T00:00:00Z exclusive, initialCNY10000/no deposits, original795 finite sessions (registered outage789), cost-net CAGR>=100%/continuous MDD<=30%. Current unscaled default55.2180% CAGR/36.4122% continuous OHLC proxy MDD versus old consensus51.8503%/41.2073%. Original targets remainNOT_MET. Worst CNYday worsens from−14.4837% to−15.8029%; underwater713days unchanged. No continuous proxy second-engine replay, prospective-alpha proof or native qualification is implied. Native cases0/actual account-days0/NOT_QUALIFIED.

All seven spot candidates×four stresses and seven actual trained-risk base accounts were retained. Only atr-stop passed all paired selection gates; a one-component combination reuses that account. Permanent core fails the outage selection gate and actual beta upper band. Training uses only7312020–2021USDT returns; new2022+BUY scaling, no retroactive held sizing/curve scaling. Actual ATR diagnostic ratio.9972720085277638 and2022+beta.3370648/vol29.0160% are diagnostic, not adopted default sizing; HAC7 interval includes0. Future diaries bind source99 research, remain all cash/zero observations at actual initialization and cannot masquerade as current runtime trades/account-days.

The current canonical meter is `python -m research.adoption_spot --scenario base --out /tmp/adoption-base-NEW.json` with clean committed source and original verified inputs. Source-bound historical study reproduction needs the retained original executable commits. `research.complete_spot` default remains the frozen equal-allocation historical benchmark; `research.rebuild` is a different historical daily-bar account. Old P3/P4/equal/consensus and old joint allocation figures retain their original source identities and do not describe the current default. Never add leverage, move the window, lower goals or turn the historical sample upper bound into expected return.

One manual session repeatedly observes/reconciles/decides until deadline/interruption; no background daemon. Default read-only; `run --execute` stays blocked. Owner Demo requires explicit environment, matching UID, positive capital ceiling and persistent scoped directory. Unknown sent identities are never blindly resubmitted. Native stop replacement retains its confirmed-cancel gap and remains unverified. Engineering work authorizes no accounts/orders/transfers/credentials/settings.

Main is the development/integration baseline, not profit/safety qualification. Use normal fast-forward/PR operations, verify actual remote HEAD and preserve parallel work; no force push/history deletion. Use PROJECT_STATE.md/HANDOFF_PROMPT.md as the only current progress/recovery entries. Run all Coin synthetic account producers/tests with overlapping UIDs strictly serially; cache/state directories do not isolate HOME-based account locks. Do not alter HOME or remove/bypass locks. Keep measured source frozen until all financial work and audits are complete.

## Execution safety

Default read-only; live writes blocked. Explicit owner Demo is a validation entry, not qualification. Engineering work does not authorize orders, transfers, credentials, or account-setting changes. Unknown balances and external BTC block new risk. Do not treat a new empty state directory as proof the account is flat. Do not invent a background daemon.

Credentials: `SPOTQUANT_BINANCE_KEY` / `SPOTQUANT_BINANCE_SECRET` for live, `SPOTQUANT_BINANCE_DEMO_KEY` / `SPOTQUANT_BINANCE_DEMO_SECRET` for demo. Client ids use `sq-`. Scope is `binance:BTCUSDT:spot:{live|demo}:{uid}`.

## Verification

One CI workflow, Python 3.13, `contents: read`, timeout 10 minutes, no secrets, no market download, no full historical research. Runtime dependencies stay in the standard library.

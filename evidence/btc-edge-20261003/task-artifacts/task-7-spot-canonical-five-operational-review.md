# Spot canonical five-account launcher — scoped operational review

**PASS. QUALITY: APPROVE for collecting the five registered accounts.** No Critical/Important finding was identified in the new launcher glue or freeze bindings. This is collection acceptance only; no account was launched during review, and financial/canonical equivalence, promotion, export and initialization remain pending.

Reviewed the complete external `run-spot-canonical-five.py`, actual `spot-canonical-five-launch-freeze.json`, their registry/source/archive bindings, and only the reused controller interfaces needed to establish reservation, guard and failure behavior. The already approved serial core was hash-checked and reused; it was not subjected to another broad review or test run.

Exact reviewed artifacts:

| Artifact | SHA256 |
|---|---|
| `run-spot-canonical-five.py` | `d5d59748d82ab84f97a77d2704cde764e2d7d5f7cf365fbd1d3417aacd87faf6` |
| `spot-canonical-five-launch-freeze.json` | `793cbee822a2234e4c7cfadab6e9be60b6ab9b71b72ae6085dfc1bd700958f99` |
| Reused `run-registered-recovery.py` | `cdc8538d01b46963c12b8810b468cafd754b58303a69495cfb32f4e62d497185` |
| `five-canonical-commands-fix3.json` | `2afa67613285f9f71a4311701d802d1e3df4983503c6967f91c707fee7bbfc6d` |
| `spot-canonical-reviewed-source-fix3.tar.gz` | `250bd1381114afde1b06d835185b908b1b499d3c773d53bf4ac6baecf580175a` |

The registry selects exactly base, fee150, slip2, outage and unity-risk-base, in that order, with the previously approved argv/output paths and isolated working directory. All five source expectations equal the freeze: HEAD `609606d9c0e0ad8d3c3038b329c9c4ab6d1b9629`, Python SHA `b81f1bfee086e875cbf8ff22a67b2cfdff419130a7918a6ce8754b2e9e2936c5`, protected bytes/modes SHA `eeb22cfe227c0d9ed60c937da330f515a6093dfcd82205114644e8bed8c7c7f6`. The isolated source remains clean at that HEAD. Every protected archive member's bytes and mode match the frozen source map. All five output files are absent at review time.

The original Spot freeze record is exactly equal to the original parent freeze's Spot record; no source refreeze or original identity relabeling occurred. All 316 original bound files match actual sizes/hashes, and the declared market directory inventory matches. All 12 additional bound files also match, including this launcher's bytes, registry, scoped code approval, archive, current/original-equal calibration, preliminary and five original raw account anchors. Original measured source remains 74bd6e035e36531c517029077c1a9e2e5ec44516 / Python f2d6c3e73c2acb7b328a7a0e2678bb95ceb77d8a17a46139abfe8b357befdbf6.

The wrapper calls `run_jobs` once with the same task-artifacts root and kind=`spot`, so a single existing Spot reservation covers all five jobs. Concurrency remains one, the lease descriptor is inherited by each child, and no account lock or UID mechanism is replaced. The supplied check runs before each launch and after each real child exit. It binds the freeze/controller, all new files, original source/input inventory and current canonical protected source; failures propagate into the existing stop/drain/reap/receipt flow. Nonzero child exit, missing output/hash, guard failure or receipt failure prevents subsequent launches. No retries or overwrite path were introduced.

Scratch creation is exclusive at `/workspace/scratch/btc-alpha-beta-edge-20261003/canonical-tmp/spot`, with an owner record. The directory is absent before launch. Child environment inherits HOME/UID and other settings with only TMPDIR overridden. The 4 GiB free-space floor is enforced before and after each job; the containing filesystem had 9,765,933,056 free bytes when inspected. This snapshot does not replace the launch guards.

The runner preserves separate original and canonical source identities in receipts and explicitly records adoption_approved=false, native cases 0 and actual account-days 0. The five actual outputs still require complete money/archive validation and independent six-group equivalence review alongside the original financial proof before any promotion/export/init.

Only this review report was written. No launcher/core execution, account call, producer, test/fullsuite, public check, source modification, lock/HOME/UID change, child agent or financial attestation occurred.

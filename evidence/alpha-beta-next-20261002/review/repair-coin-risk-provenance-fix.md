# Narrow provenance fix

The only controller change replaces `zip_bytes_verified_by_approved_restore: True` with `zip_bytes_must_be_verified_by_approved_restore: True` in `public_catalog()`. Catalog matching and the pre-restore attempt intent now record an obligation, never completed ZIP verification. The existing subsequent approved-restore receipt and SHA binding remain unchanged. No command, exclusion, one-attempt guard, six-fingerprint gate, or projection behavior changed.

- Pre-fix exact helper: `/workspace/btc-alpha-beta-next/review/repair_coin_risk_incumbent_pre_provenance_fix.py`; SHA256 `083068bd2bd20070f81237ef6be4459cd8dcddbbdfbeae1d2ffd035c4fafdbdc`.
- Updated helper: `/workspace/btc-alpha-beta-next/review/repair_coin_risk_incumbent.py`; SHA256 `957d4b0171469351c38b1a27bdc579a368dc0408fa37c348686d24aeb1c6c5d8`.
- Helper diff: `/workspace/btc-alpha-beta-next/review/repair-coin-risk-provenance-fix.diff`; exactly one field-name replacement, independently asserted against the old bytes.
- Updated fixture: `/workspace/btc-alpha-beta-next/review/repair_coin_risk_fixture.py`; SHA256 `4415c047d8fe7d4f27205b3607f97aecf467d4a7196ca70d7047c9a25c0222e5`.
- Fixture pre-fix copy: `/workspace/btc-alpha-beta-next/review/repair_coin_risk_fixture_pre_provenance_fix.py`; SHA256 `535212343d8ff7acdbf1aafa18d12a28decd8e2d3cdda2bc255064db79849a03`.
- Fixture diff: `/workspace/btc-alpha-beta-next/review/repair-coin-risk-provenance-fix-fixture.diff`.

Validation: `PYTHONDONTWRITEBYTECODE=1 python /workspace/btc-alpha-beta-next/review/repair_coin_risk_fixture.py` exited 0; **23 checks passed**, including every original 21 check (multiset comparison preserves duplicate test labels) and two added checks. New checks use the real public_catalog on temporary synthetic records, inspect the persisted intent inside a failing restore stub and again after failure/relaunch refusal, require the obligation field, reject the old verified field, and confirm no success receipt exists. Elapsed wall time: 1.184 seconds. Exact output: `/workspace/btc-alpha-beta-next/review/repair-coin-risk-provenance-fix-fixture.log`; SHA256 `fdbc894ed984bff13c2c9cde59196ff75f913bcc81c6aa0504a49b416685b44f`.

To obey the no-frozen-import constraint, the fixture now extracts only the same eight pure validation function definitions from the frozen assessor source using AST. No research module is imported; the fixture asserts that fact. Synthetic external Git source-proof remains stubbed as before. This is fixture plumbing only, not a production verifier change.

No actual controller launch, restore, producer, account/cache/State operation, frozen module import, product edit, or Git operation occurred. Original helper/fixture evidence is retained. Ready for scoped rereview; no actual replay authorized by this report.

# Binance stable-identity reconciliation addition

Official source checked 2026-09-21:
https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade

Query Algo Order accepts clientAlgoId and returns actualOrderId. Query Order
accepts origClientOrderId or numeric orderId with symbol. Both document history
retention limits: old unfilled canceled/expired orders can disappear after three
days and orders after ninety days. Absence is therefore not proof of no prior write.

The research-only reader now queries durable client identities and, when present,
the conditional parent's actualOrderId. It verifies symbol, identity, side and
position side. A canceled parent does not suppress child reconciliation. Unknown,
expired or conflicting results never grant resubmission permission. This is an
observation component, not a complete write/recovery lifecycle or an assertion
that partial fills were protected. No private account was queried.

Targeted fake-response checks cover canceled-parent/partially-filled-child,
child identity mismatch, unavailable history and client identity mismatch.

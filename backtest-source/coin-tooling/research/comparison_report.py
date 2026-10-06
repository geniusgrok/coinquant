from collections import Counter
from decimal import Decimal as D
def audit(row, initial_wallet, final_mark=None):
    qty, entry, realized = D(0), D(0), D(0)
    for trade in row['trades']:
        part, price = D(trade['qty']), D(trade['price'])
        signed = part if trade['side'] == 'BUY' else -part
        if not qty or qty * signed > 0:
            entry = (abs(qty) * entry + part * price) / (abs(qty) + part)
        else:
            closing = min(abs(qty), part)
            realized += closing * (price - entry) * (1 if qty > 0 else -1)
            if part > abs(qty):
                entry = price
        qty += signed
        if not qty:
            entry = D(0)
    totals = Counter()
    for income in row['funding_ledger']:
        totals[income['incomeType']] += D(income['income'])
    wallet = initial_wallet + sum(totals.values(), D(0))
    near = lambda first, second: abs(first - second) <= D('.00000001')
    checks = {'trade_quantity_matches_position': near(qty, D(row['position'])),
              'realized_pnl_matches_cash_ledger': near(realized, totals['REALIZED_PNL']),
              'fees_match_cash_ledger': near(D(row['fees']), -totals['COMMISSION'] - totals['INSURANCE_CLEAR']),
              'funding_matches_cash_ledger': near(D(row['funding']), -totals['FUNDING_FEE']),
              'no_external_cash_flows': set(totals) <= {'REALIZED_PNL', 'COMMISSION', 'INSURANCE_CLEAR', 'FUNDING_FEE'}}
    if not qty:
        checks['flat_equity_matches_wallet'] = near(wallet, D(row['final_usdt']))
    else:
        checks['open_equity_matches_valued_ledger'] = (final_mark is not None and
            near(wallet + qty * (final_mark - entry), D(row['final_usdt'])))
    return {'passed': all(checks.values()), 'checks': checks, 'wallet_from_ledger_usdt': str(wallet),
            'position_from_fills_btc': str(qty), 'entry_from_fills_usdt': str(entry),
            'income_totals': {key: str(value) for key, value in totals.items()}}


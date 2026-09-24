"""Reproduce PF55 budget exhaustion from its complete account original."""
import argparse
import csv
import gzip
import json
from bisect import bisect_right
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path


def audit(root):
    parents = json.loads((root / 'execution_summary.json').read_text())['parents']
    with gzip.open(root / 'equity.csv.gz', 'rt') as stream:
        equity = list(csv.DictReader(stream))
    times, peaks, flat = [], [], []
    peak = D(0)
    for row in equity:
        peak = max(peak, D(row['equity_usdt']))
        times.append(int(row['time']))
        peaks.append(peak)
        if D(row['quantity']) == 0 and row['event'] in ('open', 'close'):
            flat.append(row)
    with gzip.open(root / 'orders.csv.gz', 'rt') as stream:
        orders = list(csv.DictReader(stream))
    filled = [p for p in parents if D(p['filled']) > 0]
    last = filled[-1]
    last_flat_before = next(r for r in reversed(flat) if int(r['time']) <= last['call_time'])
    first_flat_after = next(r for r in flat if int(r['time']) > last['last_fill'])
    before = D(last_flat_before['equity_usdt'])
    after = D(first_flat_after['equity_usdt'])
    call_peak = peaks[bisect_right(times, last['call_time']) - 1]
    # PF55 froze this budget at the call; the remainder cannot grow while flat.
    frozen = D(last['risk_budget'])
    final = D(flat[-1]['equity_usdt'])
    final_peak = peaks[-1]
    peak_row = next(r for r in equity if D(r['equity_usdt']) == final_peak)
    assert final == after
    assert abs(final - D('.55') * final_peak - D(parents[-1]['risk_budget'])) < D('.00000001')
    assert all(p['filled'] == '0' for p in parents[parents.index(last)+1:])
    post = [o for o in orders if int(o['time']) >= last['first_fill']]
    entry = next(o for o in post if o['event'] == 'entry')
    stop = next(o for o in post if o['event'] == 'stop')
    quantity = D(entry['quantity_btc'])
    gross = quantity * (D(stop['price_or_mark']) - D(entry['price_or_mark']))
    entry_fees = D(first_flat_after['fees']) - D(last_flat_before['fees'])
    funding = D(first_flat_after['funding']) - D(last_flat_before['funding'])
    assert abs(gross-entry_fees-funding-(after-before)) < D('.00000001')
    minimum_qty = max(D('.001'), (D('50')/D(parents[-1]['original_price'])/D('.001')).to_integral_value(rounding='ROUND_CEILING')*D('.001'))
    price = D(parents[-1]['original_price'])
    stop_price = D(parents[-1]['stop'])*(1-D(parents[-1]['slippage'])-D(parents[-1]['spread'])/2)
    # The replay uses a 2026 instrument-rule snapshot and 0.075% fee; exit impact can add risk.
    minimum_risk = minimum_qty*(price-stop_price+D('.00075')*(price+stop_price))
    assert minimum_risk > final - D('.55')*final_peak
    return {
        'parents': len(parents), 'filled_parents': len(filled),
        'last_fill_utc': datetime.fromtimestamp(last['first_fill']/1000, timezone.utc).isoformat(),
        'last_exit_utc': datetime.fromtimestamp(int(first_flat_after['time'])/1000, timezone.utc).isoformat(),
        'last_parent_budget_usdt': str(frozen), 'last_entry_equity_usdt': str(before),
        'last_exit_equity_usdt': str(after), 'last_trade_net_equity_change_usdt': str(after-before),
        'high_water_before_last_entry_usdt': str(call_peak),
        'high_water_first_observed_utc': datetime.fromtimestamp(int(peak_row['time'])/1000, timezone.utc).isoformat(),
        'high_water_first_observed_quantity_btc': peak_row['quantity'],
        'last_trade_gross_pnl_usdt': str(gross),
        'last_trade_fees_usdt': str(entry_fees),
        'last_trade_funding_usdt': str(funding),
        'post_fill_order_events': post[-5:],
        'final_equity_usdt': str(final), 'final_high_water_usdt': str(final_peak),
        'final_spendable_budget_usdt': str(final - D('.55')*final_peak),
        'last_parent_minimum_executable_quantity_btc': str(minimum_qty),
        'last_parent_minimum_stop_risk_lower_bound_usdt': str(minimum_risk),
        'remaining_unfilled_parents': len(parents)-parents.index(last)-1,
        'flat_after_last_exit': all(D(r['quantity']) == 0 for r in equity if int(r['time']) >= int(first_flat_after['time'])),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('original', type=Path)
    print(json.dumps(audit(parser.parse_args().original), indent=2))

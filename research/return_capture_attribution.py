"""Event alignment of a preserved account; diagnostics are not counterfactual PnL."""
import argparse
from bisect import bisect_left
from collections import Counter, defaultdict, deque
import csv
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
from pancakequant.research import iso
from research.persistent_hold_replay import inputs, channel_state, DAY, HOUR


def trace(root, name):
    with gzip.open(root / (name + '.csv.gz'), 'rt') as f:
        return list(csv.DictReader(f))


def analyze(run, native, warmup, repairs, output):
    result = json.loads((run/'result.json').read_text())
    series, _, warm, identity = inputs(native, warmup, repairs, result.get('validation_used', False))
    trade = series['klines']; start = min(trade); end = max(trade) + HOUR
    decisions = trace(run, 'decisions'); orders = trace(run, 'orders'); equity = trace(run, 'equity')
    times = [int(r['time']) for r in decisions]
    changes = []; states = {}; window = deque(maxlen=21); regime = 0; anchor = None
    failed = None; failures = []
    for t in range(min(warm), end, DAY):
        source = warm if t < start else trade
        rows = [source[s] for s in range(t, t + DAY, HOUR)]
        bar = (max(D(r[2]) for r in rows), min(D(r[3]) for r in rows), D(rows[-1][4]))
        window.append(bar); new = channel_state(window, regime)
        if new != regime:
            if failed is not None:
                failed['end'] = iso(t + DAY); failures.append(failed); failed = None
            anchor = bar[1 if new > 0 else 0]
            if t + DAY >= start:
                idx = bisect_left(times, t + DAY)
                changes.append(dict(time=iso(t + DAY), old=regime, new=new,
                                    completed_close=str(bar[2]),
                                    prior_high=str(max(x[0] for x in list(window)[:-1])),
                                    prior_low=str(min(x[1] for x in list(window)[:-1])),
                                    first_trigger=iso(times[idx]) if idx < len(times) else None))
        elif regime and anchor is not None and failed is None:
            if (regime > 0 and bar[2] < anchor) or (regime < 0 and bar[2] > anchor):
                failed = dict(start=iso(t + DAY), direction=regime, anchor=str(anchor), close=str(bar[2]))
        regime = new; states[t + DAY] = regime
    if failed is not None:
        failed['end'] = iso(end); failures.append(failed)
    exits = []
    for i, r in enumerate(orders):
        if r['event'] not in ('regime_exit', 'stop', 'stop_gap', 'take', 'take_gap', 'liquidation'):
            continue
        t = int(r['time']); nxt = next((x for x in orders[i+1:] if x['event'] == 'entry'), None)
        nt = int(nxt['time']) if nxt else end
        exits.append(dict(time=iso(t), event=r['event'], exited_quantity=r['quantity_btc'],
                          next_entry=iso(nt) if nxt else None, flat_hours=(nt-t)/HOUR,
                          next_quantity=nxt['quantity_btc'] if nxt else None,
                          intervening_actions=dict(Counter(d['action'] for d in decisions if t <= int(d['time']) < nt))))
    # Use row indices: multiple extrema share timestamps, so time slicing loses endpoints.
    peak = 0; worst = (D(0), 0, 0)
    for i, r in enumerate(equity):
        if D(r['equity_usdt']) > D(equity[peak]['equity_usdt']): peak = i
        dd = 1 - D(r['equity_usdt']) / D(equity[peak]['equity_usdt'])
        if dd > worst[0]: worst = (dd, peak, i)
    dd, a, b = worst; parts = defaultdict(D)
    for i in range(a+1, b+1):
        r, prev = equity[i], equity[i-1]
        fees = D(r['fees'])-D(prev['fees']); funding = D(r['funding'])-D(prev['funding'])
        parts['fees'] -= fees; parts['funding'] -= funding
        q = D(prev['quantity'])
        parts['long_mark_execution' if q > 0 else 'short_mark_execution' if q < 0 else 'flat_to_entry_execution'] += D(r['equity_usdt'])-D(prev['equity_usdt'])+fees+funding
    delta = D(equity[b]['equity_usdt'])-D(equity[a]['equity_usdt'])
    assert abs(sum(parts.values(), D(0))-delta) < D('1e-18')
    result = json.loads((run/'result.json').read_text())
    assert abs(dd-D(result['mdd_conservative_envelope'])) < D('1e-18')
    recovered = next((r for r in equity[b+1:] if D(r['equity_usdt']) >= D(equity[a]['equity_usdt'])), None)
    classifications = Counter()
    for r in equity:
        if r['event'] != 'open': continue
        t = int(r['time']); signal = states[t//DAY*DAY]; q = D(r['quantity'])
        classifications['no_direction' if not signal else 'flat_with_direction' if not q else 'aligned' if q*signal > 0 else 'opposite_waiting_trigger'] += 1
    sizing = []
    previous = None
    for r in decisions:
        if previous is not None and r['action'] in ('rebalance_add','rebalance_reduce'):
            old_target = D(previous['edge_target_fraction'])
            if old_target and D(previous['equity']) > 0:
                t, pt = int(r['time']), int(previous['time'])
                price = max(D(trade[t][1]), D(series['markPriceKlines'][t][1]))
                old_price = max(D(trade[pt][1]), D(series['markPriceKlines'][pt][1]))
                sizing.append(dict(time=iso(t), action=r['action'], quantity_before=r['quantity'],
                    requested=r['requested_quantity'], accepted_delta=r['accepted_quantity'],
                    equity_factor=str(D(r['equity'])/D(previous['equity'])),
                    volatility_target_factor=str(D(r['edge_target_fraction'])/old_target),
                    inverse_price_factor=str(old_price/price), binding=r['binding_cap']))
        previous = r
    out = dict(qualification='DIAGNOSTIC_ONLY', sizing_changes=sizing, source_hashes=result['source_hashes'],
               schedule_sha256=result['schedule_sha256'], input_identity=identity,
               actions=dict(Counter(d['action'] for d in decisions)),
               hourly_state_counts=dict(classifications), regime_changes=changes, failed_breakout_intervals=failures,
               exit_intervals=exits, drawdown=dict(fraction=str(dd), peak=equity[a], trough=equity[b],
                   recovery=recovered, exact_recorded_equity_delta=str(delta),
                   telescoping_components={k:str(v) for k,v in parts.items()}),
               limitations=['Components describe recorded mark/execution changes, not independent causal effects.',
                            'High/low envelope ordering is conservative, not an observed tick path.',
                            'No posthoc directional gap return is labeled recoverable profit.'])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2)+'\n')
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('run','native','warmup','repairs','output'): p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); r = analyze(a.run,a.native,a.warmup,a.repairs,a.output)
    print(json.dumps({k:r[k] for k in ('actions','hourly_state_counts','drawdown')}, indent=2))

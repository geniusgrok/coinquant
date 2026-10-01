"""Attribute recorded account divergences without inventing new replay returns."""
import argparse
import hashlib
import json
from decimal import Decimal as D
from itertools import zip_longest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITY_FIELDS = ('window_start', 'window_end', 'fx', 'conversion', 'schedule_sha256',
                   'executed_starts_sha256', 'mark_gap', 'latency_ms', 'matcher')
KNOBS = ('primary_risk', 'macro_risk', 'impulse_atr', 'atr_bars', 'take_power',
         'life_bars', 'retrace', 'dfii_drop', 'weight_limit', 'book_participation',
         'fee', 'trigger_slippage', 'market_slippage', 'read_latency_ms', 'print_window_ms')
TRADE_FIELDS = ('time', 'side', 'qty', 'price')


def compare(base, changed, *, varying):
    if set(varying) - set(KNOBS):
        raise ValueError('unknown comparison knob')
    for row in (base, changed):
        if not row.get('complete') or not row.get('known_path') or row.get('execution_unresolved'):
            raise ValueError('comparison requires complete, known, settled account paths')
        if row['source'].get('dirty'):
            raise ValueError('recorded source was dirty')
    for key in IDENTITY_FIELDS:
        if base[key] != changed[key]:
            raise ValueError(f'identity mismatch: {key}')
    if base['source']['python_sources_sha256'] != changed['source']['python_sources_sha256']:
        raise ValueError('source mismatch')
    for key in KNOBS:
        if key not in varying and base[key] != changed[key]:
            raise ValueError(f'unregistered difference: {key}')
    bm, cm = base['market_identity'], changed['market_identity']
    for key in set(bm) | set(cm):
        if key in ('loaded_minute_files', 'loaded_print_files'):
            left, right = bm.get(key, {}), cm.get(key, {})
            if any(left[name] != right[name] for name in left.keys() & right.keys()):
                raise ValueError(f'input hash mismatch: {key}')
        elif bm.get(key) != cm.get(key):
            raise ValueError(f'input identity mismatch: {key}')
    first = None
    for index, (left, right) in enumerate(zip_longest(base['trades'], changed['trades'])):
        a = None if left is None else {k: left[k] for k in TRADE_FIELDS}
        b = None if right is None else {k: right[k] for k in TRADE_FIELDS}
        if a != b:
            first = {'index': index, 'baseline': a, 'changed': b,
                     'fields': [k for k in TRADE_FIELDS if a is None or b is None or a[k] != b[k]]}
            break
    session = next(({'index': i, 'start': a['start'],
                     'baseline': {k: a.get(k) for k in ('cycles', 'actions', 'constraints', 'funnel')},
                     'changed': {k: b.get(k) for k in ('cycles', 'actions', 'constraints', 'funnel')}}
                    for i, (a, b) in enumerate(zip(base['session_rows'], changed['session_rows']))
                    if any(a.get(k) != b.get(k) for k in ('cycles', 'actions', 'constraints', 'funnel'))), None)
    result = {'varying': list(varying), 'first_trade_divergence': first,
              'first_session_divergence': session,
              'trade_counts': [len(base['trades']), len(changed['trades'])],
              'final_usdt_change': str(D(changed['final_usdt']) - D(base['final_usdt'])),
              'new_economic_measurement': False,
              'original_path_complete': [base['path_complete'], changed['path_complete']]}
    if set(varying) == {'fee'}:
        notional = sum((D(t['qty']) * D(t['price']) for t in base['trades']), D(0))
        recorded = D(base['fees'])
        if abs(notional * D(base['fee']) - recorded) > D('0.00000001'):
            raise ValueError('baseline fee ledger does not reconcile with the trade ledger')
        extra = notional * (D(changed['fee']) - D(base['fee']))
        result['fixed_fills_extra_fee_usdt'] = str(extra)
        result['fixed_fills_final_usdt'] = str(D(base['final_usdt']) - extra)
        result['remaining_path_effect_usdt'] = str(D(result['final_usdt_change']) + extra)
        result['fixed_fills_note'] = 'Direct fee attribution only; unchanged quantities are not a feasible new account.'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('changed', type=Path)
    parser.add_argument('--varying', required=True, help='comma-separated registered knobs')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists() or args.out.resolve() in (args.baseline.resolve(), args.changed.resolve()):
        parser.error('refusing to overwrite an input or existing analysis; choose a new output name')
    blobs = [path.read_bytes() for path in (args.baseline, args.changed)]
    result = compare(*(json.loads(blob) for blob in blobs), varying=args.varying.split(','))
    result['artifacts'] = [{'path': str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                            'sha256': hashlib.sha256(blob).hexdigest()}
                           for path, blob in zip((args.baseline, args.changed), blobs)]
    result['analysis_source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('first_trade_divergence', 'final_usdt_change')}, indent=2))
    return 0


if __name__ == '__main__':
    main()

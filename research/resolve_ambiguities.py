"""Reproduce baseline exit states without modifying runtime behavior.

The wrappers observe the exact input to liquidation_takeover and delegate it
unchanged. Minute ordering results are conditional on those baseline states;
they are not a recomputed full-account economic result.
"""
import argparse
import csv
import gzip
import json
from pathlib import Path
from unittest.mock import patch

from coinquant import replay
from coinquant.config import load
from coinquant.data import Dataset
from coinquant.research import digest, iso, spec
from coinquant.types import D, serial


def classify(position, rows):
    long = position.quantity > 0
    stop, liq = position.stop_loss, position.liquidation
    first_stop = next((int(r['time']) for r in rows
                       if D(r['mark_low']) <= stop), None) if long else next(
        (int(r['time']) for r in rows if D(r['mark_high']) >= stop), None)
    first_liq = next((int(r['time']) for r in rows
                      if D(r['mark_low']) <= liq), None) if long else next(
        (int(r['time']) for r in rows if D(r['mark_high']) >= liq), None)
    if first_stop is None or first_liq is None:
        status = 'minute_and_hour_extrema_disagree'
    elif first_stop < first_liq:
        status = 'stop_trigger_precedes_liquidation_level'
    elif first_stop == first_liq:
        r = next(r for r in rows if int(r['time']) == first_stop)
        op = D(r['mark_open'])
        if (long and liq < op <= stop) or (not long and stop <= op < liq):
            status = 'stop_already_crossed_at_minute_open'
        else:
            status = 'still_ambiguous_within_same_minute'
    else:
        status = 'liquidation_level_precedes_stop'
    return {'first_stop_ms': first_stop, 'first_liquidation_ms': first_liq,
            'status': status, 'note': 'trigger order only; not proof of complete stop fill'}


def assess_stop_execution(position, rows, rules):
    """Conservative minute liquidity at/after trigger, conditioned on baseline state."""
    remaining = abs(position.quantity)
    long = position.quantity > 0
    triggered = False
    fills = []
    for row in rows:
        t = int(row['time'])
        op, low, high = (D(row[k]) for k in ('mark_open', 'mark_low', 'mark_high'))
        at_liq = op <= position.liquidation if long else op >= position.liquidation
        hit_liq = low <= position.liquidation if long else high >= position.liquidation
        at_stop = op <= position.stop_loss if long else op >= position.stop_loss
        hit_stop = low <= position.stop_loss if long else high >= position.stop_loss
        if at_liq:
            return {'status': 'liquidation_before_complete_stop', 'remaining': str(remaining), 'fills': fills}
        # Previously active market stop or known-open stop gets first execution
        # opportunity; same-minute new trigger vs liquidation stays conservative.
        if hit_liq and not (triggered or at_stop):
            return {'status': 'unresolved_same_minute', 'remaining': str(remaining), 'fills': fills}
        if triggered or hit_stop:
            triggered = True
            capacity = (D(row['volume']) * D('.01') / rules.step).to_integral_value(rounding='ROUND_DOWN') * rules.step
            amount = min(remaining, capacity, rules.maximum)
            if amount >= rules.minimum:
                price = replay.hosted_exit_price(position, position.stop_loss,
                        D(row['open']), D('.001'), adverse_gap=True)
                fills.append({'time': t, 'quantity': str(amount), 'price': str(price)})
                remaining -= amount
                if not remaining:
                    return {'status': 'fully_stopped_before_liquidation_level', 'remaining': '0', 'fills': fills}
        if hit_liq:
            return {'status': 'remaining_exposure_reaches_liquidation', 'remaining': str(remaining), 'fills': fills}
    return {'status': 'stop_incomplete_at_hour_end', 'remaining': str(remaining), 'fills': fills}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--minutes', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    frozen = spec()
    minute_root = Path(args.minutes)
    output = Path(args.output); output.mkdir(parents=True, exist_ok=False)
    original_ticks = Dataset.ticks
    original_takeover = replay.liquidation_takeover
    current = {}; events = []

    def ticks(dataset):
        for tick in original_ticks(dataset):
            current['tick'] = tick
            yield tick

    def takeover(account, rules):
        tick = current['tick']; t = tick.trade.time
        folder = minute_root / iso(t)[:10]
        inventory = json.loads((folder / 'v5-inventory.json').read_text())
        entry = next(iter(inventory['shards'].values()))['bars']
        path = folder / entry['path']
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ValueError('minute evidence changed')
        with gzip.open(path, 'rt') as stream:
            rows = [r for r in csv.DictReader(stream) if t <= int(r['time']) < t + 3600000]
        if [int(r['time']) for r in rows] != list(range(t, t + 3600000, 60000)):
            raise ValueError('incomplete native event hour')
        p = account.position
        events.append({'time': t, 'utc': iso(t), 'position': serial(p),
                       'hour_mark': serial(tick.mark),
                       'minute_file_sha256': entry['sha256'],
                       **classify(p, rows),
                       'stop_execution': assess_stop_execution(p, rows, rules)})
        return original_takeover(account, rules)

    with patch.object(Dataset, 'ticks', ticks), patch.object(replay, 'liquidation_takeover', takeover):
        result = replay.run(args.manifest, output / 'baseline', load('config.example.json'))
    report = {'qualification': 'NOT_QUALIFIED', 'baseline_result': result,
              'events': events, 'observer_sha256': digest(__file__),
              'scope': 'exact baseline states plus native-minute trigger evidence; no changed economics'}
    (output / 'ambiguities.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'events': len(events), 'ordering': [e['status'] for e in events],
                      'baseline_cagr': result.get('cagr'), 'baseline_mdd': result.get('mdd')}))


if __name__ == '__main__':
    main()

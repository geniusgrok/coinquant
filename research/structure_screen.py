"""Cash-short screening through actual finite sessions and trade-print fills."""
import argparse
from collections import OrderedDict
from contextlib import nullcontext
from datetime import datetime, timezone
from decimal import Decimal as D
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import tempfile
import time

from coinquant.config import Config
from coinquant.session import run
from research import rebuild, session_schedule, structure_perp as candidate
from research.comparison_report import audit
from research.complete_perp import ResearchExchange
from research.session_market import load_base, TradePrints
from research.unified_perp import PriorFX


class BoundedPrints(TradePrints):
    """Read original public ZIPs; at most three scratch links/binary/array days.

    The shared cache holds market inputs only, never account or execution state.
    No download, original-file mutation, or whole-vault checksum pass.
    """
    def __init__(self, root, originals):
        super().__init__(root)
        self.root.mkdir(parents=True)
        self.originals, self.days = Path(originals), OrderedDict()

    def _load(self, day_ms):
        if day_ms in self.days:
            self.days.move_to_end(day_ms)
            self._day_ms, self._rows = day_ms, self.days[day_ms]
            return self._rows
        name = f'BTCUSDT-aggTrades-{datetime.fromtimestamp(day_ms/1000, timezone.utc):%Y-%m-%d}.zip'
        for suffix in ('', '.CHECKSUM'):
            origin = self.originals/(name+suffix)
            if origin.exists():
                (self.root/(name+suffix)).symlink_to(origin)
        self.days[day_ms] = super()._load(day_ms)
        while len(self.days) > 3:
            old, _ = self.days.popitem(last=False)
            old_name = f'BTCUSDT-aggTrades-{datetime.fromtimestamp(old/1000, timezone.utc):%Y-%m-%d}.zip'
            for suffix in ('', '.CHECKSUM'):
                (self.root/(old_name+suffix)).unlink(missing_ok=True)
            for path in (self.root.parent/(self.root.name+'-cache')).glob(old_name+'.*.bin'):
                path.unlink()
        return self._rows


def window(market, tape, fx, starts, begin, end, scratch):
    accounts = []
    for i, name in enumerate(('baseline', 'candidate')):
        initial = D(10000)/fx(begin)*D('.999')
        e = ResearchExchange(market, begin, initial, fx=fx, matcher='trade_print', prints=tape,
                             uid=12000+i, terminal_ms=end)
        e.read_latency_ms, e.latency_ms, e.mark_gap = 200, 1000, 'bound'
        accounts.append({'name': name, 'exchange': e, 'initial': initial,
                         'state': scratch/name, 'sessions': []})
    for index, start in enumerate(starts):
        for c in accounts:
            e = c['exchange']
            with (candidate.variant() if c['name'] == 'candidate' else nullcontext()):
                e.advance_unattended(max(e.now_ms, start))
                report = run(Config(str(e.uid), str(c['state']), 300, 5), e,
                             execute=True, monotonic=e.monotonic, wait=e.wait)
                c['sessions'].append({'start_ms': start, 'status': report['status'],
                    'execution_unresolved': bool(report.get('execution_unresolved')),
                    'cleanup': report.get('cleanup'), 'cycles': report.get('cycles'),
                    'observations': rebuild._harvest(c['state'])})
        if index % 10 == 0:
            print(json.dumps({'session': index, 'date': rebuild.iso(start)}), flush=True)
    results = {}
    for c in accounts:
        e = c['exchange']
        e.advance_unattended(max(e.now_ms, end))
        mark = rebuild._final_mark(e) if e.q else D(0)
        equity = e.wallet+(e.q*(mark-e.entry) if e.q else D(0))
        e.capture(e.now_ms, mark)
        qty, short_entries = D(0), 0
        for trade in e.trades:
            delta = D(trade['qty'])*(1 if trade['side'] == 'BUY' else -1)
            if qty == 0 and delta < 0:
                short_entries += 1
            qty += delta
        row = {'complete': False, 'cagr': None, 'initial_cny': '10000',
            'final_cny': str(equity*e._cny()), 'final_usdt': str(equity), 'mdd': str(e.mdd_envelope),
            'position': str(e.q), 'fees': str(e.fees), 'funding': str(e.funding_paid),
            'final_mark': str(mark), 'known_path': e.known_path, 'unknown_from': e.unknown_from,
            'hindsight_bounded': e.hindsight_bounded, 'bounded_minutes': e.bounded_minutes,
            'trades': e.trades, 'funding_ledger': e.income, 'sessions': c['sessions'],
            'daily': [v for _, v in sorted(e.daily.items())],
            'execution_unresolved': sum(r['execution_unresolved'] for r in c['sessions']),
            'component_fill_events': short_entries, 'audit': None}
        row['audit'] = audit(row, c['initial'], mark)
        row['window_account_finished'] = (len(c['sessions']) == len(starts) and row['audit']['passed']
            and not row['execution_unresolved'] and row['known_path'])
        results[c['name']] = row
    return results


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('market', 'prints', 'fx', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args(argv)
    source = rebuild.source_identity()
    if source['dirty']:
        raise ValueError('freeze sources before financial screening')
    spec = json.loads(candidate.SPEC.read_text())
    schedule = session_schedule.load()['primary']
    fx, market = PriorFX(args.fx), load_base(args.market)
    # Share verified parsed months only inside this invocation, then release them.
    market._load_month = lru_cache(maxsize=8)(market._load_month)
    args.out.mkdir(parents=True, exist_ok=True)
    started, rows, rejected = time.monotonic(), [], []
    with tempfile.TemporaryDirectory(prefix='cash-short-screen-') as directory:
        tape = BoundedPrints(Path(directory)/'prints', args.prints)
        for index, dates in enumerate(spec['windows']):
            if time.monotonic()-started >= spec['screen']['max_wall_seconds']:
                rejected.append('RESOURCE_BUDGET_EXHAUSTED'); break
            begin, end = map(rebuild.timestamp, dates)
            starts = [s for s in schedule['starts_ms'] if begin <= s < end]
            if not starts:
                raise ValueError('empty registered session window')
            pair, short = {}, window(market, tape, fx, starts, begin, end, Path(directory)/str(index))
            for name, raw in short.items():
                path = args.out/f'window-{index}-{name}.json.gz'
                with gzip.open(path, 'wt') as handle:
                    json.dump(raw, handle, separators=(',', ':'))
                pair[name] = {k: raw[k] for k in ('final_cny', 'mdd', 'audit', 'execution_unresolved', 'component_fill_events')}
                pair[name].update(finished=raw['window_account_finished'], sessions=len(raw['sessions']),
                    fills=len(raw['trades']), raw_file=path.name, raw_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            row = {'window': dates, **pair,
                'paired_log_wealth_gain': math.log(float(pair['candidate']['final_cny'])/float(pair['baseline']['final_cny'])),
                'mdd_increase': float(pair['candidate']['mdd'])-float(pair['baseline']['mdd'])}
            rows.append(row)
            print(json.dumps(row), flush=True)
            if not all(v['finished'] for v in pair.values()):
                rejected.append('ACCOUNT_OR_EXECUTION_GATE_FAILED')
            if row['mdd_increase'] > spec['screen']['maximum_each_window_mdd_increase']:
                rejected.append('WINDOW_RISK_INCREASE_EXCEEDED')
            market._load_month.cache_clear()
            if rejected:
                break
        loaded_prints = tape.loaded
    gain = sum(r['paired_log_wealth_gain'] for r in rows)
    events = sum(r['candidate']['component_fill_events'] for r in rows)
    if gain < spec['screen']['minimum_sum_paired_log_wealth_gain']:
        rejected.append('INSUFFICIENT_PAIRED_WEALTH_GAIN')
    if events < spec['screen']['minimum_component_fill_events']:
        rejected.append('NO_COMPONENT_FILL_EVENTS')
    result = {'source': source, 'spec_sha256': hashlib.sha256(candidate.SPEC.read_bytes()).hexdigest(),
        'schedule_sha256': schedule['sha256'], 'fx_sha256': fx.sha256, 'market_identity': market.identity,
        'loaded_minute_files': market.loaded, 'loaded_print_files': loaded_prints,
        'rows': rows, 'sum_paired_log_wealth_gain': gain, 'component_fill_events': events,
        'decision': 'SCREEN_REJECTED' if rejected else 'FULL_MEASUREMENT_ENTRANT',
        'reasons': rejected, 'wall_seconds': time.monotonic()-started,
        'historical_screen_only': True, 'production_promoted': False, 'native_qualified': False}
    (args.out/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'loaded_minute_files', 'loaded_print_files')}), flush=True)


if __name__ == '__main__':
    main()

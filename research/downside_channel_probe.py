"""Frozen short channel diagnostic; never executes or qualifies native orders."""
import argparse
import contextlib
import hashlib
import json
from decimal import Decimal as D
from pathlib import Path

from coinquant.channel_core import ChannelCore
from coinquant.research import invocations, iso, spec, timestamp
from research.bounded_execution_replay import prepare
from research.multiscale_data import extend_minutes
from research.persistent_hold_replay import HOUR, run
from research.sustainable_replay import exit_minutes
from research.verify_account_ledger import verify

SOURCES = ('coinquant/channel_core.py', 'research/persistent_hold_replay.py',
           'research/downside_channel_probe.py',
           'evidence/downside-channel-20260924/PROTOCOL.md')


def call_hours(cache):
    cfg = spec()
    start, end = timestamp(cfg['start']), timestamp(cfg['development_end'])
    warm, trade = cache[2], cache[0]['klines']
    model = ChannelCore(-1)
    states = {}
    for t in range(min(warm), end, 4*HOUR):
        source = warm if t < start else trade
        bars = [source[x] for x in range(t, t+4*HOUR, HOUR)]
        states[t+4*HOUR] = model.update(t+4*HOUR,
            max(D(r[2]) for r in bars), min(D(r[3]) for r in bars), D(bars[-1][4]))
    calls = [t for t in invocations(cfg) if t < end]
    selected = [t for t in calls if states[t//(4*HOUR)*4*HOUR]]
    marks, trade = cache[0]['markPriceKlines'], cache[0]['klines']
    crossing = set()
    for t, nxt in zip(calls, calls[1:]+[end]):
        opportunity = states[t//(4*HOUR)*4*HOUR]
        if opportunity is None:
            continue
        entry = D(trade[t][1]); stop = opportunity.stop
        take = entry * (entry/stop)**20
        for hour in range(t, nxt, HOUR):
            mark = marks[hour]
            if D(mark[2]) >= stop or D(mark[3]) <= take:
                crossing.add(hour)
    return selected, crossing


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bounded', required=True, type=Path)
    p.add_argument('--sx60', required=True, type=Path)
    p.add_argument('--extra', type=Path, action='append', default=[])
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    if a.output.exists() or a.output.with_suffix('.invocation.json').exists():
        p.error('refusing to overwrite a research original')
    root = a.bounded/'inputs'/'development'
    prepared = exit_minutes(a.sx60/'exit-minutes', prepare(root,
        a.bounded/'old-controls'/'development', a.bounded/'inputs'/'entry-minutes',
        a.bounded/'evidence'/'MINUTE_REQUEST.json', a.bounded/'inputs'/'mark-repair'))
    candidate_calls, crossing = call_hours(prepared[0])
    sources = [a.bounded/'inputs', a.bounded/'inputs'/'entry-minutes', a.sx60/'exit-minutes', *a.extra]
    index = {(kind, path.name.removeprefix('BTCUSDT-1m-').removesuffix('.zip')) for source in sources
             for path in source.rglob('BTCUSDT-1m-*.zip')
             for kind in (('markPriceKlines' if 'markPriceKlines' in path.parts else 'klines'),)}
    # Load available official minutes now; held crossing hours without them still fail closed.
    hours = [t for t in set(candidate_calls)|crossing if
        ('klines',iso(t-60_000)[:10]) in index or ('klines',iso(t-60_000)[:7]) in index]
    hours = [t for t in hours if all((kind, iso(t)[:10]) in index or
        (kind, iso(t)[:7]) in index
        for kind in ('klines','markPriceKlines'))]
    prepared = extend_minutes(prepared, sources, hours, skip_invalid=True)
    cache, minutes, _, validation, data_id = prepared
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.with_suffix('.invocation.json').write_text(json.dumps(dict(
        candidate='downside-channel-short-probe', complete_calls=468,
        available_signal_calls=len(candidate_calls), potential_protection_hours=len(crossing),
        refined_hours=len(hours),
        source_identity={s:hashlib.sha256(Path(s).read_bytes()).hexdigest() for s in SOURCES},
        input_identity=data_id, minute_validation=validation), indent=2)+'\n')
    try:
        with a.output.with_suffix('.log').open('w') as log, contextlib.redirect_stdout(log):
            result = run(root/'native', root/'warmup', root/'repairs', a.output,
                allocation='volatility', reference='channel_core_short', lifecycle='one_campaign',
                entry_side='short', risk_scale=D('3.6'), short_risk_scale=D('3.6'),
                quantity_rules=root/'quantity/current-instrument.json',
                cached_inputs=cache, cached_minutes=minutes)
        result['candidate'] = 'downside-channel-short-probe'
        result['ledger'] = verify(a.output)
        (a.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({k:result[k] for k in ('candidate','cagr','mdd_conservative_envelope','final_cny','counts')}, indent=2))
    except BaseException as exc:
        a.output.with_suffix('.failure.txt').write_text(repr(exc)+'\n')
        raise


if __name__ == '__main__':
    main()

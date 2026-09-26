"""Local-only replay of the fixed execution/risk frontier. No exchange writes.

The shared account receives each budget explicitly. Full-window new budgets
require a source- and evidence-bound development selection, not the old 3.6 gate.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import re
from pathlib import Path
from decimal import Decimal as D

from coinquant.research import timestamp
from research.bounded_execution import ExecutionStudy, risk_scale
from research.bounded_execution_data import load_entry_minutes
from research.minute_evidence import load as load_original_minutes
from research.persistent_hold_replay import inputs, run
from research.verify_account_ledger import verify

SOURCES = ('research/persistent_hold_replay.py', 'research/bounded_execution.py',
           'research/bounded_execution_data.py', 'research/bounded_execution_replay.py',
           'research/minute_evidence.py', 'research/verify_account_ledger.py',
           'coinquant/linear_account.py', 'coinquant/linear_sizing.py',
           'coinquant/campaign.py', 'coinquant/opportunities.py', 'research/legacy/spec.json', 'research/invocation_draws.json')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_identity():
    return {name: digest(name) for name in SOURCES}


def input_identity(identity):
    # Local directory relocation is not a change to a historical input version.
    return hashlib.sha256(json.dumps(sorted(r['sha256'] for r in identity)).encode()).hexdigest()


def prepare(root, baseline, entry_minutes, request, repair=None, *, full=False):
    cache = inputs(root/'native', root/'warmup', root/'repairs', full_window=full)
    original = json.loads((baseline/'inputs.json').read_text())
    days = sorted({r['path'][-14:-4] for r in original
                   if '/1m/' in r.get('path', '') and re.fullmatch(r'\d{4}-\d{2}-\d{2}', r['path'][-14:-4])})
    days = [day for day in days if timestamp(day+'T00:00:00Z') in cache[0]['klines']]
    minute_tables, identity = load_original_minutes(root/'minutes', cache[0], days)
    added, quotes, extra, validation = load_entry_minutes(
        entry_minutes, cache[0], json.loads(request.read_text())['entry_hours_ms'], repair=repair)
    for kind in minute_tables:
        minute_tables[kind].update(added[kind])
    identity.extend(extra)
    all_identity = cache[3] + identity + [dict(sha256=digest(root/'quantity/current-instrument.json'))]
    return cache, (minute_tables, identity), quotes, validation, input_identity(all_identity)


def run_account(root, output, prepared, budget=D('3.6'), *, sliced=True, stress=False, full=False):
    budget = risk_scale(budget)
    cache, minutes, quotes, validation, data_id = prepared
    cfg = ExecutionStudy(sliced, stress, frozenset(validation['hours']), quotes, budget)
    output.parent.mkdir(parents=True, exist_ok=True)
    invocation = output.with_suffix('.invocation.json')
    if output.exists() or invocation.exists():
        raise ValueError('retain existing evidence; refusing output overwrite')
    frozen = dict(risk_scale=str(budget), full_window=full, execution=cfg.configuration(),
                  input_identity=data_id, source_identity=source_identity(), minute_validation=validation)
    invocation.write_text(json.dumps(frozen, indent=2)+'\n')
    with output.with_suffix('.log').open('w') as log, contextlib.redirect_stdout(log):
        result = run(root/'native', root/'warmup', root/'repairs', output,
                     allocation='volatility', reference='impulse_hold', lifecycle='one_campaign',
                     entry_side='long', short_risk_scale=D(0), risk_scale=budget,
                     quantity_rules=root/'quantity/current-instrument.json', cached_inputs=cache,
                     cached_minutes=minutes, execution=cfg, full_window=full)
    audit = verify(output)
    (output/'LEDGER_AUDIT.json').write_text(json.dumps(audit, indent=2)+'\n')
    return result


def verify_selection(path, budget, *, stress=False):
    """Verify preserved evidence and economic source before opening full history."""
    selection = json.loads(path.read_text())
    budget = risk_scale(budget)
    if selection.get('source_identity') != source_identity():
        raise ValueError('selection belongs to another economic source')
    for name, expected in selection['files'].items():
        if digest(path.parent/name) != expected:
            raise ValueError('selection evidence changed: '+name)
    chosen = risk_scale(selection['selected_risk_scale'])
    if budget != chosen and not (stress and budget == D('3.6')):
        raise ValueError('budget was not selected before full-window results')
    base = json.loads((path.parent/selection['baseline_main']).read_text())
    base_stress = json.loads((path.parent/selection['baseline_stress']).read_text())
    main = json.loads((path.parent/selection['selected_main']).read_text())
    stressed = json.loads((path.parent/selection['selected_stress']).read_text())
    for value in (main, stressed):
        if (D(value['risk_scale']) != chosen or value['execution']['mode'] != 'five_minute'
                or value['validation_used'] or value['schedule_sha256'] != base['schedule_sha256']
                or value['counts'].get('liquidation', 0)):
            raise ValueError('selected account identity or liquidation mismatch')
    if (main['execution']['cost_multiplier'] != 1 or stressed['execution']['cost_multiplier'] != 2
            or main['cagr'] <= base['cagr'] or D(main['mdd_conservative_envelope']) >= D('.5')
            or D(stressed['final_cny']) <= D(base_stress['final_cny'])):
        raise ValueError('selected account fails the frozen continuation rule')
    if stress:
        full_path = path.parent/selection['selected_full']
        full = json.loads(full_path.read_text())
        full_base = json.loads((path.parent/selection['baseline_full']).read_text())
        if (D(full['risk_scale']) != chosen or not full['validation_used']
                or full['cagr'] <= full_base['cagr'] or full['counts'].get('liquidation', 0)):
            raise ValueError('full-window stress requires the improved selected full account')
        measured = json.loads(full_path.parent.with_suffix('.invocation.json').read_text())
        if measured['source_identity'] != selection['source_identity']:
            raise ValueError('full account was measured under another source')
    return selection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input-root', 'baseline', 'entry-minutes', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--mark-repair', type=Path)
    parser.add_argument('--request', type=Path, default=Path('evidence/bounded-execution-20260922/MINUTE_REQUEST.json'))
    parser.add_argument('--risk-scale', type=risk_scale, default=D('3.6'))
    parser.add_argument('--full-window', action='store_true')
    parser.add_argument('--stress', action='store_true')
    parser.add_argument('--selection', type=Path)
    parser.add_argument('--development-root', type=Path)
    parser.add_argument('--mode', choices=('both', 'instant', 'five-minute'), default='both')
    args = parser.parse_args()
    selection = None
    if args.full_window:
        if args.selection:
            if args.mode != 'five-minute':
                parser.error('frontier full-window selection is five-minute only')
            selection = verify_selection(args.selection, args.risk_scale, stress=args.stress)
            if digest(args.request) != selection['request_sha256']:
                parser.error('minute request differs from the frozen selection')
        else:
            # Preserve the original 3.6-only reproduction entry, never grant it to new budgets.
            if args.risk_scale != D('3.6') or args.stress or args.development_root is None:
                parser.error('new budgets/full stress require a frozen frontier selection')
            old = json.loads((args.development_root/'development-instant/result.json').read_text())
            new = json.loads((args.development_root/'development-five-minute/result.json').read_text())
            if (D(new['risk_scale']) != D('3.6') or new['cagr'] <= old['cagr']
                    or D(new['mdd_conservative_envelope']) >= D('.5')
                    or new['schedule_sha256'] != old['schedule_sha256']):
                parser.error('original development comparison is not eligible')
    prepared = prepare(args.input_root, args.baseline, args.entry_minutes, args.request,
                       args.mark_repair, full=args.full_window)
    if selection:
        # Full history adds periods; its development prefix must remain the selected input.
        prefix = prepare(args.input_root, args.baseline, args.entry_minutes, args.request, args.mark_repair)
        if prefix[-1] != selection['development_input_identity']:
            parser.error('development data prefix differs from selected accounts')
    stage = ('full-stress' if args.stress else 'full') if args.full_window else ('stress' if args.stress else 'development')
    for sliced in (False, True):
        mode = 'five-minute' if sliced else 'instant'
        if args.mode not in ('both', mode):
            continue
        result = run_account(args.input_root, args.output/(stage+'-'+mode), prepared,
                             args.risk_scale, sliced=sliced, stress=args.stress, full=args.full_window)
        print(json.dumps({k: result[k] for k in ('candidate', 'cagr', 'mdd_conservative_envelope', 'final_cny')}))


if __name__ == '__main__':
    main()

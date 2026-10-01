"""Audit complete shared-venue accounts and report development decisions."""
import argparse
from collections import Counter
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

from research import rebuild
from research.unified_perp import PriorFX
from research.session_market import load_base
from research.session_exchange import SessionExchange
from research.rolling_prints import RollingPrints


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


def assess(accounts, fx_path, market_root=None, prints_root=None):
    fx = PriorFX(fx_path)
    if fx.sha256 != accounts['fx_sha256']:
        raise ValueError('FX bytes differ from the measured account')
    initial = D(10000) / fx(rebuild.timestamp(rebuild.START)) * D('.999')
    final_mark = None
    if all(row['complete'] for row in accounts['results'].values()) and any(
            D(row['position']) for row in accounts['results'].values()):
        if market_root is None or prints_root is None:
            raise ValueError('open accounts need the original final mark and print inputs')
        market = load_base(market_root)
        tape = RollingPrints(prints_root)
        venue = SessionExchange(market, rebuild.timestamp(rebuild.END), D(0), matcher='trade_print', prints=tape)
        final_mark = rebuild._final_mark(venue)
        if any(accounts['loaded_minute_files'].get(name) != digest for name, digest in market.loaded.items()):
            raise ValueError('final mark minute bytes differ from the measured inputs')
        recorded_prints = {}
        for row in accounts['results'].values():
            recorded_prints.update(row['loaded_print_files'])
        if any(recorded_prints.get(name) != digest for name, digest in tape.loaded.items()):
            raise ValueError('final print bytes differ from the measured inputs')
    candidates = {}
    for name, row in accounts['results'].items():
        proof = audit(row, initial, final_mark)
        reasons, alerts = Counter(), Counter()
        cycles = []
        for session in row['sessions']:
            cycles.extend(session.get('cycles', []))
            for cycle in session.get('cycles', []):
                if cycle.get('reason'):
                    reasons[cycle['reason']] += 1
                for alert in cycle.get('alerts', []):
                    if '历史超过七天' in alert or '未覆盖上次' in alert:
                        alerts[alert] += 1
        complete = (row['complete'] and row['cagr'] is not None and row['known_path']
                    and not row['execution_unresolved'] and proof['passed'])
        cagr = row['cagr'] if complete else None
        mdd = D(row['mdd'])
        candidates[name] = {'complete_account_audited': complete, 'audit': proof,
            'final_cny': row['final_cny'], 'cagr': cagr, 'continuous_mdd': str(mdd),
            'economic_targets_met': complete and cagr >= 1.5 and mdd < D('.5'),
            'cagr_shortfall_percentage_points': max(0., 150 - cagr * 100) if cagr is not None else None,
            'risk_constraint_met': complete and mdd < D('.5'), 'trade_fills': len(row['trades']),
            'sessions': len(row['sessions']), 'execution_unresolved_sessions': row['execution_unresolved'],
            'peer_cycles': len(cycles), 'peer_frozen_cycles': sum(bool(cycle['frozen']) for cycle in cycles),
            'peer_freeze_reasons': dict(reasons), 'peer_history_coverage_alerts': dict(alerts),
            'native_verified': False}
    eligible = [name for name, row in candidates.items() if row['risk_constraint_met']]
    comparable = accounts['comparable'] and all(row['complete_account_audited'] for row in candidates.values())
    leader = max(eligible, key=lambda name: D(candidates[name]['final_cny'])) if comparable and eligible else None
    return {'measurement_sources': accounts['sources'], 'baseline_comparable': comparable,
            'candidates': candidates, 'baseline_leader': leader, 'retained_runtime': 'Coinquant',
            'strategy_promoted': False, 'runtime_retired': False,
            'decision': 'Retain the existing Coinquant executor. Shared baseline is evidence for product fit; '
                        'promotion requires pressure evidence and native closure. Starquant remains research only.',
            'native_execution_verified': False, 'out_of_sample': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('accounts', type=Path)
    parser.add_argument('--star-repo', type=Path, default=Path('/workspace/starquant'))
    parser.add_argument('--market', type=Path, default=Path('/tmp/coinquant-market'))
    parser.add_argument('--prints', type=Path, default=Path('/workspace/.btc-third-round-prints'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error('refusing to overwrite an assessment')
    raw = args.accounts.read_bytes()
    report = assess(json.loads(raw), args.star_repo / 'data/usdcny_frankfurter.json', args.market, args.prints)
    report['accounts_sha256'] = hashlib.sha256(raw).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'baseline_leader': report['baseline_leader'], 'strategy_promoted': False}))
    return 0 if all(row['audit']['passed'] for row in report['candidates'].values()) else 2


if __name__ == '__main__':
    raise SystemExit(main())

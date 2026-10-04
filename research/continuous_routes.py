"""Six fixed BTC improvement routes with explicit failure alternatives.

Public/accepted evidence only. Event stress diagnostics cannot adopt a strategy
or substitute for independently financed, shared-runtime account measurement.
"""
import argparse
from collections import Counter
import csv
from decimal import Decimal as D
import gzip
import io
import json
import math
from pathlib import Path
import time
import zipfile

from research import flow_risk as flow

JOINT_SHA = '13d0390ee615ba8b76173b2dfa898eea6658501e1adcf47fb5c26cb0cc346cfe'


def solve(matrix, rhs):
    """Small four-column descriptive regression; no dependency or optimizer."""
    n = len(rhs)
    a = [list(row)+[v] for row, v in zip(matrix, rhs)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda k: abs(a[k][col]))
        if abs(a[pivot][col]) < 1e-12:
            raise ValueError('unidentifiable regression')
        a[col], a[pivot] = a[pivot], a[col]
        scale = a[col][col]
        a[col] = [v/scale for v in a[col]]
        for k in range(n):
            if k != col:
                factor = a[k][col]
                a[k] = [v-factor*w for v, w in zip(a[k], a[col])]
    return [row[-1] for row in a]


def fit(events):
    if len(events) <= 4 or len({e['veto'] for e in events}) != 2:
        return dict(identifiable=False, count=len(events), veto_coefficient=None)
    xs = [[1, int(e['veto']), e['prior_momentum'], e['prior_rms']] for e in events]
    ys = [e['forward_net_return7'] for e in events]
    gram = [[sum(x[i]*x[j] for x in xs) for j in range(4)] for i in range(4)]
    rhs = [sum(x[i]*y for x, y in zip(xs, ys)) for i in range(4)]
    try:
        coefficients = solve(gram, rhs)
        influence = solve(gram, [0, 1, 0, 0])
    except ValueError:
        return dict(identifiable=False, count=len(events), veto_coefficient=None)
    residuals = [y-sum(v*c for v, c in zip(x, coefficients)) for x, y in zip(xs, ys)]
    variance = sum((error*sum(v*c for v, c in zip(x, influence)))**2
                   for x, error in zip(xs, residuals))*len(xs)/(len(xs)-4)
    return dict(identifiable=True, count=len(events), veto_count=sum(e['veto'] for e in events),
                veto_coefficient=coefficients[1], veto_hc1_standard_error=math.sqrt(variance),
                coefficients=coefficients, prospective=False,
                uncertainty='Descriptive HC1 only; overlapping event horizons and multiple research trials are not adjusted.')


def prior(closes, day):
    stamps = list(range(day-20*flow.DAY, day+flow.DAY, flow.DAY))
    if not all(t in closes for t in stamps):
        return None
    returns = [closes[b]/closes[a]-1 for a, b in zip(stamps, stamps[1:])]
    return dict(returns=returns, rms=(sum(r*r for r in returns)/20).sqrt(),
                momentum=closes[day]/closes[stamps[0]]-1,
                worst_down=max(D(0), -min(returns)))


def information(screen, bars, kind):
    closes, events = {t: b[3] for t, b in bars.items()}, []
    fee = D('.003') if kind == 'spot' else D('.0037')
    for e in screen['alpha_events']:
        day = (e['time_ms']//flow.DAY-1)*flow.DAY
        context = prior(closes, day)
        if not e['flow']['available'] or context is None or day+7*flow.DAY not in closes:
            continue
        events.append(dict(id=e['id'], time_ms=e['time_ms'], veto=e['flow']['veto'],
            prior_rms=float(context['rms']), prior_momentum=float(context['momentum']),
            forward_net_return7=float(closes[day+7*flow.DAY]/closes[day]-1-fee)))
    overall = fit(events)
    eras = {name: fit([e for e in events if (e['time_ms'] < flow.CUT) == early])
            for name, early in [('early', True), ('late', False)]}
    checks = dict(coverage=len(events) >= .9*len(screen['alpha_events']),
                  veto_count=sum(e['veto'] for e in events) >= 10,
                  era_count=all(v.get('veto_count', 0) >= 3 for v in eras.values()),
                  effect=overall['identifiable'] and overall['veto_coefficient'] <= -.005,
                  both_eras=all(v['identifiable'] and v['veto_coefficient'] < 0 for v in eras.values()))
    qualifies = all(checks.values())
    return dict(status='SOFT_WEIGHT_ENTRANT' if qualifies else 'INSUFFICIENT_SUPPORT' if not checks['veto_count'] else 'CLOSE_FLOW_INFORMATION_FAMILY',
                gates=checks, overall=overall, eras=eras, events=events,
                expression=dict(status='RESEARCH_ACCOUNT_REQUIRED' if qualifies else 'NOT_ADMITTED_BY_INFORMATION_GATE',
                                multiplier='.75', held_changes=False, hard_veto_result_retained=True))


def pieces(detail, event, kind):
    """Actual attributed future cash basket endpoints, never invented exits."""
    if kind == 'spot':
        result = []
        for w, amount in event.get('reductions', {}).items():
            if not amount:
                continue
            future = [s for s in detail['settlements'] if s['time_ms'] > event['time_ms'] and s['sleeve'] == int(w)]
            if future:
                sold = sum(s['quantity'] for s in future)
                # Each sold fraction ends at its own actual fill. Rounding dust
                # sold months later must not extend the bulk position's risk.
                result.extend((amount*s['quantity']/sold, s['time_ms'],
                               s['proceeds']/s['quantity']/D('.999')) for s in future)
        return result
    future = [t for t in detail['trades'] if t['side'] == 'SELL' and t['time'] > event['time_ms']]
    if not future:
        return []
    sold = sum(D(t['qty']) for t in future)
    return [(event['removed']*D(t['qty'])/sold, t['time'], D(t['price'])) for t in future]


def stress(detail, event, bars, kind):
    total, covered_days = D(0), 0
    for amount, end, terminal in pieces(detail, event, kind):
        # Omit both partial days: a full-day low from before entry or after exit
        # is not an owned loss. This coarse stress is not continuous account MDD.
        lows = [b[2] for t, b in bars.items() if event['time_ms'] < t and t+flow.DAY <= end]
        covered_days += len(lows)
        low = min([event['mark'], terminal, *lows])
        total += amount*max(D(0), event['mark']-low)
    return total, covered_days


def risk_gate(events, controls):
    closed, simple = [e for e in events if e['closed']], [e for e in controls if e['closed']]
    denominator = sum((e['notional'] for e in simple), D(0))
    fraction = sum((e['notional'] for e in closed), D(0))/denominator if denominator else D(0)
    dynamic = sum((e['removed_downside_usdt'] for e in closed), D(0))
    uniform = fraction*sum((e['removed_downside_usdt'] for e in simple), D(0))
    gain = sum((e['gain'] for e in closed), D(0))
    sacrifice = max(D(0), -gain)
    eras = {name: sum((e['time_ms'] < flow.CUT) == early for e in closed) for name, early in [('early', True), ('late', False)]}
    checks = dict(count=len(closed) >= 10, eras=all(v >= 3 for v in eras.values()),
                  risk_removed=dynamic > 0, beats_simple=dynamic > uniform*D('1.20'),
                  affordable=sacrifice <= dynamic*D('.50'))
    return dict(status='RISK_ACCOUNT_ENTRANT' if all(checks.values()) else 'INSUFFICIENT_SUPPORT' if not checks['count'] else 'REJECT_RISK_TRADEOFF',
                gates=checks, closed_count=len(closed), eras=eras, removed_downside_usdt=dynamic,
                uniform_removed_downside_usdt=uniform, net_avoidance_usdt=gain,
                foregone_profit_usdt=sacrifice, sacrifice_per_removed_downside=sacrifice/dynamic if dynamic else None,
                metric='Completed-day-low attributed basket stress, not account risk reduction or MDD.', events=events)


def risk_routes(screen, bars, kind):
    details = {c['id']: c for c in screen['cohort_details']}
    trim, controls = [], []
    for source, target in [(screen['beta_events'], trim), (screen['beta_controls'], controls)]:
        for original in source:
            e = dict(original)
            e['removed_downside_usdt'], e['full_owned_days'] = stress(details[e['id']], e, bars, kind)
            target.append(e)
    held = risk_gate(trim, controls)
    closes, trail = {t: b[3] for t, b in bars.items()}, flow.atr_trail(bars)
    tail, all_entry = [], []
    for original in screen['alpha_events']:
        c = details[original['id']]
        day = (c['time_ms']//flow.DAY-1)*flow.DAY
        context = prior(closes, day)
        if context is None:
            continue
        if kind == 'coin':
            base = D('2.33')*context['rms']*D(7).sqrt()+D('.10')+D('.01')+2*(D('.00075')+D('.0011'))
            scale = base/(base+max(D(0), context['worst_down']-D('.10')))
            quantity = sum(D(t['qty']) for t in c['trades'] if t['side'] == 'BUY')
            mark = c['notional']/quantity
            reductions = {}
        else:
            reserve = trail[day]
            scale = reserve/max(reserve, context['worst_down']+D('.0035'))
            quantity, mark = c['quantity'], c['notional']/c['quantity']
            # Each sibling's original entry share is known through its settled
            # quantities; this only diagnoses reserve, not a legal account size.
            weights = Counter()
            for s in c['settlements']:
                weights[s['sleeve']] += s['quantity']
            reductions = dict(weights)
        event = dict(original, quantity=quantity, mark=mark, removed=quantity, reductions=reductions,
                     reserve_scale=scale, worst_prior_down=context['worst_down'])
        event['removed_downside_usdt'], event['full_owned_days'] = stress(c, event, bars, kind)
        all_entry.append(event)
        if scale < 1:
            affected = dict(event, removed=quantity*(1-scale), notional=original['notional']*(1-scale),
                            gain=original['gain']*(1-scale),
                            removed_downside_usdt=event['removed_downside_usdt']*(1-scale))
            tail.append(affected)
    fallback = risk_gate(tail, all_entry)
    fallback['rule'] = 'Causal max20d downside extra entry reserve beyond incumbent GAP/ATR; never alter held requested target.'
    return dict(held_reassessment=held, entry_reserve_fallback=fallback)


def execution(row, kind):
    if kind == 'spot':
        return dict(status='NO_JUSTIFIED_EXECUTION_CHANGE', fees_usdt=D(row['audit']['fees_usdt']),
                    actual_fills=len(row['fills']), reason='Actual BTC/USDT fees already reconciled; no recorded book counterfactual supports cheaper execution.')
    incomes = row['funding_ledger']
    fees = -sum((D(x['income']) for x in incomes if x['incomeType'] == 'COMMISSION'), D(0))
    funding = -sum((D(x['income']) for x in incomes if x['incomeType'] == 'FUNDING_FEE'), D(0))
    turnover = sum(D(t['qty'])*D(t['price']) for t in row['trades'])
    orders, quantities, constraints = {}, Counter(), Counter()
    for e in row['opportunity_ledger']:
        if e['event'] in ('entry_sizing', 'topup_sizing'):
            constraints[e['event']+':'+str(e['constraint'])] += 1
        if e['event'] == 'write_attempt' and e['method'] == 'POST' and e['payload'].get('timeInForce') == 'IOC':
            orders[e['identity']] = D(e['payload']['quantity'])
        if e['event'] == 'fill' and e['trade']['side'] == 'BUY':
            quantities[e['client_order_id']] += D(e['trade']['qty'])
    return dict(status='NO_JUSTIFIED_EXECUTION_CHANGE', fees_usdt=fees, net_funding_paid_usdt=funding,
                realized_fee_per_notional=fees/turnover, linear_fee_matches=abs(fees-turnover*D('.00075')) < D('1e-12'),
                ioc_orders=len(orders), zero_fill_orders=sum(not quantities[k] for k in orders),
                partial_orders=sum(0 < quantities[k] < v for k, v in orders.items()), constraints=dict(constraints),
                justified_commission_saving_from_fragment_merging=D(0),
                reason='Fee is linear in filled notional; zero-fill IOC has no commission. Maker/missed-fill improvement needs recorded book/counterfactual evidence. Prior single-topup/cost-horizon rejects retained.')


def public_qualification(folder):
    receipts = json.loads((folder/'receipts.json').read_text())
    for receipt in receipts:
        if receipt.get('raw_file'):
            raw = (folder/receipt['raw_file']).read_bytes()
            if flow.sha(raw) != receipt['sha256']:
                raise ValueError('changed public response')
        if receipt.get('status') != 200:
            receipt.update(qualification='PUBLIC_SOURCE_UNAVAILABLE')
            continue
        receipt.update(qualification='HISTORICAL_PUBLICATION_VINTAGE_NOT_PROVEN')
        if receipt['name'].startswith('oi-') or receipt['name'] == 'btc-oi':
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                files = z.infolist()
                if len(files) != 1 or files[0].file_size > 1048576:
                    raise ValueError('OI archive format or bound')
                rows = list(csv.DictReader(io.StringIO(z.read(files[0]).decode())))
                for row in rows:
                    if row.get('symbol') != 'BTCUSDT' or not D(row['sum_open_interest']).is_finite() or D(row['sum_open_interest']) < 0:
                        raise ValueError('invalid BTC OI')
                receipt.update(parsed_rows=len(rows), columns=list(rows[0]) if rows else [],
                               observed_range=[rows[0]['create_time'], rows[-1]['create_time']] if rows else [])
        elif receipt['name'] == 'btc-option-dvol':
            packet = json.loads(raw)
            receipt.update(parsed_rows=len(packet.get('result', {}).get('data', [])),
                           scope='DVOL volatility, not option skew/term-structure; does not replace missing alpha information.')
        else:
            receipt.update(scope='Final ETF flow page; a latest revised table cannot establish historical release time.')
    return dict(status='DATA_NOT_QUALIFIED', sources=receipts,
                action='Retain immutable public responses and receipts; next genuine observation can append separate research evidence. No account diary backfill/reset or trading feed.')


def joint(path):
    raw = path.read_bytes()
    if flow.sha(raw) != JOINT_SHA:
        raise ValueError('accepted actual-budget projection changed')
    packet = json.loads(raw)
    rows = [{k: r[k] for k in ('budgets', 'candidates', 'daily_cny', 'account_return_correlation',
                               'closing_gross_exposure_over_equity', 'account_raw_sha256', 'neutral_reference')}
            for r in packet['portfolios']['selected']]
    return dict(status='ACTUAL_FIXED_BUDGET_EVIDENCE_REUSED', parent=packet['parent'], rows=rows,
                reference=[5000, 5000], transfers=0, continuous_joint_mdd_verified=False,
                decision='No historical-best ratio promotion or dynamic transfer implementation; inspect real jointly financed daily risks and retain simple neutral allocation.')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('spot-root', 'coin-root', 'warmup', 'projections', 'public', 'joint', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args(argv)
    if args.output.exists():
        raise ValueError('do not overwrite retained research')
    began, manifest = time.monotonic(), []
    spot = flow.market(args.spot_root, flow.DAY, manifest)
    coin = flow.aggregate(flow.market(args.coin_root, flow.FOUR, manifest), flow.FOUR)
    raw = args.warmup.read_bytes()
    if flow.sha(raw) != flow.WARMUP:
        raise ValueError('warmup identity')
    coin.update(flow.aggregate(dict(flow.kline(r, 3600000) for r in json.loads(raw)), 3600000))
    results = {}
    for kind in ('spot', 'coin'):
        raw = (args.projections/f'{kind}-baseline-projection.json.gz').read_bytes()
        if flow.sha(raw) != flow.PROJECTIONS[kind]:
            raise ValueError('baseline projection identity')
        ledger = json.loads(gzip.decompress(raw))
        screen = (flow.spot_screen if kind == 'spot' else flow.coin_screen)(ledger, spot, coin, details=True)
        bars = spot if kind == 'spot' else coin
        results[kind] = dict(original_parent=ledger['parent_binding'],
            routes1_2=information(screen, bars, kind), route3=risk_routes(screen, bars, kind),
            route5=execution(ledger, kind))
    result = dict(format='btc-continuous-routes-v1', spec_sha256=flow.sha(Path(__file__).with_name('continuous-spec.json').read_bytes()),
                  source_sha256=flow.sha(Path(__file__).read_bytes()), flow_source_sha256=flow.sha(Path(flow.__file__).read_bytes()),
                  inputs=manifest, projects=results, route4=public_qualification(args.public), route6=joint(args.joint),
                  wall_seconds=time.monotonic()-began, independently_financed_new_accounts=0,
                  prospective_alpha_proven=False, runtime_promoted=False)
    args.output.write_text(json.dumps(flow.serial(result), indent=2)+'\n')
    print(json.dumps({k:dict(info=v['routes1_2']['status'],held=v['route3']['held_reassessment']['status'],
                           entry=v['route3']['entry_reserve_fallback']['status'],execution=v['route5']['status'])
                      for k, v in results.items()}, indent=2))


if __name__ == '__main__':
    main()

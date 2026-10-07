"""Read-only aggregate attribution of two archived simulated wallets.

The input directory holds local receipts, journals and SQLite state. No
timestamps, order identities or individual campaign results are printed.
"""
import argparse
from collections import defaultdict
from decimal import Decimal as D
import bisect
from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path

ROOT = None
STARTS = None


def account(name):
    base = ROOT / 'accounts' / name
    receipt = json.loads((base / 'receipts/027-2026Q3.json').read_text())
    fin = receipt['financial']
    if not receipt['complete'] or not fin['audit']['passed']:
        raise ValueError('incomplete or unaudited wallet')
    db = sqlite3.connect(f'file:{base}/scratch/state/intents.sqlite?mode=ro', uri=True)
    settled = json.loads(db.execute("SELECT value FROM meta WHERE key='settled_entry_campaigns'").fetchone()[0])
    by_order = {row['orderId']: row['clientOrderId'] for row in fin['orders'].values()}
    records = defaultdict(lambda: dict(buy_fills=0, base_buy_fills=0, add_buy_fills=0,
                                       base_buy_qty=D(0), add_buy_qty=D(0), sell_fills=0,
                                       buy_qty=D(0), sell_qty=D(0),
                                       buy_notional=D(0), sell_notional=D(0), fee=D(0),
                                       funding_cost=D(0), funding_events=0, first_buy=None,
                                       last_sell=None, buy_orders=set(), add_orders=set(),
                                       sell_orders=set()))
    position, owner = D(0), None
    funding = sorted((row for row in fin['funding_ledger'] if row['incomeType'] == 'FUNDING_FEE'),
                     key=lambda row: (row['time'], row['tranId']))
    fund_index = 0

    def funding_until(now, inclusive):
        nonlocal fund_index
        while fund_index < len(funding) and (funding[fund_index]['time'] < now or
                                               (inclusive and funding[fund_index]['time'] == now)):
            row = funding[fund_index]
            if owner is None:
                raise ValueError('funding without owned position')
            target = records[owner]
            target['funding_cost'] -= D(row['income'])
            target['funding_events'] += 1
            fund_index += 1

    last_time = -1
    for trade in fin['trades']:
        stamp = trade['time']
        if stamp < last_time:
            raise ValueError('nonchronological trade ledger')
        last_time = stamp
        # Funding at a closing fill's timestamp still belongs to that owner.
        funding_until(stamp, True)
        client = by_order.get(trade['orderId'])
        if client is None:
            raise ValueError('fill missing durable client order identity')
        q, px = D(trade['qty']), D(trade['price'])
        if trade['side'] == 'BUY':
            link = settled.get(client)
            if link is None:
                raise ValueError('BUY fill without durable campaign map')
            campaign = link['campaign']
            if position and owner != campaign:
                raise ValueError('new opportunity bought while foreign campaign held')
            if not position:
                owner = campaign
            target = records[campaign]
            target['buy_fills'] += 1
            if link.get('add', False):
                target['add_buy_fills'] += 1
                target['add_buy_qty'] += q
            else:
                target['base_buy_fills'] += 1
                target['base_buy_qty'] += q
            target['buy_qty'] += q
            target['buy_notional'] += q * px
            target['fee'] += q * px * D('.00075')
            target['buy_orders'].add(client)
            if link.get('add', False):
                target['add_orders'].add(client)
            target['first_buy'] = min(target['first_buy'], stamp) if target['first_buy'] else stamp
            position += q
        elif trade['side'] == 'SELL':
            if owner is None or position < q:
                raise ValueError('SELL lacks proven owned inventory')
            campaign = owner
            target = records[campaign]
            target['sell_fills'] += 1
            target['sell_qty'] += q
            target['sell_notional'] += q * px
            target['fee'] += q * px * D('.00075')
            target['sell_orders'].add(client)
            target['last_sell'] = stamp
            position -= q
            if not position:
                owner = None
        else:
            raise ValueError('unexpected fill side')
    funding_until(10**18, True)
    if fund_index != len(funding) or position != 0 or owner is not None:
        raise ValueError('unclosed account inventory or funding')
    for campaign, row in records.items():
        if row['buy_qty'] != row['sell_qty'] or row['first_buy'] is None or row['last_sell'] is None:
            raise ValueError('campaign inventory did not settle')
        row['pnl'] = row['sell_notional'] - row['buy_notional'] - row['fee'] - row['funding_cost']
        row['entry_session'] = bisect.bisect_right(STARTS, row['first_buy'])
        row['exit_start_interval'] = bisect.bisect_right(STARTS, row['last_sell'])
        row['entry_year'] = datetime.fromtimestamp(row['first_buy']/1000, timezone.utc).year
        row['exit_year'] = datetime.fromtimestamp(row['last_sell']/1000, timezone.utc).year
    if len(records) != len({row['campaign'] for row in settled.values()}):
        raise ValueError('settled campaign map and actual inventory disagree')
    if sum((row['fee'] for row in records.values()), D(0)) != D(fin['fees']):
        raise ValueError('commission accounting does not reproduce wallet')
    if sum((row['funding_cost'] for row in records.values()), D(0)) != D(fin['funding']):
        raise ValueError('funding accounting does not reproduce wallet')
    residual = sum((row['pnl'] for row in records.values()), D(0)) + D(receipt['initial_usdt']) - D(fin['wallet_usdt'])
    if abs(residual) > D('0.000000000000000001'):
        raise ValueError('campaign cashflows do not reproduce terminal wallet')
    return receipt, records


def summary():
    a, b = account('baseline'), account('entry-shock-defer')
    left, right = a[1], b[1]
    if any(len(row['buy_orders'] - row['add_orders']) != 1 for row in list(left.values()) + list(right.values())):
        raise ValueError('campaign has zero or multiple filled opening orders')
    reports = []
    for name in ('baseline', 'entry-shock-defer'):
        path = ROOT / 'accounts' / name / 'scratch/reports.jsonl'
        reports.append([json.loads(line) for line in path.open()])
    if len(reports[0]) != len(STARTS) or len(reports[1]) != len(STARTS):
        raise ValueError('manual session count mismatch')
    if any(x['start_ms'] != y['start_ms'] or x['start_ms'] != start or
           x['pending_intents'] or y['pending_intents'] or
           x['execution_unresolved'] or y['execution_unresolved']
           for x, y, start in zip(*reports, STARTS)):
        raise ValueError('unmatched or unresolved manual session')
    shared, base_only, cand_only = set(left) & set(right), set(left) - set(right), set(right) - set(left)
    print('campaigns',len(left),len(right),'shared',len(shared),'base_only',len(base_only),'cand_only',len(cand_only))
    print('types_baseline',sum(x<0 for x in left),sum(x>0 for x in left),'candidate',sum(x<0 for x in right),sum(x>0 for x in right))
    print('net_buy_fill_delta',sum(x['buy_fills'] for x in right.values())-sum(x['buy_fills'] for x in left.values()))
    print('net_sell_fill_delta',sum(x['sell_fills'] for x in right.values())-sum(x['sell_fills'] for x in left.values()))
    print('shared_first_entry_session_changed',sum(left[k]['entry_session']!=right[k]['entry_session'] for k in shared))
    print('shared_first_entry_time_changed',sum(left[k]['first_buy']!=right[k]['first_buy'] for k in shared))
    print('shared_exit_start_interval_changed',sum(
        left[k]['exit_start_interval'] != right[k]['exit_start_interval'] for k in shared))

    def aggregate(rows):
        return {key: (sum((row[key] for row in rows), D(0)) if key in
                 ('buy_qty','base_buy_qty','add_buy_qty','buy_notional','sell_notional','fee','funding_cost','pnl')
                 else sum(len(row[key]) for row in rows) if key in
                 ('buy_orders','add_orders','sell_orders')
                 else sum(row[key] for row in rows))
                for key in ('buy_fills','base_buy_fills','add_buy_fills','sell_fills',
                            'buy_orders','add_orders','sell_orders', 'buy_qty','base_buy_qty',
                            'add_buy_qty','buy_notional','sell_notional','fee','funding_cost',
                            'funding_events','pnl')}

    def compare(label, keys):
        old = aggregate([left[k] for k in keys if k in left])
        new = aggregate([right[k] for k in keys if k in right])
        print(label, 'campaigns', len(keys), 'delta',
              {k: str(new[k] - v) for k, v in old.items()})

    compare('all',set(left)|set(right))
    compare('baseline_only',base_only)
    compare('shared',shared)
    for year in (2023, 2024):
        keys={k for k,row in left.items() if row['entry_year']==year}
        compare('entry_year_'+str(year), keys)
    for typ in ('macro','primary'):
        keys={k for k in set(left)|set(right) if (k<0)==(typ=='macro')}
        compare(typ, keys)
    print('baseline_multi_order_campaigns', sum(len(row['buy_orders'])>1 for row in left.values()))
    print('candidate_multi_order_campaigns', sum(len(row['buy_orders'])>1 for row in right.values()))
    print('baseline_nonadd_orders', sum(len(row['buy_orders']-row['add_orders']) for row in left.values()))
    print('candidate_nonadd_orders', sum(len(row['buy_orders']-row['add_orders']) for row in right.values()))
    print('baseline_max_nonadd_orders', max(len(row['buy_orders']-row['add_orders']) for row in left.values()))
    print('candidate_max_nonadd_orders', max(len(row['buy_orders']-row['add_orders']) for row in right.values()))
    daily_left = {row['date']: row for row in a[0]['financial']['daily']}
    daily_right = {row['date']: row for row in b[0]['financial']['daily']}
    for year in (2022, 2023, 2024, 2025):
        date = f'{year}-12-31'
        before = daily_left[date]
        after = daily_right[date]
        relative_gap = (D(after['equity_cny']) / D(before['equity_cny']) - 1) * 100
        print('year_end', year, 'relative_equity_gap_pct', round(relative_gap, 4),
              'fee_delta', round(D(after['fees_usdt']) - D(before['fees_usdt']), 2),
              'funding_delta', round(D(after['funding_paid_usdt']) - D(before['funding_paid_usdt']), 2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True,
                        help='Local complete pair directory with session_schedule.json and accounts/')
    options = parser.parse_args()
    ROOT = options.root
    STARTS = json.loads((ROOT / 'session_schedule.json').read_text())['primary']['starts_ms']
    summary()

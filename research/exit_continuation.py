"""Cheap descriptive screen for the frozen ordinary-exit continuation hypothesis."""
import argparse
import gzip
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
from statistics import median

ACCOUNT_SHA = '8277a620e75249017f5594a8f989ce335f7bb6d90814a724ff5eee6b92d3674e'
BAR_SHA = '6a35dadcbe9228d95191a2d2716bc2c2d9f01aa8be08638718325fbefb376009'
ARCHIVE_SHA = 'c9f9b30ab5f5a551a9a9bf5e9bd99ced3dc934b50d116eee1d9f5d59ff941cc3'
DAY = 86400000
FEE = D('.00075')


def read_inputs(account_path, archive_path):
    assert hashlib.sha256(account_path.read_bytes()).hexdigest() == ACCOUNT_SHA
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == ARCHIVE_SHA
    with gzip.open(account_path) as stream:
        account = json.load(stream)
    with zipfile.ZipFile(archive_path) as archive:
        raw = archive.read('daily-composition.json')
    assert hashlib.sha256(raw).hexdigest() == BAR_SHA
    assert account['complete'] and account['session_count'] == 795
    bars = {int(day): value for day, value in json.loads(raw)['bars'].items()}
    return account['financial'], bars


def episodes(financial):
    orders = {int(v['orderId']): v for v in financial['orders'].values()}
    children = {int(v['actualOrderId']): v for v in financial['algos'].values()
                if int(v.get('actualOrderId') or 0)}
    quantity = D(0)
    starts, closed = [], []
    opened = None
    for trade in financial['trades']:
        prior = quantity
        fill = D(trade['qty']) * (1 if trade['side'] == 'BUY' else -1)
        quantity += fill
        assert quantity >= 0
        if prior == 0 and quantity > 0:
            opened = trade['time']
            starts.append(opened)
        if prior > 0 and quantity == 0:
            order = orders[int(trade['orderId'])]
            assert order['type'] == 'MARKET' and opened is not None
            child = children.get(int(trade['orderId']))
            closed.append(dict(opened_ms=opened, closed_ms=trade['time'],
                               order_id=int(trade['orderId']),
                               kind=child['orderType'] if child else 'ordinary',
                               qty=D(order['executedQty'])))
    assert quantity == 0 and len(closed) == 50
    return starts, closed


def stats(rows):
    values = sorted(row['fee_only_return'] for row in rows)
    if not values:
        return None
    lows = sorted(row['tail_low_return'] for row in rows)
    fifth = max(0, (len(values) + 19)//20 - 1)
    return dict(events=len(values), mean=str(sum(values) / len(values)),
                median=str(median(values)), fifth_percentile=str(values[fifth]),
                worst=str(values[0]), positive=sum(value > 0 for value in values),
                equal_notional_net=str(sum(values)),
                half_size_net=str(sum(values)/2),
                intervening_entries=sum(row['intervening_entry'] for row in rows),
                notional_days_usdt=str(sum(row['notional_days_usdt'] for row in rows)),
                tail_low_below_open=sum(row['tail_low_return'] < 0 for row in rows),
                fifth_percentile_tail_low=str(lows[fifth]), worst_tail_low=str(lows[0]))


def run(financial, bars):
    starts, closed = episodes(financial)
    ordinary = [event for event in closed if event['kind'] == 'ordinary']
    assert len(ordinary) == 36

    def observe(event, shift):
        day = (event['closed_ms']//DAY + shift)*DAY
        span = [bars[day + i*DAY] for i in range(8)]
        first, last = D(span[0]['open']), D(span[-1]['open'])
        low = min(D(bar['low']) for bar in span[:7])
        return dict(closed_ms=event['closed_ms'], year=datetime.fromtimestamp(
                        event['closed_ms']/1000, timezone.utc).year,
                    fee_only_return=(last/first)*(1-FEE)**2-1,
                    gross_return=last/first-1,
                    tail_low_return=low/first-1,
                    notional_days_usdt=event['qty']*first*7,
                    intervening_entry=any(event['closed_ms'] < start < day+7*DAY for start in starts))

    rows = [observe(event, 1) for event in ordinary]
    shifted = [observe(event, 2) for event in ordinary]
    split = len(rows)//2
    daily = financial['daily']
    actual_notional_days = sum((D(row['gross_btc_exposure_usdt']) for row in daily), D(0))
    trade_notional = sum((D(t['qty'])*D(t['price']) for t in financial['trades']), D(0))
    result = dict(account_source_sha256=ACCOUNT_SHA, bar_source_sha256=BAR_SHA,
                  ordinary_exits=len(rows), protection_exits=len(closed)-len(rows),
                  first_half=stats(rows[:split]), second_half=stats(rows[split:]),
                  all=stats(rows), start_one_day_later=stats(shifted),
                  by_year={str(year):stats([r for r in rows if r['year'] == year])
                           for year in sorted({r['year'] for r in rows})},
                  baseline=dict(actual_btc_notional_days_usdt=str(actual_notional_days),
                                trade_notional_usdt=str(trade_notional),
                                fees_usdt=financial['fees'], funding_paid_usdt=financial['funding']))
    result['screen_rejected'] = (D(result['first_half']['mean']) <= 0
                                 or D(result['second_half']['mean']) <= 0
                                 or D(result['all']['fifth_percentile']) < D('-.10')
                                 or result['all']['intervening_entries']*2 > len(rows))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--account', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(*read_inputs(args.account, args.archive)), indent=2))

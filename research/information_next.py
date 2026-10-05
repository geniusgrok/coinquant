"""Build a causal closed-window cross-demand packet from bound public raw streams.

No capture, backfill, accounts or orders. A valid input is transport/feature
evidence, not a mature predictor or an account entrant. Coinbase matches expose
maker side; Kraken v2 trades expose taker side. FX comes from a subscribed
Coinbase level2 or public level2_batch book, never from a trade price or an
asserted conversion flag. Batch time is the latest event in that 50ms batch;
its rebuilt state is never made available before the raw receipt.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from research.replacement_routes import number
from research.tradeoff_routes import cross_demand

SECOND = 1_000_000_000
DOCS = {
    'coinbase': '52929f0f85be7632c34f978bd60a153f5dc6b33aab3d41713a9db95565ffd43f',
    'kraken': 'a7fa3c8796b7a3abb5b27cd8cfd0915a69d0d51e13cd916e3b72917557152ada',
}


def bound(path, expected):
    limit = 16 * 1024 * 1024
    if path.stat().st_size > limit:
        raise ValueError('finite stream input exceeds 16 MiB')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('finite stream input grew past 16 MiB')
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected:
        raise ValueError('original raw SHA-256 mismatch')
    return raw


def event_ns(value):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.utcoffset() is None:
        raise ValueError('UTC offset required')
    delta = stamp.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    fraction = re.search(r'\.(\d+)(?:Z|[+-]\d\d:\d\d)$', value)
    if fraction and len(fraction[1]) > 9:
        raise ValueError('sub-nanosecond event clock unsupported')
    remainder = int(fraction[1].ljust(9, '0')) % 1000 if fraction else 0
    return (delta.days * 86400 + delta.seconds) * SECOND + delta.microseconds * 1000 + remainder


def load_stream(binding, decision, sources):
    path = Path(binding['receipt_path'])
    rec = json.loads(bound(path, binding['receipt_sha256']))
    expected_url = {'coinbase': 'wss://ws-feed.exchange.coinbase.com', 'kraken': 'wss://ws.kraken.com/v2'}
    if (rec['venue'] != binding['venue'] or rec['url'] != expected_url[binding['venue']]
            or rec['TLS_verified'] is not True
            or rec['websocket_http_status'] != 101 or rec['connection_attempts'] != 1
            or rec['reconnects'] != 0 or rec['private_request'] is not False
            or rec['failures'] or rec['status'] != 'FIXED_WINDOW_STOP'):
        raise ValueError('failed, reconnected or unqualified stream')
    name = rec['raw_messages_file']
    if Path(name).name != name:
        raise ValueError('raw stream must be beside its original receipt')
    raw = bound(path.parent / name, rec['raw_messages_sha256'])
    if len(raw) != rec['raw_bytes']:
        raise ValueError('original raw byte count mismatch')
    sources.extend([binding['receipt_sha256'], rec['raw_messages_sha256']])
    rows = []
    last = 0
    for line in raw.splitlines():
        item = json.loads(line)
        received = item['receipt_ns']
        if type(received) is not int or received < last or item['opcode'] != 1:
            raise ValueError('nonmonotone receipt or non-text message')
        last = received
        text = item['raw_text']
        if hashlib.sha256(text.encode()).hexdigest() != item['raw_sha256']:
            raise ValueError('original message SHA-256 mismatch')
        if received <= decision:
            rows.append((received, json.loads(text)))
    return rows


def unique_trades(rows):
    unique = {}
    for row in rows:
        identity = row['id']
        if type(identity) is not int or identity < 0:
            raise ValueError('invalid trade sequence')
        if identity in unique and {k: v for k, v in row.items() if k != 'received'} != {
                k: v for k, v in unique[identity].items() if k != 'received'}:
            raise ValueError('conflicting duplicate trade')
        unique.setdefault(identity, row)
    result = sorted(unique.values(), key=lambda r: r['id'])
    if any(b['time'] < a['time'] for a, b in zip(result, result[1:])):
        raise ValueError('trade event time goes backwards in sequence')
    return result


def compile_window(plan):
    start, end, decision = (plan[k] for k in ('start_ns', 'end_ns', 'decision_ns'))
    if any(type(t) is not int for t in (start, end, decision, plan['registered_ns'])):
        raise ValueError('explicit integer clocks required')
    if (not 0 <= plan['registered_ns'] <= start < end <= decision
            or end - start < SECOND or decision - end > 60 * SECOND):
        raise ValueError('registered closed causal window required')
    sources = []
    for venue, expected in DOCS.items():
        binding = plan['semantics'][venue]
        bound(Path(binding['path']), expected)
        if binding['sha256'] != expected:
            raise ValueError('use the original accepted side-semantics document')
        sources.append(expected)
    streams = {}
    for binding in plan['streams']:
        if binding['venue'] in streams or binding['venue'] not in DOCS:
            raise ValueError('exactly two distinct accepted venues required')
        streams[binding['venue']] = load_stream(binding, decision, sources)
    if set(streams) != set(DOCS):
        raise ValueError('paired original streams absent')

    trades = {venue: [] for venue in streams}
    beats, quotes = [], []
    bids, asks = {}, {}
    book_snapshot = False
    level2_ack = False
    last_book_event = 0
    for received, msg in streams['coinbase']:
        kind, product = msg.get('type'), msg.get('product_id')
        if kind == 'subscriptions':
            level2_ack = any(c.get('name') in ('level2', 'level2_batch', 'level2_50') and 'USDT-USD' in c.get('product_ids', [])
                            for c in msg.get('channels', []))
        if product == 'BTC-USD' and kind in ('match', 'last_match', 'heartbeat'):
            stamp = event_ns(msg['time'])
            if stamp > received:
                raise ValueError('future Coinbase exchange event')
            if kind == 'heartbeat':
                beats.append((stamp, msg['last_trade_id'], received))
            else:
                if msg['side'] not in ('buy', 'sell'):
                    raise ValueError('unknown Coinbase maker side')
                trades['coinbase'].append(dict(id=msg['trade_id'], time=stamp, received=received,
                    side='buy' if msg['side'] == 'sell' else 'sell',
                    qty=number(msg['size'], positive=True), price=number(msg['price'], positive=True)))
        if product != 'USDT-USD':
            continue
        if kind == 'snapshot':
            if book_snapshot or not level2_ack:
                raise ValueError('unexpected conversion snapshot or missing level2 acknowledgement')
            bids = {number(p, positive=True): number(q, positive=True) for p, q in msg['bids']}
            asks = {number(p, positive=True): number(q, positive=True) for p, q in msg['asks']}
            book_snapshot = True
        elif kind == 'l2update':
            stamp = event_ns(msg['time'])
            if not book_snapshot or not last_book_event <= stamp <= received:
                raise ValueError('uninitialized or noncausal conversion book')
            for side, price, qty in msg['changes']:
                if side not in ('buy', 'sell'):
                    raise ValueError('unknown conversion book side')
                price, qty = number(price, positive=True), number(qty, nonnegative=True)
                book = bids if side == 'buy' else asks
                if qty:
                    book[price] = qty
                else:
                    book.pop(price, None)
            if not bids or not asks or max(bids) > min(asks):
                raise ValueError('empty or crossed conversion book')
            last_book_event = stamp
            quotes.append(dict(time=stamp, received=received, bid=max(bids), ask=min(asks)))
    for received, msg in streams['kraken']:
        if msg.get('channel') != 'trade' or msg.get('type') != 'update':
            continue
        for trade in msg['data']:
            if trade['symbol'] != 'BTC/USD':
                continue
            stamp = event_ns(trade['timestamp'])
            if stamp > received or trade['side'] not in ('buy', 'sell'):
                raise ValueError('future Kraken event or unknown taker side')
            trades['kraken'].append(dict(id=trade['trade_id'], time=stamp, received=received,
                side=trade['side'], qty=number(trade['qty'], positive=True),
                price=number(trade['price'], positive=True)))

    blockers, flows = [], []
    for venue, values in trades.items():
        values = unique_trades(values)
        before = [r for r in values if r['time'] < start]
        after = [r for r in values if r['time'] >= end]
        if venue == 'coinbase':
            left = [b for b in beats if b[0] < start]
            right = [b for b in beats if b[0] >= end]
            if not left or not right:
                blockers.append('coinbase missing heartbeat boundary fences')
                continue
            low, high = max(left)[1] + 1, min(right)[1]
        else:
            if not before or not after:
                blockers.append('kraken missing before/after trade-ID boundary fences')
                continue
            low, high = before[-1]['id'], after[0]['id']
        ids = [r['id'] for r in values if low <= r['id'] <= high]
        if high < low or len(ids) != high - low + 1 or any(b != a + 1 for a, b in zip(ids, ids[1:])):
            blockers.append(venue + ' incomplete fenced trade-ID coverage')
            continue
        selected = [r for r in values if start <= r['time'] < end]
        buys = sum((r['qty'] for r in selected if r['side'] == 'buy'), Decimal(0))
        sells = sum((r['qty'] for r in selected if r['side'] == 'sell'), Decimal(0))
        if not buys + sells:
            blockers.append(venue + ' empty signed-flow denominator')
        flows.append(dict(venue=venue, buy_btc=str(buys), sell_btc=str(sells)))
    initial = [q for q in quotes if q['time'] <= start and q['received'] <= start]
    if not initial:
        blockers.append('no causal timestamped level2 conversion book at window start')
    else:
        coverage = [initial[-1]] + [q for q in quotes if start < q['time'] <= decision]
        if (start - coverage[0]['time'] > SECOND or decision - coverage[-1]['time'] > SECOND
                or any(b['time'] - a['time'] > SECOND for a, b in zip(coverage, coverage[1:]))
                or any(q['received'] - q['time'] > SECOND for q in coverage)):
            blockers.append('conversion book exceeds one-second window/receipt freshness limit')
    result = dict(status='WAIT_COMPLETE_WINDOW' if blockers else 'CLOSED_RESEARCH_WINDOW',
        blockers=blockers, source_sha256=list(dict.fromkeys(sources)), orders=0, account_entrants=0,
        mature_outcomes=0, predictive_alpha_proven=False,
        meaning='Bound finite raw stream reconstruction; no authenticated funds or economic qualification.')
    if not blockers:
        fx = quotes[-1]
        row = dict(base='BTC', quote='USDT', start_ms=start // 1_000_000, end_ms=end // 1_000_000,
            available_ms=decision // 1_000_000, venues=list(streams), flows=flows,
            complete_window=True, conversion_qualified=True, source_sha256=result['source_sha256'],
            fx_book_ms=fx['time'] // 1_000_000, fx_available_ms=fx['received'] // 1_000_000,
            fx_pair='USDT/USD', fx_bid=str(fx['bid']), fx_ask=str(fx['ask']),
            fx_source_sha256=next(b['receipt_sha256'] for b in plan['streams'] if b['venue'] == 'coinbase'))
        result.update(packet={'decision_ms': row['available_ms'], 'cross-venue': row},
                      observation=cross_demand(row, row['available_ms']))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = compile_window(json.loads(args.plan.read_text()))
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
